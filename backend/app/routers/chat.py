from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .. import auth, ai_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = None


@router.post("")
def chat(
    payload: ChatRequest,
    current_user=Depends(auth.get_current_user),
):
    try:
        reply = ai_service.chat_reply(
            payload.message,
            [h.dict() for h in (payload.history or [])],
        )
    except Exception as e:
        reply = f"(AI chat unavailable: {e})"
    return {"reply": reply}
