"""Paths and configuration for bitnet-hub."""

import os
import platform
from pathlib import Path

# Default home directory: ~/.bitnet-hub
BITNET_HUB_HOME = Path(os.environ.get("BITNET_HUB_HOME", Path.home() / ".bitnet-hub"))
MODELS_DIR = BITNET_HUB_HOME / "models"
BITNET_CPP_DIR = BITNET_HUB_HOME / "bitnet.cpp"
DB_PATH = BITNET_HUB_HOME / "models.json"

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
        "home": str(BITNET_HUB_HOME),
    }


def ensure_dirs():
    """Create required directories if they don't exist."""
    BITNET_HUB_HOME.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
