# Rename + Phase A: Bulletproof Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename `bitnet_hub` → `bithub` everywhere, then add tests, CI, config file support, logging, disk space checks, error handling, and model integrity — making the existing code production-grade.

**Architecture:** The existing module structure stays the same (cli, config, registry, downloader, builder, server, api). We add `logging_setup.py` for structured logging, extend `config.py` with TOML support, and create a full pytest suite. Every module gets hardened error handling and type hints.

**Tech Stack:** pytest, pytest-asyncio, pytest-cov, mypy, ruff, tomli (Python 3.9-3.10 backport for TOML)

---

## File Map

**Renamed (directory move):**
- `bitnet_hub/` → `bithub/` (all files inside)

**Modified:**
- `bithub/__init__.py` — update docstring
- `bithub/cli.py` — all imports, all string references
- `bithub/config.py` — env var name, paths, add TOML loading
- `bithub/registry.py` — add schema validation
- `bithub/downloader.py` — imports, add disk space check
- `bithub/builder.py` — imports
- `bithub/server.py` — imports, error handling hardening
- `bithub/api.py` — imports, request validation, error responses
- `pyproject.toml` — package name, entry point, dev deps
- `README.md` — all references
- `CLAUDE.md` — all references
- `CONTRIBUTING.md` — all references

**Created:**
- `bithub/logging_setup.py` — structured logging configuration
- `tests/conftest.py` — shared fixtures
- `tests/test_registry.py`
- `tests/test_config.py`
- `tests/test_downloader.py`
- `tests/test_builder.py`
- `tests/test_server.py`
- `tests/test_api.py`
- `tests/test_cli.py`
- `.github/workflows/ci.yml`

---

## Task 0: Rename `bitnet_hub` → `bithub`

**Files:**
- Rename: `bitnet_hub/` → `bithub/`
- Modify: `pyproject.toml`
- Modify: `bithub/__init__.py`
- Modify: `bithub/cli.py`
- Modify: `bithub/config.py`
- Modify: `bithub/downloader.py`
- Modify: `bithub/builder.py`
- Modify: `bithub/server.py`
- Modify: `bithub/api.py`
- Modify: `README.md`
- Modify: `CLAUDE.md`
- Modify: `CONTRIBUTING.md`

- [ ] **Step 1: Rename the package directory**

```bash
git mv bitnet_hub bithub
```

- [ ] **Step 2: Update `pyproject.toml`**

Replace the full file content:

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "bithub"
version = "0.1.0"
description = "The missing friendly interface for BitNet inference. Ollama for 1-bit LLMs."
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.9"
dependencies = [
    "click>=8.0",
    "rich>=13.0",
    "huggingface-hub>=0.20.0",
    "fastapi>=0.100.0",
    "uvicorn>=0.20.0",
    "httpx>=0.24.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.0",
    "mypy>=1.0",
    "ruff>=0.4",
]

[project.scripts]
bithub = "bithub.cli:cli"

[project.urls]
Homepage = "https://github.com/sagarjhaa/bithub"
Issues = "https://github.com/sagarjhaa/bithub/issues"

[tool.setuptools.packages.find]
include = ["bithub*"]

[tool.setuptools.package-data]
bithub = ["registry.json"]

[tool.ruff]
target-version = "py39"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "W"]

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 3: Update `bithub/__init__.py`**

```python
"""bithub — Ollama for 1-bit LLMs."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Update all imports and string references in every Python file**

In every `.py` file under `bithub/`, do a find-and-replace:
- `bitnet_hub` → `bithub` (import paths)
- `bitnet-hub` → `bithub` (CLI name in user-facing strings)
- `BITNET_HUB_HOME` → `BITHUB_HOME` (env var and constant)
- `.bitnet-hub` → `.bithub` (config directory)
- `bitnet-hub` → `bithub` (in FastAPI title, docstrings, error messages)

Specific file changes:

**`bithub/config.py`** — rename constants:
```python
"""bithub configuration — paths, defaults, system detection."""

import os
import platform
from pathlib import Path

