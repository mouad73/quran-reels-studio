# Quran Reels Studio

Create Quran videos on your own computer with scenic backgrounds, original recitation, shaped Arabic captions, and an optional translation of the meaning.

**Choose a passage → review the text → add a Pexels or Pixabay key → generate an MP4.** You can also upload your own footage with no API key. Quran text and recitation come from AlQuran Cloud; no OpenAI account, AI voice, or paid video-generation service is required.

By [TechMouad](https://techmouad.com). [دليل عربي](docs/README.ar.md).

## What it does

- Local Streamlit interface and command-line interface.
- Explicit selection of 1–12 consecutive, complete ayahs.
- Three reciters, English or French meaning, or Arabic only.
- Pexels and Pixabay stock-video search, or your own video.
- Portrait 720p/1080p, square 720p, and landscape 720p.
- Captions timed from decoded ayah audio samples; no invented word-level alignment.
- Complete Arabic and translation text, measured with the bundled Amiri font and RAQM shaping.
- H.264 MP4 with AAC audio, plus a JSON source manifest and credits file.
- Local preview and downloads; no automatic social publishing.
- Upload your own logo; set its position, size and opacity while preserving transparency.
- Show/hide and independently position Arabic text, translation, surah name, ayah reference, reciter name and a custom watermark.
- Live layout preview, adjustable text sizes/widths, background dimming and optional caption panels.

## Install

Requires **Python 3.11+** and **FFmpeg/ffprobe** on PATH. A CPU is sufficient; rendering speed depends on your computer.

Install FFmpeg using your system's package manager, or follow [FFmpeg's download instructions](https://ffmpeg.org/download.html). For example:

```powershell
# Windows with winget; open a new terminal after installation
winget install --id Gyan.FFmpeg --exact
```

```bash
# Ubuntu / Debian
sudo apt-get update && sudo apt-get install ffmpeg python3-venv
# macOS with Homebrew
brew install ffmpeg
```

Download this repository's ZIP and extract it, or clone it:

```bash
git clone https://github.com/mouad73/quran-reels-studio.git
cd quran-reels-studio
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\python.exe -m quran_reels.setup_windows
.venv\Scripts\python.exe -m streamlit run app.py
```

macOS / Linux:

```bash
.venv/bin/python -m pip install -e .
.venv/bin/python -m streamlit run app.py
```

The interface opens at **http://127.0.0.1:8501**. On Windows, `start-windows.bat` creates the environment, installs the app, and starts it. It still requires Python and FFmpeg to be installed first.

Windows x64 also needs FriBiDi for Arabic layout, as described in [Pillow's documentation](https://pillow.readthedocs.io/en/stable/installation/building-from-source.html). The Windows setup command (also run by the launcher) downloads a pinned [conda-forge FriBiDi package](https://anaconda.org/conda-forge/fribidi), checks its SHA-256, and places its DLL and license inside `.venv`. It does not change system settings. If the DLL cannot load, install Microsoft's current x64 Visual C++ Redistributable from its official download page, or use Docker. The bundled runtime installer targets Windows x64; other Windows architectures should use Docker.

## Create your first video

1. Pick **Pexels**, **Pixabay**, or **My own video** in the sidebar.
2. Paste your own provider key, or upload a video you have permission to use.
3. Start with **Surah 112, ayahs 1–4**, Alafasy, and portrait 720p.
4. Click **Load passage for review**. Read the Arabic and meaning and listen to the supplied recordings.
5. In **Design your video**, show/hide elements and set their positions. Upload a logo if desired, then check the layout preview. Confirm the text review and click **Generate video**.
6. Watch the complete result. Download the MP4 or ZIP containing the video, source manifest, and credits.

Get a key from [Pexels](https://www.pexels.com/api/) or [Pixabay](https://pixabay.com/api/docs/). The app uses the [Pexels video search API](https://www.pexels.com/api/documentation/) and [Pixabay video API](https://pixabay.com/api/docs/). Keys are sent only to the selected stock provider and are not put in exported metadata. AlQuran Cloud endpoints used here do not need a key; [their documentation](https://alquran.cloud/api) describes the text and audio editions.

Keys may also be read from a local `.env` file. Copy `.env.example` to `.env` and fill in the provider you use. Never upload `.env` to GitHub.

## Customize the final video

Open an element under **Design your video** to turn it on/off and set its horizontal position, vertical position, text size and maximum width. The surah name and ayah reference have separate controls. You can also show the reciter's name or replace/remove the default watermark with your channel name.

Positions run from **0 to 100** over the space available to that element: 0 is left/top, 50 centers it and 100 aligns it with the right/bottom edge. Text and logos remain inside the frame. Logo width scales with the frame while preserving the original aspect ratio; height is limited to 35% of the frame. PNG, JPEG and WebP logos are accepted, with a 10 MB / 16-million-pixel limit. Transparent PNG is recommended. Logo opacity can be adjusted separately.

The live preview uses a sample background and the same composition code as the export. Select **Preview ayah** to inspect different ayahs, since text lengths vary. Overlap warnings help you spot elements placed on top of each other; intentional overlaps are allowed. Hide the Arabic text and translation if you want a recitation video without captions. Background dimming and caption panels are independent options.

**Save layout settings** downloads `layout.json` for reuse from the CLI. Each new export includes the same file and records the settings and logo hash in `sources.json`. The original logo image is not included in the output bundle. The player shows your last generated video until you generate again after changing settings.

## Command line

After installation, run from your activated virtual environment, or prefix these commands with its Python executable:

```bash
python -m quran_reels.cli --surah 112 --start 1 --end 4 \
  --background /path/to/your-video.mp4 --output output/ikhlas

python -m quran_reels.cli --surah 94 --start 5 --end 6 \
  --provider pexels --query "ocean waves" --output output/ease

python -m quran_reels.cli --surah 112 --start 1 --end 4 \
  --provider pixabay --query "forest" --translation none --output output/forest

python -m quran_reels.cli --surah 112 --start 1 --end 4 \
  --background /path/to/your-video.mp4 --layout /path/to/layout.json \
  --logo /path/to/logo.png --output output/my-channel
```

These examples use Bash line continuations. In PowerShell, put each command on one line. `--output` must identify a fresh folder; existing videos are not overwritten. Run `python -m quran_reels.cli --help` for formats and supported editions. Stock API keys come from environment variables or `.env`, not command-line arguments.

## Docker

Docker installs Python and FFmpeg for you:

```bash
docker build -t quran-reels-studio .
docker run --rm -p 127.0.0.1:8501:8501 quran-reels-studio
```

Open the local URL and enter your key in the interface. Download results before removing the container, or mount `/app/output` and `/app/.cache` to writable local directories for persistence.

## Output and privacy

Each successful run writes a new folder in `output/`:

| File | Contents |
| --- | --- |
| `video.mp4` | Finished video, with the original background sound removed |
| `sources.json` | Exact source text, editions, public audio URLs, ayah timing, background provenance, and hashes |
| `credits.txt` | Quran and stock source information to keep with your video |
| `layout.json` | Visibility, positions, sizes, logo opacity, watermark and background settings |

The app binds to localhost by default. Keys typed in the sidebar stay in that Streamlit session; `.env` keys stay on disk until you remove them. Stock search responses are cached in `.cache/stock` for 24 hours, in line with Pixabay's caching guidance. Downloads and intermediate files use a temporary directory. Output videos remain until you delete them. This is a local single-user tool: deploying it as an internet service requires authentication, quotas, storage controls, and a separate security review.

## Accuracy and limitations

- This version uses **AlQuran Cloud**, not the private project's Quran.Foundation credentials. The API's edition IDs, ayah numbers, and global ayah IDs must match before rendering; this is an integrity check, not scholarly certification.
- Captions display **one complete ayah at a time**. They do not highlight individual words or make claims about phrase-level acoustic alignment.
- Recitation is decoded and joined without changing its speed or cutting within an ayah. When the API prefixes an unnumbered opening basmala to another surah's ayah 1, the app separates that prefix from the numbered caption and retains both the raw text and opening in the manifest. Al-Fatiha 1:1 stays intact. Recordings are kept as supplied; listen for opening recitation according to the source edition.
- A background must cover the entire recording. Footage is center-cropped, never looped. Stock search checks the first 30 results; try a different search or upload your own longer clip if none is suitable.
- The app can render up to **three minutes**, with at most 12 ayahs per run. There is no guarantee every surah or long ayah fits a single caption. Unreadable layouts stop with an error instead of removing text.
- Nature search terms and provider safe-search are not visual content moderation. Review footage yourself.
- Provider access does not grant blanket reuse rights. Check the current terms for stock, recitation recordings, and translation editions before public distribution. MIT covers this application's code, not those external materials.
- External APIs can fail, change their catalogue, or impose rate limits. This app never substitutes another reciter on failure.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

Tests cover edition matching, malformed/incomplete responses, credential-safe errors, 24-hour stock caching, background selection, Arabic layout, and sample-based audio timing. CI runs them on Windows and Linux. [Validation notes](docs/VALIDATION.md) distinguish local live checks from mocked tests.

## Project background

This is an independent, simplified implementation informed by a private QuranReels automation project. No private keys, posting histories, page branding, downloaded footage, or private Quran caches are included. See [the analysis](docs/ANALYSIS.md) and [Arabic article draft](docs/article-ar.html).

Original application code: MIT. Bundled [Amiri](https://github.com/aliftype/amiri) font: SIL Open Font License; see `quran_reels/fonts/OFL.txt`.
