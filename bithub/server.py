"""
Server — start bithub with an OpenAI-compatible API.

Two modes:
  1. `serve` — starts a FastAPI server that proxies to the bitnet.cpp
     backend, providing /v1/chat/completions and /v1/models.
  2. `run` — interactive terminal chat via llama-cli.
"""

import signal
import subprocess
import threading
from pathlib import Path
from typing import List, Optional

import httpx
from rich.console import Console

from bithub.builder import get_inference_binary, is_bitnet_cpp_built
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
    model_names: Optional[List[str]] = None,
    model_name: Optional[str] = None,  # backwards compat
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    threads: int = 2,
    context_size: int = 2048,
    lazy: bool = False,
) -> None:
    """
    Start the bithub API server with one or more models.

    This provides OpenAI-compatible endpoints:
        GET  /v1/models
        POST /v1/chat/completions (streaming + non-streaming)
        GET  /health

    Args:
        model_names: List of short names from registry
        model_name: Single model name (backwards compat)
        host: Address to bind to
        port: Port to listen on
        threads: Number of CPU threads per model
        context_size: Context window size in tokens
        lazy: If True, only load models on first request
    """
    # Handle both old and new calling conventions
    if model_names is None:
        if model_name:
            model_names = [model_name]
        else:
            console.print("[red]No models specified.[/red]")
            raise SystemExit(1)

    import uvicorn

    from bithub.api import create_app
    from bithub.model_manager import ModelManager

    backend_base_port = port + 1
    manager = ModelManager(base_port=backend_base_port, max_models=len(model_names))

    for name in model_names:
        gguf_path = _preflight_check(name)
        manager.register(name, gguf_path, threads=threads, context_size=context_size)

    console.print("\n[bold green]Starting bithub server[/bold green]")
    for name in model_names:
        info = get_model_info(name)
        display_name = info["name"] if info else name
        console.print(f"  Model:    {display_name}")
    console.print(f"  Address:  http://{host}:{port}")
    console.print(f"  Threads:  {threads} per model")
    if len(model_names) > 1:
        console.print(f"  Mode:     {'lazy' if lazy else 'eager'} loading")
    console.print()
    console.print("[dim]Press Ctrl+C to stop the server[/dim]\n")

    app = create_app(
        model_name=model_names[0],
        gguf_path=_preflight_check(model_names[0]),
        manager=manager,
    )

    try:
        uvicorn.run(app, host=host, port=port, log_level="warning")
    except KeyboardInterrupt:
        console.print("\n[green]Server stopped.[/green]")


def start_background_server(
    model_name: str,
    host: str = "127.0.0.1",
    port: int = 8081,
    threads: int = 2,
    context_size: int = 2048,
) -> threading.Thread:
    """Start the API server in a background thread for REPL use."""
    gguf_path = _preflight_check(model_name)

    import uvicorn

    from bithub.api import create_app

    backend_port = port + 1
    app = create_app(
        model_name=model_name,
        gguf_path=gguf_path,
        threads=threads,
        context_size=context_size,
        backend_port=backend_port,
    )

    server_thread = threading.Thread(
        target=uvicorn.run,
        kwargs={"app": app, "host": host, "port": port, "log_level": "error"},
        daemon=True,
    )
    server_thread.start()
    return server_thread


def wait_for_server(url: str, timeout: float = 30.0) -> bool:
    """Wait for the API server to become ready."""
    import time
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = httpx.get(f"{url}/health", timeout=2.0)
            if resp.status_code == 200:
                return True
        except (httpx.ConnectError, httpx.ReadTimeout):
            pass
        time.sleep(0.5)
    return False


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
