import json
from datetime import datetime
import os
import time
import requests


current_weather = ""


def update_weather() -> None:
    print(f"ℹ️ Weather update started")

    global current_weather
    lat = os.getenv("WEATHER_LAT")
    lon = os.getenv("WEATHER_LON")
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not (lat and lon and api_key):
        current_weather = ""
        return

    path = os.path.join("data", os.getenv("INSTANCE_NAME", "default"), "weather.txt")
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < 3 * 3600:
        try:
            with open(path, "r", encoding="utf-8") as f:
                current_weather = f.read().strip()
            return
        except Exception:
            pass

    try:
        url = (
            "https://api.openweathermap.org/data/2.5/weather"
            f"?lat={lat}&lon={lon}"
            "&units=metric&lang=en"
            f"&appid={api_key}"
        )

        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        current_weather = f"{temp}°C, {desc}"

        print(f"ℹ️ Got weather from API: {current_weather}")

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(current_weather)
    except Exception as e:
        current_weather = ""
        print(f"⛔ Weather update failed: {e}")


def enhance_system_prompt(prompt: str) -> str:
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    hour = now.hour
    if 5 <= hour < 12:
        period = "morning"
    elif 12 <= hour < 17:
        period = "day"
    elif 17 <= hour < 22:
        period = "evening"
    else:
        period = "night"
    result = (
        f"{prompt}\nIf your answer is related to daytime, use this info Current date: {date_str}. Current time: {time_str}. It's {period}."
    )
    if current_weather:
        result += f"\nIf your answer is related to weather, use this info Current weather: {current_weather}."
    return result

