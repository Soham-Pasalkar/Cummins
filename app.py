import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from dataclasses import dataclass, field
from datetime import datetime
import json
import traceback
import base64
import io
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from scipy import stats as scipy_stats

# ==========================================================
# PAGE CONFIG
# ==========================================================
st.set_page_config(
    page_title="PUMA Analytics Pro | Cummins",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="⚙️"
)

# ==========================================================
# CONSTANTS
# ==========================================================
MISSING_DATA_FAIL_THRESHOLD  = 0.10
VIOLATION_FAIL_THRESHOLD     = 0.05
VIOLATION_WARN_THRESHOLD     = 0.0
TRANSIENT_DURATION_THRESHOLD = 1500

CONFIG_MAP = {
    "Steady":          "PUMA_Config_Steady.xlsx",
    "Transient – 1Hz": "PUMA_Config_Transient_1Hz.xlsx",
    "Transient – 3Hz": "PUMA_Config_Transient_3Hz.xlsx",
    "Transient – 10Hz":"PUMA_Config_Transient_10Hz.xlsx",
}

NAVY       = "#1a3a8f"
DARK_NAVY  = "#0d1b40"
LIGHT_BG   = "#f4f6fb"
WHITE      = "#ffffff"
ACCENT     = "#3b5fc0"
SUCCESS    = "#27ae60"
WARNING    = "#e67e22"
DANGER     = "#c0392b"
MUTED      = "#6b7a99"

CHART_COLORS = [NAVY, "#c0392b", SUCCESS, WARNING, "#8e44ad", "#16a085", "#2980b9", "#d35400"]

