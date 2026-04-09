"""Tests for bithub.registry."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.conftest import SAMPLE_REGISTRY


class TestLoadRegistry:
    def test_loads_valid_registry(self, sample_registry_file: Path) -> None:
        with patch("bithub.registry.REGISTRY_PATH", sample_registry_file):
            from bithub.registry import load_registry
            result = load_registry()
        assert "models" in result
        assert "test-model" in result["models"]

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.json"
        with patch("bithub.registry.REGISTRY_PATH", missing):
            from bithub.registry import load_registry
            with pytest.raises(FileNotFoundError):
                load_registry()

    def test_raises_on_invalid_json(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{invalid json")
        with patch("bithub.registry.REGISTRY_PATH", bad_file):
            from bithub.registry import load_registry
            with pytest.raises(json.JSONDecodeError):
                load_registry()

    def test_raises_on_missing_models_key(self, tmp_path: Path) -> None:
        no_models = tmp_path / "empty.json"
        no_models.write_text(json.dumps({"version": 1}))
        with patch("bithub.registry.REGISTRY_PATH", no_models):
            from bithub.registry import load_registry
            with pytest.raises(ValueError, match="missing 'models' key"):
                load_registry()


class TestGetModelInfo:
    def test_returns_model_info(self, sample_registry_file: Path) -> None:
        with patch("bithub.registry.REGISTRY_PATH", sample_registry_file):
            from bithub.registry import get_model_info
            info = get_model_info("test-model")
        assert info is not None
        assert info["name"] == "Test Model"
        assert info["hf_repo"] == "test-org/test-model-gguf"

    def test_returns_none_for_unknown_model(self, sample_registry_file: Path) -> None:
        with patch("bithub.registry.REGISTRY_PATH", sample_registry_file):
            from bithub.registry import get_model_info
            info = get_model_info("nonexistent-model")
        assert info is None


class TestListAvailableModels:
    def test_lists_all_models(self, sample_registry_file: Path) -> None:
        with patch("bithub.registry.REGISTRY_PATH", sample_registry_file):
            from bithub.registry import list_available_models
            models = list_available_models()
        assert len(models) == 2
        assert "test-model" in models
        assert "test-model-2" in models
