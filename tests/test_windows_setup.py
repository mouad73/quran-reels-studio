import hashlib
import io
import subprocess
import tarfile
import zipfile
from types import SimpleNamespace

import pytest
import zstandard

from quran_reels import setup_windows


def package():
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w") as tar:
        for name, data in {"Library/bin/fribidi-0.dll": b"test-dll", "info/licenses/COPYING": b"test-license", "../../unwanted.txt": b"must-not-extract"}.items():
            member = tarfile.TarInfo(name)
            member.size = len(data)
            tar.addfile(member, io.BytesIO(data))
    result = io.BytesIO()
    with zipfile.ZipFile(result, "w") as zip:
        zip.writestr("pkg-test.tar.zst", zstandard.ZstdCompressor().compress(archive.getvalue()))
    return result.getvalue()


@pytest.mark.parametrize("tampered", [False, True])
def test_windows_setup_verifies_package_and_extracts_only_runtime_and_license(monkeypatch, tmp_path, tampered):
    data = package()
    scripts = tmp_path / "Scripts"
    scripts.mkdir()
    monkeypatch.setattr(setup_windows.sys, "platform", "win32")
    monkeypatch.setattr(setup_windows.sys, "prefix", str(tmp_path))
    monkeypatch.setattr(setup_windows.sys, "base_prefix", str(tmp_path / "base"))
    monkeypatch.setattr(setup_windows.sys, "executable", str(scripts / "python.exe"))
    monkeypatch.setattr(setup_windows.platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(setup_windows, "SHA256", hashlib.sha256(data).hexdigest())
    monkeypatch.setattr(setup_windows.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(data + b"changed" if tampered else data))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0))
    if tampered:
        with pytest.raises(SystemExit, match="checksum mismatch"):
            setup_windows.install(force=True)
        assert not (scripts / "fribidi.dll").exists()
    else:
        setup_windows.install(force=True)
        assert (scripts / "fribidi.dll").read_bytes() == b"test-dll"
        assert (tmp_path / "fribidi-license" / "COPYING").read_bytes() == b"test-license"
        assert not (tmp_path.parent / "unwanted.txt").exists()
