"""Bootstrap the private Windows runtime; never installs anything system-wide."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile


MAX_ENGINE_DOWNLOAD = 200 * 1024 * 1024


def data_directory() -> Path:
    """Source installs keep their existing folders; the launcher passes its own."""
    override = os.environ.get("QRS_DATA_DIR")
    return Path(override).resolve() if override else Path(__file__).resolve().parent.parent


def write_status(folder: Path, message: str):
    folder.mkdir(parents=True, exist_ok=True)
    temporary = folder / "launcher-status.tmp"
    temporary.write_text(message, encoding="utf-8")
    os.replace(temporary, folder / "launcher-status.txt")


def engine_files(folder: Path):
    return [folder / "bin" / name for name in ("ffmpeg.exe", "ffprobe.exe")]


def valid_engine(folder: Path, metadata: dict) -> bool:
    try:
        receipt = json.loads((folder / "verified.json").read_text(encoding="utf-8"))
        if receipt["archive_sha256"] != metadata["sha256"]:
            return False
        for file in engine_files(folder):
            with file.open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != receipt["files"][file.name]:
                    return False
        return (folder / "LICENSE").is_file()
    except (OSError, KeyError, ValueError):
        return False


def install_engine(folder: Path, metadata: dict, progress=lambda message: None) -> Path:
    """Download upstream FFmpeg once, verify bytes, and select only required files.

    FFmpeg is not redistributed inside our ZIP. Its executables and license are
    retrieved directly from the pinned upstream release on the user's computer.
    Archive paths are never used as extraction destinations.
    """
    target = folder / "runtime" / ("ffmpeg-" + metadata["version"])
    if valid_engine(target, metadata):
        return target / "bin"
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ffmpeg-setup-", dir=target.parent) as temporary:
        work = Path(temporary)
        archive = work / "download.zip"
        progress("تحميل محرك الفيديو لأول مرة… يتطلب اتصالاً بالإنترنت")
        request = urllib.request.Request(metadata["url"], headers={"User-Agent": "Quran-Reels-Studio/0.3"})
        digest = hashlib.sha256()
        total = 0
        with urllib.request.urlopen(request, timeout=45) as response, archive.open("wb") as stream:
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_ENGINE_DOWNLOAD:
                    raise RuntimeError("The video engine download exceeded the allowed size.")
                digest.update(chunk)
                stream.write(chunk)
                progress(f"تحميل محرك الفيديو: {total // (1024 * 1024)} MB")
        if digest.hexdigest() != metadata["sha256"]:
            raise RuntimeError("The video engine checksum did not match. Nothing was installed. Restart to retry.")
        staged = work / "engine"
        (staged / "bin").mkdir(parents=True)
        wanted = {"ffmpeg.exe": staged / "bin" / "ffmpeg.exe", "ffprobe.exe": staged / "bin" / "ffprobe.exe", "LICENSE": staged / "LICENSE"}
        found = set()
        with zipfile.ZipFile(archive) as package:
            for member in package.infolist():
                name = member.filename.replace("\\", "/").split("/")[-1]
                if name not in wanted or member.is_dir():
                    continue
                if name in found or member.file_size > MAX_ENGINE_DOWNLOAD:
                    raise RuntimeError("Unexpected video engine archive contents.")
                with package.open(member) as source, wanted[name].open("wb") as destination:
                    shutil.copyfileobj(source, destination)
                found.add(name)
        if found != set(wanted):
            raise RuntimeError("The upstream archive is missing the video engine or its license.")
        hashes = {}
        for file in engine_files(staged):
            with file.open("rb") as stream:
                hashes[file.name] = hashlib.file_digest(stream, "sha256").hexdigest()
        (staged / "verified.json").write_text(json.dumps({"archive_sha256": metadata["sha256"], "files": hashes}), encoding="utf-8")
        # A failed/partial installation has no receipt and is never executed.
        target.mkdir(exist_ok=True)
        (target / "bin").mkdir(exist_ok=True)
        for file in [*engine_files(staged), staged / "LICENSE", staged / "verified.json"]:
            relative = file.relative_to(staged)
            os.replace(file, target / relative)
    return target / "bin"


def self_test(app_root: Path, folder: Path):
    """Real packaged-runtime checks, including Arabic shaping and media encoding."""
    from PIL import features
    from .layout import FONT
    assert features.check_feature("raqm"), "Arabic shaping unavailable"
    assert FONT.is_file(), "Bundled Arabic font missing"
    import importlib.metadata
    assert importlib.metadata.version("streamlit")
    work = folder / "self-test"
    work.mkdir(parents=True, exist_ok=True)
    # Test font shaping directly without any network or generated Quran text.
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new("RGB", (640, 360), "#123e33")
    ImageDraw.Draw(image).text((320, 160), "اختبار عرض العربية", font=ImageFont.truetype(str(FONT), 38, layout_engine=ImageFont.Layout.RAQM), fill="white", anchor="mm", direction="rtl")
    image.save(work / "arabic.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", str(work / "arabic.png"), "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000", "-t", "1", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(work / "test.mp4")], check=True, timeout=90, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(work / "test.mp4")], check=True, capture_output=True, text=True, timeout=30, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    streams = json.loads(probe.stdout)["streams"]
    assert {s["codec_name"] for s in streams} >= {"h264", "aac"}
    return {"python": sys.version.split()[0], "streamlit": importlib.metadata.version("streamlit"), "arabicShaping": True, "ffmpegEncoding": True, "appRoot": str(app_root), "dataDirectory": str(folder)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    folder = data_directory()
    folder.mkdir(parents=True, exist_ok=True)
    log_path = folder / "launcher.log"
    with log_path.open("a", encoding="utf-8", buffering=1) as log:
        sys.stdout = sys.stderr = log
        try:
            app_root = Path(__file__).resolve().parent.parent
            config = folder / ".streamlit" / "config.toml"
            if not config.exists():
                config.parent.mkdir(exist_ok=True)
                shutil.copy2(app_root / ".streamlit" / "config.toml", config)
            os.chdir(folder)
            metadata = json.loads((app_root / "desktop-runtime.json").read_text(encoding="utf-8"))
            engine = install_engine(folder, metadata["ffmpeg"], lambda message: write_status(folder, message))
            os.environ["PATH"] = str(engine) + os.pathsep + os.environ.get("PATH", "")
            os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
            if args.self_test:
                result = self_test(app_root, folder)
                (folder / "self-test-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                return 0
            write_status(folder, "بدء تشغيل الأداة على جهازك…")
            from streamlit.web import cli
            sys.argv = ["streamlit", "run", str(app_root / "app.py"), "--server.address=127.0.0.1", f"--server.port={args.port}", "--server.headless=true", "--server.fileWatcherType=none", "--browser.gatherUsageStats=false", "--global.developmentMode=false"]
            return cli.main()
        except Exception:
            import traceback
            traceback.print_exc()
            write_status(folder, "تعذر بدء التشغيل. افتح سجل التشغيل لمعرفة السبب، ثم أعد المحاولة.")
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
