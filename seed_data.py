from datetime import date, timedelta
import numpy as np
from database import (
    DEFAULT_DB_PATH,
    clear_all_logs,
    init_db,
    insert_daily_log,
    insert_dietary_data,
    insert_environmental_data,
    insert_wearable_data,
)


def generate_mock_data(
    days: int = 60,
    seed: int = 42,
    overwrite: bool = True,
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    """Generate synthetic 60-day longitudinal demo records without mutating global RNG state."""
    init_db(db_path)
    if overwrite:
        clear_all_logs(db_path)

    rng = np.random.default_rng(seed)
    end_dt = date.today()
    start_dt = end_dt - timedelta(days=days - 1)
    dates = [start_dt + timedelta(days=i) for i in range(days)]

    uv_base = np.clip(rng.normal(loc=5.5, scale=2.5, size=days), 1.0, 11.0)
    p_delta_base = np.clip(rng.exponential(scale=3.5, size=days), 1.0, 14.0)
    temps = rng.normal(loc=22.0, scale=4.0, size=days)

    sleep = np.clip(rng.normal(loc=7.2, scale=1.1, size=days), 3.5, 9.5)
    hrv = np.clip(rng.normal(loc=46.0, scale=10.0, size=days), 18.0, 75.0)
    rhr = np.clip(rng.normal(loc=66.0, scale=6.0, size=days), 54, 90)
    steps = np.clip(rng.normal(loc=5500, scale=1800, size=days), 800, 12000).astype(int)

    sugar_flags = (rng.random(days) > 0.7).astype(int)
    alcohol_flags = (rng.random(days) > 0.8).astype(int)
    alfalfa_garlic = (rng.random(days) > 0.85).astype(int)
    strain_flags = (rng.random(days) > 0.78).astype(int)

    for i in range(days):
        base_pain = 2.0 + float(rng.normal(0, 0.6))
        base_fatigue = 3.0 + float(rng.normal(0, 0.8))

        lag_2_uv = uv_base[i - 2] if i >= 2 else 4.0
        lag_2_p = p_delta_base[i - 2] if i >= 2 else 3.0
        lag_2_diet = alfalfa_garlic[i - 2] if i >= 2 else 0
        lag_2_strain = strain_flags[i - 2] if i >= 2 else 0

        if lag_2_uv > 7.5 or lag_2_p > 7.0 or lag_2_diet == 1 or lag_2_strain == 1:
            base_pain += 3.8
            base_fatigue += 3.2
            hrv[i] = max(18.0, hrv[i] - 14.0)

        pain_val = int(np.clip(round(base_pain), 0, 10))
        fatigue_val = int(np.clip(round(base_fatigue), 0, 10))
        is_flare = 1 if (pain_val >= 6 or fatigue_val >= 7) else 0
        dt_str = dates[i].isoformat()

        insert_daily_log(
            dt_str,
            pain_val,
            fatigue_val,
            is_flare,
            "Synthetic demo record (simulated multi-factor exposure).",
            db_path=db_path,
        )
        insert_environmental_data(
            dt_str,
            max_uv=round(float(uv_base[i]), 1),
            min_pressure=round(1013.25 - float(p_delta_base[i]) / 2.0, 1),
            max_pressure=round(1013.25 + float(p_delta_base[i]) / 2.0, 1),
            pressure_delta=round(float(p_delta_base[i]), 1),
            avg_temp=round(float(temps[i]), 1),
            db_path=db_path,
        )
        insert_wearable_data(
            dt_str,
            hrv_rmssd=round(float(hrv[i]), 1),
            resting_hr=int(rhr[i]),
            sleep_hours=round(float(sleep[i]), 1),
            steps=int(steps[i]),
            db_path=db_path,
        )
        insert_dietary_data(
            diet_date=dt_str,
            gluten=int(rng.random() > 0.6),
            dairy=int(rng.random() > 0.5),
            sugar=int(sugar_flags[i]),
            alcohol=int(alcohol_flags[i]),
            nightshades=int(rng.random() > 0.7),
            alfalfa_garlic=int(alfalfa_garlic[i]),
            sodium=int(rng.random() > 0.5),
            water=round(float(rng.uniform(1.5, 3.0)), 1),
            notes="Synthetic demo nutrition entry",
            strenuous_activity=int(strain_flags[i]),
            db_path=db_path,
        )


if __name__ == "__main__":
    generate_mock_data()
    print("Generated 60 days of synthetic sample data.")