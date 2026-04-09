"""
Server — start bitnet.cpp's built-in server for a model.

bitnet.cpp (via llama.cpp) includes a server binary that provides
an OpenAI-compatible API out of the box. This module manages
starting and stopping that server process.
"""

import signal
import subprocess
import sys
import time
from pathlib import Path

from rich.console import Console

from bitnet_hub.builder import get_server_binary, get_inference_binary, is_bitnet_cpp_built
from bitnet_hub.config import DEFAULT_HOST, DEFAULT_PORT
from bitnet_hub.downloader import get_model_gguf_path, is_model_downloaded

console = Console()


def start_server(
    model_name: str,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    threads: int = 2,
    context_size: int = 2048,
) -> None:
    """
    Start the bitnet.cpp server for a given model.

    This blocks until the server is stopped (Ctrl+C).

    Args:
        model_name: Short name from registry
        host: Address to bind to
        port: Port to listen on
        threads: Number of CPU threads
        context_size: Context window size in tokens
    """
    # Pre-flight checks
    if not is_bitnet_cpp_built():
        console.print("[red]bitnet.cpp is not built yet.[/red]")
        console.print("Run [bold]bitnet-hub setup[/bold] first to clone and build the engine.")
        raise SystemExit(1)

    if not is_model_downloaded(model_name):
        console.print(f"[red]Model {model_name} is not downloaded.[/red]")
        console.print(f"Run [bold]bitnet-hub pull {model_name}[/bold] first.")
        raise SystemExit(1)

    gguf_path = get_model_gguf_path(model_name)
    if not gguf_path:
        console.print(f"[red]Could not find GGUF file for {model_name}.[/red]")
        raise SystemExit(1)

    # Find the server binary (prefer llama-server, fall back to llama-cli --server)
    server_bin = get_server_binary()
    cli_bin = get_inference_binary()

    if server_bin:
        cmd = [
            str(server_bin),
            "-m", str(gguf_path),
            "--host", host,
            "--port", str(port),
            "-t", str(threads),
            "-c", str(context_size),
        ]
    elif cli_bin:
        # Fallback: use llama-cli in server mode if available
        cmd = [
            str(cli_bin),
            "-m", str(gguf_path),
            "--host", host,
            "--port", str(port),
            "-t", str(threads),
            "-c", str(context_size),
            "--server",
        ]
    else:
        console.print("[red]No server binary found.[/red]")
        console.print("bitnet.cpp may not have built correctly.")
        console.print("Run [bold]bitnet-hub setup --force[/bold] to rebuild.")
        raise SystemExit(1)

    # Launch
    console.print(f"\n[bold green]Starting bitnet-hub server[/bold green]")
    console.print(f"  Model:    {model_name}")
    console.print(f"  GGUF:     {gguf_path.name}")
    console.print(f"  Address:  http://{host}:{port}")
    console.print(f"  Threads:  {threads}")
    console.print(f"  Context:  {context_size} tokens")
    console.print()
    console.print(f"  [bold]OpenAI-compatible endpoint:[/bold]")
    console.print(f"  http://{host}:{port}/v1/chat/completions")
    console.print()
    console.print("[dim]Press Ctrl+C to stop the server[/dim]\n")

    # Run the server process, forwarding output
    try:
        process = subprocess.Popen(
            cmd,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

        # Wait for the process, handling Ctrl+C gracefully
        process.wait()

    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down server...[/yellow]")
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        console.print("[green]Server stopped.[/green]")

    except Exception as e:
        console.print(f"[red]Server error: {e}[/red]")
        raise SystemExit(1)


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
    if not is_bitnet_cpp_built():
        console.print("[red]bitnet.cpp is not built yet.[/red]")
        console.print("Run [bold]bitnet-hub setup[/bold] first.")
        raise SystemExit(1)

    if not is_model_downloaded(model_name):
        console.print(f"[red]Model {model_name} is not downloaded.[/red]")
        console.print(f"Run [bold]bitnet-hub pull {model_name}[/bold] first.")
        raise SystemExit(1)

    gguf_path = get_model_gguf_path(model_name)
    if not gguf_path:
        console.print(f"[red]Could not find GGUF file for {model_name}.[/red]")
        raise SystemExit(1)

    cli_bin = get_inference_binary()
    if not cli_bin:
        console.print("[red]No inference binary found.[/red]")
        raise SystemExit(1)

    console.print(f"\n[bold green]Chat with {model_name}[/bold green]")
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
    except KeyboardInterrupt:
        console.print("\n[green]Chat ended.[/green]")
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
