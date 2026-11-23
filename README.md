# Lupus Flare Tracker & Early Warning Engine

A longitudinal multi-factor autoimmune decision-support and analytics platform designed to surface delayed symptom triggers across environmental conditions, wearable biometrics, physical exertion, and dietary patterns.

## Project Architecture

This repository provides two ways to explore and run the platform:

1. **Primary Python + Streamlit + SQLite Engine (`app.py`, `database.py`, `analytics.py`, `weather_service.py`, `seed_data.py`)**
   - Relational SQLite persistence (`daily_logs`, `environmental_data`, `wearable_data`, `dietary_logs`).
   - Automated weather and UV/barometric pressure ingestion via the Open-Meteo API.
   - Time-lagged Pearson & Spearman correlation discovery (`T-1` to `T-3` days) and a configurable 48-hour acute risk index.
   - One-page print-ready Clinical Briefing for rheumatology appointments.

2. **Static Browser Demo (`index.html`, `tracking_analytics.html`)**
   - Zero-backend Tailwind CSS + Plotly.js web portal using browser `localStorage` for instant static hosting (e.g., GitHub Pages).
   - Includes a one-click **Demo Guest** mode pre-populated with 60 days of synthetic longitudinal data, natural-language meal parsing, physical strain logging, and a printable clinical brief.
   - *Note:* Authentication in `index.html` is a client-side `localStorage` prototype intended solely for demonstration and portfolio review—not for storing real Protected Health Information (PHI).

## Quick Start (Python / Streamlit App)

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the application
streamlit run app.py