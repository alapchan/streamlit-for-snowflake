import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# ──────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG & CUSTOM CSS
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="❄️ Snowflake Credit Consumption Estimator",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.image("pwc_logo.jpg",width=800)

st.markdown("""
<style>
   
    /* ── Global Background ── */
    .main {
        background: linear-gradient(160deg, #1a1a1a 0%, #2D2D2D 40%, #1a1a1a 100%);
    }
    .block-container {
        padding-top: 2rem;
    }

    /* ── Sidebar — PwC Dark with Orange accent ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #2D2D2D 0%, #1a1a1a 100%);
        border-right: 3px solid #D04A02;
    }
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #D04A02 !important;
    }
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown li,
    [data-testid="stSidebar"] .stMarkdown label {
        color: #E0E0E0 !important;
    }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stSlider label,
    [data-testid="stSidebar"] .stNumberInput label {
        color: #E0E0E0 !important;
    }

    /* ── Sidebar Info boxes ── */
    [data-testid="stSidebar"] .stAlert {
        background-color: rgba(208, 74, 2, 0.1) !important;
        border-left: 4px solid #D04A02 !important;
        color: #FFB600 !important;
    }

    /* ── PwC Logo Watermark Effect (subtle) ── */
    .main::before {
        content: "";
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 500px;
        height: 500px;
        background: radial-gradient(
            circle,
            rgba(208, 74, 2, 0.03) 0%,
            transparent 70%
        );
        pointer-events: none;
        z-index: 0;
    }

    /* ── Hero Header ── */
    .hero {
        text-align: center;
        padding: 30px 0 15px 0;
        position: relative;
    }
    .hero h1 {
        font-size: 2.8rem;
        background: linear-gradient(90deg, #D04A02, #FFB600, #EB8C00, #D04A02);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 900;
        animation: shimmer 4s ease-in-out infinite;
    }
    @keyframes shimmer {
        0% { background-position: 0% center; }
        50% { background-position: 200% center; }
        100% { background-position: 0% center; }
    }
    .hero p {
        color: #a0a0a0;
        font-size: 1.1rem;
    }

    /* ── PwC Gradient Divider ── */
    .gradient-divider {
        height: 3px;
        background: linear-gradient(
            90deg,
            transparent,
            #D04A02,
            #FFB600,
            #EB8C00,
            #D04A02,
            transparent
        );
        border: none;
        margin: 20px 0;
        border-radius: 2px;
    }

    /* ── Section Headers ── */
    .section-header {
        font-size: 1.5rem;
        font-weight: 700;
        color: #D04A02;
        border-bottom: 2px solid #D04A02;
        padding-bottom: 8px;
        margin: 30px 0 20px 0;
        letter-spacing: 0.5px;
    }

    /* ── Metric Cards — PwC Style ── */
    .metric-card {
        background: linear-gradient(135deg, #2D2D2D 0%, #3a3a3a 50%, #2D2D2D 100%);
        border: 1px solid #D04A02;
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        box-shadow:
            0 4px 20px rgba(208, 74, 2, 0.15),
            inset 0 1px 0 rgba(255, 182, 0, 0.1);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .metric-card::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #D04A02, #FFB600, #D04A02);
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow:
            0 8px 35px rgba(208, 74, 2, 0.3),
            0 4px 15px rgba(255, 182, 0, 0.15);
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 800;
        color: #D04A02;
        margin: 8px 0;
        text-shadow: 0 0 20px rgba(208, 74, 2, 0.3);
    }
    .metric-label {
        font-size: 0.9rem;
        color: #a0a0a0;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-weight: 600;
    }
    .metric-sub {
        font-size: 0.8rem;
        color: #707070;
        margin-top: 6px;
    }

    /* ── Expander Styling ── */
    .streamlit-expanderHeader {
        background-color: #2D2D2D !important;
        border: 1px solid #464646 !important;
        border-radius: 8px !important;
        color: #D04A02 !important;
        font-weight: 600 !important;
    }
    .streamlit-expanderHeader:hover {
        border-color: #D04A02 !important;
    }

    /* ── Input Fields ── */
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        background-color: #2D2D2D !important;
        border-color: #464646 !important;
        color: #E0E0E0 !important;
    }
    .stSelectbox > div > div:focus-within,
    .stMultiSelect > div > div:focus-within {
        border-color: #D04A02 !important;
        box-shadow: 0 0 0 1px #D04A02 !important;
    }

    .stNumberInput > div > div > input {
        background-color: #2D2D2D !important;
        border-color: #464646 !important;
        color: #E0E0E0 !important;
    }
    .stNumberInput > div > div > input:focus {
        border-color: #D04A02 !important;
        box-shadow: 0 0 0 1px #D04A02 !important;
    }

    /* ── Slider — PwC Orange ── */
    .stSlider > div > div > div > div {
        background-color: #D04A02 !important;
    }
    .stSlider > div > div > div > div > div {
        background-color: #FFB600 !important;
    }

    /* ── Checkbox ── */
    .stCheckbox label span {
        color: #E0E0E0 !important;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #2D2D2D;
        border-radius: 8px 8px 0 0;
        color: #a0a0a0;
        border: 1px solid #464646;
        padding: 8px 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #D04A02 !important;
        color: white !important;
        border-color: #D04A02 !important;
    }

    /* ── DataFrame / Tables ── */
    .stDataFrame {
        border: 1px solid #464646;
        border-radius: 8px;
    }

    /* ── Info / Success / Warning alerts ── */
    .stAlert[data-baseweb="notification"] {
        border-radius: 8px !important;
    }

    /* ── Buttons (if any) ── */
    .stButton > button {
        background: linear-gradient(135deg, #D04A02 0%, #B8390E 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 700;
        padding: 8px 24px;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #FFB600 0%, #EB8C00 100%);
        color: #1a1a1a;
        box-shadow: 0 4px 20px rgba(255, 182, 0, 0.4);
    }

    /* ── PwC Badge (top-right corner) ── */
    .pwc-badge {
        position: fixed;
        top: 12px;
        right: 20px;
        background: linear-gradient(135deg, #D04A02 0%, #B8390E 100%);
        color: white;
        padding: 6px 18px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 800;
        letter-spacing: 2px;
        z-index: 999;
        box-shadow: 0 4px 15px rgba(208, 74, 2, 0.4);
        font-family: 'Georgia', serif;
    }

    /* ── PwC Footer ── */
    .pwc-footer {
        text-align: center;
        padding: 30px 0;
        color: #707070;
        font-size: 0.85rem;
        border-top: 1px solid #464646;
        margin-top: 40px;
    }
    .pwc-footer strong {
        color: #D04A02;
    }
    .pwc-footer .pwc-logo-text {
        font-size: 1.4rem;
        font-weight: 800;
        color: #D04A02;
        font-family: 'Georgia', serif;
        letter-spacing: 3px;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #1a1a1a;
    }
    ::-webkit-scrollbar-thumb {
        background: #D04A02;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #FFB600;
    }
</style>
""", unsafe_allow_html=True)



# PwC Badge (top-right)
st.markdown('<div class="pwc-badge">PwC</div>', unsafe_allow_html=True)

# Hero
st.markdown("""
<div class="hero">
    <h1>❄️ Snowflake Credit Consumption Estimator</h1>
    <p>Interactive cost modeler powered by the official
    <b>Snowflake Service Consumption Table</b> — Effective March 2, 2026</p>
    <p style="color: #D04A02; font-size: 0.85rem; letter-spacing: 2px;
       margin-top: 8px; font-weight: 600;">
       BUILT BY PwC  |  DATA & ANALYTICS</p>
</div>
<div class="gradient-divider"></div>
""", unsafe_allow_html=True)



# ──────────────────────────────────────────────────────────────────────────────
# DATA — EXACT FROM CreditConsumptionTable.pdf (Effective March 2, 2026)
# ──────────────────────────────────────────────────────────────────────────────

# Table 1(a): Standard Warehouse Credits/Hour
STANDARD_WH_CREDITS = {
    "XS": 1, "S": 2, "M": 4, "L": 8, "XL": 16,
    "2XL": 32, "3XL": 64, "4XL": 128, "5XL": 256, "6XL": 512,
}

# Table 1(b): Gen 2 Warehouse Credits/Hour
GEN2_WH_CREDITS = {
    "AWS": {"XS": 1.35, "S": 2.7, "M": 5.4, "L": 10.8, "XL": 21.6,
            "2XL": 43.2, "3XL": 86.4, "4XL": 172.8},
    "Azure": {"XS": 1.25, "S": 2.5, "M": 5, "L": 10, "XL": 20,
              "2XL": 40, "3XL": 80, "4XL": 160},
    "GCP": {"XS": 1.35, "S": 2.7, "M": 5.4, "L": 10.8, "XL": 21.6,
            "2XL": 43.2, "3XL": 86.4, "4XL": 172.8},
}

# Table 1(c): Snowpark Optimized Warehouses Credits/Hour
SNOWPARK_WH_CREDITS = {
    "MEMORY_1X":      {"XS": 1.0, "S": 2.0, "M": 4.0, "L": 8.0,
                       "XL": 16.0, "2XL": 32.0, "3XL": 64.0, "4XL": 128.0},
    "MEMORY_1X_x86":  {"XS": 1.1, "S": 2.2, "M": 4.4, "L": 8.8,
                       "XL": 17.6, "2XL": 35.2, "3XL": 70.4, "4XL": 140.8},
    "MEMORY_16X":     {"M": 6.0, "L": 12.0, "XL": 24.0, "2XL": 48.0,
                       "3XL": 96.0, "4XL": 192.0, "5XL": 384.0, "6XL": 768.0},
    "MEMORY_16X_x86": {"M": 6.25, "L": 12.5, "XL": 25.0, "2XL": 50.0,
                       "3XL": 100.0, "4XL": 200.0},
    "MEMORY_64X":     {"L": 15.0, "XL": 30.0, "2XL": 60.0,
                       "3XL": 120.0, "4XL": 240.0},
    "MEMORY_64X_x86": {"L": 16.0, "XL": 32.0, "2XL": 64.0,
                       "3XL": 128.0, "4XL": 256.0},
}

# Table 1(d): Interactive Warehouse Credits/Hour
INTERACTIVE_WH_CREDITS = {
    "XS": 0.6, "S": 1.2, "M": 2.4, "L": 4.8, "XL": 9.6,
    "2XL": 19.2, "3XL": 38.4, "4XL": 76.8,
}

# Table 2: On Demand Credit Pricing ($/Credit) — ALL AWS REGIONS
AWS_ON_DEMAND_PRICING = {
    "AWS US East (Northern Virginia)":          {"Standard": 2.00, "Enterprise": 3.00, "Business Critical": 4.00, "VPS": 6.00},
    "AWS US West (Oregon)":                     {"Standard": 2.00, "Enterprise": 3.00, "Business Critical": 4.00, "VPS": 6.00},
    "AWS EU (Dublin)":                          {"Standard": 2.00, "Enterprise": 3.00, "Business Critical": 4.00, "VPS": 6.00},
    "AWS EU (Frankfurt)":                       {"Standard": 2.50, "Enterprise": 3.50, "Business Critical": 4.50, "VPS": 7.50},
    "AWS AP (Sydney)":                          {"Standard": 2.50, "Enterprise": 3.50, "Business Critical": 5.00, "VPS": 7.00},
    "AWS AP (Singapore)":                       {"Standard": 2.50, "Enterprise": 3.50, "Business Critical": 5.00, "VPS": 7.00},
    "AWS Canada Central":                       {"Standard": 2.25, "Enterprise": 3.50, "Business Critical": 4.50, "VPS": 7.00},
    "AWS US East 2 (Ohio)":                     {"Standard": 2.00, "Enterprise": 3.00, "Business Critical": 4.00, "VPS": 6.00},
    "AWS AP Northeast 1 (Tokyo)":               {"Standard": 2.50, "Enterprise": 3.50, "Business Critical": 5.00, "VPS": 7.00},
    "AWS AP (Mumbai)":                          {"Standard": 2.00, "Enterprise": 3.00, "Business Critical": 4.00, "VPS": 6.50},
    "AWS US East 1 Commercial Gov":             {"Standard": 2.00, "Enterprise": 3.00, "Business Critical": 4.00, "VPS": 6.00},
    "AWS Europe (London)":                      {"Standard": 2.25, "Enterprise": 3.50, "Business Critical": 4.50, "VPS": 7.00},
    "AWS Asia Pacific (Seoul)":                 {"Standard": 2.50, "Enterprise": 3.50, "Business Critical": 5.00, "VPS": 7.00},
    "AWS US Gov West 1":                        {"Standard": 3.00, "Enterprise": 4.50, "Business Critical": 6.00, "VPS": 9.00},
    "AWS US Gov West 1 (FedRAMP High Plus)":    {"Standard": 3.00, "Enterprise": 4.50, "Business Critical": 6.00, "VPS": 9.00},
    "AWS Europe (Stockholm)":                   {"Standard": 2.00, "Enterprise": 3.00, "Business Critical": 4.00, "VPS": 6.50},
    "AWS Asia Pacific (Osaka)":                 {"Standard": 2.50, "Enterprise": 3.50, "Business Critical": 5.00, "VPS": 7.00},
    "AWS South America East 1 (São Paulo)":     {"Standard": 3.00, "Enterprise": 4.50, "Business Critical": 6.50, "VPS": 9.50},
    "AWS EU (Paris)":                           {"Standard": 2.25, "Enterprise": 3.50, "Business Critical": 4.50, "VPS": 7.00},
    "AWS Asia Pacific (Jakarta)":               {"Standard": 2.50, "Enterprise": 3.50, "Business Critical": 5.00, "VPS": 7.00},
    "AWS US Gov East 1 (FedRAMP High Plus)":    {"Standard": 3.00, "Enterprise": 4.50, "Business Critical": 6.00, "VPS": 9.00},
    "AWS EU (Zurich)":                          {"Standard": 2.75, "Enterprise": 3.75, "Business Critical": 5.25, "VPS": 7.50},
    "AWS US Gov West 1 (DoD)":                  {"Standard": 3.00, "Enterprise": 4.50, "Business Critical": 6.00, "VPS": 9.00},
    "AWS US West (Commercial Gov - Oregon)":    {"Standard": 2.00, "Enterprise": 3.00, "Business Critical": 4.00, "VPS": 6.00},
    "AWS Africa (Cape Town)":                   {"Standard": 2.75, "Enterprise": 4.00, "Business Critical": 5.50, "VPS": 8.00},
    "AWS Middle East (UAE)":                    {"Standard": 2.50, "Enterprise": 3.50, "Business Critical": 5.00, "VPS": 7.00},
}

# Table 5: Serverless Feature Multipliers
SERVERLESS_FEATURES = {
    "Serverless Tasks":                  {"compute_mult": 0.9,  "cs_mult": 1,    "unit_charge": None},
    "Serverless Tasks Flex":             {"compute_mult": 0.5,  "cs_mult": 1,    "unit_charge": None},
    "Snowpipe":                          {"compute_mult": None, "cs_mult": None, "unit_charge": "0.0037 Credits/GB"},
    "Snowpipe Streaming":               {"compute_mult": None, "cs_mult": None, "unit_charge": "0.0037 Credits/uncompressed GB"},
    "Snowpipe Streaming Classic":        {"compute_mult": 1,    "cs_mult": None, "unit_charge": "0.01 Credits/client instance/hour"},
    "Automated Refresh & Data Reg.":     {"compute_mult": 1.25, "cs_mult": None, "unit_charge": "0.06 Credits/1000 files"},
    "Backup":                            {"compute_mult": 2,    "cs_mult": 1,    "unit_charge": None},
    "Clustered Tables":                  {"compute_mult": 2,    "cs_mult": 1,    "unit_charge": None},
    "Copy Files":                        {"compute_mult": 2,    "cs_mult": None, "unit_charge": None},
    "Data Quality Monitoring":           {"compute_mult": 2,    "cs_mult": 1,    "unit_charge": None},
    "Failsafe Recovery":                 {"compute_mult": 0.9,  "cs_mult": 1,    "unit_charge": None},
    "Logging":                           {"compute_mult": 1.25, "cs_mult": None, "unit_charge": "0.28 Credits/1000 file batches"},
    "Materialized Views Maintenance":    {"compute_mult": 2,    "cs_mult": 1,    "unit_charge": None},
    "Open Catalog":                      {"compute_mult": None, "cs_mult": None, "unit_charge": "0.5 Credits/1M requests"},
    "Query Acceleration":                {"compute_mult": 1,    "cs_mult": None, "unit_charge": None},
    "Replication":                       {"compute_mult": 2,    "cs_mult": 0.35, "unit_charge": None},
    "Search Optimization Service":       {"compute_mult": 2,    "cs_mult": 1,    "unit_charge": None},
    "Sensitive Data Classification":     {"compute_mult": 0.9,  "cs_mult": 1,    "unit_charge": None},
    "Serverless Alerts":                 {"compute_mult": 0.9,  "cs_mult": 1,    "unit_charge": None},
    "Storage Lifecycle Policy Exec.":    {"compute_mult": 0.50, "cs_mult": 1,    "unit_charge": None},
    "Table Optimization":                {"compute_mult": 0.75, "cs_mult": 1,    "unit_charge": None},
    "Telemetry Data Ingest":             {"compute_mult": None, "cs_mult": None, "unit_charge": "0.0212 Credits/GB"},
    "Trust Center":                      {"compute_mult": 1,    "cs_mult": 1,    "unit_charge": None},
}

# ══════════════════════════════════════════════════════════════════════════════
# TABLE 1(e): SPCS COMPUTE — CPU INSTANCE FAMILY
# Source: CreditConsumptionTable.pdf — Table 1(e)
# ══════════════════════════════════════════════════════════════════════════════
SPCS_CPU_CREDITS = {
    "CPU_X64_XS":  {"spcs": 0.06, "openflow": None},
    "CPU_X64_S":   {"spcs": 0.11, "openflow": 0.11},
    "CPU_X64_M":   {"spcs": 0.22, "openflow": None},
    "CPU_X64_SL":  {"spcs": 0.41, "openflow": 0.41},
    "CPU_X64_L":   {"spcs": 0.83, "openflow": 0.83},
}

# ══════════════════════════════════════════════════════════════════════════════
# TABLE 1(f): SPCS COMPUTE — HIGH-MEMORY INSTANCE FAMILY
# Source: CreditConsumptionTable.pdf — Table 1(f)
# ══════════════════════════════════════════════════════════════════════════════
SPCS_HIGHMEM_CREDITS = {
    "HIGHMEM_X64_S":  0.28,
    "HIGHMEM_X64_M":  1.11,
    "HIGHMEM_X64_SL": 2.93,
    "HIGHMEM_X64_L":  4.44,
}

# ══════════════════════════════════════════════════════════════════════════════
# TABLE 1(g): SPCS COMPUTE — GPU INSTANCE FAMILY
# Source: CreditConsumptionTable.pdf — Table 1(g)
# ══════════════════════════════════════════════════════════════════════════════
SPCS_GPU_CREDITS = {
    "GPU_NV_XS":             0.25,
    "GPU_GCP_NV_L4_1_24G":   0.43,
    "GPU_NV_S":              0.57,
    "GPU_NV_SM":             1.70,
    "GPU_GCP_NV_L4_4_24G":   1.94,
    "GPU_NV_M":              2.68,
    "GPU_NV_2M":             3.50,
    "GPU_NV_3M":             3.55,
    "GPU_GCP_NV_A100_8_40G": 11.68,
    "GPU_NV_SL":             13.50,
    "GPU_NV_L":              14.12,
}