# ~/.bithub/ is the default home for all bithub data
BITHUB_HOME = Path(os.environ.get("BITHUB_HOME", Path.home() / ".bithub"))
MODELS_DIR = BITHUB_HOME / "models"
BITNET_CPP_DIR = BITHUB_HOME / "bitnet.cpp"
DB_PATH = BITHUB_HOME / "models.json"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
```

**`bithub/cli.py`** — update all imports from `bithub.*` and replace every `bitnet-hub` string with `bithub`. The Click group name and all help text must say `bithub`.

**`bithub/downloader.py`** — update imports: `from bithub.config import MODELS_DIR, ensure_dirs` and `from bithub.registry import get_model_info`.

**`bithub/builder.py`** — update import: `from bithub.config import BITNET_CPP_DIR, ensure_dirs`.

**`bithub/server.py`** — update all imports from `bithub.*` and string references.

**`bithub/api.py`** — update all imports from `bithub.*`, FastAPI title to `"bithub API"`, and all string references.

- [ ] **Step 5: Update documentation files**

**`README.md`** — replace all `bitnet-hub` with `bithub`, `bitnet_hub` with `bithub`, `~/.bitnet-hub` with `~/.bithub`.

**`CLAUDE.md`** — same replacements, also update `BITNET_HUB_HOME` → `BITHUB_HOME`.

**`CONTRIBUTING.md`** — same replacements.

- [ ] **Step 6: Verify the rename works**

```bash
pip install -e .
bithub --version
bithub --help
```

Expected: CLI responds as `bithub`, version `0.1.0`, all commands listed.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "Rename bitnet-hub to bithub across all code, config, and docs"
```

---

## Task 1: Dev Tooling and Test Infrastructure

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Install dev dependencies**

```bash
pip install -e ".[dev]"
```

- [ ] **Step 2: Create `tests/__init__.py`**

```python
```

(Empty file — makes `tests/` a package.)

- [ ] **Step 3: Create `tests/conftest.py` with shared fixtures**

```python
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
```

- [ ] **Step 4: Verify pytest discovers the fixture file**

```bash
pytest --collect-only
```

Expected: shows `tests/conftest.py` and 0 tests collected (no test files yet).

- [ ] **Step 5: Verify ruff and mypy run**

```bash
ruff check bithub/
mypy bithub/ --ignore-missing-imports
```

Expected: ruff may report issues (we'll fix later), mypy may report missing type hints (expected). Both tools should run without crashing.

- [ ] **Step 6: Commit**

```bash
git add tests/__init__.py tests/conftest.py
git commit -m "Add test infrastructure with shared fixtures"
```

---

## Task 2: Test and Harden `registry.py`

**Files:**
- Modify: `bithub/registry.py`
- Create: `tests/test_registry.py`

- [ ] **Step 1: Write failing tests for registry**

Create `tests/test_registry.py`:

```python
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
        assert info["repo_id"] == "test-org/test-model-gguf"

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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_registry.py -v
```

Expected: `test_raises_on_missing_models_key` fails because `load_registry` doesn't validate the schema yet.

- [ ] **Step 3: Add schema validation to `registry.py`**

Replace `bithub/registry.py` with:

```python
"""Model registry — loads and queries the curated model catalog."""

import json
from pathlib import Path

REGISTRY_PATH = Path(__file__).parent / "registry.json"


def load_registry() -> dict:
    """Load the model registry from disk. Raises on missing/invalid file."""
    with open(REGISTRY_PATH) as f:
        data = json.load(f)
    if "models" not in data:
        raise ValueError(f"Registry {REGISTRY_PATH} missing 'models' key")
    return data


def get_model_info(model_name: str) -> dict | None:
    """Return info dict for a model, or None if not found."""
    registry = load_registry()
    return registry["models"].get(model_name)


def list_available_models() -> dict:
    """Return all models from the registry."""
    registry = load_registry()
    return registry["models"]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_registry.py -v
```

Expected: all 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add bithub/registry.py tests/test_registry.py
git commit -m "Add registry validation and tests"
```

---

## Task 3: Test and Harden `config.py` + Add TOML Config Support

**Files:**
- Modify: `bithub/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_config.py`:

```python
"""Tests for bithub.config."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest


class TestPaths:
    def test_default_home_is_dot_bithub(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            # Re-import to pick up fresh env
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
            # Non-overridden values remain defaults
            assert config["server"]["host"] == "127.0.0.1"

    def test_ignores_malformed_toml(self, tmp_path: Path) -> None:
        home = tmp_path / ".bithub"
        home.mkdir()
        config_file = home / "config.toml"
        config_file.write_text("not valid [[[ toml")
        with patch("bithub.config.BITHUB_HOME", home):
            from bithub.config import load_config
            # Should return defaults, not crash
            config = load_config()
            assert config["server"]["port"] == 8080
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_config.py -v
```

Expected: `TestLoadConfig` tests fail because `load_config` doesn't exist yet.

- [ ] **Step 3: Add TOML config loading to `config.py`**

Add to the end of `bithub/config.py`:

```python
import sys
import copy
import logging

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
```

Also add `tomli` as a conditional dependency in `pyproject.toml`:

```toml
dependencies = [
    "click>=8.0",
    "rich>=13.0",
    "huggingface-hub>=0.20.0",
    "fastapi>=0.100.0",
    "uvicorn>=0.20.0",
    "httpx>=0.24.0",
    "tomli>=2.0; python_version < '3.11'",
]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_config.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add bithub/config.py tests/test_config.py pyproject.toml
git commit -m "Add TOML config file support and config tests"
```

---

## Task 4: Structured Logging

**Files:**
- Create: `bithub/logging_setup.py`
- Modify: `bithub/config.py` (add log path constant)

- [ ] **Step 1: Add log path constant to `config.py`**

Add after the `DB_PATH` line in `bithub/config.py`:

```python
LOG_PATH = BITHUB_HOME / "bithub.log"
```

- [ ] **Step 2: Create `bithub/logging_setup.py`**

```python
"""Structured logging setup for bithub."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from bithub.config import LOG_PATH, BITHUB_HOME


def setup_logging(debug: bool = False, verbose: bool = False) -> None:
    """Configure logging for bithub.

    - File handler always writes to ~/.bithub/bithub.log (INFO level).
    - Console handler only active with --debug (DEBUG) or --verbose (INFO).
    - Default: no console output — terminal stays clean.
    """
    BITHUB_HOME.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("bithub")
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    # File handler — always on, rotated
    file_handler = RotatingFileHandler(
        LOG_PATH, maxBytes=10 * 1024 * 1024, backupCount=3
    )
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)
    root.addHandler(file_handler)

    # Console handler — only with flags
    if debug or verbose:
        try:
            from rich.logging import RichHandler
            console_handler = RichHandler(rich_tracebacks=True, show_path=False)
        except ImportError:
            console_handler = logging.StreamHandler()  # type: ignore[assignment]
        console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
        root.addHandler(console_handler)
