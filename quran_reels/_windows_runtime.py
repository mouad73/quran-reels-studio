"""Load the venv-local FriBiDi library before Pillow initializes RAQM."""
import sys
from pathlib import Path

_FRIBIDI = None


def preload_fribidi():
    global _FRIBIDI
    if sys.platform != "win32" or _FRIBIDI is not None:
        return
    dll = Path(sys.prefix) / "Scripts" / "fribidi.dll"
    if dll.is_file():
        import ctypes
        try:
            _FRIBIDI = ctypes.WinDLL(str(dll))
        except OSError:
            # check_dependencies gives the user an actionable setup message.
            pass
