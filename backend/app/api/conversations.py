from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.db.models import get_db
from app.db import crud
from app.rag.pipeline import ask_query, ask_query_stream
from fastapi.responses import StreamingResponse
import json

router = APIRouter()


class MessageCreate(BaseModel):
    query: str
    conversation_id: Optional[int] = None
    stream: bool = False


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    sources: Optional[List[Dict]] = None
    created_at: datetime


class ConversationSummary(BaseModel):
    id: int
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    message_count: int


@router.post("/conversations")
async def create_conversation(title: Optional[str] = None, db: Session = Depends(get_db)):
    """Создать новый диалог."""
    conv = crud.create_conversation(db, title)
    return {
        "id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at,
        "updated_at": conv.updated_at,
    }


@router.get("/conversations", response_model=List[ConversationSummary])
async def list_conversations(db: Session = Depends(get_db)):
    """Список всех диалогов."""
    conversations = crud.get_conversations(db)
    return [
        {
            "id": c.id,
            "title": c.title or f"Диалог #{c.id}",
            "created_at": c.created_at,
            "updated_at": c.updated_at,
            "message_count": len(c.messages),
        }
        for c in conversations
    ]


@router.get("/conversations/{conv_id}")
async def get_conversation(conv_id: int, db: Session = Depends(get_db)):
    """Получить диалог с сообщениями."""
    conv = crud.get_conversation(db, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = []
    for msg in conv.messages:
        sources = None
        if msg.sources:
            try:
                sources = json.loads(msg.sources)
            except:
                pass
        messages.append({
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "sources": sources,
            "created_at": msg.created_at,
        })
    
    return {
        "id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at,
        "updated_at": conv.updated_at,
        "messages": messages,
    }


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: int, db: Session = Depends(get_db)):
    """Удалить диалог."""
    if not crud.delete_conversation(db, conv_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "deleted"}


@router.post("/conversations/{conv_id}/ask")
async def ask_in_conversation(conv_id: int, req: MessageCreate, db: Session = Depends(get_db)):
    """
    Задать вопрос в контексте диалога.
    Сохраняет вопрос и ответ в БД.
    """
    conv = crud.get_conversation(db, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Сохраняем вопрос пользователя
    user_msg = crud.add_message(db, conv_id, "user", req.query)
    
    # Получаем историю диалога для контекста
    messages = crud.get_messages(db, conv_id)
    history = []
    for msg in messages[:-1]:  # Все кроме текущего вопроса
        history.append(f"{msg.role}: {msg.content}")
    
    # Формируем промпт с историей
    context_prompt = ""
    if history:
        context_prompt = "Предыстория диалога:\n" + "\n".join(history[-6:]) + "\n\n"
    
    try:
        if req.stream:
            async def stream_with_history():
                # Стриминг с сохранением ответа
                full_answer = ""
                sources = None
                error_occurred = False
                
                try:
                    async for chunk in ask_query_stream(req.query, top_k=5):
                        if chunk.startswith("data: "):
                            data = chunk[6:].strip()
                            if data == "[DONE]":
                                # Сохраняем ответ
                                if sources:
                                    crud.add_message(db, conv_id, "assistant", full_answer, sources)
                                yield chunk
                                return
                            
                            try:
                                parsed = json.loads(data)
                                if parsed.get("type") == "sources":
                                    sources = parsed.get("sources")
                                elif parsed.get("type") == "token":
                                    full_answer += parsed.get("content", "")
                                elif parsed.get("type") == "error":
                                    error_occurred = True
                                    full_answer = f"Ошибка: {parsed.get('message', 'Неизвестная ошибка')}"
                            except:
                                pass
                        yield chunk
                except Exception as stream_exc:
                    # Обработка ошибки стриминга
                    error_occurred = True
                    full_answer = f"Ошибка при генерации ответа: {str(stream_exc)}"
                    # Отправляем финальный токен с ошибкой
                    error_chunk = f'data: {{"type": "token", "content": "{full_answer}"}}\n\n'
                    yield error_chunk
                    yield "data: [DONE]\n\n"
                
                # Если была ошибка, сохраняем её как сообщение
                if error_occurred and full_answer:
                    crud.add_message(db, conv_id, "assistant", full_answer, None)
            
            return StreamingResponse(stream_with_history(), media_type="text/event-stream")
        else:
            result = await ask_query(req.query, top_k=5)
            crud.add_message(db, conv_id, "assistant", result["answer"], result.get("sources", []))
            return result
    except Exception as e:
        # При ошибке сохраняем сообщение об ошибке как assistant message
        error_message = f"Не удалось получить ответ: {str(e)}"
        crud.add_message(db, conv_id, "assistant", error_message, None)
        # Возвращаем ошибку как обычный ответ (не HTTPException, чтобы фронтенд не ломался)
        return {"answer": error_message, "sources": [], "error": str(e)}