from pathlib import Path

from streamlit.testing.v1 import AppTest

from quran_reels import sources
from quran_reels.sources import Passage, Verse


def test_ui_loads_reviews_passage_and_invalidates_changed_selection(monkeypatch):
    catalogue = [{"number": i, "numberOfAyahs": 4, "englishName": f"Surah {i}", "name": "سورة"} for i in range(1, 115)]
    monkeypatch.setattr(sources, "surahs", lambda: catalogue)
    monkeypatch.setattr(sources, "fetch_passage", lambda *args: Passage(112, "Al-Ikhlaas", "ar.alafasy", "en.sahih", (Verse("112:1", "قُلْ هُوَ ٱللَّهُ أَحَدٌ", "Say, He is Allah, One.", "https://example.org/audio.mp3"),)))
    # This test exercises UI state without requiring local FFmpeg on CI.
    from quran_reels import renderer
    monkeypatch.setattr(renderer, "check_dependencies", lambda: None)
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py")).run()
    assert not app.exception
    assert app.button[1].disabled
    app.button[0].click().run()
    assert not app.exception
    next(c for c in app.checkbox if c.label.startswith("I have reviewed")).check().run()
    assert not app.button[1].disabled
    app.selectbox[1].select("Mahmoud Khalil Al-Husary").run()
    assert not app.exception
    assert app.button[1].disabled
    assert not next(c for c in app.checkbox if c.label.startswith("I have reviewed")).value


def test_design_controls_reach_export_and_preview(monkeypatch, tmp_path):
    from quran_reels import renderer
    monkeypatch.setattr(renderer, "check_dependencies", lambda: None)
    monkeypatch.setattr(sources, "surahs", lambda: [{"number": i, "numberOfAyahs": 4, "englishName": f"Surah {i}", "name": "سورة"} for i in range(1, 115)])
    monkeypatch.setattr(sources, "fetch_passage", lambda *a: Passage(112, "Al-Ikhlaas", "ar.alafasy", "en.sahih", (Verse("112:1", "قُلْ هُوَ ٱللَّهُ أَحَدٌ", "Say, He is Allah, One.", "https://example.org/audio.mp3"),)))
    captured = {}
    def export(passage, output, **kwargs):
        captured.update(kwargs)
        for name in ["video.mp4", "credits.txt", "sources.json", "layout.json"]:
            (tmp_path / name).write_bytes(b"test export")
        return tmp_path / "video.mp4"
    monkeypatch.setattr(renderer, "generate", export)
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py")).run()
    app.button[0].click().run()
    app.checkbox("design-surah-visible").uncheck().run()
    app.checkbox("design-watermark-visible").uncheck().run()
    app.slider("design-arabic-y").set_value(35).run()
    next(t for t in app.text_input if t.label == "Pexels API key").set_value("test-key").run()
    next(c for c in app.checkbox if c.label.startswith("I have reviewed")).check().run()
    app.button[1].click().run()
    assert not app.exception
    assert not captured["style"].surah.visible
    assert not captured["style"].watermark.visible
    assert captured["style"].arabic.y == 35
