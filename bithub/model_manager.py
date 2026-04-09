"""Model manager — manages multiple llama-server backend processes."""

import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from rich.console import Console

from bithub.builder import get_server_binary

console = Console()


@dataclass
class BackendProcess:
    """Manages a single llama-server subprocess."""
    process: Optional[subprocess.Popen] = None
    model_name: str = ""
    backend_port: int = 8081
    ready: bool = False

    def start(
        self,
        gguf_path: Path,
        threads: int = 2,
        context_size: int = 2048,
    ) -> bool:
        """Start the llama-server backend process."""
        server_bin = get_server_binary()
        if not server_bin:
            console.print("[red]No server binary found. Run bithub setup first.[/red]")
            return False

        cmd = [
            str(server_bin),
            "-m", str(gguf_path),
            "--host", "127.0.0.1",
            "--port", str(self.backend_port),
            "-t", str(threads),
            "-c", str(context_size),
        ]

        self.process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

        self.ready = self._wait_for_ready()
        return self.ready

    def _wait_for_ready(self, timeout: int = 60) -> bool:
        """Poll the backend health endpoint until ready."""
        start = time.time()
        while time.time() - start < timeout:
            if self.process and self.process.poll() is not None:
                stderr = self.process.stderr.read().decode() if self.process.stderr else ""
                console.print(f"[red]Backend for {self.model_name} exited unexpectedly.[/red]")
                if stderr:
                    console.print(f"[dim]{stderr[:500]}[/dim]")
                return False
            try:
                resp = httpx.get(
                    f"http://127.0.0.1:{self.backend_port}/health", timeout=2,
                )
                if resp.status_code == 200:
                    return True
            except (httpx.ConnectError, httpx.ReadTimeout):
                pass
            time.sleep(1)
        return False

    def stop(self) -> None:
        """Gracefully stop the backend process."""
        if self.process:
            self.process.send_signal(signal.SIGTERM)
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process = None
            self.ready = False

    @property
    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None


class ModelManager:
    """Manages multiple model backends with port allocation."""

    def __init__(self, base_port: int = 8081, max_models: int = 3) -> None:
        self.base_port = base_port
        self.max_models = max_models
        self.models: Dict[str, dict] = {}
        self.backends: Dict[str, BackendProcess] = {}
        self._next_port = base_port

    def register(
        self,
        name: str,
        gguf_path: Path,
        threads: int = 2,
        context_size: int = 2048,
    ) -> None:
        """Register a model for serving (does not start the backend yet)."""
        if name in self.models:
            return
        if len(self.models) >= self.max_models:
            raise ValueError(
                f"Maximum {self.max_models} models allowed. "
                f"Already registered: {list(self.models.keys())}"
            )
        port = self._next_port
        self._next_port += 1
        self.models[name] = {
            "gguf_path": gguf_path,
            "threads": threads,
            "context_size": context_size,
            "backend_port": port,
        }

    def start_model(self, name: str) -> bool:
        """Start the backend for a registered model."""
        if name not in self.models:
            return False
        if name in self.backends and self.backends[name].is_running:
            return True

        info = self.models[name]
        backend = BackendProcess(
            model_name=name, backend_port=info["backend_port"],
        )
        console.print(f"  [bold]Starting backend for {name}...[/bold]")
        success = backend.start(
            gguf_path=info["gguf_path"],
            threads=info["threads"],
            context_size=info["context_size"],
        )
        if success:
            self.backends[name] = backend
            console.print(f"  [green]{name} ready on port {info['backend_port']}[/green]")
        return success

    def start_all(self) -> bool:
        """Start backends for all registered models."""
        all_ok = True
        for name in self.models:
            if not self.start_model(name):
                all_ok = False
        return all_ok

    def stop_all(self) -> None:
        """Stop all running backends."""
        for name, backend in self.backends.items():
            console.print(f"  [dim]Stopping {name}...[/dim]")
            backend.stop()
        self.backends.clear()

    def get_backend_url(self, model_name: str) -> Optional[str]:
        """Get the backend URL for a model."""
        if model_name not in self.models:
            return None
        port = self.models[model_name]["backend_port"]
        return f"http://127.0.0.1:{port}"

    def is_loaded(self, model_name: str) -> bool:
        """Check if a model's backend is running."""
        return model_name in self.backends and self.backends[model_name].is_running

    def ensure_loaded(self, model_name: str) -> bool:
        """Ensure a model is loaded (lazy loading)."""
        if self.is_loaded(model_name):
            return True
        if model_name in self.models:
            return self.start_model(model_name)
        return False

    def list_models(self) -> List[dict]:
        """List all registered models with their status."""
        result = []
        for name, info in self.models.items():
            result.append({
                "name": name,
                "loaded": self.is_loaded(name),
                "port": info["backend_port"],
            })
        return result
