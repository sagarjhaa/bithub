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
import sys
from pathlib import Path
from typing import List, Optional, Union

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, validator
from rich.console import Console

from bithub.downloader import get_downloaded_models
from bithub.model_manager import ModelManager

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
# FastAPI app
# ──────────────────────────────────────────────────────────────


def create_app(
    model_name: str,
    gguf_path: Path,
    threads: int = 2,
    context_size: int = 2048,
    backend_port: int = 8081,
    manager: Optional[ModelManager] = None,
) -> FastAPI:
    """
    Create the FastAPI app with model backend(s).

    In single-model mode (no manager provided), creates a ModelManager
    with a single registered model for backwards compatibility.

    In multi-model mode, uses the provided ModelManager which may have
    multiple models registered.

    Args:
        model_name: Name of the model to serve (single-model mode)
        gguf_path: Path to the GGUF file (single-model mode)
        threads: CPU threads for inference
        context_size: Context window size
        backend_port: Internal port for the llama-server backend
        manager: Optional ModelManager for multi-model mode

    Returns:
        Configured FastAPI app
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
        manager.start_all()
        loaded = [m["name"] for m in manager.list_models() if m["loaded"]]
        if loaded:
            console.print(f"[green]Ready! Models: {', '.join(loaded)}[/green]\n")

    @app.on_event("shutdown")
    async def shutdown():
        console.print("\n[yellow]Shutting down backends...[/yellow]")
        manager.stop_all()

    # ── Health ──────────────────────────────────────────────

    @app.get("/health")
    async def health():
        loaded = [m for m in manager.list_models() if m["loaded"]]
        return {
            "status": "ok" if loaded else "no_models_loaded",
            "models_loaded": len(loaded),
        }

    # ── Models ──────────────────────────────────────────────

    @app.get("/v1/models")
    async def list_models_endpoint():
        """List available models (OpenAI-compatible)."""
        models = []
        for m in manager.list_models():
            models.append({
                "id": m["name"],
                "object": "model",
                "created": 0,
                "owned_by": "bithub",
                "status": "loaded" if m["loaded"] else "available",
            })
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

    # ── Chat Completions ────────────────────────────────────

    @app.post("/v1/chat/completions")
    async def chat_completions(request: ChatCompletionRequest):
        """OpenAI-compatible chat completion endpoint."""
        model_name = request.model
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
