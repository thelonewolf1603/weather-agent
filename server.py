import httpx
from fastmcp import FastMCP
import os
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("WeatherService")

API_KEY = os.getenv("WEATHER_API_KEY")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

@mcp.tool()
async def get_weather(city: str, units: str = "metric") -> str:
    """
    Fetches the current weather for a specific city.
    Only use this if the user asks for weather, temperature, or conditions.
    """
    params = {"q": city, "appid": API_KEY, "units": units}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(BASE_URL, params=params)
        if response.status_code != 200:
            return f"Error: Could not find weather for {city}."
        
        data = response.json()
        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        unit = "°C" if units == "metric" else "°F"
        return f"It is {temp}{unit} in {city} with {desc}."

if __name__ == "__main__":
    # Running as a persistent SSE server
    mcp.run(transport="sse", host="0.0.0.0", port=8000)