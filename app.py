import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta

from database import (
    init_db, insert_daily_log, insert_wearable_data,
    get_unified_dataset
)
from weather_service import fetch_daily_weather
from analytics import compute_lagged_correlations, calculate_48h_risk_index

# Initialize Page Configuration
st.set_page_config(
    page_title="Lupus Flare Tracker & Early Warning Engine",
    page_icon="🩺",
    layout="wide"
)

# Initialize Database
init_db()

# Custom CSS for Printable Clinical Brief
st.markdown("""
<style>
@media print {
    .stApp > header, .stSidebar, .stButton, .no-print { display: none !important; }
    .main .block-container { padding: 0 !important; margin: 0 !important; }
}
.metric-card {
    background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR CONFIGURATION
st.sidebar.title("Patient Profile")
patient_name = st.sidebar.text_input("Patient Name", value="Jane Doe")
patient_dob = st.sidebar.text_input("DOB", value="1988-04-12")

st.sidebar.markdown("---")
st.sidebar.title("Location & Weather Sync")
lat = st.sidebar.number_input("Latitude", value=34.0522, format="%.4f")
lon = st.sidebar.number_input("Longitude", value=-118.2437, format="%.4f")

# Data Loader
df = get_unified_dataset()

# Application Tabs
tab1, tab2, tab3 = st.tabs([
    "📝 Quick 5-Sec Log",
    "📈 Analytics & Triggers",
    "📋 Clinical Briefing"
])

# ==========================================
# TAB 1: QUICK DAILY LOG
# ==========================================
with tab1:
    st.subheader("Daily Symptom & Biometric Entry")
    col_a, col_b = st.columns([1, 1])
    
    with col_a:
        log_date = st.date_input("Entry Date", value=date.today())
        pain_score = st.slider("Joint / Muscle Pain (0-10)", 0, 10, 3)
        fatigue_score = st.slider("Fatigue Severity (0-10)", 0, 10, 4)
        flare_active = st.checkbox("Active Lupus Flare Day", value=False)
        notes = st.text_area("Symptom Notes / Triggers", placeholder="E.g., High sun exposure at beach...")

    with col_b:
        st.markdown("#### Biometric Wearable Sync (Optional)")
        hrv_rmssd = st.number_input("HRV rMSSD (ms)", value=42.0, step=1.0)
        resting_hr = st.number_input("Resting Heart Rate (bpm)", value=68, step=1)
        sleep_hours = st.number_input("Sleep Duration (Hours)", value=7.5, step=0.5)
        steps = st.number_input("Daily Step Count", value=5400, step=100)

    st.markdown("---")
    if st.button("Save Daily Log & Auto-Fetch Weather", type="primary"):
        insert_daily_log(log_date, pain_score, fatigue_score, flare_active, notes)
        insert_wearable_data(log_date, hrv_rmssd, resting_hr, sleep_hours, steps)
        
        success, msg = fetch_daily_weather(lat, lon, str(log_date))
        if success:
            st.success(f"Log saved and weather synced! ({msg})")
        else:
            st.warning(f"Log saved, but weather sync issue: {msg}")
        st.rerun()

# ==========================================
# TAB 2: PREDICTIVE ANALYTICS
# ==========================================
with tab2:
    st.title("Predictive Analytics & Trigger Discovery")
    
    if df.empty or len(df) < 3:
        st.info("Insufficient data for predictive analytics. Log at least 3-5 days of symptoms.")
    else:
        risk_index = calculate_48h_risk_index(df)
        
        col_risk, col_chart = st.columns([1, 2])
        with col_risk:
            st.markdown("### 48-Hour Flare Vulnerability")
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=risk_index,
                number={'suffix': "%"},
                gauge={
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "#0F172A"},
                    'steps': [
                        {'range': [0, 30], 'color': "#CBD5E1"},
                        {'range': [30, 60], 'color': "#94A3B8"},
                        {'range': [60, 100], 'color': "#475569"}
                    ]
                }
            ))
            fig_gauge.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_gauge, use_container_width=True)
            st.caption("Score based on recent UV intensity, barometric pressure deltas, HRV, and sleep length.")

        with col_chart:
            st.markdown("### Time Series Overlay")
            fig_ts = px.line(
                df, x='date', y=['pain_score', 'fatigue_score', 'max_uv'],
                labels={'value': 'Level / Score', 'date': 'Date'},
                color_discrete_map={'pain_score': '#1E293B', 'fatigue_score': '#64748B', 'max_uv': '#CBD5E1'}
            )
            fig_ts.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10), legend_title_text='')
            st.plotly_chart(fig_ts, use_container_width=True)

        st.markdown("---")
        st.subheader("Time-Lagged Cross-Correlation Matrix (T-1 to T-3 Days)")
        corr_df = compute_lagged_correlations(df, target_metric='pain_score')
        
        if not corr_df.empty:
            pivot_df = corr_df.pivot(index="Feature", columns="Lag_Days", values="Pearson_r")
            fig_heatmap = px.imshow(
                pivot_df,
                labels=dict(x="Lag Offset (Days Prior)", y="Environmental / Biometric Trigger", color="Pearson r"),
                x=['T-1 Day', 'T-2 Days', 'T-3 Days'],
                color_continuous_scale="Blues",
                text_auto=True
            )
            fig_heatmap.update_layout(height=300)
            st.plotly_chart(fig_heatmap, use_container_width=True)

            st.markdown("#### High-Confidence Identified Triggers")
            significant = corr_df[corr_df['Pearson_p'] < 0.25].sort_values(by="Pearson_r", ascending=False)
            if not significant.empty:
                st.dataframe(significant[['Feature', 'Lag_Days', 'Pearson_r', 'Pearson_p']], use_container_width=True)
            else:
                st.caption("No strong statistical triggers isolated yet. Continue logging daily.")
        else:
            st.caption("Need more data points to compute time-lagged cross-correlations.")

# ==========================================
# TAB 3: DOCTOR'S CLINICAL BRIEF
# ==========================================
with tab3:
    st.markdown("<div class='no-print'>", unsafe_allow_html=True)
    st.info("💡 Print or export this tab to PDF for your clinical appointment.")
    st.markdown("</div>", unsafe_allow_html=True)

    # Brief Header
    col_hdr1, col_hdr2 = st.columns([2, 1])
    with col_hdr1:
        st.title("Lupus Clinical Summary Brief")
        st.markdown(f"**Patient:** {patient_name} &nbsp;&nbsp;&nbsp;&nbsp; **DOB:** {patient_dob}")
    with col_hdr2:
        st.markdown(f"**Report Date:** {date.today().strftime('%Y-%m-%d')}")
        st.markdown("**Reporting Period:** Past 90 Days")

    st.markdown("---")

    # Key Metrics
    c1, c2, c3, c4 = st.columns(4)
    total_days = len(df)
    flare_days = df['flare_active'].sum() if not df.empty else 0
    avg_pain = round(df['pain_score'].mean(), 1) if not df.empty else 0.0
    avg_hrv = round(df['hrv_rmssd'].mean(), 1) if not df.empty else 0.0

    c1.metric("Logged Days", total_days)
    c2.metric("Flare Days Count", flare_days)
    c3.metric("Mean Pain Score", f"{avg_pain} / 10")
    c4.metric("Baseline HRV", f"{avg_hrv} ms")

    st.markdown("### Identified High-Confidence Triggers")
    corr_df = compute_lagged_correlations(df, target_metric='pain_score') if not df.empty else pd.DataFrame()
    if not corr_df.empty:
        top_triggers = corr_df.sort_values(by="Pearson_r", ascending=False).head(3)
        st.table(top_triggers[['Feature', 'Lag_Days', 'Pearson_r', 'Spearman_r']])
    else:
        st.write("Insufficient historical data to verify statistically significant environmental triggers.")

    st.markdown("### Recent 30-Day Symptom & Exposure History")
    if not df.empty:
        recent_30 = df.sort_values("date", ascending=False).head(30)
        st.dataframe(
            recent_30[['date', 'pain_score', 'fatigue_score', 'flare_active', 'max_uv', 'pressure_delta', 'hrv_rmssd', 'sleep_hours']],
            use_container_width=True
        )

    st.markdown("---")
    st.markdown("**Physician Sign-off:** _______________________ &nbsp;&nbsp;&nbsp;&nbsp; **Date:** ____________")