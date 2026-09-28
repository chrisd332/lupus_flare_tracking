-- Create Database 
CREATE DATABASE IF NOT EXISTS lupus_tracker;
USE lupus_tracker;
    
-- Daily Patient Log Table
CREATE TABLE IF NOT EXISTS daily_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date DATE UNIQUE NOT NULL,
    pain_score INTEGER NOT NULL CHECK (pain_score BETWEEN 0 AND 10),
    fatigue_score INTEGER NOT NULL CHECK (fatigue_score BETWEEN 0 AND 10),
    flare_active BOOLEAN NOT NULL DEFAULT 0,
    notes TEXT
);

-- Environmental Factor Table
CREATE TABLE IF NOT EXISTS environmental_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date DATE UNIQUE NOT NULL,
    max_uv NUMERIC(4, 2),
    min_pressure NUMERIC(6, 2),
    max_pressure NUMERIC(6, 2),
    pressure_delta NUMERIC(6, 2),
    avg_temp NUMERIC(4, 2),
    FOREIGN KEY (entry_date) REFERENCES daily_logs(entry_date) ON DELETE CASCADE
);

-- Biometric / Wearable Integration Table
CREATE TABLE IF NOT EXISTS wearable_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date DATE UNIQUE NOT NULL,
    hrv_rmssd NUMERIC(5, 2),
    resting_hr INTEGER,
    sleep_hours NUMERIC(4, 2),
    steps INTEGER,
    FOREIGN KEY (entry_date) REFERENCES daily_logs(entry_date) ON DELETE CASCADE
);

-- Analytical View (Unified View for Reporting & Correlation)
CREATE VIEW IF NOT EXISTS v_lupus_analytical_mart AS
SELECT 
    d.entry_date,
    d.pain_score,
    d.fatigue_score,
    d.flare_active,
    d.notes,
    e.max_uv,
    e.pressure_delta,
    e.avg_temp,
    w.hrv_rmssd,
    w.resting_hr,
    w.sleep_hours,
    w.steps
FROM daily_logs d
LEFT JOIN environmental_data e ON d.entry_date = e.entry_date
LEFT JOIN wearable_data w ON d.entry_date = w.entry_date
ORDER BY d.entry_date ASC;