from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from app.rag.pipeline import search_query, ask_query, ask_query_stream

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    filters: Optional[Dict[str, Any]] = None


class AskRequest(BaseModel):
    query: str
    top_k: int = 5
    filters: Optional[Dict[str, Any]] = None
    stream: bool = False


class SearchResult(BaseModel):
    path: str
    filename: str
    snippet: str
    score: float
    page: Optional[int] = None
    file_type: Optional[str] = None


@router.post("/search", response_model=List[SearchResult])
async def search(req: SearchRequest):
    try:
        results = await search_query(req.query, top_k=req.top_k, filters=req.filters)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask")
async def ask(req: AskRequest):
    try:
        if req.stream:
            return StreamingResponse(
                ask_query_stream(req.query, top_k=req.top_k, filters=req.filters),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        answer = await ask_query(req.query, top_k=req.top_k, filters=req.filters)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
