"""CLI entry point for bitnet-hub."""

import click
from rich.console import Console
from rich.table import Table

from bitnet_hub import __version__
from bitnet_hub.registry import list_available_models, get_model_info

console = Console()


@click.group()
@click.version_option(version=__version__)
def cli():
    """bitnet-hub — Ollama for 1-bit LLMs.

    Download, manage, and serve BitNet models with a single command.
    """
    pass


# ──────────────────────────────────────────────────────────────
# Model management
# ──────────────────────────────────────────────────────────────


@cli.command()
@click.argument("model_name")
@click.option("--force", is_flag=True, help="Re-download even if already present")
def pull(model_name, force):
    """Download a BitNet model from HuggingFace.

    Example: bitnet-hub pull 2B-4T
    """
    from bitnet_hub.downloader import download_model
    download_model(model_name, force=force)


@cli.command()
@click.option("--force", is_flag=True, help="Re-clone and rebuild from scratch")
def setup(force):
    """Clone and build bitnet.cpp (the inference engine).

    This downloads and compiles Microsoft's bitnet.cpp so you can
    run models locally. Only needs to be done once.

    Example: bitnet-hub setup
    """
    from bitnet_hub.builder import setup_bitnet_cpp
    success = setup_bitnet_cpp(force=force)
    if not success:
        raise SystemExit(1)


# ──────────────────────────────────────────────────────────────
# Serve and run
# ──────────────────────────────────────────────────────────────


@cli.command()
@click.argument("model_name")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=8080, help="Port to listen on")
@click.option("--threads", "-t", default=2, help="Number of CPU threads")
@click.option("--context-size", "-c", default=2048, help="Context window size")
def serve(model_name, host, port, threads, context_size):
    """Start an OpenAI-compatible API server for a model.

    Example: bitnet-hub serve 2B-4T
    """
    from bitnet_hub.server import start_server
    start_server(model_name, host=host, port=port, threads=threads, context_size=context_size)


@cli.command()
@click.argument("model_name")
@click.option("--threads", "-t", default=2, help="Number of CPU threads")
@click.option("--context-size", "-c", default=2048, help="Context window size")
def run(model_name, threads, context_size):
    """Chat with a model in your terminal.

    Example: bitnet-hub run 2B-4T
    """
    from bitnet_hub.server import run_interactive
    run_interactive(model_name, threads=threads, context_size=context_size)


# ──────────────────────────────────────────────────────────────
# Model listing and status
# ──────────────────────────────────────────────────────────────


@cli.command("list")
def list_models():
    """Show downloaded models."""
    from bitnet_hub.downloader import get_downloaded_models

    downloaded = get_downloaded_models()
    if not downloaded:
        console.print("[yellow]No models downloaded yet.[/yellow]")
        console.print("Run [bold]bitnet-hub models[/bold] to see available models.")
        console.print("Run [bold]bitnet-hub pull <name>[/bold] to download one.")
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
    from bitnet_hub.downloader import is_model_downloaded

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


@cli.command()
@click.argument("model_name")
@click.confirmation_option(prompt="Are you sure you want to remove this model?")
def rm(model_name):
    """Remove a downloaded model.

    Example: bitnet-hub rm 2B-4T
    """
    from bitnet_hub.downloader import remove_model

    if remove_model(model_name):
        console.print(f"[green]Removed {model_name}.[/green]")
    else:
        console.print(f"[yellow]Model {model_name} is not downloaded.[/yellow]")


@cli.command()
def status():
    """Show the current state of bitnet-hub.

    Reports on the inference engine build status and downloaded models.
    """
    from bitnet_hub.builder import is_bitnet_cpp_built, get_inference_binary, get_server_binary
    from bitnet_hub.downloader import get_downloaded_models
    from bitnet_hub.config import BITNET_HUB_HOME, MODELS_DIR, BITNET_CPP_DIR

    console.print(f"\n[bold]bitnet-hub v{__version__}[/bold]\n")

    # Paths
    console.print(f"  Home:       {BITNET_HUB_HOME}")
    console.print(f"  Models:     {MODELS_DIR}")
    console.print(f"  Engine:     {BITNET_CPP_DIR}")

    # Engine status
    if is_bitnet_cpp_built():
        cli_bin = get_inference_binary()
        srv_bin = get_server_binary()
        console.print(f"\n  [green]Engine:     Built[/green]")
        if cli_bin:
            console.print(f"    CLI:      {cli_bin}")
        if srv_bin:
            console.print(f"    Server:   {srv_bin}")
    else:
        console.print(f"\n  [yellow]Engine:     Not built[/yellow]")
        console.print("    Run [bold]bitnet-hub setup[/bold] to build it.")

    # Downloaded models
    downloaded = get_downloaded_models()
    console.print(f"\n  Models:     {len(downloaded)} downloaded")
    for m in downloaded:
        console.print(f"    [cyan]{m['name']}[/cyan] ({m['size_mb']} MB)")

    console.print()


if __name__ == "__main__":
    cli()
