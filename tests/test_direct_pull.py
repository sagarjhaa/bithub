"""Tests for direct HuggingFace pull (hf:org/repo syntax)."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestParseHfPrefix:
    def test_detects_hf_prefix(self) -> None:
        from bithub.downloader import is_direct_hf_pull
        assert is_direct_hf_pull("hf:microsoft/BitNet-b1.58-2B-4T-gguf") is True
        assert is_direct_hf_pull("2B-4T") is False
        assert is_direct_hf_pull("hf:") is False

    def test_extracts_repo_id(self) -> None:
        from bithub.downloader import parse_hf_uri
        repo_id, name = parse_hf_uri("hf:microsoft/BitNet-b1.58-2B-4T-gguf")
        assert repo_id == "microsoft/BitNet-b1.58-2B-4T-gguf"
        assert name == "BitNet-b1.58-2B-4T-gguf"

    def test_extracts_short_name(self) -> None:
        from bithub.downloader import parse_hf_uri
        _, name = parse_hf_uri("hf:tiiuae/Falcon3-1B-Instruct-1.58bit")
        assert name == "Falcon3-1B-Instruct-1.58bit"


class TestCustomModelRegistry:
    def test_save_and_load_custom_model(self, tmp_home: Path) -> None:
        with patch("bithub.registry.BITHUB_HOME", tmp_home):
            # Also need to patch the module-level CUSTOM_MODELS_PATH
            custom_path = tmp_home / "custom_models.json"
            with patch("bithub.registry.CUSTOM_MODELS_PATH", custom_path):
                from bithub.registry import save_custom_model, load_custom_models
                save_custom_model("my-model", {
                    "hf_repo": "user/my-model-gguf",
                    "name": "My Model",
                    "source": "direct",
                })
                models = load_custom_models()
                assert "my-model" in models
                assert models["my-model"]["hf_repo"] == "user/my-model-gguf"

    def test_empty_when_no_file(self, tmp_home: Path) -> None:
        custom_path = tmp_home / "custom_models.json"
        with patch("bithub.registry.CUSTOM_MODELS_PATH", custom_path):
            from bithub.registry import load_custom_models
            models = load_custom_models()
            assert models == {}


class TestDownloadDirectHf:
    def test_downloads_from_hf_repo(self, tmp_home: Path) -> None:
        mock_api = MagicMock()
        mock_api.list_repo_files.return_value = ["model.gguf", "README.md"]

        model_dir = tmp_home / "models" / "my-model"
        model_dir.mkdir(parents=True)
        fake_gguf = model_dir / "model.gguf"
        fake_gguf.write_bytes(b"\x00" * 100)

        custom_path = tmp_home / "custom_models.json"
        with patch("bithub.downloader.MODELS_DIR", tmp_home / "models"), \
             patch("bithub.downloader.ensure_dirs"), \
             patch("bithub.downloader.HfApi", return_value=mock_api), \
             patch("bithub.downloader.hf_hub_download", return_value=str(fake_gguf)), \
             patch("bithub.registry.BITHUB_HOME", tmp_home), \
             patch("bithub.registry.CUSTOM_MODELS_PATH", custom_path):
            from bithub.downloader import download_direct_hf
            result = download_direct_hf("user/my-model-gguf", name="my-model")
            assert result.exists()
