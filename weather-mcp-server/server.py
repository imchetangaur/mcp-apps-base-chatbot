"""
Weather MCP Server — returns rich Remote DOM UI for weather data.

Uses WeatherAPI.com for current weather, forecasts, and city search.
Returns native Remote DOM JSON (application/vnd.mcp-ui.remote-dom)
styled to match the shadowbot-ui dark theme.

Run:   WEATHER_API_KEY=<key> python3 server.py
Connect: stdio (cmd: python3, args: [path/to/server.py])
"""

import json
import os
import ssl
import urllib.request
import urllib.parse
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, EmbeddedResource, TextResourceContents

app = Server("weather-service")

REMOTE_DOM_MIME = "application/vnd.mcp-ui.remote-dom"

# Load .env file if present (fallback for when envs aren't passed via extension config)
_server_dir = os.path.dirname(os.path.abspath(__file__))
for _env_name in (".env", ".env.example"):
    _env_path = os.path.join(_server_dir, _env_name)
    if os.path.exists(_env_path):
        with open(_env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
        break

API_KEY = os.environ.get("WEATHER_API_KEY", "").strip()
BASE_URL = "https://api.weatherapi.com/v1"

# ── Theme colors (use CSS variables for dynamic theming) ─────────
BG_PRIMARY = "var(--bg-primary, #151515)"
BG_SURFACE = "var(--bg-secondary, #1f1f1f)"
BG_TERTIARY = "var(--border, #383838)"
TEXT_PRIMARY = "var(--text-primary, #ffffff)"
TEXT_SECONDARY = "var(--text-secondary, #c7c7c7)"
TEXT_MUTED = "var(--text-muted, #707070)"
ACCENT = "var(--accent, #92c5f9)"
ACCENT_HOVER = "var(--accent-hover, #b9dafc)"
SUCCESS = "var(--success, #87bb62)"
WARNING = "#ffcc17"          # sunny/clear weather — yellow (not themed)
CAUTION = "#f5921b"          # thunder/alerts — orange (not themed)
DANGER = "var(--error, #f0561d)"
BRAND = "#ee0000"            # Red Hat brand — red (not themed)


_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


def _api_get(endpoint: str, params: dict) -> dict:
    """Make a GET request to WeatherAPI.com."""
    params["key"] = API_KEY
    qs = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/{endpoint}?{qs}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10, context=_ssl_ctx) as resp:
        return json.loads(resp.read().decode())


def _condition_color(code: int) -> str:
    """Return accent color based on weather condition code."""
    if code == 1000:
        return WARNING  # sunny/clear → yellow
    if code in (1003, 1006, 1009):
        return TEXT_SECONDARY  # cloudy → gray
    if code in (1030, 1135, 1147):
        return TEXT_MUTED  # mist/fog
    if code >= 1063 and code <= 1201:
        return ACCENT  # rain → blue
    if code >= 1204 and code <= 1264:
        return ACCENT_HOVER  # sleet/snow → light blue
    if code >= 1273:
        return CAUTION  # thunder → orange
    return ACCENT


def _wind_direction_arrow(degree: int) -> str:
    """Simple arrow for wind direction."""
    arrows = ["↑", "↗", "→", "↘", "↓", "↙", "←", "↖"]
    idx = round(degree / 45) % 8
    return arrows[idx]


