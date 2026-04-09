"""Model registry — loads and queries the curated model catalog."""

import json
from pathlib import Path
from typing import Optional

from bithub.config import BITHUB_HOME

REGISTRY_PATH = Path(__file__).parent / "registry.json"
CUSTOM_MODELS_PATH = BITHUB_HOME / "custom_models.json"


def load_registry() -> dict:
    """Load the model registry from disk. Raises on missing/invalid file."""
    with open(REGISTRY_PATH) as f:
        data = json.load(f)
    if "models" not in data:
        raise ValueError(f"Registry {REGISTRY_PATH} missing 'models' key")
    return data


def get_model_info(model_name: str) -> Optional[dict]:
    """Return info dict for a model, checking registry then custom models."""
    registry = load_registry()
    info = registry["models"].get(model_name)
    if info:
        return info
    custom = load_custom_models()
    return custom.get(model_name)


def load_custom_models() -> dict:
    """Load user's custom (directly-pulled) models."""
    if not CUSTOM_MODELS_PATH.exists():
        return {}
    try:
        with open(CUSTOM_MODELS_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_custom_model(name: str, info: dict) -> None:
    """Save a custom model entry to custom_models.json."""
    models = load_custom_models()
    models[name] = info
    BITHUB_HOME.mkdir(parents=True, exist_ok=True)
    with open(CUSTOM_MODELS_PATH, "w") as f:
        json.dump(models, f, indent=2)


def list_available_models() -> dict:
    """Return all models from the registry."""
    registry = load_registry()
    return registry["models"]
