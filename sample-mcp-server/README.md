# Product Catalog MCP Server

Demonstrates **Remote DOM** rendering with product cards and bar charts.

## Run

```bash
python3 server.py
```

**Requires:** `mcp` Python package (`pip install mcp`)

## Connect

```
Type: stdio
Command: python3
Args: /path/to/sample-mcp-server/server.py
```

## Tools

### `search_products`

Browse products by category with visual cards.

- **category** (required) — `shoes` or `electronics`
- **color** (optional) — filter by color (e.g., `blue`, `black`)

Returns a grid of product cards with images, prices, badges, and "View Details" buttons. Clicking a card sends a follow-up message to the LLM.

### `show_chart`

Display business data as a horizontal bar chart.

- **dataset** (required) — `sales` (quarterly revenue) or `users` (monthly active users)
- **title** (optional) — chart title

### `render_html`

Render arbitrary HTML content in a sandboxed iframe.

- **html** (required) — complete HTML string
- **title** (optional) — toolbar title

## Example Queries

- "Show me shoes"
- "Search for blue electronics"
- "Show the sales chart"
- "Render a hello world HTML page"
