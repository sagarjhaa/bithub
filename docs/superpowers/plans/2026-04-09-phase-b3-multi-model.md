# Phase B3: Multi-Model Serving

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow the API server to load and route requests to multiple models simultaneously, selected by the `model` field in chat completion requests.

**Architecture:** Replace the single global `BackendProcess` with a `ModelManager` class that manages a dict of model_name → BackendProcess. Each loaded model gets its own llama-server subprocess on a unique port. The FastAPI router looks up the right backend by `request.model`. Supports eager loading (start all backends at boot) and lazy loading (start backend on first request). The `serve` CLI command accepts multiple model names.

**Tech Stack:** Existing — FastAPI, subprocess, httpx. No new dependencies.

---

## File Map

**Created:**
- `bithub/model_manager.py` — ModelManager class, manages multiple BackendProcess instances
- `tests/test_model_manager.py` — ModelManager unit tests

**Modified:**
- `bithub/api.py` — Use ModelManager instead of global `_backend`, route by model name
- `bithub/server.py` — Update `start_server` and `start_background_server` for multi-model
- `bithub/cli.py` — `serve` accepts multiple models, add `--lazy` flag
- `tests/test_api.py` — Update for multi-model API
- `tests/test_cli.py` — Update serve command tests

---

## Task 0: Extract ModelManager from api.py

**Files:**
- Create: `bithub/model_manager.py`
- Create: `tests/test_model_manager.py`

Extract the `BackendProcess` dataclass from api.py into a new module, then wrap it in a `ModelManager` that manages multiple instances.

- [ ] **Step 1: Write failing tests**

Create `tests/test_model_manager.py`:

```python
"""Tests for bithub.model_manager."""

from pathlib import Path
from typing import Dict
from unittest.mock import patch, MagicMock

import pytest


class TestModelManager:
    def test_register_model(self) -> None:
        from bithub.model_manager import ModelManager
        mgr = ModelManager(base_port=9000)
        mgr.register("test-model", Path("/fake/model.gguf"), threads=2, context_size=2048)
        assert "test-model" in mgr.models
        assert mgr.models["test-model"]["gguf_path"] == Path("/fake/model.gguf")

    def test_register_multiple_models(self) -> None:
        from bithub.model_manager import ModelManager
        mgr = ModelManager(base_port=9000)
        mgr.register("model-a", Path("/fake/a.gguf"))
        mgr.register("model-b", Path("/fake/b.gguf"))
        assert len(mgr.models) == 2

    def test_port_assignment(self) -> None:
        from bithub.model_manager import ModelManager
        mgr = ModelManager(base_port=9000)
        mgr.register("model-a", Path("/fake/a.gguf"))
        mgr.register("model-b", Path("/fake/b.gguf"))
        port_a = mgr.models["model-a"]["backend_port"]
        port_b = mgr.models["model-b"]["backend_port"]
        assert port_a != port_b

    def test_get_backend_url(self) -> None:
        from bithub.model_manager import ModelManager
        mgr = ModelManager(base_port=9000)
        mgr.register("test-model", Path("/fake/model.gguf"))
        url = mgr.get_backend_url("test-model")
        assert url is not None
        assert "9000" in url

    def test_get_backend_url_unknown_model(self) -> None:
        from bithub.model_manager import ModelManager
        mgr = ModelManager(base_port=9000)
        url = mgr.get_backend_url("nonexistent")
        assert url is None

    def test_list_models(self) -> None:
        from bithub.model_manager import ModelManager
        mgr = ModelManager(base_port=9000)
        mgr.register("model-a", Path("/fake/a.gguf"))
        mgr.register("model-b", Path("/fake/b.gguf"))
        models = mgr.list_models()
        assert len(models) == 2
        names = [m["name"] for m in models]
        assert "model-a" in names
        assert "model-b" in names

    def test_is_model_loaded_before_start(self) -> None:
        from bithub.model_manager import ModelManager
        mgr = ModelManager(base_port=9000)
        mgr.register("test-model", Path("/fake/model.gguf"))
        assert mgr.is_loaded("test-model") is False

    def test_max_models_default(self) -> None:
        from bithub.model_manager import ModelManager
        mgr = ModelManager(base_port=9000, max_models=2)
        mgr.register("a", Path("/fake/a.gguf"))
        mgr.register("b", Path("/fake/b.gguf"))
        with pytest.raises(ValueError, match="Maximum.*models"):
            mgr.register("c", Path("/fake/c.gguf"))
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
/usr/bin/python3 -m pytest tests/test_model_manager.py -v
```

- [ ] **Step 3: Create `bithub/model_manager.py`**

```python
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
        """Start backends for all registered models. Returns False if any fail."""
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
        """Get the backend URL for a model. Returns None if not registered."""
        if model_name not in self.models:
            return None
        port = self.models[model_name]["backend_port"]
        return f"http://127.0.0.1:{port}"

    def is_loaded(self, model_name: str) -> bool:
        """Check if a model's backend is running."""
        return model_name in self.backends and self.backends[model_name].is_running

    def ensure_loaded(self, model_name: str) -> bool:
        """Ensure a model is loaded (lazy loading). Start if not running."""
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
```

