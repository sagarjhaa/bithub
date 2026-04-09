"""Paths and configuration for bitnet-hub."""

import os
from pathlib import Path

# Default home directory: ~/.bitnet-hub
BITNET_HUB_HOME = Path(os.environ.get("BITNET_HUB_HOME", Path.home() / ".bitnet-hub"))
MODELS_DIR = BITNET_HUB_HOME / "models"
BITNET_CPP_DIR = BITNET_HUB_HOME / "bitnet.cpp"
DB_PATH = BITNET_HUB_HOME / "models.json"

# Server defaults
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080

def ensure_dirs():
    """Create required directories if they don't exist."""
    BITNET_HUB_HOME.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
