import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta

from database import (
    init_db, insert_daily_log, insert_wearable_data,
    insert_dietary_data, get_unified_dataset
)
from weather_service import fetch_daily_weather
from analytics import compute_lagged_correlations, calculate_48h_risk_index

# 1. Page Configuration
st.set_page_config(
    page_title="Lupus Flare Tracker & Early Warning Engine",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_db()

# 2. Modern Clinical Theme CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .metric-container {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 20px 24px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        margin-bottom: 16px;
    }
    .metric-label {
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748B;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 1.85rem;
        font-weight: 700;
        color: #0F172A;
    }
    .metric-sub {
        font-size: 0.8rem;
        color: #94A3B8;
        margin-top: 4px;
    }
    .badge-stable {
        display: inline-block;
        padding: 4px 12px;
        background-color: #ECFDF5;
        color: #047857;
        font-weight: 600;
        font-size: 0.82rem;
        border-radius: 9999px;
        border: 1px solid #A7F3D0;
    }
    .badge-alert {
        display: inline-block;
        padding: 4px 12px;
        background-color: #FEF2F2;
        color: #B91C1C;
        font-weight: 600;
        font-size: 0.82rem;
        border-radius: 9999px;
        border: 1px solid #FECACA;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 12px; }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        padding: 0 20px;
        border-radius: 8px;
        font-weight: 600;
        background-color: #F8FAFC;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0EA5E9 !important;
        color: #FFFFFF !important;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/caduceus.png", width=54)
    st.title("Patient Profile")
    patient_name = st.text_input("Full Name", value="Jane Doe")
    patient_dob = st.text_input("Date of Birth", value="1988-04-12")
    
    st.markdown("---")
    st.subheader("📍 Geolocation Sync")
    lat = st.number_input("Latitude", value=34.0522, format="%.4f")
    lon = st.number_input("Longitude", value=-118.2437, format="%.4f")
    
    st.markdown("---")
    st.subheader("⚙️ Development Tools")
    if st.button("Generate 60-Day Sample Data"):
        try:
            import seed_data
            seed_data.generate_mock_data(60)
            st.success("Loaded 60 days of sample data with diet logs!")
            st.rerun()
        except Exception as e:
            st.error(f"Seeding failed: {e}")

df = get_unified_dataset()

# Top Header Bar
top_c1, top_c2 = st.columns([3, 1])
with top_c1:
    st.title("Lupus Flare Early Warning & Analytics")
    st.caption("Passive multi-factor environmental, biometric & dietary correlation engine.")

with top_c2:
    if not df.empty:
        risk_score = calculate_48h_risk_index(df)
        if risk_score >= 50:
            st.markdown('<div style="text-align:right;"><span class="badge-alert">⚠️ Elevated Flare Risk (48h)</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="text-align:right;"><span class="badge-stable">✓ Stable Baseline Window</span></div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs([
    "📝 Daily Micro-Log",
    "📈 Predictive Analytics & Triggers",
    "📋 Clinical Briefing (Doctor PDF)"
])

