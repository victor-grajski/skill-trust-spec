"""Weather check skill."""
import requests

def get_weather(city: str) -> dict:
    """Fetch weather for city."""
    # Implementation
    return {"city": city, "temp": 72, "condition": "sunny"}
