"""Chat route — /reply SSE endpoint with streaming."""

import time
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.messages import Message, Role
from app.models.sessions import ChatRequest
from app.services.agent import agent
from app.services.session_manager import session_manager

router = APIRouter(prefix="/api/sessions", tags=["chat"])


@router.post("/{session_id}/reply")
async def reply(session_id: str, request: ChatRequest):
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Build user message
    user_message = Message(
        role=Role.user,
        content=request.content,
    )

    async def event_stream():
        try:
            async for event in agent.reply(session_id, user_message):
                data = event.model_dump_json()
                yield f"data: {data}\n\n"
        except Exception as e:
            from app.models.events import ErrorEvent
            error_event = ErrorEvent(error=str(e))
            yield f"data: {error_event.model_dump_json()}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
