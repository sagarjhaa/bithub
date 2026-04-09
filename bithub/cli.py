"""CLI entry point for bithub."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from bithub import __version__
from bithub.config import get_default_threads
from bithub.registry import list_available_models, get_model_info

console = Console()

# Auto-detect a sensible thread count
_DEFAULT_THREADS = get_default_threads()


def _suggest_model(model_name: str) -> None:
    """When a model name isn't found, suggest close matches."""
    available = list(list_available_models().keys())

    # Simple substring match
    suggestions = [m for m in available if model_name.lower() in m.lower()]
    if not suggestions:
        # Try the other direction
        suggestions = [m for m in available if m.lower() in model_name.lower()]

    console.print(f"[red]Unknown model:[/red] {model_name}")
    if suggestions:
        console.print(f"  Did you mean: [bold cyan]{suggestions[0]}[/bold cyan]?")
    console.print("  Run [bold]bithub models[/bold] to see all available models.")


def _ensure_engine_ready() -> bool:
    """Check if the engine is built. If not, offer to set it up."""
    from bithub.builder import is_bitnet_cpp_built

    if is_bitnet_cpp_built():
        return True

    console.print("[yellow]The bitnet.cpp engine is not built yet.[/yellow]")

    if click.confirm("  Would you like to set it up now?", default=True):
        from bithub.builder import setup_bitnet_cpp
        return setup_bitnet_cpp()
    else:
        console.print("  Run [bold]bithub setup[/bold] when you're ready.")
        return False


def _ensure_model_ready(model_name: str) -> bool:
    """Check if a model is downloaded. If not, offer to pull it."""
    from bithub.downloader import is_model_downloaded

    if is_model_downloaded(model_name):
        return True

    info = get_model_info(model_name)
    if not info:
        _suggest_model(model_name)
        return False

    console.print(f"[yellow]Model {model_name} is not downloaded yet.[/yellow]")
    console.print(f"  ({info['name']}, {info['parameters']} params, ~{info['size_mb']}MB)")

    if click.confirm("  Would you like to download it now?", default=True):
        from bithub.downloader import download_model
        try:
            download_model(model_name)
            return True
        except SystemExit:
            return False
    else:
        console.print(f"  Run [bold]bithub pull {model_name}[/bold] when you're ready.")
        return False


# ──────────────────────────────────────────────────────────────
# Main CLI group
# ──────────────────────────────────────────────────────────────


@click.group()
@click.version_option(version=__version__)
@click.option("--debug", is_flag=True, hidden=True, help="Enable debug logging")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx, debug, verbose):
    """bithub — Ollama for 1-bit LLMs.

    Download, manage, and serve BitNet models with a single command.

    \b
    Quick start:
        bithub setup            # one-time engine build
        bithub pull 2B-4T       # download a model
        bithub serve 2B-4T      # start OpenAI-compatible API
        bithub run 2B-4T        # chat in terminal
    """
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    ctx.obj["verbose"] = verbose
    from bithub.logging_setup import setup_logging
    setup_logging(debug=debug, verbose=verbose)


# ──────────────────────────────────────────────────────────────
# Model management
# ──────────────────────────────────────────────────────────────


@cli.command()
@click.argument("model_name")
@click.option("--force", is_flag=True, help="Re-download even if already present")
def pull(model_name, force):
    """Download a BitNet model from HuggingFace.

    \b
    Examples:
        bithub pull 2B-4T           # Microsoft's flagship 2B model
        bithub pull falcon3-1B      # Smallest Falcon3 model
        bithub pull 700M            # Tiny model for quick testing
        bithub pull 2B-4T --force   # Re-download
    """
    info = get_model_info(model_name)
    if not info:
        _suggest_model(model_name)
        raise SystemExit(1)

    from bithub.downloader import download_model
    download_model(model_name, force=force)


@cli.command()
@click.option("--force", is_flag=True, help="Re-clone and rebuild from scratch")
def setup(force):
    """Clone and build bitnet.cpp (the inference engine).

    Only needs to be done once. Downloads Microsoft's bitnet.cpp and
    compiles it for your system.

    \b
    Requirements: git, cmake, clang
        macOS:   brew install cmake llvm git
        Ubuntu:  sudo apt install cmake clang git
    """
    from bithub.builder import setup_bitnet_cpp
    success = setup_bitnet_cpp(force=force)
    if success:
        console.print("\n[bold green]You're all set![/bold green] Next steps:")
        console.print("  1. [bold]bithub pull 2B-4T[/bold]    — download a model")
        console.print("  2. [bold]bithub serve 2B-4T[/bold]   — start the API server")
        console.print("  3. [bold]bithub run 2B-4T[/bold]     — chat in terminal")
    else:
        raise SystemExit(1)


# ──────────────────────────────────────────────────────────────
# Serve and run
# ──────────────────────────────────────────────────────────────


@cli.command()
@click.argument("model_name")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=8080, help="Port to listen on")
@click.option("--threads", "-t", default=_DEFAULT_THREADS, show_default=True,
              help="Number of CPU threads")
@click.option("--context-size", "-c", default=2048, show_default=True,
              help="Context window size")
def serve(model_name, host, port, threads, context_size):
    """Start an OpenAI-compatible API server for a model.

    Any app that speaks the OpenAI API can connect — Open WebUI,
    Cursor, or your own scripts.

    \b
    Examples:
        bithub serve 2B-4T
        bithub serve 2B-4T --port 9000
        bithub serve falcon3-3B -t 4 -c 4096
    """
    if not _ensure_engine_ready():
        raise SystemExit(1)
    if not _ensure_model_ready(model_name):
        raise SystemExit(1)

    from bithub.server import start_server
    start_server(model_name, host=host, port=port, threads=threads,
                 context_size=context_size)


