# Validation record

Local checks performed on Windows on 2026-11-02. Python 3.13, Pillow 12.3.0 with RAQM, Streamlit 1.66.1. Provider credentials were supplied only at runtime and are not in this repository.

## Automated tests

`python -m pytest -q`: **39 passed** (including the v0.2 layout controls).

Coverage includes exact edition/ayah joins even with reordered source lists; rejection of missing text/audio, mismatched global ayah IDs, unsupported input ranges and wrong surahs; separation of the API's prefixed unnumbered basmala while preserving Al-Fatiha 1:1; credential-safe network errors; Pexels's current video endpoint; Pixabay attribution; 24-hour stock cache reuse; shaped caption layout in four formats; rejection of oversized captions; sample-counted ayah boundaries; and Streamlit passage loading/review invalidation when the reciter changes.

The tests also check that Windows runtime setup refuses a modified package and extracts only the expected DLL and license, ignoring unrelated archive paths. The tests mock external APIs and decoding. They do not validate the theological meaning of translations or listen to recordings.

## Live checks

- AlQuran Cloud: retrieved Surah 112, ayahs 1–4, Arabic `quran-uthmani`, translation `en.sahih`, and `ar.alafasy` audio; checked matching source identifiers.
- Also retrieved each configured reciter (`ar.alafasy`, `ar.abdurrahmaansudais`, `ar.husary`) with `fr.hamidullah` for 112:1. This confirms response availability, not full listening review of each library.
- Pexels: downloaded real footage and rendered Surah 112:1–4 at 720×1280, approximately 13.1 seconds. Regenerated after the basmala handling correction.
- Pixabay: queried the live API, downloaded footage and rendered 94:5–6 at 720×1280, approximately 8.5 seconds.
- Local footage: rendered 112:2 with `ar.husary` and French meaning at 720×720, approximately 5.0 seconds, into an Arabic-named folder. This caught and fixed Windows console encoding for output paths.
- Every successful render passes ffprobe dimensions/duration checks and a full FFmpeg decode. Video and source audio hashes are recorded with the export.
- The first clean Windows CI run exposed a missing FriBiDi runtime that was already present on the development machine. The Windows launcher now installs a fixed conda-forge 1.0.18 package inside the virtual environment after checking its SHA-256; it keeps the package license. Package discovery explicitly includes only `quran_reels`, so later local outputs cannot break reinstalls or enter a distribution.
- Inspected representative video frames for Arabic shaping, complete visible text, translation, and background composition. Browser check confirmed the local interface and loaded Quran/audio preview; the automated UI test covers the review control.

External media and generated outputs are deliberately excluded from Git. No Facebook/TikTok publishing was performed. Docker and macOS were not run locally; the Dockerfile is provided for reproducible setup and GitHub Actions exercises the automated tests on Windows and Linux.

## Custom-layout checks

The v0.2 checks cover independent visibility/placement of every text element, removal of all overlays, transparent logo resizing/opacity, invalid image rejection, saved-layout validation, overlap reporting and UI-to-export propagation. A live 720×1280 Pexels export with a sample transparent logo, hidden surah/reference labels and custom watermark was rendered and decoded. The preview uses the same overlay composition as the MP4 renderer.

## Limits of this evidence

These checks cover a few short passages and two stock providers. They do not establish that every ayah fits every layout, that all provider assets have suitable content, or that redistribution rights apply to every recording/translation. Per-word synchronization, automatic content moderation, multi-user hosting, GPU performance, and social-platform delivery are outside this version's scope.
