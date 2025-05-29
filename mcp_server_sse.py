"""
MCP Server using SSE (Server-Sent Events) transport with OpenWeatherMap API

This server demonstrates:
1. SSE transport instead of stdio (HTTP-based, can be deployed remotely)
2. Integration with external REST APIs (OpenWeatherMap)
3. Real-world useful tools (weather data)
4. Proper error handling for API failures

Key differences from stdio server:
- Runs as HTTP server on localhost:8000
- Uses Server-Sent Events for real-time communication
- Can handle multiple concurrent clients
- Better suited for production deployment

Weather tools provided:
- current_weather: Get current weather for a city
- weather_forecast: Get 5-day weather forecast
- weather_by_coordinates: Get weather by lat/lon coordinates
"""

import os
import asyncio
import json
import aiohttp
from typing import Any, Dict, List
from dotenv import load_dotenv

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# SSE server imports
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import Response

# Load environment variables
load_dotenv()

# Get OpenWeatherMap API key
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
if not OPENWEATHERMAP_API_KEY:
    raise ValueError("OPENWEATHERMAP_API_KEY environment variable is required")

# OpenWeatherMap API base URL
WEATHER_API_BASE = "https://api.openweathermap.org/data/2.5"

# Create the MCP server
server = Server("weather-tools-sse")


class WeatherAPIError(Exception):
    """Custom exception for weather API errors."""
    pass


