"""Performance benchmarking for bithub models."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from rich.console import Console
from rich.table import Table

from bithub.config import BENCHMARKS_DIR

console = Console()

BENCHMARK_PROMPTS = [
    {
        "name": "short",
        "messages": [{"role": "user", "content": "What is 2+2? Answer in one sentence."}],
    },
    {
        "name": "medium",
        "messages": [{"role": "user", "content": "Explain how a CPU works in about 100 words. Cover the fetch-decode-execute cycle."}],
    },
    {
        "name": "long",
        "messages": [{"role": "user", "content": "Write a detailed explanation of how neural networks learn, covering forward propagation, loss functions, backpropagation, and gradient descent. Use concrete examples. Aim for about 300 words."}],
    },
]


def compute_metrics(token_count: int, total_time: float, time_to_first_token: float) -> dict:
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
    return {
        "prompt": prompt_name,
        "tok/s": f"{metrics['tokens_per_second']:.1f}",
        "ttft": f"{metrics['time_to_first_token']:.2f}s",
        "total": f"{metrics['total_time']:.2f}s",
        "tokens": str(metrics["token_count"]),
    }


def run_single_benchmark(api_url: str, model: str, prompt: dict) -> dict:
    url = f"{api_url}/v1/chat/completions"
    payload = {"model": model, "messages": prompt["messages"], "stream": True, "max_tokens": 512}
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
    results = []
    for prompt in BENCHMARK_PROMPTS:
        console.print(f"  Running: [cyan]{prompt['name']}[/cyan]...", end=" ")
        metrics = run_single_benchmark(api_url, model, prompt)
        console.print(f"[green]{metrics['tokens_per_second']:.1f} tok/s[/green]")
        metrics["prompt"] = prompt["name"]
        results.append(metrics)
    return results


def display_results(model: str, results: List[dict]) -> None:
    table = Table(title=f"Benchmark: {model}")
    table.add_column("Prompt", style="cyan")
    table.add_column("Tokens/s", justify="right", style="bold green")
    table.add_column("TTFT", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("Tokens", justify="right", style="dim")
    for r in results:
        row = format_result_row(r["prompt"], r)
        table.add_row(row["prompt"], row["tok/s"], row["ttft"], row["total"], row["tokens"])
    if results:
        avg_tps = sum(r["tokens_per_second"] for r in results) / len(results)
        avg_ttft = sum(r["time_to_first_token"] for r in results) / len(results)
        table.add_row("", "", "", "", "", end_section=True)
        table.add_row("[bold]average[/bold]", f"[bold]{avg_tps:.1f}[/bold]", f"{avg_ttft:.2f}s", "", "")
    console.print()
    console.print(table)


def display_comparison(results_by_model: Dict[str, List[dict]]) -> None:
    models = list(results_by_model.keys())
    table = Table(title="Benchmark Comparison")
    table.add_column("Prompt", style="cyan")
    for model in models:
        table.add_column(f"{model} tok/s", justify="right", style="bold green")
        table.add_column(f"{model} TTFT", justify="right", style="dim")
    for pname in [p["name"] for p in BENCHMARK_PROMPTS]:
        row: List[str] = [pname]
        for model in models:
            result = next((r for r in results_by_model[model] if r["prompt"] == pname), None)
            if result:
                row.append(f"{result['tokens_per_second']:.1f}")
                row.append(f"{result['time_to_first_token']:.2f}s")
            else:
                row.extend(["-", "-"])
        table.add_row(*row)
    console.print()
    console.print(table)


def save_results(model: str, data: dict) -> Path:
    BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = BENCHMARKS_DIR / f"{model}-{date_str}.json"
    path.write_text(json.dumps(data, indent=2))
    return path


def load_latest_result(model: str) -> Optional[dict]:
    if not BENCHMARKS_DIR.exists():
        return None
    files = sorted(BENCHMARKS_DIR.glob(f"{model}-*.json"), reverse=True)
    if not files:
        return None
    return json.loads(files[0].read_text())