# ==========================================================
# CSS
# ==========================================================
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

    * {{ font-family: 'DM Sans', sans-serif !important; }}
    code, pre {{ font-family: 'DM Mono', monospace !important; }}

    .main, .stApp {{ background: {LIGHT_BG}; }}

    /* Hide Streamlit's sidebar script-name artifact */
    [data-testid="stSidebarHeader"] {{ display: none !important; }}

    section[data-testid="stSidebar"] {{ background: {DARK_NAVY} !important; }}

    /* Sidebar markdown/prose → white on dark bg */
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown span,
    section[data-testid="stSidebar"] .stMarkdown strong,
    section[data-testid="stSidebar"] .stMarkdown h3 {{
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }}

    /* Step headings */
    section[data-testid="stSidebar"] h3 {{
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }}

    /* Radio buttons — white text on dark */
    section[data-testid="stSidebar"] .stRadio > label,
    section[data-testid="stSidebar"] .stRadio p {{
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }}

    /* Checkboxes — white text on dark */
    section[data-testid="stSidebar"] .stCheckbox > label,
    section[data-testid="stSidebar"] .stCheckbox p {{
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }}

    /* File uploader — the card has its own bg so needs dark text */
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] *,
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] *,
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] small {{
        color: #333333 !important;
        -webkit-text-fill-color: #333333 !important;
    }}

    /* File uploader top label → white (it's above the card) */
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] > label {{
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }}

    /* Sidebar metrics (quick stats) */
    section[data-testid="stSidebar"] [data-testid="stMetricLabel"] {{
        color: #c8d6f5 !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stMetricValue"] {{
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }}

    h1, h2, h3 {{
        font-weight: 700 !important;
        color: {DARK_NAVY} !important;
        -webkit-text-fill-color: {DARK_NAVY} !important;
        background: none !important;
        letter-spacing: -0.02em;
    }}

    .metric-card {{
        background: {WHITE};
        border: 1px solid #dce3f0;
        border-top: 4px solid {NAVY};
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 2px 8px rgba(13,27,64,0.07);
        transition: all 0.25s ease;
    }}
    .metric-card:hover {{
        border-top-color: {ACCENT};
        box-shadow: 0 8px 24px rgba(13,27,64,0.13);
        transform: translateY(-2px);
    }}
    .metric-card .label {{
        font-size: 11px; color: {MUTED}; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px;
    }}
    .metric-card .value {{
        font-size: 24px; font-weight: 700; color: {DARK_NAVY};
    }}
    .metric-card .sub {{
        font-size: 12px; color: {MUTED}; margin-top: 4px;
    }}

    .status-PASS    {{ color: {SUCCESS}; font-weight: 700; }}
    .status-WARNING {{ color: {WARNING}; font-weight: 700; }}
    .status-FAIL    {{ color: {DANGER};  font-weight: 700; }}

    .info-panel {{
        background: {WHITE};
        border-left: 4px solid {NAVY};
        padding: 18px 22px;
        border-radius: 8px;
        margin: 12px 0;
        box-shadow: 0 2px 8px rgba(13,27,64,0.06);
    }}
    .info-panel h3, .info-panel h4 {{
        color: {DARK_NAVY} !important;
        -webkit-text-fill-color: {DARK_NAVY} !important;
        margin-top: 0;
    }}

    .test-selector-card {{
        background: {WHITE};
        border: 2px solid #dce3f0;
        border-radius: 14px;
        padding: 24px;
        text-align: center;
        cursor: pointer;
        transition: all 0.25s;
        margin-bottom: 8px;
    }}
    .test-selector-card:hover, .test-selector-card.selected {{
        border-color: {NAVY};
        box-shadow: 0 6px 20px rgba(26,58,143,0.18);
    }}

    .stButton>button {{
        background: {NAVY};
        color: {WHITE} !important;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 10px 22px;
        transition: all 0.25s;
    }}
    .stButton>button:hover {{
        background: {ACCENT};
        box-shadow: 0 6px 20px rgba(26,58,143,0.3);
        transform: translateY(-2px);
        color: {WHITE} !important;
    }}

    .stDataFrame {{ border: 1px solid #dce3f0; border-radius: 8px; overflow: hidden; }}

    /* ── TAB TEXT FIX ── */
    [data-testid="stTabs"] [data-baseweb="tab"] {{
        color: {DARK_NAVY} !important;
        -webkit-text-fill-color: {DARK_NAVY} !important;
    }}
    [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {{
        color: {NAVY} !important;
        -webkit-text-fill-color: {NAVY} !important;
        font-weight: 600 !important;
    }}
    [data-testid="stTabs"] [data-baseweb="tab"]:hover {{
        color: {NAVY} !important;
        -webkit-text-fill-color: {NAVY} !important;
    }}

    /* ── MAIN CONTENT MARKDOWN TEXT FIX ── */
    .main .stMarkdown p,
    .main .stMarkdown span,
    .main .stMarkdown strong,
    .main .stMarkdown b,
    .main .stMarkdown li,
    .block-container .stMarkdown p,
    .block-container .stMarkdown strong,
    .block-container .stMarkdown b {{
        color: {DARK_NAVY} !important;
        -webkit-text-fill-color: {DARK_NAVY} !important;
    }}

    [data-testid="stMetricLabel"] {{ color: {MUTED} !important; font-size: 12px !important; }}
    [data-testid="stMetricValue"] {{ color: {DARK_NAVY} !important; font-weight: 700 !important; }}

    .section-header {{
        font-size: 18px; font-weight: 700; color: {DARK_NAVY};
        border-bottom: 2px solid #dce3f0; padding-bottom: 8px;
        margin: 24px 0 16px 0;
    }}

    .tag {{
        display: inline-block; padding: 2px 10px;
        border-radius: 20px; font-size: 11px; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.5px;
    }}
    .tag-PASS    {{ background: #eafaf1; color: {SUCCESS}; }}
    .tag-WARNING {{ background: #fef9e7; color: {WARNING}; }}
    .tag-FAIL    {{ background: #fdedec; color: {DANGER};  }}

    .warning-box {{
        background: #fef9e7; border-left: 4px solid {WARNING};
        padding: 12px 16px; border-radius: 6px; margin: 8px 0;
        color: #7d5a00; font-size: 13px;
    }}
    .error-box {{
        background: #fdedec; border-left: 4px solid {DANGER};
        padding: 12px 16px; border-radius: 6px; margin: 8px 0;
        color: #922b21; font-size: 13px;
    }}
    .success-box {{
        background: #eafaf1; border-left: 4px solid {SUCCESS};
        padding: 12px 16px; border-radius: 6px; margin: 8px 0;
        color: #1e8449; font-size: 13px;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================================
# PLOTLY LAYOUT DEFAULTS — all chart text black
# ==========================================================
PLOT_FONT       = dict(color=DARK_NAVY, family="DM Sans, sans-serif")
PLOT_AXIS_FONT  = dict(color=DARK_NAVY, size=12)
PLOT_TICK_FONT  = dict(color=DARK_NAVY, size=11)
PLOT_TITLE_FONT = dict(color=DARK_NAVY, size=13)

def apply_chart_defaults(fig, height=None, title=None):
    """Apply consistent dark-text styling to any Plotly figure."""
    updates = dict(
        font=PLOT_FONT,
        title_font=PLOT_TITLE_FONT,
        paper_bgcolor=WHITE,
        plot_bgcolor="#f8faff",
        template="plotly_white",
    )
    if height:
        updates["height"] = height
    if title:
        updates["title"] = title
    fig.update_layout(**updates)
    fig.update_xaxes(
        title_font=PLOT_AXIS_FONT,
        tickfont=PLOT_TICK_FONT,
        linecolor=DARK_NAVY,
        gridcolor="#e8ecf4",
    )
    fig.update_yaxes(
        title_font=PLOT_AXIS_FONT,
        tickfont=PLOT_TICK_FONT,
        linecolor=DARK_NAVY,
        gridcolor="#e8ecf4",
    )
    # Fix subplot annotation (title) colors
    for ann in fig.layout.annotations:
        ann.font = dict(color=DARK_NAVY, size=12)
    return fig

# ==========================================================
# SESSION STATE
# ==========================================================
defaults = {
    "validated": False,
    "summary_df": None,
    "df": None,
    "baseline_df": None,
    "time_col": None,
    "test_metadata": {},
    "selected_test_type": None,
    "config_df": None,
    "match_report": None,
    "validation_warnings": [],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

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
    max_val: float
    min_val: float
    std: float
    cv_pct: float
    baseline_delta: Optional[float]
    missing_percent: float
    category: str = "General"
    config_min: Optional[float] = None
    config_max: Optional[float] = None
    config_warn_low: Optional[float] = None
    config_warn_high: Optional[float] = None
    config_mean: Optional[float] = None
    config_std: Optional[float] = None
    config_cv: Optional[float] = None


@dataclass
class MatchReport:
    matched: List[str] = field(default_factory=list)
    in_data_not_config: List[str] = field(default_factory=list)
    in_config_not_data: List[str] = field(default_factory=list)
    total_data_params: int = 0
    total_config_params: int = 0

    @property
    def match_rate(self):
        if self.total_config_params == 0:
            return 0.0
        return len(self.matched) / self.total_config_params * 100


# ==========================================================
# FILE LOADING — ROBUST
# ==========================================================

def safe_load_file(uploaded_file) -> Tuple[Optional[pd.DataFrame], List[str]]:
    warnings = []
    try:
        file_bytes = uploaded_file.read()
        filename   = uploaded_file.name.lower()
        df = _parse_bytes(file_bytes, filename, warnings)
        if df is None or df.empty:
            return None, warnings + [f"File '{uploaded_file.name}' loaded as empty — check format."]
        return df, warnings
    except Exception as e:
        return None, [f"Failed to load '{uploaded_file.name}': {e}"]


def safe_load_bytes(file_bytes: bytes, filename: str) -> Tuple[Optional[pd.DataFrame], List[str]]:
    warnings = []
    try:
        df = _parse_bytes(file_bytes, filename.lower(), warnings)
        if df is None or df.empty:
            return None, warnings + [f"File '{filename}' loaded as empty."]
        return df, warnings
    except Exception as e:
        return None, [f"Failed to parse '{filename}': {e}"]


def _parse_bytes(file_bytes: bytes, filename: str, warnings: List[str]) -> Optional[pd.DataFrame]:
    if filename.endswith(('.xlsx', '.xls')):
        try:
            df = pd.read_excel(io.BytesIO(file_bytes), header=0)
            unnamed_ratio = sum(1 for c in df.columns if str(c).startswith('Unnamed')) / max(len(df.columns), 1)
            if unnamed_ratio > 0.5:
                warnings.append("Detected title row — skipping first row and re-reading.")
                df = pd.read_excel(io.BytesIO(file_bytes), header=1)
            for col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col], errors='ignore')
                except Exception:
                    pass
            return df
        except Exception as e:
            raise ValueError(f"Excel parse error: {e}")

    elif filename.endswith('.csv'):
        for sep in [',', '\t', ';', '|']:
            try:
                df = pd.read_csv(io.BytesIO(file_bytes), sep=sep)
                if df.shape[1] > 1:
                    return df
            except Exception:
                continue
        return pd.read_csv(io.BytesIO(file_bytes))

    elif filename.endswith('.txt'):
        for sep in ['\t', ',', ';', '|']:
            try:
                df = pd.read_csv(io.BytesIO(file_bytes), sep=sep)
                if df.shape[1] > 1:
                    return df
            except Exception:
                continue
        return pd.read_csv(io.BytesIO(file_bytes), sep=None, engine='python')

    else:
        raise ValueError(f"Unsupported file type: {filename}")


# ==========================================================
# CONFIG VALIDATION
# ==========================================================

def validate_config_integrity(config_df: pd.DataFrame) -> Tuple[bool, List[str]]:
    issues = []
    if "Parameter" not in config_df.columns:
        issues.append("Config is missing required 'Parameter' column.")
        return False, issues
    if "Min" not in config_df.columns or "Max" not in config_df.columns:
        issues.append("Config is missing 'Min' or 'Max' columns — threshold checks disabled.")

    if "Min" in config_df.columns and "Max" in config_df.columns:
        bad = config_df.dropna(subset=["Min","Max"])
        bad = bad[pd.to_numeric(bad["Min"], errors='coerce') > pd.to_numeric(bad["Max"], errors='coerce')]
        if len(bad) > 0:
            issues.append(f"Min > Max for {len(bad)} parameters: {bad['Parameter'].tolist()[:5]}{'...' if len(bad)>5 else ''}. These rows will be skipped.")

    dupes = config_df["Parameter"].duplicated()
    if dupes.any():
        issues.append(f"Duplicate parameters in config: {config_df['Parameter'][dupes].tolist()}. First occurrence used.")

    return True, issues


def reconcile_parameters(data_df: pd.DataFrame, config_df: pd.DataFrame, time_col: str) -> MatchReport:
    data_params   = set(c for c in data_df.columns if c != time_col)
    config_params = set(config_df["Parameter"].dropna().tolist())

    matched             = sorted(data_params & config_params)
    in_data_not_config  = sorted(data_params - config_params)
    in_config_not_data  = sorted(config_params - data_params)

    return MatchReport(
        matched=matched,
        in_data_not_config=in_data_not_config,
        in_config_not_data=in_config_not_data,
        total_data_params=len(data_params),
        total_config_params=len(config_params),
    )


# ==========================================================
# TIME DETECTION
# ==========================================================

def detect_time_col(df: pd.DataFrame) -> str:
    candidates = ["time (s)", "time_s", "time", "t", "elapsed_time", "test_time", "sec", "seconds", "timestamp"]
    for c in candidates:
        for col in df.columns:
            if col.lower() == c and pd.api.types.is_numeric_dtype(df[col]):
                return col
    for col in df.columns:
        if 'time' in col.lower() and pd.api.types.is_numeric_dtype(df[col]):
            return col
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            return col
    return df.columns[0]


# ==========================================================
# SENSOR CATEGORIZATION
# ==========================================================

def categorize_parameter(name: str) -> str:
    p = name.lower()
    if any(x in p for x in ['temp','thermal','ect','egt','iat','_t_','_t$']):
        return "Temperature"
    elif any(x in p for x in ['press','pres','map','boost','baro','_p_']):
        return "Pressure"
    elif any(x in p for x in ['speed','rpm','ckp','cmp','freq']):
        return "Speed/RPM"
    elif any(x in p for x in ['torque','load','trq']):
        return "Torque/Load"
    elif any(x in p for x in ['flow','maf','rate','mass']):
        return "Flow/Rate"
    elif any(x in p for x in ['volt','current','power','elec','batt']):
        return "Electrical"
    elif any(x in p for x in ['nox','co2','hc','o2','soot','pm','emission','dpf','scr','urea']):
        return "Emissions"
    elif any(x in p for x in ['pos','tps','egr','valve','vgt','throttle']):
        return "Position/Valve"
    elif any(x in p for x in ['fuel','inj','rail']):
        return "Fuel System"
    elif any(x in p for x in ['knock','det']):
        return "Knock"
    elif any(x in p for x in ['lambda','afr','air']):
        return "Air/Fuel"
    elif any(x in p for x in ['cool','water','oil','lube']):
        return "Cooling/Lubrication"
    return "Other"


# ==========================================================
# VALIDATION ENGINE
# ==========================================================

def run_validation(
    df: pd.DataFrame,
    config_df: pd.DataFrame,
    time_col: str,
    matched_params: List[str],
    baseline_df: Optional[pd.DataFrame] = None,
) -> Tuple[List[ParameterResult], List[str]]:
    time_array = df[time_col].to_numpy(dtype=float)
    config_lookup = config_df.drop_duplicates(subset=["Parameter"]).set_index("Parameter")
    results  = []
    warnings = []

    for param in matched_params:
        try:
            row = config_lookup.loc[param]

            series  = pd.to_numeric(df[param], errors="coerce")
            missing_pct = float(series.isna().mean())
            values  = series.ffill().bfill().to_numpy(dtype=float)

            if len(values) == 0:
                warnings.append(f"{param}: no numeric data found — skipped.")
                continue

            tv = time_array[:len(values)]

            viols = np.zeros(len(values), dtype=bool)
            c_min = _safe_float(row.get("Min"))
            c_max = _safe_float(row.get("Max"))
            if c_min is not None: viols |= values < c_min
            if c_max is not None: viols |= values > c_max

            viol_count   = int(np.sum(viols))
            viol_pct     = viol_count / len(values) if len(values) > 0 else 0.0

            if missing_pct > MISSING_DATA_FAIL_THRESHOLD:
                status = "FAIL"
            elif viol_pct > VIOLATION_FAIL_THRESHOLD:
                status = "FAIL"
            elif viol_pct > VIOLATION_WARN_THRESHOLD:
                status = "WARNING"
            else:
                status = "PASS"

            mean_val = float(np.nanmean(values))
            std_val  = float(np.nanstd(values))
            cv_pct   = float((std_val / abs(mean_val)) * 100) if abs(mean_val) > 1e-9 else 0.0

            baseline_delta = None
            if baseline_df is not None and param in baseline_df.columns:
                try:
                    b = pd.to_numeric(baseline_df[param], errors="coerce").dropna()
                    if len(b) > 0:
                        baseline_delta = float(mean_val - b.mean())
                except Exception:
                    pass

            results.append(ParameterResult(
                name=param,
                unit=str(row.get("Unit", "")),
                status=status,
                violations=viol_count,
                violation_percent=float(viol_pct),
                mean=mean_val,
                max_val=float(np.nanmax(values)),
                min_val=float(np.nanmin(values)),
                std=std_val,
                cv_pct=round(cv_pct, 2),
                baseline_delta=baseline_delta,
                missing_percent=missing_pct,
                category=categorize_parameter(param),
                config_min=c_min,
                config_max=c_max,
                config_warn_low=_safe_float(row.get("WarnLow")),
                config_warn_high=_safe_float(row.get("WarnHigh")),
                config_mean=_safe_float(row.get("Mean")),
                config_std=_safe_float(row.get("Std Dev")),
                config_cv=_safe_float(row.get("CV (%)")),
            ))

        except KeyError:
            warnings.append(f"{param}: not found in config index — skipped.")
        except Exception as e:
            warnings.append(f"{param}: unexpected error during validation — {e}. Skipped.")

    return results, warnings


def _safe_float(val) -> Optional[float]:
    try:
        v = float(val)
        return None if np.isnan(v) else v
    except Exception:
        return None


# ==========================================================
# TEST METADATA DETECTION
# ==========================================================

def detect_test_metadata(df: pd.DataFrame, time_col: str, selected_type: str) -> dict:
    try:
        duration         = float(df[time_col].max() - df[time_col].min())
        total_sensors    = len([c for c in df.columns if c != time_col])
        total_datapoints = len(df)
        time_diff        = df[time_col].diff().median()
        freq_hz          = (1 / time_diff) if time_diff and time_diff > 0 else None

        return {
            "selected_type":    selected_type,
            "duration":         duration,
            "total_sensors":    total_sensors,
            "total_datapoints": total_datapoints,
            "detected_freq_hz": round(freq_hz, 2) if freq_hz else None,
            "timestamp":        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        return {"selected_type": selected_type, "error": str(e)}


# ==========================================================
# PDF REPORT GENERATION
# ==========================================================

def generate_pdf_report(
    summary_df: pd.DataFrame,
    metadata: dict,
    match_report: MatchReport,
    test_type: str,
) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table,
        TableStyle, HRFlowable, PageBreak
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=18*mm, leftMargin=18*mm,
        topMargin=22*mm, bottomMargin=18*mm
    )

    RL_NAVY    = colors.HexColor("#1a3a8f")
    RL_DARK    = colors.HexColor("#0d1b40")
    RL_ACCENT  = colors.HexColor("#3b5fc0")
    RL_SUCCESS = colors.HexColor("#27ae60")
    RL_WARN    = colors.HexColor("#e67e22")
    RL_FAIL    = colors.HexColor("#c0392b")
    RL_LIGHT   = colors.HexColor("#f4f6fb")
    RL_BORDER  = colors.HexColor("#dce3f0")
    RL_MUTED   = colors.HexColor("#6b7a99")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", fontSize=22, textColor=RL_DARK,
                                  fontName="Helvetica-Bold", spaceAfter=4, alignment=TA_LEFT)
    subtitle_style = ParagraphStyle("Sub", fontSize=11, textColor=RL_NAVY,
                                     fontName="Helvetica", spaceAfter=16, alignment=TA_LEFT)
    h2_style = ParagraphStyle("H2", fontSize=14, textColor=RL_DARK,
                               fontName="Helvetica-Bold", spaceBefore=16, spaceAfter=8)
    h3_style = ParagraphStyle("H3", fontSize=11, textColor=RL_NAVY,
                               fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=6)
    body_style = ParagraphStyle("Body", fontSize=9, textColor=colors.HexColor("#2c3e6b"),
                                 fontName="Helvetica", leading=14)
    small_style = ParagraphStyle("Small", fontSize=8, textColor=RL_MUTED,
                                  fontName="Helvetica", leading=12)
    center_style = ParagraphStyle("Center", fontSize=9, alignment=TA_CENTER,
                                   fontName="Helvetica")

    story = []

    story.append(Paragraph("PUMA Analytics Pro", title_style))
    story.append(Paragraph(f"Test Validation Report — {test_type}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=RL_NAVY, spaceAfter=12))

    story.append(Paragraph("Test Information", h2_style))
    ts = metadata.get("timestamp", "N/A")
    dur = metadata.get("duration", 0)
    freq = metadata.get("detected_freq_hz", "N/A")
    sensors = metadata.get("total_sensors", "N/A")
    dpts = metadata.get("total_datapoints", 0)

    meta_data = [
        ["Field", "Value"],
        ["Test Type", test_type],
        ["Timestamp", ts],
        ["Duration", f"{int(dur)}s ({dur/60:.1f} min)"],
        ["Detected Frequency", f"{freq} Hz" if freq != "N/A" else "N/A"],
        ["Total Sensors in Data", str(sensors)],
        ["Total Data Points", f"{dpts:,}"],
        ["Parameters Validated", str(len(match_report.matched))],
        ["Config Parameters", str(match_report.total_config_params)],
        ["Match Rate", f"{match_report.match_rate:.1f}%"],
    ]
    meta_table = Table(meta_data, colWidths=[70*mm, 100*mm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), RL_NAVY),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 9),
        ("BACKGROUND", (0,1), (-1,-1), RL_LIGHT),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, RL_LIGHT]),
        ("GRID",       (0,0), (-1,-1), 0.5, RL_BORDER),
        ("ROWHEIGHT",  (0,0), (-1,-1), 16),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING",(0,0), (-1,-1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Validation Summary", h2_style))
    total  = len(summary_df)
    fails  = (summary_df["status"] == "FAIL").sum()
    warns  = (summary_df["status"] == "WARNING").sum()
    passes = (summary_df["status"] == "PASS").sum()
    pass_rate = passes / total * 100 if total > 0 else 0

    kpi_data = [
        ["Metric", "Count", "Percentage"],
        ["✓  PASS",    str(passes), f"{pass_rate:.1f}%"],
        ["⚠  WARNING", str(warns),  f"{warns/total*100:.1f}%" if total else "0%"],
        ["✗  FAIL",    str(fails),  f"{fails/total*100:.1f}%" if total else "0%"],
        ["TOTAL",      str(total),  "100%"],
    ]
    kpi_table = Table(kpi_data, colWidths=[80*mm, 45*mm, 45*mm])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), RL_DARK),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME",   (0,-1),(-1,-1),"Helvetica-Bold"),
        ("BACKGROUND", (0,1), (-1,1), colors.HexColor("#eafaf1")),
        ("BACKGROUND", (0,2), (-1,2), colors.HexColor("#fef9e7")),
        ("BACKGROUND", (0,3), (-1,3), colors.HexColor("#fdedec")),
        ("BACKGROUND", (0,4), (-1,4), RL_LIGHT),
        ("TEXTCOLOR",  (0,1), (-1,1), RL_SUCCESS),
        ("TEXTCOLOR",  (0,2), (-1,2), RL_WARN),
        ("TEXTCOLOR",  (0,3), (-1,3), RL_FAIL),
        ("FONTNAME",   (0,1), (-1,3), "Helvetica-Bold"),
        ("GRID",       (0,0), (-1,-1), 0.5, RL_BORDER),
        ("FONTSIZE",   (0,0), (-1,-1), 10),
        ("ROWHEIGHT",  (0,0), (-1,-1), 18),
        ("ALIGN",      (1,0), (-1,-1), "CENTER"),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING",(0,0), (-1,-1), 10),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 14))

    if match_report.in_config_not_data or match_report.in_data_not_config:
        story.append(Paragraph("Parameter Mismatch Report", h2_style))
        if match_report.in_config_not_data:
            story.append(Paragraph(
                f"Parameters in Config but NOT in Data ({len(match_report.in_config_not_data)}):", h3_style))
            txt = ", ".join(match_report.in_config_not_data[:30])
            if len(match_report.in_config_not_data) > 30:
                txt += f" ... and {len(match_report.in_config_not_data)-30} more"
            story.append(Paragraph(txt, small_style))
            story.append(Spacer(1, 6))
        if match_report.in_data_not_config:
            story.append(Paragraph(
                f"Parameters in Data but NOT in Config ({len(match_report.in_data_not_config)}) — unvalidated:", h3_style))
            txt = ", ".join(match_report.in_data_not_config[:30])
            if len(match_report.in_data_not_config) > 30:
                txt += f" ... and {len(match_report.in_data_not_config)-30} more"
            story.append(Paragraph(txt, small_style))
        story.append(Spacer(1, 10))

    failed_df = summary_df[summary_df["status"] == "FAIL"].sort_values("violation_percent", ascending=False)
    if len(failed_df) > 0:
        story.append(PageBreak())
        story.append(Paragraph("Failed Parameters", h2_style))
        fail_headers = ["Parameter", "Category", "Unit", "Mean", "Std Dev", "CV%", "Viol%", "Config Min", "Config Max"]
        fail_rows = [fail_headers]
        for _, r in failed_df.head(50).iterrows():
            fail_rows.append([
                r["name"][:28],
                r.get("category",""),
                r.get("unit",""),
                f"{r['mean']:.2f}",
                f"{r['std']:.2f}",
                f"{r.get('cv_pct',0):.1f}%",
                f"{r['violation_percent']*100:.1f}%",
                f"{r.get('config_min','N/A')}",
                f"{r.get('config_max','N/A')}",
            ])
        col_w = [48*mm,28*mm,14*mm,18*mm,18*mm,14*mm,14*mm,18*mm,18*mm]
        fail_table = Table(fail_rows, colWidths=col_w, repeatRows=1)
        fail_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), RL_FAIL),
            ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 7.5),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#fff5f5")]),
            ("GRID",       (0,0), (-1,-1), 0.4, RL_BORDER),
            ("ROWHEIGHT",  (0,0), (-1,-1), 14),
            ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING",(0,0), (-1,-1), 5),
        ]))
        story.append(fail_table)
        if len(failed_df) > 50:
            story.append(Paragraph(f"... and {len(failed_df)-50} more failed parameters (see CSV export).", small_style))

    story.append(PageBreak())
    story.append(Paragraph("Full Parameter Results", h2_style))
    all_headers = ["Parameter", "Category", "Status", "Mean", "Std Dev", "CV%", "Violations", "Missing%"]
    all_rows = [all_headers]
    for _, r in summary_df.sort_values("status").iterrows():
        all_rows.append([
            r["name"][:30],
            r.get("category",""),
            r["status"],
            f"{r['mean']:.2f}",
            f"{r['std']:.2f}",
            f"{r.get('cv_pct',0):.1f}%",
            f"{r['violation_percent']*100:.1f}%",
            f"{r['missing_percent']*100:.1f}%",
        ])

    col_w2 = [52*mm, 30*mm, 20*mm, 20*mm, 20*mm, 14*mm, 18*mm, 16*mm]
    all_table = Table(all_rows, colWidths=col_w2, repeatRows=1)

    row_styles = [
        ("BACKGROUND", (0,0), (-1,0), RL_DARK),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.black),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 7.5),
        ("GRID",       (0,0), (-1,-1), 0.4, RL_BORDER),
        ("ROWHEIGHT",  (0,0), (-1,-1), 13),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING",(0,0), (-1,-1), 5),
    ]
    for i, row in enumerate(all_rows[1:], 1):
        if row[2] == "FAIL":
            row_styles.append(("BACKGROUND", (0,i), (-1,i), colors.HexColor("#fff0f0")))
            row_styles.append(("TEXTCOLOR",  (2,i), (2,i), RL_FAIL))
        elif row[2] == "WARNING":
            row_styles.append(("BACKGROUND", (0,i), (-1,i), colors.HexColor("#fffbf0")))
            row_styles.append(("TEXTCOLOR",  (2,i), (2,i), RL_WARN))
        else:
            row_styles.append(("BACKGROUND", (0,i), (-1,i), colors.white if i%2==0 else RL_LIGHT))
            row_styles.append(("TEXTCOLOR",  (2,i), (2,i), RL_SUCCESS))

    all_table.setStyle(TableStyle(row_styles))
    story.append(all_table)

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=RL_BORDER))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Generated by PUMA Analytics Pro | Cummins Engineering | {ts}",
        ParagraphStyle("Footer", fontSize=8, textColor=RL_MUTED, alignment=TA_CENTER)
    ))

    doc.build(story)
    return buf.getvalue()


