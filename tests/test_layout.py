import io
from dataclasses import replace

import pytest
from PIL import Image

from quran_reels.layout import LogoStyle, VideoStyle, compose_overlay, load_logo, overlap_warnings, position
from quran_reels.sources import Passage, UserError, Verse


def passage():
    return Passage(112, "Al-Ikhlaas", "ar.alafasy", "en.sahih", (Verse("112:1", "قُلْ هُوَ ٱللَّهُ أَحَدٌ", "Say, He is Allah, One.", "https://example.org/1.mp3"),))


def hidden_style():
    style = VideoStyle(dim=0, panels=False)
    return replace(style, **{name: replace(getattr(style, name), visible=False) for name in ["arabic", "translation", "surah", "reference", "reciter", "watermark"]})


def test_all_overlays_can_be_removed():
    p = passage()
    overlay, boxes = compose_overlay(p, p.verses[0], (720, 1280), hidden_style())
    assert boxes == {}
    assert overlay.getchannel("A").getbbox() is None


def test_every_text_element_can_be_placed_independently_and_hidden():
    p = passage()
    defaults = VideoStyle()
    for name in ["arabic", "translation", "surah", "reference", "reciter", "watermark"]:
        style = replace(hidden_style(), **{name: replace(getattr(defaults, name), visible=True, x=100, y=100)})
        _, boxes = compose_overlay(p, p.verses[0], (720, 1280), style)
        assert list(boxes) == [name]
        assert boxes[name][2:] == (720, 1280)


def test_logo_keeps_transparency_aspect_ratio_opacity_and_position():
    p = passage()
    logo = Image.new("RGBA", (100, 50), (255, 0, 0, 128))
    style = replace(hidden_style(), logo=LogoStyle(True, 100, 0, 20, 50))
    overlay, boxes = compose_overlay(p, p.verses[0], (720, 1280), style, logo)
    assert boxes["logo"] == (576, 0, 720, 72)
    assert overlay.getpixel((600, 30)) == (255, 0, 0, 64)
    assert overlay.getpixel((500, 30))[3] == 0


def test_logo_upload_is_decoded_by_content_and_rejects_non_images():
    with pytest.raises(UserError):
        load_logo(b"not an image")
    data = io.BytesIO()
    Image.new("RGBA", (30, 20), (0, 100, 20, 0)).save(data, format="PNG")
    image = load_logo(data.getvalue())
    assert image.mode == "RGBA" and image.getpixel((0, 0))[3] == 0


def test_missing_enabled_logo_is_an_actionable_error():
    p = passage()
    with pytest.raises(UserError, match="Upload a logo"):
        compose_overlay(p, p.verses[0], (720, 1280), replace(hidden_style(), logo=LogoStyle(visible=True)))


@pytest.mark.parametrize("data", [{"unexpected": True}, {"dim": -1}, {"arabic": {"x": float("nan")}}, {"surah": {"visible": "false"}}, {"logo": {"opacity": 110}}])
def test_invalid_saved_layout_is_rejected(data):
    with pytest.raises(UserError):
        VideoStyle.from_dict(data)


def test_layout_round_trips_without_private_file_paths():
    style = replace(VideoStyle(), logo=LogoStyle(True, 80, 5, 15, 60), watermark_text="My channel")
    assert VideoStyle.from_dict(style.to_dict()) == style
    assert "path" not in str(style.to_dict())


def test_overlaps_are_reported_and_positions_never_crop_edges():
    assert overlap_warnings({"arabic": (0, 0, 50, 50), "translation": (40, 40, 80, 80)})
    assert not overlap_warnings({"arabic": (0, 0, 50, 50), "translation": (50, 50, 80, 80)})
    assert position((720, 1280), (100, 50), 0, 0) == (0, 0)
    assert position((720, 1280), (100, 50), 100, 100) == (620, 1230)
