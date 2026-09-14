from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional
from datetime import datetime
import requests
from app.config import settings
from app.database import get_supabase_client
from pydantic import BaseModel

router = APIRouter()


class WeatherData(BaseModel):
    """Real-time weather data from Open-Meteo."""
    latitude: float
    longitude: float
    temperature: float
    humidity: int
    precipitation: float
    wind_speed: float
    condition: str
    timestamp: str
    source: str = "Open-Meteo"


@router.get("/current", response_model=WeatherData)
async def get_current_weather(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude"),
):
    """
    Fetch real-time weather from Open-Meteo API.
    
    No demo data - uses live coordinates and current conditions.
    """
    try:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
            "timezone": "auto"
        }
        
        response = requests.get(
            f"{settings.openmeteo_api_url}/forecast",
            params=params,
            timeout=10
        )
        
        if response.status_code != 200:
            return {"status": "UNAVAILABLE_DATA", "message": "Failed to fetch weather data"}
        
        data = response.json()
        current = data.get("current", {})
        
        # Map WMO weather codes to conditions
        weather_code = current.get("weather_code", 0)
        condition_map = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Foggy",
            48: "Foggy with rime",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with hail",
            99: "Thunderstorm with hail"
        }
        
        weather = WeatherData(
            latitude=latitude,
            longitude=longitude,
            temperature=current.get("temperature_2m", 0),
            humidity=current.get("relative_humidity_2m", 0),
            precipitation=current.get("precipitation", 0),
            wind_speed=current.get("wind_speed_10m", 0),
            condition=condition_map.get(weather_code, "Unknown"),
            timestamp=datetime.now().isoformat(),
            source="Open-Meteo"
        )
        
        return weather
    
    except Exception as e:
        return {"status": "UNAVAILABLE_DATA", "message": str(e)}


@router.get("/forecast")
async def get_weather_forecast(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    days: int = Query(7, ge=1, le=16, description="Forecast days"),
):
    """
    Get 7-16 day weather forecast from Open-Meteo.
    """
    try:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
            "timezone": "auto",
            "forecast_days": days
        }
        
        response = requests.get(
            f"{settings.openmeteo_api_url}/forecast",
            params=params,
            timeout=10
        )
        
        if response.status_code != 200:
            return {"status": "UNAVAILABLE_DATA"}
        
        data = response.json()
        daily = data.get("daily", {})
        
        forecast = []
        dates = daily.get("time", [])
        temps_max = daily.get("temperature_2m_max", [])
        temps_min = daily.get("temperature_2m_min", [])
        precip = daily.get("precipitation_sum", [])
        
        for i, date in enumerate(dates[:days]):
            forecast.append({
                "date": date,
                "temp_max": temps_max[i] if i < len(temps_max) else None,
                "temp_min": temps_min[i] if i < len(temps_min) else None,
                "precipitation": precip[i] if i < len(precip) else 0,
                "source": "Open-Meteo"
            })
        
        return forecast if forecast else {"status": "UNAVAILABLE_DATA"}
    
    except Exception as e:
        return {"status": "UNAVAILABLE_DATA", "message": str(e)}


@router.get("/profile-weather")
async def get_profile_weather(
    user_id: str = Query(..., description="Supabase user ID"),
    supabase=Depends(get_supabase_client)
):
    """
    Get weather for user's profile location (from Supabase).
    """
    try:
        # Fetch user profile with coordinates
        profile = supabase.table("profiles").select("latitude,longitude").eq("id", user_id).execute()
        
        if not profile.data:
            return {"status": "UNAVAILABLE_DATA", "message": "User profile not found"}
        
        user_loc = profile.data[0]
        lat = user_loc.get("latitude")
        lon = user_loc.get("longitude")
        
        if not lat or not lon:
            return {"status": "UNAVAILABLE_DATA", "message": "User location not configured"}
        
        # Fetch weather for user's coordinates
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
            "timezone": "auto"
        }
        
        response = requests.get(
            f"{settings.openmeteo_api_url}/forecast",
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            current = data.get("current", {})
            return {
                "location": {"latitude": lat, "longitude": lon},
                "weather": {
                    "temperature": current.get("temperature_2m"),
                    "humidity": current.get("relative_humidity_2m"),
                    "wind_speed": current.get("wind_speed_10m")
                },
                "source": "Open-Meteo",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {"status": "UNAVAILABLE_DATA"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