# ══════════════════════════════════════════════════════════════════════════════
# TABLE 1(h): SNOWFLAKE OPENFLOW COMPUTE
# Source: CreditConsumptionTable.pdf — Table 1(h)
# ══════════════════════════════════════════════════════════════════════════════
OPENFLOW_PRICING = {
    "BYOC Deployment":               {"rate": 0.0225, "unit": "Credits per vCPU per Hour"},
    "Snowflake Deployment (SPCS)":    {"rate": None, "unit": "See SPCS CPU table above"},
}

# ══════════════════════════════════════════════════════════════════════════════
# TABLE 1(i): SNOWFLAKE POSTGRES COMPUTE
# Source: CreditConsumptionTable.pdf — Table 1(i)
# ══════════════════════════════════════════════════════════════════════════════
POSTGRES_COMPUTE = {
    # instance_family: {cloud: {standard_cr_hr, ha_cr_hr}}
    "STANDARD_M":    {"AWS": {"standard": 0.0356, "ha": 0.0712}, "Azure": {"standard": 0.0376, "ha": 0.0752}},
    "STANDARD_L":    {"AWS": {"standard": 0.0712, "ha": 0.1424}, "Azure": {"standard": 0.0752, "ha": 0.1504}},
    "STANDARD_XL":   {"AWS": {"standard": 0.1424, "ha": 0.2848}, "Azure": {"standard": 0.1504, "ha": 0.3008}},
    "STANDARD_2X":   {"AWS": {"standard": 0.2848, "ha": 0.5696}, "Azure": {"standard": 0.3008, "ha": 0.6016}},
    "STANDARD_4XL":  {"AWS": {"standard": 0.5696, "ha": 1.1392}, "Azure": {"standard": 0.6016, "ha": 1.2032}},
    "STANDARD_8XL":  {"AWS": {"standard": 1.1392, "ha": 2.2784}, "Azure": {"standard": 1.2032, "ha": 2.4064}},
    "STANDARD_12XL": {"AWS": {"standard": 1.7088, "ha": 3.4176}, "Azure": {"standard": 1.8048, "ha": 3.6096}},
    "STANDARD_24XL": {"AWS": {"standard": 3.4176, "ha": 6.8352}, "Azure": {"standard": 3.6096, "ha": 7.2192}},
    "HIGHMEM_L":     {"AWS": {"standard": 0.1024, "ha": 0.2048}, "Azure": {"standard": 0.1088, "ha": 0.2176}},
    "HIGHMEM_XL":    {"AWS": {"standard": 0.2048, "ha": 0.4096}, "Azure": {"standard": 0.2176, "ha": 0.4352}},
    "HIGHMEM_2XL":   {"AWS": {"standard": 0.4096, "ha": 0.8192}, "Azure": {"standard": 0.4352, "ha": 0.8704}},
    "HIGHMEM_4XL":   {"AWS": {"standard": 0.8192, "ha": 1.6384}, "Azure": {"standard": 0.8704, "ha": 1.7408}},
    "HIGHMEM_8XL":   {"AWS": {"standard": 1.6384, "ha": 3.2768}, "Azure": {"standard": 1.7408, "ha": 3.4816}},
    "HIGHMEM_12XL":  {"AWS": {"standard": 2.4576, "ha": 4.9152}, "Azure": {"standard": 2.6112, "ha": 5.2224}},
    "HIGHMEM_16XL":  {"AWS": {"standard": 3.2768, "ha": 6.5536}, "Azure": {"standard": 3.4816, "ha": 6.9632}},
    "HIGHMEM_24XL":  {"AWS": {"standard": 4.9152, "ha": 9.8304}, "Azure": {"standard": 5.2224, "ha": 10.4448}},
    "HIGHMEM_32XL":  {"AWS": {"standard": 6.5536, "ha": 13.1072}, "Azure": {"standard": 6.9632, "ha": 13.9264}},
    "HIGHMEM_48XL":  {"AWS": {"standard": 9.8304, "ha": 19.6608}, "Azure": {"standard": 10.4448, "ha": 20.8896}},
    "BURST_XS":      {"AWS": {"standard": 0.0068, "ha": 0.0136}, "Azure": {"standard": None, "ha": None}},
    "BURST_S":       {"AWS": {"standard": 0.0136, "ha": 0.0272}, "Azure": {"standard": 0.0144, "ha": 0.0288}},
    "BURST_M":       {"AWS": {"standard": 0.0272, "ha": 0.0544}, "Azure": {"standard": 0.0288, "ha": 0.0576}},
}

# ══════════════════════════════════════════════════════════════════════════════
# TABLE 3(b): HYBRID TABLES STORAGE PRICING (GB/mo)
# Source: CreditConsumptionTable.pdf — Table 3(b)
# ══════════════════════════════════════════════════════════════════════════════
HYBRID_STORAGE_PRICING = {
    "AWS": {
        "US East (Northern Virginia)": 0.34, "US West (Oregon)": 0.34,
        "EU Dublin": 0.34, "EU Frankfurt": 0.36,
        "AP Sydney": 0.37, "AP Singapore": 0.37,
        "Canada Central": 0.37, "US East 2 (Ohio)": 0.34,
        "AP Northeast 1 (Tokyo)": 0.37, "AP Mumbai": 0.34,
        "US East 1 Commercial Gov": 0.34, "Europe (London)": 0.35,
        "Asia Pacific (Seoul)": 0.37, "US Gov West 1": 0.58,
        "US Gov West 1 (Fedramp High Plus)": 0.58,
        "Europe (Stockholm)": 0.34, "Asia Pacific (Osaka)": 0.37,
        "South America East 1 (São Paulo)": 0.60,
        "EU (Paris)": 0.35, "Asia Pacific (Jakarta)": 0.37,
        "US Gov East 1 (Fedramp High Plus)": 0.58,
        "EU (Zurich)": 0.40, "US Gov West 1 (DoD)": 0.58,
        "US West (Commercial Gov - Oregon)": 0.34,
        "Africa (Cape Town)": 0.40, "Middle East (UAE)": 0.37,
    },
    "Azure": {
        "East US 2 (Virginia)": 0.34, "West US 2 (Washington)": 0.34,
        "West Europe (Netherlands)": 0.34,
        "Australia East (New South Wales)": 0.37,
        "Canada Central (Toronto)": 0.37,
        "Southeast Asia (Singapore)": 0.37,
        "Switzerland North": 0.43, "Central US (Iowa)": 0.34,
        "North Europe (Ireland)": 0.34, "Japan East (Tokyo)": 0.37,
        "UAE North (Dubai)": 0.38, "South Central US (Texas)": 0.34,
        "Central India (Pune)": 0.37, "UK South (London)": 0.35,
        "Mexico Central": 0.34, "Korea Central": 0.37,
        "Sweden Central": 0.34, "East US (Virginia)": 0.34,
    },
}

# ══════════════════════════════════════════════════════════════════════════════
# TABLE 3(c): SPCS BLOCK STORAGE PRICING
# Source: CreditConsumptionTable.pdf — Table 3(c)
# ══════════════════════════════════════════════════════════════════════════════
SPCS_BLOCK_STORAGE = {
    "AWS": {
        "US East (Northern Virginia)":           {"volume": 81.92,  "iops": 5.00, "throughput": 40.96, "snapshot": 51.20},
        "US West (Oregon)":                      {"volume": 81.92,  "iops": 5.00, "throughput": 40.96, "snapshot": 51.20},
        "EU Dublin":                             {"volume": 90.12,  "iops": 5.50, "throughput": 45.06, "snapshot": 51.20},
        "EU Frankfurt":                          {"volume": 97.49,  "iops": 6.00, "throughput": 48.75, "snapshot": 55.30},
        "AP Sydney":                             {"volume": 98.31,  "iops": 6.00, "throughput": 49.16, "snapshot": 56.30},
        "AP Singapore":                          {"volume": 98.31,  "iops": 6.00, "throughput": 49.16, "snapshot": 51.20},
        "Canada Central":                        {"volume": 90.12,  "iops": 5.50, "throughput": 45.06, "snapshot": 56.30},
        "US East 2 (Ohio)":                      {"volume": 81.92,  "iops": 5.00, "throughput": 40.96, "snapshot": 51.20},
        "AP Northeast 1 (Tokyo)":                {"volume": 98.31,  "iops": 6.00, "throughput": 49.16, "snapshot": 51.20},
        "AP Mumbai":                             {"volume": 81.92,  "iops": 5.00, "throughput": 40.96, "snapshot": 51.20},
        "US East 1 Commercial Gov":              {"volume": 81.92,  "iops": 5.00, "throughput": 40.96, "snapshot": 51.20},
        "Europe (London)":                       {"volume": 90.12,  "iops": 5.50, "throughput": 45.06, "snapshot": 54.30},
        "US Gov West 1":                         {"volume": 98.31,  "iops": 6.00, "throughput": 49.16, "snapshot": 67.60},
        "US Gov West 1 (Fedramp High Plus)":     {"volume": 98.31,  "iops": 6.00, "throughput": 49.16, "snapshot": 67.60},
        "Europe (Stockholm)":                    {"volume": 85.61,  "iops": 5.20, "throughput": 42.81, "snapshot": 48.60},
        "Asia Pacific (Osaka)":                  {"volume": 98.31,  "iops": 6.00, "throughput": 49.16, "snapshot": 51.20},
        "South America East 1 (São Paulo)":      {"volume": 155.65, "iops": 9.50, "throughput": 77.83, "snapshot": 69.60},
        "EU (Paris)":                            {"volume": 95.03,  "iops": 5.80, "throughput": 47.52, "snapshot": 54.30},
        "Asia Pacific (Jakarta)":                {"volume": 98.31,  "iops": 6.00, "throughput": 49.16, "snapshot": 51.20},
        "US Gov East 1 (Fedramp High Plus)":     {"volume": 98.31,  "iops": 6.00, "throughput": 49.16, "snapshot": 67.60},
        "EU (Zurich)":                           {"volume": 116.95, "iops": 7.00, "throughput": 58.48, "snapshot": 60.40},
        "US Gov West 1 (DoD)":                   {"volume": 98.31,  "iops": 6.00, "throughput": 49.16, "snapshot": 67.60},
        "US West (Commercial Gov - Oregon)":     {"volume": 81.92,  "iops": 5.00, "throughput": 40.96, "snapshot": 51.20},
        "Africa (Cape Town)":                    {"volume": 107.21, "iops": 6.50, "throughput": 53.25, "snapshot": 60.93},
        "Middle East (UAE)":                     {"volume": 99.12,  "iops": 6.10, "throughput": 49.15, "snapshot": 56.32},
    },
    "Azure": {
        "East US 2 (Virginia)":                  {"volume": 82.23,  "iops": 5.11, "throughput": 41.12, "snapshot": 51.20},
        "West US 2 (Washington)":                {"volume": 82.20,  "iops": 5.11, "throughput": 41.12, "snapshot": 51.20},
        "West Europe (Netherlands)":             {"volume": 97.18,  "iops": 5.84, "throughput": 48.59, "snapshot": 51.20},
        "Australia East (New South Wales)":      {"volume": 82.23,  "iops": 5.11, "throughput": 41.12, "snapshot": 56.30},
        "Canada Central (Toronto)":              {"volume": 90.40,  "iops": 5.84, "throughput": 44.86, "snapshot": 56.30},
        "Southeast Asia (Singapore)":            {"volume": 98.68,  "iops": 5.84, "throughput": 49.34, "snapshot": 51.20},
        "Switzerland North":                     {"volume": 117.37, "iops": 7.30, "throughput": 58.31, "snapshot": 56.30},
        "US Gov Virginia":                       {"volume": 98.68,  "iops": 5.84, "throughput": 49.34, "snapshot": 107.00},
        "Central US (Iowa)":                     {"volume": 92.70,  "iops": 5.84, "throughput": 46.35, "snapshot": 51.20},
        "North Europe (Ireland)":                {"volume": 82.23,  "iops": 5.11, "throughput": 41.12, "snapshot": 51.20},
        "Japan East (Tokyo)":                    {"volume": 98.68,  "iops": 5.84, "throughput": 49.34, "snapshot": 51.20},
        "UAE North (Dubai)":                     {"volume": 99.42,  "iops": 5.84, "throughput": 49.34, "snapshot": 61.40},
        "South Central US (Texas)":              {"volume": 82.23,  "iops": 5.11, "throughput": 41.12, "snapshot": 51.20},
        "Central India (Pune)":                  {"volume": 82.23,  "iops": 5.11, "throughput": 41.12, "snapshot": 51.20},
        "UK South (London)":                     {"volume": 94.94,  "iops": 5.84, "throughput": 47.10, "snapshot": 54.30},
        "US Gov Virginia (Fed Ramp High Plus)":  {"volume": 98.68,  "iops": 5.84, "throughput": 49.34, "snapshot": 107.00},
        "Mexico Central":                        {"volume": 90.11,  "iops": 7.30, "throughput": 45.06, "snapshot": 56.32},
        "Korea Central":                         {"volume": 93.39,  "iops": 5.70, "throughput": 47.10, "snapshot": 51.20},
        "Sweden Central":                        {"volume": 82.94,  "iops": 5.20, "throughput": 41.98, "snapshot": 51.20},
        "East US (Virginia)":                    {"volume": 82.94,  "iops": 5.20, "throughput": 41.98, "snapshot": 51.20},
    },
    "GCP": {
        "US Central 1 (Iowa) CPU":               {"volume": 81.92,  "iops": 5.00, "throughput": 40.96, "snapshot": 51.20},
        "US Central 1 (Iowa) GPU":               {"volume": 81.92,  "iops": None, "throughput": 122.88, "snapshot": 51.20},
        "US East 4 (N. Virginia) CPU":            {"volume": 81.92,  "iops": 5.00, "throughput": 40.96, "snapshot": 51.20},
        "US East 4 (N. Virginia) GPU":            {"volume": 81.92,  "iops": None, "throughput": 122.88, "snapshot": 51.20},
        "Europe West 4 (Netherlands) CPU":        {"volume": 86.02,  "iops": 5.00, "throughput": 43.01, "snapshot": 51.20},
    },
}

# ══════════════════════════════════════════════════════════════════════════════
# TABLE 3(e): ARCHIVE STORAGE AND DATA RETRIEVAL PRICING
# Source: CreditConsumptionTable.pdf — Table 3(e)
# ══════════════════════════════════════════════════════════════════════════════
ARCHIVE_STORAGE_PRICING = {
    "AWS": {
        "US East (Northern Virginia)":           {"storage": 4.00, "retrieval": 30.00},
        "US West (Oregon)":                      {"storage": 4.00, "retrieval": 30.00},
        "EU Dublin":                             {"storage": 4.00, "retrieval": 30.00},
        "EU Frankfurt":                          {"storage": 5.00, "retrieval": 30.00},
        "AP Sydney":                             {"storage": 5.00, "retrieval": 30.00},
        "AP Singapore":                          {"storage": 5.00, "retrieval": 30.00},
        "Canada Central":                        {"storage": 5.00, "retrieval": 30.00},
        "US East 2 (Ohio)":                      {"storage": 4.00, "retrieval": 30.00},
        "AP Northeast 1 (Tokyo)":                {"storage": 5.00, "retrieval": 30.00},
        "AP Mumbai":                             {"storage": 5.00, "retrieval": 30.00},
        "US East 1 Commercial Gov":              {"storage": 4.00, "retrieval": 30.00},
        "Europe (London)":                       {"storage": 5.00, "retrieval": 30.00},
        "Asia Pacific (Seoul)":                  {"storage": 5.00, "retrieval": 30.00},
        "US Gov West 1":                         {"storage": 6.40, "retrieval": 30.00},
        "US Gov West 1 (Fedramp High Plus)":     {"storage": 6.40, "retrieval": 30.00},
        "Europe (Stockholm)":                    {"storage": 4.00, "retrieval": 30.00},
        "Asia Pacific (Osaka)":                  {"storage": 5.00, "retrieval": 30.00},
        "South America East 1 (São Paulo)":      {"storage": 8.30, "retrieval": 30.00},
        "EU (Paris)":                            {"storage": 5.00, "retrieval": 30.00},
        "Asia Pacific (Jakarta)":                {"storage": 5.00, "retrieval": 30.00},
        "US Gov East 1 (Fedramp High Plus)":     {"storage": 6.40, "retrieval": 30.00},
        "EU (Zurich)":                           {"storage": 5.50, "retrieval": 30.00},
        "US Gov West 1 (DoD)":                   {"storage": 6.40, "retrieval": 30.00},
        "US West (Commercial Gov - Oregon)":     {"storage": 4.00, "retrieval": 30.00},
        "Africa (Cape Town)":                    {"storage": 5.00, "retrieval": 30.00},
        "Middle East (UAE)":                     {"storage": 5.00, "retrieval": 30.00},
    },
    "Azure": {
        "East US 2 (Virginia)":                  {"storage": 4.00, "retrieval": 30.00},
        "West US 2 (Washington)":                {"storage": 4.00, "retrieval": 30.00},
        "West Europe (Netherlands)":             {"storage": 5.00, "retrieval": 30.00},
        "Australia East (New South Wales)":      {"storage": 5.00, "retrieval": 30.00},
        "Canada Central (Toronto)":              {"storage": 5.00, "retrieval": 30.00},
        "Southeast Asia (Singapore)":            {"storage": 5.00, "retrieval": 30.00},
        "Switzerland North":                     {"storage": 5.71, "retrieval": 42.90},
        "US Gov Virginia":                       {"storage": 6.40, "retrieval": 30.00},
        "Central US (Iowa)":                     {"storage": 4.92, "retrieval": 36.90},
        "North Europe (Ireland)":                {"storage": 4.00, "retrieval": 30.00},
        "Japan East (Tokyo)":                    {"storage": 5.00, "retrieval": 30.00},
        "UAE North (Dubai)":                     {"storage": 5.00, "retrieval": 30.00},
        "South Central US (Texas)":              {"storage": 4.80, "retrieval": 36.00},
        "Central India (Pune)":                  {"storage": 5.00, "retrieval": 30.00},
        "UK South (London)":                     {"storage": 5.00, "retrieval": 30.00},
        "US Gov Virginia (Fed Ramp High Plus)":  {"storage": 6.40, "retrieval": 30.00},
        "Mexico Central":                        {"storage": 4.95, "retrieval": 33.00},
        "Korea Central":                         {"storage": 5.00, "retrieval": 30.00},
        "Sweden Central":                        {"storage": 4.00, "retrieval": 30.00},
        "East US (Virginia)":                    {"storage": 4.00, "retrieval": 30.00},
    },
    "GCP": {
        "US Central 1 (Iowa)":                   {"storage": 4.00, "retrieval": 20.00},
        "US East 4 (N. Virginia)":               {"storage": 6.00, "retrieval": 20.00},
        "Europe West 2 (London)":                {"storage": 7.00, "retrieval": 20.00},
        "Europe West 3 (Frankfurt)":             {"storage": 6.00, "retrieval": 20.00},
        "Europe West 4 (Netherlands)":           {"storage": 4.00, "retrieval": 20.00},
        "Middle East Central 2 (Dammam)":        {"storage": 6.00, "retrieval": 20.00},
        "Australia Southeast 2 (Melbourne)":     {"storage": 6.00, "retrieval": 20.00},
    },
}

