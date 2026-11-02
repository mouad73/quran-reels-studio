# Windows download

The portable x64 ZIP is the simplest route for Windows users: extract the whole
archive and open `QuranReelsStudio.exe`. It includes a private Python 3.13.17
runtime, pinned app dependencies, Amiri and the Arabic shaping DLL. It does not
install a global Python or change PATH, the registry, firewall, or system settings.

The first launch downloads the pinned FFmpeg 9.0.2 essentials ZIP directly from
GyanD, verifies its SHA-256 before extracting only the two executables and their
license, and saves a receipt with executable hashes. Later launches reuse the
verified files. If download fails, the launcher shows an error and a log button;
restart after restoring connectivity. Existing keys are never required for setup.

The app and all media processing bind to `127.0.0.1`. The launcher picks a free
port, opens the browser when Streamlit is healthy, and keeps a Windows job object
containing Python and its FFmpeg children. Closing or crashing the launcher stops
that process group. A second launcher instance is rejected. Saved videos remain.

The user data root is `%LOCALAPPDATA%\QuranReelsStudio`. It holds `output/`,
`.cache/`, downloaded FFmpeg, `.streamlit/config.toml`, and `launcher.log`.
Users may supply a local `.env` there themselves; it is never in the download.
The embedded runtime does not include pip or depend on the user's Python.

The launcher uses the .NET Framework already supplied with Windows 10/11. The
executable is unsigned. The Python source installation remains available when
a user's device policy disallows unsigned executables. No security settings
should be disabled to use this tool.

## Build and verify

Build on Windows x64 using Python 3.13 in a venv:

```powershell
python -m venv .package-venv
.package-venv\Scripts\python.exe -m pip install -e ".[dev]"
.package-venv\Scripts\python.exe -m quran_reels.setup_windows
.package-venv\Scripts\python.exe -m pytest -q
.package-venv\Scripts\python.exe packaging/windows/build.py
Expand-Archive -LiteralPath dist/Quran-Reels-Studio-0.3.0-Windows-x64.zip -DestinationPath build/extracted-release
.package-venv\Scripts\python.exe packaging/windows/smoke.py build/extracted-release/QuranReelsStudio
```

The builder refuses to overwrite an existing output directory or release ZIP.
Use `--out build/windows-candidate-2` and move the previous candidate ZIP aside
if a rebuild is necessary. It copies only allowlisted app sources and required
assets, not the repository, existing `.env`, output, caches or private media.
The ZIP includes a package/version manifest, original dependency licenses and
metadata, FriBiDi's corresponding source/build recipe, and a SHA-256 sidecar.
FFmpeg binaries are not redistributed in our ZIP.

`runtime-requirements.lock` pins Windows CPython 3.13 wheels with SHA-256 hashes.
To deliberately refresh it, resolve `runtime-requirements.in` into a **fresh**
`build/windows-wheels` directory using `pip download --only-binary=:all:`, review
the versions, then run `packaging/windows/lock.py`. Do not reuse stale wheels
from a different resolution. Rebuild and verify before publishing.

The package smoke check runs with only `Windows\System32` on PATH and an Arabic
data-folder name. It performs the first-launch upstream download, Arabic shaping,
real H.264/AAC encoding and probing, then starts the embedded Streamlit server and
checks health. This is not a clean Windows VM or a substitute for browser/video
review; native launcher and browser checks are recorded separately in VALIDATION.

The Windows package workflow runs on version tags or manual dispatch. It uploads
the ZIP, checksum and smoke result as Actions artifacts; publication is separate.

## References

- [Python's embeddable distribution](https://docs.python.org/3.13/using/windows.html#the-embeddable-package)
- [Windows .NET Framework versions](https://learn.microsoft.com/en-us/dotnet/framework/install/guide-for-developers)
- [FFmpeg upstream release](https://github.com/GyanD/codexffmpeg/releases/tag/9.0.2)
- [FFmpeg licensing](https://ffmpeg.org/legal.html)
- [FriBiDi source](https://github.com/fribidi/fribidi/releases/tag/v1.0.18)
