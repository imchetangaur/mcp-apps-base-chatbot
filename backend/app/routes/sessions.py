from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.sessions import Session
from app.services.session_manager import session_manager

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    name: str = "New Chat"


class SessionSummary(BaseModel):
    id: str
    name: str
    created: float
    updated: float
    message_count: int


@router.post("", response_model=Session)
async def create_session(request: CreateSessionRequest):
    return session_manager.create(name=request.name)


@router.get("", response_model=list[SessionSummary])
async def list_sessions():
    sessions = session_manager.list_all()
    return [
        SessionSummary(
            id=s.id,
            name=s.name,
            created=s.created,
            updated=s.updated,
            message_count=len(s.messages),
        )
        for s in sessions
    ]


@router.get("/{session_id}", response_model=Session)
async def get_session(session_id: str):
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    if not session_manager.delete(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted"}


class RenameRequest(BaseModel):
    name: str


@router.put("/{session_id}/name")
async def rename_session(session_id: str, request: RenameRequest):
    session = session_manager.update_name(session_id, request.name)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "ok"}
