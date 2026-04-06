"""MCP Manager — manages MCP server connections and tool execution."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

from app.models.extensions import (
    ExtensionConfig,
    HttpExtensionConfig,
    StdioExtensionConfig,
    ToolInfo,
)

logger = logging.getLogger(__name__)


@dataclass
class MCPConnection:
    """Holds state for a single MCP server connection."""
    name: str
    config: ExtensionConfig
    session: ClientSession | None = None
    tools: list[ToolInfo] = field(default_factory=list)
    # Background task that keeps the context managers alive
    _task: asyncio.Task | None = None
    _ready: asyncio.Event = field(default_factory=asyncio.Event)
    _error: str | None = None
    # For cleanup
    _cancel: asyncio.Event = field(default_factory=asyncio.Event)


class MCPManager:
    """Manages MCP server connections per session."""

    def __init__(self):
        # session_id -> {extension_name -> MCPConnection}
        self._connections: dict[str, dict[str, MCPConnection]] = {}

    async def add_extension(
        self, session_id: str, config: ExtensionConfig
    ) -> list[ToolInfo]:
        """Connect to an MCP server and discover its tools."""
        if session_id not in self._connections:
            self._connections[session_id] = {}

        conn = MCPConnection(name=config.name, config=config)
        self._connections[session_id][config.name] = conn

        # Start the connection in a background task
        conn._task = asyncio.create_task(
            self._run_connection(session_id, conn)
        )

        # Wait for connection to be ready (or fail)
        await conn._ready.wait()

        if conn._error:
            # Clean up failed connection
            self._connections[session_id].pop(config.name, None)
            raise RuntimeError(f"Failed to connect to MCP server '{config.name}': {conn._error}")

        return conn.tools

    async def _run_connection(self, session_id: str, conn: MCPConnection):
        """Run an MCP connection in a background task, keeping context managers alive."""
        try:
            if isinstance(conn.config, StdioExtensionConfig):
                await self._run_stdio(conn)
            elif isinstance(conn.config, HttpExtensionConfig):
                await self._run_http(conn)
        except Exception as e:
            logger.error(f"MCP connection error for '{conn.name}': {e}")
            conn._error = str(e)
            conn._ready.set()

    async def _run_stdio(self, conn: MCPConnection):
        """Run a stdio MCP connection."""
        config: StdioExtensionConfig = conn.config
        server_params = StdioServerParameters(
            command=config.cmd,
            args=config.args,
            env=config.envs if config.envs else None,
        )

        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                conn.session = session
                conn.tools = await self._discover_tools(session, conn.name)
                conn._ready.set()

                # Keep alive until cancelled
                await conn._cancel.wait()

    async def _run_http(self, conn: MCPConnection):
        """Run a streamable HTTP MCP connection."""
        config: HttpExtensionConfig = conn.config

        async with streamablehttp_client(url=config.uri) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                conn.session = session
                conn.tools = await self._discover_tools(session, conn.name)
                conn._ready.set()

                # Keep alive until cancelled
                await conn._cancel.wait()

    async def _discover_tools(
        self, session: ClientSession, extension_name: str
    ) -> list[ToolInfo]:
        """Discover tools from an MCP server."""
        result = await session.list_tools()
        tools = []
        for tool in result.tools:
            # Prefix tool name with extension name to avoid collisions
            prefixed_name = f"{extension_name}__{tool.name}"
            tools.append(
                ToolInfo(
                    name=prefixed_name,
                    description=tool.description or "",
                    input_schema=tool.inputSchema if tool.inputSchema else {},
                    extension_name=extension_name,
                )
            )
        return tools

    async def remove_extension(self, session_id: str, name: str):
        """Disconnect from MCP server and clean up."""
        conns = self._connections.get(session_id, {})
        conn = conns.pop(name, None)
        if conn:
            conn._cancel.set()
            if conn._task:
                conn._task.cancel()
                try:
                    await conn._task
                except (asyncio.CancelledError, Exception):
                    pass

    async def list_tools(self, session_id: str) -> list[ToolInfo]:
        """Return all tools from all connected MCP servers for a session."""
        conns = self._connections.get(session_id, {})
        tools = []
        for conn in conns.values():
            tools.extend(conn.tools)
        return tools

    async def get_extensions(self, session_id: str) -> list[ExtensionConfig]:
        """Return all extension configs for a session."""
        conns = self._connections.get(session_id, {})
        return [conn.config for conn in conns.values()]

    async def call_tool(
        self, session_id: str, tool_name: str, arguments: dict
    ) -> list[dict]:
        """Dispatch a tool call to the correct MCP server.
        Returns a list of rich content blocks (text, image, resource)."""
        conns = self._connections.get(session_id, {})

        # Parse prefixed name: "extension_name__tool_name"
        if "__" in tool_name:
            ext_name, actual_tool_name = tool_name.split("__", 1)
        else:
            # Try to find the tool in any extension
            ext_name = None
            actual_tool_name = tool_name
            for conn in conns.values():
                for t in conn.tools:
                    if t.name == tool_name or t.name.endswith(f"__{tool_name}"):
                        ext_name = conn.name
                        break
                if ext_name:
                    break

        if not ext_name or ext_name not in conns:
            raise RuntimeError(f"No MCP server found for tool '{tool_name}'")

        conn = conns[ext_name]
        if not conn.session:
            raise RuntimeError(f"MCP server '{ext_name}' is not connected")

        result = await conn.session.call_tool(actual_tool_name, arguments)

        # Convert MCP content blocks to rich content blocks
        blocks = []
        for block in result.content:
            block_type = getattr(block, "type", None)

            if block_type == "text":
                blocks.append({
                    "type": "text",
                    "text": block.text,
                })
            elif block_type == "image":
                blocks.append({
                    "type": "image",
                    "data": block.data,
                    "mimeType": getattr(block, "mimeType", "image/png"),
                })
            elif block_type == "resource":
                # Embedded resource (can contain HTML, text, or binary)
                resource = block.resource
                resource_dict = {
                    "uri": str(resource.uri) if hasattr(resource, "uri") else "",
                }
                mime = str(getattr(resource, "mimeType", "")) or None
                if mime:
                    resource_dict["mimeType"] = mime
                # Text content (includes HTML)
                if hasattr(resource, "text") and resource.text:
                    resource_dict["text"] = resource.text
                # Binary/blob content (base64)
                if hasattr(resource, "blob") and resource.blob:
                    resource_dict["blob"] = resource.blob
                blocks.append({
                    "type": "resource",
                    "resource": resource_dict,
                    "mimeType": mime,
                })
            else:
                # Fallback: try to get text
                text = getattr(block, "text", None)
                if text:
                    blocks.append({"type": "text", "text": text})
                else:
                    blocks.append({"type": "text", "text": str(block)})

        return blocks if blocks else [{"type": "text", "text": "(empty result)"}]

    async def read_resource(
        self, session_id: str, extension_name: str, uri: str
    ) -> dict:
        """Read a resource from an MCP server by URI."""
        conns = self._connections.get(session_id, {})
        conn = conns.get(extension_name)
        if not conn or not conn.session:
            raise RuntimeError(f"MCP server '{extension_name}' not connected")

        result = await conn.session.read_resource(uri)

        # Return first content block
        for block in result.contents:
            mime = str(getattr(block, "mimeType", "text/plain"))
            text = getattr(block, "text", None)
            blob = getattr(block, "blob", None)
            return {
                "uri": str(getattr(block, "uri", uri)),
                "mimeType": mime,
                "text": text,
                "blob": blob,
            }

        return {"uri": uri, "mimeType": "text/plain", "text": ""}

    async def cleanup_session(self, session_id: str):
        """Clean up all connections for a session."""
        conns = self._connections.pop(session_id, {})
        for conn in conns.values():
            conn._cancel.set()
            if conn._task:
                conn._task.cancel()
                try:
                    await conn._task
                except (asyncio.CancelledError, Exception):
                    pass

    async def cleanup_all(self):
        """Clean up all connections (app shutdown)."""
        for session_id in list(self._connections.keys()):
            await self.cleanup_session(session_id)


# Singleton
mcp_manager = MCPManager()