- [ ] **Step 4: Run tests**

```bash
/usr/bin/python3 -m pytest tests/test_model_manager.py -v
```

Expected: all 8 tests pass.

- [ ] **Step 5: Commit**

```bash
git add bithub/model_manager.py tests/test_model_manager.py
git commit -m "Add ModelManager for multi-model backend orchestration"
```

---

## Task 1: Update api.py to Use ModelManager

**Files:**
- Modify: `bithub/api.py`

Replace the global `_backend` and `BackendProcess` usage with `ModelManager`. The `create_app` function changes signature to accept either a single model or multiple models.

- [ ] **Step 1: Read current `bithub/api.py`**

- [ ] **Step 2: Refactor `create_app` to use ModelManager**

Key changes:
1. Remove the `BackendProcess` class and global `_backend` from api.py (now in model_manager.py)
2. Replace `create_app` signature to accept a ModelManager instance
3. Chat completions routes by `request.model` to the right backend
4. `/v1/models` shows registered models with loaded status
5. Support lazy loading (start backend on first request if not running)

Replace the entire section from `# Backend process manager` through end of file with:

```python
from bithub.model_manager import ModelManager


def create_app(
    model_name: str,
    gguf_path: Path,
    threads: int = 2,
    context_size: int = 2048,
    backend_port: int = 8081,
    manager: Optional[ModelManager] = None,
) -> FastAPI:
    """Create the FastAPI app.

    If a ModelManager is provided, it's used directly (multi-model mode).
    Otherwise, a single-model manager is created for backwards compatibility.
    """
    if manager is None:
        manager = ModelManager(base_port=backend_port)
        manager.register(model_name, gguf_path, threads=threads, context_size=context_size)

    app = FastAPI(
        title="bithub API",
        description="OpenAI-compatible API for BitNet 1-bit LLMs",
        version="0.1.0",
    )

    @app.on_event("startup")
    async def startup():
        console.print("\n[bold]Starting model backends...[/bold]")
        success = manager.start_all()
        if not success:
            console.print("[red]Some backends failed to start.[/red]")
        loaded = [m["name"] for m in manager.list_models() if m["loaded"]]
        console.print(f"[green]Ready! Models: {', '.join(loaded)}[/green]\n")

    @app.on_event("shutdown")
    async def shutdown():
        console.print("\n[yellow]Shutting down backends...[/yellow]")
        manager.stop_all()

    @app.get("/health")
    async def health():
        loaded = [m for m in manager.list_models() if m["loaded"]]
        return {
            "status": "ok" if loaded else "no_models_loaded",
            "models_loaded": len(loaded),
        }

    @app.get("/v1/models")
    async def list_models_endpoint():
        models = []
        for m in manager.list_models():
            models.append({
                "id": m["name"],
                "object": "model",
                "created": 0,
                "owned_by": "bithub",
                "status": "loaded" if m["loaded"] else "available",
            })
        # Also include downloaded but not registered models
        downloaded = get_downloaded_models()
        registered_names = {m["name"] for m in manager.list_models()}
        for d in downloaded:
            if d["name"] not in registered_names:
                models.append({
                    "id": d["name"],
                    "object": "model",
                    "created": 0,
                    "owned_by": "bithub",
                    "status": "available",
                })
        return {"object": "list", "data": models}

    @app.post("/v1/chat/completions")
    async def chat_completions(request: ChatCompletionRequest):
        model_name = request.model

        # Try lazy loading
        if not manager.is_loaded(model_name):
            if model_name in manager.models:
                if not manager.ensure_loaded(model_name):
                    raise HTTPException(
                        status_code=503,
                        detail=f"Failed to start backend for {model_name}",
                    )
            else:
                available = [m["name"] for m in manager.list_models()]
                raise HTTPException(
                    status_code=404,
                    detail=f"Model '{model_name}' not found. Available: {available}",
                )

        backend_url = manager.get_backend_url(model_name)
        if not backend_url:
            raise HTTPException(status_code=503, detail="Backend not available")

        url = f"{backend_url}/v1/chat/completions"
        payload = {
            "model": request.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
            "top_p": request.top_p,
            "max_tokens": request.max_tokens,
            "stream": request.stream,
        }
        if request.stop:
            payload["stop"] = request.stop

        if request.stream:
            return await _stream_response(url, payload, model_name)
        else:
            return await _non_stream_response(url, payload, model_name)

    async def _non_stream_response(
        backend_url: str, payload: dict, model_name: str
    ) -> JSONResponse:
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(backend_url, json=payload)
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=resp.status_code,
                        detail=f"Backend error: {resp.text[:500]}",
                    )
                data = resp.json()
                data["model"] = model_name
                return JSONResponse(content=data)
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Backend not reachable")
        except httpx.ReadTimeout:
            raise HTTPException(status_code=504, detail="Backend timed out")

    async def _stream_response(
        backend_url: str, payload: dict, model_name: str
    ) -> StreamingResponse:
        async def generate():
            try:
                async with httpx.AsyncClient(timeout=300) as client:
                    async with client.stream("POST", backend_url, json=payload) as resp:
                        async for line in resp.aiter_lines():
                            if line.startswith("data: "):
                                chunk_str = line[6:]
                                if chunk_str.strip() == "[DONE]":
                                    yield "data: [DONE]\n\n"
                                    break
                                try:
                                    chunk = json.loads(chunk_str)
                                    chunk["model"] = model_name
                                    yield f"data: {json.dumps(chunk)}\n\n"
                                except json.JSONDecodeError:
                                    yield f"data: {chunk_str}\n\n"
            except httpx.ConnectError:
                error = {"error": {"message": "Backend not reachable", "type": "server_error"}}
                yield f"data: {json.dumps(error)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    return app
```