# ══════════════════════════════════════════════════════════════════════════════
# TABLE 3(f): SNOWFLAKE POSTGRES STORAGE
# Source: CreditConsumptionTable.pdf — Table 3(f)
# ══════════════════════════════════════════════════════════════════════════════
POSTGRES_STORAGE_PRICING = {
    "AWS": {
        "US East (Northern Virginia)":           {"standard": 117.76, "ha": 235.52},
        "US West (Oregon)":                      {"standard": 117.76, "ha": 235.52},
        "EU Dublin":                             {"standard": 129.55, "ha": 259.10},
        "EU Frankfurt":                          {"standard": 140.15, "ha": 280.30},
        "AP Sydney":                             {"standard": 141.32, "ha": 282.64},
        "AP Singapore":                          {"standard": 141.32, "ha": 282.64},
        "Canada Central":                        {"standard": 129.55, "ha": 259.10},
        "US East 2 (Ohio)":                      {"standard": 117.76, "ha": 235.52},
        "AP Northeast 1 (Tokyo)":                {"standard": 141.32, "ha": 282.64},
        "AP Mumbai":                             {"standard": 117.76, "ha": 235.52},
        "US East 1 Commercial Gov":              {"standard": 117.76, "ha": 235.52},
        "Europe (London)":                       {"standard": 136.60, "ha": 273.20},
        "Asia Pacific (Seoul)":                  {"standard": 134.25, "ha": 268.50},
        "US Gov West 1":                         {"standard": 141.32, "ha": 282.64},
        "US Gov West 1 (Fedramp High Plus)":     {"standard": 141.32, "ha": 282.64},
        "Europe (Stockholm)":                    {"standard": 123.06, "ha": 246.12},
        "Asia Pacific (Osaka)":                  {"standard": 141.32, "ha": 282.64},
        "South America East 1 (São Paulo)":      {"standard": 223.74, "ha": 447.48},
        "EU (Paris)":                            {"standard": 136.60, "ha": 273.20},
        "Asia Pacific (Jakarta)":                {"standard": 141.32, "ha": 282.64},
        "US Gov East 1 (Fedramp High Plus)":     {"standard": 141.32, "ha": 282.64},
        "EU (Zurich)":                           {"standard": 168.11, "ha": 336.22},
        "US Gov West 1 (DoD)":                   {"standard": 141.32, "ha": 282.64},
        "US West (Commercial Gov - Oregon)":     {"standard": 117.76, "ha": 235.52},
        "Africa (Cape Town)":                    {"standard": 154.11, "ha": 308.22},
        "Middle East (UAE)":                     {"standard": 142.49, "ha": 284.98},
    },
    "Azure": {
        "East US 2 (Virginia)":                  {"standard": 118.21, "ha": 236.42},
        "West US 2 (Washington)":                {"standard": 118.16, "ha": 236.32},
        "West Europe (Netherlands)":             {"standard": 139.70, "ha": 279.40},
        "Australia East (New South Wales)":      {"standard": 118.21, "ha": 236.42},
        "Canada Central (Toronto)":              {"standard": 129.95, "ha": 259.90},
        "Southeast Asia (Singapore)":            {"standard": 141.85, "ha": 283.70},
        "Switzerland North":                     {"standard": 168.71, "ha": 337.42},
        "US Gov Virginia":                       {"standard": 141.85, "ha": 283.70},
        "Central US (Iowa)":                     {"standard": 133.26, "ha": 266.52},
        "North Europe (Ireland)":                {"standard": 118.21, "ha": 236.42},
        "Japan East (Tokyo)":                    {"standard": 141.85, "ha": 283.70},
        "UAE North (Dubai)":                     {"standard": 142.91, "ha": 285.82},
        "South Central US (Texas)":              {"standard": 118.21, "ha": 236.42},
        "Central India (Pune)":                  {"standard": 118.21, "ha": 236.42},
        "UK South (London)":                     {"standard": 136.47, "ha": 272.94},
        "US Gov Virginia (Fed Ramp High Plus)":  {"standard": 141.85, "ha": 283.70},
        "Mexico Central":                        {"standard": 129.54, "ha": 259.08},
        "Sweden Central":                        {"standard": 118.78, "ha": 237.56},
        "Korea Central":                         {"standard": 134.25, "ha": 268.50},
        "East US (Virginia)":                    {"standard": 119.23, "ha": 238.46},
    },
}

