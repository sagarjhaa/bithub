"""Tests for bithub.bench."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest


class TestBenchmarkPrompts:
    def test_has_three_prompts(self) -> None:
        from bithub.bench import BENCHMARK_PROMPTS
        assert len(BENCHMARK_PROMPTS) == 3

    def test_prompts_have_required_fields(self) -> None:
        from bithub.bench import BENCHMARK_PROMPTS
        for p in BENCHMARK_PROMPTS:
            assert "name" in p
            assert "messages" in p
            assert len(p["messages"]) > 0


class TestTimingCalculation:
    def test_compute_tokens_per_second(self) -> None:
        from bithub.bench import compute_metrics
        result = compute_metrics(token_count=20, total_time=2.0, time_to_first_token=0.1)
        assert result["tokens_per_second"] == pytest.approx(10.0, rel=0.01)
        assert result["time_to_first_token"] == pytest.approx(0.1, rel=0.01)
        assert result["total_time"] == pytest.approx(2.0, rel=0.01)

    def test_zero_time_returns_zero_tps(self) -> None:
        from bithub.bench import compute_metrics
        result = compute_metrics(token_count=0, total_time=0.0, time_to_first_token=0.0)
        assert result["tokens_per_second"] == 0.0

    def test_formats_result_row(self) -> None:
        from bithub.bench import format_result_row
        row = format_result_row("short", {
            "tokens_per_second": 15.3,
            "time_to_first_token": 0.12,
            "total_time": 1.5,
            "token_count": 23,
        })
        assert row["prompt"] == "short"
        assert "15.3" in row["tok/s"]
        assert "0.12" in row["ttft"]


class TestResultStorage:
    def test_save_results(self, tmp_path: Path) -> None:
        from bithub.bench import save_results
        results = {"model": "test-model", "results": [{"prompt": "short", "tokens_per_second": 15.0}]}
        with patch("bithub.bench.BENCHMARKS_DIR", tmp_path):
            path = save_results("test-model", results)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["model"] == "test-model"

    def test_load_results(self, tmp_path: Path) -> None:
        from bithub.bench import save_results, load_latest_result
        results = {"model": "test-model", "results": []}
        with patch("bithub.bench.BENCHMARKS_DIR", tmp_path):
            save_results("test-model", results)
            loaded = load_latest_result("test-model")
        assert loaded is not None
        assert loaded["model"] == "test-model"

    def test_load_returns_none_when_missing(self, tmp_path: Path) -> None:
        from bithub.bench import load_latest_result
        with patch("bithub.bench.BENCHMARKS_DIR", tmp_path):
            loaded = load_latest_result("nonexistent")
        assert loaded is None
