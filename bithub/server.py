"""
Server — start bithub with an OpenAI-compatible API.

Two modes:
  1. `serve` — starts a FastAPI server that proxies to the bitnet.cpp
     backend, providing /v1/chat/completions and /v1/models.
  2. `run` — interactive terminal chat via llama-cli.
"""

import signal
import subprocess
import sys
from pathlib import Path

from rich.console import Console

from bithub.builder import get_server_binary, get_inference_binary, is_bitnet_cpp_built
from bithub.config import DEFAULT_HOST, DEFAULT_PORT
from bithub.downloader import get_model_gguf_path, is_model_downloaded
from bithub.registry import get_model_info

console = Console()


def _preflight_check(model_name: str) -> Path:
    """
    Run common checks before serving or chatting.
    Returns the GGUF path on success, exits on failure.
    """
    if not is_bitnet_cpp_built():
        console.print("[red]bitnet.cpp is not built yet.[/red]")
        console.print("Run [bold]bithub setup[/bold] first to clone and build the engine.")
        raise SystemExit(1)

    if not is_model_downloaded(model_name):
        console.print(f"[red]Model {model_name} is not downloaded.[/red]")
        console.print(f"Run [bold]bithub pull {model_name}[/bold] first.")
        raise SystemExit(1)

    gguf_path = get_model_gguf_path(model_name)
    if not gguf_path:
        console.print(f"[red]Could not find GGUF file for {model_name}.[/red]")
        raise SystemExit(1)

    return gguf_path


def start_server(
    model_name: str,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    threads: int = 2,
    context_size: int = 2048,
) -> None:
    """
    Start the bithub API server (FastAPI + bitnet.cpp backend).

    This provides OpenAI-compatible endpoints:
        GET  /v1/models
        POST /v1/chat/completions (streaming + non-streaming)
        GET  /health

    Args:
        model_name: Short name from registry
        host: Address to bind to
        port: Port to listen on
        threads: Number of CPU threads
        context_size: Context window size in tokens
    """
    gguf_path = _preflight_check(model_name)

    # Get model info for display
    info = get_model_info(model_name)
    display_name = info["name"] if info else model_name

    console.print(f"\n[bold green]Starting bithub server[/bold green]")
    console.print(f"  Model:    {display_name}")
    console.print(f"  GGUF:     {gguf_path.name}")
    console.print(f"  Address:  http://{host}:{port}")
    console.print(f"  Threads:  {threads}")
    console.print(f"  Context:  {context_size} tokens")
    console.print()
    console.print(f"  [bold]Endpoints:[/bold]")
    console.print(f"    POST http://{host}:{port}/v1/chat/completions")
    console.print(f"    GET  http://{host}:{port}/v1/models")
    console.print(f"    GET  http://{host}:{port}/health")
    console.print()
    console.print("  [bold]Connect from Python:[/bold]")
    console.print(f'    client = openai.OpenAI(base_url="http://{host}:{port}/v1", api_key="not-needed")')
    console.print()
    console.print("[dim]Press Ctrl+C to stop the server[/dim]\n")

    # Use the internal backend port (one above the user-facing port)
    backend_port = port + 1

    # Create and run the FastAPI app
    from bithub.api import create_app
    import uvicorn

    app = create_app(
        model_name=model_name,
        gguf_path=gguf_path,
        threads=threads,
        context_size=context_size,
        backend_port=backend_port,
    )

    try:
        uvicorn.run(app, host=host, port=port, log_level="warning")
    except KeyboardInterrupt:
        console.print("\n[green]Server stopped.[/green]")


def run_interactive(
    model_name: str,
    threads: int = 2,
    context_size: int = 2048,
) -> None:
    """
    Run interactive chat with a model in the terminal.

    Uses llama-cli in interactive/conversation mode.

    Args:
        model_name: Short name from registry
        threads: Number of CPU threads
        context_size: Context window size
    """
    gguf_path = _preflight_check(model_name)

    cli_bin = get_inference_binary()
    if not cli_bin:
        console.print("[red]No inference binary found.[/red]")
        raise SystemExit(1)

    info = get_model_info(model_name)
    display_name = info["name"] if info else model_name

    console.print(f"\n[bold green]Chat with {display_name}[/bold green]")
    console.print(f"  Using: {gguf_path.name}")
    console.print(f"  Threads: {threads}")
    console.print("[dim]Press Ctrl+C to exit[/dim]\n")

    cmd = [
        str(cli_bin),
        "-m", str(gguf_path),
        "-t", str(threads),
        "-c", str(context_size),
        "--interactive",
        "--color",
    ]

    try:
        process = subprocess.Popen(cmd)
        process.wait()
        if process.returncode != 0:
            console.print(
                f"\n[red]Process exited with code {process.returncode}.[/red] "
                f"Run [bold]bithub status[/bold] to check your setup."
            )
    except FileNotFoundError:
        console.print(
            "[red]Inference binary not found.[/red] "
            "Run [bold]bithub setup[/bold] to rebuild."
        )
        raise SystemExit(1)
    except KeyboardInterrupt:
        console.print("\n[green]Chat ended.[/green]")
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
