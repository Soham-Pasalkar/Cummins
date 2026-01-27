import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import date

# =========================================================
# Page Config (MUST be first Streamlit call)
# =========================================================
st.set_page_config(
    page_title="SpecCheck",
    layout="wide"
)

# =========================================================
# Sensor Configuration (Domain Truth)
# =========================================================
SENSOR_CONFIG = {
    "Thermocouple": {
        "units": ["°C"],
        "range": (0, 1200),
        "tolerance": (-2, 2),      # ± °C
        "needs_ambient": True
    },
    "RTD": {
        "units": ["°C"],
        "range": (-50, 600),
        "tolerance": (-0.5, 0.5),  # ± °C
        "needs_ambient": True
    },
    "Pressure Sensor": {
        "units": ["bar", "Pa"],
        "range": (0, 300),
        "tolerance": (-2, 2),      # ± %
        "needs_ambient": False
    },
    "Flow Sensor": {
        "units": ["kg/s"],
        "range": (0, 50),
        "tolerance": (-5, 5),      # ± %
        "needs_ambient": False
    }
}

# =========================================================
# Title
# =========================================================
st.title("SpecCheck")
st.caption("Instrumentation Data Validation & Analysis")

# =========================================================
# Sidebar: Context
# =========================================================
st.sidebar.header("Test Context")

sensor_type = st.sidebar.selectbox(
    "Sensor Type",
    list(SENSOR_CONFIG.keys())
)

sensor_config = SENSOR_CONFIG[sensor_type]

unit = st.sidebar.selectbox(
    "Unit",
    sensor_config["units"]
)

calibration_date = st.sidebar.date_input(
    "Last Calibration Date",
    value=date.today()
)

test_condition = st.sidebar.selectbox(
    "Test Condition",
    ["Steady State", "Transient", "Startup"]
)

ambient_temp = None
if sensor_config["needs_ambient"]:
    ambient_temp = st.sidebar.number_input(
        "Ambient Temperature (°C)",
        value=25.0
    )

# =========================================================
# Main: Data Upload
# =========================================================
st.header("1. Upload Measurement Data")

uploaded_file = st.file_uploader(
    "Upload CSV file (must contain 'time' and 'value' columns)",
    type=["csv"]
)

if uploaded_file is not None:
    data = pd.read_csv(uploaded_file)

    st.subheader("Raw Data Preview")
    st.dataframe(data.head())

    # -----------------------------------------------------
    # Sanity Checks
    # -----------------------------------------------------
    if "time" not in data.columns or "value" not in data.columns:
        st.error("CSV must contain 'time' and 'value' columns.")
        st.stop()

    data = data.dropna(subset=["time", "value"])

    # =====================================================
    # Validation
    # =====================================================
    st.header("2. Run Validation")

    if st.button("Validate Data"):
        min_limit, max_limit = sensor_config["range"]
        tol_low, tol_high = sensor_config["tolerance"]

        # Expected value (simple baseline)
        expected_value = data["value"].mean()

        tolerance_low = expected_value + tol_low
        tolerance_high = expected_value + tol_high

        # ---------------- Range Check ----------------
        data["range_valid"] = data["value"].between(
            min_limit,
            max_limit
        )

        # ---------------- Tolerance Check ----------------
        data["tolerance_valid"] = data["value"].between(
            tolerance_low,
            tolerance_high
        )

        # ---------------- Final Status ----------------
        data["status"] = np.where(
            data["range_valid"] & data["tolerance_valid"],
            "PASS",
            "FAIL"
        )

        # ---------------- Verdict ----------------
        if data["status"].eq("FAIL").any():
            st.error("❌ Validation Failed")
        else:
            st.success("✅ Validation Passed")

        # ---------------- Active Rules ----------------
        st.info(
            f"""
            **Active Validation Rules**
            - Sensor Type: {sensor_type}
            - Valid Range: {min_limit} to {max_limit} {unit}
            - Tolerance Band: {tolerance_low:.2f} to {tolerance_high:.2f} {unit}
            """
        )

        # =================================================
        # Visualization
        # =================================================
        st.header("3. Visualization")

        fig, ax = plt.subplots(figsize=(10, 4))

        ax.plot(
            data["time"],
            data["value"],
            label="Measured Value",
            linewidth=1.5
        )

        ax.axhline(min_limit, color="red", linestyle="--", alpha=0.6)
        ax.axhline(max_limit, color="red", linestyle="--", alpha=0.6)

        ax.axhspan(
            tolerance_low,
            tolerance_high,
            color="green",
            alpha=0.2,
            label="Tolerance Band"
        )

        ax.set_xlabel("Time")
        ax.set_ylabel(f"Value ({unit})")
        ax.legend()

        st.pyplot(fig)

        # =================================================
        # Detailed Results
        # =================================================
        st.header("4. Validation Details")

        st.dataframe(
            data[["time", "value", "status"]],
            use_container_width=True
        )

        failed_points = data[data["status"] == "FAIL"]

        if not failed_points.empty:
            st.warning("Failed Data Points")
            st.dataframe(
                failed_points,
                use_container_width=True
            )
