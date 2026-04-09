"""Paths and configuration for bithub."""

import copy
import logging
import os
import platform
import sys
from pathlib import Path

# Default home directory: ~/.bithub
BITHUB_HOME = Path(os.environ.get("BITHUB_HOME", Path.home() / ".bithub"))
MODELS_DIR = BITHUB_HOME / "models"
BITNET_CPP_DIR = BITHUB_HOME / "bitnet.cpp"
DB_PATH = BITHUB_HOME / "models.json"
LOG_PATH = BITHUB_HOME / "bithub.log"
BENCHMARKS_DIR = BITHUB_HOME / "benchmarks"

# Pre-built binaries installed by Docker/Homebrew/install script
PREBUILT_DIR = Path(os.environ.get("BITHUB_PREBUILT_DIR", BITHUB_HOME / "prebuilt"))

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


def ensure_dirs() -> None:
    """Create required directories if they don't exist."""
    BITHUB_HOME.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)


if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore[assignment]

_DEFAULT_CONFIG: dict = {
    "server": {
        "port": DEFAULT_PORT,
        "host": DEFAULT_HOST,
        "threads": get_default_threads(),
    },
    "models": {
        "default": None,
        "directory": str(MODELS_DIR),
    },
    "download": {
        "check_disk_space": True,
        "min_free_gb": 5,
    },
}


def load_config() -> dict:
    """Load config from ~/.bithub/config.toml, merged over defaults.

    Returns defaults if file missing, unreadable, or tomli not installed.
    """
    config = copy.deepcopy(_DEFAULT_CONFIG)
    config_path = BITHUB_HOME / "config.toml"
    if not config_path.exists():
        return config
    if tomllib is None:
        logging.warning("Install 'tomli' for config file support on Python <3.11")
        return config
    try:
        with open(config_path, "rb") as f:
            user_config = tomllib.load(f)
        for section, values in user_config.items():
            if section in config and isinstance(values, dict):
                config[section].update(values)
    except Exception:
        logging.warning("Failed to parse %s, using defaults", config_path)
    return config
