"""
Model downloader — pull BitNet GGUF models from HuggingFace.

Downloads into ~/.bithub/models/<model_name>/ with progress bars.
Uses huggingface_hub for reliable, resumable downloads.
"""

import hashlib
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from huggingface_hub import hf_hub_download, HfApi
from huggingface_hub.utils import (
    EntryNotFoundError,
    RepositoryNotFoundError,
    GatedRepoError,
)
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
)

from bithub.config import MODELS_DIR, ensure_dirs
from bithub.registry import get_model_info

console = Console()


def get_gguf_filename(model_info: dict) -> str:
    """
    Determine the correct GGUF filename to download.

    Strategy:
    1. If the HF repo is a -gguf repo, list files and pick the GGUF.
    2. Otherwise, look for common patterns based on quant_type.
    """
    repo_id = model_info["hf_repo"]
    name = model_info["name"]
    quant = model_info.get("quant_type", "i2_s")

    # Try common naming patterns
    candidates = [
        f"{name}-{quant}.gguf",
        f"{name}.gguf",
    ]

    # Check what's actually in the repo
    try:
        api = HfApi()
        files = api.list_repo_files(repo_id)
        gguf_files = [f for f in files if f.endswith(".gguf")]

        if len(gguf_files) == 1:
            return gguf_files[0]

        # Prefer the file matching our quant_type
        for f in gguf_files:
            if quant in f:
                return f

        # Fall back to first GGUF file
        if gguf_files:
            return gguf_files[0]

    except Exception:
        pass

    # Last resort: use first candidate
    return candidates[0]


def is_model_downloaded(model_name: str) -> bool:
    """Check if a model has already been downloaded."""
    model_dir = MODELS_DIR / model_name
    if not model_dir.exists():
        return False
    gguf_files = list(model_dir.glob("*.gguf"))
    return len(gguf_files) > 0


def get_downloaded_models() -> List[dict]:
    """Return info about all downloaded models."""
    ensure_dirs()
    downloaded = []
    if not MODELS_DIR.exists():
        return downloaded

    for model_dir in sorted(MODELS_DIR.iterdir()):
        if not model_dir.is_dir():
            continue
        gguf_files = list(model_dir.glob("*.gguf"))
        if gguf_files:
            size_bytes = sum(f.stat().st_size for f in gguf_files)
            downloaded.append({
                "name": model_dir.name,
                "path": str(model_dir),
                "gguf_file": str(gguf_files[0]),
                "size_mb": round(size_bytes / (1024 * 1024)),
            })
    return downloaded


def get_model_gguf_path(model_name: str) -> Optional[Path]:
    """Return the path to a downloaded model's GGUF file, or None."""
    model_dir = MODELS_DIR / model_name
    gguf_files = list(model_dir.glob("*.gguf"))
    return gguf_files[0] if gguf_files else None


def _compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _write_checksum(gguf_path: Path) -> None:
    """Write SHA256 checksum file next to the GGUF."""
    sha = _compute_sha256(gguf_path)
    checksum_file = gguf_path.parent / "sha256"
    checksum_file.write_text(sha)


def verify_checksum(model_name: str) -> bool:
    """Verify a model's GGUF matches its stored SHA256. Returns False if mismatch or missing."""
    gguf_path = get_model_gguf_path(model_name)
    if gguf_path is None:
        return False
    checksum_file = gguf_path.parent / "sha256"
    if not checksum_file.exists():
        return False
    stored = checksum_file.read_text().strip()
    actual = _compute_sha256(gguf_path)
    return stored == actual


def _parse_size_mb(size_mb: int) -> int:
    """Convert size in MB to bytes."""
    return size_mb * 1024 * 1024


def _check_disk_space(target_dir: Path, size_mb: int) -> None:
    """Abort if disk space is insufficient for the download."""
    required = _parse_size_mb(size_mb)
    if required == 0:
        return
    # Ensure the directory (or its parent) exists for disk_usage check
    check_path = target_dir if target_dir.exists() else target_dir.parent
    usage = shutil.disk_usage(check_path)
    buffer = 1024**3  # 1GB buffer
    if usage.free < required + buffer:
        free_gb = usage.free / 1024**3
        req_gb = required / 1024**3
        console.print(
            f"[red]Insufficient disk space.[/red] "
            f"Need {req_gb:.1f}GB, only {free_gb:.1f}GB free at {target_dir}"
        )
        raise SystemExit(1)


def is_direct_hf_pull(model_ref: str) -> bool:
    """Check if a model reference uses the hf: prefix."""
    return model_ref.startswith("hf:") and len(model_ref) > 3 and "/" in model_ref


def parse_hf_uri(model_ref: str) -> Tuple[str, str]:
    """Parse hf:org/repo into (repo_id, short_name)."""
    repo_id = model_ref[3:]  # strip "hf:"
    short_name = repo_id.split("/")[-1]
    return repo_id, short_name


