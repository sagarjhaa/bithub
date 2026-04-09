"""Tests for bithub.api — OpenAI-compatible API endpoints and request validation."""

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_client():
    """Create a TestClient with mocked dependencies (no real backend)."""
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
        app.router.on_startup.clear()
        app.router.on_shutdown.clear()
        client = TestClient(app)
        yield client


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_200(self, api_client):
        resp = api_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "model" in data

    def test_health_includes_model_field(self, api_client):
        resp = api_client.get("/health")
        data = resp.json()
        # Backend startup is skipped in tests, so model may be empty
        assert "model" in data


class TestModelsEndpoint:
    """Tests for GET /v1/models."""

    def test_models_returns_200(self, api_client):
        resp = api_client.get("/v1/models")
        assert resp.status_code == 200

    def test_models_returns_list_object(self, api_client):
        resp = api_client.get("/v1/models")
        data = resp.json()
        assert data["object"] == "list"
        assert "data" in data
        assert isinstance(data["data"], list)


class TestChatCompletionsValidation:
    """Tests for POST /v1/chat/completions request validation."""

    def _make_payload(self, **overrides):
        payload = {
            "model": "test-model",
            "messages": [{"role": "user", "content": "Hello"}],
        }
        payload.update(overrides)
        return payload

    def test_rejects_empty_messages(self, api_client):
        payload = self._make_payload(messages=[])
        resp = api_client.post("/v1/chat/completions", json=payload)
        assert resp.status_code == 422

    def test_rejects_temperature_above_2(self, api_client):
        payload = self._make_payload(temperature=2.5)
        resp = api_client.post("/v1/chat/completions", json=payload)
        assert resp.status_code == 422

    def test_rejects_temperature_below_0(self, api_client):
        payload = self._make_payload(temperature=-0.1)
        resp = api_client.post("/v1/chat/completions", json=payload)
        assert resp.status_code == 422

    def test_rejects_negative_max_tokens(self, api_client):
        payload = self._make_payload(max_tokens=-1)
        resp = api_client.post("/v1/chat/completions", json=payload)
        assert resp.status_code == 422

    def test_rejects_zero_max_tokens(self, api_client):
        payload = self._make_payload(max_tokens=0)
        resp = api_client.post("/v1/chat/completions", json=payload)
        assert resp.status_code == 422

    def test_rejects_top_p_above_1(self, api_client):
        payload = self._make_payload(top_p=1.5)
        resp = api_client.post("/v1/chat/completions", json=payload)
        assert resp.status_code == 422

    def test_rejects_top_p_below_0(self, api_client):
        payload = self._make_payload(top_p=-0.1)
        resp = api_client.post("/v1/chat/completions", json=payload)
        assert resp.status_code == 422
