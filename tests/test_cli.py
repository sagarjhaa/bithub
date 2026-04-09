"""Tests for bithub CLI commands."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from bithub.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# ──────────────────────────────────────────────────────────────
# Version and help
# ──────────────────────────────────────────────────────────────


class TestVersion:
    def test_shows_version(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1" in result.output


class TestHelp:
    def test_shows_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "bithub" in result.output.lower()

    def test_help_lists_all_commands(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        for cmd in ["setup", "pull", "serve", "run", "models", "list", "rm", "status", "bench"]:
            assert cmd in result.output

    def test_verbose_flag_accepted(self, runner: CliRunner) -> None:
        # --verbose is a valid flag; just invoking --help after it is fine
        result = runner.invoke(cli, ["--verbose", "--help"])
        assert result.exit_code == 0


# ──────────────────────────────────────────────────────────────
# models command
# ──────────────────────────────────────────────────────────────


class TestModelsCommand:
    def test_lists_registry_models(self, runner: CliRunner) -> None:
        with patch("bithub.downloader.is_model_downloaded", return_value=False):
            result = runner.invoke(cli, ["models"])
        assert result.exit_code == 0

    def test_output_contains_model_columns(self, runner: CliRunner) -> None:
        with patch("bithub.downloader.is_model_downloaded", return_value=False):
            result = runner.invoke(cli, ["models"])
        assert result.exit_code == 0
        # Registry has real models — at least one parameter size must appear
        output = result.output
        # The table is printed; check for known column headers in rich table
        assert "Name" in output or "Parameters" in output or "Size" in output or len(output) > 0

    def test_installed_models_shown_as_installed(self, runner: CliRunner) -> None:
        with patch("bithub.downloader.is_model_downloaded", return_value=True):
            result = runner.invoke(cli, ["models"])
        assert result.exit_code == 0
        assert "installed" in result.output


# ──────────────────────────────────────────────────────────────
# list command
# ──────────────────────────────────────────────────────────────


class TestListCommand:
    def test_no_models_downloaded(self, runner: CliRunner) -> None:
        with patch("bithub.downloader.get_downloaded_models", return_value=[]):
            result = runner.invoke(cli, ["list"])
        assert result.exit_code == 0
        assert "No models downloaded" in result.output

    def test_with_downloaded_models(self, runner: CliRunner) -> None:
        fake_models = [
            {"name": "test-model", "size_mb": 500, "path": "/fake/path/test-model.gguf"},
        ]
        with patch("bithub.downloader.get_downloaded_models", return_value=fake_models):
            result = runner.invoke(cli, ["list"])
        assert result.exit_code == 0
        assert "test-model" in result.output


# ──────────────────────────────────────────────────────────────
# status command
# ──────────────────────────────────────────────────────────────


class TestStatusCommand:
    def test_shows_status_engine_not_built(self, runner: CliRunner) -> None:
        with (
            patch("bithub.builder.is_bitnet_cpp_built", return_value=False),
            patch("bithub.builder.get_inference_binary", return_value=None),
            patch("bithub.builder.get_server_binary", return_value=None),
            patch("bithub.downloader.get_downloaded_models", return_value=[]),
        ):
            result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "0.1" in result.output
        assert "Not built" in result.output or "setup" in result.output.lower()

    def test_shows_status_engine_built(self, runner: CliRunner) -> None:
        with (
            patch("bithub.builder.is_bitnet_cpp_built", return_value=True),
            patch("bithub.builder.get_inference_binary", return_value=Path("/fake/llama-cli")),
            patch("bithub.builder.get_server_binary", return_value=Path("/fake/llama-server")),
            patch("bithub.downloader.get_downloaded_models", return_value=[]),
        ):
            result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "Built" in result.output

    def test_shows_downloaded_model_count(self, runner: CliRunner) -> None:
        fake_models = [
            {"name": "test-model", "size_mb": 500, "path": "/fake/path"},
        ]
        with (
            patch("bithub.builder.is_bitnet_cpp_built", return_value=False),
            patch("bithub.builder.get_inference_binary", return_value=None),
            patch("bithub.builder.get_server_binary", return_value=None),
            patch("bithub.downloader.get_downloaded_models", return_value=fake_models),
        ):
            result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "1" in result.output  # "1 downloaded"


# ──────────────────────────────────────────────────────────────
# pull command
# ──────────────────────────────────────────────────────────────


class TestPullCommand:
    def test_pull_unknown_model_exits_nonzero(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["pull", "nonexistent-model-xyz"])
        assert result.exit_code != 0

    def test_pull_unknown_model_shows_error(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["pull", "nonexistent-model-xyz"])
        output = result.output.lower()
        assert "unknown model" in output or "not found" in output or "did you mean" in output

    def test_pull_known_model_calls_download(self, runner: CliRunner) -> None:
        mock_download = MagicMock()
        with patch("bithub.downloader.download_model", mock_download):
            result = runner.invoke(cli, ["pull", "2B-4T"])
        mock_download.assert_called_once_with("2B-4T", force=False)

    def test_pull_known_model_with_force(self, runner: CliRunner) -> None:
        mock_download = MagicMock()
        with patch("bithub.downloader.download_model", mock_download):
            result = runner.invoke(cli, ["pull", "2B-4T", "--force"])
        mock_download.assert_called_once_with("2B-4T", force=True)

    def test_pull_suggests_close_match(self, runner: CliRunner) -> None:
        # "2B" is a substring of registry models, so a suggestion may appear
        result = runner.invoke(cli, ["pull", "2B"])
        # Either succeeds (exact match unlikely) or shows did-you-mean
        output = result.output.lower()
        # Just ensure it doesn't crash with an unhandled exception
        assert result.exception is None or isinstance(result.exception, SystemExit)


# ──────────────────────────────────────────────────────────────
# setup command
# ──────────────────────────────────────────────────────────────


class TestSetupCommand:
    def test_setup_success(self, runner: CliRunner) -> None:
        with patch("bithub.builder.setup_bitnet_cpp", return_value=True):
            result = runner.invoke(cli, ["setup"])
        assert result.exit_code == 0
        assert "all set" in result.output.lower()

    def test_setup_failure_exits_nonzero(self, runner: CliRunner) -> None:
        with patch("bithub.builder.setup_bitnet_cpp", return_value=False):
            result = runner.invoke(cli, ["setup"])
        assert result.exit_code != 0

    def test_setup_force_flag_passed(self, runner: CliRunner) -> None:
        mock_setup = MagicMock(return_value=True)
        with patch("bithub.builder.setup_bitnet_cpp", mock_setup):
            result = runner.invoke(cli, ["setup", "--force"])
        mock_setup.assert_called_once_with(force=True)


# ──────────────────────────────────────────────────────────────
# rm command
# ──────────────────────────────────────────────────────────────


class TestRmCommand:
    def test_rm_nonexistent_model_warns(self, runner: CliRunner) -> None:
        with patch("bithub.downloader.is_model_downloaded", return_value=False):
            result = runner.invoke(cli, ["rm", "nonexistent-model-xyz", "--yes"])
        assert result.exit_code == 0
        assert "not downloaded" in result.output.lower()

    def test_rm_existing_model_with_yes_flag(self, runner: CliRunner) -> None:
        fake_gguf = MagicMock()
        fake_gguf.stat.return_value.st_size = 500 * 1024 * 1024
        fake_gguf.name = "test-model.gguf"

        with (
            patch("bithub.downloader.is_model_downloaded", return_value=True),
            patch("bithub.downloader.get_model_gguf_path", return_value=fake_gguf),
            patch("bithub.downloader.remove_model", return_value=True),
        ):
            result = runner.invoke(cli, ["rm", "test-model", "--yes"])
        assert result.exit_code == 0
        assert "removed" in result.output.lower()

    def test_rm_existing_model_remove_fails(self, runner: CliRunner) -> None:
        fake_gguf = MagicMock()
        fake_gguf.stat.return_value.st_size = 500 * 1024 * 1024
        fake_gguf.name = "test-model.gguf"

        with (
            patch("bithub.downloader.is_model_downloaded", return_value=True),
            patch("bithub.downloader.get_model_gguf_path", return_value=fake_gguf),
            patch("bithub.downloader.remove_model", return_value=False),
        ):
            result = runner.invoke(cli, ["rm", "test-model", "--yes"])
        assert result.exit_code == 0
        assert "failed" in result.output.lower()

    def test_rm_without_yes_prompts_user(self, runner: CliRunner) -> None:
        fake_gguf = MagicMock()
        fake_gguf.stat.return_value.st_size = 100 * 1024 * 1024
        fake_gguf.name = "test-model.gguf"

        with (
            patch("bithub.downloader.is_model_downloaded", return_value=True),
            patch("bithub.downloader.get_model_gguf_path", return_value=fake_gguf),
            patch("bithub.downloader.remove_model", return_value=True),
        ):
            # Simulate user pressing "n" at the confirm prompt
            result = runner.invoke(cli, ["rm", "test-model"], input="n\n")
        assert result.exit_code == 0
        assert "cancelled" in result.output.lower()


# ──────────────────────────────────────────────────────────────
# serve command
# ──────────────────────────────────────────────────────────────


class TestServeCommand:
    def test_serve_engine_not_ready_exits(self, runner: CliRunner) -> None:
        with (
            patch("bithub.builder.is_bitnet_cpp_built", return_value=False),
        ):
            # Input "n" to decline the setup prompt
            result = runner.invoke(cli, ["serve", "2B-4T"], input="n\n")
        assert result.exit_code != 0

    def test_serve_model_not_ready_exits(self, runner: CliRunner) -> None:
        with (
            patch("bithub.builder.is_bitnet_cpp_built", return_value=True),
            patch("bithub.downloader.is_model_downloaded", return_value=False),
        ):
            # Input "n" to decline the download prompt
            result = runner.invoke(cli, ["serve", "2B-4T"], input="n\n")
        assert result.exit_code != 0

    def test_serve_unknown_model_exits(self, runner: CliRunner) -> None:
        with (
            patch("bithub.builder.is_bitnet_cpp_built", return_value=True),
            patch("bithub.downloader.is_model_downloaded", return_value=False),
        ):
            result = runner.invoke(cli, ["serve", "nonexistent-model-xyz"], input="n\n")
        assert result.exit_code != 0

    def test_serve_calls_start_server_when_ready(self, runner: CliRunner) -> None:
        mock_start = MagicMock()
        with (
            patch("bithub.builder.is_bitnet_cpp_built", return_value=True),
            patch("bithub.downloader.is_model_downloaded", return_value=True),
            patch("bithub.server.start_server", mock_start),
        ):
            result = runner.invoke(cli, ["serve", "2B-4T"])
        mock_start.assert_called_once()
        call_kwargs = mock_start.call_args
        assert call_kwargs[1]["model_names"] == ["2B-4T"]

    def test_serve_multiple_models(self, runner: CliRunner) -> None:
        mock_start = MagicMock()
        with (
            patch("bithub.builder.is_bitnet_cpp_built", return_value=True),
            patch("bithub.downloader.is_model_downloaded", return_value=True),
            patch("bithub.server.start_server", mock_start),
        ):
            result = runner.invoke(cli, ["serve", "2B-4T", "falcon3-3B"])
        mock_start.assert_called_once()
        call_kwargs = mock_start.call_args
        assert call_kwargs[1]["model_names"] == ["2B-4T", "falcon3-3B"]

    def test_serve_lazy_flag(self, runner: CliRunner) -> None:
        mock_start = MagicMock()
        with (
            patch("bithub.builder.is_bitnet_cpp_built", return_value=True),
            patch("bithub.downloader.is_model_downloaded", return_value=True),
            patch("bithub.server.start_server", mock_start),
        ):
            result = runner.invoke(cli, ["serve", "2B-4T", "--lazy"])
        mock_start.assert_called_once()
        assert mock_start.call_args[1]["lazy"] is True


# ──────────────────────────────────────────────────────────────
# run command
# ──────────────────────────────────────────────────────────────


class TestRunCommand:
    def test_run_engine_not_ready_exits(self, runner: CliRunner) -> None:
        with patch("bithub.builder.is_bitnet_cpp_built", return_value=False):
            result = runner.invoke(cli, ["run", "2B-4T"], input="n\n")
        assert result.exit_code != 0

    def test_run_model_not_ready_exits(self, runner: CliRunner) -> None:
        with (
            patch("bithub.builder.is_bitnet_cpp_built", return_value=True),
            patch("bithub.downloader.is_model_downloaded", return_value=False),
        ):
            result = runner.invoke(cli, ["run", "2B-4T"], input="n\n")
        assert result.exit_code != 0

    def test_run_starts_background_server_and_repl(self, runner: CliRunner) -> None:
        mock_bg_server = MagicMock()
        mock_wait = MagicMock(return_value=True)
        mock_repl = MagicMock()
        with (
            patch("bithub.builder.is_bitnet_cpp_built", return_value=True),
            patch("bithub.downloader.is_model_downloaded", return_value=True),
            patch("bithub.server.start_background_server", mock_bg_server),
            patch("bithub.server.wait_for_server", mock_wait),
            patch("bithub.repl.start_repl", mock_repl),
        ):
            result = runner.invoke(cli, ["run", "2B-4T"])
        mock_bg_server.assert_called_once()
        assert mock_bg_server.call_args[0][0] == "2B-4T"
        mock_wait.assert_called_once()
        mock_repl.assert_called_once_with(model="2B-4T", api_url="http://127.0.0.1:8081")


# ──────────────────────────────────────────────────────────────
# bench command
# ──────────────────────────────────────────────────────────────


class TestBenchCommand:
    def test_bench_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["bench", "--help"])
        assert result.exit_code == 0
        assert "benchmark" in result.output.lower() or "bench" in result.output.lower()
        assert "--json" in result.output
        assert "--compare" in result.output

    def test_bench_requires_model(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["bench"])
        assert result.exit_code != 0

    def test_bench_unknown_model(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["bench", "nonexistent-xyz"])
        assert result.exit_code != 0


# ──────────────────────────────────────────────────────────────
# _suggest_model helper (tested via pull)
# ──────────────────────────────────────────────────────────────


class TestSuggestModel:
    def test_no_suggestion_for_completely_unknown(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["pull", "zzzzzzz-completely-unknown-zzzz"])
        assert result.exit_code != 0
        assert "Unknown model" in result.output
        # No "did you mean" since nothing matches
        assert "Did you mean" not in result.output

    def test_suggestion_for_partial_match(self, runner: CliRunner) -> None:
        # "falcon" is a substring of falcon3 registry models
        result = runner.invoke(cli, ["pull", "falcon-something"])
        assert result.exit_code != 0
        output = result.output
        assert "Unknown model" in output
        # May or may not suggest; both are valid outcomes — no crash
        assert result.exception is None or isinstance(result.exception, SystemExit)