@cli.command()
@click.argument("model_name")
@click.option("--threads", "-t", default=_DEFAULT_THREADS, show_default=True,
              help="Number of CPU threads")
@click.option("--context-size", "-c", default=2048, show_default=True,
              help="Context window size")
def run(model_name, threads, context_size):
    """Chat with a model in your terminal.

    \b
    Examples:
        bithub run 2B-4T
        bithub run falcon3-3B -t 4
    """
    if not _ensure_engine_ready():
        raise SystemExit(1)
    if not _ensure_model_ready(model_name):
        raise SystemExit(1)

    from bithub.server import run_interactive
    run_interactive(model_name, threads=threads, context_size=context_size)


# ──────────────────────────────────────────────────────────────
# Model listing and status
# ──────────────────────────────────────────────────────────────


@cli.command("list")
def list_models():
    """Show downloaded models."""
    from bithub.downloader import get_downloaded_models

    downloaded = get_downloaded_models()
    if not downloaded:
        console.print("[yellow]No models downloaded yet.[/yellow]\n")
        console.print("  Get started:")
        console.print("    [bold]bithub pull 2B-4T[/bold]    — Microsoft's flagship (recommended)")
        console.print("    [bold]bithub pull 700M[/bold]     — smallest, great for testing")
        console.print("    [bold]bithub models[/bold]        — see all available models")
        return

    table = Table(title="Downloaded Models")
    table.add_column("Name", style="bold cyan")
    table.add_column("Size", justify="right")
    table.add_column("Path", style="dim")

    for m in downloaded:
        table.add_row(m["name"], f"{m['size_mb']} MB", m["path"])

    console.print(table)


@cli.command()
def models():
    """Show all available BitNet models in the registry."""
    from bithub.downloader import is_model_downloaded

    table = Table(title="Available BitNet Models")
    table.add_column("Name", style="bold cyan")
    table.add_column("Parameters", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("Status", justify="center")
    table.add_column("Description")

    for short_name, info in list_available_models().items():
        installed = is_model_downloaded(short_name)
        status = "[green]installed[/green]" if installed else "[dim]—[/dim]"
        table.add_row(
            short_name,
            info["parameters"],
            f"~{info['size_mb']}MB",
            status,
            info["description"],
        )

    console.print(table)
    console.print("\n  [dim]Tip: bithub pull <name> to download a model[/dim]")


@cli.command()
@click.argument("model_name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def rm(model_name, yes):
    """Remove a downloaded model.

    \b
    Examples:
        bithub rm 2B-4T
        bithub rm falcon3-3B -y    # skip confirmation
    """
    from bithub.downloader import is_model_downloaded, remove_model, get_model_gguf_path

    if not is_model_downloaded(model_name):
        console.print(f"[yellow]Model {model_name} is not downloaded.[/yellow]")
        return

    # Show what will be removed
    gguf_path = get_model_gguf_path(model_name)
    if gguf_path:
        size_mb = gguf_path.stat().st_size / (1024 * 1024)
        console.print(f"  Model: [bold]{model_name}[/bold]")
        console.print(f"  File:  {gguf_path.name}")
        console.print(f"  Size:  {size_mb:.0f} MB")

    if not yes and not click.confirm("\n  Remove this model?", default=False):
        console.print("  [dim]Cancelled.[/dim]")
        return

    if remove_model(model_name):
        console.print(f"[green]Removed {model_name}.[/green]")
    else:
        console.print(f"[red]Failed to remove {model_name}.[/red]")


@cli.command()
def status():
    """Show the current state of bithub."""
    from bithub.builder import is_bitnet_cpp_built, get_inference_binary, get_server_binary
    from bithub.downloader import get_downloaded_models
    from bithub.config import BITHUB_HOME, MODELS_DIR, BITNET_CPP_DIR, get_system_info

    sys_info = get_system_info()

    # Header
    console.print(Panel(
        f"[bold]bithub[/bold] v{__version__}\n"
        f"[dim]{sys_info['os']} {sys_info['arch']} / "
        f"Python {sys_info['python']} / "
        f"{sys_info['cpu_cores']} CPU cores[/dim]",
        border_style="blue",
    ))

    # Paths
    console.print(f"  Home:     [dim]{BITHUB_HOME}[/dim]")
    console.print(f"  Models:   [dim]{MODELS_DIR}[/dim]")
    console.print(f"  Engine:   [dim]{BITNET_CPP_DIR}[/dim]")

    # Engine status
    if is_bitnet_cpp_built():
        cli_bin = get_inference_binary()
        srv_bin = get_server_binary()
        console.print(f"\n  Engine:   [green]Built[/green]")
        if cli_bin:
            console.print(f"    CLI:    [dim]{cli_bin}[/dim]")
        if srv_bin:
            console.print(f"    Server: [dim]{srv_bin}[/dim]")
    else:
        console.print(f"\n  Engine:   [yellow]Not built[/yellow]")
        console.print("    Run [bold]bithub setup[/bold] to get started.")

    # Downloaded models
    downloaded = get_downloaded_models()
    total_size = sum(m["size_mb"] for m in downloaded)
    console.print(f"\n  Models:   {len(downloaded)} downloaded ({total_size} MB total)")
    for m in downloaded:
        console.print(f"    [cyan]{m['name']}[/cyan] ({m['size_mb']} MB)")

    if not downloaded:
        console.print("    [dim]Run bithub pull <name> to download a model[/dim]")

    console.print()


if __name__ == "__main__":
    cli()