def _build_current_weather_tree(data: dict) -> str:
    """Build Remote DOM tree for current weather display."""
    loc = data["location"]
    cur = data["current"]
    cond = cur["condition"]
    cond_color = _condition_color(cond["code"])
    icon_url = f"https:{cond['icon']}" if cond["icon"].startswith("//") else cond["icon"]
    wind_arrow = _wind_direction_arrow(cur.get("wind_degree", 0))

    tree = {
        "type": "div",
        "props": {"style": {"padding": "0"}},
        "children": [
            # ── Location header ──
            {
                "type": "div",
                "props": {"style": {
                    "background": "transparent",
                    "borderRadius": "16px",
                    "padding": "0",
                    "border": "none",
                }},
                "children": [
                    # City + condition row
                    {
                        "type": "div",
                        "props": {"style": {"display": "flex", "justifyContent": "space-between", "alignItems": "flex-start"}},
                        "children": [
                            {
                                "type": "div",
                                "children": [
                                    {
                                        "type": "h2",
                                        "props": {"style": {"margin": "0", "fontSize": "24px", "fontWeight": "700", "color": TEXT_PRIMARY}},
                                        "children": [loc["name"]],
                                    },
                                    {
                                        "type": "p",
                                        "props": {"style": {"margin": "4px 0 0", "fontSize": "13px", "color": TEXT_MUTED}},
                                        "children": [f"{loc.get('region', '')}, {loc['country']}"],
                                    },
                                    {
                                        "type": "p",
                                        "props": {"style": {"margin": "2px 0 0", "fontSize": "12px", "color": TEXT_MUTED}},
                                        "children": [f"Local time: {loc.get('localtime', '')}"],
                                    },
                                ],
                            },
                            {
                                "type": "div",
                                "props": {"style": {"textAlign": "right"}},
                                "children": [
                                    {
                                        "type": "img",
                                        "props": {
                                            "src": icon_url,
                                            "alt": cond["text"],
                                            "style": {"width": "64px", "height": "64px"},
                                        },
                                    },
                                ],
                            },
                        ],
                    },

                    # Temperature + condition
                    {
                        "type": "div",
                        "props": {"style": {"display": "flex", "alignItems": "baseline", "gap": "12px", "marginTop": "16px"}},
                        "children": [
                            {
                                "type": "span",
                                "props": {"style": {"fontSize": "48px", "fontWeight": "800", "color": TEXT_PRIMARY, "lineHeight": "1"}},
                                "children": [f"{cur['temp_c']}°"],
                            },
                            {
                                "type": "span",
                                "props": {"style": {"fontSize": "14px", "color": TEXT_SECONDARY}},
                                "children": [f"/ {cur['temp_f']}°F"],
                            },
                            {
                                "type": "span",
                                "props": {"style": {
                                    "background": cond_color,
                                    "color": BG_PRIMARY,
                                    "padding": "4px 12px",
                                    "borderRadius": "20px",
                                    "fontSize": "12px",
                                    "fontWeight": "600",
                                }},
                                "children": [cond["text"]],
                            },
                        ],
                    },

                    # Feels like
                    {
                        "type": "p",
                        "props": {"style": {"fontSize": "13px", "color": TEXT_MUTED, "marginTop": "4px"}},
                        "children": [f"Feels like {cur['feelslike_c']}°C / {cur['feelslike_f']}°F"],
                    },
                ],
            },

            # ── Detail cards grid ──
            {
                "type": "div",
                "props": {"style": {
                    "display": "grid",
                    "gridTemplateColumns": "repeat(auto-fill, minmax(140px, 1fr))",
                    "gap": "12px",
                    "marginTop": "16px",
                }},
                "children": [
                    _detail_card("💨 Wind", f"{cur['wind_kph']} km/h", f"{wind_arrow} {cur.get('wind_dir', '')}"),
                    _detail_card("💧 Humidity", f"{cur['humidity']}%", "Relative"),
                    _detail_card("👁 Visibility", f"{cur['vis_km']} km", f"{cur['vis_miles']} mi"),
                    _detail_card("🌡 Pressure", f"{cur['pressure_mb']} mb", f"{cur['pressure_in']} in"),
                    _detail_card("☀️ UV Index", f"{cur['uv']}", _uv_label(cur["uv"])),
                    _detail_card("☁️ Cloud", f"{cur['cloud']}%", "Coverage"),
                ],
            },

            # ── Action buttons ──
            {
                "type": "div",
                "props": {"style": {"display": "flex", "gap": "10px", "marginTop": "16px"}},
                "children": [
                    {
                        "type": "button",
                        "action": f"Show me the 3-day forecast for {loc['name']}",
                        "props": {"style": {
                            "background": ACCENT,
                            "color": BG_PRIMARY,
                            "border": "none",
                            "padding": "10px 20px",
                            "borderRadius": "8px",
                            "fontSize": "13px",
                            "fontWeight": "600",
                            "cursor": "pointer",
                        }},
                        "children": ["3-Day Forecast"],
                    },
                    {
                        "type": "button",
                        "action": f"Show me the 7-day forecast for {loc['name']}",
                        "props": {"style": {
                            "background": BG_TERTIARY,
                            "color": TEXT_PRIMARY,
                            "border": f"1px solid {TEXT_MUTED}",
                            "padding": "10px 20px",
                            "borderRadius": "8px",
                            "fontSize": "13px",
                            "fontWeight": "600",
                            "cursor": "pointer",
                        }},
                        "children": ["7-Day Forecast"],
                    },
                ],
            },
        ],
    }

    return json.dumps(tree)


