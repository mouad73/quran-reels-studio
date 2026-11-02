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
    app.checkbox[0].check().run()
    assert not app.button[1].disabled
    app.selectbox[1].select("Mahmoud Khalil Al-Husary").run()
    assert not app.exception
    assert app.button[1].disabled
    assert not app.checkbox[0].value
