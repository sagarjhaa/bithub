"""Tests for bithub.model_manager."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestModelManager:
    def test_register_model(self) -> None:
        from bithub.model_manager import ModelManager
        mgr = ModelManager(base_port=9000)
        mgr.register("test-model", Path("/fake/model.gguf"), threads=2, context_size=2048)
        assert "test-model" in mgr.models
        assert mgr.models["test-model"]["gguf_path"] == Path("/fake/model.gguf")

    def test_register_multiple_models(self) -> None:
        from bithub.model_manager import ModelManager
        mgr = ModelManager(base_port=9000)
        mgr.register("model-a", Path("/fake/a.gguf"))
        mgr.register("model-b", Path("/fake/b.gguf"))
        assert len(mgr.models) == 2

    def test_port_assignment(self) -> None:
        from bithub.model_manager import ModelManager
        mgr = ModelManager(base_port=9000)
        mgr.register("model-a", Path("/fake/a.gguf"))
        mgr.register("model-b", Path("/fake/b.gguf"))
        port_a = mgr.models["model-a"]["backend_port"]
        port_b = mgr.models["model-b"]["backend_port"]
        assert port_a != port_b

    def test_get_backend_url(self) -> None:
        from bithub.model_manager import ModelManager
        mgr = ModelManager(base_port=9000)
        mgr.register("test-model", Path("/fake/model.gguf"))
        url = mgr.get_backend_url("test-model")
        assert url is not None
        assert "9000" in url

    def test_get_backend_url_unknown_model(self) -> None:
        from bithub.model_manager import ModelManager
        mgr = ModelManager(base_port=9000)
        url = mgr.get_backend_url("nonexistent")
        assert url is None

    def test_list_models(self) -> None:
        from bithub.model_manager import ModelManager
        mgr = ModelManager(base_port=9000)
        mgr.register("model-a", Path("/fake/a.gguf"))
        mgr.register("model-b", Path("/fake/b.gguf"))
        models = mgr.list_models()
        assert len(models) == 2
        names = [m["name"] for m in models]
        assert "model-a" in names
        assert "model-b" in names

    def test_is_model_loaded_before_start(self) -> None:
        from bithub.model_manager import ModelManager
        mgr = ModelManager(base_port=9000)
        mgr.register("test-model", Path("/fake/model.gguf"))
        assert mgr.is_loaded("test-model") is False

    def test_max_models_default(self) -> None:
        from bithub.model_manager import ModelManager
        mgr = ModelManager(base_port=9000, max_models=2)
        mgr.register("a", Path("/fake/a.gguf"))
        mgr.register("b", Path("/fake/b.gguf"))
        with pytest.raises(ValueError, match="Maximum.*models"):
            mgr.register("c", Path("/fake/c.gguf"))

    def test_register_same_model_twice_is_noop(self) -> None:
        from bithub.model_manager import ModelManager
        mgr = ModelManager(base_port=9000)
        mgr.register("test-model", Path("/fake/model.gguf"))
        mgr.register("test-model", Path("/fake/model.gguf"))
        assert len(mgr.models) == 1
