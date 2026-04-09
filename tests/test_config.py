"""Tests for bithub.config."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest


class TestPaths:
    def test_default_home_is_dot_bithub(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import bithub.config as cfg
            importlib.reload(cfg)
            assert cfg.BITHUB_HOME == Path.home() / ".bithub"

    def test_home_from_env_var(self, tmp_path: Path) -> None:
        custom = str(tmp_path / "custom-home")
        with patch.dict(os.environ, {"BITHUB_HOME": custom}):
            import importlib
            import bithub.config as cfg
            importlib.reload(cfg)
            assert cfg.BITHUB_HOME == Path(custom)

    def test_models_dir_under_home(self) -> None:
        import bithub.config as cfg
        assert cfg.MODELS_DIR == cfg.BITHUB_HOME / "models"

    def test_bitnet_cpp_dir_under_home(self) -> None:
        import bithub.config as cfg
        assert cfg.BITNET_CPP_DIR == cfg.BITHUB_HOME / "bitnet.cpp"


class TestGetDefaultThreads:
    def test_returns_int(self) -> None:
        from bithub.config import get_default_threads
        result = get_default_threads()
        assert isinstance(result, int)
        assert result >= 2

    def test_capped_at_8(self) -> None:
        with patch("os.cpu_count", return_value=32):
            import importlib
            import bithub.config as cfg
            importlib.reload(cfg)
            result = cfg.get_default_threads()
            assert result <= 8

    def test_min_of_2(self) -> None:
        with patch("os.cpu_count", return_value=1):
            import importlib
            import bithub.config as cfg
            importlib.reload(cfg)
            result = cfg.get_default_threads()
            assert result >= 2


class TestEnsureDirs:
    def test_creates_home_and_models_dirs(self, tmp_path: Path) -> None:
        home = tmp_path / ".bithub"
        with patch("bithub.config.BITHUB_HOME", home), \
             patch("bithub.config.MODELS_DIR", home / "models"):
            from bithub.config import ensure_dirs
            ensure_dirs()
            assert home.exists()
            assert (home / "models").exists()


class TestLoadConfig:
    def test_returns_defaults_when_no_config_file(self, tmp_path: Path) -> None:
        home = tmp_path / ".bithub"
        home.mkdir()
        with patch("bithub.config.BITHUB_HOME", home):
            from bithub.config import load_config
            config = load_config()
            assert config["server"]["port"] == 8080
            assert config["server"]["host"] == "127.0.0.1"

    def test_loads_toml_config(self, tmp_path: Path) -> None:
        home = tmp_path / ".bithub"
        home.mkdir()
        config_file = home / "config.toml"
        config_file.write_text('[server]\nport = 9090\n')
        with patch("bithub.config.BITHUB_HOME", home):
            from bithub.config import load_config
            config = load_config()
            assert config["server"]["port"] == 9090
            assert config["server"]["host"] == "127.0.0.1"

    def test_ignores_malformed_toml(self, tmp_path: Path) -> None:
        home = tmp_path / ".bithub"
        home.mkdir()
        config_file = home / "config.toml"
        config_file.write_text("not valid [[[ toml")
        with patch("bithub.config.BITHUB_HOME", home):
            from bithub.config import load_config
            config = load_config()
            assert config["server"]["port"] == 8080
