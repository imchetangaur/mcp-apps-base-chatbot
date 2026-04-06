from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from .messages import Message


class MessageEvent(BaseModel):
    type: Literal["Message"] = "Message"
    message: Message


class ErrorEvent(BaseModel):
    type: Literal["Error"] = "Error"
    error: str


class FinishEvent(BaseModel):
    type: Literal["Finish"] = "Finish"
    reason: str


class PingEvent(BaseModel):
    type: Literal["Ping"] = "Ping"


SSEEvent = Annotated[
    Union[MessageEvent, ErrorEvent, FinishEvent, PingEvent],
    Field(discriminator="type"),
]
