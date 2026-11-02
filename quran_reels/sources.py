"""Explicit Quran editions and stock providers; credentials never enter manifests."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests

API = "https://api.alquran.cloud/v1"
BASMALA = "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ"
RECITERS = {"Mishary Rashid Alafasy": "ar.alafasy", "Abdurrahmaan As-Sudais": "ar.abdurrahmaansudais", "Mahmoud Khalil Al-Husary": "ar.husary"}
TRANSLATIONS = {"English · Saheeh International": "en.sahih", "French · Muhammad Hamidullah": "fr.hamidullah", "No translation": None}


class UserError(RuntimeError):
    """An actionable error safe to show without raw request URLs or credentials."""


def get_json(url, *, params=None, headers=None):
    try:
        response = requests.get(url, params=params, headers=headers, timeout=(15, 60))
        if response.status_code in (401, 403):
            raise UserError("The provider refused access. Check your API key and account permissions.")
        if response.status_code == 429:
            raise UserError("The provider rate limit was reached. Please try again later.")
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        raise UserError("Could not retrieve provider data. Check your connection and try again.") from None


def download(url: str, destination: Path, limit=350 * 1024 * 1024):
    if urlparse(url).scheme != "https":
        raise UserError("The provider returned a media URL without HTTPS.")
    temporary = destination.with_suffix(destination.suffix + ".part")
    try:
        with requests.get(url, stream=True, timeout=(15, 90)) as response:
            response.raise_for_status()
            total = 0
            with temporary.open("wb") as target:
                for chunk in response.iter_content(1024 * 1024):
                    total += len(chunk)
                    if total > limit:
                        raise UserError("The media download exceeds the 350 MB per-file limit.")
                    target.write(chunk)
        temporary.replace(destination)
    except requests.RequestException:
        raise UserError("The media download failed. Please try again.") from None
    finally:
        temporary.unlink(missing_ok=True)


@dataclass(frozen=True)
class Verse:
    reference: str
    arabic: str
    translation: str
    audio_url: str
    source_arabic: str = ""
    opening_basmala: str = ""


@dataclass(frozen=True)
class Passage:
    surah: int
    name: str
    reciter: str
    translation_edition: str | None
    verses: tuple[Verse, ...]

    def to_dict(self):
        return asdict(self)


def surahs():
    payload = get_json(f"{API}/surah")
    if payload.get("code") != 200 or not isinstance(payload.get("data"), list):
        raise UserError("The Quran API returned an unexpected chapter catalogue.")
    return payload["data"]


def fetch_passage(surah: int, start: int, end: int, reciter="ar.alafasy", translation="en.sahih") -> Passage:
    if not 1 <= surah <= 114 or not 1 <= start <= end or end - start >= 12:
        raise UserError("Choose a surah from 1–114 and a consecutive range of 1–12 complete ayahs.")
    if reciter not in RECITERS.values() or translation not in TRANSLATIONS.values():
        raise UserError("Choose a supported reciter and translation edition.")
    editions = ["quran-uthmani", reciter] + ([translation] if translation else [])
    payload = get_json(f"{API}/surah/{surah}/editions/{','.join(editions)}")
    try:
        data = payload["data"]
        by_id = {item["edition"]["identifier"]: item for item in data}
        for identifier in editions:
            item = by_id[identifier]
            if item["number"] != surah or item["numberOfAyahs"] < end:
                raise ValueError
        maps = {identifier: {v["numberInSurah"]: v for v in by_id[identifier]["ayahs"]} for identifier in editions}
        verses = []
        for number in range(start, end + 1):
            records = [maps[e][number] for e in editions]
            if len({v["number"] for v in records}) != 1:
                raise ValueError
            raw_arabic = maps["quran-uthmani"][number]["text"].strip()
            arabic, opening = raw_arabic, ""
            # The API prefixes the unnumbered opening to many surahs' ayah 1.
            # Keep it in provenance; the numbered ayah caption starts after it.
            # Al-Fatiha 1:1 is itself the basmala and must remain intact.
            if surah != 1 and number == 1 and raw_arabic.startswith(BASMALA + " "):
                arabic = raw_arabic[len(BASMALA):].strip()
                opening = BASMALA
            translated = maps[translation][number]["text"].strip() if translation else ""
            audio = maps[reciter][number]["audio"]
            if not arabic or (translation and not translated) or not audio.startswith("https://"):
                raise ValueError
            verses.append(Verse(f"{surah}:{number}", arabic, translated, audio, raw_arabic, opening))
        return Passage(surah, by_id["quran-uthmani"]["englishName"], reciter, translation, tuple(verses))
    except (KeyError, TypeError, ValueError, AttributeError):
        raise UserError("The Quran source did not supply a complete matching passage. Check the verse range; no content was substituted.") from None


def stock_candidates(provider: str, key: str, query: str, duration: float, width: int, height: int, cache_dir: Path):
    if provider not in {"pexels", "pixabay"}:
        raise UserError("Choose Pexels, Pixabay, or your own background video.")
    if not key.strip():
        raise UserError(f"Add your {provider.title()} API key or choose a local video.")
    if not query.strip() or len(query) > 100:
        raise UserError("Use a background search of 1–100 characters.")
    # Provider search results are cached for 24 hours. Only a hash of the key is used.
    cache_dir.mkdir(parents=True, exist_ok=True)
    identity = hashlib.sha256(f"{provider}:{key}:{query}".encode()).hexdigest()
    cache = cache_dir / f"{identity}.json"
    if cache.exists() and time.time() - cache.stat().st_mtime < 86400:
        payload = json.loads(cache.read_text(encoding="utf-8"))
    else:
        if provider == "pexels":
            payload = get_json("https://api.pexels.com/v1/videos/search", params={"query": query, "per_page": 30}, headers={"Authorization": key.strip()})
        else:
            payload = get_json("https://pixabay.com/api/videos/", params={"key": key.strip(), "q": query, "per_page": 30, "safesearch": "true"})
        # Save only response data, never the authenticated request URL.
        cache.write_text(json.dumps(payload), encoding="utf-8")
    candidates = []
    for video in payload.get("videos" if provider == "pexels" else "hits", []):
        if float(video.get("duration", 0)) < duration + 0.25:
            continue
        files = video.get("video_files", []) if provider == "pexels" else list(video.get("videos", {}).values())
        for media in files:
            mw, mh = media.get("width", 0), media.get("height", 0)
            link = media.get("link") or media.get("url", "")
            if not mw or not mh or not link.startswith("https://"):
                continue
            if provider == "pexels" and media.get("file_type") != "video/mp4":
                continue
            # Prefer sufficient resolution and a close aspect ratio, then smaller files.
            scale = max(width / mw, height / mh)
            score = abs(mw / mh - width / height) + max(0, scale - 1) * 4 + mw * mh / 1e8
            candidates.append((score, {"provider": provider, "id": video["id"], "creator": video.get("user", {}).get("name", "") if provider == "pexels" else video.get("user", ""), "source_url": video.get("url") if provider == "pexels" else video.get("pageURL"), "download_url": link}))
    return [c for _, c in sorted(candidates, key=lambda entry: entry[0])]
