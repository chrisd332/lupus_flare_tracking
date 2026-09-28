import pandas as pd
import numpy as np
from scipy.stats import pearsonr, spearmanr
from database import get_unified_dataset

def build_lagged_features(df: pd.DataFrame) -> pd.DataFrame:
    """Creates T-1, T-2, and T-3 lagged columns for environmental and wearable metrics."""
    if df.empty or len(df) < 5:
        return df

    df = df.sort_values("date").copy()
    target_cols = ['max_uv', 'pressure_delta', 'hrv_rmssd', 'sleep_hours']

    for col in target_cols:
        if col in df.columns:
            for lag in [1, 2, 3]:
                df[f"{col}_lag_{lag}"] = df[col].shift(lag)

    return df

def compute_lagged_correlations(df: pd.DataFrame, target_metric='pain_score'):
    """
    Calculates Pearson & Spearman correlations between lagged triggers
    and target pain/flare outcomes.
    """
    df_lagged = build_lagged_features(df)
    if df_lagged.empty or len(df_lagged.dropna(subset=[target_metric])) < 5:
        return pd.DataFrame()

    results = []
    feature_cols = [c for c in df_lagged.columns if "_lag_" in c]

    for col in feature_cols:
        valid = df_lagged[[col, target_metric]].dropna()
        if len(valid) > 5:
            p_corr, p_val = pearsonr(valid[col], valid[target_metric])
            s_corr, s_val = spearmanr(valid[col], valid[target_metric])
            
            parts = col.split("_lag_")
            base_feature = parts[0]
            lag_days = int(parts[1])

            results.append({
                "Feature": base_feature,
                "Lag_Days": lag_days,
                "Pearson_r": round(p_corr, 3),
                "Pearson_p": round(p_val, 4),
                "Spearman_r": round(s_corr, 3),
                "Spearman_p": round(s_val, 4)
            })

    return pd.DataFrame(results)

def calculate_48h_risk_index(df: pd.DataFrame) -> float:
    """
    Calculates 0-100% vulnerability risk index based on recent 48-hour exposure:
    - High UV exposure (UV >= 5 or >= 8)
    - Significant barometric swings (Pressure Delta >= 6 or >= 10 hPa)
    - Suppressed HRV (HRV < 40 or < 25 ms)
    - Severe sleep deprivation (Sleep < 6.5 or < 5 hrs)
    """
    if df.empty or len(df) < 2:
        return 15.0  # Baseline default risk

    recent = df.sort_values("date").tail(2)

    uv_score = 0
    pressure_score = 0
    hrv_score = 0
    sleep_score = 0

    # Evaluate 48h UV exposure
    max_uv_48h = recent['max_uv'].max()
    if pd.notnull(max_uv_48h):
        if max_uv_48h >= 8:
            uv_score = 30
        elif max_uv_48h >= 5:
            uv_score = 15

    # Evaluate 48h pressure instability
    max_p_delta = recent['pressure_delta'].max()
    if pd.notnull(max_p_delta):
        if max_p_delta >= 10:
            pressure_score = 30
        elif max_p_delta >= 6:
            pressure_score = 15

    # Evaluate HRV suppression
    min_hrv = recent['hrv_rmssd'].min()
    if pd.notnull(min_hrv):
        if min_hrv < 25:
            hrv_score = 25
        elif min_hrv < 40:
            hrv_score = 12

    # Evaluate Sleep deprivation
    min_sleep = recent['sleep_hours'].min()
    if pd.notnull(min_sleep):
        if min_sleep < 5:
            sleep_score = 15
        elif min_sleep < 6.5:
            sleep_score = 8

    total_risk = float(uv_score + pressure_score + hrv_score + sleep_score)
    return min(100.0, max(5.0, total_risk))