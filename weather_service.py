from typing import Tuple
import requests
from database import insert_environmental_data, normalize_date

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"


def geocode_city(city_query: str) -> Tuple[float, float, str]:
    """Resolve a city/state string to (lat, lon, resolved_label) with Bowie, MD fallback."""
    query = (city_query or "").strip()
    if not query:
        return 38.9615, -76.7347, "Bowie, Maryland (Default)"

    try:
        resp = requests.get(
            OPEN_METEO_GEOCODE_URL,
            params={"name": query, "count": 1, "language": "en", "format": "json"},
            timeout=8,
        )
        resp.raise_for_status()
        results = resp.json().get("results") or []
        if results:
            top = results[0]
            label_parts = [top.get("name"), top.get("admin1"), top.get("country_code")]
            label = ", ".join([p for p in label_parts if p])
            return float(top["latitude"]), float(top["longitude"]), label
    except requests.RequestException:
        pass

    return 38.9615, -76.7347, "Bowie, Maryland (Fallback)"


def fetch_daily_weather(lat: float, lon: float, target_date: str) -> Tuple[bool, str]:
    """Fetch daily UV, barometric pressure swing, and temperature from Open-Meteo and store in SQLite."""
    if not (-90.0 <= float(lat) <= 90.0 and -180.0 <= float(lon) <= 180.0):
        return False, "Invalid latitude/longitude coordinates."

    try:
        iso_date = normalize_date(target_date)
    except ValueError as exc:
        return False, str(exc)

    params = {
        "latitude": round(float(lat), 4),
        "longitude": round(float(lon), 4),
        "daily": "uv_index_max,temperature_2m_mean",
        "hourly": "surface_pressure",
        "start_date": iso_date,
        "end_date": iso_date,
        "timezone": "auto",
    }

    try:
        resp = requests.get(OPEN_METEO_FORECAST_URL, params=params, timeout=10)
        if resp.status_code == 400:
            # Older dates outside forecast window fall back to archive endpoint
            resp = requests.get(OPEN_METEO_ARCHIVE_URL, params=params, timeout=10)
        resp.raise_for_status()
        payload = resp.json()

        daily = payload.get("daily", {})
        hourly = payload.get("hourly", {})

        uv_list = daily.get("uv_index_max") or [None]
        temp_list = daily.get("temperature_2m_mean") or [None]
        pressures = [p for p in (hourly.get("surface_pressure") or []) if p is not None]

        max_uv = round(float(uv_list[0]), 1) if uv_list[0] is not None else None
        avg_temp = round(float(temp_list[0]), 1) if temp_list[0] is not None else None

        if pressures:
            min_p = round(float(min(pressures)), 1)
            max_p = round(float(max(pressures)), 1)
            p_delta = round(max_p - min_p, 1)
        else:
            min_p = max_p = p_delta = None

        insert_environmental_data(
            env_date=iso_date,
            max_uv=max_uv,
            min_pressure=min_p,
            max_pressure=max_p,
            pressure_delta=p_delta,
            avg_temp=avg_temp,
        )
        return True, f"UV {max_uv if max_uv is not None else 'N/A'}, ΔP {p_delta if p_delta is not None else 'N/A'} hPa"
    except requests.Timeout:
        return False, "Weather API timed out after 10s."
    except requests.RequestException as exc:
        return False, f"Weather API request failed: {exc}"