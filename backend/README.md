# Backend

FastAPI backend for MCP Apps Base Chatbot.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env   # Add your API key
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `DEFAULT_MODEL` | No | Model name (default: `gemini-2.0-flash`) |

## API Endpoints

### Sessions

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/sessions` | Create a new chat session |
| `GET` | `/api/sessions` | List all sessions |
| `GET` | `/api/sessions/{id}` | Get session with messages |
| `PUT` | `/api/sessions/{id}/name` | Rename a session |
| `DELETE` | `/api/sessions/{id}` | Delete a session |

### Chat

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/sessions/{id}/reply` | Send a message, receive SSE stream |

The `/reply` endpoint returns Server-Sent Events:
- `Message` — assistant message (text, tool requests, tool responses)
- `Error` — error notification
- `Finish` — stream complete
- `Ping` — heartbeat

### MCP Extensions

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/sessions/{id}/extensions` | Connect an MCP server |
| `GET` | `/api/sessions/{id}/extensions` | List connected servers |
| `DELETE` | `/api/sessions/{id}/extensions/{name}` | Disconnect a server |
| `GET` | `/api/sessions/{id}/tools` | List discovered tools |

### MCP Proxy

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/mcp-proxy/sandbox` | Sandbox iframe host page |
| `POST` | `/api/mcp-proxy/guest` | Store HTML for iframe rendering |
| `GET` | `/api/mcp-proxy/guest` | Retrieve stored HTML by nonce |

## Architecture

```
app/
├── main.py              # FastAPI app, CORS, lifespan hooks
├── config.py            # Environment-based settings
├── models/
│   ├── messages.py      # Message, content block types
│   ├── sessions.py      # Session model, request schemas
│   ├── extensions.py    # MCP server config (stdio/http)
│   └── events.py        # SSE event types
├── routes/
│   ├── sessions.py      # Session CRUD endpoints
│   ├── chat.py          # /reply SSE streaming endpoint
│   ├── extensions.py    # MCP server management
│   └── mcp_proxy.py     # Iframe sandbox proxy
└── services/
    ├── session_manager.py  # In-memory session store
    ├── mcp_manager.py      # MCP client lifecycle, tool routing
    ├── llm_service.py      # Gemini API with tool use + streaming
    └── agent.py            # Agent loop: message → LLM → tools → loop
```

### Agent Loop

The core flow in `agent.py`:

1. User message appended to conversation
2. Get available tools from `mcp_manager`
3. Call LLM with conversation + tool definitions (streaming)
4. If LLM returns text → yield `MessageEvent`
5. If LLM returns `tool_use` → yield tool request, execute via `mcp_manager`, yield tool response, loop back to step 3
6. If LLM stops → yield `FinishEvent`

### MCP Manager

Manages per-session MCP server connections:

- **stdio**: Spawns subprocess via `mcp.client.stdio.stdio_client`
- **streamable_http**: Connects via `mcp.client.streamable_http.streamablehttp_client`
- Tool names prefixed with `{server_name}__` to avoid collisions
- Background tasks keep connections alive until cancelled

## Dependencies

Defined in `pyproject.toml`:
- `fastapi` — web framework
- `uvicorn` — ASGI server
- `pydantic` v2 — data models
- `google-genai` — Gemini LLM API
- `mcp` — MCP client SDK
- `python-dotenv` — env var loading
