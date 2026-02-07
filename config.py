"""
Auto Portable Python Deployer - Configuration
"""
import shutil
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.resolve()

# Environment paths
PYTHON_EMBEDDED_DIR = BASE_DIR / "python_embedded"


def _resolve_python_path() -> Path:
    """Find the best available Python executable.

    Priority: embedded Python > system Python
    """
    embedded = PYTHON_EMBEDDED_DIR / "python.exe"
    if embedded.exists():
        return embedded

    system_python = shutil.which("python")
    if system_python:
        return Path(system_python)

    return embedded


PYTHON_PATH = _resolve_python_path()
USE_EMBEDDED = (PYTHON_EMBEDDED_DIR / "python.exe").exists()

# UI Settings
WINDOW_TITLE = "Auto Portable Python Deployer"
WINDOW_SIZE = "950x750"
APP_VERSION = "1.0.0"