def _detail_card(label: str, value: str, sub: str) -> dict:
    """Small stat card for weather details."""
    return {
        "type": "div",
        "props": {"style": {
            "background": "transparent",
            "borderRadius": "12px",
            "padding": "14px",
            "border": f"1px solid {BG_TERTIARY}",
        }},
        "children": [
            {"type": "p", "props": {"style": {"fontSize": "12px", "color": TEXT_MUTED, "margin": "0"}}, "children": [label]},
            {"type": "p", "props": {"style": {"fontSize": "20px", "fontWeight": "700", "color": TEXT_PRIMARY, "margin": "4px 0 0"}}, "children": [value]},
            {"type": "p", "props": {"style": {"fontSize": "11px", "color": TEXT_MUTED, "margin": "2px 0 0"}}, "children": [sub]},
        ],
    }


def _uv_label(uv: float) -> str:
    if uv <= 2:
        return "Low"
    if uv <= 5:
        return "Moderate"
    if uv <= 7:
        return "High"
    if uv <= 10:
        return "Very High"
    return "Extreme"


def _build_forecast_tree(data: dict, days_count: int) -> str:
    """Build Remote DOM tree for multi-day forecast."""
    loc = data["location"]
    forecast_days = data["forecast"]["forecastday"]

    day_cards = []
    for fd in forecast_days:
        day = fd["day"]
        cond = day["condition"]
        icon_url = f"https:{cond['icon']}" if cond["icon"].startswith("//") else cond["icon"]
        cond_color = _condition_color(cond["code"])

        # Date formatting
        date_str = fd["date"]

        # Hourly mini-chart (6h intervals)
        hourly_temps = []
        for h in fd.get("hour", [])[::6]:
            hourly_temps.append({
                "type": "div",
                "props": {"style": {"textAlign": "center", "flex": "1"}},
                "children": [
                    {"type": "p", "props": {"style": {"fontSize": "10px", "color": TEXT_MUTED, "margin": "0"}}, "children": [h["time"].split(" ")[1]]},
                    {"type": "img", "props": {
                        "src": f"https:{h['condition']['icon']}" if h["condition"]["icon"].startswith("//") else h["condition"]["icon"],
                        "alt": h["condition"]["text"],
                        "style": {"width": "28px", "height": "28px", "margin": "2px auto", "display": "block"},
                    }},
                    {"type": "p", "props": {"style": {"fontSize": "12px", "color": TEXT_PRIMARY, "margin": "0", "fontWeight": "600"}}, "children": [f"{h['temp_c']}°"]},
                ],
            })

        card = {
            "type": "div",
            "action": f"Show me the current weather for {loc['name']}",
            "props": {"style": {
                "background": "transparent",
                "borderRadius": "14px",
                "padding": "18px",
                "border": f"1px solid {BG_TERTIARY}",
                "cursor": "pointer",
                "transition": "transform 0.2s",
            }},
            "children": [
                # Date + condition
                {
                    "type": "div",
                    "props": {"style": {"display": "flex", "justifyContent": "space-between", "alignItems": "center"}},
                    "children": [
                        {
                            "type": "div",
                            "children": [
                                {"type": "p", "props": {"style": {"fontSize": "15px", "fontWeight": "700", "color": TEXT_PRIMARY, "margin": "0"}}, "children": [date_str]},
                                {
                                    "type": "span",
                                    "props": {"style": {
                                        "background": cond_color,
                                        "color": BG_PRIMARY,
                                        "padding": "2px 10px",
                                        "borderRadius": "20px",
                                        "fontSize": "11px",
                                        "fontWeight": "600",
                                        "display": "inline-block",
                                        "marginTop": "4px",
                                    }},
                                    "children": [cond["text"]],
                                },
                            ],
                        },
                        {
                            "type": "img",
                            "props": {
                                "src": icon_url,
                                "alt": cond["text"],
                                "style": {"width": "48px", "height": "48px"},
                            },
                        },
                    ],
                },

                # Temp range
                {
                    "type": "div",
                    "props": {"style": {"display": "flex", "alignItems": "baseline", "gap": "8px", "marginTop": "10px"}},
                    "children": [
                        {"type": "span", "props": {"style": {"fontSize": "28px", "fontWeight": "800", "color": TEXT_PRIMARY}}, "children": [f"{day['maxtemp_c']}°"]},
                        {"type": "span", "props": {"style": {"fontSize": "14px", "color": TEXT_MUTED}}, "children": [f"/ {day['mintemp_c']}°"]},
                    ],
                },

                # Stats row
                {
                    "type": "div",
                    "props": {"style": {"display": "flex", "gap": "16px", "marginTop": "8px"}},
                    "children": [
                        {"type": "span", "props": {"style": {"fontSize": "12px", "color": TEXT_SECONDARY}}, "children": [f"💨 {day['maxwind_kph']} km/h"]},
                        {"type": "span", "props": {"style": {"fontSize": "12px", "color": TEXT_SECONDARY}}, "children": [f"💧 {day['avghumidity']}%"]},
                        {"type": "span", "props": {"style": {"fontSize": "12px", "color": TEXT_SECONDARY}}, "children": [f"🌧 {day['daily_chance_of_rain']}%"]},
                    ],
                },

                # Hourly strip
                {
                    "type": "div",
                    "props": {"style": {
                        "display": "flex",
                        "gap": "4px",
                        "marginTop": "12px",
                        "background": "transparent",
                        "borderRadius": "8px",
                        "padding": "8px",
                        "border": f"1px solid {BG_TERTIARY}",
                    }},
                    "children": hourly_temps,
                },
            ],
        }
        day_cards.append(card)

    tree = {
        "type": "div",
        "children": [
            {
                "type": "h2",
                "props": {"style": {"fontSize": "20px", "fontWeight": "700", "color": TEXT_PRIMARY, "marginBottom": "4px"}},
                "children": [f"{days_count}-Day Forecast"],
            },
            {
                "type": "p",
                "props": {"style": {"fontSize": "13px", "color": TEXT_MUTED, "marginBottom": "16px"}},
                "children": [f"{loc['name']}, {loc.get('region', '')} — {loc['country']}"],
            },
            {
                "type": "div",
                "props": {"style": {
                    "display": "grid",
                    "gridTemplateColumns": "repeat(auto-fill, minmax(280px, 1fr))",
                    "gap": "14px",
                }},
                "children": day_cards,
            },
        ],
    }

    return json.dumps(tree)


