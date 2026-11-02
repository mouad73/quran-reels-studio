"""Install the missing Windows text-layout DLL into this virtual environment.

The official Pillow Windows wheels need a separate FriBiDi runtime. We fetch a
fixed conda-forge package, verify its SHA-256, and copy only its DLL and license.
No system paths or global Python installation are modified.
"""
import hashlib
import io
import platform
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

URL = "https://conda.anaconda.org/conda-forge/win-64/fribidi-1.0.18-hfd05255_0.conda"
SHA256 = "beb4dad871f0e1fcfb088698ec08898bca9f4b0b385053aafafe4eee352654b5"
CHECK = "import quran_reels; from PIL import features; raise SystemExit(0 if features.check_feature('raqm') else 1)"


def install(*, force=False):
    if sys.platform != "win32":
        print("Windows runtime setup is not needed on this platform.")
        return
    if sys.prefix == sys.base_prefix:
        raise SystemExit("Run this command with the project's .venv Python, not a global Python installation.")
    if platform.machine().upper() not in {"AMD64", "X86_64"}:
        raise SystemExit("This runtime installer supports Windows x64. Use the Docker option for other architectures.")
    # Verify the existing Pillow runtime in a fresh process so feature detection
    # is not cached before a newly installed DLL can be loaded.
    import subprocess
    check = subprocess.run([sys.executable, "-c", CHECK], capture_output=True)
    if check.returncode == 0 and not force:
        print("Arabic text shaping is ready (RAQM/FriBiDi).")
        return
    import zstandard
    print("Installing the pinned conda-forge FriBiDi text-layout runtime into .venv…")
    try:
        with urllib.request.urlopen(URL, timeout=60) as response:
            data = response.read(2 * 1024 * 1024)
    except OSError:
        raise SystemExit("Could not download FriBiDi. Check your connection and rerun setup.") from None
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise SystemExit("FriBiDi package checksum mismatch; nothing was installed.")
    extracted = {}
    with zipfile.ZipFile(io.BytesIO(data)) as package:
        for entry in package.namelist():
            if not entry.endswith(".tar.zst"):
                continue
            with zstandard.ZstdDecompressor().stream_reader(io.BytesIO(package.read(entry))) as stream:
                with tarfile.open(fileobj=stream, mode="r|") as archive:
                    for member in archive:
                        if member.isfile() and (member.name in {"Library/bin/fribidi.dll", "Library/bin/fribidi-0.dll"} or member.name.startswith("info/licenses/")):
                            file = archive.extractfile(member)
                            if file:
                                extracted[member.name] = file.read()
    dll = extracted.get("Library/bin/fribidi.dll") or extracted.get("Library/bin/fribidi-0.dll")
    if not dll or not any(n.startswith("info/licenses/") for n in extracted):
        raise SystemExit("The verified package did not contain the expected DLL and license.")
    scripts = Path(sys.executable).parent
    (scripts / "fribidi.dll").write_bytes(dll)
    license_dir = Path(sys.prefix) / "fribidi-license"
    license_dir.mkdir(exist_ok=True)
    for name, content in extracted.items():
        if name.startswith("info/licenses/"):
            (license_dir / Path(name).name).write_bytes(content)
    result = subprocess.run([sys.executable, "-c", CHECK], capture_output=True)
    if result.returncode:
        raise SystemExit("FriBiDi was installed, but Pillow could not load it. See the README's Windows troubleshooting and Docker option.")
    print("Arabic text shaping is ready. FriBiDi license saved in .venv/fribidi-license/.")


if __name__ == "__main__":
    install()