def download_model(model_name: str, force: bool = False) -> Path:
    """
    Download a model from HuggingFace.

    Args:
        model_name: Short name from registry (e.g. '2B-4T')
        force: If True, re-download even if already present

    Returns:
        Path to the downloaded GGUF file

    Raises:
        SystemExit on errors (after printing helpful messages)
    """
    ensure_dirs()

    # Look up model in registry
    info = get_model_info(model_name)
    if not info:
        console.print(f"[red]Unknown model: {model_name}[/red]")
        console.print("Run [bold]bithub models[/bold] to see available models.")
        raise SystemExit(1)

    # Check disk space before downloading
    _check_disk_space(MODELS_DIR, info.get("size_mb", 0))

    model_dir = MODELS_DIR / model_name
    repo_id = info["hf_repo"]

    # Check if already downloaded
    if not force and is_model_downloaded(model_name):
        existing = get_model_gguf_path(model_name)
        console.print(f"[green]Model {model_name} already downloaded:[/green] {existing}")
        console.print("Use [bold]--force[/bold] to re-download.")
        return existing

    # Determine which file to download
    console.print(f"\n[bold]Pulling {info['name']}[/bold]")
    console.print(f"  Repository: [dim]{repo_id}[/dim]")
    console.print(f"  Parameters: {info['parameters']}")
    console.print(f"  Estimated size: ~{info['size_mb']}MB\n")

    with console.status("[bold blue]Finding GGUF file in repository..."):
        try:
            gguf_filename = get_gguf_filename(info)
        except Exception as e:
            console.print(f"[red]Failed to list repository files: {e}[/red]")
            raise SystemExit(1)

    console.print(f"  Downloading: [cyan]{gguf_filename}[/cyan]\n")

    # Download with huggingface_hub (it handles progress, caching, and resumption)
    try:
        downloaded_path = hf_hub_download(
            repo_id=repo_id,
            filename=gguf_filename,
            local_dir=str(model_dir),
            local_dir_use_symlinks=False,
        )
        downloaded_path = Path(downloaded_path)

    except RepositoryNotFoundError:
        console.print(f"[red]Repository not found: {repo_id}[/red]")
        console.print("The model may have been removed or the repo ID may be wrong.")
        raise SystemExit(1)

    except EntryNotFoundError:
        console.print(f"[red]File not found: {gguf_filename}[/red]")
        console.print(f"This file doesn't exist in {repo_id}.")
        console.print("The model registry may need updating.")
        raise SystemExit(1)

    except GatedRepoError:
        console.print(f"[red]Access denied: {repo_id} is a gated repository.[/red]")
        console.print("You may need to accept the model's license on HuggingFace first:")
        console.print(f"  [link]https://huggingface.co/{repo_id}[/link]")
        raise SystemExit(1)

    except Exception as e:
        console.print(f"[red]Download failed: {e}[/red]")
        raise SystemExit(1)

    # Verify the file exists and has size
    if not downloaded_path.exists():
        console.print("[red]Download seemed to succeed but file not found.[/red]")
        raise SystemExit(1)

    size_mb = downloaded_path.stat().st_size / (1024 * 1024)
    console.print(f"\n[green]Downloaded successfully![/green]")
    console.print(f"  File: {downloaded_path}")
    console.print(f"  Size: {size_mb:.0f} MB")

    _write_checksum(downloaded_path)
    console.print(f"  Checksum: [dim]SHA256 written[/dim]")

    return downloaded_path


def download_direct_hf(repo_id: str, name: Optional[str] = None, force: bool = False) -> Path:
    """Download a GGUF model directly from any HuggingFace repo."""
    ensure_dirs()

    if not name:
        name = repo_id.split("/")[-1]

    model_dir = MODELS_DIR / name

    if not force and is_model_downloaded(name):
        existing = get_model_gguf_path(name)
        console.print(f"[green]Model {name} already downloaded:[/green] {existing}")
        console.print("Use [bold]--force[/bold] to re-download.")
        return existing

    console.print(f"\n[bold]Pulling from HuggingFace[/bold]")
    console.print(f"  Repository: [dim]{repo_id}[/dim]")
    console.print(f"  [yellow]Not in curated registry. Compatibility not guaranteed.[/yellow]\n")

    with console.status("[bold blue]Finding GGUF file in repository..."):
        try:
            api = HfApi()
            files = api.list_repo_files(repo_id)
            gguf_files = [f for f in files if f.endswith(".gguf")]
        except Exception as e:
            console.print(f"[red]Failed to access repository: {e}[/red]")
            raise SystemExit(1)

    if not gguf_files:
        console.print(f"[red]No GGUF files found in {repo_id}[/red]")
        raise SystemExit(1)

    gguf_filename = gguf_files[0]
    if len(gguf_files) > 1:
        console.print(f"  Found {len(gguf_files)} GGUF files, downloading: [cyan]{gguf_filename}[/cyan]")
    else:
        console.print(f"  Downloading: [cyan]{gguf_filename}[/cyan]\n")

    try:
        downloaded_path = hf_hub_download(
            repo_id=repo_id,
            filename=gguf_filename,
            local_dir=str(model_dir),
            local_dir_use_symlinks=False,
        )
        downloaded_path = Path(downloaded_path)
    except Exception as e:
        console.print(f"[red]Download failed: {e}[/red]")
        raise SystemExit(1)

    size_mb = downloaded_path.stat().st_size / (1024 * 1024)
    console.print(f"\n[green]Downloaded successfully![/green]")
    console.print(f"  File: {downloaded_path}")
    console.print(f"  Size: {size_mb:.0f} MB")

    _write_checksum(downloaded_path)
    console.print(f"  Checksum: [dim]SHA256 written[/dim]")

    from bithub.registry import save_custom_model
    save_custom_model(name, {
        "hf_repo": repo_id,
        "name": name,
        "source": "direct",
    })

    return downloaded_path


def remove_model(model_name: str) -> bool:
    """
    Remove a downloaded model.

    Returns True if removed, False if not found.
    """
    model_dir = MODELS_DIR / model_name
    if not model_dir.exists():
        return False

    shutil.rmtree(model_dir)
    return True