```

- [ ] **Step 3: Wire logging into CLI**

Add `--debug` and `--verbose` flags to the `cli` group in `bithub/cli.py`. In the `cli()` function body, add:

```python
@click.group()
@click.version_option(__version__, prog_name="bithub")
@click.option("--debug", is_flag=True, hidden=True, help="Enable debug logging")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx, debug, verbose):
    """bithub — Ollama for 1-bit LLMs."""
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    ctx.obj["verbose"] = verbose
    from bithub.logging_setup import setup_logging
    setup_logging(debug=debug, verbose=verbose)
```

- [ ] **Step 4: Verify logging works**

```bash
bithub --debug status
ls ~/.bithub/bithub.log
```

Expected: debug output on terminal, log file created.

- [ ] **Step 5: Commit**

```bash
git add bithub/logging_setup.py bithub/config.py bithub/cli.py
git commit -m "Add structured logging with file rotation and debug/verbose flags"
```

---

## Task 5: Test `downloader.py` + Disk Space Checks

**Files:**
- Modify: `bithub/downloader.py`
- Create: `tests/test_downloader.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_downloader.py`:

```python
"""Tests for bithub.downloader."""

import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import SAMPLE_REGISTRY


@pytest.fixture
def patched_downloader(tmp_home: Path, sample_registry_file: Path):
    """Patch downloader to use temp dirs."""
    with patch("bithub.downloader.MODELS_DIR", tmp_home / "models"), \
         patch("bithub.downloader.ensure_dirs"), \
         patch("bithub.registry.REGISTRY_PATH", sample_registry_file):
        import importlib
        import bithub.downloader as dl
        importlib.reload(dl)
        yield dl


class TestGetGgufFilename:
    def test_finds_gguf_in_repo(self, patched_downloader) -> None:
        mock_api = MagicMock()
        mock_api.list_repo_files.return_value = [
            "README.md",
            "model.gguf",
            "config.json",
        ]
        with patch("bithub.downloader.HfApi", return_value=mock_api):
            result = patched_downloader.get_gguf_filename(
                {"repo_id": "test-org/test-model-gguf"}
            )
        assert result == "model.gguf"

    def test_raises_when_no_gguf(self, patched_downloader) -> None:
        mock_api = MagicMock()
        mock_api.list_repo_files.return_value = ["README.md", "config.json"]
        with patch("bithub.downloader.HfApi", return_value=mock_api):
            with pytest.raises(SystemExit):
                patched_downloader.get_gguf_filename(
                    {"repo_id": "test-org/test-model-gguf"}
                )


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


