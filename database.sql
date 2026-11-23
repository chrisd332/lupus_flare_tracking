PRAGMA foreign_keys = ON;

-- 1. Daily Patient Symptom Logs
CREATE TABLE IF NOT EXISTS daily_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT UNIQUE NOT NULL,
    pain_score INTEGER NOT NULL CHECK (pain_score BETWEEN 0 AND 10),
    fatigue_score INTEGER NOT NULL CHECK (fatigue_score BETWEEN 0 AND 10),
    flare_active INTEGER NOT NULL DEFAULT 0 CHECK (flare_active IN (0, 1)),
    notes TEXT DEFAULT ''
);

-- 2. Environmental Data
CREATE TABLE IF NOT EXISTS environmental_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT UNIQUE NOT NULL,
    max_uv REAL,
    min_pressure REAL,
    max_pressure REAL,
    pressure_delta REAL,
    avg_temp REAL,
    FOREIGN KEY (date) REFERENCES daily_logs(date) ON DELETE CASCADE
);

-- 3. Wearable & Biometric Data
CREATE TABLE IF NOT EXISTS wearable_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT UNIQUE NOT NULL,
    hrv_rmssd REAL,
    resting_hr REAL,
    sleep_hours REAL,
    steps INTEGER,
    FOREIGN KEY (date) REFERENCES daily_logs(date) ON DELETE CASCADE
);

-- 4. Dietary & Physical Strain Logs
CREATE TABLE IF NOT EXISTS dietary_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT UNIQUE NOT NULL,
    gluten INTEGER NOT NULL DEFAULT 0 CHECK (gluten IN (0, 1)),
    dairy INTEGER NOT NULL DEFAULT 0 CHECK (dairy IN (0, 1)),
    processed_sugar INTEGER NOT NULL DEFAULT 0 CHECK (processed_sugar IN (0, 1)),
    alcohol INTEGER NOT NULL DEFAULT 0 CHECK (alcohol IN (0, 1)),
    nightshades INTEGER NOT NULL DEFAULT 0 CHECK (nightshades IN (0, 1)),
    alfalfa_garlic INTEGER NOT NULL DEFAULT 0 CHECK (alfalfa_garlic IN (0, 1)),
    high_sodium INTEGER NOT NULL DEFAULT 0 CHECK (high_sodium IN (0, 1)),
    strenuous_activity INTEGER NOT NULL DEFAULT 0 CHECK (strenuous_activity IN (0, 1)),
    water_liters REAL DEFAULT 2.0,
    diet_notes TEXT DEFAULT '',
    FOREIGN KEY (date) REFERENCES daily_logs(date) ON DELETE CASCADE
);

-- 5. Unified Analytical Mart View
CREATE VIEW IF NOT EXISTS v_lupus_analytical_mart AS
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
ORDER BY d.date ASC;