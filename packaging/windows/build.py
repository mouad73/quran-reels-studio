"""Build the Windows x64 ZIP from explicit application files and pinned wheels.

Run from a development venv after quran_reels.setup_windows. No user .env,
output videos, caches, credentials, or editable-install metadata are copied.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
PACKAGING = Path(__file__).resolve().parent


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "build" / "windows")
    args = parser.parse_args()
    if sys.platform != "win32" or sys.version_info[:2] != (3, 13):
        raise SystemExit("Build with Python 3.13 x64 on Windows.")
    manifest = json.loads((PACKAGING / "runtime.json").read_text())
    out = args.out.resolve()
    if out.exists():
        raise SystemExit("Output directory already exists. Choose a fresh --out directory.")
    bundle = out / "QuranReelsStudio"
    runtime = bundle / "runtime"
    app = bundle / "app"
    runtime.mkdir(parents=True)
    app.mkdir()
    cache = ROOT / "build" / "windows-downloads"
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / manifest["python"]["url"].rsplit("/", 1)[-1]
    if not archive.exists():
        with urllib.request.urlopen(manifest["python"]["url"], timeout=60) as source, archive.open("wb") as destination:
            shutil.copyfileobj(source, destination)
    if sha(archive) != manifest["python"]["sha256"]:
        raise SystemExit("Python runtime checksum mismatch.")
    with zipfile.ZipFile(archive) as package:
        for member in package.infolist():
            target = (runtime / member.filename).resolve()
            if not target.is_relative_to(runtime.resolve()):
                raise SystemExit("Unexpected Python archive path.")
        package.extractall(runtime)
    (runtime / "python313._pth").write_text("python313.zip\n.\nLib/site-packages\n../app\nimport site\n", encoding="utf-8")
    subprocess.run([sys.executable, "-m", "pip", "install", "--only-binary=:all:", "--require-hashes", "--no-compile", "--target", str(runtime / "Lib" / "site-packages"), "-r", str(PACKAGING / "runtime-requirements.lock")], check=True)
    dll = Path(sys.executable).parent / "fribidi.dll"
    license_dir = Path(sys.prefix) / "fribidi-license"
    if not dll.is_file() or not license_dir.is_dir():
        raise SystemExit("First run this venv's python -m quran_reels.setup_windows.")
    shutil.copy2(dll, runtime / "fribidi.dll")
    shutil.copytree(license_dir, runtime / "fribidi-license")
    # Supply the LGPL library's corresponding source and the actual conda build
    # recipe beside its replaceable DLL, rather than only linking elsewhere.
    from quran_reels import setup_windows
    import zstandard
    source_dir = runtime / "fribidi-source"
    source_dir.mkdir()
    source = cache / "fribidi-1.0.18.tar.xz"
    if not source.exists():
        with urllib.request.urlopen(manifest["fribidiSource"]["url"], timeout=60) as response, source.open("wb") as destination:
            shutil.copyfileobj(response, destination)
    if sha(source) != manifest["fribidiSource"]["sha256"]:
        raise SystemExit("FriBiDi source checksum mismatch.")
    shutil.copy2(source, source_dir / source.name)
    with urllib.request.urlopen(setup_windows.URL, timeout=60) as response:
        conda = response.read(2 * 1024 * 1024)
    if hashlib.sha256(conda).hexdigest() != setup_windows.SHA256:
        raise SystemExit("FriBiDi build package checksum mismatch.")
    verified_dll = False
    with zipfile.ZipFile(io.BytesIO(conda)) as package:
        for entry in package.namelist():
            if not entry.endswith(".tar.zst"):
                continue
            with zstandard.ZstdDecompressor().stream_reader(io.BytesIO(package.read(entry))) as stream:
                with tarfile.open(fileobj=stream, mode="r|") as archive:
                    for member in archive:
                        if not member.isfile():
                            continue
                        if member.name in {"Library/bin/fribidi.dll", "Library/bin/fribidi-0.dll"}:
                            verified_dll = hashlib.sha256(archive.extractfile(member).read()).hexdigest() == sha(runtime / "fribidi.dll")
                        if member.name.startswith("info/recipe/"):
                            target = (source_dir / member.name).resolve()
                            if not target.is_relative_to(source_dir.resolve()):
                                raise SystemExit("Unexpected build recipe archive path.")
                            target.parent.mkdir(parents=True, exist_ok=True)
                            target.write_bytes(archive.extractfile(member).read())
    if not verified_dll:
        raise SystemExit("The build environment's FriBiDi DLL does not match the pinned package.")
    # Explicit source allowlist: no recursive copy of the repository or user data.
    shutil.copy2(ROOT / "app.py", app / "app.py")
    (app / ".streamlit").mkdir()
    shutil.copy2(ROOT / ".streamlit" / "config.toml", app / ".streamlit" / "config.toml")
    package_dir = app / "quran_reels"
    package_dir.mkdir()
    for file in (ROOT / "quran_reels").glob("*.py"):
        shutil.copy2(file, package_dir / file.name)
    shutil.copytree(ROOT / "quran_reels" / "fonts", package_dir / "fonts")
    (app / "desktop-runtime.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    version = __import__("tomllib").loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    shutil.copy2(ROOT / "LICENSE", bundle / "LICENSE-APP.txt")
    shutil.copy2(PACKAGING / "START-HERE.ar.txt", bundle / "START-HERE.ar.txt")
    shutil.copy2(PACKAGING / "THIRD-PARTY.txt", bundle / "THIRD-PARTY.txt")
    shutil.copy2(PACKAGING / "runtime-requirements.lock", bundle / "runtime-requirements.lock")
    compiler = Path(os.environ["WINDIR"]) / "Microsoft.NET" / "Framework64" / "v4.0.30319" / "csc.exe"
    subprocess.run([str(compiler), "/nologo", "/target:winexe", "/platform:x64", "/optimize+", "/utf8output", "/reference:System.Windows.Forms.dll", "/reference:System.Drawing.dll", "/out:" + str(bundle / "QuranReelsStudio.exe"), str(PACKAGING / "Launcher.cs")], check=True)
    # Compile test the embedded runtime with deliberately minimal PATH, no system Python.
    environment = {**os.environ, "PATH": os.path.join(os.environ["WINDIR"], "System32"), "QRS_DATA_DIR": str(out / "verification-data")}
    check = subprocess.run([str(runtime / "python.exe"), "-c", "import quran_reels,streamlit,requests; from PIL import features; assert features.check_feature('raqm'); from streamlit.web import cli; print('Embedded imports and Arabic shaping ready')"], cwd=out, env=environment, check=True, capture_output=True, text=True, timeout=90)
    print(check.stdout.strip())
    packages = []
    for dist in importlib.metadata.distributions(path=[str(runtime / "Lib" / "site-packages")]):
        packages.append({"name": dist.metadata["Name"], "version": dist.version})
    receipt = {"appVersion": version, "architecture": "windows-x64", "python": manifest["python"], "ffmpeg": {**manifest["ffmpeg"], "delivery": "downloaded directly from upstream on first launch; not bundled"}, "packages": sorted(packages, key=lambda item: item["name"].lower()), "fribidiSha256": sha(runtime / "fribidi.dll"), "sourceCommit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "hasUncommittedBuildSources": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())}
    (bundle / "BUILD-MANIFEST.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    destination = ROOT / "dist"
    destination.mkdir(exist_ok=True)
    zip_path = destination / ("Quran-Reels-Studio-" + version + "-Windows-x64.zip")
    if zip_path.exists():
        raise SystemExit("Release ZIP already exists; use a new version or move the previous candidate first.")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as package:
        for file in sorted(bundle.rglob("*")):
            if file.is_file() and "__pycache__" not in file.parts and file.suffix != ".pyc":
                if file.name == ".env" or "secrets.toml" == file.name:
                    raise SystemExit("Private file unexpectedly found in bundle.")
                package.write(file, Path("QuranReelsStudio") / file.relative_to(bundle))
    checksum = sha(zip_path)
    zip_path.with_suffix(".zip.sha256").write_text(checksum + "  " + zip_path.name + "\n", encoding="ascii")
    print(json.dumps({"bundle": str(bundle), "zip": str(zip_path), "bytes": zip_path.stat().st_size, "sha256": checksum}))


if __name__ == "__main__":
    main()
