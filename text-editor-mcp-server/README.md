# Text Editor MCP Server

Interactive text editor with inline AI-powered refinement. Uses **HTML iframe** rendering for full interactivity.

## Run

```bash
python3 server.py
```

**Requires:** `mcp` Python package (`pip install mcp`)

## Connect

```
Type: stdio
Command: python3
Args: /path/to/text-editor-mcp-server/server.py
```

## Tools

### `open_editor`

Opens an interactive text editor.

- **text** (optional) — initial content
- **title** (optional) — editor title (default: "Text Editor")

### `update_editor`

Updates the editor with new content. Used after refining text — pass the complete text with only the refined portion replaced.

- **text** (required) — full updated text
- **title** (optional) — editor title

## How Refinement Works

1. Ask the LLM to open the editor with some text
2. **Select text** in the editor — a floating refinement bar appears
3. Type a refinement request (e.g., "make it more formal", "fix grammar", "translate to Spanish")
4. Click **Refine** — the request is sent as a chat message
5. The LLM refines only the selected portion and calls `update_editor`
6. The editor updates in-place (previous editor instance is replaced via URI deduplication)

## Features

- Full textarea with dark theme
- Text selection detection with floating refinement input
- Copy to clipboard button
- Send full text to chat button
- Character count
- In-place updates (same URI `ui://text-editor/main`)

## Example Queries

- "Open a text editor"
- "Open the editor with a paragraph about climate change"
- "Write a product description in the text editor"
