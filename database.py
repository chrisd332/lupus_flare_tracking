import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from typing import Optional, Union

import pandas as pd

DEFAULT_DB_PATH = os.getenv("LUPUS_DB_PATH", "lupus_tracker.db")


def normalize_date(value: Union[str, date, datetime]) -> str:
    """Normalize date/datetime/string inputs to strict ISO YYYY-MM-DD format."""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return datetime.fromisoformat(value.strip()[:10]).date().isoformat()
    raise ValueError(f"Unsupported date value: {value!r}")


def _clamp_int(value: int, low: int, high: int) -> int:
    return max(low, min(high, int(value)))


@contextmanager
def get_connection(db_path: str = DEFAULT_DB_PATH):
    """Context-managed SQLite connection with foreign keys enabled."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initialize database tables and run lightweight schema migrations."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL,
            pain_score INTEGER NOT NULL CHECK (pain_score BETWEEN 0 AND 10),
            fatigue_score INTEGER NOT NULL CHECK (fatigue_score BETWEEN 0 AND 10),
            flare_active INTEGER NOT NULL DEFAULT 0 CHECK (flare_active IN (0, 1)),
            notes TEXT DEFAULT ''
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS environmental_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL,
            max_uv REAL,
            min_pressure REAL,
            max_pressure REAL,
            pressure_delta REAL,
            avg_temp REAL,
            FOREIGN KEY (date) REFERENCES daily_logs(date) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS wearable_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL,
            hrv_rmssd REAL,
            resting_hr REAL,
            sleep_hours REAL,
            steps INTEGER,
            FOREIGN KEY (date) REFERENCES daily_logs(date) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS dietary_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL,
            gluten INTEGER NOT NULL DEFAULT 0,
            dairy INTEGER NOT NULL DEFAULT 0,
            processed_sugar INTEGER NOT NULL DEFAULT 0,
            alcohol INTEGER NOT NULL DEFAULT 0,
            nightshades INTEGER NOT NULL DEFAULT 0,
            alfalfa_garlic INTEGER NOT NULL DEFAULT 0,
            high_sodium INTEGER NOT NULL DEFAULT 0,
            strenuous_activity INTEGER NOT NULL DEFAULT 0,
            water_liters REAL DEFAULT 2.0,
            diet_notes TEXT DEFAULT '',
            FOREIGN KEY (date) REFERENCES daily_logs(date) ON DELETE CASCADE
        )
        """)

        # Lightweight migration for older DB files missing strenuous_activity
        existing_cols = {
            row["name"] for row in cursor.execute("PRAGMA table_info(dietary_logs);").fetchall()
        }
        if "strenuous_activity" not in existing_cols:
            cursor.execute(
                "ALTER TABLE dietary_logs ADD COLUMN strenuous_activity INTEGER NOT NULL DEFAULT 0;"
            )


def insert_daily_log(
    log_date: Union[str, date, datetime],
    pain_score: int,
    fatigue_score: int,
    flare_active: Union[bool, int],
    notes: str = "",
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    """Insert or update daily symptom log."""
    iso_date = normalize_date(log_date)
    pain = _clamp_int(pain_score, 0, 10)
    fatigue = _clamp_int(fatigue_score, 0, 10)
    flare = 1 if bool(flare_active) else 0

    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO daily_logs (date, pain_score, fatigue_score, flare_active, notes)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (date) DO UPDATE SET
                pain_score = excluded.pain_score,
                fatigue_score = excluded.fatigue_score,
                flare_active = excluded.flare_active,
                notes = excluded.notes
            """,
            (iso_date, pain, fatigue, flare, notes or ""),
        )


def insert_environmental_data(
    env_date: Union[str, date, datetime],
    max_uv: Optional[float],
    min_pressure: Optional[float],
    max_pressure: Optional[float],
    pressure_delta: Optional[float],
    avg_temp: Optional[float],
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    """Insert or update environmental data (ensures parent daily_logs row exists)."""
    iso_date = normalize_date(env_date)
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO daily_logs (date, pain_score, fatigue_score, flare_active, notes)
            VALUES (?, 0, 0, 0, '')
            """,
            (iso_date,),
        )
        conn.execute(
            """
            INSERT INTO environmental_data (date, max_uv, min_pressure, max_pressure, pressure_delta, avg_temp)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (date) DO UPDATE SET
                max_uv = excluded.max_uv,
                min_pressure = excluded.min_pressure,
                max_pressure = excluded.max_pressure,
                pressure_delta = excluded.pressure_delta,
                avg_temp = excluded.avg_temp
            """,
            (iso_date, max_uv, min_pressure, max_pressure, pressure_delta, avg_temp),
        )


