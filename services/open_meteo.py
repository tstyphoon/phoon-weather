"""Open-Meteo：海外地點，以及氣象署查不到時的備援。免金鑰。"""
from __future__ import annotations

import httpx

GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST = "https://api.open-meteo.com/v1/forecast"


class OpenMeteoError(Exception):
    pass


async def geocode(client: httpx.AsyncClient, name: str) -> dict | None:
    """地名 -> {name, country, lat, lon}。找不到回傳 None。"""
    try:
        r = await client.get(GEOCODE, params={"name": name, "count": 1, "language": "zh"})
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise OpenMeteoError(str(e)) from None
    results = r.json().get("results") or []
    if not results:
        return None
    g = results[0]
    return {"name": g.get("name", name), "country": g.get("country", ""),
            "admin1": g.get("admin1", ""), "lat": g["latitude"], "lon": g["longitude"]}


async def forecast(client: httpx.AsyncClient, lat: float, lon: float, day_offset: int) -> dict:
    """day_offset：0 今天、1 明天、2 後天。風速單位 m/s。"""
    try:
        r = await client.get(FORECAST, params={
            "latitude": lat, "longitude": lon, "timezone": "auto", "forecast_days": 4,
            "wind_speed_unit": "ms",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,"
                     "wind_speed_10m_max",
            "current": "temperature_2m,wind_speed_10m,precipitation"})
        r.raise_for_status()
        j = r.json()
        d = j["daily"]
        return {
            "temp_min": d["temperature_2m_min"][day_offset],
            "temp_max": d["temperature_2m_max"][day_offset],
            "rain_prob": d["precipitation_probability_max"][day_offset],
            "wind_speed": d["wind_speed_10m_max"][day_offset],
            "now": {"temp": j["current"]["temperature_2m"],
                    "wind_speed": j["current"]["wind_speed_10m"],
                    "rain_mm": j["current"]["precipitation"]},
        }
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
        raise OpenMeteoError(str(e)) from None