# ══════════════════════════════════════════════════════════════════════════════
# TABLE 4(e): OUTBOUND PRIVATELINK PRICING
# Source: CreditConsumptionTable.pdf — Table 4(e)
# ══════════════════════════════════════════════════════════════════════════════
PRIVATELINK_PRICING = {
    "AWS": {
        "US East (Northern Virginia)":       {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "US West (Oregon)":                  {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "EU Dublin":                         {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "EU Frankfurt":                      {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "AP Sydney":                         {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "AP Singapore":                      {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "Canada Central":                    {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "US East 2 (Ohio)":                  {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "US Gov West 1 (DoD)":               {"endpoint": 12.50, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "US West (Commercial Gov - Oregon)": {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "Africa (Cape Town)":                {"endpoint": 13.09, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "Middle East (UAE)":                 {"endpoint": 12.10, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
    },
    "Azure": {
        "East US 2 (Virginia)":                  {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "West US 2 (Washington)":                {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "West Europe (Netherlands)":             {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "Australia East (New South Wales)":      {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "Canada Central (Toronto)":              {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "Southeast Asia (Singapore)":            {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "Switzerland North":                     {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "US Gov Virginia":                       {"endpoint": 13.00, "first_1pb": 12.80, "next_4pb": 12.80, "over_5pb": 12.80},
        "Central US (Iowa)":                     {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "North Europe (Ireland)":                {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "Japan East (Tokyo)":                    {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "UAE North (Dubai)":                     {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "South Central US (Texas)":              {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "Central India (Pune)":                  {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "UK South (London)":                     {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "US Gov Virginia (Fed Ramp High Plus)":  {"endpoint": 13.00, "first_1pb": 12.80, "next_4pb": 12.80, "over_5pb": 12.80},
        "Mexico Central":                        {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "Korea Central":                         {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "Sweden Central":                        {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
        "East US (Virginia)":                    {"endpoint": 10.00, "first_1pb": 10.24, "next_4pb": 6.14, "over_5pb": 4.09},
    },
    "GCP": {
        "US Central 1 (Iowa)":                   {"endpoint": 10.00, "first_1pb": 30.72, "next_4pb": 26.62, "over_5pb": 24.57},
        "US East 4 (N. Virginia)":               {"endpoint": 10.00, "first_1pb": 30.72, "next_4pb": 26.62, "over_5pb": 24.57},
        "Europe West 4 (Netherlands)":           {"endpoint": 10.00, "first_1pb": 30.72, "next_4pb": 26.62, "over_5pb": 24.57},
        "Europe West 2 (London)":                {"endpoint": 10.00, "first_1pb": 30.72, "next_4pb": 26.62, "over_5pb": 24.57},
        "Europe West 3 (Frankfurt)":             {"endpoint": 10.00, "first_1pb": 30.72, "next_4pb": 26.62, "over_5pb": 24.57},
        "Middle East Central 2 (Dammam)":        {"endpoint": 10.00, "first_1pb": 30.72, "next_4pb": 26.62, "over_5pb": 24.57},
        "Australia Southeast 2 (Melbourne)":     {"endpoint": 10.00, "first_1pb": 30.72, "next_4pb": 26.62, "over_5pb": 24.57},
    },
}

CLOUD_SERVICES_CREDITS_PER_HOUR = 4.4

WAREHOUSE_TYPES = [
    "Standard Warehouse",
    "Gen 2 Warehouse",
    "Snowpark Optimized Warehouse",
    "Interactive Warehouse",
]

# ──────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ──────────────────────────────────────────────────────────────────────────────
def get_credits_per_hour(wh_type, wh_size, cloud_provider="AWS",
                         snowpark_constraint="MEMORY_1X"):
    if wh_type == "Standard Warehouse":
        return STANDARD_WH_CREDITS.get(wh_size, 0)
    elif wh_type == "Gen 2 Warehouse":
        return GEN2_WH_CREDITS.get(cloud_provider, {}).get(wh_size, 0)
    elif wh_type == "Snowpark Optimized Warehouse":
        return SNOWPARK_WH_CREDITS.get(snowpark_constraint, {}).get(wh_size, 0)
    elif wh_type == "Interactive Warehouse":
        return INTERACTIVE_WH_CREDITS.get(wh_size, 0)
    return 0


def get_available_sizes(wh_type, cloud_provider="AWS",
                        snowpark_constraint="MEMORY_1X"):
    if wh_type == "Standard Warehouse":
        return list(STANDARD_WH_CREDITS.keys())
    elif wh_type == "Gen 2 Warehouse":
        return list(GEN2_WH_CREDITS.get(cloud_provider, {}).keys())
    elif wh_type == "Snowpark Optimized Warehouse":
        return list(SNOWPARK_WH_CREDITS.get(snowpark_constraint, {}).keys())
    elif wh_type == "Interactive Warehouse":
        return list(INTERACTIVE_WH_CREDITS.keys())
    return []


def generate_gradient_colors(values, low_color=(41, 181, 232),
                              high_color=(168, 85, 247)):
    """Generate gradient RGB strings for a list of numeric values."""
    if not values or max(values) == min(values):
        return [f"rgba({low_color[0]},{low_color[1]},{low_color[2]},0.3)"] * len(values)
    mn, mx = min(values), max(values)
    colors = []
    for v in values:
        ratio = (v - mn) / (mx - mn) if mx != mn else 0
        r = int(low_color[0] + (high_color[0] - low_color[0]) * ratio)
        g = int(low_color[1] + (high_color[1] - low_color[1]) * ratio)
        b = int(low_color[2] + (high_color[2] - low_color[2]) * ratio)
        colors.append(f"rgba({r},{g},{b},0.35)")
    return colors



# ──────────────────────────────────────────────────────────────────────────────
# SIDEBAR — GLOBAL CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Global Configuration")

    cloud_provider = st.selectbox("☁️ Cloud Provider", ["AWS", "Azure", "GCP"],
                                  index=0,
                                  help="Select your cloud provider")

    if cloud_provider == "AWS":
        region_options = list(AWS_ON_DEMAND_PRICING.keys())
    elif cloud_provider == "Azure":
        region_options = [
            "Azure East US 2 (Virginia)", "Azure West US 2 (Washington)",
            "Azure West Europe (Netherlands)",
            "Azure Australia East (New South Wales)",
            "Azure Canada Central (Toronto)",
            "Azure Southeast Asia (Singapore)",
            "Azure Switzerland North", "Azure US Gov Virginia",
            "Azure US Central (Iowa)", "Azure North Europe (Ireland)",
            "Azure Japan East (Tokyo)", "Azure UAE North (Dubai)",
            "Azure South Central US (Texas)",
            "Azure Central India (Pune)", "Azure UK South (London)",
            "Azure US Gov Virginia (Fed Ramp High Plus)",
            "Azure Mexico Central", "Azure Korea Central",
            "Azure Sweden Central", "Azure East US (Virginia)",
        ]
    else:
        region_options = [
            "GCP US Central 1 (Iowa)", "GCP US East 4 (N. Virginia)",
            "GCP Europe West 4 (Netherlands)",
            "GCP Europe West 2 (London)",
            "GCP Europe West 3 (Frankfurt)",
            "GCP Middle East Central 2 (Dammam)",
            "GCP Australia Southeast 2 (Melbourne)",
        ]

    region = st.selectbox("🌍 Region", region_options,
                          help="Select your deployment region")

    edition = st.selectbox("🏷️ Snowflake Edition",
                           ["Standard", "Enterprise",
                            "Business Critical", "VPS"],
                           index=1,
                           help="Your Snowflake service edition")

    if cloud_provider == "AWS" and region in AWS_ON_DEMAND_PRICING:
        credit_price = AWS_ON_DEMAND_PRICING[region].get(edition, 3.00)
    else:
        default_prices = {"Standard": 2.00, "Enterprise": 3.00,
                          "Business Critical": 4.00, "VPS": 6.00}
        credit_price = default_prices.get(edition, 3.00)

    st.markdown("---")
    st.markdown(f"### 💰 Credit Price: **${credit_price:.2f}**/credit")

    st.markdown("---")
    st.markdown("## 📅 Usage Period")
    hours_per_day = st.slider("Hours per Day", 1, 24, 8,
                              help="Average hours each warehouse runs daily")
    days_per_month = st.slider("Days per Month", 1, 31, 22,
                               help="Working days per month")
    total_hours = hours_per_day * days_per_month
    st.info(f"📊 **{total_hours}** total hours/month")

# ──────────────────────────────────────────────────────────────────────────────
# MAIN — MULTI-WAREHOUSE CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="section-header">🏗️ Virtual Warehouse Configuration</div>',
    unsafe_allow_html=True)

num_warehouses = st.number_input("Number of Warehouses to Configure",
                                 min_value=1, max_value=20, value=2)

warehouse_configs = []
cols_per_row = 2

for i in range(num_warehouses):
    if i % cols_per_row == 0:
        cols = st.columns(cols_per_row)
    col = cols[i % cols_per_row]

    with col:
        with st.expander(f"🔧 Warehouse #{i+1}", expanded=(i < 2)):
            wh_name = st.text_input("Name", value=f"WH_{i+1}",
                                    key=f"wh_name_{i}")
            wh_type = st.selectbox("Type", WAREHOUSE_TYPES,
                                   key=f"wh_type_{i}")

            snowpark_constraint = "MEMORY_1X"
            if wh_type == "Snowpark Optimized Warehouse":
                snowpark_constraint = st.selectbox(
                    "Resource Constraint",
                    list(SNOWPARK_WH_CREDITS.keys()),
                    key=f"sp_rc_{i}")

            avail_sizes = get_available_sizes(wh_type, cloud_provider,
                                              snowpark_constraint)
            wh_size = st.selectbox("Size", avail_sizes, key=f"wh_size_{i}")

            num_clusters = st.number_input(
                "Clusters (multi-cluster)", min_value=1, max_value=10,
                value=1, key=f"wh_clust_{i}",
                help="Credits = credits_per_hour × number_of_clusters")

            cph = get_credits_per_hour(wh_type, wh_size, cloud_provider,
                                       snowpark_constraint)
            effective_cph = cph * num_clusters

            st.markdown(
                f"**Credits/Hour:** `{cph}` × {num_clusters} cluster(s) "
                f"= **`{effective_cph}`**")

            warehouse_configs.append({
                "name": wh_name,
                "type": wh_type,
                "size": wh_size,
                "constraint": (snowpark_constraint
                               if wh_type == "Snowpark Optimized Warehouse"
                               else "—"),
                "clusters": num_clusters,
                "credits_per_hour": cph,
                "effective_cph": effective_cph,
            })

# ──────────────────────────────────────────────────────────────────────────────
# CLOUD SERVICES SECTION
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="section-header">☁️ Cloud Services Usage</div>',
    unsafe_allow_html=True)

cs_col1, cs_col2 = st.columns(2)
with cs_col1:
    cloud_services_hours = st.number_input(
        "Cloud Services Hours per Day",
        min_value=0.0, max_value=24.0, value=2.0, step=0.5,
        help="Cloud Services billed at 4.4 credits/hour. "
             "Free if ≤ 10% of daily VW credits.")
with cs_col2:
    apply_cs_adjustment = st.checkbox(
        "Apply Cloud Services 10% Adjustment", value=True,
        help="Daily CS charges waived if ≤ 10% of daily VW credits")

# ──────────────────────────────────────────────────────────────────────────────
# SERVERLESS FEATURES SECTION
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="section-header">⚡ Serverless Features</div>',
    unsafe_allow_html=True)

selected_serverless = st.multiselect(
    "Select Serverless Features in use",
    list(SERVERLESS_FEATURES.keys()),
    help="Choose features; credits calculated based on feature multipliers "
         "from Table 5.")

serverless_hours = {}
if selected_serverless:
    sf_cols = st.columns(min(len(selected_serverless), 3))
    for idx, feat in enumerate(selected_serverless):
        with sf_cols[idx % len(sf_cols)]:
            serverless_hours[feat] = st.number_input(
                f"{feat} — Compute-Hours/month",
                min_value=0.0, value=10.0, step=1.0, key=f"sf_{feat}")

# ──────────────────────────────────────────────────────────────────────────────
# Table 4(a): AWS Data Transfer Pricing ($/TB)
# ──────────────────────────────────────────────────────────────────────────────
AWS_DATA_TRANSFER = {
    "AWS US East (Northern Virginia)":       {"Same Region": 0, "SPCS Same Region": 3.07, "Same Cloud Diff Region": 20, "Diff Cloud/Internet": 90},
    "AWS US West (Oregon)":                  {"Same Region": 0, "SPCS Same Region": 3.07, "Same Cloud Diff Region": 20, "Diff Cloud/Internet": 90},
    "AWS EU Dublin":                         {"Same Region": 0, "SPCS Same Region": 3.07, "Same Cloud Diff Region": 20, "Diff Cloud/Internet": 90},
    "AWS EU Frankfurt":                      {"Same Region": 0, "SPCS Same Region": 3.07, "Same Cloud Diff Region": 20, "Diff Cloud/Internet": 90},
    "AWS AP Sydney":                         {"Same Region": 0, "SPCS Same Region": 3.07, "Same Cloud Diff Region": 140, "Diff Cloud/Internet": 140},
    "AWS AP Singapore":                      {"Same Region": 0, "SPCS Same Region": 3.07, "Same Cloud Diff Region": 90, "Diff Cloud/Internet": 120},
    "AWS Canada Central":                    {"Same Region": 0, "SPCS Same Region": 3.07, "Same Cloud Diff Region": 20, "Diff Cloud/Internet": 90},
    "AWS US East 2 (Ohio)":                  {"Same Region": 0, "SPCS Same Region": 3.07, "Same Cloud Diff Region": 20, "Diff Cloud/Internet": 90},
    "AWS AP Northeast 1 (Tokyo)":            {"Same Region": 0, "SPCS Same Region": 3.07, "Same Cloud Diff Region": 90, "Diff Cloud/Internet": 114},
    "AWS AP (Mumbai)":                       {"Same Region": 0, "SPCS Same Region": 3.07, "Same Cloud Diff Region": 60, "Diff Cloud/Internet": 90},
    "AWS US East 1 Commercial Gov":          {"Same Region": 0, "SPCS Same Region": 3.07, "Same Cloud Diff Region": 20, "Diff Cloud/Internet": 90},
    "AWS Europe (London)":                   {"Same Region": 0, "SPCS Same Region": 3.07, "Same Cloud Diff Region": 20, "Diff Cloud/Internet": 90},
    "AWS Asia Pacific (Seoul)":              {"Same Region": 0, "SPCS Same Region": 3.07, "Same Cloud Diff Region": 80, "Diff Cloud/Internet": 126},
    "AWS US Gov West 1":                     {"Same Region": 0, "SPCS Same Region": 7.17, "Same Cloud Diff Region": 30, "Diff Cloud/Internet": 155},
    "AWS US Gov West 1 (FedRAMP High Plus)": {"Same Region": 0, "SPCS Same Region": 7.17, "Same Cloud Diff Region": 30, "Diff Cloud/Internet": 155},
    "AWS Europe (Stockholm)":                {"Same Region": 0, "SPCS Same Region": 3.07, "Same Cloud Diff Region": 20, "Diff Cloud/Internet": 90},
    "AWS Asia Pacific (Osaka)":              {"Same Region": 0, "SPCS Same Region": 3.07, "Same Cloud Diff Region": 90, "Diff Cloud/Internet": 114},
    "AWS South America East 1 (São Paulo)":  {"Same Region": 0, "SPCS Same Region": 3.07, "Same Cloud Diff Region": 138, "Diff Cloud/Internet": 150},
    "AWS EU (Paris)":                        {"Same Region": 0, "SPCS Same Region": 3.07, "Same Cloud Diff Region": 20, "Diff Cloud/Internet": 90},
    "AWS Asia Pacific (Jakarta)":            {"Same Region": 0, "SPCS Same Region": 3.07, "Same Cloud Diff Region": 90, "Diff Cloud/Internet": 120},
    "AWS US Gov East 1 (FedRAMP High Plus)": {"Same Region": 0, "SPCS Same Region": 7.17, "Same Cloud Diff Region": 30, "Diff Cloud/Internet": 155},
    "AWS EU (Zurich)":                       {"Same Region": 0, "SPCS Same Region": 3.07, "Same Cloud Diff Region": 20, "Diff Cloud/Internet": 90},
    "AWS US Gov West 1 (DoD)":               {"Same Region": 0, "SPCS Same Region": 7.17, "Same Cloud Diff Region": 30, "Diff Cloud/Internet": 155},
    "AWS US West (Commercial Gov - Oregon)": {"Same Region": 0, "SPCS Same Region": 3.07, "Same Cloud Diff Region": 20, "Diff Cloud/Internet": 90},
    "AWS Africa (Cape Town)":                {"Same Region": 0, "SPCS Same Region": 3.07, "Same Cloud Diff Region": 80, "Diff Cloud/Internet": 147},
    "AWS Middle East (UAE)":                 {"Same Region": 0, "SPCS Same Region": 3.07, "Same Cloud Diff Region": 90, "Diff Cloud/Internet": 110},
}

# ──────────────────────────────────────────────────────────────────────────────
# Table 6(a): Cortex AI Features — Credits per 1M Tokens
# ──────────────────────────────────────────────────────────────────────────────
CORTEX_AI_MODELS = {
    # ── AI Complete models ──
    "claude-4-opus":                    {"input": 7.50,  "output": 37.50},
    "claude-haiku-4-5":                 {"input": 0.55,  "output": 2.75},
    "claude-opus-4-5":                  {"input": 2.75,  "output": 13.75},
    "claude-opus-4-6":                  {"input": 2.75,  "output": 13.75},
    "claude-opus-4-6-long-context":     {"input": 5.50,  "output": 20.63},
    "claude-sonnet-4-5":                {"input": 1.65,  "output": 8.25},
    "claude-sonnet-4-5-long-context":   {"input": 3.30,  "output": 12.38},
    "claude-sonnet-4-6":                {"input": 1.65,  "output": 8.25},
    "claude-sonnet-4-6-long-context":   {"input": 3.30,  "output": 12.38},
    "deepseek-r1":                      {"input": 0.68,  "output": 2.70},
    "gemini-2-5-flash":                 {"input": 0.15,  "output": 1.25},
    "gemini-2-5-flash-lite":            {"input": 0.05,  "output": 0.20},
    "gemini-3-pro":                     {"input": 1.00,  "output": 6.00},
    "gemini-3-pro-long-context":        {"input": 2.00,  "output": 9.00},
    "llama3.1-405b":                    {"input": 1.20,  "output": 1.20},
    "llama3.1-70b":                     {"input": 0.36,  "output": 0.36},
    "llama3.1-8b":                      {"input": 0.11,  "output": 0.11},
    "llama3.3-70b":                     {"input": 0.36,  "output": 0.36},
    "llama4-maverick":                  {"input": 0.12,  "output": 0.49},
    "llama4-scout":                     {"input": 0.09,  "output": 0.33},
    "mistral-large2":                   {"input": 1.00,  "output": 3.00},
    "mistral-7b":                       {"input": 0.08,  "output": 0.10},
    "mixtral-8x7b":                     {"input": 0.23,  "output": 0.35},
    "openai-gpt-4.1":                   {"input": 1.00,  "output": 4.00},
    "openai-gpt-5":                     {"input": 0.69,  "output": 5.50},
    "openai-gpt-5-mini":                {"input": 0.14,  "output": 1.10},
    "openai-gpt-5-nano":                {"input": 0.03,  "output": 0.22},
    "openai-gpt-5.1":                   {"input": 0.69,  "output": 5.50},
    "openai-gpt-5.2":                   {"input": 0.97,  "output": 7.70},
    "openai-gpt-oss-120b":              {"input": 0.08,  "output": 0.30},
    "openai-gpt-oss-20b":               {"input": 0.04,  "output": 0.15},
    "pixtral-large":                    {"input": 1.00,  "output": 3.00},
    "snowflake-llama-3.1-405b":         {"input": 0.96,  "output": 0.96},
    "snowflake-llama-3.3-70b":          {"input": 0.29,  "output": 0.29},
    # ── Other Cortex functions (single rate = credits per 1M tokens) ──
    "AI Embed Image 1024 – voyage-multimodal-3":        {"input": 0.06, "output": 0},
    "AI Embed Text 1024 – multilingual-e5-large":       {"input": 0.05, "output": 0},
    "AI Embed Text 1024 – snowflake-arctic-embed-l-v2.0": {"input": 0.05, "output": 0},
    "AI Embed Text 1024 – voyage-multilingual-2":       {"input": 0.07, "output": 0},
    "AI Embed Text 768 – e5-base-v2":                   {"input": 0.03, "output": 0},
    "AI Embed Text 768 – snowflake-arctic-embed-m":     {"input": 0.03, "output": 0},
    "AI Sentiment":                     {"input": 1.60,  "output": 0},
    "AI_CLASSIFY":                      {"input": 1.39,  "output": 0},
    "AI_EXTRACT – arctic-extract":      {"input": 5.00,  "output": 0},
    "AI_REDACT":                        {"input": 0.63,  "output": 0},
    "AI_TRANSCRIBE":                    {"input": 1.30,  "output": 0},
    "AI_TRANSLATE":                     {"input": 1.50,  "output": 0},
    "Extract Answer":                   {"input": 0.08,  "output": 0},
    "Guard":                            {"input": 0.25,  "output": 0},
    "Summarize":                        {"input": 0.10,  "output": 0},
    "Translate":                        {"input": 1.50,  "output": 0},
}

# ──────────────────────────────────────────────────────────────────────────────
# STORAGE SECTION
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="section-header">💾 Storage</div>',
    unsafe_allow_html=True)

stor_c1, stor_c2 = st.columns(2)
with stor_c1:
    storage_tb = st.number_input("Standard Storage (TB)",
                                 min_value=0.0, value=5.0, step=0.5)
    storage_price_per_tb = st.number_input(
        "Storage Price ($/TB/month)",
        min_value=0.0, value=23.0, step=1.0,
        help="On-Demand standard storage price from Table 3(a)")
with stor_c2:
    storage_cost = storage_tb * storage_price_per_tb
    st.metric("Monthly Storage Cost", f"${storage_cost:,.2f}")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION: SPCS COMPUTE (Tables 1e, 1f, 1g)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-header">🐳 SPCS Compute (Snowpark Container Services)</div>',
    unsafe_allow_html=True)

st.markdown("""
<p style="color:#a0a0a0; font-size:0.9rem;">
    Compute Nodes are charged per second (5-min minimum on start/resume).
    Select your instance types and estimate running hours.
    <i>Source: Tables 1(e), 1(f), 1(g) in CreditConsumptionTable.pdf</i>
</p>
""", unsafe_allow_html=True)

spcs_num_nodes = st.number_input("Number of SPCS Compute Nodes", min_value=0,
                                  max_value=20, value=0, key="spcs_nodes")

spcs_node_results = []
total_spcs_credits = 0.0
total_spcs_cost = 0.0

for n in range(spcs_num_nodes):
    with st.expander(f"🐳 SPCS Node {n + 1}", expanded=(n == 0)):
        spc_col1, spc_col2, spc_col3 = st.columns(3)

        with spc_col1:
            spcs_family = st.selectbox(
                "Instance Family",
                ["CPU", "High-Memory", "GPU"],
                key=f"spcs_family_{n}")

        # Build instance list based on family
        if spcs_family == "CPU":
            instance_options = list(SPCS_CPU_CREDITS.keys())
        elif spcs_family == "High-Memory":
            instance_options = list(SPCS_HIGHMEM_CREDITS.keys())
        else:
            instance_options = list(SPCS_GPU_CREDITS.keys())

        with spc_col2:
            spcs_instance = st.selectbox(
                "Instance Type",
                instance_options,
                key=f"spcs_instance_{n}")

        with spc_col3:
            spcs_node_count = st.number_input(
                "Number of Nodes",
                min_value=1, max_value=50, value=1,
                key=f"spcs_count_{n}")

        sph_col1, sph_col2 = st.columns(2)
        with sph_col1:
            spcs_hours = st.number_input(
                "Hours per Day",
                min_value=0.0, max_value=24.0, value=8.0, step=1.0,
                key=f"spcs_hours_{n}")
        with sph_col2:
            spcs_days = st.number_input(
                "Days per Month",
                min_value=1, max_value=31, value=days_per_month,
                key=f"spcs_days_{n}")

        # Get credit rate
        if spcs_family == "CPU":
            cr_hr = SPCS_CPU_CREDITS[spcs_instance]["spcs"]
        elif spcs_family == "High-Memory":
            cr_hr = SPCS_HIGHMEM_CREDITS[spcs_instance]
        else:
            cr_hr = SPCS_GPU_CREDITS[spcs_instance]

        monthly_hrs = spcs_hours * spcs_days
        node_credits = cr_hr * monthly_hrs * spcs_node_count
        node_cost = node_credits * credit_price

        total_spcs_credits += node_credits
        total_spcs_cost += node_cost

        st.markdown(f"""
        <div style="background:rgba(208,74,2,0.08); padding:10px;
                    border-radius:8px; margin-top:8px;">
            <span style="color:#D04A02; font-weight:700;">
                {cr_hr} credits/hr × {monthly_hrs:.0f} hrs × {spcs_node_count} nodes
                = <u>{node_credits:,.2f} credits</u>
                (${node_cost:,.2f}/month)
            </span>
        </div>
        """, unsafe_allow_html=True)

        spcs_node_results.append({
            "Node": f"SPCS Node {n + 1}",
            "Family": spcs_family,
            "Instance": spcs_instance,
            "Count": spcs_node_count,
            "Credits/Hr": cr_hr,
            "Monthly Hours": monthly_hrs,
            "Monthly Credits": round(node_credits, 2),
            "Monthly Cost ($)": round(node_cost, 2),
        })


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: OPENFLOW COMPUTE (Table 1h)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-header">🔄 Snowflake Openflow Compute</div>',
    unsafe_allow_html=True)

st.markdown("""
<p style="color:#a0a0a0; font-size:0.9rem;">
    Openflow Compute is charged per second with a 60-second minimum.
    BYOC Deployment: <b style="color:#D04A02;">0.0225 Credits per vCPU per Hour</b>.
    SPCS Deployment uses SPCS CPU rates above.
    <i>Source: Table 1(h) in CreditConsumptionTable.pdf</i>
</p>
""", unsafe_allow_html=True)

ofc_col1, ofc_col2, ofc_col3 = st.columns(3)

with ofc_col1:
    openflow_deployment = st.selectbox(
        "Deployment Type",
        ["None", "BYOC Deployment", "Snowflake Deployment (SPCS)"],
        key="openflow_type")

total_openflow_credits = 0.0
total_openflow_cost = 0.0

if openflow_deployment == "BYOC Deployment":
    with ofc_col2:
        openflow_vcpus = st.number_input(
            "Number of vCPUs", min_value=1, max_value=1000, value=4,
            key="openflow_vcpus")
    with ofc_col3:
        openflow_hours = st.number_input(
            "Hours per Month", min_value=0.0, max_value=744.0,
            value=float(total_hours), step=1.0, key="openflow_hours")

    total_openflow_credits = 0.0225 * openflow_vcpus * openflow_hours
    total_openflow_cost = total_openflow_credits * credit_price

    st.info(f"💡 Openflow BYOC: {openflow_vcpus} vCPUs × {openflow_hours:.0f} hrs "
            f"× 0.0225 cr/vCPU/hr = **{total_openflow_credits:,.2f} credits** "
            f"(${total_openflow_cost:,.2f}/month)")

elif openflow_deployment == "Snowflake Deployment (SPCS)":
    st.info("💡 Snowflake Deployment (SPCS) uses SPCS CPU instance rates from "
            "Table 1(e). Configure those in the SPCS Compute section above.")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: POSTGRES COMPUTE (Table 1i)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-header">🐘 Snowflake Postgres Compute</div>',
    unsafe_allow_html=True)

st.markdown("""
<p style="color:#a0a0a0; font-size:0.9rem;">
    Postgres Compute is available on <b>AWS</b> and <b>Azure</b> only.
    Billed per second with a 1-minute minimum on start/resume.
    <i>Source: Table 1(i) in CreditConsumptionTable.pdf</i>
</p>
""", unsafe_allow_html=True)

total_postgres_credits = 0.0
total_postgres_cost = 0.0
postgres_results = []

pg_enabled = st.checkbox("Enable Postgres Compute Estimation",
                          key="pg_enabled")

if pg_enabled:
    if cloud_provider == "GCP":
        st.warning("⚠️ Postgres Compute is not available on GCP. "
                   "Please select AWS or Azure in the sidebar.")
    else:
        pg_num = st.number_input("Number of Postgres Nodes",
                                  min_value=1, max_value=10, value=1,
                                  key="pg_num")

        for p in range(pg_num):
            with st.expander(f"🐘 Postgres Node {p + 1}", expanded=(p == 0)):
                pgc1, pgc2, pgc3 = st.columns(3)

                # Filter instances available for this cloud
                available_instances = [
                    inst for inst, data in POSTGRES_COMPUTE.items()
                    if cloud_provider in data and
                    data[cloud_provider]["standard"] is not None
                ]

                with pgc1:
                    pg_instance = st.selectbox(
                        "Instance Family",
                        available_instances,
                        key=f"pg_inst_{p}")

                with pgc2:
                    pg_ha = st.selectbox(
                        "High Availability",
                        ["Standard", "High Availability"],
                        key=f"pg_ha_{p}")

                with pgc3:
                    pg_hours_month = st.number_input(
                        "Hours per Month",
                        min_value=0.0, max_value=744.0,
                        value=float(total_hours), step=1.0,
                        key=f"pg_hours_{p}")

                ha_key = "ha" if pg_ha == "High Availability" else "standard"
                pg_cr_hr = POSTGRES_COMPUTE[pg_instance][cloud_provider][ha_key]
                pg_credits = pg_cr_hr * pg_hours_month
                pg_cost = pg_credits * credit_price

                total_postgres_credits += pg_credits
                total_postgres_cost += pg_cost

                st.markdown(f"""
                <div style="background:rgba(208,74,2,0.08); padding:10px;
                            border-radius:8px; margin-top:8px;">
                    <span style="color:#D04A02; font-weight:700;">
                        {pg_cr_hr} credits/hr × {pg_hours_month:.0f} hrs
                        = <u>{pg_credits:,.4f} credits</u>
                        (${pg_cost:,.2f}/month)
                    </span>
                </div>
                """, unsafe_allow_html=True)

                postgres_results.append({
                    "Node": f"Postgres {p + 1}",
                    "Instance": pg_instance,
                    "Mode": pg_ha,
                    "Cloud": cloud_provider,
                    "Credits/Hr": pg_cr_hr,
                    "Monthly Hours": pg_hours_month,
                    "Monthly Credits": round(pg_credits, 4),
                    "Monthly Cost ($)": round(pg_cost, 2),
                })


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: HYBRID TABLES STORAGE (Table 3b)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-header">🔗 Hybrid Tables Storage</div>',
    unsafe_allow_html=True)

st.markdown("""
<p style="color:#a0a0a0; font-size:0.9rem;">
    Hybrid Tables storage is priced per <b>GB per month</b>.
    <i>Source: Table 3(b) in CreditConsumptionTable.pdf</i>
</p>
""", unsafe_allow_html=True)

hybrid_storage_cost = 0.0

htc1, htc2, htc3 = st.columns(3)

# Lookup price based on region
hybrid_regions = HYBRID_STORAGE_PRICING.get(cloud_provider, {})
hybrid_region_list = list(hybrid_regions.keys()) if hybrid_regions else []

with htc1:
    hybrid_region_sel = st.selectbox(
        "Region",
        hybrid_region_list if hybrid_region_list else ["N/A"],
        key="hybrid_region")

with htc2:
    hybrid_gb = st.number_input(
        "Hybrid Table Storage (GB)",
        min_value=0.0, max_value=100000.0, value=0.0, step=10.0,
        key="hybrid_gb")

hybrid_price_gb = hybrid_regions.get(hybrid_region_sel, 0.34) if hybrid_region_list else 0.34

with htc3:
    st.metric("Price ($/GB/month)", f"${hybrid_price_gb:.2f}")

hybrid_storage_cost = hybrid_gb * hybrid_price_gb

if hybrid_gb > 0:
    st.info(f"💡 Hybrid Tables: {hybrid_gb:,.0f} GB × ${hybrid_price_gb:.2f}/GB "
            f"= **${hybrid_storage_cost:,.2f}/month**")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: SPCS BLOCK STORAGE (Table 3c)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-header">📦 SPCS Block Storage</div>',
    unsafe_allow_html=True)

st.markdown("""
<p style="color:#a0a0a0; font-size:0.9rem;">
    SPCS Block Storage includes Volume, IOPS, Throughput, and Snapshot costs.
    <i>Source: Table 3(c) in CreditConsumptionTable.pdf</i>
</p>
""", unsafe_allow_html=True)

spcs_storage_cost = 0.0

block_regions = SPCS_BLOCK_STORAGE.get(cloud_provider, {})
block_region_list = list(block_regions.keys()) if block_regions else []

if block_region_list:
    bsc1, bsc2 = st.columns(2)

    with bsc1:
        block_region_sel = st.selectbox(
            "Region", block_region_list, key="block_region")

    block_pricing = block_regions.get(block_region_sel, {})

    with bsc2:
        st.markdown(f"""
        <div style="background:rgba(208,74,2,0.08); padding:10px;
                    border-radius:8px;">
            <b style="color:#D04A02;">Region Pricing:</b><br>
            Volume: <b>${block_pricing.get('volume', 0):.2f}</b>/TB/mo |
            IOPS: <b>${block_pricing.get('iops', 0) or 'N/A'}</b>/1K IOPS-mo |
            Throughput: <b>${block_pricing.get('throughput', 0):.2f}</b>/GB/sec-mo |
            Snapshot: <b>${block_pricing.get('snapshot', 0):.2f}</b>/TB/mo
        </div>
        """, unsafe_allow_html=True)

    bs_col1, bs_col2, bs_col3, bs_col4 = st.columns(4)

    with bs_col1:
        block_vol_tb = st.number_input(
            "Block Storage Volume (TB)",
            min_value=0.0, max_value=1000.0, value=0.0, step=0.5,
            key="block_vol")
    with bs_col2:
        block_iops_k = st.number_input(
            "IOPS (thousands)",
            min_value=0.0, max_value=10000.0, value=0.0, step=1.0,
            key="block_iops")
    with bs_col3:
        block_throughput = st.number_input(
            "Throughput (GB/sec)",
            min_value=0.0, max_value=100.0, value=0.0, step=0.5,
            key="block_tp")
    with bs_col4:
        block_snapshot_tb = st.number_input(
            "Snapshot (TB)",
            min_value=0.0, max_value=1000.0, value=0.0, step=0.5,
            key="block_snap")

    vol_cost = block_vol_tb * block_pricing.get("volume", 0)
    iops_cost = block_iops_k * (block_pricing.get("iops", 0) or 0)
    tp_cost = block_throughput * block_pricing.get("throughput", 0)
    snap_cost = block_snapshot_tb * block_pricing.get("snapshot", 0)
    spcs_storage_cost = vol_cost + iops_cost + tp_cost + snap_cost

    if spcs_storage_cost > 0:
        st.info(f"💡 SPCS Block Storage Total: "
                f"Vol ${vol_cost:,.2f} + IOPS ${iops_cost:,.2f} + "
                f"Throughput ${tp_cost:,.2f} + Snapshot ${snap_cost:,.2f} "
                f"= **${spcs_storage_cost:,.2f}/month**")
else:
    st.warning(f"⚠️ SPCS Block Storage data not available for {cloud_provider}.")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: ARCHIVE STORAGE & DATA RETRIEVAL (Table 3e)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-header">🗃️ Archive Storage & Data Retrieval</div>',
    unsafe_allow_html=True)

st.markdown("""
<p style="color:#a0a0a0; font-size:0.9rem;">
    Archive Storage is a low-cost tier for infrequently accessed data.
    Retrieval costs apply when accessing archived data.
    <i>Source: Table 3(e) in CreditConsumptionTable.pdf</i>
</p>
""", unsafe_allow_html=True)

archive_cost = 0.0

archive_regions = ARCHIVE_STORAGE_PRICING.get(cloud_provider, {})
archive_region_list = list(archive_regions.keys()) if archive_regions else []

if archive_region_list:
    arc1, arc2, arc3 = st.columns(3)

    with arc1:
        archive_region_sel = st.selectbox(
            "Region", archive_region_list, key="archive_region")

    archive_prices = archive_regions.get(archive_region_sel, {})

    with arc2:
        archive_tb = st.number_input(
            "Archive Storage (TB)",
            min_value=0.0, max_value=10000.0, value=0.0, step=1.0,
            key="archive_tb")

    with arc3:
        archive_retrieval_tb = st.number_input(
            "Data Retrieval (TB/month)",
            min_value=0.0, max_value=10000.0, value=0.0, step=1.0,
            key="archive_retrieval_tb")

    storage_price = archive_prices.get("storage", 4.00)
    retrieval_price = archive_prices.get("retrieval", 30.00)

    archive_storage_total = archive_tb * storage_price
    archive_retrieval_total = archive_retrieval_tb * retrieval_price
    archive_cost = archive_storage_total + archive_retrieval_total

    if archive_cost > 0:
        st.info(f"💡 Archive: Storage {archive_tb} TB × ${storage_price}/TB "
                f"= ${archive_storage_total:,.2f} | "
                f"Retrieval {archive_retrieval_tb} TB × ${retrieval_price}/TB "
                f"= ${archive_retrieval_total:,.2f} | "
                f"**Total: ${archive_cost:,.2f}/month**")
else:
    st.warning(f"⚠️ Archive Storage data not available for {cloud_provider}.")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: POSTGRES STORAGE (Table 3f)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-header">🐘 Snowflake Postgres Storage</div>',
    unsafe_allow_html=True)

st.markdown("""
<p style="color:#a0a0a0; font-size:0.9rem;">
    Postgres Storage is available on <b>AWS</b> and <b>Azure</b>.
    High Availability doubles the storage cost.
    <i>Source: Table 3(f) in CreditConsumptionTable.pdf</i>
</p>
""", unsafe_allow_html=True)

postgres_storage_cost = 0.0

pg_storage_regions = POSTGRES_STORAGE_PRICING.get(cloud_provider, {})
pg_storage_region_list = list(pg_storage_regions.keys()) if pg_storage_regions else []

if pg_storage_region_list:
    psc1, psc2, psc3 = st.columns(3)

    with psc1:
        pg_storage_region_sel = st.selectbox(
            "Region", pg_storage_region_list, key="pg_storage_region")

    with psc2:
        pg_storage_tb = st.number_input(
            "Postgres Storage (TB)",
            min_value=0.0, max_value=1000.0, value=0.0, step=0.5,
            key="pg_storage_tb")

    with psc3:
        pg_storage_ha = st.selectbox(
            "Mode",
            ["Standard", "High Availability"],
            key="pg_storage_ha")

    pg_s_prices = pg_storage_regions.get(pg_storage_region_sel, {})
    pg_ha_key = "ha" if pg_storage_ha == "High Availability" else "standard"
    pg_price_tb = pg_s_prices.get(pg_ha_key, 117.76)

    postgres_storage_cost = pg_storage_tb * pg_price_tb

    if postgres_storage_cost > 0:
        st.info(f"💡 Postgres Storage ({pg_storage_ha}): "
                f"{pg_storage_tb} TB × ${pg_price_tb:,.2f}/TB "
                f"= **${postgres_storage_cost:,.2f}/month**")
elif cloud_provider == "GCP":
    st.warning("⚠️ Postgres Storage is not available on GCP.")
else:
    st.warning("⚠️ No Postgres Storage data available for this selection.")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION: OUTBOUND PRIVATELINK (Table 4e)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-header">🔒 Outbound PrivateLink</div>',
    unsafe_allow_html=True)

st.markdown("""
<p style="color:#a0a0a0; font-size:0.9rem;">
    Outbound PrivateLink incurs charges for endpoints and data processed.
    Data processed uses a tiered pricing model based on volume.
    <i>Source: Table 4(e) in CreditConsumptionTable.pdf</i>
</p>
""", unsafe_allow_html=True)

privatelink_cost = 0.0

pl_regions = PRIVATELINK_PRICING.get(cloud_provider, {})
pl_region_list = list(pl_regions.keys()) if pl_regions else []

if pl_region_list:
    plc1, plc2, plc3 = st.columns(3)

    with plc1:
        pl_region_sel = st.selectbox(
            "Region", pl_region_list, key="pl_region")

    pl_prices = pl_regions.get(pl_region_sel, {})

    with plc2:
        pl_endpoints = st.number_input(
            "Number of Endpoints",
            min_value=0, max_value=100, value=0, key="pl_endpoints")

    with plc3:
        pl_hours = st.number_input(
            "Endpoint Hours/month (per endpoint)",
            min_value=0.0, max_value=744.0, value=720.0, step=1.0,
            key="pl_hours")

    pl_data_col1, pl_data_col2 = st.columns(2)

    with pl_data_col1:
        pl_data_tb = st.number_input(
            "Data Processed (TB/month)",
            min_value=0.0, max_value=100000.0, value=0.0, step=1.0,
            key="pl_data_tb")

    # Calculate endpoint cost
    endpoint_cost_per_k_hrs = pl_prices.get("endpoint", 10.00)
    total_endpoint_hours = pl_endpoints * pl_hours
    endpoint_cost = (total_endpoint_hours / 1000.0) * endpoint_cost_per_k_hrs

    # Calculate tiered data processing cost
    first_1pb_rate = pl_prices.get("first_1pb", 10.24)
    next_4pb_rate = pl_prices.get("next_4pb", 6.14)
    over_5pb_rate = pl_prices.get("over_5pb", 4.09)

    data_tb = pl_data_tb
    data_cost = 0.0

    # First 1 PB = 1024 TB
    if data_tb <= 1024:
        data_cost = data_tb * first_1pb_rate
    elif data_tb <= 5120:  # 5 PB = 5120 TB
        data_cost = (1024 * first_1pb_rate) + ((data_tb - 1024) * next_4pb_rate)
    else:
        data_cost = ((1024 * first_1pb_rate) +
                     (4096 * next_4pb_rate) +
                     ((data_tb - 5120) * over_5pb_rate))

    privatelink_cost = endpoint_cost + data_cost

    if privatelink_cost > 0:
        with pl_data_col2:
            st.markdown(f"""
            <div style="background:rgba(208,74,2,0.08); padding:10px;
                        border-radius:8px;">
                <b style="color:#D04A02;">PrivateLink Breakdown:</b><br>
                Endpoints: ${endpoint_cost:,.2f} |
                Data: ${data_cost:,.2f}<br>
                <b>Total: ${privatelink_cost:,.2f}/month</b>
            </div>
            """, unsafe_allow_html=True)
else:
    st.warning(f"⚠️ PrivateLink pricing not available for {cloud_provider}.")

# ──────────────────────────────────────────────────────────────────────────────
# DATA TRANSFER SECTION
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="section-header">🔄 Data Transfer</div>',
    unsafe_allow_html=True)

dt_col1, dt_col2, dt_col3 = st.columns(3)

with dt_col1:
    transfer_type = st.selectbox(
        "Transfer Type",
        ["Same Cloud Diff Region", "Diff Cloud/Internet",
         "SPCS Same Region", "Same Region"],
        index=0,
        help="Type of data transfer per Table 4(a/b/c)")

with dt_col2:
    transfer_tb = st.number_input(
        "Data Transfer Volume (TB/month)",
        min_value=0.0, value=1.0, step=0.5,
        help="Total TB transferred per month")

with dt_col3:
    # Resolve price per TB from the data
    if cloud_provider == "AWS":
        dt_lookup = AWS_DATA_TRANSFER
        # Try exact region match, else default
        dt_price_per_tb = 0.0
        for dt_key, dt_vals in dt_lookup.items():
            if dt_key in region or region in dt_key:
                dt_price_per_tb = dt_vals.get(transfer_type, 0)
                break
        if dt_price_per_tb == 0 and transfer_type != "Same Region":
            dt_price_per_tb = 90.0  # sensible default
    else:
        # Azure/GCP defaults based on PDF patterns
        default_dt = {
            "Same Region": 0,
            "SPCS Same Region": 0,
            "Same Cloud Diff Region": 20.0,
            "Diff Cloud/Internet": 87.50
        }
        dt_price_per_tb = default_dt.get(transfer_type, 20.0)

    st.metric("Price per TB", f"${dt_price_per_tb:,.2f}")

data_transfer_cost = transfer_tb * dt_price_per_tb
st.info(f"📡 **Monthly Data Transfer Cost:** ${data_transfer_cost:,.2f} "
        f"({transfer_tb:.1f} TB × ${dt_price_per_tb:,.2f}/TB)")

# ──────────────────────────────────────────────────────────────────────────────
# AI FEATURES / CORTEX TOKENS SECTION
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="section-header">🤖 Snowflake AI Features (Cortex)</div>',
    unsafe_allow_html=True)

st.caption("Pricing from Table 6(a) — Credits per 1 million Tokens")

selected_ai_models = st.multiselect(
    "Select AI Models in use",
    list(CORTEX_AI_MODELS.keys()),
    help="Select Cortex AI models you plan to use. "
         "Pricing is in Credits per 1M Tokens from Table 6(a).")

ai_model_configs = []
if selected_ai_models:
    ai_cols_per_row = 2
    for idx, model in enumerate(selected_ai_models):
        if idx % ai_cols_per_row == 0:
            ai_cols = st.columns(ai_cols_per_row)
        ai_col = ai_cols[idx % ai_cols_per_row]

        with ai_col:
            with st.expander(f"🧠 {model}", expanded=True):
                rates = CORTEX_AI_MODELS[model]

                st.markdown(
                    f"**Rates:** Input: `{rates['input']}` credits/1M tokens"
                    + (f" | Output: `{rates['output']}` credits/1M tokens"
                       if rates['output'] > 0 else ""))

                input_tokens = st.number_input(
                    "Input Tokens (millions/month)",
                    min_value=0.0, value=1.0, step=0.5,
                    key=f"ai_input_{model}")

                if rates["output"] > 0:
                    output_tokens = st.number_input(
                        "Output Tokens (millions/month)",
                        min_value=0.0, value=0.5, step=0.5,
                        key=f"ai_output_{model}")
                else:
                    output_tokens = 0.0

                input_credits = input_tokens * rates["input"]
                output_credits = output_tokens * rates["output"]
                total_model_credits = input_credits + output_credits
                total_model_cost = total_model_credits * credit_price

                st.markdown(
                    f"**Credits:** {input_credits:.2f} (in) + "
                    f"{output_credits:.2f} (out) = "
                    f"**{total_model_credits:.2f} credits** "
                    f"→ **${total_model_cost:,.2f}**")

                ai_model_configs.append({
                    "Model": model,
                    "Input Rate (cr/1M)": rates["input"],
                    "Output Rate (cr/1M)": rates["output"],
                    "Input Tokens (M)": input_tokens,
                    "Output Tokens (M)": output_tokens,
                    "Input Credits": round(input_credits, 4),
                    "Output Credits": round(output_credits, 4),
                    "Total Credits": round(total_model_credits, 4),
                    "Monthly Cost ($)": round(total_model_cost, 2),
                })

total_ai_credits = sum(c["Total Credits"] for c in ai_model_configs)
total_ai_cost = sum(c["Monthly Cost ($)"] for c in ai_model_configs)

# ──────────────────────────────────────────────────────────────────────────────
# CALCULATIONS
# ──────────────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────────
# CALCULATIONS (UPDATED WITH DATA TRANSFER + AI)
# ──────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-header">📊 Cost Estimation Results</div>',
    unsafe_allow_html=True)

# ── Warehouse credits (same as before) ──
wh_results = []
for wh in warehouse_configs:
    monthly_credits = wh["effective_cph"] * total_hours
    monthly_cost = monthly_credits * credit_price
    wh_results.append({
        "Warehouse": wh["name"],
        "Type": wh["type"],
        "Size": wh["size"],
        "Constraint": wh["constraint"],
        "Clusters": wh["clusters"],
        "Credits/Hour": wh["credits_per_hour"],
        "Effective Credits/Hour": wh["effective_cph"],
        "Monthly Credits": round(monthly_credits, 2),
        "Monthly Cost ($)": round(monthly_cost, 2),
    })

total_wh_credits = sum(r["Monthly Credits"] for r in wh_results)
total_wh_cost = sum(r["Monthly Cost ($)"] for r in wh_results)

# ── Cloud Services (same as before) ──
daily_wh_credits = (total_wh_credits / days_per_month
                    if days_per_month > 0 else 0)
daily_cs_credits = cloud_services_hours * CLOUD_SERVICES_CREDITS_PER_HOUR

if apply_cs_adjustment and daily_cs_credits <= (0.10 * daily_wh_credits):
    effective_daily_cs_credits = 0
    cs_note = "✅ Cloud Services charges waived (≤ 10% of daily VW credits)"
else:
    effective_daily_cs_credits = daily_cs_credits
    cs_note = "⚠️ Cloud Services charges apply (> 10% of daily VW credits)"

total_cs_credits = effective_daily_cs_credits * days_per_month
total_cs_cost = total_cs_credits * credit_price

# ── Serverless (same as before) ──
total_sf_credits = 0
sf_details = []
for feat in selected_serverless:
    info = SERVERLESS_FEATURES[feat]
    hrs = serverless_hours.get(feat, 0)
    if info["compute_mult"] is not None:
        feat_credits = hrs * info["compute_mult"]
    else:
        feat_credits = 0
    total_sf_credits += feat_credits
    sf_details.append({
        "Feature": feat,
        "Compute-Hours": hrs,
        "Multiplier": info["compute_mult"] if info["compute_mult"] else "N/A",
        "Credits": round(feat_credits, 2),
    })
total_sf_cost = total_sf_credits * credit_price

# ── Grand totals (NOW INCLUDES DATA TRANSFER + AI) ──

# ══════════════════════════════════════════════════════════════════════════════
# UPDATED GRAND TOTAL CALCULATION
# ══════════════════════════════════════════════════════════════════════════════

# All credit-based costs
grand_total_credits = (
    total_wh_credits +
    total_cs_credits +
    total_sf_credits +
    total_ai_credits +
    total_spcs_credits +
    total_openflow_credits +
    total_postgres_credits
)

# All dollar costs (credits × price + direct $ charges)
grand_total_cost = (
    total_wh_cost +
    total_cs_cost +
    total_sf_cost +
    storage_cost +
    data_transfer_cost +
    total_ai_cost +
    total_spcs_cost +
    total_openflow_cost +
    total_postgres_cost +
    hybrid_storage_cost +
    spcs_storage_cost +
    archive_cost +
    postgres_storage_cost +
    privatelink_cost
)

# ──────────────────────────────────────────────────────────────────────────────
# METRIC CARDS
# ──────────────────────────────────────────────────────────────────────────────

m1, m2, m3 = st.columns(3)
m4, m5, m6 = st.columns(3)

with m1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">🏗️ Warehouse Credits</div>
        <div class="metric-value">{total_wh_credits:,.1f}</div>
        <div class="metric-sub">${total_wh_cost:,.2f} / month</div>
    </div>""", unsafe_allow_html=True)

with m2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">☁️ Cloud Services</div>
        <div class="metric-value">{total_cs_credits:,.1f}</div>
        <div class="metric-sub">${total_cs_cost:,.2f} / month</div>
    </div>""", unsafe_allow_html=True)

with m3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">⚡ Serverless</div>
        <div class="metric-value">{total_sf_credits:,.1f}</div>
        <div class="metric-sub">${total_sf_cost:,.2f} / month</div>
    </div>""", unsafe_allow_html=True)

with m4:
    st.markdown(f"""
    <div class="metric-card" style="border-color: #f97316;">
        <div class="metric-label">🔄 Data Transfer</div>
        <div class="metric-value" style="color:#f97316;">
            {transfer_tb:.1f} TB</div>
        <div class="metric-sub">${data_transfer_cost:,.2f} / month</div>
    </div>""", unsafe_allow_html=True)

with m5:
    st.markdown(f"""
    <div class="metric-card" style="border-color: #22c55e;">
        <div class="metric-label">🤖 AI / Cortex</div>
        <div class="metric-value" style="color:#22c55e;">
            {total_ai_credits:,.2f}</div>
        <div class="metric-sub">${total_ai_cost:,.2f} / month</div>
    </div>""", unsafe_allow_html=True)

with m6:
    st.markdown(f"""
    <div class="metric-card" style="border-color: #a855f7;">
        <div class="metric-label">💎 GRAND TOTAL</div>
        <div class="metric-value" style="color:#a855f7;">
            ${grand_total_cost:,.2f}</div>
        <div class="metric-sub">{grand_total_credits:,.1f} credits + 
            ${data_transfer_cost:,.2f} transfer</div>
    </div>""", unsafe_allow_html=True)

st.markdown(
    f"<p style='text-align:center;color:#6c6c8a;margin-top:8px;'>"
    f"{cs_note}</p>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# WAREHOUSE BREAKDOWN — PLOTLY TABLE (NO MATPLOTLIB)
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="section-header">📋 Warehouse Breakdown</div>',
    unsafe_allow_html=True)

wh_df = pd.DataFrame(wh_results)

# Build a beautiful Plotly table with gradient row colours
cost_values = [r["Monthly Cost ($)"] for r in wh_results]
row_colors = generate_gradient_colors(cost_values)

header_color = "rgba(41,181,232,0.25)"
fig_table = go.Figure(data=[go.Table(
    columnwidth=[120, 160, 60, 90, 60, 90, 110, 110, 120],
    header=dict(
        values=[f"<b>{c}</b>" for c in wh_df.columns],
        fill_color=header_color,
        align="center",
        font=dict(color="white", size=13, family="Arial Black"),
        line_color="rgba(41,181,232,0.4)",
        height=36,
    ),
    cells=dict(
        values=[wh_df[c].tolist() for c in wh_df.columns],
        fill_color=[row_colors * 1 for _ in wh_df.columns],
        align="center",
        font=dict(color="white", size=12),
        line_color="rgba(255,255,255,0.08)",
        height=32,
        format=[None, None, None, None, None, ".2f", ".2f", ",.2f", "$,.2f"],
    ),
)])
fig_table.update_layout(
    margin=dict(l=0, r=0, t=10, b=10),
    paper_bgcolor="rgba(0,0,0,0)",
    height=45 + 36 * max(len(wh_results), 1),
)
st.plotly_chart(fig_table, use_container_width=True)

# ── Updated Metric Cards Layout (4 rows × 3 columns) ──

# Row 1 (existing)
mc_r1c1, mc_r1c2, mc_r1c3 = st.columns(3)
with mc_r1c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">🏗️ WAREHOUSES</div>
        <div class="metric-value">${total_wh_cost:,.2f}</div>
        <div class="metric-sub">{total_wh_credits:,.1f} credits</div>
    </div>""", unsafe_allow_html=True)

with mc_r1c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">☁️ CLOUD SERVICES</div>
        <div class="metric-value">${total_cs_cost:,.2f}</div>
        <div class="metric-sub">{total_cs_credits:,.1f} credits</div>
    </div>""", unsafe_allow_html=True)

with mc_r1c3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">⚡ SERVERLESS</div>
        <div class="metric-value">${total_sf_cost:,.2f}</div>
        <div class="metric-sub">{total_sf_credits:,.1f} credits</div>
    </div>""", unsafe_allow_html=True)

# Row 2
mc_r2c1, mc_r2c2, mc_r2c3 = st.columns(3)
with mc_r2c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">🐳 SPCS COMPUTE</div>
        <div class="metric-value">${total_spcs_cost:,.2f}</div>
        <div class="metric-sub">{total_spcs_credits:,.1f} credits</div>
    </div>""", unsafe_allow_html=True)

with mc_r2c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">🔄 OPENFLOW</div>
        <div class="metric-value">${total_openflow_cost:,.2f}</div>
        <div class="metric-sub">{total_openflow_credits:,.1f} credits</div>
    </div>""", unsafe_allow_html=True)

with mc_r2c3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">🐘 POSTGRES COMPUTE</div>
        <div class="metric-value">${total_postgres_cost:,.2f}</div>
        <div class="metric-sub">{total_postgres_credits:,.4f} credits</div>
    </div>""", unsafe_allow_html=True)

# Row 3
mc_r3c1, mc_r3c2, mc_r3c3 = st.columns(3)
with mc_r3c1:
    combined_storage = storage_cost + hybrid_storage_cost + spcs_storage_cost + archive_cost + postgres_storage_cost
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">💾 ALL STORAGE</div>
        <div class="metric-value">${combined_storage:,.2f}</div>
        <div class="metric-sub">
            Std: ${storage_cost:,.0f} | Hybrid: ${hybrid_storage_cost:,.0f} |
            SPCS: ${spcs_storage_cost:,.0f}<br>
            Archive: ${archive_cost:,.0f} | Postgres: ${postgres_storage_cost:,.0f}
        </div>
    </div>""", unsafe_allow_html=True)

with mc_r3c2:
    combined_transfer = data_transfer_cost + privatelink_cost
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">🔄 DATA TRANSFER & PRIVATELINK</div>
        <div class="metric-value">${combined_transfer:,.2f}</div>
        <div class="metric-sub">
            Transfer: ${data_transfer_cost:,.2f} |
            PrivateLink: ${privatelink_cost:,.2f}
        </div>
    </div>""", unsafe_allow_html=True)

with mc_r3c3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">🤖 AI / CORTEX</div>
        <div class="metric-value">${total_ai_cost:,.2f}</div>
        <div class="metric-sub">{total_ai_credits:,.1f} credits</div>
    </div>""", unsafe_allow_html=True)

# Row 4 — Grand Total (full width)
st.markdown(f"""
<div class="metric-card" style="border-color:#FFB600;
     box-shadow: 0 4px 30px rgba(255,182,0,0.2);">
    <div class="metric-label" style="font-size:1rem;">💎 GRAND TOTAL — MONTHLY</div>
    <div class="metric-value" style="font-size:3rem; color:#FFB600;">
        ${grand_total_cost:,.2f}
    </div>
    <div class="metric-sub" style="font-size:1rem;">
        {grand_total_credits:,.1f} total credits |
        Annual: <b style="color:#D04A02;">${grand_total_cost * 12:,.2f}</b>
    </div>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# SERVERLESS DETAIL TABLE
# ──────────────────────────────────────────────────────────────────────────────
if sf_details:
    st.markdown(
        '<div class="section-header">'
        '⚡ Serverless Feature Breakdown</div>',
        unsafe_allow_html=True)

    sf_df = pd.DataFrame(sf_details)
    sf_cost_vals = [r["Credits"] for r in sf_details]
    sf_row_colors = generate_gradient_colors(sf_cost_vals)

    fig_sf_table = go.Figure(data=[go.Table(
        header=dict(
            values=[f"<b>{c}</b>" for c in sf_df.columns],
            fill_color=header_color,
            align="center",
            font=dict(color="white", size=13, family="Arial Black"),
            line_color="rgba(41,181,232,0.4)",
            height=36,
        ),
        cells=dict(
            values=[sf_df[c].tolist() for c in sf_df.columns],
            fill_color=[sf_row_colors for _ in sf_df.columns],
            align="center",
            font=dict(color="white", size=12),
            line_color="rgba(255,255,255,0.08)",
            height=32,
        ),
    )])
    fig_sf_table.update_layout(
        margin=dict(l=0, r=0, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        height=45 + 36 * max(len(sf_details), 1),
    )
    st.plotly_chart(fig_sf_table, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# VISUALIZATIONS
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="section-header">📈 Visual Analytics</div>',
    unsafe_allow_html=True)

viz_c1, viz_c2 = st.columns(2)

# PIE — Cost Breakdown
with viz_c1:
    cost_breakdown = {
        "Virtual Warehouses": total_wh_cost,
        "Cloud Services": total_cs_cost,
        "Serverless Features": total_sf_cost,
        "Storage": storage_cost,
    }
    cost_breakdown = {k: v for k, v in cost_breakdown.items() if v > 0}

    fig_pie = go.Figure(data=[go.Pie(
        labels=list(cost_breakdown.keys()),
        values=list(cost_breakdown.values()),
        hole=0.55,
        marker=dict(
            colors=["#29b5e8", "#a855f7", "#f97316", "#22c55e"],
            line=dict(color="#1a1a3e", width=3)),
        textinfo="label+percent",
        textfont=dict(size=13, color="white"),
        hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<br>"
                      "%{percent}<extra></extra>",
    )])
    fig_pie.update_layout(
        title=dict(text="Monthly Cost Distribution",
                   font=dict(size=18, color="#29b5e8")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        legend=dict(font=dict(color="white", size=12)),
        height=420,
        annotations=[dict(
            text=f"${grand_total_cost:,.0f}", x=0.5, y=0.5,
            font_size=22, font_color="#a855f7", showarrow=False)],
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# BAR — Per-Warehouse Credits
with viz_c2:
    fig_bar = go.Figure()
    wh_names = [r["Warehouse"] for r in wh_results]
    wh_credits_vals = [r["Monthly Credits"] for r in wh_results]
    wh_cost_vals = [r["Monthly Cost ($)"] for r in wh_results]

    fig_bar.add_trace(go.Bar(
        x=wh_names, y=wh_credits_vals, name="Credits",
        marker=dict(color="#29b5e8",
                    line=dict(color="#1e90ff", width=1)),
        text=[f"{v:,.0f}" for v in wh_credits_vals],
        textposition="outside",
        textfont=dict(color="white"),
        hovertemplate="<b>%{x}</b><br>Credits: %{y:,.1f}<extra></extra>",
    ))
    fig_bar.add_trace(go.Bar(
        x=wh_names, y=wh_cost_vals, name="Cost ($)",
        marker=dict(color="#a855f7",
                    line=dict(color="#9333ea", width=1)),
        text=[f"${v:,.0f}" for v in wh_cost_vals],
        textposition="outside",
        textfont=dict(color="white"),
        hovertemplate="<b>%{x}</b><br>Cost: $%{y:,.2f}<extra></extra>",
    ))
    fig_bar.update_layout(
        title=dict(text="Per-Warehouse Monthly Credits & Cost",
                   font=dict(size=18, color="#29b5e8")),
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        xaxis=dict(showgrid=False, color="white"),
        yaxis=dict(showgrid=True,
                   gridcolor="rgba(255,255,255,0.1)", color="white"),
        legend=dict(font=dict(color="white")),
        height=420,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# 12-MONTH PROJECTION
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="section-header">📅 12-Month Cost Projection</div>',
    unsafe_allow_html=True)

months = [f"Month {i+1}" for i in range(12)]
monthly_wh = [total_wh_cost] * 12
monthly_cs = [total_cs_cost] * 12
monthly_sf = [total_sf_cost] * 12
monthly_stor = [storage_cost] * 12
cumulative = []
running = 0
for i in range(12):
    running += monthly_wh[i] + monthly_cs[i] + monthly_sf[i] + monthly_stor[i]
    cumulative.append(running)

fig_area = go.Figure()
fig_area.add_trace(go.Scatter(
    x=months, y=monthly_wh, name="Warehouses", stackgroup="one",
    line=dict(width=0), fillcolor="rgba(41,181,232,0.5)"))
fig_area.add_trace(go.Scatter(
    x=months, y=monthly_cs, name="Cloud Services", stackgroup="one",
    line=dict(width=0), fillcolor="rgba(168,85,247,0.5)"))
fig_area.add_trace(go.Scatter(
    x=months, y=monthly_sf, name="Serverless", stackgroup="one",
    line=dict(width=0), fillcolor="rgba(249,115,22,0.5)"))
fig_area.add_trace(go.Scatter(
    x=months, y=monthly_stor, name="Storage", stackgroup="one",
    line=dict(width=0), fillcolor="rgba(34,197,94,0.5)"))
fig_area.add_trace(go.Scatter(
    x=months, y=cumulative, name="Cumulative",
    mode="lines+markers",
    line=dict(color="#f43f5e", width=3, dash="dot"),
    marker=dict(size=8, color="#f43f5e"),
    yaxis="y2"))

fig_area.update_layout(
    title=dict(text="12-Month Spend Projection",
               font=dict(size=18, color="#29b5e8")),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="white"),
    xaxis=dict(showgrid=False, color="white"),
    yaxis=dict(title="Monthly ($)", showgrid=True,
               gridcolor="rgba(255,255,255,0.1)", color="white"),
    yaxis2=dict(title="Cumulative ($)", overlaying="y",
                side="right", color="#f43f5e", showgrid=False),
    legend=dict(font=dict(color="white"), orientation="h",
                yanchor="bottom", y=1.02, xanchor="right", x=1),
    height=450,
)
st.plotly_chart(fig_area, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# HEATMAP — FIXED (no titlefont / tickfont issues)
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="section-header">'
    '🔥 Credits/Hour Heatmap — Standard & Interactive</div>',
    unsafe_allow_html=True)

heatmap_sizes = ["XS", "S", "M", "L", "XL", "2XL", "3XL", "4XL"]
heatmap_types = ["Standard", "Gen 2 (AWS)", "Interactive"]
z_data = []
for wt in heatmap_types:
    row = []
    for sz in heatmap_sizes:
        if wt == "Standard":
            row.append(STANDARD_WH_CREDITS.get(sz, 0))
        elif wt == "Gen 2 (AWS)":
            row.append(GEN2_WH_CREDITS["AWS"].get(sz, 0))
        elif wt == "Interactive":
            row.append(INTERACTIVE_WH_CREDITS.get(sz, 0))
    z_data.append(row)

fig_heat = go.Figure(data=go.Heatmap(
    z=z_data,
    x=heatmap_sizes,
    y=heatmap_types,
    colorscale=[
        [0, "#0f2744"], [0.25, "#1e3a5f"],
        [0.5, "#29b5e8"], [0.75, "#a855f7"], [1, "#f43f5e"]],
    text=[[str(v) for v in row] for row in z_data],
    texttemplate="%{text}",
    textfont=dict(size=14, color="white"),
    hovertemplate="Type: %{y}<br>Size: %{x}<br>"
                  "Credits/Hr: %{z}<extra></extra>",
    colorbar=dict(
        title=dict(text="Credits/Hr", font=dict(color="white")),
        tickfont=dict(color="white"),
    ),
))
fig_heat.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="white"),
    xaxis=dict(title="Warehouse Size", color="white"),
    yaxis=dict(title="Warehouse Type", color="white"),
    height=300,
)
st.plotly_chart(fig_heat, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# SCENARIO COMPARISON
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="section-header">'
    '🔀 Quick Scenario Comparison — Standard Warehouse</div>',
    unsafe_allow_html=True)

sc_col1, sc_col2, sc_col3 = st.columns(3)
with sc_col1:
    sc_sizes = st.multiselect(
        "Sizes to Compare",
        list(STANDARD_WH_CREDITS.keys()),
        default=["S", "M", "L", "XL"])
with sc_col2:
    sc_hours_list = st.multiselect(
        "Daily Hour Profiles", [4, 8, 12, 16, 24], default=[8, 12, 24])
with sc_col3:
    sc_days = st.number_input("Working Days/Month", 1, 31, 22,
                              key="sc_days")

if sc_sizes and sc_hours_list:
    scenario_rows = []
    for sz in sc_sizes:
        for hrs in sc_hours_list:
            cred = STANDARD_WH_CREDITS[sz]
            mo_credits = cred * hrs * sc_days
            mo_cost = mo_credits * credit_price
            scenario_rows.append({
                "Size": sz,
                "Hours/Day": hrs,
                "Credits/Hour": cred,
                "Monthly Credits": mo_credits,
                "Monthly Cost ($)": mo_cost,
            })
    sc_df = pd.DataFrame(scenario_rows)

    fig_sc = px.bar(
        sc_df, x="Size", y="Monthly Cost ($)",
        color="Hours/Day", barmode="group",
        color_continuous_scale=["#29b5e8", "#a855f7", "#f43f5e"],
        text="Monthly Cost ($)")
    fig_sc.update_traces(
        texttemplate="$%{text:,.0f}", textposition="outside",
        textfont_color="white")
    fig_sc.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        xaxis=dict(color="white", showgrid=False),
        yaxis=dict(color="white", showgrid=True,
                   gridcolor="rgba(255,255,255,0.1)"),
        height=420,
    )
    st.plotly_chart(fig_sc, use_container_width=True)

    # Scenario table — Plotly (no matplotlib)
    sc_cost_vals = sc_df["Monthly Cost ($)"].tolist()
    sc_row_colors = generate_gradient_colors(sc_cost_vals)

    fig_sc_tbl = go.Figure(data=[go.Table(
        header=dict(
            values=[f"<b>{c}</b>" for c in sc_df.columns],
            fill_color=header_color,
            align="center",
            font=dict(color="white", size=13, family="Arial Black"),
            line_color="rgba(41,181,232,0.4)",
            height=36,
        ),
        cells=dict(
            values=[sc_df[c].tolist() for c in sc_df.columns],
            fill_color=[sc_row_colors for _ in sc_df.columns],
            align="center",
            font=dict(color="white", size=12),
            line_color="rgba(255,255,255,0.08)",
            height=32,
            format=[None, None, ",.0f", ",.0f", "$,.2f"],
        ),
    )])
    fig_sc_tbl.update_layout(
        margin=dict(l=0, r=0, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        height=45 + 36 * max(len(scenario_rows), 1),
    )
    st.plotly_chart(fig_sc_tbl, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# SERVERLESS REFERENCE TABLE
# ──────────────────────────────────────────────────────────────────────────────
with st.expander("📚 Serverless Feature Reference (Table 5)", expanded=False):
    ref_rows = []
    for feat, info in SERVERLESS_FEATURES.items():
        ref_rows.append({
            "Feature": feat,
            "Compute Multiplier": (info["compute_mult"]
                                   if info["compute_mult"] is not None
                                   else "—"),
            "Cloud Services Multiplier": (info["cs_mult"]
                                          if info["cs_mult"] is not None
                                          else "—"),
            "Unit Charge": info["unit_charge"] if info["unit_charge"] else "—",
        })
    st.dataframe(pd.DataFrame(ref_rows),
                 use_container_width=True, hide_index=True)

# ──────────────────────────────────────────────────────────────────────────────
# CREDIT REFERENCE TABLES
# ──────────────────────────────────────────────────────────────────────────────
with st.expander("📖 Warehouse Credit Reference Tables", expanded=False):
    tab1, tab2, tab3, tab4 = st.tabs(
        ["Standard", "Gen 2", "Snowpark Optimized", "Interactive"])

    with tab1:
        st.markdown("**Table 1(a): Standard Warehouse — Credits/Hour**")
        st.dataframe(pd.DataFrame([STANDARD_WH_CREDITS]), hide_index=True)

    with tab2:
        st.markdown("**Table 1(b): Gen 2 Warehouse — Credits/Hour**")
        st.dataframe(pd.DataFrame(GEN2_WH_CREDITS).T,
                     use_container_width=True)

    with tab3:
        st.markdown("**Table 1(c): Snowpark Optimized — Credits/Hour**")
        sp_df = pd.DataFrame(SNOWPARK_WH_CREDITS).T.fillna("—")
        st.dataframe(sp_df, use_container_width=True)

    with tab4:
        st.markdown("**Table 1(d): Interactive Warehouse — Credits/Hour**")
        st.dataframe(pd.DataFrame([INTERACTIVE_WH_CREDITS]),
                     hide_index=True)

# ──────────────────────────────────────────────────────────────────────────────
# AWS REGION PRICING REFERENCE
# ──────────────────────────────────────────────────────────────────────────────
with st.expander("🌎 AWS On-Demand Credit Pricing by Region (Table 2)",
                 expanded=False):
    pricing_rows = []
    for reg, editions_dict in AWS_ON_DEMAND_PRICING.items():
        pricing_rows.append({"Region": reg, **editions_dict})
    pricing_df = pd.DataFrame(pricing_rows)
    st.dataframe(pricing_df, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# DOWNLOAD ESTIMATION REPORT (Corrected — No Indentation Errors)
# ══════════════════════════════════════════════════════════════════════════════
import io
import json
from datetime import datetime

st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-header">📥 Download Estimation Report</div>',
    unsafe_allow_html=True)

st.markdown("""
<p style="color:#a0a0a0; font-size:0.95rem;">
    Export your complete cost estimation as a downloadable file.
    Choose between <b style="color:#D04A02;">Excel (.xlsx)</b> for detailed
    multi-sheet workbooks, <b style="color:#FFB600;">CSV (.csv)</b> for
    quick single-sheet exports, <b style="color:#EB8C00;">PDF (.pdf)</b> for
    executive summaries, or <b style="color:#D04A02;">JSON (.json)</b> for
    machine-readable output.
</p>
""", unsafe_allow_html=True)

report_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

dl_col1, dl_col2 = st.columns(2)

# ──────────────────────────────────────────────────────────────────────────────
# EXCEL DOWNLOAD
# ──────────────────────────────────────────────────────────────────────────────
with dl_col1:
    st.markdown("""
    <div class="metric-card" style="border-color:#D04A02; padding:16px;">
        <div class="metric-label">📊 EXCEL WORKBOOK</div>
        <div style="color:#a0a0a0; font-size:0.8rem; margin-top:6px;">
            Multi-sheet report with all categories, summaries, and configuration details
        </div>
    </div>
    """, unsafe_allow_html=True)

    excel_buffer = io.BytesIO()

    with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:

        # ── Sheet 1: Executive Summary ──
        summary_rows = {
            "Parameter": [
                "Report Generated",
                "Cloud Provider",
                "Region",
                "Snowflake Edition",
                "Credit Price ($/credit)",
                "Hours per Day",
                "Days per Month",
                "Total Monthly Hours",
                "",
                "── COST BREAKDOWN ──",
                "Virtual Warehouse Credits",
                "Virtual Warehouse Cost ($)",
                "Cloud Services Credits",
                "Cloud Services Cost ($)",
                "Serverless Credits",
                "Serverless Cost ($)",
                "SPCS Compute Credits",
                "SPCS Compute Cost ($)",
                "Openflow Compute Credits",
                "Openflow Compute Cost ($)",
                "Postgres Compute Credits",
                "Postgres Compute Cost ($)",
                "Standard Storage Cost ($)",
                "Hybrid Tables Storage Cost ($)",
                "SPCS Block Storage Cost ($)",
                "Archive Storage Cost ($)",
                "Postgres Storage Cost ($)",
                "Data Transfer Cost ($)",
                "PrivateLink Cost ($)",
                "AI / Cortex Credits",
                "AI / Cortex Cost ($)",
                "",
                "── GRAND TOTALS ──",
                "Total Monthly Credits",
                "Total Monthly Cost ($)",
                "Estimated Annual Cost ($)",
            ],
            "Value": [
                report_timestamp,
                cloud_provider,
                region,
                edition,
                f"${credit_price:.2f}",
                hours_per_day,
                days_per_month,
                total_hours,
                "",
                "",
                round(total_wh_credits, 2),
                f"${total_wh_cost:,.2f}",
                round(total_cs_credits, 2),
                f"${total_cs_cost:,.2f}",
                round(total_sf_credits, 2),
                f"${total_sf_cost:,.2f}",
                round(total_spcs_credits, 2),
                f"${total_spcs_cost:,.2f}",
                round(total_openflow_credits, 2),
                f"${total_openflow_cost:,.2f}",
                round(total_postgres_credits, 4),
                f"${total_postgres_cost:,.2f}",
                f"${storage_cost:,.2f}",
                f"${hybrid_storage_cost:,.2f}",
                f"${spcs_storage_cost:,.2f}",
                f"${archive_cost:,.2f}",
                f"${postgres_storage_cost:,.2f}",
                f"${data_transfer_cost:,.2f}",
                f"${privatelink_cost:,.2f}",
                round(total_ai_credits, 2),
                f"${total_ai_cost:,.2f}",
                "",
                "",
                round(grand_total_credits, 2),
                f"${grand_total_cost:,.2f}",
                f"${grand_total_cost * 12:,.2f}",
            ]
        }
        df_summary = pd.DataFrame(summary_rows)
        df_summary.to_excel(writer, sheet_name="Executive Summary", index=False)

        # ── Sheet 2: Warehouse Breakdown ──
        if wh_results:
            df_wh = pd.DataFrame(wh_results)
            df_wh.to_excel(writer, sheet_name="Warehouse Breakdown", index=False)

        # ── Sheet 3: Cloud Services ──
        cs_sheet = {
            "Parameter": [
                "CS Hours per Day",
                "CS Credits per Hour",
                "Daily CS Credits",
                "10% Adjustment Applied",
                "Daily WH Credits",
                "10% Threshold",
                "Effective Daily CS Credits",
                "Monthly CS Credits",
                "Monthly CS Cost ($)",
            ],
            "Value": [
                cloud_services_hours,
                4.4,
                round(daily_cs_credits, 2),
                "Yes" if apply_cs_adjustment else "No",
                round(daily_wh_credits, 2),
                round(0.10 * daily_wh_credits, 2),
                round(effective_daily_cs_credits, 2),
                round(total_cs_credits, 2),
                round(total_cs_cost, 2),
            ]
        }
        df_cs = pd.DataFrame(cs_sheet)
        df_cs.to_excel(writer, sheet_name="Cloud Services", index=False)

        # ── Sheet 4: Serverless Features ──
        if sf_details:
            df_sf = pd.DataFrame(sf_details)
            df_sf.to_excel(writer, sheet_name="Serverless Features", index=False)

        # ── Sheet 5: SPCS Compute ──
        if spcs_node_results:
            df_spcs = pd.DataFrame(spcs_node_results)
            df_spcs.to_excel(writer, sheet_name="SPCS Compute", index=False)

        # ── Sheet 6: Postgres Compute ──
        if postgres_results:
            df_pg = pd.DataFrame(postgres_results)
            df_pg.to_excel(writer, sheet_name="Postgres Compute", index=False)

        # ── Sheet 7: Standard Storage ──
        storage_sheet = {
            "Parameter": [
                "Storage Volume (TB)",
                "Price per TB ($/month)",
                "Monthly Storage Cost ($)",
                "Annual Storage Cost ($)",
            ],
            "Value": [
                storage_tb,
                storage_price_per_tb,
                round(storage_cost, 2),
                round(storage_cost * 12, 2),
            ]
        }
        df_storage = pd.DataFrame(storage_sheet)
        df_storage.to_excel(writer, sheet_name="Standard Storage", index=False)

        # ── Sheet 8: Additional Storage ──
        add_storage_rows = []
        add_storage_rows.append({
            "Storage Type": "Hybrid Tables",
            "Volume": f"{hybrid_gb:.0f} GB",
            "Unit Price": f"${hybrid_price_gb:.2f}/GB/mo",
            "Monthly Cost ($)": round(hybrid_storage_cost, 2),
            "Annual Cost ($)": round(hybrid_storage_cost * 12, 2),
        })
        add_storage_rows.append({
            "Storage Type": "SPCS Block Storage (Volume)",
            "Volume": f"{block_vol_tb:.1f} TB" if 'block_vol_tb' in dir() else "0 TB",
            "Unit Price": f"${block_pricing.get('volume', 0):.2f}/TB/mo" if 'block_pricing' in dir() else "N/A",
            "Monthly Cost ($)": round(vol_cost, 2) if 'vol_cost' in dir() else 0,
            "Annual Cost ($)": round((vol_cost if 'vol_cost' in dir() else 0) * 12, 2),
        })
        add_storage_rows.append({
            "Storage Type": "SPCS Block Storage (IOPS)",
            "Volume": f"{block_iops_k:.0f}K IOPS" if 'block_iops_k' in dir() else "0",
            "Unit Price": f"${block_pricing.get('iops', 0) or 0:.2f}/1K IOPS-mo" if 'block_pricing' in dir() else "N/A",
            "Monthly Cost ($)": round(iops_cost, 2) if 'iops_cost' in dir() else 0,
            "Annual Cost ($)": round((iops_cost if 'iops_cost' in dir() else 0) * 12, 2),
        })
        add_storage_rows.append({
            "Storage Type": "SPCS Block Storage (Throughput)",
            "Volume": f"{block_throughput:.1f} GB/sec" if 'block_throughput' in dir() else "0",
            "Unit Price": f"${block_pricing.get('throughput', 0):.2f}/GB/sec-mo" if 'block_pricing' in dir() else "N/A",
            "Monthly Cost ($)": round(tp_cost, 2) if 'tp_cost' in dir() else 0,
            "Annual Cost ($)": round((tp_cost if 'tp_cost' in dir() else 0) * 12, 2),
        })
        add_storage_rows.append({
            "Storage Type": "SPCS Block Storage (Snapshot)",
            "Volume": f"{block_snapshot_tb:.1f} TB" if 'block_snapshot_tb' in dir() else "0",
            "Unit Price": f"${block_pricing.get('snapshot', 0):.2f}/TB/mo" if 'block_pricing' in dir() else "N/A",
            "Monthly Cost ($)": round(snap_cost, 2) if 'snap_cost' in dir() else 0,
            "Annual Cost ($)": round((snap_cost if 'snap_cost' in dir() else 0) * 12, 2),
        })
        add_storage_rows.append({
            "Storage Type": "Archive Storage",
            "Volume": f"{archive_tb:.1f} TB" if 'archive_tb' in dir() else "0 TB",
            "Unit Price": f"${archive_prices.get('storage', 0):.2f}/TB/mo" if 'archive_prices' in dir() else "N/A",
            "Monthly Cost ($)": round(archive_storage_total, 2) if 'archive_storage_total' in dir() else 0,
            "Annual Cost ($)": round((archive_storage_total if 'archive_storage_total' in dir() else 0) * 12, 2),
        })
        add_storage_rows.append({
            "Storage Type": "Archive Data Retrieval",
            "Volume": f"{archive_retrieval_tb:.1f} TB/mo" if 'archive_retrieval_tb' in dir() else "0 TB",
            "Unit Price": f"${archive_prices.get('retrieval', 0):.2f}/TB" if 'archive_prices' in dir() else "N/A",
            "Monthly Cost ($)": round(archive_retrieval_total, 2) if 'archive_retrieval_total' in dir() else 0,
            "Annual Cost ($)": round((archive_retrieval_total if 'archive_retrieval_total' in dir() else 0) * 12, 2),
        })
        add_storage_rows.append({
            "Storage Type": "Postgres Storage",
            "Volume": f"{pg_storage_tb:.1f} TB" if 'pg_storage_tb' in dir() else "0 TB",
            "Unit Price": f"${pg_price_tb:,.2f}/TB/mo" if 'pg_price_tb' in dir() else "N/A",
            "Monthly Cost ($)": round(postgres_storage_cost, 2),
            "Annual Cost ($)": round(postgres_storage_cost * 12, 2),
        })
        df_add_storage = pd.DataFrame(add_storage_rows)
        df_add_storage.to_excel(writer, sheet_name="Additional Storage", index=False)

        # ── Sheet 9: Data Transfer ──
        transfer_sheet = {
            "Parameter": [
                "Transfer Type",
                "Transfer Volume (TB/month)",
                "Price per TB ($)",
                "Monthly Transfer Cost ($)",
                "Annual Transfer Cost ($)",
            ],
            "Value": [
                transfer_type,
                transfer_tb,
                dt_price_per_tb,
                round(data_transfer_cost, 2),
                round(data_transfer_cost * 12, 2),
            ]
        }
        df_transfer = pd.DataFrame(transfer_sheet)
        df_transfer.to_excel(writer, sheet_name="Data Transfer", index=False)

        # ── Sheet 10: PrivateLink ──
        pl_sheet = {
            "Parameter": [
                "Region",
                "Number of Endpoints",
                "Endpoint Hours/month",
                "Endpoint Cost ($)",
                "Data Processed (TB/month)",
                "Data Processing Cost ($)",
                "Total PrivateLink Cost ($)",
                "Annual PrivateLink Cost ($)",
            ],
            "Value": [
                pl_region_sel if 'pl_region_sel' in dir() else "N/A",
                pl_endpoints if 'pl_endpoints' in dir() else 0,
                pl_hours if 'pl_hours' in dir() else 0,
                round(endpoint_cost, 2) if 'endpoint_cost' in dir() else 0,
                pl_data_tb if 'pl_data_tb' in dir() else 0,
                round(data_cost, 2) if 'data_cost' in dir() else 0,
                round(privatelink_cost, 2),
                round(privatelink_cost * 12, 2),
            ]
        }
        df_pl = pd.DataFrame(pl_sheet)
        df_pl.to_excel(writer, sheet_name="PrivateLink", index=False)

        # ── Sheet 11: AI / Cortex Models ──
        if ai_model_configs:
            df_ai = pd.DataFrame(ai_model_configs)
            df_ai.to_excel(writer, sheet_name="AI Cortex Models", index=False)

        # ── Sheet 12: Openflow ──
        openflow_sheet = {
            "Parameter": [
                "Deployment Type",
                "vCPUs (BYOC only)",
                "Hours per Month",
                "Rate (Credits/vCPU/hr)",
                "Monthly Credits",
                "Monthly Cost ($)",
                "Annual Cost ($)",
            ],
            "Value": [
                openflow_deployment if 'openflow_deployment' in dir() else "None",
                openflow_vcpus if 'openflow_vcpus' in dir() else "N/A",
                openflow_hours if 'openflow_hours' in dir() else 0,
                0.0225,
                round(total_openflow_credits, 2),
                round(total_openflow_cost, 2),
                round(total_openflow_cost * 12, 2),
            ]
        }
        df_openflow = pd.DataFrame(openflow_sheet)
        df_openflow.to_excel(writer, sheet_name="Openflow Compute", index=False)

        # ── Sheet 13: 12-Month Projection ──
        projection_rows = []
        for month_num in range(1, 13):
            projection_rows.append({
                "Month": month_num,
                "Warehouse ($)": round(total_wh_cost, 2),
                "Cloud Services ($)": round(total_cs_cost, 2),
                "Serverless ($)": round(total_sf_cost, 2),
                "SPCS Compute ($)": round(total_spcs_cost, 2),
                "Openflow ($)": round(total_openflow_cost, 2),
                "Postgres Compute ($)": round(total_postgres_cost, 2),
                "Standard Storage ($)": round(storage_cost, 2),
                "Hybrid Storage ($)": round(hybrid_storage_cost, 2),
                "SPCS Block Storage ($)": round(spcs_storage_cost, 2),
                "Archive Storage ($)": round(archive_cost, 2),
                "Postgres Storage ($)": round(postgres_storage_cost, 2),
                "Data Transfer ($)": round(data_transfer_cost, 2),
                "PrivateLink ($)": round(privatelink_cost, 2),
                "AI / Cortex ($)": round(total_ai_cost, 2),
                "Monthly Total ($)": round(grand_total_cost, 2),
                "Cumulative Total ($)": round(grand_total_cost * month_num, 2),
            })
        df_projection = pd.DataFrame(projection_rows)
        df_projection.to_excel(writer, sheet_name="12-Month Projection", index=False)

        # ── Format workbook ──
        workbook = writer.book
        header_fmt = workbook.add_format({
            "bold": True, "font_color": "#FFFFFF",
            "bg_color": "#D04A02", "border": 1,
            "text_wrap": True, "valign": "vcenter", "align": "center",
        })
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            worksheet.set_column("A:A", 38)
            worksheet.set_column("B:Z", 24)
            worksheet.freeze_panes(1, 0)

    excel_data = excel_buffer.getvalue()

    st.download_button(
        label="📊  Download Excel Report (.xlsx)",
        data=excel_data,
        file_name=f"Snowflake_Estimation_{cloud_provider}_{edition}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

# ──────────────────────────────────────────────────────────────────────────────
# CSV DOWNLOAD
# ──────────────────────────────────────────────────────────────────────────────
with dl_col2:
    st.markdown("""
    <div class="metric-card" style="border-color:#FFB600; padding:16px;">
        <div class="metric-label">📄 CSV EXPORT</div>
        <div style="color:#a0a0a0; font-size:0.8rem; margin-top:6px;">
            Consolidated single-file export suitable for further analysis or import
        </div>
    </div>
    """, unsafe_allow_html=True)

    csv_rows = []
    blank = {"Section": "", "Item": "", "Detail": "",
             "Credits": "", "Monthly Cost ($)": "", "Annual Cost ($)": ""}

    # ── Config ──
    csv_rows.append({"Section": "CONFIGURATION", "Item": "Report Generated",
                     "Detail": report_timestamp, "Credits": "",
                     "Monthly Cost ($)": "", "Annual Cost ($)": ""})
    csv_rows.append({"Section": "", "Item": "Cloud Provider",
                     "Detail": cloud_provider, "Credits": "",
                     "Monthly Cost ($)": "", "Annual Cost ($)": ""})
    csv_rows.append({"Section": "", "Item": "Region",
                     "Detail": region, "Credits": "",
                     "Monthly Cost ($)": "", "Annual Cost ($)": ""})
    csv_rows.append({"Section": "", "Item": "Edition",
                     "Detail": edition, "Credits": "",
                     "Monthly Cost ($)": "", "Annual Cost ($)": ""})
    csv_rows.append({"Section": "", "Item": "Credit Price",
                     "Detail": f"${credit_price:.2f}", "Credits": "",
                     "Monthly Cost ($)": "", "Annual Cost ($)": ""})
    csv_rows.append({"Section": "", "Item": "Usage Period",
                     "Detail": f"{hours_per_day}h/day x {days_per_month}d/mo = {total_hours}h",
                     "Credits": "", "Monthly Cost ($)": "",
                     "Annual Cost ($)": ""})
    csv_rows.append(blank.copy())

    # ── Warehouses ──
    for wh in wh_results:
        csv_rows.append({
            "Section": "WAREHOUSE",
            "Item": wh["Warehouse"],
            "Detail": f"{wh['Type']} | {wh['Size']} | {wh['Clusters']} cluster(s)",
            "Credits": wh["Monthly Credits"],
            "Monthly Cost ($)": wh["Monthly Cost ($)"],
            "Annual Cost ($)": round(wh["Monthly Cost ($)"] * 12, 2),
        })
    csv_rows.append(blank.copy())

    # ── Cloud Services ──
    csv_rows.append({
        "Section": "CLOUD SERVICES",
        "Item": f"CS ({cloud_services_hours} hrs/day)",
        "Detail": cs_note if 'cs_note' in dir() else "",
        "Credits": round(total_cs_credits, 2),
        "Monthly Cost ($)": round(total_cs_cost, 2),
        "Annual Cost ($)": round(total_cs_cost * 12, 2),
    })
    csv_rows.append(blank.copy())

    # ── Serverless ──
    for sf in sf_details:
        csv_rows.append({
            "Section": "SERVERLESS",
            "Item": sf["Feature"],
            "Detail": f"Multiplier: {sf['Multiplier']}",
            "Credits": sf["Credits"],
            "Monthly Cost ($)": round(sf["Credits"] * credit_price, 2),
            "Annual Cost ($)": round(sf["Credits"] * credit_price * 12, 2),
        })
    csv_rows.append(blank.copy())

    # ── SPCS Compute ──
    for sn in spcs_node_results:
        csv_rows.append({
            "Section": "SPCS COMPUTE",
            "Item": sn["Node"],
            "Detail": f"{sn['Family']} | {sn['Instance']} | {sn['Count']} nodes",
            "Credits": sn["Monthly Credits"],
            "Monthly Cost ($)": sn["Monthly Cost ($)"],
            "Annual Cost ($)": round(sn["Monthly Cost ($)"] * 12, 2),
        })
    csv_rows.append(blank.copy())

    # ── Openflow ──
    if total_openflow_credits > 0:
        csv_rows.append({
            "Section": "OPENFLOW",
            "Item": openflow_deployment if 'openflow_deployment' in dir() else "N/A",
            "Detail": f"{openflow_vcpus} vCPUs" if 'openflow_vcpus' in dir() else "",
            "Credits": round(total_openflow_credits, 2),
            "Monthly Cost ($)": round(total_openflow_cost, 2),
            "Annual Cost ($)": round(total_openflow_cost * 12, 2),
        })
        csv_rows.append(blank.copy())

    # ── Postgres Compute ──
    for pg in postgres_results:
        csv_rows.append({
            "Section": "POSTGRES COMPUTE",
            "Item": pg["Node"],
            "Detail": f"{pg['Instance']} | {pg['Mode']} | {pg['Cloud']}",
            "Credits": pg["Monthly Credits"],
            "Monthly Cost ($)": pg["Monthly Cost ($)"],
            "Annual Cost ($)": round(pg["Monthly Cost ($)"] * 12, 2),
        })
    csv_rows.append(blank.copy())

    # ── All Storage ──
    csv_rows.append({
        "Section": "STORAGE", "Item": "Standard Storage",
        "Detail": f"{storage_tb} TB @ ${storage_price_per_tb}/TB",
        "Credits": "N/A",
        "Monthly Cost ($)": round(storage_cost, 2),
        "Annual Cost ($)": round(storage_cost * 12, 2),
    })
    csv_rows.append({
        "Section": "", "Item": "Hybrid Tables Storage",
        "Detail": f"{hybrid_gb:.0f} GB @ ${hybrid_price_gb:.2f}/GB",
        "Credits": "N/A",
        "Monthly Cost ($)": round(hybrid_storage_cost, 2),
        "Annual Cost ($)": round(hybrid_storage_cost * 12, 2),
    })
    csv_rows.append({
        "Section": "", "Item": "SPCS Block Storage",
        "Detail": "Volume + IOPS + Throughput + Snapshot",
        "Credits": "N/A",
        "Monthly Cost ($)": round(spcs_storage_cost, 2),
        "Annual Cost ($)": round(spcs_storage_cost * 12, 2),
    })
    csv_rows.append({
        "Section": "", "Item": "Archive Storage + Retrieval",
        "Detail": f"Storage + Retrieval",
        "Credits": "N/A",
        "Monthly Cost ($)": round(archive_cost, 2),
        "Annual Cost ($)": round(archive_cost * 12, 2),
    })
    csv_rows.append({
        "Section": "", "Item": "Postgres Storage",
        "Detail": f"{pg_storage_tb:.1f} TB" if 'pg_storage_tb' in dir() else "0 TB",
        "Credits": "N/A",
        "Monthly Cost ($)": round(postgres_storage_cost, 2),
        "Annual Cost ($)": round(postgres_storage_cost * 12, 2),
    })
    csv_rows.append(blank.copy())

    # ── Data Transfer & PrivateLink ──
    csv_rows.append({
        "Section": "DATA TRANSFER",
        "Item": f"{transfer_tb} TB ({transfer_type})",
        "Detail": f"${dt_price_per_tb}/TB",
        "Credits": "N/A",
        "Monthly Cost ($)": round(data_transfer_cost, 2),
        "Annual Cost ($)": round(data_transfer_cost * 12, 2),
    })
    csv_rows.append({
        "Section": "PRIVATELINK",
        "Item": f"{pl_endpoints if 'pl_endpoints' in dir() else 0} endpoints",
        "Detail": f"{pl_data_tb if 'pl_data_tb' in dir() else 0} TB processed",
        "Credits": "N/A",
        "Monthly Cost ($)": round(privatelink_cost, 2),
        "Annual Cost ($)": round(privatelink_cost * 12, 2),
    })
    csv_rows.append(blank.copy())

    # ── AI / Cortex ──
    for ai in ai_model_configs:
        csv_rows.append({
            "Section": "AI / CORTEX",
            "Item": ai["Model"],
            "Detail": f"In: {ai['Input Tokens (M)']}M | Out: {ai['Output Tokens (M)']}M",
            "Credits": ai["Total Credits"],
            "Monthly Cost ($)": ai["Monthly Cost ($)"],
            "Annual Cost ($)": round(ai["Monthly Cost ($)"] * 12, 2),
        })
    csv_rows.append(blank.copy())

    # ── Grand Total ──
    csv_rows.append({
        "Section": "═══ GRAND TOTAL ═══",
        "Item": "",
        "Detail": "",
        "Credits": round(grand_total_credits, 2),
        "Monthly Cost ($)": round(grand_total_cost, 2),
        "Annual Cost ($)": round(grand_total_cost * 12, 2),
    })

    df_csv = pd.DataFrame(csv_rows)
    csv_data = df_csv.to_csv(index=False)

    st.download_button(
        label="📄  Download CSV Report (.csv)",
        data=csv_data,
        file_name=f"Snowflake_Estimation_{cloud_provider}_{edition}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

# ──────────────────────────────────────────────────────────────────────────────
# PDF DOWNLOAD
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)

pdf_col1, pdf_col2, pdf_col3 = st.columns([1, 2, 1])
with pdf_col2:
    st.markdown("""
    <div class="metric-card" style="border-color:#EB8C00; padding:16px;">
        <div class="metric-label">📑 PDF EXECUTIVE SUMMARY</div>
        <div style="color:#a0a0a0; font-size:0.8rem; margin-top:6px;">
            PwC-branded executive summary with all key metrics and complete cost breakdown
        </div>
    </div>
    """, unsafe_allow_html=True)

    try:
        from fpdf import FPDF as FPDF_LIB

        class ReportPDF(FPDF_LIB):
            def header(self):
                self.set_fill_color(208, 74, 2)
                self.rect(0, 0, 210, 4, "F")
                self.set_fill_color(255, 182, 0)
                self.rect(0, 4, 210, 1.5, "F")
                self.set_y(8)
                self.set_font("Helvetica", "B", 8)
                self.set_text_color(208, 74, 2)
                self.cell(95, 5, "PwC  |  Snowflake Credit Consumption Estimation")
                self.set_text_color(150, 150, 150)
                self.cell(95, 5, report_timestamp, align="R",
                          new_x="LMARGIN", new_y="NEXT")
                self.ln(2)

            def footer(self):
                self.set_y(-15)
                self.set_fill_color(45, 45, 45)
                self.rect(0, self.get_y() - 1, 210, 18, "F")
                self.set_font("Helvetica", "I", 7)
                self.set_text_color(150, 150, 150)
                self.cell(0, 10,
                          f"Page {self.page_no()} | PwC Snowflake Estimation | Confidential",
                          align="C")

        pdf = ReportPDF()
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        # ── Title ──
        pdf.set_font("Helvetica", "B", 22)
        pdf.set_text_color(208, 74, 2)
        pdf.cell(0, 12, "Snowflake Cost Estimation Report",
                 new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6,
                 f"Cloud: {cloud_provider}  |  Region: {region}  |  "
                 f"Edition: {edition}  |  Credit: ${credit_price:.2f}",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6,
                 f"Usage: {hours_per_day} hrs/day x {days_per_month} days/mo "
                 f"= {total_hours} hrs/month",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

        # ── Divider ──
        pdf.set_draw_color(208, 74, 2)
        pdf.set_line_width(0.5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

        # ── Summary Table ──
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(208, 74, 2)
        pdf.cell(0, 8, "Complete Monthly Cost Summary",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        # Header row
        col_w = [68, 33, 38, 41]
        headers = ["Category", "Credits", "Monthly ($)", "Annual ($)"]
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(208, 74, 2)
        pdf.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            pdf.cell(col_w[i], 7, h, border=1, fill=True, align="C")
        pdf.ln()

        # Data rows
        cost_rows = [
            ("Virtual Warehouses", f"{total_wh_credits:,.1f}",
             f"${total_wh_cost:,.2f}", f"${total_wh_cost * 12:,.2f}"),
            ("Cloud Services", f"{total_cs_credits:,.1f}",
             f"${total_cs_cost:,.2f}", f"${total_cs_cost * 12:,.2f}"),
            ("Serverless Features", f"{total_sf_credits:,.1f}",
             f"${total_sf_cost:,.2f}", f"${total_sf_cost * 12:,.2f}"),
            ("SPCS Compute (CPU/HiMem/GPU)", f"{total_spcs_credits:,.1f}",
             f"${total_spcs_cost:,.2f}", f"${total_spcs_cost * 12:,.2f}"),
            ("Openflow Compute", f"{total_openflow_credits:,.1f}",
             f"${total_openflow_cost:,.2f}", f"${total_openflow_cost * 12:,.2f}"),
            ("Postgres Compute", f"{total_postgres_credits:,.4f}",
             f"${total_postgres_cost:,.2f}", f"${total_postgres_cost * 12:,.2f}"),
            ("Standard Storage", "N/A",
             f"${storage_cost:,.2f}", f"${storage_cost * 12:,.2f}"),
            ("Hybrid Tables Storage", "N/A",
             f"${hybrid_storage_cost:,.2f}", f"${hybrid_storage_cost * 12:,.2f}"),
            ("SPCS Block Storage", "N/A",
             f"${spcs_storage_cost:,.2f}", f"${spcs_storage_cost * 12:,.2f}"),
            ("Archive Storage & Retrieval", "N/A",
             f"${archive_cost:,.2f}", f"${archive_cost * 12:,.2f}"),
            ("Postgres Storage", "N/A",
             f"${postgres_storage_cost:,.2f}", f"${postgres_storage_cost * 12:,.2f}"),
            ("Data Transfer", "N/A",
             f"${data_transfer_cost:,.2f}", f"${data_transfer_cost * 12:,.2f}"),
            ("Outbound PrivateLink", "N/A",
             f"${privatelink_cost:,.2f}", f"${privatelink_cost * 12:,.2f}"),
            ("AI / Cortex", f"{total_ai_credits:,.1f}",
             f"${total_ai_cost:,.2f}", f"${total_ai_cost * 12:,.2f}"),
        ]

        pdf.set_font("Helvetica", "", 8)
        fill = False
        for row in cost_rows:
            if fill:
                pdf.set_fill_color(255, 243, 224)
            else:
                pdf.set_fill_color(255, 255, 255)
            pdf.set_text_color(60, 60, 80)
            for i, cell in enumerate(row):
                align = "L" if i == 0 else "R"
                pdf.cell(col_w[i], 6, cell, border=1, fill=True, align=align)
            pdf.ln()
            fill = not fill

        # Grand total row
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(208, 74, 2)
        pdf.set_text_color(255, 255, 255)
        totals = [
            "GRAND TOTAL",
            f"{grand_total_credits:,.1f}",
            f"${grand_total_cost:,.2f}",
            f"${grand_total_cost * 12:,.2f}"
        ]
        for i, cell in enumerate(totals):
            align = "L" if i == 0 else "R"
            pdf.cell(col_w[i], 8, cell, border=1, fill=True, align=align)
        pdf.ln()

        # ── Warehouse Details ──
        if wh_results:
            pdf.ln(6)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(208, 74, 2)
            pdf.cell(0, 7, "Warehouse Details",
                     new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

            wh_hdr = ["Name", "Type", "Size", "Cl", "Cr/Hr", "Mo Cr", "Cost ($)"]
            wh_cw = [30, 26, 18, 12, 22, 32, 40]
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_fill_color(208, 74, 2)
            pdf.set_text_color(255, 255, 255)
            for i, h in enumerate(wh_hdr):
                pdf.cell(wh_cw[i], 6, h, border=1, fill=True, align="C")
            pdf.ln()

            pdf.set_font("Helvetica", "", 7)
            for wh in wh_results:
                pdf.set_text_color(60, 60, 80)
                pdf.set_fill_color(255, 255, 255)
                vals = [
                    str(wh["Warehouse"])[:14],
                    str(wh["Type"])[:12],
                    str(wh["Size"]),
                    str(wh["Clusters"]),
                    f"{wh['Credits/Hour']:.1f}",
                    f"{wh['Monthly Credits']:,.1f}",
                    f"${wh['Monthly Cost ($)']:,.2f}",
                ]
                for i, cell in enumerate(vals):
                    pdf.cell(wh_cw[i], 5, cell, border=1, align="C")
                pdf.ln()

        # ── SPCS Details ──
        if spcs_node_results:
            pdf.ln(6)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(208, 74, 2)
            pdf.cell(0, 7, "SPCS Compute Details",
                     new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

            sp_hdr = ["Node", "Family", "Instance", "Count", "Cr/Hr", "Mo Cr", "Cost ($)"]
            sp_cw = [22, 22, 30, 16, 22, 30, 38]
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_fill_color(208, 74, 2)
            pdf.set_text_color(255, 255, 255)
            for i, h in enumerate(sp_hdr):
                pdf.cell(sp_cw[i], 6, h, border=1, fill=True, align="C")
            pdf.ln()

            pdf.set_font("Helvetica", "", 7)
            for sn in spcs_node_results:
                pdf.set_text_color(60, 60, 80)
                pdf.set_fill_color(255, 255, 255)
                vals = [
                    sn["Node"][:10],
                    sn["Family"],
                    sn["Instance"][:14],
                    str(sn["Count"]),
                    f"{sn['Credits/Hr']:.2f}",
                    f"{sn['Monthly Credits']:,.2f}",
                    f"${sn['Monthly Cost ($)']:,.2f}",
                ]
                for i, cell in enumerate(vals):
                    pdf.cell(sp_cw[i], 5, cell, border=1, align="C")
                pdf.ln()

        # ── AI Details ──
        if ai_model_configs:
            pdf.ln(6)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(208, 74, 2)
            pdf.cell(0, 7, "AI / Cortex Model Details",
                     new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

            ai_hdr = ["Model", "In (M)", "Out (M)", "Credits", "Cost ($)"]
            ai_cw = [55, 28, 28, 30, 39]
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_fill_color(208, 74, 2)
            pdf.set_text_color(255, 255, 255)
            for i, h in enumerate(ai_hdr):
                pdf.cell(ai_cw[i], 6, h, border=1, fill=True, align="C")
            pdf.ln()

            pdf.set_font("Helvetica", "", 7)
            for ai in ai_model_configs:
                pdf.set_text_color(60, 60, 80)
                pdf.set_fill_color(255, 255, 255)
                vals = [
                    ai["Model"][:25],
                    f"{ai['Input Tokens (M)']:.1f}",
                    f"{ai['Output Tokens (M)']:.1f}",
                    f"{ai['Total Credits']:.2f}",
                    f"${ai['Monthly Cost ($)']:,.2f}",
                ]
                for i, cell in enumerate(vals):
                    pdf.cell(ai_cw[i], 5, cell, border=1, align="C")
                pdf.ln()

        # ── Disclaimer ──
        pdf.ln(8)
        pdf.set_draw_color(208, 74, 2)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)
        pdf.set_font("Helvetica", "I", 7)
        pdf.set_text_color(130, 130, 130)
        pdf.multi_cell(0, 4,
            "DISCLAIMER: This estimation is for planning purposes only. "
            "Actual costs may vary based on usage patterns, auto-suspend settings, "
            "query complexity, concurrency scaling, and negotiated pricing. "
            "Refer to your Order Form for contractual rates. "
            "Data sourced from the Snowflake Service Consumption Table "
            "(Effective March 2, 2026).\n\n"
            f"(c) {datetime.now().year} PricewaterhouseCoopers LLP. "
            "All rights reserved.")

        pdf_buffer = io.BytesIO()
        pdf_output = pdf.output()
        pdf_buffer.write(pdf_output)
        pdf_data = pdf_buffer.getvalue()

        st.download_button(
            label="📑  Download PDF Summary (.pdf)",
            data=pdf_data,
            file_name=f"Snowflake_Estimation_{cloud_provider}_{edition}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    except ImportError:
        st.warning(
            "⚠️ PDF export requires `fpdf2`. Install with: `pip install fpdf2`")

# ──────────────────────────────────────────────────────────────────────────────
# JSON DOWNLOAD
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)

json_col1, json_col2, json_col3 = st.columns([1, 2, 1])
with json_col2:
    report_json = {
        "report_metadata": {
            "generated": report_timestamp,
            "tool": "Snowflake Credit Consumption Estimator",
            "source": "Snowflake Service Consumption Table (Effective March 2, 2026)",
            "prepared_by": "PwC",
        },
        "configuration": {
            "cloud_provider": cloud_provider,
            "region": region,
            "edition": edition,
            "credit_price_usd": credit_price,
            "hours_per_day": hours_per_day,
            "days_per_month": days_per_month,
            "total_monthly_hours": total_hours,
        },
        "cost_breakdown": {
            "virtual_warehouses": {
                "total_credits": round(total_wh_credits, 2),
                "monthly_cost_usd": round(total_wh_cost, 2),
                "details": wh_results,
            },
            "cloud_services": {
                "total_credits": round(total_cs_credits, 2),
                "monthly_cost_usd": round(total_cs_cost, 2),
                "ten_pct_adjustment": apply_cs_adjustment,
            },
            "serverless_features": {
                "total_credits": round(total_sf_credits, 2),
                "monthly_cost_usd": round(total_sf_cost, 2),
                "details": sf_details,
            },
            "spcs_compute": {
                "total_credits": round(total_spcs_credits, 2),
                "monthly_cost_usd": round(total_spcs_cost, 2),
                "details": spcs_node_results,
            },
            "openflow_compute": {
                "total_credits": round(total_openflow_credits, 2),
                "monthly_cost_usd": round(total_openflow_cost, 2),
            },
            "postgres_compute": {
                "total_credits": round(total_postgres_credits, 4),
                "monthly_cost_usd": round(total_postgres_cost, 2),
                "details": postgres_results,
            },
            "storage": {
                "standard": {"volume_tb": storage_tb, "monthly_cost_usd": round(storage_cost, 2)},
                "hybrid_tables": {"volume_gb": hybrid_gb, "monthly_cost_usd": round(hybrid_storage_cost, 2)},
                "spcs_block": {"monthly_cost_usd": round(spcs_storage_cost, 2)},
                "archive": {"monthly_cost_usd": round(archive_cost, 2)},
                "postgres": {"monthly_cost_usd": round(postgres_storage_cost, 2)},
            },
            "data_transfer": {
                "type": transfer_type,
                "volume_tb": transfer_tb,
                "monthly_cost_usd": round(data_transfer_cost, 2),
            },
            "privatelink": {
                "monthly_cost_usd": round(privatelink_cost, 2),
            },
            "ai_cortex": {
                "total_credits": round(total_ai_credits, 2),
                "monthly_cost_usd": round(total_ai_cost, 2),
                "models": ai_model_configs,
            },
        },
        "grand_totals": {
            "total_monthly_credits": round(grand_total_credits, 2),
            "total_monthly_cost_usd": round(grand_total_cost, 2),
            "total_annual_cost_usd": round(grand_total_cost * 12, 2),
        },
    }

    json_data = json.dumps(report_json, indent=2, default=str)

    st.download_button(
        label="🔧  Download JSON Report (.json)",
        data=json_data,
        file_name=f"Snowflake_Estimation_{cloud_provider}_{edition}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
        mime="application/json",
        use_container_width=True,
    )

# ── Download format summary ──
st.markdown("""
<div style="text-align:center; margin-top:20px; padding:15px;
            background:rgba(208,74,2,0.05); border-radius:12px;
            border:1px dashed #D04A02;">
    <p style="color:#D04A02; font-size:0.9rem; font-weight:600;
              margin-bottom:5px;">
        📋 Download Formats Available
    </p>
    <p style="color:#a0a0a0; font-size:0.8rem; margin:0;">
        <b>Excel (.xlsx)</b> — 13-sheet workbook with all categories &amp; 12-month projection<br>
        <b>CSV (.csv)</b> — Single consolidated file for data analysis or database import<br>
        <b>PDF (.pdf)</b> — PwC-branded executive summary for stakeholder presentations<br>
        <b>JSON (.json)</b> — Machine-readable format for API integration or automation
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)
# ──────────────────────────────────────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)
st.markdown("""
<div class="pwc-footer">
    <div class="pwc-logo-text">PwC</div>
    <p style="margin-top: 8px;">
        <strong>Snowflake Credit Consumption Estimator</strong><br>
        Data sourced from the Snowflake Service Consumption Table
        — Effective March 2, 2026
    </p>
    <p style="font-size: 0.75rem; color: #555; margin-top: 12px;">
        ⚠️ This estimator is for planning purposes only. Actual costs may vary
        based on usage patterns, auto-suspend settings, query complexity, and
        negotiated pricing. Always refer to your Order Form for contractual pricing.
    </p>
    <p style="font-size: 0.7rem; color: #464646; margin-top: 15px;">
        © 2026 PricewaterhouseCoopers LLP. All rights reserved.
        PwC refers to the PwC network member firms and/or their specified subsidiaries.
    </p>
</div>
""", unsafe_allow_html=True)