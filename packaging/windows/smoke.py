"""Exercise the extracted release with no Python or FFmpeg on PATH."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    python = bundle / "runtime" / "python.exe"
    with tempfile.TemporaryDirectory(prefix="quran-تجربة-", dir=bundle.parent, ignore_cleanup_errors=True) as temporary:
        data = Path(temporary)
        assert data.resolve().is_relative_to(bundle.parent.resolve())
        environment = {**os.environ, "PATH": os.path.join(os.environ["WINDIR"], "System32"), "QRS_DATA_DIR": str(data), "PYTHONPATH": "", "PYTHONHOME": ""}
        # Tests first-launch download, SHA validation, DLL loading, font shaping,
        # and real H.264/AAC encoding with the downloaded executables.
        subprocess.run([str(python), "-m", "quran_reels.desktop", "--self-test"], cwd=data, env=environment, check=True, timeout=480)
        result = json.loads((data / "self-test-result.json").read_text(encoding="utf-8"))
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        process = subprocess.Popen([str(python), "-m", "quran_reels.desktop", "--port", str(port)], cwd=data, env=environment)
        try:
            for _ in range(90):
                if process.poll() is not None:
                    raise RuntimeError((data / "launcher.log").read_text(encoding="utf-8")[-5000:])
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=1) as response:
                        if response.status == 200:
                            result["loopbackServer"] = True
                            break
                except OSError:
                    time.sleep(0.5)
            else:
                raise RuntimeError("Packaged Streamlit server did not become ready")
        finally:
            process.terminate()
            process.wait(timeout=15)
        result["minimalSystemPath"] = True
        result["unicodeDataPath"] = True
        result.pop("appRoot", None)
        result.pop("dataDirectory", None)
        (bundle.parent / "smoke-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result))


if __name__ == "__main__":
    main()
