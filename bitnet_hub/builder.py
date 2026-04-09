"""
Model builder — clone and build bitnet.cpp for local inference.

bitnet.cpp is Microsoft's inference engine optimized for 1-bit LLMs.
This module handles cloning the repo and running the build process,
so the user doesn't have to do it manually.
"""

import subprocess
import sys
from pathlib import Path

from rich.console import Console

from bitnet_hub.config import BITNET_CPP_DIR, ensure_dirs

console = Console()

BITNET_CPP_REPO = "https://github.com/microsoft/BitNet.git"


def is_bitnet_cpp_built() -> bool:
    """Check if bitnet.cpp is already cloned and built."""
    # The build produces a binary at build/bin/llama-cli (or similar)
    build_dir = BITNET_CPP_DIR / "build"
    if not build_dir.exists():
        return False

    # Look for the inference binary
    inference_bin = _find_inference_binary()
    return inference_bin is not None


def _find_inference_binary() -> Path | None:
    """Find the bitnet.cpp inference binary."""
    candidates = [
        BITNET_CPP_DIR / "build" / "bin" / "llama-cli",
        BITNET_CPP_DIR / "build" / "bin" / "main",
        BITNET_CPP_DIR / "build" / "bin" / "llama-server",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def _find_server_binary() -> Path | None:
    """Find the bitnet.cpp server binary specifically."""
    candidates = [
        BITNET_CPP_DIR / "build" / "bin" / "llama-server",
        BITNET_CPP_DIR / "build" / "bin" / "server",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def get_inference_binary() -> Path | None:
    """Return path to the inference CLI binary, or None if not built."""
    return _find_inference_binary()


def get_server_binary() -> Path | None:
    """Return path to the server binary, or None if not built."""
    return _find_server_binary()


def _run_command(cmd: list[str], cwd: Path | None = None, desc: str = "") -> bool:
    """Run a shell command with live output."""
    if desc:
        console.print(f"  [dim]{desc}[/dim]")

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=False,
            text=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Command failed (exit code {e.returncode}): {' '.join(cmd)}[/red]")
        return False
    except FileNotFoundError:
        console.print(f"[red]Command not found: {cmd[0]}[/red]")
        console.print("Make sure required build tools are installed (cmake, clang, git).")
        return False


def _check_prerequisites() -> list[str]:
    """Check for required build tools and return list of missing ones."""
    missing = []
    for tool in ["git", "cmake", "python3"]:
        try:
            subprocess.run(
                [tool, "--version"],
                capture_output=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append(tool)
    return missing


def clone_bitnet_cpp(force: bool = False) -> bool:
    """
    Clone the bitnet.cpp repository.

    Args:
        force: If True, remove and re-clone.

    Returns:
        True if successful.
    """
    ensure_dirs()

    if BITNET_CPP_DIR.exists() and not force:
        console.print("[green]bitnet.cpp already cloned.[/green]")
        return True

    if BITNET_CPP_DIR.exists() and force:
        import shutil
        console.print("[yellow]Removing existing bitnet.cpp clone...[/yellow]")
        shutil.rmtree(BITNET_CPP_DIR)

    console.print(f"\n[bold]Cloning bitnet.cpp[/bold]")
    console.print(f"  From: {BITNET_CPP_REPO}")
    console.print(f"  To:   {BITNET_CPP_DIR}\n")

    return _run_command(
        ["git", "clone", "--recursive", BITNET_CPP_REPO, str(BITNET_CPP_DIR)],
        desc="git clone --recursive ...",
    )


def build_bitnet_cpp() -> bool:
    """
    Build bitnet.cpp using its setup_env.py script.

    The setup_env.py script in bitnet.cpp handles:
    - Installing Python dependencies
    - Running cmake configure
    - Building the project

    Returns:
        True if successful.
    """
    if not BITNET_CPP_DIR.exists():
        console.print("[red]bitnet.cpp not cloned. Run clone first.[/red]")
        return False

    setup_script = BITNET_CPP_DIR / "setup_env.py"

    if setup_script.exists():
        console.print("\n[bold]Building bitnet.cpp via setup_env.py[/bold]\n")
        return _run_command(
            [sys.executable, str(setup_script), "-md", "dummy"],
            cwd=BITNET_CPP_DIR,
            desc="python setup_env.py ...",
        )
    else:
        # Fallback: manual cmake build
        console.print("\n[bold]Building bitnet.cpp via cmake[/bold]\n")
        build_dir = BITNET_CPP_DIR / "build"
        build_dir.mkdir(exist_ok=True)

        success = _run_command(
            ["cmake", "..", "-DCMAKE_BUILD_TYPE=Release"],
            cwd=build_dir,
            desc="cmake configure ...",
        )
        if not success:
            return False

        return _run_command(
            ["cmake", "--build", ".", "--config", "Release", "-j"],
            cwd=build_dir,
            desc="cmake build ...",
        )


def setup_bitnet_cpp(force: bool = False) -> bool:
    """
    Full setup: check prerequisites, clone, and build bitnet.cpp.

    This is the main entry point — it does everything needed to get
    the inference engine ready.

    Returns:
        True if the engine is ready to use.
    """
    # Check if already built
    if not force and is_bitnet_cpp_built():
        binary = get_inference_binary()
        console.print(f"[green]bitnet.cpp already built:[/green] {binary}")
        return True

    # Check prerequisites
    console.print("[bold]Checking build prerequisites...[/bold]")
    missing = _check_prerequisites()
    if missing:
        console.print(f"[red]Missing required tools: {', '.join(missing)}[/red]")
        console.print("\nInstall them first:")
        console.print("  macOS:  brew install cmake llvm git")
        console.print("  Ubuntu: sudo apt install cmake clang git")
        return False
    console.print("[green]All prerequisites found.[/green]")

    # Clone
    if not clone_bitnet_cpp(force=force):
        return False

    # Build
    if not build_bitnet_cpp():
        return False

    # Verify
    binary = get_inference_binary()
    if binary:
        console.print(f"\n[green]bitnet.cpp built successfully![/green]")
        console.print(f"  Binary: {binary}")
        return True
    else:
        console.print("[red]Build completed but inference binary not found.[/red]")
        console.print("You may need to build manually. See:")
        console.print(f"  {BITNET_CPP_DIR}/README.md")
        return False
