import sqlite3
import pandas as pd
from datetime import datetime, date

DB_NAME = "lupus_tracker.db"

def get_connection():
    """Establish and return a database connection."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables if they do not exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Daily Symptom Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT UNIQUE NOT NULL,
        pain_score INTEGER NOT NULL,
        fatigue_score INTEGER NOT NULL,
        flare_active INTEGER NOT NULL,
        notes TEXT
    )
    """)
    
    # 2. Environmental Data
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS environmental_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT UNIQUE NOT NULL,
        max_uv REAL,
        min_pressure REAL,
        max_pressure REAL,
        pressure_delta REAL,
        avg_temp REAL
    )
    """)
    
    # 3. Wearable / Biometric Data
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wearable_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT UNIQUE NOT NULL,
        hrv_rmssd REAL,
        resting_hr REAL,
        sleep_hours REAL,
        steps INTEGER
    )
    """)

    # 4. Optional Dietary / Nutritional Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dietary_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT UNIQUE NOT NULL,
        gluten INTEGER DEFAULT 0,
        dairy INTEGER DEFAULT 0,
        processed_sugar INTEGER DEFAULT 0,
        alcohol INTEGER DEFAULT 0,
        nightshades INTEGER DEFAULT 0,
        alfalfa_garlic INTEGER DEFAULT 0,
        high_sodium INTEGER DEFAULT 0,
        water_liters REAL DEFAULT 2.0,
        diet_notes TEXT
    )
    """)
    
    conn.commit()
    conn.close()

def insert_daily_log(log_date, pain_score, fatigue_score, flare_active, notes=""):
    """Insert or update daily symptom log."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO daily_logs (date, pain_score, fatigue_score, flare_active, notes)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT (date) DO UPDATE SET
        pain_score = excluded.pain_score,
        fatigue_score = excluded.fatigue_score,
        flare_active = excluded.flare_active,
        notes = excluded.notes
    """, (str(log_date), pain_score, fatigue_score, int(flare_active), notes))
    conn.commit()
    conn.close()

def insert_environmental_data(env_date, max_uv, min_pressure, max_pressure, pressure_delta, avg_temp):
    """Insert or update environmental data."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO environmental_data (date, max_uv, min_pressure, max_pressure, pressure_delta, avg_temp)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT (date) DO UPDATE SET
        max_uv = excluded.max_uv,
        min_pressure = excluded.min_pressure,
        max_pressure = excluded.max_pressure,
        pressure_delta = excluded.pressure_delta,
        avg_temp = excluded.avg_temp
    """, (str(env_date), max_uv, min_pressure, max_pressure, pressure_delta, avg_temp))
    conn.commit()
    conn.close()

def insert_wearable_data(wear_date, hrv_rmssd, resting_hr, sleep_hours, steps):
    """Insert or update wearable biometric data."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO wearable_data (date, hrv_rmssd, resting_hr, sleep_hours, steps)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT (date) DO UPDATE SET
        hrv_rmssd = excluded.hrv_rmssd,
        resting_hr = excluded.resting_hr,
        sleep_hours = excluded.sleep_hours,
        steps = excluded.steps
    """, (str(wear_date), hrv_rmssd, resting_hr, sleep_hours, steps))
    conn.commit()
    conn.close()

def insert_dietary_data(diet_date, gluten, dairy, sugar, alcohol, nightshades, alfalfa_garlic, sodium, water, notes=""):
    """Insert or update optional dietary habit logs."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO dietary_logs (date, gluten, dairy, processed_sugar, alcohol, nightshades, alfalfa_garlic, high_sodium, water_liters, diet_notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT (date) DO UPDATE SET
        gluten = excluded.gluten,
        dairy = excluded.dairy,
        processed_sugar = excluded.processed_sugar,
        alcohol = excluded.alcohol,
        nightshades = excluded.nightshades,
        alfalfa_garlic = excluded.alfalfa_garlic,
        high_sodium = excluded.high_sodium,
        water_liters = excluded.water_liters,
        diet_notes = excluded.diet_notes
    """, (str(diet_date), int(gluten), int(dairy), int(sugar), int(alcohol), int(nightshades), int(alfalfa_garlic), int(sodium), float(water), notes))
    conn.commit()
    conn.close()

def get_unified_dataset():
    """Extract complete merged dataset joined on date."""
    conn = get_connection()
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
        t.water_liters,
        t.diet_notes
    FROM daily_logs d
    LEFT JOIN environmental_data e ON d.date = e.date
    LEFT JOIN wearable_data w ON d.date = w.date
    LEFT JOIN dietary_logs t ON d.date = t.date
    ORDER BY d.date ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
    return df

if __name__ == "__main__":
    init_db()
    print("Database schema updated with dietary_logs.")