"""Paths and configuration for bithub."""

import os
import platform
from pathlib import Path

# Default home directory: ~/.bithub
BITHUB_HOME = Path(os.environ.get("BITHUB_HOME", Path.home() / ".bithub"))
MODELS_DIR = BITHUB_HOME / "models"
BITNET_CPP_DIR = BITHUB_HOME / "bitnet.cpp"
DB_PATH = BITHUB_HOME / "models.json"

# Server defaults
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080


def get_default_threads() -> int:
    """Auto-detect a sensible default thread count based on CPU cores.

    Uses half the available cores (leaving room for the OS and other work),
    with a minimum of 2 and a max of 8 for safety.
    """
    try:
        cores = os.cpu_count() or 4
        threads = max(2, min(cores // 2, 8))
        return threads
    except Exception:
        return 2


def get_system_info() -> dict:
    """Gather system info for diagnostics."""
    return {
        "os": platform.system(),
        "arch": platform.machine(),
        "python": platform.python_version(),
        "cpu_cores": os.cpu_count() or "unknown",
        "home": str(BITHUB_HOME),
    }


def ensure_dirs():
    """Create required directories if they don't exist."""
    BITHUB_HOME.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
