from __future__ import annotations

import time

from app.models.sessions import Session


class SessionManager:
    """In-memory session store for POC."""

    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create(self, name: str = "New Chat") -> Session:
        session = Session(name=name)
        self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def list_all(self) -> list[Session]:
        return sorted(self._sessions.values(), key=lambda s: s.updated, reverse=True)

    def delete(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None

    def update_name(self, session_id: str, name: str) -> Session | None:
        session = self._sessions.get(session_id)
        if session:
            session.name = name
            session.updated = time.time()
        return session

    def touch(self, session_id: str):
        session = self._sessions.get(session_id)
        if session:
            session.updated = time.time()


# Singleton
session_manager = SessionManager()
