"""Model registry — catalog of known BitNet models."""

import json
from pathlib import Path

REGISTRY_PATH = Path(__file__).parent / "registry.json"


def load_registry() -> dict:
    """Load the model registry from the bundled JSON file."""
    with open(REGISTRY_PATH) as f:
        return json.load(f)["models"]


def get_model_info(model_name: str) -> dict | None:
    """Look up a model by its short name (e.g. '2B-4T')."""
    registry = load_registry()
    return registry.get(model_name)


def list_available_models() -> dict:
    """Return all models in the registry."""
    return load_registry()