def _build_search_results_tree(results: list, query: str) -> str:
    """Build Remote DOM tree for city search results."""
    if not results:
        tree = {
            "type": "div",
            "props": {"style": {"padding": "20px", "textAlign": "center"}},
            "children": [
                {"type": "p", "props": {"style": {"color": TEXT_MUTED, "fontSize": "14px"}}, "children": [f'No cities found for "{query}"']},
            ],
        }
        return json.dumps(tree)

    items = []
    for r in results[:10]:
        items.append({
            "type": "div",
            "action": f"Show me the current weather for {r['name']}, {r.get('region', '')}, {r['country']}",
            "props": {"style": {
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "space-between",
                "background": "transparent",
                "borderRadius": "10px",
                "padding": "14px 18px",
                "border": f"1px solid {BG_TERTIARY}",
                "cursor": "pointer",
                "transition": "transform 0.2s",
            }},
            "children": [
                {
                    "type": "div",
                    "children": [
                        {"type": "p", "props": {"style": {"fontSize": "15px", "fontWeight": "600", "color": TEXT_PRIMARY, "margin": "0"}}, "children": [r["name"]]},
                        {"type": "p", "props": {"style": {"fontSize": "12px", "color": TEXT_MUTED, "margin": "2px 0 0"}},
                         "children": [f"{r.get('region', '')} — {r['country']}"]},
                        {"type": "p", "props": {"style": {"fontSize": "11px", "color": TEXT_MUTED, "margin": "2px 0 0"}},
                         "children": [f"{r['lat']}, {r['lon']}"]},
                    ],
                },
                {
                    "type": "button",
                    "action": f"Show me the current weather for {r['name']}, {r.get('region', '')}, {r['country']}",
                    "props": {"style": {
                        "background": ACCENT,
                        "color": BG_PRIMARY,
                        "border": "none",
                        "padding": "8px 16px",
                        "borderRadius": "8px",
                        "fontSize": "12px",
                        "fontWeight": "600",
                        "cursor": "pointer",
                    }},
                    "children": ["Get Weather"],
                },
            ],
        })

    tree = {
        "type": "div",
        "children": [
            {
                "type": "h2",
                "props": {"style": {"fontSize": "18px", "fontWeight": "700", "color": TEXT_PRIMARY, "marginBottom": "4px"}},
                "children": [f"Search Results"],
            },
            {
                "type": "p",
                "props": {"style": {"fontSize": "13px", "color": TEXT_MUTED, "marginBottom": "14px"}},
                "children": [f'{len(results)} cities matching "{query}"'],
            },
            {
                "type": "div",
                "props": {"style": {"display": "flex", "flexDirection": "column", "gap": "8px"}},
                "children": items,
            },
        ],
    }

    return json.dumps(tree)