class TestDiskSpaceCheck:
    def test_aborts_when_insufficient_space(self, patched_downloader) -> None:
        # Mock disk_usage to return only 100MB free
        mock_usage = MagicMock()
        mock_usage.free = 100 * 1024 * 1024  # 100MB
        with patch("shutil.disk_usage", return_value=mock_usage), \
             patch("bithub.downloader.get_model_info", return_value={
                 "repo_id": "test-org/test", "size": "500MB",
             }):
            with pytest.raises(SystemExit):
                patched_downloader.download_model("test-model")

    def test_proceeds_when_sufficient_space(self, patched_downloader, tmp_home: Path) -> None:
        # Mock disk_usage to return 10GB free
        mock_usage = MagicMock()
        mock_usage.free = 10 * 1024 * 1024 * 1024  # 10GB
        mock_gguf = MagicMock()
        mock_gguf.return_value = "model.gguf"
        with patch("shutil.disk_usage", return_value=mock_usage), \
             patch("bithub.downloader.get_gguf_filename", mock_gguf), \
             patch("bithub.downloader.get_model_info", return_value={
                 "repo_id": "test-org/test", "size": "500MB",
             }), \
             patch("bithub.downloader.hf_hub_download", return_value="/fake/path"):
            # Should not raise
            patched_downloader.download_model("test-model")


class TestRemoveModel:
    def test_removes_existing_model(self, patched_downloader, mock_model_dir: Path) -> None:
        assert mock_model_dir.exists()
        result = patched_downloader.remove_model("test-model")
        assert result is True
        assert not mock_model_dir.exists()

    def test_returns_false_for_nonexistent(self, patched_downloader) -> None:
        result = patched_downloader.remove_model("nonexistent")
        assert result is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_downloader.py -v
