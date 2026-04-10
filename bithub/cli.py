"""CLI entry point for bithub."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from bithub import __version__
from bithub.config import get_default_threads
from bithub.registry import get_model_info, list_available_models

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
@click.option("--name", default=None, help="Short name for direct HF pulls")
def pull(model_name, force, name):
    """Download a BitNet model from HuggingFace.

    \b
    Examples:
        bithub pull 2B-4T                                 # from registry
        bithub pull falcon3-1B --force                     # re-download
        bithub pull hf:microsoft/BitNet-b1.58-2B-4T-gguf  # direct from HF
        bithub pull hf:user/custom-model --name mymodel    # with custom name
    """
    from bithub.downloader import download_direct_hf, is_direct_hf_pull, parse_hf_uri

    if is_direct_hf_pull(model_name):
        repo_id, default_name = parse_hf_uri(model_name)
        download_direct_hf(repo_id, name=name or default_name, force=force)
        return

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
@click.argument("model_names", nargs=-1, required=True)
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=8080, help="Port to listen on")
@click.option("--threads", "-t", default=_DEFAULT_THREADS, show_default=True,
              help="Number of CPU threads per model")
@click.option("--context-size", "-c", default=2048, show_default=True,
              help="Context window size")
@click.option("--lazy", is_flag=True, help="Only load models on first request")
def serve(model_names, host, port, threads, context_size, lazy):
    """Start an OpenAI-compatible API server.

    Accepts one or more model names. Requests are routed by the 'model'
    field in the API request.

    \b
    Examples:
        bithub serve 2B-4T
        bithub serve 2B-4T falcon3-3B
        bithub serve 2B-4T falcon3-3B --lazy
    """
    if not _ensure_engine_ready():
        raise SystemExit(1)

    for name in model_names:
        if not _ensure_model_ready(name):
            raise SystemExit(1)

    from bithub.server import start_server
    start_server(
        model_names=list(model_names),
        host=host, port=port,
        threads=threads, context_size=context_size,
        lazy=lazy,
    )


@cli.command()
@click.argument("model_name")
@click.option("--threads", "-t", default=_DEFAULT_THREADS, show_default=True,
              help="Number of CPU threads")
@click.option("--context-size", "-c", default=2048, show_default=True,
              help="Context window size")
@click.option("--port", default=8081, hidden=True, help="API server port for REPL backend")
def run(model_name, threads, context_size, port):
    """Chat with a model in your terminal.

    Starts a local API server in the background and opens an interactive
    chat session with markdown rendering, history, and slash commands.

    \b
    Examples:
        bithub run 2B-4T
        bithub run falcon3-3B -t 4

    \b
    Commands in chat:
        /help     Show commands
        /clear    Clear history
        /system   Set system prompt
        /export   Save conversation
        /quit     Exit
    """
    if not _ensure_engine_ready():
        raise SystemExit(1)
    if not _ensure_model_ready(model_name):
        raise SystemExit(1)

    from bithub.server import start_background_server, wait_for_server

    api_url = f"http://127.0.0.1:{port}"

    console.print("[dim]Starting local API server...[/dim]")
    start_background_server(
        model_name, host="127.0.0.1", port=port,
        threads=threads, context_size=context_size,
    )

    if not wait_for_server(api_url):
        console.print("[red]Server failed to start. Run bithub status for diagnostics.[/red]")
        raise SystemExit(1)

    console.print("[dim]Server ready.[/dim]\n")

    from bithub.repl import start_repl
    start_repl(model=model_name, api_url=api_url)


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
@click.argument("query")
@click.option("--limit", default=15, help="Number of results to show")
def search(query, limit):
    """Search Hugging Face for 1.58-bit models.

    Checks if results are compatible with the BitNet engine.
    """
    from huggingface_hub import HfApi
    from rich.table import Table

    console.print(f"\n[dim]Searching HuggingFace for '{query}'...[/dim]")

    try:
        api = HfApi()
        # Fetch search results sorted by downloads
        models_data = list(api.list_models(
            search=query,
            sort="downloads",
            direction=-1,
            limit=limit * 3  # Fetch extra to filter
        ))
    except Exception as e:
        console.print(f"[red]Search failed: {e}[/red]")
        raise SystemExit(1)

    table = Table(title=f"Search Results for '{query}'")
    table.add_column("Repository", style="bold cyan")
    table.add_column("Downloads", justify="right")
    table.add_column("Compatible?", justify="center")

    shown = 0
    for m in models_data:
        tags = [t.lower() for t in (m.tags or [])]
        name = m.id.lower()

        # Heuristic 1.58-bit / bitnet compatibility detection
        is_compatible = False
        if "bitnet" in tags or "1.58bit" in tags or "1.58-bit" in tags:
            is_compatible = True
        elif "1.58" in name or "bitnet" in name or "i2_s" in name:
            is_compatible = True
        # If it's a known non-quantized repo with 1.58bit, we allow testing it
        # However if it explicitly doesn't have gguf/i2_s we can't definitively say

        comp_str = "[green]Yes[/green]" if is_compatible else "[dim]Unknown[/dim]"

        table.add_row(m.id, f"{m.downloads:,}", comp_str)
        shown += 1
        if shown >= limit:
            break

    if shown == 0:
        console.print(f"[yellow]No models found matching '{query}'.[/yellow]")
        return

    console.print(table)
    console.print("\n  [dim]To test a compatible model, use the direct pull tag:[/dim]")
    console.print("  [bold]bithub pull hf:<repository>[/bold]\n")


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
    from bithub.downloader import get_model_gguf_path, is_model_downloaded, remove_model

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
@click.argument("model_names", nargs=-1, required=True)
@click.option("--port", default=8090, hidden=True, help="Port for benchmark server")
@click.option("--threads", "-t", default=_DEFAULT_THREADS, show_default=True,
              help="Number of CPU threads")
@click.option("--context-size", "-c", default=2048, show_default=True,
              help="Context window size")
@click.option("--json-output", "--json", "json_output", is_flag=True, help="Output results as JSON")
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

    from bithub.bench import (
        display_comparison,
        display_results,
        run_benchmark,
        save_results,
    )
    from bithub.server import start_background_server, wait_for_server

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


@cli.command()
def status():
    """Show the current state of bithub."""
    from bithub.builder import get_inference_binary, get_server_binary, is_bitnet_cpp_built
    from bithub.config import BITHUB_HOME, BITNET_CPP_DIR, MODELS_DIR, get_system_info
    from bithub.downloader import get_downloaded_models

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
        console.print("\n  Engine:   [green]Built[/green]")
        if cli_bin:
            console.print(f"    CLI:    [dim]{cli_bin}[/dim]")
        if srv_bin:
            console.print(f"    Server: [dim]{srv_bin}[/dim]")
    else:
        console.print("\n  Engine:   [yellow]Not built[/yellow]")
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
