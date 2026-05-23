import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.0-flash")

# ── MIME types ─────────────────────────────────────────────────────
MCP_APP_MIME = "text/html;profile=mcp-app"
REMOTE_DOM_MIME = "application/vnd.mcp-ui.remote-dom"

# ── render_ui tool definition ──────────────────────────────────────
RENDER_UI_TOOL = {
    "name": "render_ui",
    "description": (
        "Render a rich interactive UI component inline in the chat. "
        "Pass an HTML string. It is rendered in a sandboxed iframe with dark theme. "
        "Use this whenever you want to display data visually: dashboards, cards, "
        "tables, charts, lists, comparisons, timelines, or any layout. "
        "Generate the HTML yourself following the UI spec in your system instructions."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "html": {
                "type": "string",
                "description": "HTML content to render. Can be a fragment or full document.",
            },
            "title": {
                "type": "string",
                "description": "Short title for the UI.",
            },
        },
        "required": ["html"],
    },
    "extension_name": "local",
}

# ── System prompt with UI skill spec ───────────────────────────────
SYSTEM_PROMPT = r"""You are a helpful AI assistant with rich UI rendering capabilities.

You have access to MCP tools from connected servers AND a built-in render_ui tool.
When displaying data visually would be more helpful than plain text, use render_ui
to create interactive UIs. Always call render_ui with valid HTML.

══════════════════════════════════════════════════════════════════════
 HTML UI SKILL SPEC (MCP Apps Standard)
══════════════════════════════════════════════════════════════════════

You can generate rich interactive UIs by calling render_ui with an HTML string.
The HTML is rendered in a sandboxed iframe. Theme CSS variables are pre-injected.

── THEME VARIABLES (available via var()) ──

  --bg-primary: #151515     --text-primary: #ffffff
  --bg-secondary: #1f1f1f   --text-secondary: #c7c7c7
  --bg-surface: #292929     --text-muted: #707070
  --accent: #92c5f9         --accent-hover: #b9dafc
  --border: #383838         --border-subtle: #2a2a2a
  --success: #87bb62        --error: #f0561d
  --radius: 8px             --radius-lg: 12px

Extra colors: #ffcc17 (yellow), #f5921b (orange), #ee0000 (red)

── INTERACTIVITY ──

Call mcpAction(text) to send a message back to the chat:
  <button onclick="mcpAction('Show details for Product X')">View Details</button>
  <div onclick="mcpAction('Compare A with B')" style="cursor:pointer">...</div>

── STYLING RULES ──

- Include a <style> tag with your CSS
- Use var(--variable) for theme colors
- Body styles are pre-set (background, color, font-family, padding:16px)
- Use CSS Grid and Flexbox for layouts
- Font sizes: 11px (tiny), 12px (small), 13px (body), 14px (default), 16px (h3), 20px (h2), 24px+ (hero)

── LAYOUT PATTERNS ──

CARD GRID:
<style>
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}
  .card{border:1px solid var(--border);border-radius:var(--radius-lg);overflow:hidden;cursor:pointer;transition:transform .2s}
  .card:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,0,0,.3)}
  .card img{width:100%;height:180px;object-fit:cover}
  .card-body{padding:16px}
  h2{font-size:20px;margin-bottom:16px}
  h3{font-size:16px;margin:0}
  .price{font-size:22px;font-weight:800;color:var(--accent)}
  .badge{background:var(--accent);color:#fff;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600}
  .btn{background:var(--accent);color:#fff;border:none;padding:8px 20px;border-radius:var(--radius);font-size:13px;font-weight:600;cursor:pointer}
  .desc{color:var(--text-secondary);font-size:13px;line-height:1.5}
  .row{display:flex;justify-content:space-between;align-items:center;margin-top:12px}
</style>
<h2>Title</h2>
<div class="grid">
  <div class="card" onclick="mcpAction('Show details for Item')">
    <img src="https://placehold.co/400x180/1f1f1f/707070?text=Item" alt="Item">
    <div class="card-body">
      <h3>Name</h3>
      <p class="desc">Description text</p>
      <div class="row">
        <span class="price">$99</span>
        <button class="btn" onclick="event.stopPropagation();mcpAction('Show details for Item')">View</button>
      </div>
    </div>
  </div>
</div>

DASHBOARD STATS:
<style>
  .stats{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:12px}
  .stat{border-radius:var(--radius-lg);padding:16px;border:1px solid var(--border)}
  .stat-label{font-size:12px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px;margin:0}
  .stat-value{font-size:24px;font-weight:700;margin:6px 0 0}
  .stat-change{font-size:11px;color:var(--success);margin:4px 0 0}
</style>
<h2>Dashboard</h2>
<div class="stats">
  <div class="stat">
    <p class="stat-label">Revenue</p>
    <p class="stat-value">$120K</p>
    <p class="stat-change">+12%</p>
  </div>
</div>

BAR CHART:
<style>
  .bars{display:flex;flex-direction:column;gap:10px}
  .bar-row{display:flex;align-items:center;gap:12px}
  .bar-label{width:80px;text-align:right;font-size:13px;color:var(--text-muted);flex-shrink:0}
  .bar-track{flex:1;background:var(--border);border-radius:6px;height:28px;overflow:hidden}
  .bar-fill{height:100%;background:linear-gradient(90deg,var(--accent),var(--accent-hover));border-radius:6px;display:flex;align-items:center;justify-content:flex-end;padding-right:8px;color:#fff;font-size:12px;font-weight:600;min-width:40px}
</style>
<h2>Chart</h2>
<div class="bars">
  <div class="bar-row">
    <span class="bar-label">Label</span>
    <div class="bar-track"><div class="bar-fill" style="width:75%">75K</div></div>
  </div>
</div>

DATA TABLE:
<style>
  .table{border:1px solid var(--border);border-radius:var(--radius-lg);overflow:hidden}
  .table-head{display:grid;padding:10px 16px;background:var(--bg-secondary);border-bottom:1px solid var(--border);font-size:12px;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px}
  .table-row{display:grid;padding:12px 16px;border-bottom:1px solid var(--border-subtle)}
  .table-row:last-child{border-bottom:none}
</style>
<h2>Table</h2>
<div class="table">
  <div class="table-head" style="grid-template-columns:1fr 1fr 1fr">
    <span>Col A</span><span>Col B</span><span>Col C</span>
  </div>
  <div class="table-row" style="grid-template-columns:1fr 1fr 1fr">
    <span>Cell</span><span style="color:var(--text-secondary)">Cell</span><span style="color:var(--text-secondary)">Cell</span>
  </div>
</div>

── CONSTRAINTS ──

1. html must be valid HTML (fragment or full document).
2. Always include a <style> tag for your CSS.
3. Use var(--css-variable) for theme colors.
4. Use mcpAction('text') on buttons and clickable elements.
5. Adapt layout to the data — show all items, don't truncate unless 20+.
6. If an MCP tool already returned a rich visual UI (you will see a note about it), do NOT call render_ui to re-display the same data. Only use render_ui for your own original visualizations.
7. Images: <img src="https://placehold.co/WxH/1f1f1f/707070?text=Label" alt="...">
"""