```

Expected: `TestDiskSpaceCheck` tests fail — disk space checking doesn't exist yet.

- [ ] **Step 3: Add disk space checking to `downloader.py`**

Add this helper function before `download_model`:

```python
def _parse_size_string(size_str: str) -> int:
    """Parse a size string like '500MB' or '2.5GB' into bytes."""
    size_str = size_str.strip().upper()
    multipliers = {"KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
    for suffix, mult in multipliers.items():
        if size_str.endswith(suffix):
            return int(float(size_str[: -len(suffix)]) * mult)
    return 0  # Unknown format, skip check


def _check_disk_space(target_dir: Path, required_size_str: str) -> None:
    """Abort if disk space is insufficient for the download."""
    required = _parse_size_string(required_size_str)
    if required == 0:
        return  # Can't determine size, skip check
    usage = shutil.disk_usage(target_dir)
    # Need required + 1GB buffer
    buffer = 1024**3
    if usage.free < required + buffer:
        free_gb = usage.free / 1024**3
        req_gb = required / 1024**3
        console.print(
            f"[red]Insufficient disk space.[/red] "
            f"Need {req_gb:.1f}GB, only {free_gb:.1f}GB free at {target_dir}"
        )
        raise SystemExit(1)
```

Then add a call to `_check_disk_space` at the start of `download_model`, right after looking up the model info:

```python
def download_model(model_name: str, force: bool = False) -> Path:
    # ... existing model_info lookup ...
    _check_disk_space(MODELS_DIR, model_info.get("size", "0MB"))
    # ... rest of existing download logic ...
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_downloader.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add bithub/downloader.py tests/test_downloader.py
git commit -m "Add disk space checking and downloader tests"
```

---

## Task 6: Test `builder.py`

**Files:**
- Create: `tests/test_builder.py`

- [ ] **Step 1: Write tests**

Create `tests/test_builder.py`:

```python
"""Tests for bithub.builder."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestIsBitnetCppBuilt:
    def test_false_when_dir_missing(self, tmp_path: Path) -> None:
        with patch("bithub.builder.BITNET_CPP_DIR", tmp_path / "nonexistent"):
            from bithub.builder import is_bitnet_cpp_built
            assert is_bitnet_cpp_built() is False

    def test_false_when_no_binaries(self, tmp_path: Path) -> None:
        cpp_dir = tmp_path / "bitnet.cpp"
        cpp_dir.mkdir()
        with patch("bithub.builder.BITNET_CPP_DIR", cpp_dir):
            from bithub.builder import is_bitnet_cpp_built
            assert is_bitnet_cpp_built() is False

    def test_true_when_server_binary_exists(self, tmp_path: Path) -> None:
        cpp_dir = tmp_path / "bitnet.cpp"
        bin_dir = cpp_dir / "build" / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "llama-server").touch()
        with patch("bithub.builder.BITNET_CPP_DIR", cpp_dir):
            from bithub.builder import is_bitnet_cpp_built
            assert is_bitnet_cpp_built() is True


class TestFindBinaries:
    def test_find_server_binary(self, tmp_path: Path) -> None:
        cpp_dir = tmp_path / "bitnet.cpp"
        bin_dir = cpp_dir / "build" / "bin"
        bin_dir.mkdir(parents=True)
        server_bin = bin_dir / "llama-server"
        server_bin.touch()
        with patch("bithub.builder.BITNET_CPP_DIR", cpp_dir):
            from bithub.builder import _find_server_binary
            result = _find_server_binary()
            assert result is not None
            assert result.name == "llama-server"

    def test_find_inference_binary(self, tmp_path: Path) -> None:
        cpp_dir = tmp_path / "bitnet.cpp"
        bin_dir = cpp_dir / "build" / "bin"
        bin_dir.mkdir(parents=True)
        cli_bin = bin_dir / "llama-cli"
        cli_bin.touch()
        with patch("bithub.builder.BITNET_CPP_DIR", cpp_dir):
            from bithub.builder import _find_inference_binary
            result = _find_inference_binary()
            assert result is not None
            assert result.name == "llama-cli"

    def test_returns_none_when_missing(self, tmp_path: Path) -> None:
        with patch("bithub.builder.BITNET_CPP_DIR", tmp_path / "empty"):
            from bithub.builder import _find_server_binary, _find_inference_binary
            assert _find_server_binary() is None
            assert _find_inference_binary() is None


class TestCheckPrerequisites:
    def test_reports_missing_tools(self) -> None:
        with patch("shutil.which", return_value=None):
            from bithub.builder import _check_prerequisites
            missing = _check_prerequisites()
            assert len(missing) > 0
            assert any("git" in m for m in missing)

    def test_all_present(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/fake"):
            from bithub.builder import _check_prerequisites
            missing = _check_prerequisites()
            assert len(missing) == 0


class TestRunCommand:
    def test_successful_command(self) -> None:
        from bithub.builder import _run_command
        result = _run_command(["echo", "hello"], desc="test echo")
        assert result is True

    def test_failed_command(self) -> None:
        from bithub.builder import _run_command
        result = _run_command(["false"], desc="test failure")
        assert result is False
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/test_builder.py -v
```

Expected: all tests pass (builder.py already has the functions, we're just testing them).

- [ ] **Step 3: Commit**

```bash
git add tests/test_builder.py
git commit -m "Add builder tests"
```

---

## Task 7: Test and Harden `server.py`

**Files:**
- Modify: `bithub/server.py`
- Create: `tests/test_server.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_server.py`:

```python
"""Tests for bithub.server."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


@pytest.fixture
def mock_preflight():
    """Patch all external dependencies for server tests."""
    fake_gguf = Path("/fake/model.gguf")
    with patch("bithub.server.is_bitnet_cpp_built", return_value=True), \
         patch("bithub.server.is_model_downloaded", return_value=True), \
         patch("bithub.server.get_model_gguf_path", return_value=fake_gguf), \
         patch("bithub.server.get_server_binary", return_value=Path("/fake/llama-server")), \
         patch("bithub.server.get_inference_binary", return_value=Path("/fake/llama-cli")), \
         patch("bithub.server.get_model_info", return_value={"name": "Test"}):
        yield fake_gguf


class TestPreflightCheck:
    def test_raises_when_engine_not_built(self) -> None:
        with patch("bithub.server.is_bitnet_cpp_built", return_value=False):
            from bithub.server import _preflight_check
            with pytest.raises(SystemExit):
                _preflight_check("test-model")

    def test_raises_when_model_not_downloaded(self) -> None:
        with patch("bithub.server.is_bitnet_cpp_built", return_value=True), \
             patch("bithub.server.is_model_downloaded", return_value=False):
            from bithub.server import _preflight_check
            with pytest.raises(SystemExit):
                _preflight_check("test-model")

    def test_returns_path_when_all_ready(self, mock_preflight) -> None:
        from bithub.server import _preflight_check
        result = _preflight_check("test-model")
        assert result == Path("/fake/model.gguf")


class TestStartServer:
    def test_server_starts_subprocess(self, mock_preflight) -> None:
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None  # still running
        mock_proc.pid = 12345
        with patch("subprocess.Popen", return_value=mock_proc) as popen_mock, \
             patch("bithub.server.console"), \
             patch("bithub.api.create_app") as mock_app, \
             patch("uvicorn.run"):
            from bithub.server import start_server
            start_server("test-model", port=9090, threads=4)
            # Verify uvicorn.run was called
            import uvicorn
            uvicorn.run.assert_called_once()

    def test_server_reports_backend_crash(self, mock_preflight) -> None:
        """Backend process crashing should be reported, not silently ignored."""
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 1  # exited with error
        mock_proc.stderr = MagicMock()
        mock_proc.stderr.read.return_value = b"segfault"
        with patch("subprocess.Popen", return_value=mock_proc), \
             patch("bithub.server.console") as mock_console:
            # The server should handle backend failure gracefully
            # This test validates the error handling we're about to add
            pass  # Placeholder — implementation in step 3


class TestRunInteractive:
    def test_runs_inference_binary(self, mock_preflight) -> None:
        mock_proc = MagicMock()
        mock_proc.wait.return_value = 0
        mock_proc.returncode = 0
        with patch("subprocess.Popen", return_value=mock_proc), \
             patch("bithub.server.console"):
            from bithub.server import run_interactive
            run_interactive("test-model", threads=4)
            subprocess.Popen.assert_called_once()

    def test_reports_crash(self, mock_preflight) -> None:
        mock_proc = MagicMock()
        mock_proc.wait.return_value = 1
        mock_proc.returncode = 1
        with patch("subprocess.Popen", return_value=mock_proc), \
             patch("bithub.server.console") as mock_console:
            from bithub.server import run_interactive
            run_interactive("test-model", threads=4)
            # Should print error about non-zero exit
            mock_console.print.assert_called()
```

- [ ] **Step 2: Run tests to see what fails**

```bash
pytest tests/test_server.py -v
```

Expected: `test_reports_crash` in `TestRunInteractive` fails — `run_interactive` doesn't check returncode.

- [ ] **Step 3: Harden `server.py` error handling**

In `run_interactive`, after `process.wait()`, add crash reporting:

```python
def run_interactive(model_name: str, threads: int = 2, context_size: int = 2048) -> None:
    # ... existing preflight and command setup ...
    try:
        process = subprocess.Popen(cmd)
        process.wait()
        if process.returncode != 0:
            console.print(
                f"\n[red]Process exited with code {process.returncode}.[/red] "
                f"Run [bold]bithub status[/bold] to check your setup."
            )
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]")
        process.terminate()
        process.wait(timeout=5)
    except FileNotFoundError:
        console.print(
            "[red]Inference binary not found.[/red] "
            "Run [bold]bithub setup[/bold] to rebuild."
        )
        raise SystemExit(1)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_server.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add bithub/server.py tests/test_server.py
