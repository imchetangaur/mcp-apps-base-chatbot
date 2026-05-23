"""
Sample MCP Server that returns rich UI content using Remote DOM.

Demonstrates two rendering modes:
  1. Remote DOM (application/vnd.mcp-ui.remote-dom) — JSON component tree
     rendered as native React components with host theming
  2. HTML (text/html) — raw HTML rendered in sandboxed iframe (fallback)

Run: python3 server.py
Connect via: stdio (cmd: python3, args: [path/to/server.py])
"""

import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, EmbeddedResource, TextResourceContents


app = Server("product-catalog")

REMOTE_DOM_MIME = "application/vnd.mcp-ui.remote-dom"

# Sample product data
PRODUCTS = {
    "shoes": [
        {
            "name": "Adidas Ultraboost 23",
            "color": "Light Blue / Cloud White",
            "price": "$190",
            "type": "Running",
            "image": "https://placehold.co/300x200/4A90D9/FFFFFF?text=Ultraboost+23",
            "description": "Premium running shoe with Boost cushioning and Primeknit+ upper.",
        },
        {
            "name": "Nike Air Max 270",
            "color": "Royal Blue / Black",
            "price": "$160",
            "type": "Lifestyle",
            "image": "https://placehold.co/300x200/1E3A5F/FFFFFF?text=Air+Max+270",
            "description": "Iconic Air Max with the largest Air unit yet for all-day comfort.",
        },
        {
            "name": "New Balance 990v6",
            "color": "Navy / Grey",
            "price": "$200",
            "type": "Running/Lifestyle",
            "image": "https://placehold.co/300x200/2C3E50/FFFFFF?text=990v6",
            "description": "Made in USA premium shoe with ENCAP midsole technology.",
        },
    ],
    "electronics": [
        {
            "name": 'MacBook Pro 16"',
            "color": "Space Black",
            "price": "$2,499",
            "type": "Laptop",
            "image": "https://placehold.co/300x200/1A1A2E/FFFFFF?text=MacBook+Pro",
            "description": "M4 Pro chip, 18GB RAM, 512GB SSD, Liquid Retina XDR display.",
        },
        {
            "name": "Sony WH-1000XM5",
            "color": "Midnight Blue",
            "price": "$348",
            "type": "Headphones",
            "image": "https://placehold.co/300x200/16213E/FFFFFF?text=WH-1000XM5",
            "description": "Industry-leading noise cancellation with exceptional sound quality.",
        },
    ],
}

CHART_DATA = {
    "sales": {"Q1": 45000, "Q2": 52000, "Q3": 49000, "Q4": 61000},
    "users": {"Jan": 1200, "Feb": 1350, "Mar": 1500, "Apr": 1800, "May": 2100, "Jun": 2400},
}


def _build_product_tree(products: list[dict], category: str) -> str:
    """Build a Remote DOM JSON component tree for product cards."""
    cards = []
    for p in products:
        card = {
            "type": "card",
            "action": f"Tell me more about {p['name']}. Show detailed specs, reviews, and similar products.",
            "children": [
                {
                    "type": "img",
                    "props": {
                        "src": p["image"],
                        "alt": p["name"],
                        "style": {"width": "100%", "height": "180px", "objectFit": "cover"},
                    },
                },
                {
                    "type": "div",
                    "props": {"style": {"padding": "16px"}},
                    "children": [
                        {
                            "type": "row",
                            "props": {
                                "style": {
                                    "display": "flex",
                                    "justifyContent": "space-between",
                                    "alignItems": "start",
                                    "marginBottom": "8px",
                                }
                            },
                            "children": [
                                {
                                    "type": "h3",
                                    "props": {
                                        "style": {
                                            "margin": "0",
                                            "fontSize": "16px",
                                            "color": "var(--text-primary)",
                                        }
                                    },
                                    "children": [p["name"]],
                                },
                                {
                                    "type": "badge",
                                    "children": [p["type"]],
                                },
                            ],
                        },
                        {
                            "type": "subtitle",
                            "children": [p["color"]],
                        },
                        {
                            "type": "description",
                            "children": [p["description"]],
                        },
                        {
                            "type": "row",
                            "props": {
                                "style": {
                                    "display": "flex",
                                    "justifyContent": "space-between",
                                    "alignItems": "center",
                                    "marginTop": "12px",
                                }
                            },
                            "children": [
                                {"type": "price", "children": [p["price"]]},
                                {
                                    "type": "button",
                                    "action": f"Tell me more about {p['name']}. Show detailed specs, reviews, and similar products.",
                                    "children": ["View Details"],
                                },
                            ],
                        },
                    ],
                },
            ],
        }
        cards.append(card)

    tree = {
        "type": "div",
        "children": [
            {
                "type": "heading",
                "children": [f"{category.title()} Collection"],
            },
            {
                "type": "grid",
                "children": cards,
            },
        ],
    }

    return json.dumps(tree)


