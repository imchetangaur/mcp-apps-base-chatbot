"""Agent — orchestrates the reply loop: user message -> LLM -> tool calls -> response.

Follows the Goose pattern:
  User message → LLM (with MCP tools) → tool call → MCP server executes
  → rich result (text/HTML/images) → streamed to UI → rendered in iframe
"""

from __future__ import annotations

import uuid
from typing import AsyncIterator

from app.models.events import SSEEvent, MessageEvent, FinishEvent, ErrorEvent
from app.models.messages import (
    Message,
    Role,
    TextContent,
    ToolRequestContent,
    ToolResponseContent,
    ResourceContent,
    ToolCall,
    ToolResult,
    ToolResultBlock,
    EmbeddedResource,
)
from app.services.session_manager import session_manager
from app.services.llm_service import llm_service
from app.services.mcp_manager import mcp_manager


def _messages_to_gemini(messages: list[Message]) -> list[dict]:
    """Convert our Message format to the intermediate format for LLM service."""
    # Build a map of call_id -> tool_name from all toolRequest blocks
    call_id_to_name: dict[str, str] = {}
    for msg in messages:
        for c in msg.content:
            if c.type == "toolRequest":
                call_id_to_name[c.id] = c.tool_call.name

    result = []
    for msg in messages:
        blocks = []
        for c in msg.content:
            if c.type == "text":
                blocks.append({"type": "text", "text": c.text})
            elif c.type == "toolRequest":
                blocks.append({
                    "type": "tool_use",
                    "name": c.tool_call.name,
                    "input": c.tool_call.arguments,
                })
            elif c.type == "toolResponse":
                # Extract text content from rich result blocks for LLM
                text_parts = []
                for block in c.tool_result.content:
                    if block.type == "text" and block.text:
                        text_parts.append(block.text)
                    elif block.type == "image":
                        text_parts.append(f"[Image: {block.mimeType}]")
                    elif block.type == "resource" and block.resource:
                        if block.resource.text:
                            text_parts.append(block.resource.text[:500])
                        else:
                            text_parts.append(f"[Resource: {block.resource.uri}]")
                content_text = "\n".join(text_parts) if text_parts else "(empty)"
                # Look up the tool name from the matching toolRequest
                tool_name = call_id_to_name.get(c.id, c.id)
                blocks.append({
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "content": content_text,
                    "is_error": c.tool_result.status == "error",
                })
            elif c.type == "resource":
                # Resource content in assistant message — skip for LLM
                # (LLM already saw the content via tool result)
                pass
        if blocks:
            result.append({"role": msg.role.value, "content": blocks})
    return result


def _tools_to_gemini(tools: list) -> list[dict]:
    """Convert ToolInfo to tool definitions."""
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.input_schema,
        }
        for t in tools
    ]


def _make_result_blocks(raw_blocks: list[dict]) -> list[ToolResultBlock]:
    """Convert raw MCP content blocks to ToolResultBlock models."""
    result = []
    for b in raw_blocks:
        block_type = b.get("type", "text")
        resource_data = b.get("resource")
        embedded = None
        if resource_data:
            embedded = EmbeddedResource(**resource_data)
        result.append(ToolResultBlock(
            type=block_type,
            text=b.get("text"),
            data=b.get("data"),
            mimeType=b.get("mimeType"),
            resource=embedded,
        ))
    return result


