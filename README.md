# MCP Apps Base Chatbot

A base chatbot that connects to **MCP (Model Context Protocol) servers** and renders their rich UI responses — product cards, weather dashboards, interactive editors — directly in the chat interface.

Use this as a starting point to build chat applications that integrate with any MCP-compatible tool server.

**[Blog Post](blog.md)** | **[MCP Apps Spec](https://modelcontextprotocol.io/extensions/apps/overview)** | **[MCP-UI Docs](https://mcpui.dev/guide/introduction)**

## Architecture

```
┌─────────────┐     SSE      ┌──────────────┐    stdio/http    ┌─────────────────┐
│   Frontend   │◄────────────►│   Backend    │◄────────────────►│  MCP Servers    │
│  React+Vite  │   /api/*     │  FastAPI     │   MCP Protocol   │  (tools + UI)   │
└─────────────┘              └──────────────┘                  └─────────────────┘
```

- **Frontend** — Chat UI with Remote DOM and `@mcp-ui/client` AppRenderer for MCP Apps content
- **Backend** — Session management, MCP server connections, LLM agent loop (Gemini)
- **MCP Servers** — Standalone tool servers returning rich UI via `EmbeddedResource` with `_meta.ui.resourceUri` on tool definitions

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

## MCP Apps & UI Rendering

MCP servers return rich UI content using two mechanisms that work together:

### 1. `_meta.ui.resourceUri` on Tool Definitions

Following the [MCP Apps specification](https://modelcontextprotocol.io/extensions/apps/overview), each tool declares its UI resource in the tool definition via `_meta.ui.resourceUri`. This tells hosts that the tool has an associated UI and where to find it.

```python
Tool(
    name="search_products",
    description="Search for products by category.",
    inputSchema={...},
    _meta={"ui": {"resourceUri": "ui://product-catalog/search-app"}},
)
```

Servers also register resource handlers so hosts can fetch the UI:

```python
@app.list_resources()
async def list_resources():
    return [
        Resource(
            uri="ui://product-catalog/search-app",
            name="Product Search UI",
            mimeType="application/vnd.mcp-ui.remote-dom",
        ),
    ]

@app.read_resource()
async def read_resource(uri):
    # Serve the UI content for the given URI
    ...
```

### 2. `EmbeddedResource` in Tool Responses

Tools return dynamic content per-call as `EmbeddedResource` objects with a URI and MIME type:

```
MCP Server tool response
  └── EmbeddedResource
        ├── uri       →  "ui://weather/London/current"
        ├── mimeType  →  "application/vnd.mcp-ui.remote-dom"  or  "text/html;profile=mcp-app"
        └── text      →  JSON component tree  or  HTML string
```

The **uri** serves two purposes:
1. **Identification** — names the content for debugging and display
2. **Deduplication** — when a new resource arrives with the same URI as a previous one, the frontend replaces the old instance instead of showing both (enables in-place updates)

The **mimeType** determines the rendering mode:

### Rendering Modes

#### Remote DOM (`application/vnd.mcp-ui.remote-dom`) — Custom

A JSON component tree rendered as native React elements with host theming. This is a custom rendering approach, not part of the official MCP Apps spec.

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

#### MCP Apps HTML (`text/html;profile=mcp-app`) — Official Standard

Full HTML rendered in a sandboxed iframe via `@mcp-ui/client`'s [AppRenderer](https://mcpui.dev). Theme CSS variables are passed through `hostContext.styles.variables`. The iframe can communicate back via the MCP Apps JSON-RPC protocol.

#### Plain HTML (`text/html`)

HTML rendered in a sandboxed iframe via the backend's proxy. The iframe can send actions back via:
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
| `ui://text-editor/{uuid}` | Text Editor | Editor instance |

## Included MCP Servers

| Server | Directory | Tools | `_meta.ui` | Rendering |
|--------|-----------|-------|------------|-----------|
| Product Catalog | `sample-mcp-server/` | `search_products`, `show_chart`, `render_html` | Yes | Remote DOM + HTML |
| Weather | `weather-mcp-server/` | `get_current_weather`, `get_forecast`, `search_cities` | Yes | Remote DOM |
| Text Editor | `text-editor-mcp-server/` | `open_editor` | Yes | MCP Apps HTML |

All servers declare `_meta.ui.resourceUri` on their tools and register resource handlers via `@app.list_resources()` and `@app.read_resource()`.

## Project Structure

```
mcp-apps-base-chatbot/
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── config.py         # System prompt, render_ui tool, MIME types
│   │   ├── services/
│   │   │   ├── agent.py      # Agentic loop (LLM + tool execution)
│   │   │   ├── mcp_manager.py # MCP connections, _meta.ui extraction
│   │   │   └── llm_service.py # Gemini API wrapper
│   │   ├── routes/
│   │   │   └── mcp_proxy.py  # Sandbox proxy for iframe content
│   │   └── models/           # Pydantic models (messages, sessions, extensions)
├── frontend/                 # React + Vite frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── McpAppRenderer.tsx    # Routes content to RemoteDom or AppRenderer
│   │   │   ├── RemoteDomRenderer.tsx # JSON tree → native React elements
│   │   │   ├── AssistantMessage.tsx  # Rich content detection + rendering
│   │   │   └── MessageList.tsx       # URI deduplication for in-place updates
│   │   ├── hooks/
│   │   │   └── useChatStream.ts      # SSE consumer + message state
│   │   └── types/
│   │       └── extension.ts          # ToolInfo with ui_resource_uri
├── sample-mcp-server/        # Product catalog MCP server
├── weather-mcp-server/        # Weather MCP server
└── text-editor-mcp-server/    # Text editor MCP server
```

## Building Your Own MCP Server

Create a new Python file using the `mcp` SDK:

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, EmbeddedResource, TextResourceContents, Resource
import json

app = Server("my-server")

REMOTE_DOM_MIME = "application/vnd.mcp-ui.remote-dom"
MY_TOOL_RESOURCE_URI = "ui://my-server/result-app"


# 1. Register resources (for _meta.ui.resourceUri discovery)
@app.list_resources()
async def list_resources():
    return [
        Resource(
            uri=MY_TOOL_RESOURCE_URI,
            name="My Tool UI",
            mimeType=REMOTE_DOM_MIME,
            description="Interactive result display.",
        ),
    ]

@app.read_resource()
async def read_resource(uri):
    placeholder = json.dumps({"type": "div", "children": ["Loading..."]})
    return [TextResourceContents(uri=uri, mimeType=REMOTE_DOM_MIME, text=placeholder)]


# 2. Register tools with _meta.ui.resourceUri
@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="my_tool",
            description="Returns a visual UI",
            inputSchema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            _meta={"ui": {"resourceUri": MY_TOOL_RESOURCE_URI}},
        ),
    ]


