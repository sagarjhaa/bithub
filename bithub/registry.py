"""Model registry — loads and queries the curated model catalog."""

import json
from pathlib import Path
from typing import Optional

REGISTRY_PATH = Path(__file__).parent / "registry.json"


def load_registry() -> dict:
    """Load the model registry from disk. Raises on missing/invalid file."""
    with open(REGISTRY_PATH) as f:
        data = json.load(f)
    if "models" not in data:
        raise ValueError(f"Registry {REGISTRY_PATH} missing 'models' key")
    return data


def get_model_info(model_name: str) -> Optional[dict]:
    """Return info dict for a model, or None if not found."""
    registry = load_registry()
    return registry["models"].get(model_name)


def list_available_models() -> dict:
    """Return all models from the registry."""
    registry = load_registry()
    return registry["models"]
