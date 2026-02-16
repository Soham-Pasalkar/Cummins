import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from dataclasses import dataclass
from datetime import datetime
import json
from typing import Optional, List, Dict
import io

# ==========================================================
# PAGE CONFIG
# ==========================================================
st.set_page_config(
    page_title="PUMA Analytics Pro | Cummins",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon=""
)

# ==========================================================
# CUSTOM CSS - CUMMINS THEMED
# ==========================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
    
    * {
        font-family: 'Outfit', sans-serif;
    }
    
    .main {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
    }
    
    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
    }
    
    h1, h2, h3 {
        font-weight: 700;
        letter-spacing: -0.02em;
        background: linear-gradient(135deg, #ffd700 0%, #ff6b35 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 215, 0, 0.2);
        border-radius: 12px;
        padding: 20px;
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        border-color: rgba(255, 215, 0, 0.5);
        box-shadow: 0 8px 32px rgba(255, 215, 0, 0.15);
        transform: translateY(-2px);
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #ffd700 0%, #ff6b35 100%);
        color: #0a0e27;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        box-shadow: 0 8px 24px rgba(255, 215, 0, 0.4);
        transform: translateY(-2px);
    }
    
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .info-panel {
        background: rgba(255, 255, 255, 0.03);
        border-left: 4px solid #ffd700;
        padding: 16px;
        border-radius: 8px;
        margin: 16px 0;
    }
    
    code {
        font-family: 'JetBrains Mono', monospace;
        background: rgba(255, 215, 0, 0.1);
        padding: 2px 6px;
        border-radius: 4px;
        color: #ffd700;
    }
    
    .test-type-chip {
        display: inline-block;
        padding: 6px 14px;
        background: rgba(255, 107, 53, 0.2);
        border: 1px solid #ff6b35;
        border-radius: 16px;
        font-size: 11px;
        font-weight: 600;
        margin: 4px;
    }
    
    .tooltip {
        position: relative;
        display: inline-block;
        cursor: help;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# SESSION STATE INIT
# ==========================================================
defaults = {
    "validated": False,
    "summary_df": None,
    "df": None,
    "baseline_df": None,
    "validator": None,
    "test_metadata": {},
    "selected_sensors": [],
    "violation_details": None,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ==========================================================
# DATA MODELS
# ==========================================================

@dataclass
class ParameterResult:
    name: str
    unit: str
    status: str
    violations: int
    violation_percent: float
    mean: float
    max: float
    min: float
    std: float
    baseline_delta: Optional[float]
    missing_percent: float
    category: str = "general"
    first_violation_time: Optional[float] = None
    max_violation_duration: Optional[float] = None


@dataclass
class TestMetadata:
    test_type: str
    frequency: Optional[str]
    duration: float
    total_sensors: int
    timestamp: str
    total_datapoints: int


# ==========================================================
# VALIDATION ENGINE (OPTIMIZED)
# ==========================================================

class RuleEngine:
    """Advanced rule engine with statistical methods"""
    
    @staticmethod
    def threshold(values, min_val=None, max_val=None):
        violations = np.zeros(len(values), dtype=bool)
        if min_val is not None and not pd.isna(min_val):
            violations |= values < min_val
        if max_val is not None and not pd.isna(max_val):
            violations |= values > max_val
        return violations

    @staticmethod
    def roc(values, roc_limit=None):
        """Rate of Change validation"""
        if roc_limit is None or pd.isna(roc_limit):
            return np.zeros(len(values), dtype=bool)
        roc = np.abs(np.diff(values, prepend=values[0]))
        return roc > roc_limit

    @staticmethod
    def duration_filter(violations, time_array, min_duration=0):
        """Filter violations based on minimum duration"""
        if min_duration == 0 or pd.isna(min_duration):
            return violations

        filtered = np.zeros(len(violations), dtype=bool)
        start = None

        for i, flag in enumerate(violations):
            if flag and start is None:
                start = i
            elif not flag and start is not None:
                duration = time_array[i - 1] - time_array[start]
                if duration >= min_duration:
                    filtered[start:i] = True
                start = None

        # Handle violation that extends to end
        if start is not None:
            duration = time_array[-1] - time_array[start]
            if duration >= min_duration:
                filtered[start:] = True

        return filtered
    
    @staticmethod
    def get_violation_details(violations, time_array):
        """Extract detailed violation information"""
        if not np.any(violations):
            return None, None
        
        # Find first violation
        first_idx = np.where(violations)[0][0]
        first_time = time_array[first_idx]
        
        # Find longest continuous violation
        max_duration = 0
        current_duration = 0
        start_idx = None
        
        for i, v in enumerate(violations):
            if v:
                if start_idx is None:
                    start_idx = i
                current_duration = time_array[i] - time_array[start_idx]
            else:
                if current_duration > max_duration:
                    max_duration = current_duration
                start_idx = None
                current_duration = 0
        
        # Check last segment
        if start_idx is not None:
            current_duration = time_array[-1] - time_array[start_idx]
            if current_duration > max_duration:
                max_duration = current_duration
        
        return first_time, max_duration


class SpecValidator:
    """Production-grade validator optimized for PUMA data"""

    def __init__(self, df, config_df, baseline_df=None):
        self.df = df
        self.config = config_df
        self.baseline = baseline_df
        self.time_col = self._detect_time()
        
    def validate(self, progress_callback=None):
        """Run validation with optional progress tracking"""
        time_array = self.df[self.time_col].to_numpy()
        results = []
        total_params = len(self.config)

        for idx, row in self.config.iterrows():
            if progress_callback:
                progress_callback((idx + 1) / total_params)

            param = row.get("Parameter")
            if param not in self.df.columns:
                continue

            series = pd.to_numeric(self.df[param], errors="coerce")
            missing_percent = float(series.isna().mean())

            values = series.fillna(method='ffill').fillna(method='bfill').to_numpy()
            if len(values) == 0:
                continue

            # Align time array
            time_values = time_array[:len(values)]

            # Apply validation rules
            threshold_v = RuleEngine.threshold(
                values,
                row.get("Min"),
                row.get("Max")
            )

            roc_v = RuleEngine.roc(
                values,
                row.get("ROC")
            )

            # Combine violations
            combined = threshold_v | roc_v

            # Apply duration filter
            duration_v = RuleEngine.duration_filter(
                combined,
                time_values,
                row.get("MinDuration", 0)
            )

            violations = int(np.sum(duration_v))
            violation_percent = violations / len(values) if len(values) > 0 else 0

            # Get violation details
            first_viol_time, max_viol_duration = RuleEngine.get_violation_details(
                duration_v, time_values
            )

            status = self._assign_status(violation_percent, missing_percent)

            # Calculate baseline delta
            baseline_delta = None
            if self.baseline is not None and param in self.baseline.columns:
                try:
                    baseline_series = pd.to_numeric(
                        self.baseline[param], errors="coerce"
                    ).dropna()
                    if len(baseline_series) > 0:
                        baseline_delta = float(values.mean() - baseline_series.mean())
                except Exception:
                    baseline_delta = None

            # Determine category
            category = self._categorize_parameter(param)

            results.append(
                ParameterResult(
                    name=param,
                    unit=row.get("Unit", ""),
                    status=status,
                    violations=violations,
                    violation_percent=float(violation_percent),
                    mean=float(np.mean(values)),
                    max=float(np.max(values)),
                    min=float(np.min(values)),
                    std=float(np.std(values)),
                    baseline_delta=baseline_delta,
                    missing_percent=missing_percent,
                    category=category,
                    first_violation_time=first_viol_time,
                    max_violation_duration=max_viol_duration
                )
            )

        return results

    def _detect_time(self):
        """Detect time column - flexible matching"""
        time_candidates = ["time", "timestamp", "t", "elapsed_time", "test_time", "sec", "seconds"]
        for col in self.df.columns:
            if col.lower() in time_candidates:
                return col
        # Assume first column is time
        return self.df.columns[0]

    def _assign_status(self, violation_percent, missing_percent):
        """Assign PASS/WARNING/FAIL status"""
        if missing_percent > 0.1:
            return "FAIL"
        if violation_percent > 0.05:
            return "FAIL"
        if violation_percent > 0:
            return "WARNING"
        return "PASS"
    
    def _categorize_parameter(self, param_name: str) -> str:
        """Categorize parameters based on naming conventions"""
        param_lower = param_name.lower()
        
        if any(x in param_lower for x in ['temp', 'temperature', 'thermal', 'ect', 'egt', 'iat']):
            return "Temperature"
        elif any(x in param_lower for x in ['press', 'pressure', 'map', 'boost']):
            return "Pressure"
        elif any(x in param_lower for x in ['speed', 'rpm', 'ckp', 'cmp']):
            return "Speed/RPM"
        elif any(x in param_lower for x in ['torque', 'load']):
            return "Torque/Load"
        elif any(x in param_lower for x in ['flow', 'maf', 'rate']):
            return "Flow/Rate"
        elif any(x in param_lower for x in ['voltage', 'current', 'power', 'volt']):
            return "Electrical"
        elif any(x in param_lower for x in ['emission', 'nox', 'co2', 'hc', 'o2', 'soot', 'pm']):
            return "Emissions"
        elif any(x in param_lower for x in ['position', 'tps', 'egr', 'valve']):
            return "Position/Valve"
        elif any(x in param_lower for x in ['fuel']):
            return "Fuel System"
        elif any(x in param_lower for x in ['knock', 'detonation']):
            return "Knock/Detonation"
        else:
            return "Other"


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def detect_test_type(df, time_col) -> TestMetadata:
    """Automatically detect test type and characteristics"""
    duration = df[time_col].max() - df[time_col].min()
    total_sensors = len([col for col in df.columns if col != time_col])
    total_datapoints = len(df)
    
    # Detect frequency based on time delta
    time_diff = df[time_col].diff().median()
    
    if duration > 1500:  # Likely transient test (around 1800s)
        test_type = "Transient"
        if time_diff < 0.15:
            frequency = "10Hz"
        elif time_diff < 0.5:
            frequency = "3Hz"
        else:
            frequency = "1Hz"
    else:
        test_type = "Steady State"
        frequency = f"{1/time_diff:.1f}Hz" if time_diff > 0 else "Unknown"
    
    return TestMetadata(
        test_type=test_type,
        frequency=frequency,
        duration=float(duration),
        total_sensors=total_sensors,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total_datapoints=total_datapoints
    )


@st.cache_data
def run_validation_cached(test_bytes, config_bytes, baseline_bytes=None):
    """Cached validation to prevent re-computation"""
    df = pd.read_excel(io.BytesIO(test_bytes))
    config_df = pd.read_excel(io.BytesIO(config_bytes))
    baseline_df = pd.read_excel(io.BytesIO(baseline_bytes)) if baseline_bytes else None
    
    validator = SpecValidator(df, config_df, baseline_df)
    results = validator.validate()
    
    return results, df, baseline_df, validator


# ==========================================================
# HEADER
# ==========================================================

col_header1, col_header2 = st.columns([3, 1])

with col_header1:
    st.title("PUMA Analytics Pro")
    st.caption("Cummins Test Data Validation & Analysis Platform")

with col_header2:
    st.markdown(f"""
    <div style='text-align: right; padding-top: 20px;'>
        <span style='color: #ffd700; font-size: 12px; font-weight: 600;'>
            CUMMINS ENGINEERING
        </span>
    </div>
    """, unsafe_allow_html=True)

# ==========================================================
# SIDEBAR
# ==========================================================

# Display Cummins logo above the card
import base64
from pathlib import Path

logo_path = Path(__file__).parent / "cummins_logo.png"
if logo_path.exists():
    with open(logo_path, "rb") as f:
        logo_data = base64.b64encode(f.read()).decode()
    st.sidebar.markdown(f"""
    <div style='text-align: center; padding: 16px 20px 12px 20px; background: linear-gradient(135deg, #1a1f3a 0%, #0a0e27 100%); border-radius: 12px; margin-bottom: 20px; border: 2px solid rgba(255, 215, 0, 0.3); box-shadow: 0 4px 20px rgba(255, 215, 0, 0.1);'>
        <img src='data:image/png;base64,{logo_data}' style='width: 120px; height: auto; margin-bottom: 8px;'/>
        <div style='height: 2px; width: 50px; background: linear-gradient(90deg, #ffd700 0%, #ff6b35 100%); margin: 8px auto;'></div>
        <p style='color: #ff6b35; margin: 0; font-size: 10px; font-weight: 600; letter-spacing: 1px;'>PUMA ANALYTICS PRO</p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.sidebar.markdown("""
    <div style='text-align: center; padding: 24px 20px; background: linear-gradient(135deg, #1a1f3a 0%, #0a0e27 100%); border-radius: 12px; margin-bottom: 20px; border: 2px solid rgba(255, 215, 0, 0.3); box-shadow: 0 4px 20px rgba(255, 215, 0, 0.1);'>
        <div style='font-size: 42px; margin-bottom: 8px;'>⚙️</div>
        <h2 style='color: #ffd700; margin: 0; font-size: 22px; font-weight: 700; letter-spacing: 2px;'>CUMMINS</h2>
        <div style='height: 2px; width: 60px; background: linear-gradient(90deg, #ffd700 0%, #ff6b35 100%); margin: 12px auto;'></div>
        <p style='color: #ff6b35; margin: 0; font-size: 11px; font-weight: 600; letter-spacing: 1px;'>PUMA ANALYTICS PRO</p>
    </div>
    """, unsafe_allow_html=True)

st.sidebar.header("📁 Data Upload")

test_file = st.sidebar.file_uploader(
    "Test Data (Excel)", 
    type=["xlsx", "xls"],
    help="Upload PUMA generated test data"
)

config_file = st.sidebar.file_uploader(
    "Configuration (Excel)", 
    type=["xlsx", "xls"],
    help="Upload validation configuration with Min/Max/ROC rules"
)

baseline_file = st.sidebar.file_uploader(
    "Baseline Data (Optional)", 
    type=["xlsx", "xls"],
    help="Upload baseline test for comparison"
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Validation Settings")

# Advanced settings
with st.sidebar.expander("Advanced Options"):
    show_warnings = st.checkbox("Include Warnings in Analysis", value=True)
    auto_categorize = st.checkbox("Auto-Categorize Sensors", value=True)
    show_violation_details = st.checkbox("Show Violation Details", value=True)

st.sidebar.markdown("---")

run_validation = st.sidebar.button("🚀 Run Analysis", use_container_width=True)

# Quick stats in sidebar
if st.session_state.validated and st.session_state.summary_df is not None:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Quick Stats")
    summary_df = st.session_state.summary_df
    
    total = len(summary_df)
    fails = (summary_df["status"] == "FAIL").sum()
    warns = (summary_df["status"] == "WARNING").sum()
    passes = (summary_df["status"] == "PASS").sum()
    
    st.sidebar.metric("Pass Rate", f"{passes/total*100:.1f}%")
    st.sidebar.progress(passes/total)
    
    st.sidebar.markdown(f"""
    <div style='font-size: 12px; color: #888; margin-top: 10px;'>
        ✅ {passes} Passed<br>
        ⚠️ {warns} Warnings<br>
        ❌ {fails} Failed
    </div>
    """, unsafe_allow_html=True)

# ==========================================================
# INFO PANEL
# ==========================================================

if not st.session_state.validated:
    st.markdown("""
    <div class='info-panel'>
        <h3 style='margin-top: 0;'>📊 Welcome to PUMA Analytics Pro</h3>
        <p><strong>Production-grade platform</strong> for analyzing PUMA test data with 600-1500+ sensor columns.</p>
        
        <h4>🎯 Key Features:</h4>
        <ul>
            <li>✅ <strong>Large-Scale Processing:</strong> Handle 600-1800 sensor columns efficiently</li>
            <li>✅ <strong>Intelligent Validation:</strong> Threshold, ROC, and duration-based rules</li>
            <li>✅ <strong>Auto-Detection:</strong> Automatically identifies test type and frequency</li>
            <li>✅ <strong>Smart Categorization:</strong> Groups sensors by type (Temp, Pressure, Emissions, etc.)</li>
            <li>✅ <strong>Baseline Comparison:</strong> Compare tests against reference data</li>
            <li>✅ <strong>Interactive Viz:</strong> Beautiful charts, heatmaps, and time series</li>
            <li>✅ <strong>Multi-Format Export:</strong> JSON, CSV, Excel reports</li>
        </ul>
        
        <h4>🚀 Getting Started:</h4>
        <ol>
            <li>Upload your <strong>Test Data</strong> Excel file (from PUMA)</li>
            <li>Upload <strong>Configuration</strong> file with validation rules</li>
            <li>(Optional) Upload <strong>Baseline</strong> for comparison</li>
            <li>Click <strong>"🚀 Run Analysis"</strong></li>
        </ol>
        
        <p style='margin-bottom: 0;'><em>💡 Tip: If you don't have a config file, the system can auto-generate one from your test data!</em></p>
    </div>
    """, unsafe_allow_html=True)

# ==========================================================
# RUN VALIDATION
# ==========================================================

if run_validation and test_file and config_file:
    
    with st.spinner("🔄 Loading and validating data..."):
        # Read files into bytes for caching
        test_bytes = test_file.read()
        config_bytes = config_file.read()
        baseline_bytes = baseline_file.read() if baseline_file else None
        
        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(pct):
            progress_bar.progress(min(pct, 1.0))
            status_text.text(f"Validating parameters... {int(pct * 100)}%")
        
        try:
            # Run validation
            results, df, baseline_df, validator = run_validation_cached(
                test_bytes, 
                config_bytes, 
                baseline_bytes
            )
            
            # Detect test metadata
            test_metadata = detect_test_type(df, validator.time_col)
            
            # Create summary dataframe
            summary_df = pd.DataFrame([r.__dict__ for r in results])
            
            # Update session state
            st.session_state.summary_df = summary_df
            st.session_state.df = df
            st.session_state.baseline_df = baseline_df
            st.session_state.validator = validator
            st.session_state.validated = True
            st.session_state.test_metadata = test_metadata
            
            progress_bar.progress(1.0)
            status_text.text("✅ Validation complete!")
            
            st.success(f"✅ Successfully validated {len(summary_df)} parameters from {test_metadata.total_datapoints:,} data points!")
            
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Error during validation: {str(e)}")
            st.info("💡 Please check that your files are in the correct format.")

# ==========================================================
# DISPLAY RESULTS
# ==========================================================

if st.session_state.validated and st.session_state.summary_df is not None:
    
    summary_df = st.session_state.summary_df
    df = st.session_state.df
    baseline_df = st.session_state.baseline_df
    validator = st.session_state.validator
    test_metadata = st.session_state.test_metadata
    
    # ==========================================================
    # TEST METADATA PANEL
    # ==========================================================
    
    st.markdown("### 📋 Test Information")
    
    meta_col1, meta_col2, meta_col3, meta_col4, meta_col5 = st.columns(5)
    
    with meta_col1:
        st.markdown(f"""
        <div class='metric-card'>
            <div style='font-size: 12px; color: #888; margin-bottom: 4px;'>TEST TYPE</div>
            <div style='font-size: 20px; font-weight: 700; color: #ffd700;'>{test_metadata.test_type}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with meta_col2:
        freq_display = test_metadata.frequency if test_metadata.frequency else "N/A"
        st.markdown(f"""
        <div class='metric-card'>
            <div style='font-size: 12px; color: #888; margin-bottom: 4px;'>FREQUENCY</div>
            <div style='font-size: 20px; font-weight: 700; color: #ff6b35;'>{freq_display}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with meta_col3:
        st.markdown(f"""
        <div class='metric-card'>
            <div style='font-size: 12px; color: #888; margin-bottom: 4px;'>DURATION</div>
            <div style='font-size: 20px; font-weight: 700; color: #ffd700;'>{int(test_metadata.duration)}s</div>
        </div>
        """, unsafe_allow_html=True)
    
    with meta_col4:
        st.markdown(f"""
        <div class='metric-card'>
            <div style='font-size: 12px; color: #888; margin-bottom: 4px;'>SENSORS</div>
            <div style='font-size: 20px; font-weight: 700; color: #ff6b35;'>{test_metadata.total_sensors}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with meta_col5:
        st.markdown(f"""
        <div class='metric-card'>
            <div style='font-size: 12px; color: #888; margin-bottom: 4px;'>DATA POINTS</div>
            <div style='font-size: 20px; font-weight: 700; color: #ffd700;'>{test_metadata.total_datapoints:,}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ==========================================================
    # KPI DASHBOARD
    # ==========================================================
    
    st.markdown("### 📊 Validation Dashboard")
    
    total = len(summary_df)
    fails = (summary_df["status"] == "FAIL").sum()
    warns = (summary_df["status"] == "WARNING").sum()
    passes = (summary_df["status"] == "PASS").sum()
    pass_rate = (passes / total * 100) if total > 0 else 0
    
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    
    with kpi1:
        st.metric("Total Parameters", total)
    
    with kpi2:
        st.metric("✅ PASS", passes, delta=f"{pass_rate:.1f}%", delta_color="normal")
    
    with kpi3:
        st.metric("⚠️ WARNING", warns)
    
    with kpi4:
        st.metric("❌ FAIL", fails)
    
    with kpi5:
        avg_violation = summary_df['violation_percent'].mean() * 100
        st.metric("Avg Violation %", f"{avg_violation:.2f}%")
    
    # Status pie chart
    chart_col1, chart_col2 = st.columns([1, 2])
    
    with chart_col1:
        status_counts = summary_df['status'].value_counts()
        fig_pie = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            color=status_counts.index,
            color_discrete_map={'PASS': '#2ecc71', 'WARNING': '#f1c40f', 'FAIL': '#e74c3c'},
            title="Status Distribution"
        )
        fig_pie.update_layout(
            template="plotly_dark",
            height=300,
            showlegend=True
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with chart_col2:
        # Category breakdown
        category_stats = summary_df.groupby('category').agg({
            'status': lambda x: ((x == 'PASS').sum() / len(x) * 100),
            'name': 'count'
        }).reset_index()
        category_stats.columns = ['Category', 'Pass Rate %', 'Count']
        category_stats = category_stats.sort_values('Pass Rate %')
        
        fig_category = px.bar(
            category_stats,
            y='Category',
            x='Pass Rate %',
            orientation='h',
            color='Pass Rate %',
            color_continuous_scale=['#e74c3c', '#f1c40f', '#2ecc71'],
            range_color=[0, 100],
            title="Pass Rate by Category",
            text='Count'
        )
        fig_category.update_layout(
            template="plotly_dark",
            height=300,
            showlegend=False,
            xaxis_title="Pass Rate (%)",
            yaxis_title=""
        )
        fig_category.update_traces(texttemplate='%{text} sensors', textposition='outside')
        st.plotly_chart(fig_category, use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ==========================================================
    # FAILED PARAMETERS SUMMARY
    # ==========================================================
    
    if fails > 0 or warns > 0:
        st.markdown("### ⚠️ Parameters Requiring Attention")
        
        attention_df = summary_df[summary_df['status'].isin(['FAIL', 'WARNING'])].copy()
        attention_df = attention_df.sort_values('violation_percent', ascending=False)
        
        # Create summary cards
        st.markdown(f"""
        <div class='info-panel'>
            <h4 style='margin-top: 0; color: #ff6b35;'>🔍 Top Issues Found:</h4>
            <ul style='margin-bottom: 0;'>
        """, unsafe_allow_html=True)
        
        for idx, row in attention_df.head(5).iterrows():
            viol_pct = row['violation_percent'] * 100
            st.markdown(f"<li><strong>{row['name']}</strong> ({row['category']}): {viol_pct:.1f}% violations - Status: <strong>{row['status']}</strong></li>", unsafe_allow_html=True)
        
        st.markdown("</ul></div>", unsafe_allow_html=True)
    
    # ==========================================================
    # MULTI-SENSOR TIME SERIES
    # ==========================================================
    
    st.markdown("### 📈 Multi-Sensor Time Series Analysis")
    
    sensor_col1, sensor_col2, sensor_col3 = st.columns([3, 1, 1])
    
    with sensor_col1:
        all_sensors = [col for col in df.columns if col != validator.time_col]
        
        # Default to failed sensors
        default_sensors = summary_df[summary_df['status'].isin(['FAIL', 'WARNING'])]['name'].head(4).tolist()
        
        selected_sensors = st.multiselect(
            "Select Sensors to Plot (up to 6)",
            all_sensors,
            default=default_sensors[:4],
            max_selections=6
        )
    
    with sensor_col2:
        show_baseline = st.checkbox(
            "Show Baseline", 
            value=True if baseline_df is not None else False,
            disabled=baseline_df is None
        )
    
    with sensor_col3:
        plot_style = st.selectbox(
            "Plot Style",
            ["Stacked Subplots", "Overlaid"],
            index=0
        )
    
    if selected_sensors:
        if plot_style == "Stacked Subplots":
            # Create subplots
            num_plots = len(selected_sensors)
            fig_multi = make_subplots(
                rows=num_plots, 
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                subplot_titles=selected_sensors
            )
            
            for idx, sensor in enumerate(selected_sensors, 1):
                # Test data
                fig_multi.add_trace(
                    go.Scatter(
                        x=df[validator.time_col],
                        y=df[sensor],
                        mode="lines",
                        name=f"{sensor}",
                        line=dict(color='#ffd700', width=1.5),
                        showlegend=(idx == 1)
                    ),
                    row=idx, col=1
                )
                
                # Baseline data
                if show_baseline and baseline_df is not None and sensor in baseline_df.columns:
                    fig_multi.add_trace(
                        go.Scatter(
                            x=baseline_df[validator.time_col],
                            y=baseline_df[sensor],
                            mode="lines",
                            name="Baseline",
                            line=dict(color='#ff6b35', width=1, dash='dash'),
                            showlegend=(idx == 1)
                        ),
                        row=idx, col=1
                    )
                
                # Add unit to y-axis
                sensor_info = summary_df[summary_df['name'] == sensor]
                if not sensor_info.empty:
                    unit = sensor_info.iloc[0]['unit']
                    fig_multi.update_yaxes(title_text=f"{unit}", row=idx, col=1)
            
            fig_multi.update_layout(
                height=250 * num_plots,
                template="plotly_dark",
                hovermode='x unified',
                showlegend=True
            )
            
            fig_multi.update_xaxes(title_text="Time (s)", row=num_plots, col=1)
            
            st.plotly_chart(fig_multi, use_container_width=True)
        
        else:  # Overlaid
            fig_overlay = go.Figure()
            
            for sensor in selected_sensors:
                fig_overlay.add_trace(go.Scatter(
                    x=df[validator.time_col],
                    y=df[sensor],
                    mode="lines",
                    name=sensor,
                    line=dict(width=2)
                ))
            
            fig_overlay.update_layout(
                template="plotly_dark",
                height=500,
                xaxis_title="Time (s)",
                yaxis_title="Value",
                hovermode='x unified',
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=1,
                    xanchor="left",
                    x=1.01
                )
            )
            
            st.plotly_chart(fig_overlay, use_container_width=True)
    else:
        st.info("ℹ️ Select sensors from the dropdown to visualize time series data.")
    
    # ==========================================================
    # DETAILED PARAMETER TABLE
    # ==========================================================
    
    st.markdown("### 📄 Detailed Results Table")
    
    table_col1, table_col2, table_col3 = st.columns([2, 2, 1])
    
    with table_col1:
        status_filter = st.multiselect(
            "Filter by Status",
            ["FAIL", "WARNING", "PASS"],
            default=["FAIL", "WARNING", "PASS"]
        )
    
    with table_col2:
        category_filter = st.multiselect(
            "Filter by Category",
            sorted(summary_df['category'].unique()),
            default=[]
        )
    
    with table_col3:
        search_query = st.text_input("Search", placeholder="Parameter name...")
    
    # Apply filters
    display_df = summary_df[summary_df["status"].isin(status_filter)]
    
    if category_filter:
        display_df = display_df[display_df['category'].isin(category_filter)]
    
    if search_query:
        display_df = display_df[
            display_df["name"].str.contains(search_query, case=False, na=False)
        ]
    
    # Format for display
    table_df = display_df.copy()
    table_df['violation_percent'] = (table_df['violation_percent'] * 100).round(2).astype(str) + '%'
    table_df['missing_percent'] = (table_df['missing_percent'] * 100).round(2).astype(str) + '%'
    
    for col in ['mean', 'max', 'min', 'std']:
        table_df[col] = table_df[col].round(3)
    
    if 'baseline_delta' in table_df.columns:
        # Convert to numeric first, then round
        table_df['baseline_delta'] = pd.to_numeric(table_df['baseline_delta'], errors='coerce').round(3)
    
    if 'first_violation_time' in table_df.columns:
        table_df['first_violation_time'] = pd.to_numeric(table_df['first_violation_time'], errors='coerce').round(2)
    
    if 'max_violation_duration' in table_df.columns:
        table_df['max_violation_duration'] = pd.to_numeric(table_df['max_violation_duration'], errors='coerce').round(2)
    
    # Select columns to display
    display_cols = ['name', 'category', 'status', 'unit', 'mean', 'min', 'max', 
                    'std', 'violations', 'violation_percent', 'missing_percent']
    
    if baseline_df is not None:
        display_cols.append('baseline_delta')
    
    if show_violation_details:
        display_cols.extend(['first_violation_time', 'max_violation_duration'])
    
    available_cols = [col for col in display_cols if col in table_df.columns]
    
    st.dataframe(
        table_df[available_cols],
        use_container_width=True,
        height=400
    )
    
    st.caption(f"Showing {len(table_df)} of {len(summary_df)} parameters")
    
    # ==========================================================
    # EXPORT OPTIONS
    # ==========================================================
    
    st.markdown("### 💾 Export Results")
    
    export_col1, export_col2, export_col3, export_col4 = st.columns(4)
    
    # JSON export
    with export_col1:
        session_data = {
            "timestamp": test_metadata.timestamp,
            "test_metadata": {
                "type": test_metadata.test_type,
                "frequency": test_metadata.frequency,
                "duration": test_metadata.duration,
                "total_sensors": test_metadata.total_sensors,
                "total_datapoints": test_metadata.total_datapoints
            },
            "summary": summary_df.to_dict(orient='records'),
            "statistics": {
                "total_parameters": int(total),
                "pass": int(passes),
                "warning": int(warns),
                "fail": int(fails),
                "pass_rate": float(pass_rate)
            }
        }
        
        st.download_button(
            "📥 Download JSON",
            json.dumps(session_data, indent=2, default=str),
            file_name=f"puma_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    # CSV export
    with export_col2:
        csv_buffer = io.StringIO()
        summary_df.to_csv(csv_buffer, index=False)
        
        st.download_button(
            "📥 Download CSV",
            csv_buffer.getvalue(),
            file_name=f"puma_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    # Excel export
    with export_col3:
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Add category stats
            category_full = summary_df.groupby(['category', 'status']).size().unstack(fill_value=0)
            category_full.to_excel(writer, sheet_name='Category Breakdown')
            
            # Add failed parameters detail
            if fails > 0:
                failed_detail = summary_df[summary_df['status'] == 'FAIL']
                failed_detail.to_excel(writer, sheet_name='Failed Parameters', index=False)
        
        st.download_button(
            "📥 Download Excel",
            excel_buffer.getvalue(),
            file_name=f"puma_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    # Failed parameters only
    with export_col4:
        failed_df = summary_df[summary_df['status'].isin(['FAIL', 'WARNING'])]
        failed_csv = io.StringIO()
        failed_df.to_csv(failed_csv, index=False)
        
        st.download_button(
            "📥 Issues Only (CSV)",
            failed_csv.getvalue(),
            file_name=f"puma_issues_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )

# ==========================================================
# FOOTER
# ==========================================================

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px; border-top: 1px solid rgba(255, 255, 255, 0.1);'>
    <p style='margin: 0;'>PUMA Analytics Pro v2.0 | Built for Cummins Engineering</p>
    <p style='margin: 4px 0 0 0; font-size: 12px;'>Production-Grade Test Data Analysis Platform</p>
</div>
""", unsafe_allow_html=True)
