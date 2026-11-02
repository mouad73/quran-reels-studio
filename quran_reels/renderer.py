"""Sample-counted ayah timing and complete, shaped Arabic captions."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import wave
from datetime import datetime, timezone
from pathlib import Path

from PIL import features

from .sources import API, Passage, UserError, download, stock_candidates
from .layout import FONT, VideoStyle, compose_overlay, load_logo, wrap

SIZES = {"Portrait 720p": (720, 1280), "Portrait 1080p": (1080, 1920), "Square 720p": (720, 720), "Landscape 720p": (1280, 720)}


def run(command, timeout=900):
    try:
        return subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except FileNotFoundError:
        raise UserError("Install FFmpeg and ffprobe, then restart the app. See README.md.") from None
    except subprocess.TimeoutExpired:
        raise UserError("The media operation timed out. Try a shorter passage or 720p.") from None
    except subprocess.CalledProcessError:
        raise UserError("FFmpeg could not process this media. Check the input video and available disk space.") from None


def check_dependencies():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise UserError("FFmpeg and ffprobe must be available on PATH. See README.md.")
    if not features.check_feature("raqm"):
        raise UserError("Pillow needs RAQM/FriBiDi for correct Arabic shaping. On Windows run .venv\\Scripts\\python.exe -m quran_reels.setup_windows, then restart the app. See README.md for other platforms.")


def probe(path: Path):
    return json.loads(run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)]).stdout)


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def caption_image(passage: Passage, verse, size, destination: Path, style=None, logo=None):
    image, _ = compose_overlay(passage, verse, size, style, logo)
    image.save(destination)


def prepare_audio(passage: Passage, workspace: Path):
    cues, frames, offset = [], [], 0
    for index, verse in enumerate(passage.verses):
        mp3, wav = workspace / f"ayah-{index}.mp3", workspace / f"ayah-{index}.wav"
        download(verse.audio_url, mp3)
        run(["ffmpeg", "-y", "-v", "error", "-i", str(mp3), "-vn", "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
        with wave.open(str(wav), "rb") as audio:
            count = audio.getnframes()
            if count <= 0:
                raise UserError("The provider returned an empty ayah recording.")
            frames.append(audio.readframes(count))
        cues.append({"reference": verse.reference, "start": offset / 48000, "end": (offset + count) / 48000, "source_audio_sha256": sha256(mp3), "decoded_samples": count})
        offset += count
    combined = workspace / "recitation.wav"
    with wave.open(str(combined), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(48000)
        for frame in frames:
            audio.writeframes(frame)
    return combined, cues, offset / 48000


def generate(passage: Passage, output: Path, *, size=(720, 1280), provider="pexels", key="", query="mountains nature", local_video: Path | None = None, style: VideoStyle | None = None, logo_path: Path | None = None, cache_dir: Path | None = None, progress=lambda message: None):
    check_dependencies()
    style = style or VideoStyle()
    style.validate()
    logo = None
    if style.logo.visible:
        if not logo_path or not Path(logo_path).is_file():
            raise UserError("Upload a logo or turn off Show logo.")
        if Path(logo_path).stat().st_size > 10 * 1024 * 1024:
            raise UserError("The logo must be smaller than 10 MB.")
        logo = load_logo(Path(logo_path).read_bytes())
    # Validate every ayah's exact layout before downloading media.
    for verse in passage.verses:
        compose_overlay(passage, verse, size, style, logo)
    if not passage.verses or len(passage.verses) > 12 or size not in SIZES.values():
        raise UserError("Use 1–12 ayahs and a supported output size.")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output / "video.mp4").exists():
        raise UserError("This output folder already contains a video. Choose a new folder.")
    with tempfile.TemporaryDirectory(prefix="quran-reels-") as temporary:
        workspace = Path(temporary)
        progress("Downloading original recitation and measuring each complete ayah…")
        audio, cues, duration = prepare_audio(passage, workspace)
        if duration > 180:
            raise UserError("This passage exceeds the three-minute rendering limit. Select fewer complete ayahs.")
        progress("Preparing the background…")
        if local_video:
            background = Path(local_video).resolve()
            if not background.is_file():
                raise UserError("The background video does not exist.")
            source = {"provider": "local", "file_name": background.name}
        else:
            candidates = stock_candidates(provider, key, query, duration, *size, cache_dir or Path.cwd() / ".cache" / "stock")
            if not candidates:
                raise UserError("No clip long enough for the complete recitation was found. Try another search or upload a longer video.")
            source = candidates[0].copy()
            background = workspace / "background.mp4"
            download(source.pop("download_url"), background)
        media = probe(background)
        if not any(s["codec_type"] == "video" for s in media["streams"]):
            raise UserError("The background file has no video stream.")
        if float(media["format"]["duration"]) < duration:
            raise UserError(f"The background must be at least {duration:.1f} seconds long. Recitation is never cut and footage is not looped.")
        source["sha256"] = sha256(background)
        progress("Typesetting Arabic and translation…")
        # One RGBA PNG per ayah. FFmpeg reads each once and repeats its last frame.
        command = ["ffmpeg", "-y", "-v", "error", "-threads", "2", "-i", str(background), "-i", str(audio)]
        for index, verse in enumerate(passage.verses):
            overlay = workspace / f"caption-{index}.png"
            caption_image(passage, verse, size, overlay, style, logo)
            command += ["-i", str(overlay)]
        width, height = size
        filters = [f"[0:v]setpts=PTS-STARTPTS,scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1,fps=30[v0]"]
        for index, cue in enumerate(cues):
            filters.append(f"[v{index}][{index + 2}:v]overlay=0:0:enable='gte(t,{cue['start']:.9f})*lt(t,{cue['end']:.9f})'[v{index + 1}]")
        temporary_video = workspace / "render.mp4"
        command += ["-filter_complex_threads", "1", "-filter_complex", ";".join(filters), "-map", f"[v{len(cues)}]", "-map", "1:a:0", "-t", f"{duration:.9f}", "-c:v", "libx264", "-threads", "2", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(temporary_video)]
        progress(f"Rendering {duration:.1f} seconds of video…")
        run(command)
        final = probe(temporary_video)
        video_stream = next(s for s in final["streams"] if s["codec_type"] == "video")
        if (video_stream["width"], video_stream["height"]) != size or abs(float(final["format"]["duration"]) - duration) > .15:
            raise UserError("The rendered video did not pass size or duration validation.")
        run(["ffmpeg", "-v", "error", "-i", str(temporary_video), "-f", "null", "-", "-xerror"])
        manifest = {"tool": "Quran Reels Studio 0.2.0", "created_at": datetime.now(timezone.utc).isoformat(), "quran_api": API, "arabic_edition": "quran-uthmani", "passage": passage.to_dict(), "cues": cues, "duration": duration, "size": list(size), "layout": style.to_dict(), "logo_sha256": sha256(logo_path) if logo is not None else None, "background": source, "video_sha256": sha256(temporary_video), "review": "Review Arabic, translation, recitation, background and usage rights before publishing. Timing is per ayah, not per word."}
        (output / "layout.json").write_text(json.dumps(style.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        (output / "sources.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        credits = f"Quran text and recitation: AlQuran Cloud ({API})\nArabic: quran-uthmani\nReciter edition: {passage.reciter}\nTranslation: {passage.translation_edition or 'none'}\nBackground: {source['provider']}\nCreator: {source.get('creator', 'your own footage')}\nSource: {source.get('source_url', source.get('file_name', ''))}\n\nCheck each provider's current terms and recording/translation permissions before public reuse.\n"
        (output / "credits.txt").write_text(credits, encoding="utf-8")
        shutil.copyfile(temporary_video, output / "video.mp4")
        progress("Video ready. Review the full export before sharing.")
    return output / "video.mp4"
