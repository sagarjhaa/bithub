"""Tests for bithub dashboard API endpoints."""

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def dashboard_client():
    from bithub.model_manager import ModelManager
    from bithub.api import create_app

    mgr = ModelManager(base_port=19000)
    mgr.register("test-model", Path("/fake/model.gguf"))

    app = create_app(
        model_name="test-model",
        gguf_path=Path("/fake/model.gguf"),
        manager=mgr,
    )
    app.router.on_startup.clear()
    app.router.on_shutdown.clear()

    client = TestClient(app)
    yield client, mgr


class TestStatsEndpoint:
    def test_returns_stats(self, dashboard_client) -> None:
        client, mgr = dashboard_client
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert "uptime_seconds" in data
        assert "total_requests" in data
        assert "models_registered" in data

    def test_request_counter(self, dashboard_client) -> None:
        client, mgr = dashboard_client
        mgr.record_request()
        mgr.record_request()
        response = client.get("/api/stats")
        data = response.json()
        assert data["total_requests"] == 2


class TestConfigEndpoint:
    def test_get_config(self, dashboard_client) -> None:
        client, _ = dashboard_client
        response = client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert "server" in data


class TestModelsManagement:
    def test_list_downloaded(self, dashboard_client) -> None:
        client, _ = dashboard_client
        with patch("bithub.dashboard_api.get_downloaded_models", return_value=[]):
            response = client.get("/api/models/downloaded")
        assert response.status_code == 200

    def test_delete_model(self, dashboard_client) -> None:
        client, _ = dashboard_client
        with patch("bithub.dashboard_api.remove_model", return_value=True):
            response = client.delete("/api/models/test-model")
        assert response.status_code == 200
        assert response.json()["removed"] is True

    def test_delete_nonexistent(self, dashboard_client) -> None:
        client, _ = dashboard_client
        with patch("bithub.dashboard_api.remove_model", return_value=False):
            response = client.delete("/api/models/nonexistent")
        assert response.status_code == 404
