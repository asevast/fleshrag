from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.db.models import get_db
from app.db import crud

router = APIRouter()


class ExportRequest(BaseModel):
    conversation_id: Optional[int] = None
    include_sources: bool = True
    format: str = "markdown"  # пока только markdown


@router.get("/export/conversation/{conv_id}")
async def export_conversation(
    conv_id: int,
    include_sources: bool = True,
    db: Session = Depends(get_db)
):
    """
    Экспорт диалога в Markdown формате.
    """
    conv = crud.get_conversation(db, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    lines = []
    
    # Заголовок
    title = conv.title or f"Диалог #{conv.id}"
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"**Дата создания:** {conv.created_at.strftime('%d.%m.%Y %H:%M')}")
    lines.append(f"**Дата обновления:** {conv.updated_at.strftime('%d.%m.%Y %H:%M')}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Сообщения
    for msg in conv.messages:
        if msg.role == "user":
            lines.append(f"## 👤 Пользователь")
            lines.append("")
            lines.append(msg.content)
        else:
            lines.append(f"## 🤖 Ассистент")
            lines.append("")
            lines.append(msg.content)
        
        # Источники
        if include_sources and msg.sources:
            try:
                import json
                sources = json.loads(msg.sources)
                if sources:
                    lines.append("")
                    lines.append("### Источники:")
                    lines.append("")
                    for i, src in enumerate(sources, 1):
                        filename = src.get("filename", "Unknown")
                        path = src.get("path", "Unknown")
                        snippet = src.get("snippet", "")[:200]
                        score = src.get("score", 0)
                        rerank = src.get("rerank_score")
                        
                        lines.append(f"**{i}.** {filename}")
                        lines.append(f"- Путь: `{path}`")
                        lines.append(f"- Score: {score:.3f}" + (f", Rerank: {rerank:.3f}" if rerank else ""))
                        if snippet:
                            lines.append(f"- Сниппет: > {snippet}")
                        lines.append("")
            except:
                pass
        
        lines.append("")
        lines.append("---")
        lines.append("")
    
    # Футер
    lines.append("")
    lines.append(f"*Экспортировано из FleshRAG {datetime.now().strftime('%d.%m.%Y %H:%M')}*")
    
    content = "\n".join(lines)
    
    filename = (conv.title or f"conversation_{conv_id}").replace(" ", "_").replace("/", "_")
    filename = f"{filename}.md"
    
    return PlainTextResponse(
        content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.post("/export/search")
async def export_search_results(
    query: str,
    results: List[Dict[str, Any]],
    include_sources: bool = True,
):
    """
    Экспорт результатов поиска в Markdown.
    """
    lines = []
    
    lines.append(f"# Результаты поиска")
    lines.append("")
    lines.append(f"**Запрос:** {query}")
    lines.append(f"**Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    lines.append(f"**Найдено:** {len(results)}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    for i, result in enumerate(results, 1):
        filename = result.get("filename", "Unknown")
        path = result.get("path", "Unknown")
        snippet = result.get("snippet", "")
        score = result.get("score", 0)
        page = result.get("page")
        file_type = result.get("file_type")
        
        lines.append(f"## {i}. {filename}")
        lines.append("")
        lines.append(f"- **Путь:** `{path}`")
        if file_type:
            lines.append(f"- **Тип:** {file_type}")
        if page:
            lines.append(f"- **Страница:** {page}")
        lines.append(f"- **Score:** {score:.3f}")
        lines.append("")
        lines.append("### Сниппет:")
        lines.append("")
        lines.append(f"> {snippet}")
        lines.append("")
        lines.append("---")
        lines.append("")
    
    content = "\n".join(lines)
    
    filename = query[:50].replace(" ", "_").replace("/", "_").replace("?", "")
    filename = f"search_{filename}.md"
    
    return PlainTextResponse(
        content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )