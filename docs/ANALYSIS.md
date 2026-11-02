# Analysis of the private QuranReels project

Inspected locally on 2026-11-02. The source folder is a working production automation system rather than a distributable public application.

## Reusable ideas

The original `auto_pipeline.py` obtains Quran.Foundation Arabic and translations, recitation files, and stock backgrounds. It isolates reciter audio caches, measures audio duration, and records provenance. `reel_generator.py` wraps text using real font measurements and renders vertical videos through FFmpeg. `quran_typography.py` emphasizes complete Quranic diacritics and Arabic shaping.

The surrounding system goes much further: editorial planning, reciter rotation, recitation evidence, caption policies, Facebook publishing, TikTok handoff, educational formats, illustrated stock, and durable queues. Its README describes production scheduling and specific branding. Those features solve the owner's publishing operation, but would complicate the requested simple public generator.

## Why a separate repository

The original tree includes `.env`, social-token files, publishing history, private editorial data, output videos, caches, downloaded assets, and local runtime paths. Publishing that tree would expose unrelated data and make installation difficult. Its fonts also need individual redistribution checks.

The public tool therefore uses newly written modules and an openly licensed bundled Amiri font. It does not import the private project, copy its `.env`, alter its tasks or queues, or include its media. Its only optional credentials are one stock provider's API key. AlQuran Cloud supplies text and audio without Quran.Foundation OAuth setup.

## Public implementation

| Private concern | Public implementation |
| --- | --- |
| Automated approved content rotation | User chooses exact surah and consecutive ayahs |
| Quran.Foundation OAuth and extended reciter sources | Explicit AlQuran Cloud text/audio editions |
| Brand-specific rendering | Neutral Arabic/translation video layout |
| Phrase recognition and editorial evidence | Complete-ayah captions with sample-based boundaries |
| Scheduled Facebook/TikTok publishing | Local preview and download |
| Large source caches and media libraries | Temporary downloads, 24-hour stock-search cache |
| Owner-specific production environment | Python package, Windows launcher, Dockerfile, tests |

The public implementation checks edition identity and matching ayah IDs; it does not claim the original system's phrase recognition, scholarly verification, person detection, or platform-specific publishing validation. The maximum three-minute export is a tool limit rather than a promise about any social platform's current rules.

## Publication package

The repository includes installation instructions, Arabic documentation, MIT code licensing, font license, automated checks, source manifests, and an Arabic article draft for techmouad.com. Existing social publishing automation is outside this project's scope.
