# Weather MCP Server

Live weather data from [WeatherAPI.com](https://www.weatherapi.com/) with rich **Remote DOM** UI cards.

## Setup

1. Get a free API key at [weatherapi.com](https://www.weatherapi.com/signup.aspx)
2. Set the key:
   ```bash
   cp .env.example .env.example   # Edit and add your key
   # Or pass via environment:
   export WEATHER_API_KEY=your-key
   ```

## Run

```bash
python3 server.py
```

**Requires:** `mcp` Python package (`pip install mcp`)

## Connect

```
Type: stdio
Command: python3
Args: /path/to/weather-mcp-server/server.py
Envs: WEATHER_API_KEY=your-key
```

## Tools

### `get_current_weather`

Current conditions with temperature, wind, humidity, UV index, pressure, and cloud coverage.

- **city** (required) — city name, zipcode, or lat/lon

Returns an interactive card with "3-Day Forecast" and "7-Day Forecast" buttons.

### `get_forecast`

Multi-day forecast with daily highs/lows and 6-hour temperature strips.

- **city** (required) — city name, zipcode, or lat/lon
- **days** (optional) — 1–14, default 3

Each forecast card is clickable to get the current weather for that city.

### `search_cities`

Search cities by name with clickable "Get Weather" buttons.

- **query** (required) — city name to search

## Example Queries

- "What's the weather in Tokyo?"
- "Show me a 7-day forecast for London"
- "Search for cities named Springfield"