IMPORTANT: Keep the Pydantic models (`ChatMessage`, `ChatCompletionRequest`, etc.) and all imports at the top of api.py unchanged. Only replace from the `BackendProcess` dataclass onward.

- [ ] **Step 3: Update tests/test_api.py**

The `api_client` fixture creates an app via `create_app`. Since the signature is backwards-compatible (single model still works), the existing tests should mostly work. But verify and fix if needed. The health endpoint now returns `models_loaded` instead of `model`.

- [ ] **Step 4: Run tests**

```bash
/usr/bin/python3 -m pytest tests/test_api.py -v
/usr/bin/python3 -m pytest tests/ -v
```

- [ ] **Step 5: Commit**

```bash
git add bithub/api.py tests/test_api.py
git commit -m "Refactor api.py to use ModelManager for multi-model routing"
```

---

## Task 2: Update CLI `serve` Command for Multiple Models

**Files:**
- Modify: `bithub/cli.py`
- Modify: `bithub/server.py`

- [ ] **Step 1: Update `serve` command to accept multiple models**

In `bithub/cli.py`, change the `serve` command:

```python
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

    # Validate all models
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
```

- [ ] **Step 2: Update `start_server` in server.py**

Change `start_server` to accept multiple models:

```python
def start_server(
    model_names: List[str],
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    threads: int = 2,
    context_size: int = 2048,
    lazy: bool = False,
) -> None:
    """Start the bithub API server with one or more models."""
    from bithub.model_manager import ModelManager
    from bithub.api import create_app
    import uvicorn

    backend_base_port = port + 1
    manager = ModelManager(base_port=backend_base_port, max_models=len(model_names))

    for name in model_names:
        gguf_path = _preflight_check(name)
        info = get_model_info(name)
        display_name = info["name"] if info else name
        manager.register(name, gguf_path, threads=threads, context_size=context_size)

    console.print(f"\n[bold green]Starting bithub server[/bold green]")
    for name in model_names:
        info = get_model_info(name)
        display_name = info["name"] if info else name
        console.print(f"  Model:    {display_name}")
    console.print(f"  Address:  http://{host}:{port}")
    console.print(f"  Threads:  {threads} per model")
    console.print(f"  Lazy:     {'yes' if lazy else 'no'}")
    console.print()
    console.print("[dim]Press Ctrl+C to stop the server[/dim]\n")

    app = create_app(
        model_name=model_names[0],
        gguf_path=_preflight_check(model_names[0]),
        manager=manager,
    )

    if not lazy:
        # Eager mode: models start in the startup event
        pass

    try:
        uvicorn.run(app, host=host, port=port, log_level="warning")
    except KeyboardInterrupt:
        console.print("\n[green]Server stopped.[/green]")
```

Add `from typing import List` at the top if not present.

Also update `start_background_server` for backwards compat — it should still work for single-model REPL use.

- [ ] **Step 3: Update serve tests in test_cli.py**

The `serve` command now takes `model_names` (tuple) instead of `model_name` (string). Update any mocks/tests that invoke `serve`.

- [ ] **Step 4: Run tests**

```bash
/usr/bin/python3 -m pytest tests/ -v
```

- [ ] **Step 5: Commit**

```bash
git add bithub/cli.py bithub/server.py tests/test_cli.py
git commit -m "Update serve command to accept multiple models with --lazy flag"
```

---

## Task 3: Final Verification

- [ ] **Step 1: Run full test suite**

```bash
/usr/bin/python3 -m pytest tests/ --cov=bithub --cov-report=term-missing -v
```

- [ ] **Step 2: Verify CLI help**

```bash
/usr/bin/python3 -c "from bithub.cli import cli; cli(['serve', '--help'])" 2>&1 || true
```

Expected: shows `MODEL_NAMES...` (multiple) and `--lazy` flag.

- [ ] **Step 3: Commit any fixes**

```bash
git add -A
git commit -m "Phase B3 complete: multi-model serving with lazy loading"
```