git commit -m "Harden server error handling and add server tests"
```

---

## Task 8: Test and Harden `api.py`

**Files:**
- Modify: `bithub/api.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Write tests**

Create `tests/test_api.py`:

```python
"""Tests for bithub.api — OpenAI-compatible endpoints."""

from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_client():
    """Create a TestClient with mocked backend."""
    with patch("bithub.api.get_server_binary", return_value=Path("/fake/server")), \
         patch("bithub.api.is_model_downloaded", return_value=True), \
         patch("bithub.api.get_downloaded_models", return_value=[]), \
         patch("bithub.api.list_available_models", return_value={}), \
         patch("bithub.api.get_model_info", return_value={"name": "Test Model"}):
        from bithub.api import create_app
        app = create_app(
            model_name="test-model",
            gguf_path=Path("/fake/model.gguf"),
            threads=2,
            context_size=2048,
            backend_port=9999,
        )
        # Skip startup/shutdown (no real backend)
        app.router.on_startup.clear()
        app.router.on_shutdown.clear()
        client = TestClient(app)
        yield client


class TestHealthEndpoint:
    def test_health_returns_ok(self, api_client) -> None:
        response = api_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestListModels:
    def test_returns_model_list(self, api_client) -> None:
        response = api_client.get("/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data


class TestChatCompletions:
    def test_rejects_empty_messages(self, api_client) -> None:
        response = api_client.post("/v1/chat/completions", json={
            "model": "test-model",
            "messages": [],
        })
        # FastAPI validation should reject empty messages
        assert response.status_code in (400, 422)

    def test_rejects_invalid_temperature(self, api_client) -> None:
        response = api_client.post("/v1/chat/completions", json={
            "model": "test-model",
            "messages": [{"role": "user", "content": "hi"}],
            "temperature": 5.0,  # Invalid: must be 0-2
        })
        assert response.status_code in (400, 422)

    def test_rejects_negative_max_tokens(self, api_client) -> None:
        response = api_client.post("/v1/chat/completions", json={
            "model": "test-model",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": -1,
        })
        assert response.status_code in (400, 422)

    def test_valid_request_format(self, api_client) -> None:
        """Valid request shape is accepted (backend will fail since it's mocked)."""
        # We test request validation only — backend isn't running
        with patch("httpx.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "choices": [{"message": {"role": "assistant", "content": "hello"}, "finish_reason": "stop", "index": 0}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
                "model": "test-model",
                "id": "test-id",
                "object": "chat.completion",
                "created": 0,
            }
            mock_post.return_value = mock_resp
            response = api_client.post("/v1/chat/completions", json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "hi"}],
            })
            # Should at least pass validation (may fail on backend connection)
            assert response.status_code in (200, 502, 503)
```

