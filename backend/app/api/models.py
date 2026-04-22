from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
import httpx

from app.db.models import get_db
from app.config import settings
from app.models import ModelRouter

router = APIRouter()


class OllamaModel(BaseModel):
    name: str
    size: int
    digest: str
    modified_at: str


class OllamaModelsResponse(BaseModel):
    models: List[OllamaModel]


class PullRequest(BaseModel):
    model: str


class PullStatus(BaseModel):
    status: str
    completed: Optional[int] = None
    total: Optional[int] = None
    digest: Optional[str] = None


@router.get("/models", response_model=OllamaModelsResponse)
async def list_models():
    """Список доступных моделей активного провайдера.
    Для local режима при недоступном Ollama возвращает понятную ошибку.
    Для cloud режима возвращает каталог облачных моделей.
    """
    try:
        models = ModelRouter().get_provider().list_models()
        return OllamaModelsResponse(
            models=[
                OllamaModel(
                    name=m.get("name", ""),
                    size=m.get("size", 0),
                    digest=m.get("digest", ""),
                    modified_at=m.get("modified_at", ""),
                )
                for m in models
            ]
        )
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503,
            detail=(
                "Local provider is unavailable. Start Ollama via docker compose "
                "or switch to cloud mode with NEURALDEEP_API_KEY configured."
            ),
        )


@router.post("/models/pull")
async def pull_model(req: PullRequest):
    """
    Скачать модель в Ollama.
    Возвращает stream событий прогресса.
    """
    from fastapi.responses import StreamingResponse
    import json
    
    async def stream():
        async with httpx.AsyncClient() as client:
            try:
                async with client.stream(
                    "POST",
                    f"{settings.ollama_host}/api/pull",
                    json={"name": req.model, "stream": True},
                    timeout=300.0
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if line.strip():
                            try:
                                data = json.loads(line)
                                yield f"data: {json.dumps(data)}\n\n"
                            except json.JSONDecodeError:
                                pass
                yield "data: {\"status\": \"completed\"}\n\n"
            except httpx.HTTPError as e:
                yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
    
    return StreamingResponse(stream(), media_type="text/event-stream")


@router.delete("/models/{model_name:path}")
async def delete_model(model_name: str):
    """Удалить модель из Ollama."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.delete(
                f"{settings.ollama_host}/api/delete",
                json={"name": model_name},
                timeout=30.0
            )
            resp.raise_for_status()
            return {"status": "deleted", "model": model_name}
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete model: {str(e)}")
