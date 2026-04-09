"""Tests for bithub.builder."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import subprocess

import pytest

import bithub.builder as builder


class TestIsBitnetCppBuilt:
    def test_false_when_build_dir_missing(self, tmp_path: Path) -> None:
        cpp_dir = tmp_path / "bitnet.cpp"
        cpp_dir.mkdir()
        # build/ subdirectory does NOT exist
        with patch.object(builder, "BITNET_CPP_DIR", cpp_dir):
            assert builder.is_bitnet_cpp_built() is False

    def test_false_when_no_binaries(self, tmp_path: Path) -> None:
        cpp_dir = tmp_path / "bitnet.cpp"
        build_dir = cpp_dir / "build"
        build_dir.mkdir(parents=True)
        # build/ exists but bin/ is empty — no binary
        with patch.object(builder, "BITNET_CPP_DIR", cpp_dir):
            assert builder.is_bitnet_cpp_built() is False

    def test_true_when_inference_binary_exists(self, tmp_path: Path) -> None:
        cpp_dir = tmp_path / "bitnet.cpp"
        bin_dir = cpp_dir / "build" / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "llama-cli").touch()
        with patch.object(builder, "BITNET_CPP_DIR", cpp_dir):
            assert builder.is_bitnet_cpp_built() is True

    def test_true_when_server_binary_acts_as_inference_fallback(self, tmp_path: Path) -> None:
        # _find_inference_binary also checks llama-server as a fallback candidate
        cpp_dir = tmp_path / "bitnet.cpp"
        bin_dir = cpp_dir / "build" / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "llama-server").touch()
        with patch.object(builder, "BITNET_CPP_DIR", cpp_dir):
            assert builder.is_bitnet_cpp_built() is True


class TestFindBinaries:
    def test_find_server_binary(self, tmp_path: Path) -> None:
        cpp_dir = tmp_path / "bitnet.cpp"
        bin_dir = cpp_dir / "build" / "bin"
        bin_dir.mkdir(parents=True)
        server_bin = bin_dir / "llama-server"
        server_bin.touch()
        with patch.object(builder, "BITNET_CPP_DIR", cpp_dir):
            result = builder._find_server_binary()
            assert result is not None
            assert result.name == "llama-server"

    def test_find_inference_binary(self, tmp_path: Path) -> None:
        cpp_dir = tmp_path / "bitnet.cpp"
        bin_dir = cpp_dir / "build" / "bin"
        bin_dir.mkdir(parents=True)
        cli_bin = bin_dir / "llama-cli"
        cli_bin.touch()
        with patch.object(builder, "BITNET_CPP_DIR", cpp_dir):
            result = builder._find_inference_binary()
            assert result is not None
            assert result.name == "llama-cli"

    def test_returns_none_when_missing(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty"
        # directory does not exist — no binaries possible
        with patch.object(builder, "BITNET_CPP_DIR", empty_dir):
            assert builder._find_server_binary() is None
            assert builder._find_inference_binary() is None

    def test_inference_binary_prefers_llama_cli_over_server(self, tmp_path: Path) -> None:
        cpp_dir = tmp_path / "bitnet.cpp"
        bin_dir = cpp_dir / "build" / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "llama-cli").touch()
        (bin_dir / "llama-server").touch()
        with patch.object(builder, "BITNET_CPP_DIR", cpp_dir):
            result = builder._find_inference_binary()
            assert result is not None
            assert result.name == "llama-cli"


class TestCheckPrerequisites:
    def test_reports_missing_tools(self) -> None:
        def fake_run(cmd, **kwargs):
            raise FileNotFoundError("not found")

        with patch("subprocess.run", side_effect=fake_run):
            missing = builder._check_prerequisites()
            assert len(missing) > 0
            assert any("git" in m for m in missing)

    def test_all_present(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            missing = builder._check_prerequisites()
            assert missing == []

    def test_checks_expected_tools(self) -> None:
        called_with = []

        def capture_run(cmd, **kwargs):
            called_with.append(cmd[0])
            return MagicMock(returncode=0)

        with patch("subprocess.run", side_effect=capture_run):
            builder._check_prerequisites()

        assert "git" in called_with
        assert "cmake" in called_with
        assert "python3" in called_with


class TestRunCommand:
    def test_successful_command(self) -> None:
        result = builder._run_command(["echo", "hello"], desc="test echo")
        assert result is True

    def test_failed_command(self) -> None:
        result = builder._run_command(["false"], desc="test failure")
        assert result is False

    def test_missing_executable(self) -> None:
        result = builder._run_command(
            ["__nonexistent_cmd__"], desc="test missing binary"
        )
        assert result is False

    def test_runs_without_desc(self) -> None:
        result = builder._run_command(["echo", "quiet"])
        assert result is True