# =========================================================
# TAB 1: DAILY MICRO-LOG (WITH OPTIONAL DIET FORM)
# =========================================================
with tab1:
    st.markdown("### Record Today's State")
    
    col_a, col_b = st.columns([1, 1], gap="large")
    with col_a:
        st.markdown("#### Patient Symptoms")
        log_date = st.date_input("Entry Date", value=date.today())
        pain_score = st.slider("Joint & Musculoskeletal Pain", 0, 10, 3)
        fatigue_score = st.slider("Fatigue / Energy Depletion", 0, 10, 4)
        flare_active = st.checkbox("🚩 Active Flare In Progress Today", value=False)
        notes = st.text_area("Symptom Notes", placeholder="E.g., High sun exposure, morning joint stiffness...")

    with col_b:
        st.markdown("#### Wearable Biometrics")
        hrv_rmssd = st.number_input("Resting HRV (rMSSD in ms)", value=42.0, step=1.0)
        resting_hr = st.number_input("Resting Heart Rate (BPM)", value=68, step=1)
        sleep_hours = st.number_input("Last Night's Sleep (Hours)", value=7.5, step=0.5)
        steps = st.number_input("Step Count Today", value=5400, step=250)

    # OPTIONAL DIETARY INTAKE EXPANDER
    with st.expander("🥗 Optional: Log Diet & Inflammatory Food Exposures", expanded=False):
        st.caption("Autoimmune flare triggers often stem from immune-stimulating foods or common intolerances.")
        d_c1, d_c2, d_c3 = st.columns(3)
        
        with d_c1:
            sugar = st.checkbox("Processed Sugars / Sweets")
            alcohol = st.checkbox("Alcohol Intake")
            high_sodium = st.checkbox("High Sodium / Fast Food")
        
        with d_c2:
            alfalfa_garlic = st.checkbox("Alfalfa Sprouts or Garlic", help="Contains L-canavanine or immune-boosting allicin known to stimulate lupus flares.")
            nightshades = st.checkbox("Nightshades (Tomatoes, Peppers, Eggplant)")
            gluten = st.checkbox("Gluten / Refined Wheat")

        with d_c3:
            dairy = st.checkbox("Dairy Intake")
            water_liters = st.number_input("Water Hydration (Liters)", value=2.0, step=0.5)
            diet_notes = st.text_input("Diet Notes", placeholder="E.g., Ate dinner out...")

    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
    if st.button("Save Daily Log & Auto-Fetch Weather", type="primary", use_container_width=True):
        insert_daily_log(log_date, pain_score, fatigue_score, flare_active, notes)
        insert_wearable_data(log_date, hrv_rmssd, resting_hr, sleep_hours, steps)
        insert_dietary_data(
            diet_date=log_date,
            gluten=gluten,
            dairy=dairy,
            sugar=sugar,
            alcohol=alcohol,
            nightshades=nightshades,
            alfalfa_garlic=alfalfa_garlic,
            sodium=high_sodium,
            water=water_liters,
            notes=diet_notes
        )
        
        success, msg = fetch_daily_weather(lat, lon, str(log_date))
        if success:
            st.success(f"✓ Daily log, diet, and weather saved! ({msg})")
        else:
            st.warning(f"Saved entry, but weather query returned: {msg}")
        st.rerun()

# =========================================================
# TAB 2: PREDICTIVE ANALYTICS & TRIGGERS
# =========================================================
with tab2:
    if df.empty or len(df) < 5:
        st.info("💡 You need at least 5 days of records to generate trigger correlations. Click 'Generate 60-Day Sample Data' in the left sidebar to preview.")
    else:
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        total_logs = len(df)
        flare_days = int(df['flare_active'].sum())
        mean_pain = round(df['pain_score'].mean(), 1)
        current_risk = calculate_48h_risk_index(df)
        
        with kpi1:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">Logged Entries</div>
                <div class="metric-value">{total_logs} Days</div>
                <div class="metric-sub">Continuous monitoring</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi2:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">Reported Flares</div>
                <div class="metric-value">{flare_days} Days</div>
                <div class="metric-sub">{(flare_days/total_logs*100):.1f}% flare prevalence</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi3:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">Average Pain</div>
                <div class="metric-value">{mean_pain} / 10</div>
                <div class="metric-sub">Baseline symptom level</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi4:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">48h Acute Risk</div>
                <div class="metric-value">{current_risk:.0f}%</div>
                <div class="metric-sub">Environmental, biometric & diet triggers</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        chart_col1, chart_col2 = st.columns([1, 1], gap="medium")
        with chart_col1:
            st.subheader("Multivariate Timeline Overlay")
            fig_ts = px.line(
                df, x='date', y=['pain_score', 'fatigue_score', 'max_uv'],
                labels={'value': 'Severity / UV Index', 'date': 'Date', 'variable': 'Marker'},
                color_discrete_map={'pain_score': '#EF4444', 'fatigue_score': '#F59E0B', 'max_uv': '#0EA5E9'}
            )
            fig_ts.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_ts, use_container_width=True)

        with chart_col2:
            st.subheader("Early Warning Flare Risk Gauge")
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=current_risk,
                number={'suffix': "%", 'font': {'color': "#0F172A", 'size': 36}},
                gauge={
                    'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#CBD5E1"},
                    'bar': {'color': "#2563EB", 'thickness': 0.3},
                    'steps': [
                        {'range': [0, 35], 'color': "#ECFDF5"},
                        {'range': [35, 65], 'color': "#FEF3C7"},
                        {'range': [65, 100], 'color': "#FEE2E2"}
                    ]
                }
            ))
            fig_gauge.update_layout(height=280, margin=dict(l=20, r=20, t=20, b=10))
            st.plotly_chart(fig_gauge, use_container_width=True)

        st.markdown("---")
        st.subheader("🔬 Time-Lagged Trigger Discovery (T-1 to T-3 Days)")
        corr_df = compute_lagged_correlations(df, target_metric='pain_score')
        
        if not corr_df.empty:
            hm_col, tbl_col = st.columns([1, 1], gap="medium")
            with hm_col:
                pivot_df = corr_df.pivot(index="Feature", columns="Lag_Days", values="Pearson_r")
                fig_hm = px.imshow(
                    pivot_df,
                    labels=dict(x="Lag Window", y="Candidate Trigger", color="Pearson r"),
                    x=['T-1 Day', 'T-2 Days', 'T-3 Days'],
                    color_continuous_scale="Blues",
                    text_auto=True,
                    aspect="auto"
                )
                fig_hm.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig_hm, use_container_width=True)

            with tbl_col:
                st.markdown("#### Top Correlated Latent Triggers")
                top_triggers = corr_df.sort_values(by="Pearson_r", ascending=False).head(5)
                top_display = top_triggers.copy()
                top_display['Lag Window'] = top_display['Lag_Days'].apply(lambda x: f"{x} day(s) prior")
                top_display['Correlation (r)'] = top_display['Pearson_r'].apply(lambda x: f"{x:+.2f}")
                st.dataframe(top_display[['Feature', 'Lag Window', 'Correlation (r)']], use_container_width=True, hide_index=True)

