"""
Text Editor MCP Server — provides an interactive text editor with inline refinement.

Tools:
  open_editor  — Opens the editor with optional initial text

The editor supports:
  - Editable text area
  - Text selection → floating refinement input
  - Refinement calls /api/refine directly and updates textarea in-place

Run:   python3 server.py
Connect: stdio (cmd: python3, args: [path/to/server.py])
"""

import json
import uuid
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, EmbeddedResource, TextResourceContents, Resource

app = Server("text-editor")

MCP_APP_MIME = "text/html;profile=mcp-app"
EDITOR_RESOURCE_URI = "ui://text-editor/editor-app"


def _build_editor_html(text: str, title: str = "Text Editor") -> str:
    """Build a self-contained HTML editor with selection-based refinement UI."""
    escaped_text = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )

    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: 'Red Hat Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg-primary, #151515);
    color: var(--text-primary, #ffffff);
    padding: 16px;
    min-height: 100%;
  }}

  .editor-container {{
    position: relative;
    width: 100%;
  }}

  .editor-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }}

  .editor-title {{
    font-size: 14px;
    font-weight: 600;
    color: var(--text-secondary, #c7c7c7);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}

  .editor-textarea {{
    width: 100%;
    min-height: 200px;
    background: var(--bg-secondary, #1f1f1f);
    border: 1px solid var(--border, #383838);
    border-radius: 10px;
    padding: 16px;
    color: var(--text-primary, #ffffff);
    font-family: 'Red Hat Text', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 14px;
    line-height: 1.7;
    resize: vertical;
    outline: none;
    transition: border-color 0.2s;
  }}

  .editor-textarea:focus {{
    border-color: var(--accent, #92c5f9);
  }}

  .editor-textarea.refining {{
    opacity: 0.6;
    pointer-events: none;
  }}

  /* Floating refinement bar */
  .refine-bar {{
    display: none;
    position: fixed;
    background: var(--bg-surface, #292929);
    border: 1px solid var(--border, #383838);
    border-radius: 10px;
    padding: 8px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
    z-index: 1000;
    min-width: 320px;
    max-width: 420px;
    animation: refine-in 0.15s ease;
  }}

  .refine-bar.visible {{
    display: block;
  }}

  @keyframes refine-in {{
    from {{ opacity: 0; transform: translateY(4px); }}
    to {{ opacity: 1; transform: translateY(0); }}
  }}

  .refine-selected-preview {{
    font-size: 12px;
    color: var(--text-muted, #707070);
    margin-bottom: 6px;
    padding: 0 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}

  .refine-selected-preview span {{
    color: var(--accent, #92c5f9);
    font-weight: 500;
  }}

  .refine-input-row {{
    display: flex;
    gap: 6px;
  }}

  .refine-input {{
    flex: 1;
    background: var(--bg-secondary, #1f1f1f);
    border: 1px solid var(--border, #383838);
    border-radius: 8px;
    padding: 8px 12px;
    color: var(--text-primary, #ffffff);
    font-size: 13px;
    font-family: inherit;
    outline: none;
    transition: border-color 0.2s;
  }}

  .refine-input:focus {{
    border-color: var(--accent, #92c5f9);
  }}

  .refine-input::placeholder {{
    color: var(--text-muted, #707070);
  }}

  .refine-submit {{
    background: var(--accent, #92c5f9);
    color: var(--bg-primary, #151515);
    border: none;
    padding: 8px 14px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    font-family: inherit;
    white-space: nowrap;
    transition: background 0.15s;
  }}

  .refine-submit:hover {{
    background: var(--accent-hover, #b9dafc);
  }}

  .refine-submit:disabled {{
    opacity: 0.5;
    cursor: not-allowed;
  }}

  .refine-close {{
    background: none;
    border: none;
    color: var(--text-muted, #707070);
    cursor: pointer;
    padding: 8px 10px;
    border-radius: 8px;
    font-size: 13px;
    transition: color 0.15s;
  }}

  .refine-close:hover {{
    color: var(--text-primary, #ffffff);
  }}

  /* Status bar */
  .status-bar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 8px;
    font-size: 11px;
    color: var(--text-muted, #707070);
  }}

  .refine-status {{
    color: var(--accent, #92c5f9);
    font-weight: 500;
  }}
</style>
</head>
<body>
  <div class="editor-container">
    <div class="editor-header">
      <span class="editor-title">{title}</span>
    </div>

    <textarea class="editor-textarea" id="editor" spellcheck="false">{escaped_text}</textarea>

    <div class="status-bar">
      <span id="char-count"></span>
      <span id="status-text">Select text to refine</span>
    </div>
  </div>

  <!-- Floating refinement bar -->
  <div class="refine-bar" id="refineBar">
    <div class="refine-selected-preview" id="refinePreview"></div>
    <div class="refine-input-row">
      <input
        class="refine-input"
        id="refineInput"
        type="text"
        placeholder="How should this be refined?"
        autocomplete="off"
      />
      <button class="refine-submit" id="refineBtn" onclick="submitRefinement()">Refine</button>
      <button class="refine-close" onclick="closeRefineBar()">&#10005;</button>
    </div>
  </div>

  <script>
    var editor = document.getElementById('editor');
    var refineBar = document.getElementById('refineBar');
    var refineInput = document.getElementById('refineInput');
    var refinePreview = document.getElementById('refinePreview');
    var refineBtn = document.getElementById('refineBtn');
    var charCount = document.getElementById('char-count');
    var statusText = document.getElementById('status-text');

    var selectedText = '';
    var selStart = 0;
    var selEnd = 0;

    function updateCount() {{
      var len = editor.value.length;
      charCount.textContent = len + ' character' + (len !== 1 ? 's' : '');
    }}
    updateCount();
    editor.addEventListener('input', updateCount);

    editor.addEventListener('mouseup', handleSelection);
    editor.addEventListener('keyup', function(e) {{
      if (e.shiftKey) handleSelection();
    }});

    function handleSelection() {{
      var start = editor.selectionStart;
      var end = editor.selectionEnd;
      var selected = editor.value.substring(start, end).trim();

      if (selected.length > 0) {{
        selectedText = selected;
        selStart = start;
        selEnd = end;
        showRefineBar();
      }} else {{
        closeRefineBar();
      }}
    }}

    function showRefineBar() {{
      var rect = editor.getBoundingClientRect();
      var preview = selectedText.length > 50
        ? selectedText.substring(0, 50) + '...'
        : selectedText;
      refinePreview.innerHTML = 'Selected: <span>"' + preview.replace(/</g, '&lt;') + '"</span>';

      refineBar.style.left = rect.left + 'px';
      refineBar.style.top = (rect.bottom + 8) + 'px';
      refineBar.style.width = Math.min(rect.width, 420) + 'px';
      refineBar.classList.add('visible');
      refineInput.value = '';
      refineInput.focus();
    }}

    function closeRefineBar() {{
      refineBar.classList.remove('visible');
      selectedText = '';
      refineInput.value = '';
    }}

    function submitRefinement() {{
      var instruction = refineInput.value.trim();
      if (!instruction || !selectedText) return;

      var fullText = editor.value;
      var selText = selectedText;

      refineBtn.disabled = true;
      refineBtn.textContent = 'Refining...';
      editor.classList.add('refining');
      statusText.textContent = 'Refining...';
      statusText.className = 'refine-status';

      closeRefineBar();

      fetch('/api/refine', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{
          full_text: fullText,
          selected_text: selText,
          instruction: instruction
        }})
      }})
      .then(function(res) {{ return res.json(); }})
      .then(function(data) {{
        if (data.refined_text) {{
          editor.value = data.refined_text;
          updateCount();
        }}
        statusText.textContent = 'Select text to refine';
        statusText.className = '';
      }})
      .catch(function(err) {{
        statusText.textContent = 'Refinement failed';
        statusText.className = '';
      }})
      .finally(function() {{
        refineBtn.disabled = false;
        refineBtn.textContent = 'Refine';
        editor.classList.remove('refining');
      }});
    }}

    refineInput.addEventListener('keydown', function(e) {{
      if (e.key === 'Enter') {{
        e.preventDefault();
        submitRefinement();
      }}
      if (e.key === 'Escape') {{
        closeRefineBar();
        editor.focus();
      }}
    }});

    // Notify parent of height
    function notifyHeight() {{
      var h = document.documentElement.scrollHeight;
      window.parent.postMessage({{ type: 'resize', height: h }}, '*');
    }}
    new ResizeObserver(notifyHeight).observe(document.body);
    setTimeout(notifyHeight, 100);
  </script>
</body>
</html>'''


@app.list_resources()
async def list_resources():
    return [
        Resource(
            uri=EDITOR_RESOURCE_URI,
            name="Text Editor UI",
            mimeType=MCP_APP_MIME,
            description="Interactive text editor with inline AI refinement support.",
        ),
    ]


@app.read_resource()
async def read_resource(uri):
    uri_str = str(uri)
    if uri_str == EDITOR_RESOURCE_URI:
        html = _build_editor_html("", "Text Editor")
        return [TextResourceContents(uri=uri, mimeType=MCP_APP_MIME, text=html)]
    return [TextResourceContents(uri=uri, mimeType="text/plain", text="Unknown resource")]


@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="open_editor",
            description="Open an interactive text editor. The user can edit text, select portions, and request inline AI refinements. Returns a rich UI editor component.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Initial text content for the editor. If empty, opens a blank editor.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Title shown above the editor (default: 'Text Editor')",
                    },
                },
                "required": [],
            },
            _meta={"ui": {"resourceUri": EDITOR_RESOURCE_URI}},
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "open_editor":
        text = arguments.get("text", "")
        title = arguments.get("title", "Text Editor")
        html = _build_editor_html(text, title)

        editor_uri = f"ui://text-editor/{uuid.uuid4().hex[:8]}"

        return [
            TextContent(type="text", text="Opened the text editor."),
            EmbeddedResource(
                type="resource",
                resource=TextResourceContents(
                    uri=editor_uri,
                    mimeType=MCP_APP_MIME,
                    text=html,
                ),
            ),
        ]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        init_options = app.create_initialization_options()
        await app.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
