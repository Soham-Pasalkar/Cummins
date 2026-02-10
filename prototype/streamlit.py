import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import date

# =========================================================
# Page Config
# =========================================================
st.set_page_config(page_title="SpecCheck", layout="wide")

# =========================================================
# Configurations
# =========================================================
SENSOR_CONFIG = {
    "Thermocouple": {"units": ["°C"], "range": (0, 1200), "tolerance": (-2, 2)},
    "RTD": {"units": ["°C"], "range": (-50, 600), "tolerance": (-0.1, 0.1)},
    "Pressure Sensor": {"units": ["bar", "Pa"], "range": (0, 300), "tolerance": (-2, 2)},
    "Flow Sensor": {"units": ["kg/s"], "range": (0, 50), "tolerance": (-5, 5)}
}

ENGINE_CONFIG = {
    "Single Cylinder Test Rig": {"max_temp_rate": 5, "max_pressure_rate": 10},
    "Multi Cylinder Engine": {"max_temp_rate": 10, "max_pressure_rate": 20},
    "Electric Motor Test Bench": {"max_temp_rate": 3, "max_pressure_rate": None}                                          
}

TRANSIENT_DURATION = 1800  # seconds

# =========================================================
# Title
# =========================================================
st.markdown("<h1 style='color:#1f77b4;'>SpecCheck</h1>", unsafe_allow_html=True)
st.caption("Instrumentation Data Validation & Baseline Comparison")

# =========================================================
# Sidebar: Context Window
# =========================================================
st.sidebar.header("Test Context")

engine_type = st.sidebar.selectbox("Engine Type", ENGINE_CONFIG.keys())
test_type = st.sidebar.selectbox("Type of Test", ["Steady", "Transient"])
sensor_type = st.sidebar.selectbox("Sensor Type", SENSOR_CONFIG.keys())

engine_config = ENGINE_CONFIG[engine_type]
sensor_config = SENSOR_CONFIG[sensor_type]
unit = st.sidebar.selectbox("Unit", sensor_config["units"])

calibration_date = st.sidebar.date_input(
    "Last Calibration Date", value=date.today()
)

# ---------- Conditional Transient Options ----------
transient_freq = None
if test_type == "Transient":
    transient_freq = st.sidebar.selectbox(
        "Transient Frequency",
        [1, 5, 10],
        format_func=lambda x: f"{x} Hz"
    )

# =========================================================
# Upload Section
# =========================================================
st.header("1. Upload Data")

col1, col2 = st.columns(2)
with col1:
    current_file = st.file_uploader("Upload CURRENT Data (CSV)", type=["csv"])
with col2:
    baseline_file = st.file_uploader("Upload BASELINE Data (CSV)", type=["csv"])

# =========================================================
# Processing
# =========================================================
if current_file and baseline_file:

    current = pd.read_csv(current_file)
    baseline = pd.read_csv(baseline_file)

    # ---------- Time Handling ----------
    if test_type == "Transient":
        if "value" not in current.columns or "value" not in baseline.columns:
            st.error("Transient test CSVs must contain a 'value' column.")
            st.stop()

        dt = 1 / transient_freq
        time_axis = np.arange(0, TRANSIENT_DURATION, dt)

        current = current.iloc[:len(time_axis)].copy()
        baseline = baseline.iloc[:len(time_axis)].copy()

        current["time"] = time_axis
        baseline["time"] = time_axis

    else:
        for df in [current, baseline]:
            if "time" not in df.columns or "value" not in df.columns:
                st.error("Normal test CSVs must contain 'time' and 'value'.")
                st.stop()

    st.subheader("Current Data Preview")
    st.dataframe(current.head(), use_container_width=True)
    st.subheader("Baseline Data Preview")
    st.dataframe(baseline.head(), use_container_width=True)

    st.markdown("---")
    st.subheader("2. Generate Results")

    if st.button("GET RESULTS", type="primary"):

        current["baseline_value"] = np.interp(
            current["time"], baseline["time"], baseline["value"]
        )

        tol_low, tol_high = sensor_config["tolerance"]
        min_r, max_r = sensor_config["range"]

        current["lower_limit"] = current["baseline_value"] + tol_low
        current["upper_limit"] = current["baseline_value"] + tol_high

        current["range_valid"] = current["value"].between(min_r, max_r)
        current["tolerance_valid"] = current["value"].between(
            current["lower_limit"], current["upper_limit"]
        )

        current["roc"] = current["value"].diff() / current["time"].diff()

        max_rate = None
        if sensor_type in ["Thermocouple", "RTD"]:
            max_rate = engine_config["max_temp_rate"]
        elif sensor_type == "Pressure Sensor":
            max_rate = engine_config["max_pressure_rate"]

        current["roc_valid"] = True if max_rate is None else current["roc"].abs() <= max_rate

        days_since_cal = (date.today() - calibration_date).days
        calibration_valid = days_since_cal <= 180

        def status(row):
            if not row["range_valid"] or not row["tolerance_valid"]:
                return "FAIL"
            if not row["roc_valid"]:
                return "WARNING"
            return "PASS"

        current["status"] = current.apply(status, axis=1)

        # =================================================
        # Verdict
        # =================================================
        if "FAIL" in current["status"].values:
            st.error("❌ VALIDATION FAILED")
        elif "WARNING" in current["status"].values:
            st.warning("⚠️ VALIDATION COMPLETED WITH WARNINGS")
        else:
            st.success("✅ VALIDATION PASSED")

        if not calibration_valid:
            st.warning(f"⚠️ Calibration expired ({days_since_cal} days old)")

        # =================================================
        # Visualization
        # =================================================
        st.header("3. Time-Series Comparison")

        fig, ax = plt.subplots(figsize=(11, 4))
        ax.plot(current["time"], current["value"], label="Current")
        ax.plot(current["time"], current["baseline_value"], "--", label="Baseline")
        ax.fill_between(
            current["time"],
            current["lower_limit"],
            current["upper_limit"],
            alpha=0.15,
            label="Tolerance Band"
        )

        ax.set_xlim(
            0,
            TRANSIENT_DURATION if test_type == "Transient" else current["time"].max()
        )
        ax.set_xlabel("Time (seconds)")
        ax.set_ylabel(f"Value ({unit})")
        ax.legend()

        st.pyplot(fig)

        # =================================================
        # Results Table
        # =================================================
        st.header("4. Validation Results")

        def highlight(row):
            if row["status"] == "FAIL":
                return ["background-color:#ffcccc"] * len(row)
            if row["status"] == "WARNING":
                return ["background-color:#fff2cc"] * len(row)
            return [""] * len(row)

        st.dataframe(
            current[["time", "value", "baseline_value", "status"]]
            .style.apply(highlight, axis=1),
            use_container_width=True
        )