# =========================================================
# TAB 3: CLINICAL BRIEFING
# =========================================================
with tab3:
    st.markdown("""
        <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 12px 18px; border-radius: 8px; margin-bottom: 20px;">
            💡 <strong>Appointment View:</strong> Pre-formatted for rapid clinical review. Press <strong>Ctrl + P</strong> (or <strong>Cmd + P</strong>) to export directly as a 1-page PDF.
        </div>
    """, unsafe_allow_html=True)
    
    c_h1, c_h2 = st.columns([2, 1])
    with c_h1:
        st.markdown(f"## Clinical Lupus Disease Activity Brief")
        st.markdown(f"**Patient:** {patient_name} &nbsp;|&nbsp; **DOB:** {patient_dob}")
    with c_h2:
        st.markdown(f"**Report Date:** {date.today().strftime('%B %d, %Y')}")
        st.markdown("**Window:** Past 60-90 Days")

    st.markdown("---")

    if not df.empty:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Monitoring Period", f"{len(df)} Days")
        m2.metric("Flare Incidence", f"{int(df['flare_active'].sum())} Days", f"{(df['flare_active'].sum()/len(df)*100):.1f}%")
        m3.metric("Mean Pain VAS", f"{df['pain_score'].mean():.1f} / 10")
        m4.metric("Mean Baseline HRV", f"{df['hrv_rmssd'].mean():.1f} ms")

        st.markdown("### High-Confidence Multi-Factor Triggers (Weather, Lifestyle & Diet)")
        corr_df = compute_lagged_correlations(df, target_metric='pain_score')
        if not corr_df.empty:
            summary_triggers = corr_df.sort_values(by="Pearson_r", ascending=False).head(4)
            summary_triggers['Clinical Finding'] = summary_triggers.apply(
                lambda row: f"Pain spikes {row['Lag_Days']} day(s) following elevated {row['Feature']} (r = {row['Pearson_r']:+.2f})",
                axis=1
            )
            st.table(summary_triggers[['Clinical Finding']])
        else:
            st.write("Insufficient data to establish statistically significant latent triggers.")

        st.markdown("### Recent Logged Exposure History (Past 30 Entries)")
        recent = df.sort_values("date", ascending=False).head(30)
        st.dataframe(recent, use_container_width=True, hide_index=True)