class Agent:
    """Orchestrates the agentic reply loop."""

    def __init__(self):
        self._tool_name_map: dict[str, str] = {}

    async def reply(self, session_id: str, user_message: Message) -> AsyncIterator[SSEEvent]:
        """Process user message through LLM + tools loop."""
        session = session_manager.get(session_id)
        if not session:
            yield ErrorEvent(error="Session not found")
            return

        # Add user message to conversation
        session.messages.append(user_message)
        session_manager.touch(session_id)

        # Get available tools from MCP
        tools = await mcp_manager.list_tools(session_id)
        gemini_tools = _tools_to_gemini(tools) if tools else None

        # Agent loop: call LLM, handle tool use, repeat
        max_iterations = 10
        for _ in range(max_iterations):
            gemini_messages = _messages_to_gemini(session.messages)

            # Collect streaming response
            assistant_msg_id = str(uuid.uuid4())
            text_parts: list[str] = []
            tool_uses: list[dict] = []
            stop_reason = "end_turn"

            async for event in llm_service.chat_completion(
                gemini_messages,
                tools=gemini_tools,
            ):
                if event["type"] == "text_delta":
                    text_parts.append(event["text"])
                    content = [TextContent(text="".join(text_parts))]
                    yield MessageEvent(
                        message=Message(
                            id=assistant_msg_id,
                            role=Role.assistant,
                            content=content,
                        )
                    )

                elif event["type"] == "tool_use":
                    tool_uses.append(event)

                elif event["type"] == "message_stop":
                    stop_reason = event["stop_reason"]

            # Build final assistant message content
            final_content = []
            if text_parts:
                final_content.append(TextContent(text="".join(text_parts)))

            for tu in tool_uses:
                self._tool_name_map[tu["id"]] = tu["name"]
                final_content.append(
                    ToolRequestContent(
                        id=tu["id"],
                        tool_call=ToolCall(name=tu["name"], arguments=tu["input"]),
                    )
                )

            # Store assistant message
            assistant_msg = Message(
                id=assistant_msg_id,
                role=Role.assistant,
                content=final_content,
            )
            session.messages.append(assistant_msg)

            # Emit full message with tool requests
            if tool_uses:
                yield MessageEvent(message=assistant_msg)

            # If no tool use, we're done
            if stop_reason != "tool_use" or not tool_uses:
                yield FinishEvent(reason=stop_reason)
                return

            # Execute tool calls and build rich results
            tool_response_content = []
            # Collect resource blocks to include in the next assistant message
            resource_content_blocks = []
            for tu in tool_uses:
                try:
                    raw_blocks = await mcp_manager.call_tool(
                        session_id, tu["name"], tu["input"]
                    )
                    result_blocks = _make_result_blocks(raw_blocks)
                    # Separate resource blocks from text/image blocks
                    # Resources go to the AI response; only text stays in tool result
                    text_blocks = []
                    for rb in result_blocks:
                        if rb.type == "resource" and rb.resource:
                            resource_content_blocks.append(
                                ResourceContent(
                                    uri=rb.resource.uri,
                                    mimeType=rb.resource.mimeType or rb.mimeType,
                                    text=rb.resource.text,
                                    blob=rb.resource.blob,
                                )
                            )
                        else:
                            text_blocks.append(rb)
                    tool_response_content.append(
                        ToolResponseContent(
                            id=tu["id"],
                            tool_result=ToolResult(
                                status="success",
                                content=text_blocks if text_blocks else [
                                    ToolResultBlock(type="text", text="(success)")
                                ],
                            ),
                        )
                    )
                except Exception as e:
                    tool_response_content.append(
                        ToolResponseContent(
                            id=tu["id"],
                            tool_result=ToolResult(
                                status="error",
                                content=[ToolResultBlock(type="text", text=str(e))],
                            ),
                        )
                    )

            # Create tool response message
            tool_msg = Message(
                role=Role.user,
                content=tool_response_content,
            )
            session.messages.append(tool_msg)

            # Emit tool responses + resource content as a combined message
            # Resource blocks are sent in a separate assistant message so they
            # render inline in the AI response area (not inside tool call)
            if resource_content_blocks:
                resource_msg = Message(
                    role=Role.assistant,
                    content=resource_content_blocks,
                )
                session.messages.append(resource_msg)
                yield MessageEvent(message=resource_msg)

            # Emit tool responses
            yield MessageEvent(message=tool_msg)

        yield FinishEvent(reason="max_iterations")


# Singleton
agent = Agent()
