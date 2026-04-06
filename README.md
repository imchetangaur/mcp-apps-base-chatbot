# MCP Apps Base Chatbot

A base chatbot that connects to **MCP (Model Context Protocol) servers** and renders their rich UI responses — product cards, weather dashboards, interactive editors — directly in the chat interface.

Use this as a starting point to build chat applications that integrate with any MCP-compatible tool server.

## Architecture

```
┌─────────────┐     SSE      ┌──────────────┐    stdio/http    ┌─────────────────┐
│   Frontend   │◄────────────►│   Backend    │◄────────────────►│  MCP Servers    │
│  React+Vite  │   /api/*     │  FastAPI     │   MCP Protocol   │  (tools + UI)   │
└─────────────┘              └──────────────┘                  └─────────────────┘
```

- **Frontend** — Chat UI with Remote DOM and iframe rendering for MCP content
- **Backend** — Session management, MCP server connections, LLM agent loop (Gemini)
- **MCP Servers** — Standalone tool servers returning rich UI via `EmbeddedResource`

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Gemini API key](https://aistudio.google.com/apikey)

### 1. Start the backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env   # Add your GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000
```

### 2. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

### 3. Connect MCP servers

Click the **gear icon** in the chat header, then add servers:

| Server | Type | Command | Args |
|--------|------|---------|------|
| Product Catalog | stdio | `python3` | `/path/to/sample-mcp-server/server.py` |
| Weather | stdio | `python3` | `/path/to/weather-mcp-server/server.py` |
| Text Editor | stdio | `python3` | `/path/to/text-editor-mcp-server/server.py` |

## MCP-UI Rendering

MCP servers return rich UI content inside an `EmbeddedResource` with a **URI** and a **mimeType**. The frontend detects these in tool responses and renders them inline in the chat.

### How It Works

```
MCP Server tool response
  └── EmbeddedResource
        ├── uri       →  "ui://weather/London/current"     (identifies the content)
        ├── mimeType  →  "application/vnd.mcp-ui.remote-dom"  or  "text/html"
        └── text      →  JSON component tree  or  HTML string
```

The **uri** serves two purposes:
1. **Identification** — names the content for debugging and display
2. **Deduplication** — when a new resource arrives with the same URI as a previous one, the frontend replaces the old instance instead of showing both. This enables in-place updates (e.g., the text editor uses `ui://text-editor/main` so `update_editor` replaces the previous editor).

The **mimeType** determines the rendering mode:

### Remote DOM (`application/vnd.mcp-ui.remote-dom`)

A JSON component tree rendered as native React elements with host theming:

```json
{
  "type": "card",
  "action": "Show details for this product",
  "children": [
    { "type": "heading", "children": ["Product Name"] },
    { "type": "price", "children": ["$99"] }
  ]
}
```

Supported types: `card`, `grid`, `heading`, `badge`, `price`, `button`, `description`, `subtitle`, `text`, `row`, `col`, `spacer` — plus any standard HTML tag.

Nodes with an `action` property become clickable — clicking sends the action text as a new chat message, triggering the LLM agent loop.

### HTML (`text/html`)

Full HTML rendered in a sandboxed iframe via the backend's proxy. The iframe can send actions back via:
```js
window.parent.postMessage({ type: 'mcp-action', text: 'user action' }, '*');
```

### URI Convention

MCP servers should use a `ui://` scheme for their resource URIs:

```
ui://{server-name}/{resource-type}/{identifier}
```

Examples from the included servers:

| URI | Server | Description |
|-----|--------|-------------|
| `ui://product-catalog/shoes` | Product Catalog | Shoes product grid |
| `ui://product-catalog/chart/sales` | Product Catalog | Sales bar chart |
| `ui://weather/London/current` | Weather | Current weather for London |
| `ui://weather/London/forecast/3` | Weather | 3-day forecast |
| `ui://weather/search/tokyo` | Weather | City search results |
| `ui://text-editor/main` | Text Editor | Editor instance (always same URI for in-place updates) |

## Included MCP Servers

| Server | Directory | Description |
|--------|-----------|-------------|
| Product Catalog | `sample-mcp-server/` | Product cards, bar charts, custom HTML |
| Weather | `weather-mcp-server/` | Live weather cards with WeatherAPI.com |
| Text Editor | `text-editor-mcp-server/` | Interactive editor with inline AI refinement |

See each server's README for details.

## Project Structure

```
mcp-apps-base-chatbot/
├── backend/                  # FastAPI backend
├── frontend/                 # React + Vite frontend
├── sample-mcp-server/        # Product catalog MCP server
├── weather-mcp-server/       # Weather MCP server
└── text-editor-mcp-server/   # Text editor MCP server
```

## Building Your Own MCP Server

Create a new Python file using the `mcp` SDK:

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, EmbeddedResource, TextResourceContents
import json

app = Server("my-server")

@app.list_tools()
async def list_tools():
    return [Tool(name="my_tool", description="...", inputSchema={...})]

@app.call_tool()
async def call_tool(name, arguments):
    # Build a Remote DOM component tree
    tree = {
        "type": "div",
        "children": [
            {"type": "heading", "children": ["Hello World"]},
            {
                "type": "button",
                "action": "Tell me more about this",   # Clicking sends this as a chat message
                "children": ["Click Me"],
            },
        ],
    }

    return [
        # Plain text fallback (shown in tool call accordion)
        TextContent(type="text", text="Here is the result."),
        # Rich UI content (rendered inline in chat)
        EmbeddedResource(
            type="resource",
            resource=TextResourceContents(
                uri="ui://my-server/result",                    # Unique URI for this content
                mimeType="application/vnd.mcp-ui.remote-dom",   # Tells frontend to use Remote DOM renderer
                text=json.dumps(tree),                          # The JSON component tree
            ),
        ),
    ]

if __name__ == "__main__":
    import asyncio
    async def main():
        async with stdio_server() as (r, w):
            await app.run(r, w, app.create_initialization_options())
    asyncio.run(main())
```

Key points:
- **`uri`** — use `ui://{server-name}/{path}` convention. Use the same URI across calls if you want the frontend to replace previous content in-place.
- **`mimeType`** — use `application/vnd.mcp-ui.remote-dom` for JSON component trees, or `text/html` for full HTML (rendered in iframe).
- **`action`** — any node with an `action` property becomes clickable. The action text is sent as a new user message.
- **`TextContent`** — always include a plain text summary alongside the rich content for non-UI clients.

Then connect it in the UI with `python3 /path/to/your/server.py`.