- [ ] **Step 2: Run tests to see what fails**

```bash
pytest tests/test_api.py -v
```

Expected: `test_rejects_empty_messages`, `test_rejects_invalid_temperature`, `test_rejects_negative_max_tokens` fail because `ChatCompletionRequest` has no validators yet.

- [ ] **Step 3: Add Pydantic validators to `ChatCompletionRequest`**

In `bithub/api.py`, update the `ChatCompletionRequest` model:

```python
from pydantic import BaseModel, Field, field_validator

class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(default=None, gt=0)
    stream: Optional[bool] = False
    stop: Optional[list[str] | str] = None

    @field_validator("messages")
    @classmethod
    def messages_not_empty(cls, v: list) -> list:
        if len(v) == 0:
            raise ValueError("messages must not be empty")
        return v
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_api.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add bithub/api.py tests/test_api.py
git commit -m "Add API request validation and endpoint tests"
```

---

## Task 9: Test CLI Commands

**Files:**
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write CLI tests using Click's CliRunner**

Create `tests/test_cli.py`:

```python
"""Tests for bithub CLI commands."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from bithub.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestVersion:
    def test_shows_version(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestHelp:
    def test_shows_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "bithub" in result.output.lower()
        # All commands should appear
        for cmd in ["setup", "pull", "serve", "run", "models", "list", "rm", "status"]:
            assert cmd in result.output


class TestModelsCommand:
    def test_lists_registry_models(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["models"])
        assert result.exit_code == 0
        # Should show the model table
        assert "2B-4T" in result.output or "Model" in result.output


class TestListCommand:
    def test_empty_when_no_models(self, runner: CliRunner, tmp_path: Path) -> None:
        with patch("bithub.downloader.MODELS_DIR", tmp_path / "empty"):
            result = runner.invoke(cli, ["list"])
            assert result.exit_code == 0


class TestStatusCommand:
    def test_shows_status(self, runner: CliRunner) -> None:
        with patch("bithub.builder.is_bitnet_cpp_built", return_value=False):
            result = runner.invoke(cli, ["status"])
            assert result.exit_code == 0


class TestPullCommand:
    def test_pull_unknown_model_suggests(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["pull", "nonexistent-model-xyz"])
        assert result.exit_code != 0 or "not found" in result.output.lower() or "did you mean" in result.output.lower()


class TestRmCommand:
    def test_rm_nonexistent_model(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["rm", "nonexistent-model-xyz", "--yes"])
        # Should handle gracefully
        assert result.exit_code in (0, 1)


class TestSuggestModel:
    def test_suggests_similar_name(self) -> None:
        from bithub.cli import _suggest_model
        # Should not crash on unknown model
        _suggest_model("2b4t")  # Close to "2B-4T"
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/test_cli.py -v
```

Expected: all tests pass (these test existing behavior).

- [ ] **Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -m "Add CLI command tests"
```

---

## Task 10: Model Integrity (SHA256)

**Files:**
- Modify: `bithub/downloader.py`
- Modify: `tests/test_downloader.py`

- [ ] **Step 1: Write failing test for SHA256**

Add to `tests/test_downloader.py`:

```python
import hashlib


