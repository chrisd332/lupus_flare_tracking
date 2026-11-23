import pandas as pd 
 
from datetime import datetime

import requests 
 
from database import insert_environmental_data 
 
def fetch_daily_weather(lat: float, lon: float, target_date: str): 
 
    """ 
    Fetches hourly weather data from Open-Meteo for target_date and computes daily metrics. 
    target_date format: 'YYYY-MM-DD' 
    """ 
 
    url = "https://archive-api.open-meteo.com/v1/archive" 
 
     
    # Fallback to forecast API if target_date is today or in the future 
 
    if pd.to_datetime(target_date).date() >= datetime.now().date(): 
 
        url = "https://api.open-meteo.com/v1/forecast" 
 
    params = { 
        "latitude": lat, 
        "longitude": lon, 
        "start_date": target_date, 
        "end_date": target_date, 
        "hourly": ["uv_index", "surface_pressure", "temperature_2m"], 
        "timezone": "auto" 
    } 
 
    try: 
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status() 
        data = response.json() 
        hourly = data.get("hourly", {}) 
        uv_series = hourly.get("uv_index", []) 
        pressure_series = hourly.get("surface_pressure", []) 
        temp_series = hourly.get("temperature_2m", []) 
        if not uv_series or not pressure_series: 
            return False, "Incomplete weather data returned." 
 
        max_uv = max([x for x in uv_series if x is not None], default=0.0)
        valid_pressures = [x for x in pressure_series if x is not None] 
 
        min_pressure = min(valid_pressures) if valid_pressures else 1013.25 
        max_pressure = max(valid_pressures) if valid_pressures else 1013.25 
        pressure_delta = max_pressure - min_pressure 
 
        valid_temps = [x for x in temp_series if x is not None] 
        avg_temp = sum(valid_temps) / len(valid_temps) if valid_temps else 20.0 
 
        insert_environmental_data( 
            env_date=target_date, 
            max_uv=round(max_uv, 2), 
            min_pressure=round(min_pressure, 2), 
            max_pressure=round(max_pressure, 2), 
            pressure_delta=round(pressure_delta, 2), 
            avg_temp=round(avg_temp, 2) 
        ) 
 
        return True, "Successfully ingested weather data." 
 
    except Exception as e: 
        return False, f"Weather ingestion failed: {str(e)}"