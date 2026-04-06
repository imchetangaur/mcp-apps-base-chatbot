"""
Text Editor MCP Server — provides an interactive text editor with inline refinement.

Tools:
  open_editor  — Opens the editor with optional initial text
  update_editor — Updates the editor content (used after refinement)

The editor supports:
  - Editable text area
  - Text selection → floating refinement input
  - Actions sent via postMessage to trigger LLM refinement
  - In-place text updates (same editor, new content)

Run:   python3 server.py
Connect: stdio (cmd: python3, args: [path/to/server.py])
"""

import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, EmbeddedResource, TextResourceContents

app = Server("text-editor")

# Every editor response uses the same URI so the frontend can replace previous instances
EDITOR_URI = "ui://text-editor/main"


def _build_editor_html(text: str, title: str = "Text Editor") -> str:
    """Build a self-contained HTML editor with selection-based refinement UI."""
    # Escape text for embedding in HTML
    escaped_text = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )

    # Escape text for embedding in JavaScript string
    js_text = (
        text.replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("$", "\\$")
    )

    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: 'Red Hat Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #151515;
    color: #ffffff;
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
    color: #c7c7c7;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}

  .editor-actions {{
    display: flex;
    gap: 8px;
  }}

  .editor-btn {{
    background: #292929;
    border: 1px solid #383838;
    color: #c7c7c7;
    padding: 5px 12px;
    border-radius: 6px;
    font-size: 12px;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s;
  }}

  .editor-btn:hover {{
    background: #383838;
    color: #ffffff;
  }}

  .editor-btn.primary {{
    background: #92c5f9;
    color: #151515;
    border-color: #92c5f9;
    font-weight: 600;
  }}

  .editor-btn.primary:hover {{
    background: #b9dafc;
  }}

  .editor-textarea {{
    width: 100%;
    min-height: 200px;
    background: #1f1f1f;
    border: 1px solid #383838;
    border-radius: 10px;
    padding: 16px;
    color: #ffffff;
    font-family: 'Red Hat Text', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 14px;
    line-height: 1.7;
    resize: vertical;
    outline: none;
    transition: border-color 0.2s;
  }}

  .editor-textarea:focus {{
    border-color: #92c5f9;
  }}

  /* Floating refinement bar */
  .refine-bar {{
    display: none;
    position: fixed;
    background: #292929;
    border: 1px solid #383838;
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
    color: #707070;
    margin-bottom: 6px;
    padding: 0 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}

  .refine-selected-preview span {{
    color: #92c5f9;
    font-weight: 500;
  }}

  .refine-input-row {{
    display: flex;
    gap: 6px;
  }}

  .refine-input {{
    flex: 1;
    background: #1f1f1f;
    border: 1px solid #383838;
    border-radius: 8px;
    padding: 8px 12px;
    color: #ffffff;
    font-size: 13px;
    font-family: inherit;
    outline: none;
    transition: border-color 0.2s;
  }}

  .refine-input:focus {{
    border-color: #92c5f9;
  }}

  .refine-input::placeholder {{
    color: #707070;
  }}

  .refine-submit {{
    background: #92c5f9;
    color: #151515;
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
    background: #b9dafc;
  }}

  .refine-close {{
    background: none;
    border: none;
    color: #707070;
    cursor: pointer;
    padding: 8px 10px;
    border-radius: 8px;
    font-size: 13px;
    transition: color 0.15s;
  }}

  .refine-close:hover {{
    color: #ffffff;
  }}

  /* Status bar */
  .status-bar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 8px;
    font-size: 11px;
    color: #707070;
  }}

  .status-hint {{
    display: flex;
    align-items: center;
    gap: 4px;
  }}

  .status-hint kbd {{
    background: #292929;
    border: 1px solid #383838;
    border-radius: 3px;
    padding: 1px 5px;
    font-size: 10px;
    font-family: 'Red Hat Mono', monospace;
  }}
