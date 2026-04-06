from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field


class Role(str, Enum):
    user = "user"
    assistant = "assistant"


class TextContent(BaseModel):
    type: Literal["text"] = "text"
    text: str


class ToolCall(BaseModel):
    name: str
    arguments: dict


class ToolRequestContent(BaseModel):
    type: Literal["toolRequest"] = "toolRequest"
    id: str
    tool_call: ToolCall


class EmbeddedResource(BaseModel):
    uri: str
    mimeType: Optional[str] = None
    text: Optional[str] = None
    blob: Optional[str] = None


class ToolResultBlock(BaseModel):
    """A single content block inside a tool result."""
    type: str  # "text", "image", "resource"
    text: Optional[str] = None
    data: Optional[str] = None  # base64 image data
    mimeType: Optional[str] = None
    resource: Optional[EmbeddedResource] = None


class ToolResult(BaseModel):
    status: str  # "success" or "error"
    content: list[ToolResultBlock]


class ToolResponseContent(BaseModel):
    type: Literal["toolResponse"] = "toolResponse"
    id: str
    tool_result: ToolResult


class ResourceContent(BaseModel):
    """Embedded resource content (HTML/image) rendered inline in the AI response."""
    type: Literal["resource"] = "resource"
    uri: str
    mimeType: Optional[str] = None
    text: Optional[str] = None
    blob: Optional[str] = None


MessageContent = Annotated[
    Union[TextContent, ToolRequestContent, ToolResponseContent, ResourceContent],
    Field(discriminator="type"),
]


class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: Role
    content: list[MessageContent]
    created: float = Field(default_factory=time.time)
