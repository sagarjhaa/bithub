# Phase B5: Performance Benchmarks

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `bithub bench <model>` command that measures inference speed (tokens/sec, time to first token, total time) using fixed prompts, displays results as a rich table, saves JSON results, and supports side-by-side model comparison.

**Architecture:** `bithub/bench.py` starts a background API server (reusing `start_background_server` + `wait_for_server`), sends 3 fixed prompts via streaming HTTP to `/v1/chat/completions`, measures timing on each SSE chunk, and aggregates results. Results are saved to `~/.bithub/benchmarks/`. The CLI command in `cli.py` wires it up with `--json` and `--compare` options.

**Tech Stack:** httpx (streaming), time (measurement), existing server infrastructure. No new dependencies.

---

## File Map

**Created:**
- `bithub/bench.py` — Benchmark engine (prompts, timing, results)
- `tests/test_bench.py` — Benchmark unit tests

**Modified:**
- `bithub/cli.py` — Add `bench` command
- `bithub/config.py` — Add `BENCHMARKS_DIR` constant

---

## Task 0: Benchmark Engine Core

**Files:**
- Create: `bithub/bench.py`
- Create: `tests/test_bench.py`
- Modify: `bithub/config.py`

- [ ] **Step 1: Add BENCHMARKS_DIR to config.py**

Read `bithub/config.py`. Add after `LOG_PATH`:

```python
BENCHMARKS_DIR = BITHUB_HOME / "benchmarks"
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_bench.py`:

```python
"""Tests for bithub.bench."""

import json
import time
from pathlib import Path
from typing import List
from unittest.mock import patch, MagicMock

import pytest


FIXED_PROMPTS = None  # Will import from bench module


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
        # 20 tokens in 2 seconds = 10 tok/s
        result = compute_metrics(
            token_count=20,
            total_time=2.0,
            time_to_first_token=0.1,
        )
        assert result["tokens_per_second"] == pytest.approx(10.0, rel=0.01)
        assert result["time_to_first_token"] == pytest.approx(0.1, rel=0.01)
        assert result["total_time"] == pytest.approx(2.0, rel=0.01)

    def test_zero_time_returns_zero_tps(self) -> None:
        from bithub.bench import compute_metrics
        result = compute_metrics(token_count=0, total_time=0.0, time_to_first_token=0.0)
        assert result["tokens_per_second"] == 0.0

    def test_formats_result_summary(self) -> None:
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
        results = {
            "model": "test-model",
            "results": [{"prompt": "short", "tokens_per_second": 15.0}],
        }
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
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
/usr/bin/python3 -m pytest tests/test_bench.py -v
```

- [ ] **Step 4: Create `bithub/bench.py`**