# ── MCP Tools ────────────────────────────────────────────────────

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="get_current_weather",
            description="Get current/realtime weather for a city. Returns a visual weather card with temperature, conditions, wind, humidity, and more.",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, US zipcode, UK postcode, IP address, or lat/lon (e.g. 'London', '10001', '48.8566,2.3522')",
                    },
                },
                "required": ["city"],
            },
        ),
        Tool(
            name="get_forecast",
            description="Get weather forecast for a city (up to 14 days). Returns visual forecast cards with daily highs/lows, conditions, and hourly previews.",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, zipcode, or lat/lon",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of forecast days (1-14, default 3)",
                    },
                },
                "required": ["city"],
            },
        ),
        Tool(
            name="search_cities",
            description="Search for cities by name. Returns clickable results — select a city to get its weather.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "City name to search for",
                    },
                },
                "required": ["query"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        if name == "get_current_weather":
            city = arguments.get("city", "London")
            data = _api_get("current.json", {"q": city, "aqi": "no"})
            tree_json = _build_current_weather_tree(data)

            return [
                TextContent(
                    type="text",
                    text=f"Current weather for {data['location']['name']}: {data['current']['temp_c']}°C, {data['current']['condition']['text']}.",
                ),
                EmbeddedResource(
                    type="resource",
                    resource=TextResourceContents(
                        uri=f"ui://weather/{data['location']['name']}/current",
                        mimeType=REMOTE_DOM_MIME,
                        text=tree_json,
                    ),
                ),
            ]

        elif name == "get_forecast":
            city = arguments.get("city", "London")
            days = min(max(arguments.get("days", 3), 1), 14)
            data = _api_get("forecast.json", {"q": city, "days": str(days), "aqi": "no", "alerts": "no"})
            tree_json = _build_forecast_tree(data, days)

            loc = data["location"]
            return [
                TextContent(
                    type="text",
                    text=f"{days}-day forecast for {loc['name']}.",
                ),
                EmbeddedResource(
                    type="resource",
                    resource=TextResourceContents(
                        uri=f"ui://weather/{loc['name']}/forecast/{days}",
                        mimeType=REMOTE_DOM_MIME,
                        text=tree_json,
                    ),
                ),
            ]

        elif name == "search_cities":
            query = arguments.get("query", "")
            results = _api_get("search.json", {"q": query})
            tree_json = _build_search_results_tree(results, query)

            return [
                TextContent(
                    type="text",
                    text=f"Found {len(results)} cities matching '{query}'.",
                ),
                EmbeddedResource(
                    type="resource",
                    resource=TextResourceContents(
                        uri=f"ui://weather/search/{query}",
                        mimeType=REMOTE_DOM_MIME,
                        text=tree_json,
                    ),
                ),
            ]

    except Exception as e:
        return [TextContent(type="text", text=f"Weather API error: {str(e)}")]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        init_options = app.create_initialization_options()
        await app.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