</style>
</head>
<body>
  <div class="editor-container">
    <div class="editor-header">
      <span class="editor-title">{title}</span>
      <div class="editor-actions">
        <button class="editor-btn" onclick="copyText()">Copy</button>
        <button class="editor-btn primary" onclick="sendFullText()">Send to Chat</button>
      </div>
    </div>

    <textarea class="editor-textarea" id="editor" spellcheck="false">{escaped_text}</textarea>

    <div class="status-bar">
      <span id="char-count"></span>
      <span class="status-hint">Select text to refine</span>
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
      <button class="refine-submit" onclick="submitRefinement()">Refine</button>
      <button class="refine-close" onclick="closeRefineBar()">&#10005;</button>
    </div>
  </div>

  <script>
    const editor = document.getElementById('editor');
    const refineBar = document.getElementById('refineBar');
    const refineInput = document.getElementById('refineInput');
    const refinePreview = document.getElementById('refinePreview');
    const charCount = document.getElementById('char-count');

    let selectedText = '';
    let selStart = 0;
    let selEnd = 0;

    // Update character count
    function updateCount() {{
      const len = editor.value.length;
      charCount.textContent = len + ' character' + (len !== 1 ? 's' : '');
    }}
    updateCount();
    editor.addEventListener('input', updateCount);

    // Detect text selection in textarea
    editor.addEventListener('mouseup', handleSelection);
    editor.addEventListener('keyup', function(e) {{
      if (e.shiftKey) handleSelection();
    }});

    function handleSelection() {{
      const start = editor.selectionStart;
      const end = editor.selectionEnd;
      const selected = editor.value.substring(start, end).trim();

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
      // Position near the textarea
      const rect = editor.getBoundingClientRect();
      const preview = selectedText.length > 50
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

    // Submit refinement request via postMessage → chat action
    function submitRefinement() {{
      const instruction = refineInput.value.trim();
      if (!instruction || !selectedText) return;

      const fullText = editor.value;

      // Send structured action message for the LLM
      const action = [
        'Refine my text in the editor.',
        'FULL TEXT:',
        '<<<',
        fullText,
        '>>>',
        'SELECTED TEXT TO REFINE:',
        '<<<',
        selectedText,
        '>>>',
        'REFINEMENT REQUEST: ' + instruction,
        '',
        'Use the update_editor tool with the complete updated text (replace only the selected portion, keep everything else exactly the same).'
      ].join('\\n');

      window.parent.postMessage({{ type: 'mcp-action', text: action }}, '*');
      closeRefineBar();
    }}

    // Enter key submits refinement
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

    // Send full text to chat
    function sendFullText() {{
      const text = editor.value;
      window.parent.postMessage({{
        type: 'mcp-action',
        text: 'Here is my edited text:\\n\\n' + text
      }}, '*');
    }}

    // Copy text to clipboard
    function copyText() {{
      navigator.clipboard.writeText(editor.value).then(function() {{
        const btn = document.querySelector('.editor-btn');
        btn.textContent = 'Copied!';
        setTimeout(function() {{ btn.textContent = 'Copy'; }}, 1500);
      }});
    }}

    // Listen for text updates from parent (for in-place replacement)
    window.addEventListener('message', function(e) {{
      if (e.data && e.data.type === 'update-editor-text') {{
        editor.value = e.data.text;
        updateCount();
      }}
    }});

    // Notify parent of height
    function notifyHeight() {{
      const h = document.documentElement.scrollHeight;
      window.parent.postMessage({{ type: 'resize', height: h }}, '*');
    }}
    new ResizeObserver(notifyHeight).observe(document.body);
    setTimeout(notifyHeight, 100);
  </script>
</body>
</html>'''


@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="open_editor",
            description="Open an interactive text editor. The user can edit text, select portions, and request inline refinements. Returns a rich UI editor component.",
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
        ),
        Tool(
            name="update_editor",
            description=(
                "Update the text editor content with refined/modified text. "
                "Use this after refining a portion of the user's text. "
                "Pass the COMPLETE text with the refined portion replaced — "
                "do NOT pass only the changed part."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The complete updated text (with the refined portion already replaced in context)",
                    },
                    "title": {
                        "type": "string",
                        "description": "Title shown above the editor (default: 'Text Editor')",
                    },
                },
                "required": ["text"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "open_editor":
        text = arguments.get("text", "")
        title = arguments.get("title", "Text Editor")
        html = _build_editor_html(text, title)

        return [
            TextContent(type="text", text="Opened the text editor."),
            EmbeddedResource(
                type="resource",
                resource=TextResourceContents(
                    uri=EDITOR_URI,
                    mimeType="text/html",
                    text=html,
                ),
            ),
        ]

    elif name == "update_editor":
        text = arguments.get("text", "")
        title = arguments.get("title", "Text Editor")
        html = _build_editor_html(text, title)

        return [
            TextContent(type="text", text="Updated the editor with refined text."),
            EmbeddedResource(
                type="resource",
                resource=TextResourceContents(
                    uri=EDITOR_URI,
                    mimeType="text/html",
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
