import json
from pathlib import Path

import pytest

from quran_reels import sources
from quran_reels.sources import UserError, fetch_passage, stock_candidates


def payload():
    return {"data": [{"number": 112, "numberOfAyahs": 4, "englishName": "Al-Ikhlaas", "edition": {"identifier": edition}, "ayahs": [{"number": 6221 + n, "numberInSurah": n, "text": "قُلْ هُوَ ٱللَّهُ أَحَدٌ" if edition == "quran-uthmani" else "Say, He is Allah, One.", "audio": f"https://example.org/{n}.mp3"} for n in range(1, 5)]} for edition in ["quran-uthmani", "ar.alafasy", "en.sahih"]]}


def test_passage_joins_editions_by_ayah_not_list_order(monkeypatch):
    response = payload()
    response["data"][1]["ayahs"].reverse()
    monkeypatch.setattr(sources, "get_json", lambda *a, **k: response)
    passage = fetch_passage(112, 2, 3)
    assert [v.reference for v in passage.verses] == ["112:2", "112:3"]
    assert passage.verses[0].audio_url.endswith("2.mp3")


def test_prefixed_opening_is_separate_from_numbered_ayah(monkeypatch):
    response = payload()
    ayah = response["data"][0]["ayahs"][0]["text"]
    response["data"][0]["ayahs"][0]["text"] = sources.BASMALA + " " + ayah
    monkeypatch.setattr(sources, "get_json", lambda *a, **k: response)
    verse = fetch_passage(112, 1, 1).verses[0]
    assert verse.arabic == ayah
    assert verse.opening_basmala == sources.BASMALA
    assert verse.source_arabic == sources.BASMALA + " " + ayah


def test_fatiha_numbered_basmala_is_preserved(monkeypatch):
    response = payload()
    for item in response["data"]:
        item["number"] = 1
    response["data"][0]["ayahs"][0]["text"] = sources.BASMALA
    monkeypatch.setattr(sources, "get_json", lambda *a, **k: response)
    verse = fetch_passage(1, 1, 1).verses[0]
    assert verse.arabic == sources.BASMALA
    assert verse.opening_basmala == ""


@pytest.mark.parametrize("change", ["missing", "mismatched", "wrong_surah", "missing_translation", "bad_audio"])
def test_rejects_incomplete_or_mismatched_source(monkeypatch, change):
    response = payload()
    if change == "missing":
        response["data"][1]["ayahs"].pop(0)
    elif change == "mismatched":
        response["data"][1]["ayahs"][0]["number"] += 1
    elif change == "wrong_surah":
        response["data"][0]["number"] = 113
    elif change == "missing_translation":
        response["data"][2]["ayahs"][0]["text"] = ""
    else:
        response["data"][1]["ayahs"][0]["audio"] = "http://example.org/audio.mp3"
    monkeypatch.setattr(sources, "get_json", lambda *a, **k: response)
    with pytest.raises(UserError):
        fetch_passage(112, 1, 4)


@pytest.mark.parametrize("args", [(0, 1, 1), (115, 1, 1), (112, 4, 1), (2, 1, 13), (112, 0, 1)])
def test_rejects_invalid_selection_before_api(args, monkeypatch):
    monkeypatch.setattr(sources, "get_json", lambda *a, **k: pytest.fail("API must not be called"))
    with pytest.raises(UserError):
        fetch_passage(*args)


def test_pexels_new_endpoint_and_long_enough_selection(monkeypatch, tmp_path):
    calls = []
    def request(url, **kwargs):
        calls.append((url, kwargs))
        return {"videos": [{"id": i, "duration": length, "url": f"https://pexels.com/video/{i}", "user": {"name": "Creator"}, "video_files": [{"width": 720, "height": 1280, "file_type": "video/mp4", "link": f"https://videos.pexels.com/{i}.mp4"}]} for i, length in [(1, 5), (2, 30)]]}
    monkeypatch.setattr(sources, "get_json", request)
    results = stock_candidates("pexels", "secret-key", "mountains", 15, 720, 1280, tmp_path)
    assert len(results) == 1 and results[0]["id"] == 2
    assert calls[0][0] == "https://api.pexels.com/v1/videos/search"
    assert calls[0][1]["headers"] == {"Authorization": "secret-key"}
    assert "secret-key" not in next(tmp_path.iterdir()).read_text()
    stock_candidates("pexels", "secret-key", "mountains", 15, 720, 1280, tmp_path)
    assert len(calls) == 1


def test_pixabay_cache_and_attribution(monkeypatch, tmp_path):
    monkeypatch.setattr(sources, "get_json", lambda *a, **k: {"hits": [{"id": 42, "duration": 60, "pageURL": "https://pixabay.com/videos/id-42/", "user": "Artist", "videos": {"medium": {"width": 1920, "height": 1080, "url": "https://cdn.pixabay.com/video.mp4"}}}]})
    item = stock_candidates("pixabay", "private-value", "ocean", 10, 720, 1280, tmp_path)[0]
    assert item["creator"] == "Artist" and item["provider"] == "pixabay"
    assert "private-value" not in next(tmp_path.iterdir()).read_text()


def test_http_error_never_exposes_key(monkeypatch):
    def failure(*a, **k):
        raise sources.requests.RequestException("https://example.com/?key=private-value")
    monkeypatch.setattr(sources.requests, "get", failure)
    with pytest.raises(UserError) as error:
        sources.get_json("https://example.com", params={"key": "private-value"})
    assert "private-value" not in str(error.value)