# ==========================================================
# LOGO
# ==========================================================
def render_logo_sidebar():
    logo_path = Path(__file__).parent / "cummins-logo-png-transparent.png"
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
        st.sidebar.markdown(f"""
        <div style='text-align:center;padding:16px 20px 12px;background:#fff;
             border-radius:12px;margin-bottom:20px;'>
            <img src='data:image/png;base64,{logo_b64}'
                 style='width:120px;height:auto;margin-bottom:8px;'/>
            <div style='height:2px;width:50px;background:{NAVY};margin:8px auto;opacity:0.5;'></div>
            <p style='color:{NAVY};margin:0;font-size:10px;font-weight:600;letter-spacing:1px;'>
                PUMA ANALYTICS PRO</p>
        </div>""", unsafe_allow_html=True)
    else:
        st.sidebar.markdown(f"""
        <div style='text-align:center;padding:24px 20px;background:{NAVY};border-radius:12px;
             margin-bottom:20px;'>
            <div style='font-size:40px;margin-bottom:8px;'>⚙️</div>
            <h2 style='color:#fff;margin:0;font-size:20px;font-weight:700;letter-spacing:2px;
                -webkit-text-fill-color:#fff !important;'>CUMMINS</h2>
            <div style='height:2px;width:60px;background:rgba(255,255,255,0.4);margin:12px auto;'></div>
            <p style='color:#c8d6f5;margin:0;font-size:11px;font-weight:600;letter-spacing:1px;'>
                PUMA ANALYTICS PRO</p>
        </div>""", unsafe_allow_html=True)


