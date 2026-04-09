"""Dashboard-specific API endpoints for bithub web UI."""

from typing import Optional

from fastapi import APIRouter, HTTPException

from bithub.config import load_config
from bithub.downloader import get_downloaded_models, remove_model
from bithub.model_manager import ModelManager
from bithub.registry import list_available_models

router = APIRouter(prefix="/api", tags=["dashboard"])

_manager: Optional[ModelManager] = None


def init_dashboard(manager: ModelManager) -> APIRouter:
    global _manager
    _manager = manager
    return router


@router.get("/stats")
async def get_stats():
    if _manager is None:
        return {"error": "Not initialized"}
    return _manager.get_stats()


@router.get("/config")
async def get_config():
    return load_config()


@router.get("/models/downloaded")
async def list_downloaded():
    return get_downloaded_models()


@router.get("/models/registry")
async def list_registry():
    return list_available_models()


@router.delete("/models/{model_name}")
async def delete_model(model_name: str):
    success = remove_model(model_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Model {model_name} not found")
    return {"removed": True, "model": model_name}
