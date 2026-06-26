from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field


class StdioExtensionConfig(BaseModel):
    type: Literal["stdio"] = "stdio"
    name: str
    description: str = ""
    cmd: str
    args: list[str] = Field(default_factory=list)
    envs: dict[str, str] = Field(default_factory=dict)


class HttpExtensionConfig(BaseModel):
    type: Literal["streamable_http"] = "streamable_http"
    name: str
    description: str = ""
    uri: str


ExtensionConfig = Annotated[
    Union[StdioExtensionConfig, HttpExtensionConfig],
    Field(discriminator="type"),
]


class ToolInfo(BaseModel):
    name: str
    description: str
    input_schema: dict
    extension_name: str
    ui_resource_uri: Optional[str] = None
