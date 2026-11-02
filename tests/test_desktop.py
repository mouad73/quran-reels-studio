import hashlib
import io
import zipfile

import pytest

from quran_reels import desktop


def engine_archive():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("release/bin/ffmpeg.exe", b"fake-encoder")
        archive.writestr("release/bin/ffprobe.exe", b"fake-probe")
        archive.writestr("release/LICENSE", b"license")
        archive.writestr("../../escape.txt", b"never extracted")
    return stream.getvalue()


def test_engine_is_verified_before_install_and_cached_for_offline_launch(monkeypatch, tmp_path):
    data = engine_archive()
    metadata = {"version": "test", "sha256": hashlib.sha256(data).hexdigest(), "url": "https://example.test/release.zip"}
    monkeypatch.setattr(desktop.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(data))
    bin_path = desktop.install_engine(tmp_path, metadata)
    assert (bin_path / "ffmpeg.exe").read_bytes() == b"fake-encoder"
    assert not (tmp_path.parent / "escape.txt").exists()
    monkeypatch.setattr(desktop.urllib.request, "urlopen", lambda *a, **k: pytest.fail("Cached setup must not use the network"))
    assert desktop.install_engine(tmp_path, metadata) == bin_path
    (bin_path / "ffmpeg.exe").write_bytes(b"tampered")
    assert not desktop.valid_engine(bin_path.parent, metadata)


def test_engine_checksum_failure_never_installs_or_executes(monkeypatch, tmp_path):
    monkeypatch.setattr(desktop.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(engine_archive()))
    with pytest.raises(RuntimeError, match="checksum"):
        desktop.install_engine(tmp_path, {"version": "bad", "url": "https://example.test/archive", "sha256": "0" * 64})
    assert not (tmp_path / "runtime" / "ffmpeg-bad").exists()


def test_data_location_is_explicit_and_independent_of_working_directory(monkeypatch, tmp_path):
    monkeypatch.setenv("QRS_DATA_DIR", str(tmp_path / "بيانات المستخدم"))
    assert desktop.data_directory() == tmp_path / "بيانات المستخدم"
    monkeypatch.delenv("QRS_DATA_DIR")
    assert desktop.data_directory() == desktop.Path(desktop.__file__).resolve().parent.parent