# ==========================================================
# ██████████████████████  UI  ██████████████████████
# ==========================================================

col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.title("PUMA Analytics Pro")
    st.caption("Cummins Test Data Validation & Analysis Platform")
with col_h2:
    st.markdown(f"""
    <div style='text-align:right;padding-top:20px;'>
        <span style='color:{NAVY};font-size:11px;font-weight:700;letter-spacing:1px;'>
            CUMMINS ENGINEERING
        </span>
    </div>""", unsafe_allow_html=True)

render_logo_sidebar()

st.sidebar.markdown(f"""
<div style='background:rgba(255,255,255,0.08);border-radius:8px;padding:10px 14px;
     margin-bottom:12px;font-size:11px;color:#c8d6f5;'>
    📎 <strong style='color:#fff;'>Supported:</strong>
    Excel (.xlsx, .xls) &nbsp;|&nbsp; CSV &nbsp;|&nbsp; TXT
</div>""", unsafe_allow_html=True)

st.sidebar.markdown("### 🔬 Step 1 — Select Test Type")
test_type_choice = st.sidebar.radio(
    "Test Type",
    list(CONFIG_MAP.keys()),
    index=0,
    help="Choose before uploading. The matching config file will be auto-loaded."
)
st.session_state.selected_test_type = test_type_choice

st.sidebar.markdown(f"""
<div style='background:rgba(26,58,143,0.35);border-radius:6px;padding:8px 12px;
     margin-bottom:12px;font-size:11px;color:#c8d6f5;'>
    📄 Config: <strong style='color:#fff;'>{CONFIG_MAP[test_type_choice]}</strong>
</div>""", unsafe_allow_html=True)

st.sidebar.markdown("### 📁 Step 2 — Upload Files")
ACCEPTED = ["xlsx", "xls", "csv", "txt"]

test_file     = st.sidebar.file_uploader("Test Data *", type=ACCEPTED)
config_file   = st.sidebar.file_uploader(
    "Config Override (optional)", type=ACCEPTED,
    help=f"Leave blank to auto-use {CONFIG_MAP[test_type_choice]}"
)
baseline_file = st.sidebar.file_uploader("Baseline Data (optional)", type=ACCEPTED)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Step 3 — Options")
show_warnings         = st.sidebar.checkbox("Include Warnings in Analysis", value=True)
show_violation_detail = st.sidebar.checkbox("Show Violation Detail", value=True)
st.sidebar.markdown("---")

run_btn = st.sidebar.button("🚀 Run Analysis", use_container_width=True)

if st.session_state.validated and st.session_state.summary_df is not None:
    sdf = st.session_state.summary_df
    _total  = len(sdf)
    _passes = (sdf["status"] == "PASS").sum()
    _warns  = (sdf["status"] == "WARNING").sum()
    _fails  = (sdf["status"] == "FAIL").sum()
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Quick Stats")
    st.sidebar.metric("Pass Rate", f"{_passes/_total*100:.1f}%")
    st.sidebar.progress(_passes / _total)
    st.sidebar.markdown(f"""
    <div style='font-size:12px;color:#c8d6f5;margin-top:8px;'>
        ✅ {_passes} Passed &nbsp; ⚠️ {_warns} Warnings &nbsp; ❌ {_fails} Failed
    </div>""", unsafe_allow_html=True)

# ==========================================================
# WELCOME
# ==========================================================
if not st.session_state.validated:
    st.markdown(f"""
<div class='info-panel'>
<h3>📊 Welcome to PUMA Analytics Pro</h3>
<p>Production-grade platform for validating and analysing PUMA engine test data with 600–1500+ sensor parameters.</p>
<h4 style='color:{NAVY} !important;-webkit-text-fill-color:{NAVY} !important;'>🎯 Getting Started:</h4>
<ol style='color:#2c3e6b;'>
    <li><strong>Select Test Type</strong> in the sidebar — Steady or Transient (1/3/10 Hz)</li>
    <li><strong>Upload Test Data</strong> (.xlsx, .csv, .txt)</li>
    <li><strong>Optionally</strong> override config or upload a baseline for comparison</li>
    <li>Click <strong>Run Analysis</strong></li>
</ol>
<h4 style='color:{NAVY} !important;-webkit-text-fill-color:{NAVY} !important;'>✨ Features:</h4>
<p style='color:#2c3e6b;'>
Intelligent parameter matching (partial data handled gracefully) &nbsp;|&nbsp;
Strong error handling &nbsp;|&nbsp;
Multi-sensor time series &nbsp;|&nbsp;
Correlation, FFT, histogram, box plot, scatter, heatmap visualisations &nbsp;|&nbsp;
PDF + Excel + CSV export
</p>
</div>""", unsafe_allow_html=True)

# ==========================================================
# RUN VALIDATION
# ==========================================================
if run_btn:
    if not test_file:
        st.error("❌ Please upload a Test Data file to continue.")
        st.stop()

    all_warnings = []

    with st.spinner("🔄 Loading test data..."):
        test_bytes = test_file.read()
        df, w = safe_load_bytes(test_bytes, test_file.name)
        all_warnings.extend(w)
        if df is None:
            st.error(f"❌ Could not load test file: {'; '.join(w)}")
            st.stop()

    config_df = None
    with st.spinner("🔄 Loading configuration..."):
        if config_file:
            cfg_bytes = config_file.read()
            config_df, w = safe_load_bytes(cfg_bytes, config_file.name)
            all_warnings.extend(w)
            if config_df is None:
                st.warning(f"⚠️ Could not load override config: {'; '.join(w)}. Trying auto-config...")

        if config_df is None:
            auto_cfg_path = Path(__file__).parent / CONFIG_MAP[test_type_choice]
            if auto_cfg_path.exists():
                with open(auto_cfg_path, "rb") as f:
                    cfg_b = f.read()
                config_df, w = safe_load_bytes(cfg_b, CONFIG_MAP[test_type_choice])
                all_warnings.extend(w)
            if config_df is None:
                st.error(
                    f"❌ No config found. Expected '{CONFIG_MAP[test_type_choice]}' in app directory, "
                    f"or upload a config override in the sidebar."
                )
                st.stop()

    cfg_ok, cfg_issues = validate_config_integrity(config_df)
    for issue in cfg_issues:
        all_warnings.append(f"Config issue: {issue}")
    if not cfg_ok:
        st.error(f"❌ Config file has critical issues: {'; '.join(cfg_issues)}")
        st.stop()

    baseline_df = None
    if baseline_file:
        with st.spinner("🔄 Loading baseline..."):
            b_bytes = baseline_file.read()
            baseline_df, w = safe_load_bytes(b_bytes, baseline_file.name)
            all_warnings.extend(w)
            if baseline_df is None:
                all_warnings.append("Baseline could not be loaded — baseline comparison disabled.")

    with st.spinner("🔄 Detecting time column & test metadata..."):
        time_col = detect_time_col(df)
        metadata = detect_test_metadata(df, time_col, test_type_choice)

    with st.spinner("🔄 Reconciling parameters..."):
        match_report = reconcile_parameters(df, config_df, time_col)
        if len(match_report.matched) == 0:
            st.error(
                "❌ Zero parameters matched between data and config. "
                "Check that your data columns match the 'Parameter' column in the config."
            )
            st.stop()

    progress_bar  = st.progress(0)
    status_text   = st.empty()

    with st.spinner(f"🔄 Validating {len(match_report.matched)} matched parameters..."):
        results, runtime_warnings = run_validation(
            df, config_df, time_col, match_report.matched, baseline_df
        )
        all_warnings.extend(runtime_warnings)
        progress_bar.progress(1.0)

    if not show_warnings:
        for r in results:
            if r.status == "WARNING":
                r.status = "PASS"

    summary_df = pd.DataFrame([r.__dict__ for r in results])

    st.session_state.update({
        "validated":          True,
        "summary_df":         summary_df,
        "df":                 df,
        "baseline_df":        baseline_df,
        "time_col":           time_col,
        "test_metadata":      metadata,
        "config_df":          config_df,
        "match_report":       match_report,
        "validation_warnings": all_warnings,
    })

    status_text.success(
        f"✅ Validated {len(results)} parameters from "
        f"{metadata.get('total_datapoints',0):,} data points!"
    )
    st.rerun()