def _build_chart_tree(data: dict, title: str) -> str:
    """Build a Remote DOM JSON component tree for a bar chart."""
    max_val = max(data.values())
    bars = []
    for label, value in data.items():
        pct = (value / max_val) * 100
        bars.append({
            "type": "row",
            "props": {
                "style": {
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "12px",
                    "marginBottom": "10px",
                }
            },
            "children": [
                {
                    "type": "span",
                    "props": {
                        "style": {
                            "width": "40px",
                            "textAlign": "right",
                            "fontSize": "13px",
                            "color": "var(--text-muted)",
                        }
                    },
                    "children": [label],
                },
                {
                    "type": "div",
                    "props": {
                        "style": {
                            "flex": "1",
                            "background": "transparent",
                            "border": "1px solid var(--border)",
                            "borderRadius": "6px",
                            "height": "28px",
                            "overflow": "hidden",
                        }
                    },
                    "children": [
                        {
                            "type": "div",
                            "props": {
                                "style": {
                                    "width": f"{pct}%",
                                    "height": "100%",
                                    "background": "linear-gradient(90deg, var(--accent), var(--accent-hover))",
                                    "borderRadius": "6px",
                                    "display": "flex",
                                    "alignItems": "center",
                                    "justifyContent": "flex-end",
                                    "paddingRight": "8px",
                                    "color": "white",
                                    "fontSize": "12px",
                                    "fontWeight": "600",
                                    "minWidth": "40px",
                                }
                            },
                            "children": [f"{value:,}"],
                        },
                    ],
                },
            ],
        })

    tree = {
        "type": "div",
        "props": {"style": {"padding": "8px 0"}},
        "children": [
            {"type": "heading", "children": [title]},
            *bars,
        ],
    }

    return json.dumps(tree)


@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="search_products",
            description="Search for products by category (shoes, electronics). Returns visual product cards with images, prices, and details.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Product category: shoes, electronics",
                    },
                    "color": {
                        "type": "string",
                        "description": "Optional color filter (e.g. blue, black)",
                    },
                },
                "required": ["category"],
            },
        ),
        Tool(
            name="show_chart",
            description="Show a visual bar chart for business data. Available datasets: sales (quarterly revenue), users (monthly active users).",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset": {
                        "type": "string",
                        "description": "Dataset to chart: sales, users",
                    },
                    "title": {
                        "type": "string",
                        "description": "Chart title",
                    },
                },
                "required": ["dataset"],
            },
        ),
        Tool(
            name="render_html",
            description="Render custom HTML content. Use this to display any visual UI, dashboard, form, or interactive content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "html": {
                        "type": "string",
                        "description": "Complete HTML content to render",
                    },
                    "title": {
                        "type": "string",
                        "description": "Title for the rendered content",
                    },
                },
                "required": ["html"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "search_products":
        category = arguments.get("category", "shoes").lower()
        products = PRODUCTS.get(category, PRODUCTS["shoes"])

        color_filter = arguments.get("color", "").lower()
        if color_filter:
            products = [p for p in products if color_filter in p["color"].lower()]

        tree_json = _build_product_tree(products, category)

        # Return as Remote DOM (native React rendering)
        return [
            TextContent(
                type="text",
                text=f"Found {len(products)} {category} products.",
            ),
            EmbeddedResource(
                type="resource",
                resource=TextResourceContents(
                    uri=f"ui://product-catalog/{category}",
                    mimeType=REMOTE_DOM_MIME,
                    text=tree_json,
                ),
            ),
        ]

    elif name == "show_chart":
        dataset = arguments.get("dataset", "sales").lower()
        data = CHART_DATA.get(dataset, CHART_DATA["sales"])
        title = arguments.get("title", f"{dataset.title()} Data")
        tree_json = _build_chart_tree(data, title)

        return [
            TextContent(type="text", text=f"Showing {dataset} chart."),
            EmbeddedResource(
                type="resource",
                resource=TextResourceContents(
                    uri=f"ui://product-catalog/chart/{dataset}",
                    mimeType=REMOTE_DOM_MIME,
                    text=tree_json,
                ),
            ),
        ]

    elif name == "render_html":
        html = arguments.get("html", "<p>No content</p>")
        title = arguments.get("title", "Custom Render")

        # render_html still uses HTML/iframe mode
        return [
            TextContent(type="text", text=f"Rendered: {title}"),
            EmbeddedResource(
                type="resource",
                resource=TextResourceContents(
                    uri=f"ui://product-catalog/custom/{title}",
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
