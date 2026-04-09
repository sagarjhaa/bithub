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


@cli.command()
@click.argument("model_name")
def pull(model_name):
    """Download a BitNet model.

    Example: bitnet-hub pull 2B-4T
    """
    info = get_model_info(model_name)
    if not info:
        console.print(f"[red]Unknown model: {model_name}[/red]")
        console.print("Run [bold]bitnet-hub models[/bold] to see available models.")
        return

    console.print(f"[bold]Pulling {info['name']}[/bold] ({info['parameters']} parameters, ~{info['size_mb']}MB)")
    # TODO Phase 2: implement download via huggingface-hub
    console.print("[yellow]Download not yet implemented — coming in Phase 2[/yellow]")


@cli.command()
@click.argument("model_name")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=8080, help="Port to listen on")
@click.option("--threads", "-t", default=2, help="Number of CPU threads")
def serve(model_name, host, port, threads):
    """Start an OpenAI-compatible API server for a model.

    Example: bitnet-hub serve 2B-4T
    """
    info = get_model_info(model_name)
    if not info:
        console.print(f"[red]Unknown model: {model_name}[/red]")
        return

    console.print(f"[bold]Serving {info['name']}[/bold] on http://{host}:{port}")
    # TODO Phase 3: start bitnet.cpp server + FastAPI wrapper
    console.print("[yellow]Server not yet implemented — coming in Phase 3[/yellow]")


@cli.command()
@click.argument("model_name")
@click.option("--threads", "-t", default=2, help="Number of CPU threads")
def run(model_name, threads):
    """Chat with a model in your terminal.

    Example: bitnet-hub run 2B-4T
    """
    info = get_model_info(model_name)
    if not info:
        console.print(f"[red]Unknown model: {model_name}[/red]")
        return

    console.print(f"[bold]Starting chat with {info['name']}[/bold]")
    console.print("Type 'exit' or Ctrl+C to quit.\n")
    # TODO Phase 4: implement interactive chat
    console.print("[yellow]Chat not yet implemented — coming in Phase 4[/yellow]")


@cli.command("list")
def list_models():
    """Show installed models."""
    # TODO Phase 2: check which models are actually downloaded
    console.print("[yellow]Installed model tracking not yet implemented.[/yellow]")
    console.print("Showing all models from the registry instead:\n")
    _print_registry()


@cli.command()
def models():
    """Show all available BitNet models in the registry."""
    _print_registry()


@cli.command()
@click.argument("model_name")
def rm(model_name):
    """Remove a downloaded model.

    Example: bitnet-hub rm 2B-4T
    """
    info = get_model_info(model_name)
    if not info:
        console.print(f"[red]Unknown model: {model_name}[/red]")
        return

    # TODO Phase 4: implement model removal
    console.print("[yellow]Removal not yet implemented — coming in Phase 4[/yellow]")


def _print_registry():
    """Pretty-print the model registry as a table."""
    table = Table(title="Available BitNet Models")
    table.add_column("Name", style="bold cyan")
    table.add_column("Parameters", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("Description")

    for short_name, info in list_available_models().items():
        table.add_row(
            short_name,
            info["parameters"],
            f"~{info['size_mb']}MB",
            info["description"],
        )

    console.print(table)


if __name__ == "__main__":
    cli()