def insert_wearable_data(
    wear_date: Union[str, date, datetime],
    hrv_rmssd: Optional[float],
    resting_hr: Optional[float],
    sleep_hours: Optional[float],
    steps: Optional[int],
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    """Insert or update wearable biometric data."""
    iso_date = normalize_date(wear_date)
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO wearable_data (date, hrv_rmssd, resting_hr, sleep_hours, steps)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (date) DO UPDATE SET
                hrv_rmssd = excluded.hrv_rmssd,
                resting_hr = excluded.resting_hr,
                sleep_hours = excluded.sleep_hours,
                steps = excluded.steps
            """,
            (iso_date, hrv_rmssd, resting_hr, sleep_hours, steps),
        )


def insert_dietary_data(
    diet_date: Union[str, date, datetime],
    gluten: Union[bool, int],
    dairy: Union[bool, int],
    sugar: Union[bool, int],
    alcohol: Union[bool, int],
    nightshades: Union[bool, int],
    alfalfa_garlic: Union[bool, int],
    sodium: Union[bool, int],
    water: float,
    notes: str = "",
    strenuous_activity: Union[bool, int] = 0,
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    """Insert or update optional dietary and physical strain logs."""
    iso_date = normalize_date(diet_date)
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO dietary_logs (
                date, gluten, dairy, processed_sugar, alcohol,
                nightshades, alfalfa_garlic, high_sodium, strenuous_activity,
                water_liters, diet_notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (date) DO UPDATE SET
                gluten = excluded.gluten,
                dairy = excluded.dairy,
                processed_sugar = excluded.processed_sugar,
                alcohol = excluded.alcohol,
                nightshades = excluded.nightshades,
                alfalfa_garlic = excluded.alfalfa_garlic,
                high_sodium = excluded.high_sodium,
                strenuous_activity = excluded.strenuous_activity,
                water_liters = excluded.water_liters,
                diet_notes = excluded.diet_notes
            """,
            (
                iso_date,
                int(bool(gluten)),
                int(bool(dairy)),
                int(bool(sugar)),
                int(bool(alcohol)),
                int(bool(nightshades)),
                int(bool(alfalfa_garlic)),
                int(bool(sodium)),
                int(bool(strenuous_activity)),
                float(water),
                notes or "",
            ),
        )


def clear_all_logs(db_path: str = DEFAULT_DB_PATH) -> None:
    """Safely clear all stored patient logs across tables."""
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM dietary_logs;")
        conn.execute("DELETE FROM wearable_data;")
        conn.execute("DELETE FROM environmental_data;")
        conn.execute("DELETE FROM daily_logs;")


def get_unified_dataset(db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """Extract complete merged dataset joined on date."""
    with get_connection(db_path) as conn:
        query = """
        SELECT 
            d.date,
            d.pain_score,
            d.fatigue_score,
            d.flare_active,
            d.notes,
            e.max_uv,
            e.min_pressure,
            e.max_pressure,
            e.pressure_delta,
            e.avg_temp,
            w.hrv_rmssd,
            w.resting_hr,
            w.sleep_hours,
            w.steps,
            t.gluten,
            t.dairy,
            t.processed_sugar,
            t.alcohol,
            t.nightshades,
            t.alfalfa_garlic,
            t.high_sodium,
            t.strenuous_activity,
            t.water_liters,
            t.diet_notes
        FROM daily_logs d
        LEFT JOIN environmental_data e ON d.date = e.date
        LEFT JOIN wearable_data w ON d.date = w.date
        LEFT JOIN dietary_logs t ON d.date = t.date
        ORDER BY d.date ASC
        """
        df = pd.read_sql_query(query, conn)

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


if __name__ == "__main__":
    init_db()
    print("Database schema initialized and verified.")