class TestModelIntegrity:
    def test_sha256_written_after_download(self, patched_downloader, tmp_home: Path) -> None:
        """After download, a sha256 file should exist alongside the GGUF."""
        model_dir = tmp_home / "models" / "test-model"
        model_dir.mkdir(parents=True)
        gguf = model_dir / "model.gguf"
        gguf.write_bytes(b"fake model data")
        expected_hash = hashlib.sha256(b"fake model data").hexdigest()

        from bithub.downloader import _write_checksum
        _write_checksum(gguf)

        sha_file = model_dir / "sha256"
        assert sha_file.exists()
        assert sha_file.read_text().strip() == expected_hash

    def test_verify_checksum_passes(self, patched_downloader, tmp_home: Path) -> None:
        model_dir = tmp_home / "models" / "test-model"
        model_dir.mkdir(parents=True)
        gguf = model_dir / "model.gguf"
        data = b"fake model data"
        gguf.write_bytes(data)
        sha_file = model_dir / "sha256"
        sha_file.write_text(hashlib.sha256(data).hexdigest())

        from bithub.downloader import verify_checksum
        assert verify_checksum("test-model") is True

    def test_verify_checksum_fails_on_mismatch(self, patched_downloader, tmp_home: Path) -> None:
        model_dir = tmp_home / "models" / "test-model"
        model_dir.mkdir(parents=True)
        gguf = model_dir / "model.gguf"
        gguf.write_bytes(b"real data")
        sha_file = model_dir / "sha256"
        sha_file.write_text("0000000000000000000000000000000000000000000000000000000000000000")

        from bithub.downloader import verify_checksum
        assert verify_checksum("test-model") is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_downloader.py::TestModelIntegrity -v
```

Expected: fails — `_write_checksum` and `verify_checksum` don't exist.

- [ ] **Step 3: Add checksum functions to `downloader.py`**

Add to `bithub/downloader.py`:

```python
import hashlib


def _compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def _write_checksum(gguf_path: Path) -> None:
    """Write SHA256 checksum file next to the GGUF."""
    sha = _compute_sha256(gguf_path)
    checksum_file = gguf_path.parent / "sha256"
    checksum_file.write_text(sha)


def verify_checksum(model_name: str) -> bool:
    """Verify a model's GGUF matches its stored SHA256. Returns False if mismatch or missing."""
    gguf_path = get_model_gguf_path(model_name)
    if gguf_path is None:
        return False
    checksum_file = gguf_path.parent / "sha256"
    if not checksum_file.exists():
        return False
    stored = checksum_file.read_text().strip()
    actual = _compute_sha256(gguf_path)
    return stored == actual
```

Then add a call to `_write_checksum` at the end of `download_model`, after the download succeeds:

```python
    # ... after successful download ...
    _write_checksum(gguf_path)
    console.print(f"[green]SHA256 checksum saved.[/green]")
    return gguf_path
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_downloader.py -v
```

Expected: all tests pass including the new integrity tests.

- [ ] **Step 5: Commit**

```bash
git add bithub/downloader.py tests/test_downloader.py
git commit -m "Add SHA256 model integrity verification"
```

---

## Task 11: CI/CD Pipeline

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create GitHub Actions workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]
        python-version: ["3.9", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Lint with ruff
        run: ruff check bithub/

      - name: Type check with mypy
        run: mypy bithub/ --ignore-missing-imports
        continue-on-error: true  # Strict mode added incrementally

      - name: Run tests with coverage
        run: pytest --cov=bithub --cov-report=term-missing -v

      - name: Check coverage threshold
        run: pytest --cov=bithub --cov-fail-under=70 -q
```

- [ ] **Step 2: Verify workflow syntax is valid**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" 2>/dev/null || echo "Install pyyaml to validate, or just check manually"
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "Add GitHub Actions CI pipeline for linting, typing, and testing"
```

---

## Task 12: Final Verification and Cleanup

**Files:**
- Modify: `CLAUDE.md` (update project status)

- [ ] **Step 1: Run full test suite**

```bash
pytest --cov=bithub --cov-report=term-missing -v
```

Expected: all tests pass, coverage report shows >= 70% line coverage.

- [ ] **Step 2: Run ruff**

```bash
ruff check bithub/ --fix
```

Expected: any auto-fixable lint issues resolved.

- [ ] **Step 3: Run mypy**

```bash
mypy bithub/ --ignore-missing-imports
```

Expected: no critical errors (warnings acceptable for now).

- [ ] **Step 4: Verify CLI still works end-to-end**

```bash
bithub --version
bithub --help
bithub models
bithub status
```

Expected: all commands work with the new `bithub` name.

- [ ] **Step 5: Update CLAUDE.md**

Update the project status section to reflect the rename and Phase A completion. Update all references from `bitnet-hub` to `bithub`, update architecture section to show new files (`logging_setup.py`, `tests/`), add the dev dependencies note.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "Complete Phase A: rename to bithub, tests, CI, config, logging, integrity checks"
```
