"""
OpenAI-compatible API layer for bithub.

Wraps the bitnet.cpp inference engine behind a FastAPI server that
speaks the OpenAI Chat Completions protocol. Any app that works with
OpenAI (Open WebUI, Cursor, custom scripts) can connect directly.

Endpoints:
    GET  /v1/models              — list available/loaded models
    POST /v1/chat/completions    — chat completion (streaming + non-streaming)
    GET  /health                 — server health check
"""

import json
import subprocess
import signal
import sys
import time
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, validator
from rich.console import Console

from bithub.builder import get_server_binary, get_inference_binary, is_bitnet_cpp_built
from bithub.config import DEFAULT_HOST, DEFAULT_PORT
from bithub.downloader import get_model_gguf_path, is_model_downloaded, get_downloaded_models
from bithub.registry import list_available_models, get_model_info

console = Console()


# ──────────────────────────────────────────────────────────────
# Pydantic models for OpenAI-compatible request/response
# ──────────────────────────────────────────────────────────────


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=0.9, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(default=512, gt=0)
    stream: Optional[bool] = False
    stop: Optional[Union[List[str], str]] = None

    @validator("messages")
    def messages_must_not_be_empty(cls, v):
        if len(v) == 0:
            raise ValueError("messages must not be empty")
        return v


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str = "chatcmpl-bitnet"
    object: str = "chat.completion"
    created: int = 0
    model: str = ""
    choices: List[ChatCompletionChoice] = []
    usage: UsageInfo = Field(default_factory=UsageInfo)


# ──────────────────────────────────────────────────────────────
# Backend process manager for llama-server
# ──────────────────────────────────────────────────────────────


@dataclass
class BackendProcess:
    """Manages the underlying bitnet.cpp / llama-server process."""
    process: Optional[subprocess.Popen] = None
    model_name: str = ""
    backend_port: int = 8081  # internal port for llama-server
    ready: bool = False

    def start(
        self,
        model_name: str,
        gguf_path: Path,
        threads: int = 2,
        context_size: int = 2048,
        backend_port: int = 8081,
    ) -> bool:
        """Start the llama-server backend process."""
        self.model_name = model_name
        self.backend_port = backend_port

        server_bin = get_server_binary()
        if not server_bin:
            console.print("[red]No server binary found. Run bithub setup first.[/red]")
            return False

        cmd = [
            str(server_bin),
            "-m", str(gguf_path),
            "--host", "127.0.0.1",
            "--port", str(backend_port),
            "-t", str(threads),
            "-c", str(context_size),
        ]

        console.print(f"  [dim]Starting backend: {' '.join(cmd)}[/dim]")

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for the backend to become ready
        self.ready = self._wait_for_ready(timeout=60)
        return self.ready

    def _wait_for_ready(self, timeout: int = 60) -> bool:
        """Poll the backend health endpoint until it's ready."""
        start = time.time()
        while time.time() - start < timeout:
            # Check if process died
            if self.process and self.process.poll() is not None:
                stderr = self.process.stderr.read().decode() if self.process.stderr else ""
                console.print(f"[red]Backend process exited unexpectedly.[/red]")
                if stderr:
                    console.print(f"[dim]{stderr[:500]}[/dim]")
                return False

            try:
                resp = httpx.get(
                    f"http://127.0.0.1:{self.backend_port}/health",
                    timeout=2,
                )
                if resp.status_code == 200:
                    return True
            except (httpx.ConnectError, httpx.ReadTimeout):
                pass

            time.sleep(1)

        console.print("[red]Backend did not become ready within timeout.[/red]")
        return False

    def stop(self):
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


# ──────────────────────────────────────────────────────────────
# FastAPI app
# ──────────────────────────────────────────────────────────────

# Global backend — set up by create_app()
_backend = BackendProcess()


def create_app(
    model_name: str,
    gguf_path: Path,
    threads: int = 2,
    context_size: int = 2048,
    backend_port: int = 8081,
) -> FastAPI:
    """
    Create the FastAPI app with a running backend.

    Args:
        model_name: Name of the model to serve
        gguf_path: Path to the GGUF file
        threads: CPU threads for inference
        context_size: Context window size
        backend_port: Internal port for the llama-server backend

    Returns:
        Configured FastAPI app
    """
    global _backend

    app = FastAPI(
        title="bithub API",
        description="OpenAI-compatible API for BitNet 1-bit LLMs",
        version="0.1.0",
    )

    @app.on_event("startup")
    async def startup():
        global _backend
        console.print("\n[bold]Starting bitnet.cpp backend...[/bold]")
        success = _backend.start(
            model_name=model_name,
            gguf_path=gguf_path,
            threads=threads,
            context_size=context_size,
            backend_port=backend_port,
        )
        if not success:
            console.print("[red]Failed to start backend. Exiting.[/red]")
            sys.exit(1)
        console.print(f"[green]Backend ready! Model: {model_name}[/green]\n")

    @app.on_event("shutdown")
    async def shutdown():
        global _backend
        console.print("\n[yellow]Shutting down backend...[/yellow]")
        _backend.stop()

    # ── Health ──────────────────────────────────────────────

    @app.get("/health")
    async def health():
        return {
            "status": "ok" if _backend.is_running else "error",
            "model": _backend.model_name,
        }

    # ── Models ──────────────────────────────────────────────

    @app.get("/v1/models")
    async def list_models():
        """List available models (OpenAI-compatible)."""
        downloaded = get_downloaded_models()
        models = []

        for m in downloaded:
            models.append({
                "id": m["name"],
                "object": "model",
                "created": 0,
                "owned_by": "bithub",
            })

        # Always include the currently loaded model
        if _backend.model_name and not any(
            m["id"] == _backend.model_name for m in models
        ):
            models.insert(0, {
                "id": _backend.model_name,
                "object": "model",
                "created": 0,
                "owned_by": "bithub",
            })

        return {"object": "list", "data": models}

    # ── Chat Completions ────────────────────────────────────

    @app.post("/v1/chat/completions")
    async def chat_completions(request: ChatCompletionRequest):
        """OpenAI-compatible chat completion endpoint."""
        if not _backend.is_running:
            raise HTTPException(status_code=503, detail="Backend not running")

        # Forward the request to the llama-server backend
        backend_url = f"http://127.0.0.1:{_backend.backend_port}/v1/chat/completions"

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
            return await _stream_response(backend_url, payload, request.model)
        else:
            return await _non_stream_response(backend_url, payload, request.model)

    async def _non_stream_response(
        backend_url: str, payload: dict, model_name: str
    ) -> JSONResponse:
        """Forward a non-streaming request to the backend."""
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(backend_url, json=payload)

                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=resp.status_code,
                        detail=f"Backend error: {resp.text[:500]}",
                    )

                data = resp.json()
                # Ensure the model name matches what the user expects
                data["model"] = model_name
                return JSONResponse(content=data)

        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Backend not reachable")
        except httpx.ReadTimeout:
            raise HTTPException(status_code=504, detail="Backend timed out")

    async def _stream_response(
        backend_url: str, payload: dict, model_name: str
    ) -> StreamingResponse:
        """Forward a streaming request to the backend."""
        async def generate():
            try:
                async with httpx.AsyncClient(timeout=300) as client:
                    async with client.stream(
                        "POST", backend_url, json=payload
                    ) as resp:
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
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    return app
