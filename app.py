from datetime import date
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analytics import (
    FEATURE_LABELS,
    calculate_48h_risk_breakdown,
    compute_lagged_correlations,
)
from database import (
    clear_all_logs,
    get_unified_dataset,
    init_db,
    insert_daily_log,
    insert_dietary_data,
    insert_wearable_data,
)
from seed_data import generate_mock_data
from weather_service import fetch_daily_weather, geocode_city

st.set_page_config(
    page_title="Lupus Flare Tracker & Early Warning Engine",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

# Unified Low-Contrast Muted Purple & White Clinical Theme + Print Rules
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp { background-color: #FAF8FC; color: #231A30; }

    .metric-container {
        background: #FFFFFF;
        border: 1px solid #DDD5E7;
        border-radius: 10px;
        padding: 18px 22px;
        box-shadow: 0 2px 10px -2px rgba(56, 43, 75, 0.06);
        margin-bottom: 14px;
    }
    .metric-label {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #5C4879;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: #231A30;
    }
    .metric-sub {
        font-size: 0.78rem;
        color: #725C93;
        margin-top: 4px;
    }
    .badge-stable {
        display: inline-block;
        padding: 5px 14px;
        background-color: #ECFDF5;
        color: #065F46;
        font-weight: 600;
        font-size: 0.82rem;
        border-radius: 9999px;
        border: 1px solid #A7F3D0;
    }
    .badge-alert {
        display: inline-block;
        padding: 5px 14px;
        background-color: #FEF2F2;
        color: #991B1B;
        font-weight: 600;
        font-size: 0.82rem;
        border-radius: 9999px;
        border: 1px solid #FECACA;
    }
    .disclaimer-box {
        background-color: #F4F0F8;
        border: 1px solid #C8BCD8;
        border-radius: 8px;
        padding: 12px 16px;
        font-size: 0.8rem;
        color: #382B4B;
        margin-top: 12px;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 44px;
        padding: 0 18px;
        border-radius: 8px;
        font-weight: 600;
        background-color: #FFFFFF;
        border: 1px solid #DDD5E7;
        color: #4A3962;
    }
    .stTabs [aria-selected="true"] {
        background-color: #5C4879 !important;
        color: #FFFFFF !important;
        border-color: #5C4879 !important;
    }
    @media print {
        [data-testid="stSidebar"], header, footer, .no-print { display: none !important; }
        .stApp { background: #FFFFFF !important; }
    }
</style>
""",
    unsafe_allow_html=True,
)

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.markdown("### Patient Profile")
    patient_name = st.text_input("Display Name", value="Sample Patient")
    patient_dob = st.date_input("Date of Birth", value=date(1990, 1, 15))

    st.markdown("---")
    st.markdown("### Location & Weather Sync")
    city_input = st.text_input("City, State", value="Bowie, Maryland")
    resolved_lat, resolved_lon, resolved_label = geocode_city(city_input)
    st.caption(f"Resolved: {resolved_label} ({resolved_lat:.4f}, {resolved_lon:.4f})")

    st.markdown("---")
    st.markdown("### Data Management")
    if st.button("Generate 60-Day Sample Data", use_container_width=True):
        try:
            generate_mock_data(days=60, overwrite=True)
            st.success("Loaded 60 days of synthetic sample records.")
            st.rerun()
        except Exception as exc:
            st.error(f"Seeding failed: {exc}")

    df_sidebar = get_unified_dataset()
    if not df_sidebar.empty:
        csv_bytes = df_sidebar.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Export Logs (CSV)",
            data=csv_bytes,
            file_name=f"lupus_flare_logs_{date.today().isoformat()}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    confirm_reset = st.checkbox("Confirm database reset", value=False)
    if st.button("Reset All Logs", disabled=not confirm_reset, use_container_width=True):
        clear_all_logs()
        st.warning("All stored logs have been cleared.")
        st.rerun()

    st.markdown(
        """
        <div class="disclaimer-box">
            <strong>Clinical Notice:</strong> Investigational decision-support tool only. Does not provide medical diagnoses or treatment advice.
        </div>
        """,
        unsafe_allow_html=True,
    )

df = get_unified_dataset()

# Top Header Bar
top_c1, top_c2 = st.columns([3, 1])
with top_c1:
    st.title("Lupus Flare Tracker & Early Warning Engine")
    st.caption("Multi-factor environmental, biometric, physical strain & dietary correlation platform.")

with top_c2:
    if not df.empty:
        risk_score, _ = calculate_48h_risk_breakdown(df)
        if risk_score >= 50:
            st.markdown(
                f'<div style="text-align:right; padding-top:14px;"><span class="badge-alert">Elevated 48h Risk ({risk_score:.0f}%)</span></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="text-align:right; padding-top:14px;"><span class="badge-stable">Stable Baseline Window ({risk_score:.0f}%)</span></div>',
                unsafe_allow_html=True,
            )

tab1, tab2, tab3 = st.tabs(
    [
        "Daily Micro-Log",
        "Predictive Analytics & Triggers",
        "Clinical Briefing (Doctor PDF)",
    ]
)

# =========================================================
# TAB 1: DAILY MICRO-LOG
# =========================================================
with tab1:
    st.markdown("### Record Today's State")

    col_a, col_b = st.columns([1, 1], gap="large")
    with col_a:
        st.markdown("#### Patient Symptoms")
        log_date = st.date_input("Entry Date", value=date.today())
        pain_score = st.slider("Joint & Musculoskeletal Pain", 0, 10, 3)
        fatigue_score = st.slider("Fatigue / Energy Depletion", 0, 10, 4)
        flare_active = st.checkbox("Active Flare In Progress Today", value=False)
        notes = st.text_area("Symptom Notes", placeholder="E.g., High midday sun exposure, morning stiffness...")

    with col_b:
        st.markdown("#### Wearable Biometrics & Strain")
        hrv_rmssd = st.number_input("Resting HRV (rMSSD in ms)", min_value=5.0, max_value=250.0, value=42.0, step=1.0)
        resting_hr = st.number_input("Resting Heart Rate (BPM)", min_value=30, max_value=200, value=68, step=1)
        sleep_hours = st.number_input("Last Night's Sleep (Hours)", min_value=0.0, max_value=24.0, value=7.5, step=0.5)
        steps = st.number_input("Step Count Today", min_value=0, max_value=100000, value=5400, step=250)
        strenuous_activity = st.checkbox("Physical Overexertion / High-Impact Strain Today", value=False)

    with st.expander("Optional: Log Diet & Inflammatory Food Exposures", expanded=False):
        st.caption("Track immune-stimulating foods or common flare sensitivities.")
        d_c1, d_c2, d_c3 = st.columns(3)

        with d_c1:
            sugar = st.checkbox("Processed Sugars / Sweets")
            alcohol = st.checkbox("Alcohol Intake")
            high_sodium = st.checkbox("High Sodium / Fast Food")

        with d_c2:
            alfalfa_garlic = st.checkbox(
                "Alfalfa Sprouts or Garlic",
                help="Contains L-canavanine or immune-stimulating compounds associated with lupus flares.",
            )
            nightshades = st.checkbox("Nightshades (Tomatoes, Peppers, Eggplant)")
            gluten = st.checkbox("Gluten / Refined Wheat")

        with d_c3:
            dairy = st.checkbox("Dairy Intake")
            water_liters = st.number_input("Water Hydration (Liters)", min_value=0.0, max_value=15.0, value=2.0, step=0.5)
            diet_notes = st.text_input("Diet Notes", placeholder="E.g., Ate dinner out...")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
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
            notes=diet_notes,
            strenuous_activity=strenuous_activity,
        )

        success, msg = fetch_daily_weather(resolved_lat, resolved_lon, log_date.isoformat())
        if success:
            st.success(f"Daily log, strain/diet, and weather saved ({msg}).")
        else:
            st.warning(f"Saved entry, but weather sync returned: {msg}")
        st.rerun()

# =========================================================
# TAB 2: PREDICTIVE ANALYTICS & TRIGGERS
# =========================================================
with tab2:
    if df.empty or len(df) < 5:
        logged_count = len(df)
        st.info(
            f"Logged {logged_count} of 5 minimum days required to compute time-lagged trigger correlations. "
            "Use 'Generate 60-Day Sample Data' in the sidebar to preview full analytics."
        )
    else:
        date_window = st.selectbox(
            "Analysis Window",
            options=["All Logged Days", "Last 60 Days", "Last 30 Days", "Last 14 Days"],
            index=0,
        )
        df_view = df.copy()
        if date_window == "Last 60 Days":
            df_view = df_view.tail(60)
        elif date_window == "Last 30 Days":
            df_view = df_view.tail(30)
        elif date_window == "Last 14 Days":
            df_view = df_view.tail(14)

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        total_logs = len(df_view)
        flare_days = int(df_view["flare_active"].sum())
        mean_pain = round(float(df_view["pain_score"].mean()), 1)
        current_risk, risk_drivers = calculate_48h_risk_breakdown(df_view)

        with kpi1:
            st.markdown(
                f"""
            <div class="metric-container">
                <div class="metric-label">Logged Entries</div>
                <div class="metric-value">{total_logs} Days</div>
                <div class="metric-sub">Selected review window</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        with kpi2:
            st.markdown(
                f"""
            <div class="metric-container">
                <div class="metric-label">Reported Flares</div>
                <div class="metric-value">{flare_days} Days</div>
                <div class="metric-sub">{(flare_days / total_logs * 100):.1f}% flare prevalence</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        with kpi3:
            st.markdown(
                f"""
            <div class="metric-container">
                <div class="metric-label">Average Pain</div>
                <div class="metric-value">{mean_pain} / 10</div>
                <div class="metric-sub">Baseline symptom level</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        with kpi4:
            st.markdown(
                f"""
            <div class="metric-container">
                <div class="metric-label">48h Acute Risk</div>
                <div class="metric-value">{current_risk:.0f}%</div>
                <div class="metric-sub">{risk_drivers[0]}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        st.markdown("---")

        chart_col1, chart_col2 = st.columns([1, 1], gap="medium")
        with chart_col1:
            st.subheader("Multivariate Timeline Overlay")
            plot_df = df_view.rename(
                columns={
                    "pain_score": "Pain VAS",
                    "fatigue_score": "Fatigue",
                    "max_uv": "Max UV",
                }
            )
            fig_ts = px.line(
                plot_df,
                x="date",
                y=["Pain VAS", "Fatigue", "Max UV"],
                labels={"value": "Severity / UV Index", "date": "Date", "variable": "Metric"},
                color_discrete_map={
                    "Pain VAS": "#5C4879",
                    "Fatigue": "#AA98C2",
                    "Max UV": "#725C93",
                },
            )
            fig_ts.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                height=320,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_ts, use_container_width=True)

        with chart_col2:
            st.subheader("Early Warning Flare Risk Gauge")
            fig_gauge = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=current_risk,
                    number={"suffix": "%", "font": {"color": "#231A30", "size": 36}},
                    gauge={
                        "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#C8BCD8"},
                        "bar": {"color": "#5C4879", "thickness": 0.3},
                        "steps": [
                            {"range": [0, 35], "color": "#ECFDF5"},
                            {"range": [35, 65], "color": "#FEF3C7"},
                            {"range": [65, 100], "color": "#FEE2E2"},
                        ],
                    },
                )
            )
            fig_gauge.update_layout(
                height=260,
                margin=dict(l=20, r=20, t=20, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_gauge, use_container_width=True)
            st.caption("Active 48h Drivers: " + " | ".join(risk_drivers))

        st.markdown("---")
        st.subheader("Time-Lagged Trigger Discovery (T-1 to T-3 Days)")
        corr_df = compute_lagged_correlations(df_view, target_metric="pain_score")

        if not corr_df.empty:
            hm_col, tbl_col = st.columns([1, 1], gap="medium")
            with hm_col:
                pivot_df = corr_df.pivot(index="Feature_Label", columns="Lag_Days", values="Pearson_r")
                pivot_df = pivot_df.reindex(columns=[1, 2, 3])
                pivot_df.columns = ["T-1 Day", "T-2 Days", "T-3 Days"]

                fig_hm = px.imshow(
                    pivot_df,
                    labels=dict(x="Lag Window", y="Candidate Trigger", color="Pearson r"),
                    color_continuous_scale=["#FAF8FC", "#C8BCD8", "#4A3962"],
                    text_auto=".2f",
                    aspect="auto",
                )
                fig_hm.update_layout(
                    height=340,
                    margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig_hm, use_container_width=True)

            with tbl_col:
                st.markdown("#### Top Correlated Latent Triggers")
                top_triggers = corr_df.sort_values(by="Pearson_r", ascending=False).head(6).copy()
                top_triggers["Lag Window"] = top_triggers["Lag_Days"].apply(lambda x: f"{x} day(s) prior")
                top_triggers["Pearson (r)"] = top_triggers["Pearson_r"].apply(lambda x: f"{x:+.2f}")
                top_triggers["Spearman (ρ)"] = top_triggers["Spearman_r"].apply(lambda x: f"{x:+.2f}")
                top_triggers["p-value"] = top_triggers["Pearson_p"].apply(lambda x: f"{x:.4f}")
                st.dataframe(
                    top_triggers[["Feature_Label", "Lag Window", "Pearson (r)", "Spearman (ρ)", "p-value"]].rename(
                        columns={"Feature_Label": "Candidate Trigger"}
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
                st.caption("Exploratory correlation metrics; association does not establish clinical causation.")
        else:
            st.info("Not enough feature variance in the selected window to calculate lagged correlations.")

# =========================================================
# TAB 3: CLINICAL BRIEFING
# =========================================================
with tab3:
    st.markdown(
        """
        <div class="no-print" style="background-color: #F4F0F8; border: 1px solid #C8BCD8; padding: 12px 18px; border-radius: 8px; margin-bottom: 20px;">
            <strong>Appointment Export View:</strong> Pre-formatted for clinical review. Press <strong>Ctrl + P</strong> (or <strong>Cmd + P</strong>) to save as a PDF.
        </div>
    """,
        unsafe_allow_html=True,
    )

    c_h1, c_h2 = st.columns([2, 1])
    with c_h1:
        st.markdown("## Clinical Lupus Disease Activity Brief")
        st.markdown(f"**Patient:** {patient_name} &nbsp;|&nbsp; **DOB:** {patient_dob.isoformat()}")
    with c_h2:
        st.markdown(f"**Report Date:** {date.today().strftime('%B %d, %Y')}")
        st.markdown(f"**Location:** {resolved_label}")

    st.markdown("---")

    if not df.empty:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Monitoring Period", f"{len(df)} Days")
        m2.metric("Flare Incidence", f"{int(df['flare_active'].sum())} Days", f"{(df['flare_active'].sum() / len(df) * 100):.1f}%")
        m3.metric("Mean Pain VAS", f"{df['pain_score'].mean():.1f} / 10")
        mean_hrv = df["hrv_rmssd"].dropna().mean()
        m4.metric("Mean Baseline HRV", f"{mean_hrv:.1f} ms" if pd.notnull(mean_hrv) else "N/A")

        st.markdown("### High-Confidence Multi-Factor Triggers (Weather, Strain & Diet)")
        corr_df = compute_lagged_correlations(df, target_metric="pain_score")
        if not corr_df.empty:
            summary_triggers = corr_df.sort_values(by="Pearson_r", ascending=False).head(4).copy()
            summary_triggers["Clinical Finding"] = summary_triggers.apply(
                lambda row: (
                    f"Pain elevates {row['Lag_Days']} day(s) after higher {FEATURE_LABELS.get(row['Feature'], row['Feature'])} "
                    f"(r = {row['Pearson_r']:+.2f}, p = {row['Pearson_p']:.4f}, n = {row['Sample_Size']})"
                ),
                axis=1,
            )
            st.table(summary_triggers[["Clinical Finding"]])
        else:
            st.write("Insufficient data to establish statistically significant latent triggers.")

        st.markdown("### Recent Logged Exposure History (Past 14 Entries)")
        recent = df.sort_values("date", ascending=False).head(14).copy()
        recent["Date"] = recent["date"].dt.strftime("%Y-%m-%d")
        recent["Flare"] = recent["flare_active"].map({1: "Yes", 0: "No"})
        recent["Strain"] = recent["strenuous_activity"].fillna(0).astype(int).map({1: "High/Overexerted", 0: "Normal"})

        display_cols = {
            "Date": "Date",
            "pain_score": "Pain (0-10)",
            "fatigue_score": "Fatigue (0-10)",
            "Flare": "Flare",
            "max_uv": "Max UV",
            "pressure_delta": "Δ Pressure (hPa)",
            "hrv_rmssd": "HRV (ms)",
            "sleep_hours": "Sleep (hrs)",
            "Strain": "Physical Strain",
            "notes": "Notes",
        }
        available = [c for c in display_cols if c in recent.columns]
        st.dataframe(
            recent[available].rename(columns=display_cols),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No records available yet. Log an entry or load sample data from the sidebar.")