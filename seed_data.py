import numpy as np
import pandas as pd
from datetime import date, timedelta
from database import (
    init_db, insert_daily_log, insert_environmental_data,
    insert_wearable_data, insert_dietary_data
)

def generate_mock_data(days=60):
    init_db()
    np.random.seed(42)
    end_dt = date.today()
    start_dt = end_dt - timedelta(days=days)

    dates = [start_dt + timedelta(days=i) for i in range(days)]

    # Environmental baselines
    uv_base = np.clip(np.random.normal(loc=5.5, scale=2.5, size=days), 1.0, 11.0)
    p_delta_base = np.clip(np.random.exponential(scale=3.5, size=days), 1.0, 14.0)
    temps = np.random.normal(loc=22.0, scale=4.0, size=days)

    # Wearables
    sleep = np.clip(np.random.normal(loc=7.2, scale=1.1, size=days), 3.5, 9.5)
    hrv = np.clip(np.random.normal(loc=46.0, scale=10.0, size=days), 18.0, 75.0)
    rhr = np.clip(np.random.normal(loc=66.0, scale=6.0, size=days), 54, 90)
    steps = np.clip(np.random.normal(loc=5500, scale=1800, size=days), 800, 12000).astype(int)

    # Diet flags (simulated intermittent triggers)
    sugar_flags = (np.random.rand(days) > 0.7).astype(int)
    alcohol_flags = (np.random.rand(days) > 0.8).astype(int)
    alfalfa_garlic = (np.random.rand(days) > 0.85).astype(int)

    for i in range(days):
        base_pain = 2.0 + np.random.normal(0, 0.6)
        base_fatigue = 3.0 + np.random.normal(0, 0.8)

        # Causal triggers at T-2 days
        lag_2_uv = uv_base[i - 2] if i >= 2 else 4.0
        lag_2_p = p_delta_base[i - 2] if i >= 2 else 3.0
        lag_2_diet = alfalfa_garlic[i - 2] if i >= 2 else 0

        if lag_2_uv > 7.5 or lag_2_p > 7.0 or lag_2_diet == 1:
            base_pain += 4.0
            base_fatigue += 3.5
            hrv[i] = max(18.0, hrv[i] - 15.0)

        pain_val = int(np.clip(round(base_pain), 0, 10))
        fatigue_val = int(np.clip(round(base_fatigue), 0, 10))
        is_flare = 1 if (pain_val >= 6 or fatigue_val >= 7) else 0
        dt_str = str(dates[i])

        insert_daily_log(dt_str, pain_val, fatigue_val, is_flare, "Auto-generated log.")
        insert_environmental_data(
            dt_str,
            max_uv=round(float(uv_base[i]), 1),
            min_pressure=round(1013.25 - float(p_delta_base[i]) / 2, 1),
            max_pressure=round(1013.25 + float(p_delta_base[i]) / 2, 1),
            pressure_delta=round(float(p_delta_base[i]), 1),
            avg_temp=round(float(temps[i]), 1)
        )
        insert_wearable_data(
            dt_str,
            hrv_rmssd=round(float(hrv[i]), 1),
            resting_hr=int(rhr[i]),
            sleep_hours=round(float(sleep[i]), 1),
            steps=int(steps[i])
        )
        insert_dietary_data(
            diet_date=dt_str,
            gluten=int(np.random.rand() > 0.6),
            dairy=int(np.random.rand() > 0.5),
            sugar=int(sugar_flags[i]),
            alcohol=int(alcohol_flags[i]),
            nightshades=int(np.random.rand() > 0.7),
            alfalfa_garlic=int(alfalfa_garlic[i]),
            sodium=int(np.random.rand() > 0.5),
            water=round(float(np.random.uniform(1.5, 3.0)), 1),
            notes="Standard intake"
        )

    print(f"Generated {days} days of sample data with diet correlation.")

if __name__ == "__main__":
    generate_mock_data()