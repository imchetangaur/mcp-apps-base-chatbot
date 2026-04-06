from __future__ import annotations

import time
import uuid
from typing import Optional

from pydantic import BaseModel, Field

from .messages import Message, MessageContent


class Session(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "New Chat"
    created: float = Field(default_factory=time.time)
    updated: float = Field(default_factory=time.time)
    messages: list[Message] = Field(default_factory=list)
    extension_names: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    content: list[MessageContent]
