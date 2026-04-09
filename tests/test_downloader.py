"""Tests for bithub.downloader."""

import json
import shutil
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

import bithub.downloader as dl
from tests.conftest import SAMPLE_REGISTRY


@pytest.fixture
def patched_downloader(tmp_home: Path, sample_registry_file: Path):
    """Patch downloader to use temp dirs."""
    models_dir = tmp_home / "models"
    with patch.object(dl, "MODELS_DIR", models_dir), \
         patch.object(dl, "ensure_dirs"), \
         patch("bithub.registry.REGISTRY_PATH", sample_registry_file):
        yield dl


class TestGetGgufFilename:
    def test_finds_gguf_in_repo(self, patched_downloader) -> None:
        mock_api = MagicMock()
        mock_api.list_repo_files.return_value = [
            "README.md",
            "model.gguf",
            "config.json",
        ]
        with patch.object(dl, "HfApi", return_value=mock_api):
            result = patched_downloader.get_gguf_filename(
                {"hf_repo": "test-org/test-model-gguf", "name": "test-model", "quant_type": "i2_s"}
            )
        assert result == "model.gguf"

    def test_returns_candidate_when_no_gguf(self, patched_downloader) -> None:
        mock_api = MagicMock()
        mock_api.list_repo_files.return_value = ["README.md", "config.json"]
        with patch.object(dl, "HfApi", return_value=mock_api):
            # When no GGUF found in repo, it falls back to a candidate name
            result = patched_downloader.get_gguf_filename(
                {"hf_repo": "test-org/test-model-gguf", "name": "test-model", "quant_type": "i2_s"}
            )
            assert result.endswith(".gguf")


class TestIsModelDownloaded:
    def test_returns_false_when_not_downloaded(self, patched_downloader, tmp_home: Path) -> None:
        assert patched_downloader.is_model_downloaded("test-model") is False

    def test_returns_true_when_gguf_exists(self, patched_downloader, mock_model_dir: Path) -> None:
        assert patched_downloader.is_model_downloaded("test-model") is True


class TestGetDownloadedModels:
    def test_empty_when_no_models(self, patched_downloader) -> None:
        result = patched_downloader.get_downloaded_models()
        assert result == []

    def test_lists_downloaded_models(self, patched_downloader, mock_model_dir: Path) -> None:
        result = patched_downloader.get_downloaded_models()
        assert len(result) == 1
        assert result[0]["name"] == "test-model"


class TestParseSizeMb:
    def test_converts_mb_to_bytes(self) -> None:
        assert dl._parse_size_mb(500) == 500 * 1024 * 1024

    def test_zero_returns_zero(self) -> None:
        assert dl._parse_size_mb(0) == 0


class TestDiskSpaceCheck:
    def test_aborts_when_insufficient_space(self, patched_downloader, tmp_home: Path) -> None:
        mock_usage = MagicMock()
        mock_usage.free = 100 * 1024 * 1024  # 100MB
        with patch("shutil.disk_usage", return_value=mock_usage):
            with pytest.raises(SystemExit):
                patched_downloader._check_disk_space(tmp_home / "models", 500)

    def test_proceeds_when_sufficient_space(self, patched_downloader, tmp_home: Path) -> None:
        mock_usage = MagicMock()
        mock_usage.free = 10 * 1024 * 1024 * 1024  # 10GB
        with patch("shutil.disk_usage", return_value=mock_usage):
            # Should not raise
            patched_downloader._check_disk_space(tmp_home / "models", 500)

    def test_skips_check_when_zero_size(self, patched_downloader, tmp_home: Path) -> None:
        # Should not raise and should not call disk_usage
        with patch("shutil.disk_usage") as mock_du:
            patched_downloader._check_disk_space(tmp_home / "models", 0)
            mock_du.assert_not_called()


class TestDownloadModelDiskSpace:
    def test_download_aborts_when_insufficient_space(self, patched_downloader, tmp_home: Path) -> None:
        mock_usage = MagicMock()
        mock_usage.free = 100 * 1024 * 1024  # 100MB
        with patch("shutil.disk_usage", return_value=mock_usage), \
             patch.object(dl, "get_model_info", return_value={
                 "hf_repo": "test-org/test", "name": "test-model",
                 "size_mb": 500, "parameters": "1B",
             }):
            with pytest.raises(SystemExit):
                patched_downloader.download_model("test-model")

    def test_download_proceeds_when_sufficient_space(self, patched_downloader, tmp_home: Path) -> None:
        mock_usage = MagicMock()
        mock_usage.free = 10 * 1024 * 1024 * 1024  # 10GB
        mock_gguf = MagicMock()
        mock_gguf.return_value = "model.gguf"
        model_dir = tmp_home / "models" / "test-model"
        model_dir.mkdir(parents=True, exist_ok=True)
        (model_dir / "model.gguf").write_bytes(b"\x00" * 100)
        with patch("shutil.disk_usage", return_value=mock_usage), \
             patch.object(dl, "get_gguf_filename", mock_gguf), \
             patch.object(dl, "get_model_info", return_value={
                 "hf_repo": "test-org/test", "name": "test-model",
                 "size_mb": 500, "parameters": "1B",
             }), \
             patch.object(dl, "hf_hub_download", return_value=str(model_dir / "model.gguf")):
            patched_downloader.download_model("test-model", force=True)


class TestRemoveModel:
    def test_removes_existing_model(self, patched_downloader, mock_model_dir: Path) -> None:
        assert mock_model_dir.exists()
        result = patched_downloader.remove_model("test-model")
        assert result is True
        assert not mock_model_dir.exists()

    def test_returns_false_for_nonexistent(self, patched_downloader) -> None:
        result = patched_downloader.remove_model("nonexistent")
        assert result is False