# 3. Return rich content in tool responses
@app.call_tool()
async def call_tool(name, arguments):
    tree = {
        "type": "div",
        "children": [
            {"type": "heading", "children": ["Hello World"]},
            {
                "type": "button",
                "action": "Tell me more about this",
                "children": ["Click Me"],
            },
        ],
    }

    return [
        TextContent(type="text", text="Here is the result."),
        EmbeddedResource(
            type="resource",
            resource=TextResourceContents(
                uri="ui://my-server/result",
                mimeType=REMOTE_DOM_MIME,
                text=json.dumps(tree),
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
- **`_meta.ui.resourceUri`** — Declares the tool's UI resource in the tool definition, following the [MCP Apps spec](https://modelcontextprotocol.io/extensions/apps/overview). Register corresponding resource handlers via `@app.list_resources()` and `@app.read_resource()`.
- **`uri`** — Use `ui://{server-name}/{path}` convention. Same URI across calls = frontend replaces previous content in-place.
- **`mimeType`** — Use `application/vnd.mcp-ui.remote-dom` for JSON component trees (custom), or `text/html;profile=mcp-app` for full HTML (official MCP Apps MIME type).
- **`action`** — Any node with an `action` property becomes clickable. The action text is sent as a new user message.
- **`TextContent`** — Always include a plain text summary alongside the rich content for non-UI clients and LLM reasoning.

Then connect it in the UI with `python3 /path/to/your/server.py`.

## Further Reading

- [MCP Apps Specification](https://modelcontextprotocol.io/extensions/apps/overview) — The official standard for interactive UIs in MCP
- [MCP Apps Build Guide](https://modelcontextprotocol.io/extensions/apps/build) — How to build with `_meta.ui.resourceUri` and the App class
- [MCP-UI Documentation](https://mcpui.dev/guide/introduction) — `@mcp-ui/client` library for host-side rendering
- [ext-apps Repository](https://github.com/modelcontextprotocol/ext-apps) — Official examples and SDK
