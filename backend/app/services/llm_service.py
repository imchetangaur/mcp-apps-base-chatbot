"""LLM Service — Google Gemini API with tool use and streaming."""

from __future__ import annotations

import json
import uuid
from typing import AsyncIterator

from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY, DEFAULT_MODEL


class LLMService:
    """Calls Gemini API with tool-use support and streaming."""

    def __init__(self):
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        if self._client is None:
            if not GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY is not set. Add it to backend/.env")
            self._client = genai.Client(api_key=GEMINI_API_KEY)
        return self._client

    def _convert_tools(self, tools: list[dict]) -> list[types.Tool]:
        """Convert our tool format to Gemini function declarations."""
        declarations = []
        for tool in tools:
            # Convert JSON Schema to Gemini Schema
            input_schema = tool.get("input_schema", {})
            properties = input_schema.get("properties", {})
            required = input_schema.get("required", [])

            gemini_props = {}
            for prop_name, prop_def in properties.items():
                prop_type = prop_def.get("type", "STRING").upper()
                # Map JSON Schema types to Gemini types
                type_map = {
                    "STRING": "STRING",
                    "NUMBER": "NUMBER",
                    "INTEGER": "INTEGER",
                    "BOOLEAN": "BOOLEAN",
                    "ARRAY": "ARRAY",
                    "OBJECT": "OBJECT",
                }
                gemini_type = type_map.get(prop_type, "STRING")
                gemini_props[prop_name] = types.Schema(
                    type=gemini_type,
                    description=prop_def.get("description", ""),
                )

            decl = types.FunctionDeclaration(
                name=tool["name"],
                description=tool.get("description", ""),
                parameters=types.Schema(
                    type="OBJECT",
                    properties=gemini_props,
                    required=required,
                ) if gemini_props else None,
            )
            declarations.append(decl)

        return [types.Tool(function_declarations=declarations)]

    def _convert_messages(
        self, messages: list[dict], system: str
    ) -> tuple[str, list[types.Content]]:
        """Convert our message format to Gemini contents."""
        contents = []
        for msg in messages:
            role = "model" if msg["role"] == "assistant" else "user"
            parts = []
            for block in msg["content"]:
                if block.get("type") == "text":
                    parts.append(types.Part.from_text(text=block["text"]))
                elif block.get("type") == "tool_use":
                    # Function call from model
                    parts.append(
                        types.Part.from_function_call(
                            name=block["name"],
                            args=block.get("input", {}),
                        )
                    )
                elif block.get("type") == "tool_result":
                    # Function response from user
                    parts.append(
                        types.Part.from_function_response(
                            name=block.get("tool_name", "unknown"),
                            response={"result": block.get("content", "")},
                        )
                    )
            if parts:
                contents.append(types.Content(role=role, parts=parts))
        return system, contents

    async def chat_completion(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str = "You are a helpful AI assistant.",
    ) -> AsyncIterator[dict]:
        """
        Stream a chat completion from Gemini.
        Yields event dicts:
          - {"type": "text_delta", "text": "..."}
          - {"type": "tool_use", "id": "...", "name": "...", "input": {...}}
          - {"type": "message_stop", "stop_reason": "..."}
        """
        system_instruction, contents = self._convert_messages(messages, system)

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=4096,
        )
        if tools:
            config.tools = self._convert_tools(tools)

        # Use streaming
        client = self._get_client()
        response = client.models.generate_content_stream(
            model=DEFAULT_MODEL,
            contents=contents,
            config=config,
        )

        has_tool_calls = False
        for chunk in response:
            if not chunk.candidates:
                continue

            candidate = chunk.candidates[0]

            for part in candidate.content.parts:
                if part.text:
                    yield {"type": "text_delta", "text": part.text}
                elif part.function_call:
                    has_tool_calls = True
                    # Convert function call args to dict
                    args = dict(part.function_call.args) if part.function_call.args else {}
                    yield {
                        "type": "tool_use",
                        "id": f"call_{uuid.uuid4().hex[:12]}",
                        "name": part.function_call.name,
                        "input": args,
                    }

        stop_reason = "tool_use" if has_tool_calls else "end_turn"
        yield {"type": "message_stop", "stop_reason": stop_reason}


# Singleton
llm_service = LLMService()
