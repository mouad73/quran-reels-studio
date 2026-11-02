import wave

import pytest
from PIL import Image, ImageFont

from quran_reels import renderer
from quran_reels.renderer import FONT, caption_image, prepare_audio, wrap
from quran_reels.sources import Passage, Verse, UserError


def passage(text="قُلْ هُوَ ٱللَّهُ أَحَدٌ", translation="Say, He is Allah, One."):
    return Passage(112, "Al-Ikhlaas", "ar.alafasy", "en.sahih", (Verse("112:1", text, translation, "https://example.org/1.mp3"),))


def test_wrap_preserves_every_word():
    text = "قُلْ هُوَ ٱللَّهُ أَحَدٌ ٱللَّهُ ٱلصَّمَدُ"
    lines = wrap(text, ImageFont.truetype(str(FONT), 60), 240, "rtl")
    assert " ".join(lines) == text
    assert len(lines) > 1


@pytest.mark.parametrize("size", renderer.SIZES.values())
def test_caption_is_shaped_rgba_at_requested_dimensions(tmp_path, size):
    dest = tmp_path / "caption.png"
    p = passage()
    caption_image(p, p.verses[0], size, dest)
    with Image.open(dest) as image:
        assert image.mode == "RGBA" and image.size == size
        assert image.getpixel((0, 0))[3] > 0


def test_oversized_ayah_is_rejected_instead_of_truncated(tmp_path):
    p = passage("ٱللَّهُ " * 1500)
    with pytest.raises(UserError, match="too long"):
        caption_image(p, p.verses[0], (720, 1280), tmp_path / "caption.png")


def test_timing_comes_from_decoded_sample_counts(monkeypatch, tmp_path):
    p = Passage(112, "Al-Ikhlaas", "ar.alafasy", None, (Verse("112:1", "أحد", "", "https://example.org/1.mp3"), Verse("112:2", "الصمد", "", "https://example.org/2.mp3")))
    monkeypatch.setattr(renderer, "download", lambda url, path: path.write_bytes(b"original audio"))
    lengths = iter([48001, 96002])
    def decode(command, **kwargs):
        with wave.open(command[-1], "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(48000)
            stream.writeframes(b"\0\0" * next(lengths))
    monkeypatch.setattr(renderer, "run", decode)
    audio, cues, duration = prepare_audio(p, tmp_path)
    assert cues[0]["end"] == cues[1]["start"] == 48001 / 48000
    assert cues[-1]["end"] == duration == 144003 / 48000
    with wave.open(str(audio), "rb") as stream:
        assert stream.getnframes() == 144003