```python
"""Performance benchmarking for bithub models."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx
from rich.console import Console
from rich.table import Table

from bithub.config import BENCHMARKS_DIR

console = Console()


BENCHMARK_PROMPTS = [
    {
        "name": "short",
        "messages": [
            {"role": "user", "content": "What is 2+2? Answer in one sentence."},
        ],
    },
    {
        "name": "medium",
        "messages": [
            {"role": "user", "content": "Explain how a CPU works in about 100 words. Cover the fetch-decode-execute cycle."},
        ],
    },
    {
        "name": "long",
        "messages": [
            {"role": "user", "content": "Write a detailed explanation of how neural networks learn, covering forward propagation, loss functions, backpropagation, and gradient descent. Use concrete examples. Aim for about 300 words."},
        ],
    },
]


def compute_metrics(
    token_count: int,
    total_time: float,
    time_to_first_token: float,
) -> dict:
    """Compute benchmark metrics from raw measurements."""
    if total_time <= 0 or token_count <= 0:
        tps = 0.0
    else:
        tps = token_count / total_time
    return {
        "tokens_per_second": round(tps, 2),
        "time_to_first_token": round(time_to_first_token, 4),
        "total_time": round(total_time, 4),
        "token_count": token_count,
    }


def format_result_row(prompt_name: str, metrics: dict) -> dict:
    """Format metrics into display strings for a table row."""
    return {
        "prompt": prompt_name,
        "tok/s": f"{metrics['tokens_per_second']:.1f}",
        "ttft": f"{metrics['time_to_first_token']:.2f}s",
        "total": f"{metrics['total_time']:.2f}s",
        "tokens": str(metrics["token_count"]),
    }


def run_single_benchmark(
    api_url: str,
    model: str,
    prompt: dict,
) -> dict:
    """Run a single benchmark prompt and measure timing.

    Returns metrics dict with tokens_per_second, time_to_first_token, etc.
    """
    url = f"{api_url}/v1/chat/completions"
    payload = {
        "model": model,
        "messages": prompt["messages"],
        "stream": True,
        "max_tokens": 512,
    }

    token_count = 0
    time_to_first_token = 0.0
    start = time.time()
    first_token_received = False

    try:
        with httpx.stream("POST", url, json=payload, timeout=120.0) as response:
            if response.status_code != 200:
                console.print(f"  [red]API error: {response.status_code}[/red]")
                return compute_metrics(0, 0.0, 0.0)

            for line in response.iter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        if not first_token_received:
                            time_to_first_token = time.time() - start
                            first_token_received = True
                        token_count += 1
                except json.JSONDecodeError:
                    continue

    except (httpx.ConnectError, httpx.ReadTimeout) as e:
        console.print(f"  [red]Connection error: {e}[/red]")
        return compute_metrics(0, 0.0, 0.0)

    total_time = time.time() - start
    return compute_metrics(token_count, total_time, time_to_first_token)


def run_benchmark(api_url: str, model: str) -> List[dict]:
    """Run all benchmark prompts against a model. Returns list of results."""
    results = []
    for prompt in BENCHMARK_PROMPTS:
        console.print(f"  Running: [cyan]{prompt['name']}[/cyan]...", end=" ")
        metrics = run_single_benchmark(api_url, model, prompt)
        console.print(f"[green]{metrics['tokens_per_second']:.1f} tok/s[/green]")
        metrics["prompt"] = prompt["name"]
        results.append(metrics)
    return results


def display_results(model: str, results: List[dict]) -> None:
    """Display benchmark results as a rich table."""
    table = Table(title=f"Benchmark: {model}")
    table.add_column("Prompt", style="cyan")
    table.add_column("Tokens/s", justify="right", style="bold green")
    table.add_column("TTFT", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("Tokens", justify="right", style="dim")

    for r in results:
        row = format_result_row(r["prompt"], r)
        table.add_row(row["prompt"], row["tok/s"], row["ttft"], row["total"], row["tokens"])

    # Average row
    if results:
        avg_tps = sum(r["tokens_per_second"] for r in results) / len(results)
        avg_ttft = sum(r["time_to_first_token"] for r in results) / len(results)
        table.add_row("", "", "", "", "", end_section=True)
        table.add_row("[bold]average[/bold]", f"[bold]{avg_tps:.1f}[/bold]", f"{avg_ttft:.2f}s", "", "")

    console.print()
    console.print(table)


def display_comparison(results_by_model: Dict[str, List[dict]]) -> None:
    """Display side-by-side comparison of multiple models."""
    models = list(results_by_model.keys())
    table = Table(title="Benchmark Comparison")
    table.add_column("Prompt", style="cyan")
    for model in models:
        table.add_column(f"{model} tok/s", justify="right", style="bold green")
        table.add_column(f"{model} TTFT", justify="right", style="dim")

    prompt_names = [p["name"] for p in BENCHMARK_PROMPTS]
    for pname in prompt_names:
        row = [pname]
        for model in models:
            result = next((r for r in results_by_model[model] if r["prompt"] == pname), None)
            if result:
                row.append(f"{result['tokens_per_second']:.1f}")
                row.append(f"{result['time_to_first_token']:.2f}s")
            else:
                row.append("-")
                row.append("-")
        table.add_row(*row)

    console.print()
    console.print(table)


def save_results(model: str, data: dict) -> Path:
    """Save benchmark results to JSON file."""
    BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = BENCHMARKS_DIR / f"{model}-{date_str}.json"
    path.write_text(json.dumps(data, indent=2))
    return path


def load_latest_result(model: str) -> Optional[dict]:
    """Load the most recent benchmark result for a model."""
    if not BENCHMARKS_DIR.exists():
        return None
    files = sorted(BENCHMARKS_DIR.glob(f"{model}-*.json"), reverse=True)
    if not files:
        return None
    return json.loads(files[0].read_text())
```