async def make_weather_request(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Make a request to the OpenWeatherMap API.

    Args:
        endpoint: API endpoint (e.g., "weather", "forecast")
        params: Query parameters for the API call

    Returns:
        API response as dictionary

    Raises:
        WeatherAPIError: If API call fails
    """
    # Add API key to parameters
    params["appid"] = OPENWEATHERMAP_API_KEY
    params["units"] = "metric"  # Use Celsius by default

    url = f"{WEATHER_API_BASE}/{endpoint}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    raise WeatherAPIError("City not found. Please check the city name.")
                elif response.status == 401:
                    raise WeatherAPIError("Invalid API key.")
                else:
                    error_text = await response.text()
                    raise WeatherAPIError(f"API error ({response.status}): {error_text}")

    except aiohttp.ClientError as e:
        raise WeatherAPIError(f"Network error: {str(e)}")


def extract_current_weather(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract structured weather data from OpenWeatherMap API response.

    Args:
        data: Raw weather data from API

    Returns:
        Structured weather information for LLM consumption
    """
    try:
        return {
            "location": {
                "city": data.get("name", "Unknown"),
                "country": data.get("sys", {}).get("country"),
                "coordinates": {
                    "latitude": data.get("coord", {}).get("lat"),
                    "longitude": data.get("coord", {}).get("lon")
                }
            },
            "weather": {
                "main": data["weather"][0]["main"],
                "description": data["weather"][0]["description"],
                "icon": data["weather"][0]["icon"]
            },
            "temperature": {
                "current": round(data["main"]["temp"], 1),
                "feels_like": round(data["main"]["feels_like"], 1),
                "min": round(data["main"]["temp_min"], 1),
                "max": round(data["main"]["temp_max"], 1)
            },
            "conditions": {
                "humidity": data["main"]["humidity"],
                "pressure": data["main"]["pressure"],
                "visibility": data.get("visibility")
            },
            "wind": {
                "speed": data.get("wind", {}).get("speed"),
                "direction": data.get("wind", {}).get("deg")
            },
            "timestamp": data["dt"]
        }
    except KeyError as e:
        raise WeatherAPIError(f"Unexpected API response format: missing {e}")


def extract_forecast_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract structured forecast data from OpenWeatherMap API response.

    Args:
        data: Raw forecast data from API

    Returns:
        Structured forecast information for LLM consumption
    """
    try:
        location = {
            "city": data["city"]["name"],
            "country": data["city"]["country"],
            "coordinates": {
                "latitude": data["city"]["coord"]["lat"],
                "longitude": data["city"]["coord"]["lon"]
            }
        }

        # Group by date and extract daily summaries
        daily_forecasts = {}
        for item in data["list"]:
            date = item["dt_txt"].split()[0]
            if date not in daily_forecasts:
                daily_forecasts[date] = {
                    "date": date,
                    "forecasts": []
                }

            daily_forecasts[date]["forecasts"].append({
                "time": item["dt_txt"].split()[1],
                "weather": {
                    "main": item["weather"][0]["main"],
                    "description": item["weather"][0]["description"]
                },
                "temperature": round(item["main"]["temp"], 1),
                "humidity": item["main"]["humidity"],
                "wind_speed": item.get("wind", {}).get("speed")
            })

        return {
            "location": location,
            "forecast_days": list(daily_forecasts.values())[:5]  # Limit to 5 days
        }

    except KeyError as e:
        raise WeatherAPIError(f"Unexpected forecast API response format: missing {e}")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available weather tools.

    Tool descriptions focus on WHAT the tool does, not HOW to handle missing data.
    The LLM is smart enough to ask for missing parameters based on the schema.
    """
    return [
        types.Tool(
            name="current_weather",
            description=(
                "Get current weather conditions for any city worldwide. "
                "Returns structured data including temperature, humidity, wind, and conditions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, optionally with country code (e.g., 'London', 'Tokyo', 'Paris, FR')",
                        "minLength": 1
                    }
                },
                "required": ["city"]
            }
        ),
        types.Tool(
            name="weather_forecast",
            description=(
                "Get a 5-day weather forecast for any city worldwide. "
                "Returns structured daily forecast data with temperatures and conditions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, optionally with country code (e.g., 'London', 'Tokyo', 'Paris, FR')",
                        "minLength": 1
                    }
                },
                "required": ["city"]
            }
        ),
        types.Tool(
            name="weather_by_coordinates",
            description=(
                "Get current weather by geographic coordinates (latitude and longitude). "
                "Returns structured weather data for the exact location."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "number",
                        "description": "Latitude coordinate (-90 to 90)",
                        "minimum": -90,
                        "maximum": 90
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude coordinate (-180 to 180)",
                        "minimum": -180,
                        "maximum": 180
                    }
                },
                "required": ["latitude", "longitude"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[types.TextContent]:
    """
    Handle tool execution requests.
    Returns structured JSON data that the LLM can interpret and format naturally.
    """
    if arguments is None:
        arguments = {}

    try:
        if name == "current_weather":
            city = arguments.get("city")
            if not city:
                raise ValueError("City parameter is required")

            # Make API request
            raw_data = await make_weather_request("weather", {"q": city})

            # Extract structured data
            weather_data = extract_current_weather(raw_data)

            # Return as JSON string for LLM to interpret
            return [types.TextContent(
                type="text",
                text=json.dumps(weather_data, indent=2)
            )]

        elif name == "weather_forecast":
            city = arguments.get("city")
            if not city:
                raise ValueError("City parameter is required")

            # Make API request for 5-day forecast
            raw_data = await make_weather_request("forecast", {"q": city})

            # Extract structured data
            forecast_data = extract_forecast_data(raw_data)

            # Return as JSON string for LLM to interpret
            return [types.TextContent(
                type="text",
                text=json.dumps(forecast_data, indent=2)
            )]

        elif name == "weather_by_coordinates":
            latitude = arguments.get("latitude")
            longitude = arguments.get("longitude")

            if latitude is None or longitude is None:
                raise ValueError("Both latitude and longitude parameters are required")

            # Make API request with coordinates
            raw_data = await make_weather_request("weather", {
                "lat": latitude,
                "lon": longitude
            })

            # Extract structured data
            weather_data = extract_current_weather(raw_data)

            # Return as JSON string for LLM to interpret
            return [types.TextContent(
                type="text",
                text=json.dumps(weather_data, indent=2)
            )]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except WeatherAPIError as e:
        # Return error as structured data too
        error_data = {"error": str(e), "type": "weather_api_error"}
        return [types.TextContent(type="text", text=json.dumps(error_data))]
    except Exception as e:
        # Return error as structured data
        error_data = {"error": str(e), "type": "execution_error"}
        return [types.TextContent(type="text", text=json.dumps(error_data))]


async def main():
    """
    Main function to run the MCP server with SSE transport.
    """
    import uvicorn

    # Create SSE transport
    sse_transport = SseServerTransport("/messages")

    async def app(scope, receive, send):
        """Raw ASGI application for MCP SSE"""
        if scope["type"] == "http":
            path = scope["path"]
            method = scope["method"]

            if path == "/sse" and method == "GET":
                # Handle SSE connection
                async with sse_transport.connect_sse(scope, receive, send) as streams:
                    read_stream, write_stream = streams
                    await server.run(
                        read_stream,
                        write_stream,
                        InitializationOptions(
                            server_name="weather-tools-sse",
                            server_version="1.0.0",
                            capabilities=server.get_capabilities(
                                notification_options=NotificationOptions(),
                                experimental_capabilities={},
                            ),
                        ),
                    )
            elif path == "/messages" and method == "POST":
                # Handle POST messages
                await sse_transport.handle_post_message(scope, receive, send)
            else:
                # 404 for other paths
                await send({
                    "type": "http.response.start",
                    "status": 404,
                    "headers": [[b"content-type", b"text/plain"]],
                })
                await send({
                    "type": "http.response.body",
                    "body": b"Not Found",
                })

    print("🌤️  Weather MCP Server (SSE) starting...")
    print("📡 Server URL: http://localhost:8000/sse")
    print("🔧 Tools available: current_weather, weather_forecast, weather_by_coordinates")
    print("🌍 Powered by OpenWeatherMap API")
    print("⏹️  Press Ctrl+C to stop")

    # Run with uvicorn
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="info")
    server_instance = uvicorn.Server(config)
    await server_instance.serve()


if __name__ == "__main__":
    # Install required dependencies:
    # pip install mcp aiohttp python-dotenv starlette uvicorn
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Weather MCP Server stopped")