import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .renderer import SIZES, generate
from .layout import VideoStyle, LogoStyle
from .sources import RECITERS, TRANSLATIONS, UserError, fetch_passage


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    load_dotenv()
    parser = argparse.ArgumentParser(description="Generate a Quran video locally. Keys are read from .env or the environment.")
    parser.add_argument("--surah", type=int, default=112)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=4)
    parser.add_argument("--reciter", choices=list(RECITERS.values()), default="ar.alafasy")
    parser.add_argument("--translation", choices=[v for v in TRANSLATIONS.values() if v] + ["none"], default="en.sahih")
    parser.add_argument("--provider", choices=["pexels", "pixabay"], default="pexels")
    parser.add_argument("--query", default="mountains nature")
    parser.add_argument("--background", type=Path, help="Use local footage; no stock API key needed.")
    parser.add_argument("--format", choices=list(SIZES), default="Portrait 720p")
    parser.add_argument("--output", type=Path, required=True, help="A fresh output directory.")
    parser.add_argument("--layout", type=Path, help="A layout.json exported by the app.")
    parser.add_argument("--logo", type=Path, help="Your PNG, JPEG or WebP logo.")
    args = parser.parse_args()
    try:
        style = VideoStyle()
        if args.layout:
            try:
                style = VideoStyle.from_dict(json.loads(args.layout.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                raise UserError("Could not read the layout JSON file.") from None
        elif args.logo:
            from dataclasses import replace
            style = replace(style, logo=LogoStyle(visible=True))
        passage = fetch_passage(args.surah, args.start, args.end, args.reciter, None if args.translation == "none" else args.translation)
        result = generate(passage, args.output, size=SIZES[args.format], provider=args.provider, key=os.getenv(f"{args.provider.upper()}_API_KEY", ""), query=args.query, local_video=args.background, style=style, logo_path=args.logo, progress=print)
        print(f"Saved: {result}\nReview video.mp4, sources.json and credits.txt before publishing.")
    except UserError as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