- [ ] **Step 5: Run tests**

```bash
/usr/bin/python3 -m pytest tests/test_bench.py -v
/usr/bin/python3 -m pytest tests/ -v
```

- [ ] **Step 6: Commit**

```bash
git add bithub/bench.py bithub/config.py tests/test_bench.py
git commit -m "Add benchmark engine: prompts, timing, results storage"
```

---

## Task 1: CLI `bench` Command

**Files:**
- Modify: `bithub/cli.py`

- [ ] **Step 1: Read `bithub/cli.py`**

- [ ] **Step 2: Add the `bench` command**

Add before the `status` command (or after `run`):

```python
@cli.command()
@click.argument("model_names", nargs=-1, required=True)
@click.option("--port", default=8090, hidden=True, help="Port for benchmark server")
@click.option("--threads", "-t", default=_DEFAULT_THREADS, show_default=True,
              help="Number of CPU threads")
@click.option("--context-size", "-c", default=2048, show_default=True,
              help="Context window size")
@click.option("--json-output", "--json", is_flag=True, help="Output results as JSON")
@click.option("--compare", is_flag=True, help="Show side-by-side comparison")
def bench(model_names, port, threads, context_size, json_output, compare):
    """Benchmark model inference speed.

    Runs fixed prompts (short, medium, long) and measures tokens/sec,
    time to first token, and total time.

    \b
    Examples:
        bithub bench 2B-4T
        bithub bench 2B-4T --json
        bithub bench 2B-4T falcon3-3B --compare
    """
    import json as json_mod
    if not _ensure_engine_ready():
        raise SystemExit(1)

    for name in model_names:
        if not _ensure_model_ready(name):
            raise SystemExit(1)

    from bithub.server import start_background_server, wait_for_server
    from bithub.bench import (
        run_benchmark, display_results, display_comparison,
        save_results,
    )

    all_results = {}

    for i, name in enumerate(model_names):
        model_port = port + (i * 2)
        api_url = f"http://127.0.0.1:{model_port}"

        console.print(f"\n[bold]Benchmarking {name}...[/bold]")
        console.print(f"[dim]Starting server on port {model_port}...[/dim]")

        start_background_server(
            name, host="127.0.0.1", port=model_port,
            threads=threads, context_size=context_size,
        )

        if not wait_for_server(api_url):
            console.print(f"[red]Server failed to start for {name}.[/red]")
            continue

        results = run_benchmark(api_url, name)
        all_results[name] = results

        bench_data = {
            "model": name,
            "threads": threads,
            "context_size": context_size,
            "results": results,
        }
        saved_path = save_results(name, bench_data)
        console.print(f"[dim]Results saved to {saved_path}[/dim]")

        if not compare:
            if json_output:
                console.print(json_mod.dumps(bench_data, indent=2))
            else:
                display_results(name, results)

    if compare and len(all_results) > 1:
        if json_output:
            console.print(json_mod.dumps(all_results, indent=2))
        else:
            display_comparison(all_results)
```

- [ ] **Step 3: Run tests**

```bash
/usr/bin/python3 -m pytest tests/test_cli.py -v
/usr/bin/python3 -m pytest tests/ -v
```

- [ ] **Step 4: Commit**

```bash
git add bithub/cli.py
git commit -m "Add bench CLI command with --json and --compare options"
```

---

## Task 2: CLI Tests for bench Command

**Files:**
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add bench command tests**

Add to `tests/test_cli.py`:

```python
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
```

- [ ] **Step 2: Run tests**

```bash
/usr/bin/python3 -m pytest tests/test_cli.py -v
/usr/bin/python3 -m pytest tests/ -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -m "Add bench CLI command tests"
```

---

## Task 3: Final Verification

- [ ] **Step 1: Run full test suite**

```bash
/usr/bin/python3 -m pytest tests/ --cov=bithub --cov-report=term-missing -v
```

- [ ] **Step 2: Verify bench help**

```bash
/usr/bin/python3 -c "from bithub.cli import cli; cli(['bench', '--help'])" 2>&1 || true
```

- [ ] **Step 3: Commit any fixes and push**

```bash
git add -A
git commit -m "Phase B5 complete: performance benchmarks with comparison"
git push origin main
```
