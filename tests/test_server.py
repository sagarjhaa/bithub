"""Tests for bithub.server."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import bithub.server as server


class TestPreflightCheck:
    def test_exits_when_engine_not_built(self) -> None:
        with patch.object(server, "is_bitnet_cpp_built", return_value=False):
            with pytest.raises(SystemExit):
                server._preflight_check("test-model")

    def test_exits_when_model_not_downloaded(self) -> None:
        with patch.object(server, "is_bitnet_cpp_built", return_value=True), \
             patch.object(server, "is_model_downloaded", return_value=False):
            with pytest.raises(SystemExit):
                server._preflight_check("test-model")

    def test_exits_when_gguf_path_is_none(self) -> None:
        with patch.object(server, "is_bitnet_cpp_built", return_value=True), \
             patch.object(server, "is_model_downloaded", return_value=True), \
             patch.object(server, "get_model_gguf_path", return_value=None):
            with pytest.raises(SystemExit):
                server._preflight_check("test-model")

    def test_returns_gguf_path_when_ready(self, tmp_path: Path) -> None:
        fake_gguf = tmp_path / "model.gguf"
        fake_gguf.touch()
        with patch.object(server, "is_bitnet_cpp_built", return_value=True), \
             patch.object(server, "is_model_downloaded", return_value=True), \
             patch.object(server, "get_model_gguf_path", return_value=fake_gguf):
            result = server._preflight_check("test-model")
            assert result == fake_gguf


class TestRunInteractive:
    def _patch_preflight_and_binary(self, tmp_path: Path):
        """Return a context manager stack that patches preflight + binary lookup."""
        fake_gguf = tmp_path / "model.gguf"
        fake_gguf.touch()
        fake_bin = tmp_path / "llama-cli"
        fake_bin.touch()
        return (
            patch.object(server, "_preflight_check", return_value=fake_gguf),
            patch.object(server, "get_inference_binary", return_value=fake_bin),
            patch.object(server, "get_model_info", return_value={"name": "Test Model"}),
        )

    def test_calls_popen(self, tmp_path: Path) -> None:
        p1, p2, p3 = self._patch_preflight_and_binary(tmp_path)
        mock_process = MagicMock()
        mock_process.returncode = 0
        with p1, p2, p3, patch("subprocess.Popen", return_value=mock_process) as mock_popen:
            server.run_interactive("test-model")
            mock_popen.assert_called_once()
            mock_process.wait.assert_called_once()

    def test_reports_nonzero_exit_code(self, tmp_path: Path) -> None:
        p1, p2, p3 = self._patch_preflight_and_binary(tmp_path)
        mock_process = MagicMock()
        mock_process.returncode = 1
        with p1, p2, p3, \
             patch("subprocess.Popen", return_value=mock_process), \
             patch.object(server, "console") as mock_console:
            server.run_interactive("test-model")
            # Should have printed an error about the non-zero exit code
            mock_console.print.assert_any_call(
                "\n[red]Process exited with code 1.[/red] "
                "Run [bold]bithub status[/bold] to check your setup."
            )

    def test_handles_binary_not_found(self, tmp_path: Path) -> None:
        p1, p2, p3 = self._patch_preflight_and_binary(tmp_path)
        with p1, p2, p3, \
             patch("subprocess.Popen", side_effect=FileNotFoundError("not found")):
            with pytest.raises(SystemExit):
                server.run_interactive("test-model")

    def test_exits_when_no_inference_binary(self, tmp_path: Path) -> None:
        fake_gguf = tmp_path / "model.gguf"
        fake_gguf.touch()
        with patch.object(server, "_preflight_check", return_value=fake_gguf), \
             patch.object(server, "get_inference_binary", return_value=None):
            with pytest.raises(SystemExit):
                server.run_interactive("test-model")
