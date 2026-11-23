import math
import pandas as pd
import numpy as np
from database import get_unified_dataset

def build_lagged_features(df: pd.DataFrame) -> pd.DataFrame:
    """Creates T-1, T-2, and T-3 lagged columns for environmental, wearable, and dietary metrics."""
    if df.empty or len(df) < 5:
        return df

    df = df.sort_values("date").copy()
    
    # Expanded list of target exposure features
    target_cols = [
        'max_uv', 'pressure_delta', 'hrv_rmssd', 'sleep_hours',
        'processed_sugar', 'alcohol', 'nightshades', 'alfalfa_garlic', 'high_sodium'
    ]

    for col in target_cols:
        if col in df.columns:
            for lag in [1, 2, 3]:
                df[f"{col}_lag_{lag}"] = df[col].shift(lag)

    return df

def compute_lagged_correlations(df: pd.DataFrame, target_metric='pain_score'):
    """Calculates Pearson & Spearman correlations for lagged triggers."""
    df_lagged = build_lagged_features(df)
    if df_lagged.empty or len(df_lagged.dropna(subset=[target_metric])) < 5:
        return pd.DataFrame()

    results = []
    feature_cols = [c for c in df_lagged.columns if "_lag_" in c]

    for col in feature_cols:
        valid = df_lagged[[col, target_metric]].dropna()
        n = len(valid)
        # Ensure we have at least some variance in the candidate feature
        if n > 5 and valid[col].nunique() > 1:
            p_corr = valid[col].corr(valid[target_metric], method='pearson')
            
            if abs(p_corr) >= 1.0:
                p_val = 0.0
            else:
                t_stat = p_corr * np.sqrt((n - 2) / max(0.0001, (1 - p_corr**2)))
                p_val = max(0.0001, round(2 * (1 - 0.5 * (1 + math.erf(abs(t_stat) / math.sqrt(2)))), 4))

            s_corr = valid[col].corr(valid[target_metric], method='spearman')
            
            parts = col.split("_lag_")
            base_feature = parts[0]
            lag_days = int(parts[1])

            results.append({
                "Feature": base_feature,
                "Lag_Days": lag_days,
                "Pearson_r": round(float(p_corr), 3) if pd.notnull(p_corr) else 0.0,
                "Pearson_p": p_val,
                "Spearman_r": round(float(s_corr), 3) if pd.notnull(s_corr) else 0.0,
                "Spearman_p": p_val
            })

    return pd.DataFrame(results)

def calculate_48h_risk_index(df: pd.DataFrame) -> float:
    """Calculates 0-100% vulnerability risk index based on recent 48-hour exposure."""
    if df.empty or len(df) < 2:
        return 15.0

    recent = df.sort_values("date").tail(2)

    uv_score = 0
    pressure_score = 0
    hrv_score = 0
    sleep_score = 0
    diet_score = 0

    # Environmental
    max_uv_48h = recent['max_uv'].max()
    if pd.notnull(max_uv_48h):
        if max_uv_48h >= 8: uv_score = 25
        elif max_uv_48h >= 5: uv_score = 12

    max_p_delta = recent['pressure_delta'].max()
    if pd.notnull(max_p_delta):
        if max_p_delta >= 10: pressure_score = 25
        elif max_p_delta >= 6: pressure_score = 12

    # Biometrics
    min_hrv = recent['hrv_rmssd'].min()
    if pd.notnull(min_hrv):
        if min_hrv < 25: hrv_score = 20
        elif min_hrv < 40: hrv_score = 10

    min_sleep = recent['sleep_hours'].min()
    if pd.notnull(min_sleep):
        if min_sleep < 5: sleep_score = 15
        elif min_sleep < 6.5: sleep_score = 8

    # Dietary triggers logged in last 48h
    for diet_col in ['alfalfa_garlic', 'alcohol', 'processed_sugar', 'high_sodium']:
        if diet_col in recent.columns and recent[diet_col].max() == 1:
            diet_score += 5

    total_risk = float(uv_score + pressure_score + hrv_score + sleep_score + diet_score)
    return min(100.0, max(5.0, total_risk))