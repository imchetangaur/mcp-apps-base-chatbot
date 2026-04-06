# Frontend

React + TypeScript + Vite frontend for MCP Apps Base Chatbot.

## Setup

```bash
npm install
```

## Run

```bash
npm run dev        # Dev server at http://localhost:5173
npm run build      # Production build
npm run preview    # Preview production build
```

The dev server proxies `/api` requests to `http://localhost:8000` (backend).

## Key Components

### Chat UI


| Component          | File                   | Description                                               |
| ------------------ | ---------------------- | --------------------------------------------------------- |
| `App`              | `App.tsx`              | Root layout with collapsible sidebar                      |
| `SessionSidebar`   | `SessionSidebar.tsx`   | Session list, new chat, collapse toggle                   |
| `ChatView`         | `ChatView.tsx`         | Chat orchestrator — messages, input, extensions panel     |
| `MessageList`      | `MessageList.tsx`      | Scrollable message list with thinking indicator           |
| `ChatInput`        | `ChatInput.tsx`        | Text input with embedded send button                      |
| `UserMessage`      | `UserMessage.tsx`      | Right-aligned user message bubble                         |
| `AssistantMessage` | `AssistantMessage.tsx` | Left-aligned AI response with tool calls and rich content |
| `ToolCallDisplay`  | `ToolCallDisplay.tsx`  | Expandable tool call accordion                            |
| `ExtensionManager` | `ExtensionManager.tsx` | Add/remove MCP servers                                    |


### MCP-UI Rendering


| Component           | File                    | Description                                          |
| ------------------- | ----------------------- | ---------------------------------------------------- |
| `McpAppRenderer`    | `McpAppRenderer.tsx`    | Routes between Remote DOM and iframe modes           |
| `RemoteDomRenderer` | `RemoteDomRenderer.tsx` | Renders JSON component tree as native React elements |


**Remote DOM** — MCP servers return `application/vnd.mcp-ui.remote-dom` JSON. The renderer maps custom types (`card`, `grid`, `heading`, `badge`, `price`, `button`, etc.) to themed HTML elements using CSS variables from the host theme.

**HTML iframe** — MCP servers return `text/html` rendered in a sandboxed iframe via the backend's proxy. Supports bidirectional communication via `postMessage`.

**URI-based deduplication** — When multiple tool calls return resources with the same URI (e.g., `ui://text-editor/main`), only the latest instance is rendered. Previous instances are suppressed. This enables in-place content updates.

### Hooks


| Hook                | File                   | Description                                       |
| ------------------- | ---------------------- | ------------------------------------------------- |
| `useChatStream`     | `useChatStream.ts`     | SSE stream consumer, message state, submit/cancel |
| `useSessionManager` | `useSessionManager.ts` | Session CRUD with auto-refresh                    |


### API Layer


| Module       | File                | Description                            |
| ------------ | ------------------- | -------------------------------------- |
| `client`     | `api/client.ts`     | Fetch wrapper (GET, POST, PUT, DELETE) |
| `sessions`   | `api/sessions.ts`   | Session API calls + rename             |
| `chat`       | `api/chat.ts`       | SSE stream consumer for `/reply`       |
| `extensions` | `api/extensions.ts` | MCP server management API              |


## Styling

Single CSS file at `src/styles/index.css` using CSS custom properties:

```css
--bg-primary: #151515    /* page background */
--bg-secondary: #1f1f1f  /* sidebar, headers */
--bg-surface: #292929    /* cards, inputs */
--border: #383838        /* borders */
--accent: #92c5f9        /* links, buttons */
--text-primary: #ffffff  /* headings */
--text-secondary: #c7c7c7
--text-muted: #707070
```

Responsive breakpoints at 1024px, 768px, and 480px. Sidebar collapses to an overlay on mobile.

## Adding MCP-UI Support to Your Own Frontend

To render MCP tool responses as rich UI:

1. Check tool result `mimeType` — if `application/vnd.mcp-ui.remote-dom`, parse JSON and pass to `RemoteDomRenderer`
2. If `text/html`, render in a sandboxed iframe
3. Handle `onAction` callbacks — when users click interactive elements, the action text is submitted as a new chat message