# ==========================================================
# RESULTS DISPLAY
# ==========================================================
if st.session_state.validated and st.session_state.summary_df is not None:

    summary_df   = st.session_state.summary_df
    df           = st.session_state.df
    baseline_df  = st.session_state.baseline_df
    time_col     = st.session_state.time_col
    metadata     = st.session_state.test_metadata
    match_report = st.session_state.match_report
    test_type    = st.session_state.selected_test_type
    all_warnings = st.session_state.validation_warnings

    total    = len(summary_df)
    fails    = (summary_df["status"] == "FAIL").sum()
    warns    = (summary_df["status"] == "WARNING").sum()
    passes   = (summary_df["status"] == "PASS").sum()
    pass_rate = passes / total * 100 if total > 0 else 0

    if all_warnings:
        with st.expander(f"⚠️ {len(all_warnings)} Runtime Warnings (click to expand)", expanded=False):
            for w in all_warnings:
                st.markdown(f"<div class='warning-box'>⚠️ {w}</div>", unsafe_allow_html=True)

    if len(match_report.in_config_not_data) > 0 or len(match_report.in_data_not_config) > 0:
        with st.expander("🔗 Parameter Match Report", expanded=match_report.match_rate < 80):
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Matched", len(match_report.matched))
            mc2.metric("Match Rate", f"{match_report.match_rate:.1f}%")
            mc3.metric("Only in Data (unvalidated)", len(match_report.in_data_not_config))
            mc4.metric("Only in Config (missing from data)", len(match_report.in_config_not_data))

        if match_report.in_config_not_data:
            st.markdown(f"<div class='warning-box'>Parameters in config but absent from data "
                        f"({len(match_report.in_config_not_data)}): "
                        f"{', '.join(match_report.in_config_not_data[:20])}"
                        f"{'...' if len(match_report.in_config_not_data)>20 else ''}</div>",
                        unsafe_allow_html=True)
        if match_report.in_data_not_config:
            st.markdown(f"<div class='warning-box'>Parameters in data but not in config — skipped "
                        f"({len(match_report.in_data_not_config)}): "
                        f"{', '.join(match_report.in_data_not_config[:20])}"
                        f"{'...' if len(match_report.in_data_not_config)>20 else ''}</div>",
                        unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown('<div class="section-header">📋 Test Information</div>', unsafe_allow_html=True)
    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    cards = [
        (mc1, "TEST TYPE", metadata.get("selected_type","N/A"), ""),
        (mc2, "DETECTED FREQ", f"{metadata.get('detected_freq_hz','N/A')} Hz", ""),
        (mc3, "DURATION", f"{int(metadata.get('duration',0))}s", f"{metadata.get('duration',0)/60:.1f} min"),
        (mc4, "SENSORS IN DATA", str(metadata.get("total_sensors","N/A")), f"{len(match_report.matched)} validated"),
        (mc5, "DATA POINTS", f"{metadata.get('total_datapoints',0):,}", ""),
    ]
    for col, label, value, sub in cards:
        col.markdown(f"""
        <div class='metric-card'>
            <div class='label'>{label}</div>
            <div class='value'>{value}</div>
            <div class='sub'>{sub}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown('<div class="section-header">📊 Validation Dashboard</div>', unsafe_allow_html=True)

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Validated", total)
    k2.metric("✅ PASS",    passes, delta=f"{pass_rate:.1f}%")
    k3.metric("⚠️ WARNING", warns)
    k4.metric("❌ FAIL",    fails)
    k5.metric("Avg CV%", f"{summary_df['cv_pct'].mean():.1f}%")

    ch1, ch2 = st.columns([1, 2])

    with ch1:
        fig_pie = px.pie(
            values=[passes, warns, fails],
            names=["PASS", "WARNING", "FAIL"],
            color_discrete_map={"PASS": SUCCESS, "WARNING": WARNING, "FAIL": DANGER},
            title="Status Distribution", hole=0.4
        )
        fig_pie.update_layout(
            height=300,
            title_font=PLOT_TITLE_FONT,
            font=PLOT_FONT,
            paper_bgcolor=WHITE,
            plot_bgcolor=WHITE,
            margin=dict(t=40, b=10, l=10, r=10),
            legend=dict(font=dict(color=DARK_NAVY)),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with ch2:
        cat_stats = summary_df.groupby("category").agg(
            Pass_Rate=("status", lambda x: (x=="PASS").sum()/len(x)*100),
            Count=("name","count")
        ).reset_index().sort_values("Pass_Rate")

        fig_bar = px.bar(
            cat_stats, y="category", x="Pass_Rate", orientation="h",
            color="Pass_Rate",
            color_continuous_scale=[[0, DANGER],[0.5, WARNING],[1, SUCCESS]],
            range_color=[0,100], title="Pass Rate by Sensor Category",
            text="Count",
            labels={"Pass_Rate":"Pass Rate %","category":""}
        )
        fig_bar.update_layout(
            height=300, showlegend=False,
            xaxis_title="Pass Rate (%)",
            title_font=PLOT_TITLE_FONT,
            font=PLOT_FONT,
            paper_bgcolor=WHITE,
            plot_bgcolor="#f8faff",
            margin=dict(t=40, b=10, l=10, r=10),
        )
        fig_bar.update_xaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
        fig_bar.update_yaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
        fig_bar.update_traces(texttemplate="%{text}", textposition="outside",
                              textfont=dict(color=DARK_NAVY))
        st.plotly_chart(fig_bar, use_container_width=True)

    fig_cv = px.histogram(
        summary_df, x="cv_pct", nbins=40,
        title="CV% Distribution — Sensor Stability Profile",
        labels={"cv_pct": "Coefficient of Variation (%)"},
        color_discrete_sequence=[NAVY]
    )
    fig_cv.update_layout(
        height=260,
        title_font=PLOT_TITLE_FONT,
        font=PLOT_FONT,
        paper_bgcolor=WHITE,
        plot_bgcolor="#f8faff",
        margin=dict(t=40,b=30,l=30,r=10),
    )
    fig_cv.update_xaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
    fig_cv.update_yaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
    fig_cv.add_vline(x=summary_df["cv_pct"].mean(), line_dash="dash",
                     line_color=DANGER,
                     annotation_text="Mean CV",
                     annotation_font_color=DARK_NAVY)
    st.plotly_chart(fig_cv, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if fails > 0 or warns > 0:
        st.markdown('<div class="section-header">⚠️ Parameters Requiring Attention</div>', unsafe_allow_html=True)
        attn = summary_df[summary_df["status"].isin(["FAIL","WARNING"])].sort_values("violation_percent", ascending=False)
        st.markdown("<div class='info-panel'><h4 style='color:#c0392b !important;-webkit-text-fill-color:#c0392b !important;'>🔍 Top Issues</h4>", unsafe_allow_html=True)
        for _, r in attn.head(8).iterrows():
            tag_cls = f"tag-{r['status']}"
            st.markdown(
                f"<p style='margin:4px 0;color:#2c3e6b;'>"
                f"<span class='tag {tag_cls}'>{r['status']}</span> &nbsp;"
                f"<strong>{r['name']}</strong> ({r['category']}) — "
                f"{r['violation_percent']*100:.1f}% violations &nbsp;|&nbsp; "
                f"CV: {r['cv_pct']:.1f}%</p>",
                unsafe_allow_html=True
            )
        st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================================
    # VISUALIZATIONS TAB SECTION
    # ==========================================================
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">📈 Analysis & Visualizations</div>', unsafe_allow_html=True)

    all_params = [c for c in df.columns if c != time_col]
    validated_params = summary_df["name"].tolist()

    viz_tabs = st.tabs([
        "⏱ Time Series",
        "🔄 A vs B Comparison",
        "📊 Statistical Plots",
        "🌡 Heatmaps",
        "📡 Frequency (FFT)",
        "🔗 Correlation",
        "📋 Parameter Table",
    ])

    # ──────────────────────────────────
    # TAB 1 — TIME SERIES
    # ──────────────────────────────────
    with viz_tabs[0]:
        st.markdown("**Multi-sensor time series. Select up to 6 sensors.**")
        ts_col1, ts_col2, ts_col3 = st.columns([3,1,1])
        with ts_col1:
            default_ts = summary_df[summary_df["status"].isin(["FAIL","WARNING"])]["name"].head(3).tolist()
            sel_ts = st.multiselect("Select Sensors", all_params, default=default_ts[:3], max_selections=6, key="ts_sel")
        with ts_col2:
            ts_style = st.selectbox("Layout", ["Stacked Subplots","Overlaid"], key="ts_style")
        with ts_col3:
            show_limits = st.checkbox("Show Min/Max Limits", value=True, key="ts_limits")
            show_bl     = st.checkbox("Show Baseline", value=baseline_df is not None, disabled=baseline_df is None, key="ts_bl")

        if sel_ts:
            if ts_style == "Stacked Subplots":
                n = len(sel_ts)
                fig_ts = make_subplots(rows=n, cols=1, shared_xaxes=True,
                                       vertical_spacing=0.04,
                                       subplot_titles=sel_ts)
                for i, sensor in enumerate(sel_ts, 1):
                    color = CHART_COLORS[(i-1) % len(CHART_COLORS)]
                    fig_ts.add_trace(go.Scatter(
                        x=df[time_col], y=df[sensor], mode="lines",
                        name=sensor, line=dict(color=color, width=1.5)
                    ), row=i, col=1)

                    if show_bl and baseline_df is not None and sensor in baseline_df.columns:
                        btc = detect_time_col(baseline_df)
                        fig_ts.add_trace(go.Scatter(
                            x=baseline_df[btc], y=baseline_df[sensor], mode="lines",
                            name=f"Baseline:{sensor}", line=dict(color=WARNING, width=1, dash="dash")
                        ), row=i, col=1)

                    if show_limits:
                        sr = summary_df[summary_df["name"]==sensor]
                        if not sr.empty:
                            r = sr.iloc[0]
                            if pd.notna(r.get("config_min")):
                                fig_ts.add_hline(y=r["config_min"], line_dash="dot", line_color=DANGER,
                                                 line_width=1, row=i, col=1)
                            if pd.notna(r.get("config_max")):
                                fig_ts.add_hline(y=r["config_max"], line_dash="dot", line_color=DANGER,
                                                 line_width=1, row=i, col=1)
                            if pd.notna(r.get("config_warn_low")):
                                fig_ts.add_hline(y=r["config_warn_low"], line_dash="dot", line_color=WARNING,
                                                 line_width=1, row=i, col=1)
                            if pd.notna(r.get("config_warn_high")):
                                fig_ts.add_hline(y=r["config_warn_high"], line_dash="dot", line_color=WARNING,
                                                 line_width=1, row=i, col=1)

                    unit_lbl = summary_df[summary_df["name"]==sensor]["unit"].values
                    if len(unit_lbl):
                        fig_ts.update_yaxes(title_text=unit_lbl[0],
                                            title_font=PLOT_AXIS_FONT,
                                            tickfont=PLOT_TICK_FONT,
                                            row=i, col=1)

                fig_ts.update_xaxes(title_text="Time (s)", title_font=PLOT_AXIS_FONT,
                                    tickfont=PLOT_TICK_FONT, row=n, col=1)
                fig_ts.update_layout(
                    height=260*n,
                    font=PLOT_FONT,
                    hovermode="x unified",
                    paper_bgcolor=WHITE,
                    plot_bgcolor="#f8faff",
                    showlegend=False,
                )
                # Fix subplot title colors
                for ann in fig_ts.layout.annotations:
                    ann.font = dict(color=DARK_NAVY, size=12)
                st.plotly_chart(fig_ts, use_container_width=True)

            else:  # Overlaid
                fig_ov = go.Figure()
                for i, sensor in enumerate(sel_ts):
                    fig_ov.add_trace(go.Scatter(
                        x=df[time_col], y=df[sensor], mode="lines",
                        name=sensor, line=dict(width=1.8, color=CHART_COLORS[i % len(CHART_COLORS)])
                    ))
                    if show_bl and baseline_df is not None and sensor in baseline_df.columns:
                        btc = detect_time_col(baseline_df)
                        fig_ov.add_trace(go.Scatter(
                            x=baseline_df[btc], y=baseline_df[sensor], mode="lines",
                            name=f"BL:{sensor}", line=dict(width=1, dash="dash",
                                                            color=CHART_COLORS[i % len(CHART_COLORS)])
                        ))
                fig_ov.update_layout(
                    height=480,
                    font=PLOT_FONT,
                    xaxis_title="Time (s)",
                    yaxis_title="Value",
                    hovermode="x unified",
                    paper_bgcolor=WHITE,
                    plot_bgcolor="#f8faff",
                    legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.01,
                                font=dict(color=DARK_NAVY)),
                )
                fig_ov.update_xaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                fig_ov.update_yaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                st.plotly_chart(fig_ov, use_container_width=True)
        else:
            st.info("ℹ️ Select at least one sensor to plot.")

    # ──────────────────────────────────
    # TAB 2 — A vs B COMPARISON
    # ──────────────────────────────────
    with viz_tabs[1]:
        st.markdown("**Side-by-side deep comparison of two parameters over time.**")
        ab1, ab2, ab3 = st.columns([2,2,2])
        with ab1:
            param_a = st.selectbox("Parameter A", all_params, index=0, key="ab_a")
        with ab2:
            param_b = st.selectbox("Parameter B", all_params,
                                    index=min(1, len(all_params)-1), key="ab_b")
        with ab3:
            ab_mode = st.selectbox("View Mode", [
                "Dual Time Series", "Scatter (A vs B)", "Dual + Difference",
                "Normalized Overlay", "Rolling Mean Comparison"
            ], key="ab_mode")

        if param_a and param_b and param_a != param_b:
            s_a = pd.to_numeric(df[param_a], errors="coerce").ffill().bfill()
            s_b = pd.to_numeric(df[param_b], errors="coerce").ffill().bfill()
            t   = df[time_col]

            if ab_mode == "Dual Time Series":
                fig_ab = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                       vertical_spacing=0.06,
                                       subplot_titles=[param_a, param_b])
                fig_ab.add_trace(go.Scatter(x=t, y=s_a, mode="lines", name=param_a,
                                            line=dict(color=NAVY, width=1.8)), row=1, col=1)
                fig_ab.add_trace(go.Scatter(x=t, y=s_b, mode="lines", name=param_b,
                                            line=dict(color=DANGER, width=1.8)), row=2, col=1)
                fig_ab.update_xaxes(title_text="Time (s)", title_font=PLOT_AXIS_FONT,
                                    tickfont=PLOT_TICK_FONT, row=2, col=1)
                fig_ab.update_yaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                fig_ab.update_layout(height=500, font=PLOT_FONT,
                                     paper_bgcolor=WHITE, plot_bgcolor="#f8faff",
                                     hovermode="x unified")
                for ann in fig_ab.layout.annotations:
                    ann.font = dict(color=DARK_NAVY, size=12)
                st.plotly_chart(fig_ab, use_container_width=True)

            elif ab_mode == "Scatter (A vs B)":
                t_norm = (t - t.min()) / (t.max() - t.min() + 1e-9)
                fig_sc = go.Figure(go.Scatter(
                    x=s_a, y=s_b, mode="markers",
                    marker=dict(color=t_norm, colorscale="Blues",
                                size=3, opacity=0.7,
                                colorbar=dict(title="Time →",
                                              title_font=dict(color=DARK_NAVY),
                                              tickfont=dict(color=DARK_NAVY))),
                    name="A vs B"
                ))
                try:
                    mask = s_a.notna() & s_b.notna()
                    slope, intercept, r, p, _ = scipy_stats.linregress(s_a[mask], s_b[mask])
                    x_line = np.array([s_a.min(), s_a.max()])
                    fig_sc.add_trace(go.Scatter(
                        x=x_line, y=slope*x_line+intercept,
                        mode="lines", name=f"Regression (R²={r**2:.3f})",
                        line=dict(color=DANGER, width=2, dash="dash")
                    ))
                    st.info(f"📐 Correlation R² = {r**2:.4f} | Slope = {slope:.4f} | p = {p:.4e}")
                except Exception:
                    pass
                fig_sc.update_layout(
                    xaxis_title=param_a, yaxis_title=param_b,
                    height=480, font=PLOT_FONT,
                    paper_bgcolor=WHITE, plot_bgcolor="#f8faff",
                    legend=dict(font=dict(color=DARK_NAVY)),
                )
                fig_sc.update_xaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                fig_sc.update_yaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                st.plotly_chart(fig_sc, use_container_width=True)

            elif ab_mode == "Dual + Difference":
                diff = s_a.values - s_b.values
                fig_d = make_subplots(rows=3, cols=1, shared_xaxes=True,
                                      vertical_spacing=0.05,
                                      subplot_titles=[param_a, param_b, "A − B (Difference)"])
                fig_d.add_trace(go.Scatter(x=t, y=s_a, mode="lines", name=param_a,
                                           line=dict(color=NAVY, width=1.5)), row=1, col=1)
                fig_d.add_trace(go.Scatter(x=t, y=s_b, mode="lines", name=param_b,
                                           line=dict(color=DANGER, width=1.5)), row=2, col=1)
                fig_d.add_trace(go.Scatter(x=t, y=diff, mode="lines", name="Difference",
                                           fill="tozeroy",
                                           line=dict(color=SUCCESS, width=1.2)), row=3, col=1)
                fig_d.add_hline(y=0, line_dash="dash", line_color=MUTED, row=3, col=1)
                fig_d.update_xaxes(title_text="Time (s)", title_font=PLOT_AXIS_FONT,
                                   tickfont=PLOT_TICK_FONT, row=3, col=1)
                fig_d.update_yaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                fig_d.update_layout(height=600, font=PLOT_FONT,
                                    paper_bgcolor=WHITE, plot_bgcolor="#f8faff",
                                    hovermode="x unified")
                for ann in fig_d.layout.annotations:
                    ann.font = dict(color=DARK_NAVY, size=12)
                st.plotly_chart(fig_d, use_container_width=True)

            elif ab_mode == "Normalized Overlay":
                def normalize(s):
                    mn, mx = s.min(), s.max()
                    return (s - mn) / (mx - mn + 1e-9) if mx > mn else s - mn
                fig_no = go.Figure()
                fig_no.add_trace(go.Scatter(x=t, y=normalize(s_a), mode="lines", name=f"{param_a} (norm)",
                                            line=dict(color=NAVY, width=1.8)))
                fig_no.add_trace(go.Scatter(x=t, y=normalize(s_b), mode="lines", name=f"{param_b} (norm)",
                                            line=dict(color=DANGER, width=1.8)))
                fig_no.update_layout(
                    xaxis_title="Time (s)", yaxis_title="Normalized Value [0–1]",
                    height=420, font=PLOT_FONT,
                    paper_bgcolor=WHITE, plot_bgcolor="#f8faff",
                    hovermode="x unified",
                    legend=dict(font=dict(color=DARK_NAVY)),
                )
                fig_no.update_xaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                fig_no.update_yaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                st.plotly_chart(fig_no, use_container_width=True)
                st.caption("Both signals normalized to [0,1] for shape comparison regardless of unit/scale.")

            elif ab_mode == "Rolling Mean Comparison":
                win = st.slider("Rolling Window (samples)", 10, 500, 50, key="ab_roll")
                rm_a = s_a.rolling(win, center=True).mean()
                rm_b = s_b.rolling(win, center=True).mean()
                fig_rm = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                                       subplot_titles=[param_a, param_b])
                for row_i, (raw, roll, color, label) in enumerate([
                    (s_a, rm_a, NAVY, param_a),
                    (s_b, rm_b, DANGER, param_b)
                ], 1):
                    fig_rm.add_trace(go.Scatter(x=t, y=raw, mode="lines", name=f"{label} raw",
                                                line=dict(color=color, width=1, opacity=0.4),
                                                opacity=0.4), row=row_i, col=1)
                    fig_rm.add_trace(go.Scatter(x=t, y=roll, mode="lines", name=f"{label} rolling mean",
                                                line=dict(color=color, width=2.2)), row=row_i, col=1)
                fig_rm.update_xaxes(title_text="Time (s)", title_font=PLOT_AXIS_FONT,
                                    tickfont=PLOT_TICK_FONT, row=2, col=1)
                fig_rm.update_yaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                fig_rm.update_layout(height=520, font=PLOT_FONT,
                                     paper_bgcolor=WHITE, plot_bgcolor="#f8faff",
                                     hovermode="x unified")
                for ann in fig_rm.layout.annotations:
                    ann.font = dict(color=DARK_NAVY, size=12)
                st.plotly_chart(fig_rm, use_container_width=True)
        else:
            st.info("ℹ️ Select two different parameters to compare.")

    # ──────────────────────────────────
    # TAB 3 — STATISTICAL PLOTS
    # ──────────────────────────────────
    with viz_tabs[2]:
        st.markdown("**Distribution and statistical analysis of individual sensors.**")
        sp1, sp2 = st.columns([3,1])
        with sp1:
            stat_sensors = st.multiselect("Select Sensors (up to 5)", all_params,
                                           default=validated_params[:3], max_selections=5, key="stat_sel")
        with sp2:
            stat_plot = st.selectbox("Plot Type", [
                "Histogram + KDE", "Box Plot", "Violin Plot",
                "CDF (Cumulative Distribution)", "Q-Q Plot"
            ], key="stat_plot")

        if stat_sensors:
            if stat_plot == "Histogram + KDE":
                fig_h = go.Figure()
                for i, sensor in enumerate(stat_sensors):
                    vals = pd.to_numeric(df[sensor], errors="coerce").dropna()
                    color = CHART_COLORS[i % len(CHART_COLORS)]
                    fig_h.add_trace(go.Histogram(
                        x=vals, name=sensor, opacity=0.6,
                        marker_color=color, nbinsx=50,
                        histnorm="probability density"
                    ))
                    try:
                        kde = scipy_stats.gaussian_kde(vals)
                        x_kde = np.linspace(vals.min(), vals.max(), 300)
                        fig_h.add_trace(go.Scatter(
                            x=x_kde, y=kde(x_kde), mode="lines",
                            name=f"{sensor} KDE", line=dict(color=color, width=2.5)
                        ))
                    except Exception:
                        pass
                fig_h.update_layout(
                    barmode="overlay",
                    xaxis_title="Value", yaxis_title="Density",
                    height=440, font=PLOT_FONT,
                    paper_bgcolor=WHITE, plot_bgcolor="#f8faff",
                    title="Histogram + KDE — Probability Density",
                    title_font=PLOT_TITLE_FONT,
                    legend=dict(font=dict(color=DARK_NAVY)),
                )
                fig_h.update_xaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                fig_h.update_yaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                st.plotly_chart(fig_h, use_container_width=True)

            elif stat_plot == "Box Plot":
                data_box = []
                for sensor in stat_sensors:
                    vals = pd.to_numeric(df[sensor], errors="coerce").dropna()
                    data_box.append(go.Box(y=vals, name=sensor, boxmean="sd",
                                           marker_color=CHART_COLORS[stat_sensors.index(sensor) % len(CHART_COLORS)]))
                fig_box = go.Figure(data=data_box)
                fig_box.update_layout(
                    height=440,
                    yaxis_title="Value",
                    font=PLOT_FONT,
                    paper_bgcolor=WHITE, plot_bgcolor="#f8faff",
                    title="Box Plot (with mean ± std)",
                    title_font=PLOT_TITLE_FONT,
                    legend=dict(font=dict(color=DARK_NAVY)),
                )
                fig_box.update_xaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                fig_box.update_yaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                st.plotly_chart(fig_box, use_container_width=True)

            elif stat_plot == "Violin Plot":
                data_vl = []
                for i, sensor in enumerate(stat_sensors):
                    vals = pd.to_numeric(df[sensor], errors="coerce").dropna()
                    data_vl.append(go.Violin(
                        y=vals, name=sensor, box_visible=True,
                        meanline_visible=True,
                        fillcolor=CHART_COLORS[i % len(CHART_COLORS)],
                        line_color=DARK_NAVY, opacity=0.7
                    ))
                fig_vl = go.Figure(data=data_vl)
                fig_vl.update_layout(
                    height=460,
                    yaxis_title="Value",
                    font=PLOT_FONT,
                    paper_bgcolor=WHITE, plot_bgcolor="#f8faff",
                    title="Violin Plot — Full Distribution Shape",
                    title_font=PLOT_TITLE_FONT,
                    legend=dict(font=dict(color=DARK_NAVY)),
                )
                fig_vl.update_xaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                fig_vl.update_yaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                st.plotly_chart(fig_vl, use_container_width=True)

            elif stat_plot == "CDF (Cumulative Distribution)":
                fig_cdf = go.Figure()
                for i, sensor in enumerate(stat_sensors):
                    vals = pd.to_numeric(df[sensor], errors="coerce").dropna().sort_values()
                    cdf  = np.arange(1, len(vals)+1) / len(vals)
                    fig_cdf.add_trace(go.Scatter(
                        x=vals, y=cdf, mode="lines", name=sensor,
                        line=dict(color=CHART_COLORS[i % len(CHART_COLORS)], width=2)
                    ))
                fig_cdf.update_layout(
                    xaxis_title="Value", yaxis_title="Cumulative Probability",
                    height=440, font=PLOT_FONT,
                    paper_bgcolor=WHITE, plot_bgcolor="#f8faff",
                    title="CDF — Cumulative Distribution Function",
                    title_font=PLOT_TITLE_FONT,
                    hovermode="x unified",
                    legend=dict(font=dict(color=DARK_NAVY)),
                )
                fig_cdf.update_xaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                fig_cdf.update_yaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                st.plotly_chart(fig_cdf, use_container_width=True)

            elif stat_plot == "Q-Q Plot":
                sensor = stat_sensors[0]
                if len(stat_sensors) > 1:
                    st.info("Q-Q Plot shows one sensor at a time — using first selection.")
                vals = pd.to_numeric(df[sensor], errors="coerce").dropna()
                try:
                    osm, osr = scipy_stats.probplot(vals, dist="norm")
                    fig_qq = go.Figure()
                    fig_qq.add_trace(go.Scatter(
                        x=osm[0], y=osm[1], mode="markers", name=sensor,
                        marker=dict(color=NAVY, size=4, opacity=0.6)
                    ))
                    fig_qq.add_trace(go.Scatter(
                        x=[osm[0][0], osm[0][-1]],
                        y=[osr[1] + osr[0]*osm[0][0], osr[1] + osr[0]*osm[0][-1]],
                        mode="lines", name="Normal Ref.",
                        line=dict(color=DANGER, width=2, dash="dash")
                    ))
                    fig_qq.update_layout(
                        xaxis_title="Theoretical Quantiles",
                        yaxis_title="Sample Quantiles",
                        height=440, font=PLOT_FONT,
                        paper_bgcolor=WHITE, plot_bgcolor="#f8faff",
                        title=f"Q-Q Plot — {sensor} vs Normal Distribution",
                        title_font=PLOT_TITLE_FONT,
                        legend=dict(font=dict(color=DARK_NAVY)),
                    )
                    fig_qq.update_xaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                    fig_qq.update_yaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                    st.plotly_chart(fig_qq, use_container_width=True)
                    _, p_sw = scipy_stats.shapiro(vals[:5000])
                    if p_sw > 0.05:
                        st.markdown(f"<div class='success-box'>Shapiro-Wilk test p={p_sw:.4f} — data appears normally distributed.</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='warning-box'>Shapiro-Wilk test p={p_sw:.4f} — data deviates from normal distribution.</div>", unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Q-Q plot failed: {e}")
        else:
            st.info("ℹ️ Select at least one sensor.")

    # ──────────────────────────────────
    # TAB 4 — HEATMAPS
    # ──────────────────────────────────
    with viz_tabs[3]:
        hm1, hm2 = st.columns([3,1])
        with hm1:
            hm_mode = st.selectbox("Heatmap Type", [
                "Violation Heatmap (by Category)",
                "CV% Heatmap (Sensor Stability)",
                "Time-binned Signal Heatmap",
                "Missing Data Map",
            ], key="hm_mode")
        with hm2:
            hm_top_n = st.slider("Top N sensors", 20, 100, 40, key="hm_topn")

        if hm_mode == "Violation Heatmap (by Category)":
            top = summary_df.nlargest(hm_top_n, "violation_percent")
            fig_hm = px.bar(
                top, x="violation_percent", y="name", orientation="h",
                color="violation_percent",
                color_continuous_scale=[[0,SUCCESS],[0.05,WARNING],[0.2,DANGER]],
                title=f"Top {hm_top_n} Parameters by Violation %",
                labels={"violation_percent":"Violation %","name":"Parameter"}
            )
            fig_hm.update_layout(height=max(400, hm_top_n*16),
                                  font=PLOT_FONT, paper_bgcolor=WHITE,
                                  title_font=PLOT_TITLE_FONT)
            fig_hm.update_xaxes(tickformat=".1%", title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
            fig_hm.update_yaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
            st.plotly_chart(fig_hm, use_container_width=True)

        elif hm_mode == "CV% Heatmap (Sensor Stability)":
            top_cv = summary_df.nlargest(hm_top_n, "cv_pct")
            fig_cv_hm = px.bar(
                top_cv, x="cv_pct", y="name", orientation="h",
                color="cv_pct",
                color_continuous_scale=[[0,SUCCESS],[0.5,WARNING],[1,DANGER]],
                title=f"Top {hm_top_n} Most Variable Sensors (CV%)",
                labels={"cv_pct":"CV (%)","name":"Parameter"}
            )
            fig_cv_hm.update_layout(height=max(400, hm_top_n*16),
                                     font=PLOT_FONT, paper_bgcolor=WHITE,
                                     title_font=PLOT_TITLE_FONT)
            fig_cv_hm.update_xaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
            fig_cv_hm.update_yaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
            st.plotly_chart(fig_cv_hm, use_container_width=True)

        elif hm_mode == "Time-binned Signal Heatmap":
            hm_sensor = st.selectbox("Select Sensor", validated_params[:min(30, len(validated_params))], key="hm_sensor")
            n_bins = st.slider("Time bins", 20, 200, 50, key="hm_bins")
            try:
                vals = pd.to_numeric(df[hm_sensor], errors="coerce")
                t_arr = df[time_col]
                bin_edges = np.linspace(t_arr.min(), t_arr.max(), n_bins+1)
                bin_labels = [f"{b:.0f}s" for b in bin_edges[:-1]]
                binned = pd.cut(t_arr, bins=bin_edges, labels=bin_labels)
                means  = vals.groupby(binned).mean().values.reshape(1, -1)

                fig_tb = go.Figure(go.Heatmap(
                    z=means, x=bin_labels, y=[hm_sensor],
                    colorscale="RdBu_r",
                    colorbar=dict(title="Mean Value",
                                  title_font=dict(color=DARK_NAVY),
                                  tickfont=dict(color=DARK_NAVY))
                ))
                fig_tb.update_layout(
                    title=f"Time-binned Mean — {hm_sensor}",
                    xaxis_title="Time bin", height=280,
                    font=PLOT_FONT, paper_bgcolor=WHITE,
                    title_font=PLOT_TITLE_FONT,
                )
                fig_tb.update_xaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                fig_tb.update_yaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                st.plotly_chart(fig_tb, use_container_width=True)
            except Exception as e:
                st.error(f"Could not generate heatmap: {e}")

        elif hm_mode == "Missing Data Map":
            top_miss = summary_df.nlargest(hm_top_n, "missing_percent")
            if top_miss["missing_percent"].max() == 0:
                st.success("✅ No missing data detected in any validated parameter.")
            else:
                fig_miss = px.bar(
                    top_miss[top_miss["missing_percent"] > 0],
                    x="missing_percent", y="name", orientation="h",
                    color="missing_percent",
                    color_continuous_scale=[[0,SUCCESS],[0.1,WARNING],[0.5,DANGER]],
                    title="Missing Data by Parameter",
                    labels={"missing_percent":"Missing %","name":"Parameter"}
                )
                fig_miss.update_layout(height=max(300, len(top_miss)*16),
                                        font=PLOT_FONT, paper_bgcolor=WHITE,
                                        title_font=PLOT_TITLE_FONT)
                fig_miss.update_xaxes(tickformat=".1%", title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                fig_miss.update_yaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                st.plotly_chart(fig_miss, use_container_width=True)

    # ──────────────────────────────────
    # TAB 5 — FREQUENCY / FFT
    # ──────────────────────────────────
    with viz_tabs[4]:
        st.markdown("**Frequency domain analysis — identify periodic patterns and noise.**")
        fft1, fft2 = st.columns([3,1])
        with fft1:
            fft_sensors = st.multiselect("Select Sensors (up to 4)", all_params,
                                          default=validated_params[:2], max_selections=4, key="fft_sel")
        with fft2:
            fft_mode = st.selectbox("FFT Mode", ["Power Spectrum", "Spectrogram"], key="fft_mode")
            fft_log  = st.checkbox("Log Y-axis", value=True, key="fft_log")

        if fft_sensors:
            freq_hz = metadata.get("detected_freq_hz") or 1.0
            if fft_mode == "Power Spectrum":
                fig_fft = go.Figure()
                for i, sensor in enumerate(fft_sensors):
                    try:
                        vals = pd.to_numeric(df[sensor], errors="coerce").ffill().bfill().dropna().values
                        n    = len(vals)
                        fft_vals  = np.abs(np.fft.rfft(vals - vals.mean())) ** 2
                        freq_bins = np.fft.rfftfreq(n, d=1.0/freq_hz)
                        fig_fft.add_trace(go.Scatter(
                            x=freq_bins[1:], y=fft_vals[1:],
                            mode="lines", name=sensor,
                            line=dict(color=CHART_COLORS[i % len(CHART_COLORS)], width=1.5)
                        ))
                    except Exception as e:
                        st.warning(f"FFT failed for {sensor}: {e}")

                fig_fft.update_layout(
                    xaxis_title="Frequency (Hz)", yaxis_title="Power Spectral Density",
                    yaxis_type="log" if fft_log else "linear",
                    height=460, font=PLOT_FONT,
                    paper_bgcolor=WHITE, plot_bgcolor="#f8faff",
                    hovermode="x unified",
                    title="Power Spectrum (FFT)",
                    title_font=PLOT_TITLE_FONT,
                    legend=dict(font=dict(color=DARK_NAVY)),
                )
                fig_fft.update_xaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                fig_fft.update_yaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                st.plotly_chart(fig_fft, use_container_width=True)
                st.caption(f"Sampling frequency: {freq_hz} Hz. Dominant frequencies indicate periodic engine events.")

            else:  # Spectrogram
                sensor_sg = fft_sensors[0]
                if len(fft_sensors) > 1:
                    st.info("Spectrogram shows one sensor — using first selection.")
                try:
                    from scipy.signal import spectrogram as sp_spectrogram
                    vals = pd.to_numeric(df[sensor_sg], errors="coerce").ffill().bfill().dropna().values
                    f_sg, t_sg, Sxx = sp_spectrogram(vals, fs=freq_hz, nperseg=min(256, len(vals)//4))
                    fig_sg = go.Figure(go.Heatmap(
                        x=t_sg, y=f_sg, z=10*np.log10(Sxx + 1e-10),
                        colorscale="Viridis",
                        colorbar=dict(title="dB",
                                      title_font=dict(color=DARK_NAVY),
                                      tickfont=dict(color=DARK_NAVY))
                    ))
                    fig_sg.update_layout(
                        xaxis_title="Time (s)", yaxis_title="Frequency (Hz)",
                        title=f"Spectrogram — {sensor_sg}",
                        title_font=PLOT_TITLE_FONT,
                        height=420, font=PLOT_FONT, paper_bgcolor=WHITE,
                    )
                    fig_sg.update_xaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                    fig_sg.update_yaxes(title_font=PLOT_AXIS_FONT, tickfont=PLOT_TICK_FONT)
                    st.plotly_chart(fig_sg, use_container_width=True)
                except Exception as e:
                    st.error(f"Spectrogram failed: {e}")
        else:
            st.info("ℹ️ Select at least one sensor.")

    # ──────────────────────────────────
    # TAB 6 — CORRELATION
    # ──────────────────────────────────
    with viz_tabs[5]:
        st.markdown("**Cross-sensor correlation matrix and scatter pairs.**")
        cc1, cc2 = st.columns([3,1])
        with cc1:
            corr_sensors = st.multiselect(
                "Select Sensors (5–15 for best matrix)", all_params,
                default=validated_params[:min(8, len(validated_params))],
                max_selections=15, key="corr_sel"
            )
        with cc2:
            corr_method = st.selectbox("Method", ["pearson","spearman","kendall"], key="corr_method")

        if len(corr_sensors) >= 2:
            try:
                corr_data = df[corr_sensors].apply(pd.to_numeric, errors="coerce")
                corr_mat  = corr_data.corr(method=corr_method)

                fig_corr = go.Figure(go.Heatmap(
                    z=corr_mat.values,
                    x=corr_mat.columns.tolist(),
                    y=corr_mat.index.tolist(),
                    colorscale="RdBu", zmin=-1, zmax=1,
                    text=corr_mat.round(2).values,
                    texttemplate="%{text}",
                    textfont=dict(color=DARK_NAVY),
                    colorbar=dict(title=f"{corr_method.title()} r",
                                  title_font=dict(color=DARK_NAVY),
                                  tickfont=dict(color=DARK_NAVY))
                ))
                n = len(corr_sensors)
                fig_corr.update_layout(
                    title=f"Correlation Matrix ({corr_method.title()})",
                    title_font=PLOT_TITLE_FONT,
                    height=max(400, n*50),
                    font=PLOT_FONT,
                    paper_bgcolor=WHITE,
                    xaxis=dict(tickangle=-35, tickfont=PLOT_TICK_FONT,
                               title_font=PLOT_AXIS_FONT),
                    yaxis=dict(tickfont=PLOT_TICK_FONT, title_font=PLOT_AXIS_FONT),
                )
                st.plotly_chart(fig_corr, use_container_width=True)

                corr_pairs = []
                for i in range(len(corr_mat)):
                    for j in range(i+1, len(corr_mat)):
                        corr_pairs.append({
                            "Parameter A": corr_mat.index[i],
                            "Parameter B": corr_mat.columns[j],
                            "Correlation": round(corr_mat.iloc[i,j], 4),
                            "Abs Correlation": abs(round(corr_mat.iloc[i,j], 4))
                        })
                pairs_df = pd.DataFrame(corr_pairs).sort_values("Abs Correlation", ascending=False)

                col_pairs1, col_pairs2 = st.columns(2)
                with col_pairs1:
                    st.markdown("**🔺 Top Positive Correlations**")
                    st.dataframe(
                        pairs_df[pairs_df["Correlation"] > 0].head(8)[["Parameter A","Parameter B","Correlation"]],
                        use_container_width=True, height=260
                    )
                with col_pairs2:
                    st.markdown("**🔻 Top Negative Correlations**")
                    st.dataframe(
                        pairs_df[pairs_df["Correlation"] < 0].head(8)[["Parameter A","Parameter B","Correlation"]],
                        use_container_width=True, height=260
                    )
            except Exception as e:
                st.error(f"Correlation analysis failed: {e}")
        else:
            st.info("ℹ️ Select at least 2 sensors for correlation analysis.")

    # ──────────────────────────────────
    # TAB 7 — PARAMETER TABLE
    # ──────────────────────────────────
    with viz_tabs[6]:
        ft1, ft2, ft3, ft4 = st.columns([2,2,2,1])
        with ft1:
            status_filter = st.multiselect("Status", ["FAIL","WARNING","PASS"],
                                            default=["FAIL","WARNING","PASS"], key="tbl_status")
        with ft2:
            cat_filter = st.multiselect("Category", sorted(summary_df["category"].unique()),
                                         default=[], key="tbl_cat")
        with ft3:
            search_q = st.text_input("Search parameter", placeholder="Type to filter...", key="tbl_srch")
        with ft4:
            sort_col = st.selectbox("Sort by", ["violation_percent","cv_pct","std","mean"], key="tbl_sort")

        disp = summary_df[summary_df["status"].isin(status_filter)].copy()
        if cat_filter:
            disp = disp[disp["category"].isin(cat_filter)]
        if search_q:
            disp = disp[disp["name"].str.contains(search_q, case=False, na=False)]
        disp = disp.sort_values(sort_col, ascending=False)

        show_cols = ["name","category","status","unit","mean","min_val","max_val",
                     "std","cv_pct","violations","violation_percent","missing_percent"]
        if baseline_df is not None:
            show_cols.append("baseline_delta")

        tbl = disp[[c for c in show_cols if c in disp.columns]].copy()
        tbl["violation_percent"] = (tbl["violation_percent"]*100).round(2).astype(str) + "%"
        tbl["missing_percent"]   = (tbl["missing_percent"]*100).round(2).astype(str) + "%"
        for c in ["mean","min_val","max_val","std","cv_pct"]:
            if c in tbl.columns:
                tbl[c] = tbl[c].round(3)

        st.dataframe(tbl, use_container_width=True, height=460)
        st.caption(f"Showing {len(tbl)} / {len(summary_df)} parameters")

    # ==========================================================
    # EXPORT
    # ==========================================================
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">💾 Export Results</div>', unsafe_allow_html=True)

    exp1, exp2, exp3, exp4, exp5 = st.columns(5)
    ts_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    with exp1:
        session_data = {
            "timestamp":   metadata.get("timestamp",""),
            "test_type":   test_type,
            "metadata":    metadata,
            "match_report": {
                "matched":             match_report.matched,
                "in_data_not_config":  match_report.in_data_not_config,
                "in_config_not_data":  match_report.in_config_not_data,
                "match_rate_pct":      round(match_report.match_rate, 2),
            },
            "summary":     summary_df.to_dict(orient="records"),
            "statistics":  {
                "total": int(total), "pass": int(passes),
                "warning": int(warns), "fail": int(fails),
                "pass_rate_pct": round(pass_rate, 2),
            }
        }
        st.download_button(
            "📥 JSON Report", json.dumps(session_data, indent=2, default=str),
            file_name=f"puma_{ts_stamp}.json", mime="application/json",
            use_container_width=True
        )

    with exp2:
        csv_buf = io.StringIO()
        summary_df.to_csv(csv_buf, index=False)
        st.download_button(
            "📥 CSV Summary", csv_buf.getvalue(),
            file_name=f"puma_summary_{ts_stamp}.csv", mime="text/csv",
            use_container_width=True
        )

    with exp3:
        xl_buf = io.BytesIO()
        with pd.ExcelWriter(xl_buf, engine="openpyxl") as writer:
            summary_df.to_excel(writer, sheet_name="Summary", index=False)
            cat_bkdn = summary_df.groupby(["category","status"]).size().unstack(fill_value=0)
            cat_bkdn.to_excel(writer, sheet_name="Category Breakdown")
            if fails > 0:
                summary_df[summary_df["status"]=="FAIL"].to_excel(
                    writer, sheet_name="Failed Parameters", index=False)
            if warns > 0:
                summary_df[summary_df["status"]=="WARNING"].to_excel(
                    writer, sheet_name="Warnings", index=False)
            pd.DataFrame({
                "matched":            [len(match_report.matched)],
                "in_data_not_config": [len(match_report.in_data_not_config)],
                "in_config_not_data": [len(match_report.in_config_not_data)],
                "match_rate_pct":     [round(match_report.match_rate,2)],
            }).to_excel(writer, sheet_name="Match Report", index=False)
        st.download_button(
            "📥 Excel Report", xl_buf.getvalue(),
            file_name=f"puma_report_{ts_stamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with exp4:
        issues_buf = io.StringIO()
        summary_df[summary_df["status"].isin(["FAIL","WARNING"])].to_csv(issues_buf, index=False)
        st.download_button(
            "📥 Issues CSV", issues_buf.getvalue(),
            file_name=f"puma_issues_{ts_stamp}.csv", mime="text/csv",
            use_container_width=True
        )

    with exp5:
        try:
            pdf_bytes = generate_pdf_report(summary_df, metadata, match_report, test_type)
            st.download_button(
                "📥 PDF Report", pdf_bytes,
                file_name=f"puma_report_{ts_stamp}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.button("📥 PDF Report", disabled=True, use_container_width=True,
                      help=f"PDF generation failed: {e}")
            st.caption(f"PDF error: {e}")

# ==========================================================
# FOOTER
# ==========================================================
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(f"""
<div style='text-align:center;color:{MUTED};padding:20px;border-top:1px solid #dce3f0;'>
    <p style='margin:0;color:#4a5578;font-weight:600;'>
        PUMA Analytics Pro v3.0 &nbsp;|&nbsp; Cummins Engineering</p>
    <p style='margin:4px 0 0 0;font-size:12px;color:{MUTED};'>
        Production-Grade Test Data Validation & Analysis Platform</p>
</div>""", unsafe_allow_html=True)