"""Shared test fixtures for bithub."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest


SAMPLE_REGISTRY = {
    "models": {
        "test-model": {
            "name": "Test Model",
            "repo_id": "test-org/test-model-gguf",
            "description": "A test model for unit tests",
            "parameters": "1B",
            "size": "500MB",
            "quant_type": "i2_s",
        },
        "test-model-2": {
            "name": "Test Model 2",
            "repo_id": "test-org/test-model-2-gguf",
            "description": "Another test model",
            "parameters": "3B",
            "size": "2GB",
            "quant_type": "i2_s",
        },
    }
}


@pytest.fixture
def tmp_home(tmp_path: Path) -> Path:
    """Create a temporary bithub home directory structure."""
    home = tmp_path / ".bithub"
    home.mkdir()
    (home / "models").mkdir()
    return home


@pytest.fixture
def sample_registry_file(tmp_path: Path) -> Path:
    """Write a sample registry.json and return its path."""
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(SAMPLE_REGISTRY))
    return registry_path


@pytest.fixture
def mock_model_dir(tmp_home: Path) -> Path:
    """Create a fake downloaded model directory with a GGUF file."""
    model_dir = tmp_home / "models" / "test-model"
    model_dir.mkdir(parents=True)
    gguf_file = model_dir / "test-model.gguf"
    gguf_file.write_bytes(b"\x00" * 1024)  # 1KB fake GGUF
    return model_dir
