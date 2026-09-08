"""
Snowflake Multi-Account Monitor — Premium Executive Dashboard
PwC Data & AI · Safe HTML rendering · Logo-ready
"""

import os
import math
import datetime
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from config import (
    AccountConfig,
    get_account_configs,
    save_account_config,
    remove_account_config,
)
from snowflake_connector import SnowflakeConnectionManager
from theme import (
    inject_css,
    COLORS,
    CHART_COLORS,
    get_env_color,
    pwc_header,
    section_header,
)

# ─── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Snowflake Monitor · PwC",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

# ─── Pure helpers (no HTML) ───────────────────────────────────────────────────

def safe_int(val, default=0):
    try:
        if val is None:
            return default
        if isinstance(val, float) and (
                math.isnan(val) or math.isinf(val)):
            return default
        return int(val)
    except Exception:
        return default


def safe_float(val, default=0.0):
    try:
        if val is None:
            return default
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except Exception:
        return default


def fmt_num(n):
    n = safe_int(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def fmt_credits(v):
    v = safe_float(v)
    if v >= 1_000:
        return f"{v / 1_000:.1f}K"
    return f"{v:.1f}"


def load_logo():
    for p in [
        "assets/logo.png",
        "assets/pwc_logo.png",
        "assets/company_logo.png",
        "logo.png",
    ]:
        if os.path.exists(p):
            return p
    return None


# ─── HTML block builders
# ─── Each function returns ONE self-contained HTML string.
# ─── Never nest these inside another f-string.

def _card(body_html: str, border_color: str = None,
          extra_style: str = "") -> str:
    bdr = f"border-left:4px solid {border_color};" \
        if border_color else ""
    return (
        f'<div style="'
        f'background:linear-gradient(180deg,rgba(255,255,255,0.02),rgba(255,255,255,0.00)),rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-radius:18px;padding:18px;'
        f'box-shadow:0 16px 30px rgba(0,0,0,0.18);'
        f'{bdr}{extra_style}">'
        f'{body_html}'
        f'</div>'
    )


def _kpi(icon, value, label, color, sub=""):
    sub_part = (
        f'<div style="margin-top:6px;font-size:0.72rem;'
        f'color:{COLORS["text_secondary"]};">{sub}</div>'
        if sub else ""
    )
    return (
        f'<div style="'
        f'position:relative;overflow:hidden;'
        f'border-radius:18px;padding:18px 18px 16px;'
        f'background:linear-gradient(180deg,rgba(255,255,255,0.03),rgba(255,255,255,0.00)),{COLORS["bg_card"]};'
        f'border:1px solid rgba(255,255,255,0.06);'
        f'box-shadow:0 14px 28px rgba(0,0,0,0.16);'
        f'height:100%;">'
        f'<div style="position:absolute;inset:0 0 auto 0;height:3px;background:{color};"></div>'
        f'<div style="font-size:1.15rem;margin-bottom:10px;">{icon}</div>'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:1.62rem;font-weight:700;color:{color};line-height:1;">{value}</div>'
        f'<div style="margin-top:7px;font-size:0.66rem;text-transform:uppercase;letter-spacing:0.12em;color:{COLORS["text_muted"]};">{label}</div>'
        f'{sub_part}'
        f'</div>'
    )


def _chip(label, color, icon="●"):
    return (
        f'<div style="padding:8px 14px;border-radius:999px;'
        f'font-size:0.72rem;font-weight:700;'
        f'color:{color};background:{color}15;'
        f'border:1px solid {color}33;text-align:center;">'
        f'{icon}&nbsp;&nbsp;{label}'
        f'</div>'
    )


def _alert(text, color, icon):
    return (
        f'<div style="'
        f'background:linear-gradient(180deg,rgba(255,255,255,0.02),rgba(255,255,255,0.00)),rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-left:4px solid {color};'
        f'border-radius:14px;padding:14px 18px;'
        f'margin-bottom:8px;'
        f'box-shadow:0 8px 20px rgba(0,0,0,0.14);'
        f'display:flex;align-items:center;gap:12px;">'
        f'<span style="font-size:1.1rem;">{icon}</span>'
        f'<span style="font-size:0.84rem;font-weight:600;'
        f'color:{COLORS["text_primary"]};">{text}</span>'
        f'</div>'
    )


def _env_row(name, account, is_conn):
    color = get_env_color(name)
    dot_color = COLORS["green"] if is_conn else COLORS["red"]
    status_text = "Connected" if is_conn else "Disconnected"
    return (
        f'<div style="display:flex;align-items:center;gap:8px;'
        f'padding:8px 10px;border-radius:10px;margin-bottom:4px;'
        f'background:rgba(255,255,255,0.02);'
        f'border:1px solid rgba(255,255,255,0.03);">'
        f'<div style="width:8px;height:8px;border-radius:50%;'
        f'background:{dot_color};box-shadow:0 0 8px {dot_color};'
        f'flex-shrink:0;"></div>'
        f'<div style="min-width:0;flex:1;">'
        f'<div style="font-size:0.8rem;font-weight:700;color:{color};'
        f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'
        f'{name}</div>'
        f'<div style="font-size:0.64rem;color:{COLORS["text_muted"]};'
        f'font-family:JetBrains Mono,monospace;'
        f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'
        f'{account}</div>'
        f'</div>'
        f'<span style="font-size:0.6rem;font-weight:700;'
        f'color:{dot_color};background:{dot_color}15;'
        f'border:1px solid {dot_color}33;'
        f'padding:2px 8px;border-radius:999px;">'
        f'{status_text}</span>'
        f'</div>'
    )


def _section_divider():
    return '<div style="height:1px;background:linear-gradient(90deg,rgba(255,255,255,0.10),transparent);margin:0.5rem 0 1rem 0;"></div>'


def _nav_card(icon, title, desc, color):
    return (
        f'<div style="'
        f'background:linear-gradient(180deg,rgba(255,255,255,0.02),rgba(255,255,255,0.00)),rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-left:4px solid {color};'
        f'border-radius:18px;padding:20px;min-height:160px;'
        f'box-shadow:0 16px 30px rgba(0,0,0,0.18);">'
        f'<div style="font-size:1.8rem;margin-bottom:10px;">{icon}</div>'
        f'<div style="font-size:0.9rem;font-weight:800;'
        f'color:{COLORS["text_primary"]};margin-bottom:6px;">{title}</div>'
        f'<div style="font-size:0.72rem;color:{COLORS["text_muted"]};'
        f'line-height:1.5;">{desc}</div>'
        f'</div>'
    )


def _env_comparison_card(name, e, local_fail_rate):
    color = get_env_color(name)
    fr_color = COLORS["red"] if local_fail_rate > 5 else COLORS["green"]
    return (
        f'<div style="'
        f'background:linear-gradient(180deg,rgba(255,255,255,0.02),rgba(255,255,255,0.00)),rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-left:4px solid {color};'
        f'border-radius:18px;padding:18px;'
        f'margin-bottom:12px;'
        f'box-shadow:0 16px 30px rgba(0,0,0,0.18);">'
        # header row
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;margin-bottom:14px;">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<span style="font-size:0.9rem;font-weight:800;color:{color};">{name}</span>'
        f'<span style="font-size:0.68rem;color:{COLORS["text_muted"]};">'
        f'{e["databases"]} DBs · {e["warehouses"]} WHs · {e["users"]} Users'
        f'</span>'
        f'</div>'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:0.72rem;'
        f'font-weight:700;color:{COLORS["pwc_gold"]};">'
        f'{fmt_credits(e["credits_30d"])} credits / 30d'
        f'</span>'
        f'</div>'
        # stats grid
        f'<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:10px;">'
        # databases
        f'<div>'
        f'<div style="font-size:0.62rem;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.08em;margin-bottom:3px;">Databases</div>'
        f'<div style="font-family:JetBrains Mono,monospace;font-weight:700;color:{color};">{e["databases"]}</div>'
        f'</div>'
        # warehouses
        f'<div>'
        f'<div style="font-size:0.62rem;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.08em;margin-bottom:3px;">Warehouses</div>'
        f'<div style="font-family:JetBrains Mono,monospace;font-weight:700;color:{COLORS["pwc_gold"]};">{e["warehouses"]}</div>'
        f'</div>'
        # users
        f'<div>'
        f'<div style="font-size:0.62rem;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.08em;margin-bottom:3px;">Users</div>'
        f'<div style="font-family:JetBrains Mono,monospace;font-weight:700;color:{COLORS["purple"]};">{e["users"]}</div>'
        f'</div>'
        # storage
        f'<div>'
        f'<div style="font-size:0.62rem;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.08em;margin-bottom:3px;">Storage</div>'
        f'<div style="font-family:JetBrains Mono,monospace;font-weight:700;color:{COLORS["cyan"]};">{e["total_storage_gb"]:.1f} GB</div>'
        f'</div>'
        # queries
        f'<div>'
        f'<div style="font-size:0.62rem;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.08em;margin-bottom:3px;">Queries</div>'
        f'<div style="font-family:JetBrains Mono,monospace;font-weight:700;color:{COLORS["green"]};">{fmt_num(e["queries_7d"])}</div>'
        f'</div>'
        # fail rate
        f'<div>'
        f'<div style="font-size:0.62rem;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.08em;margin-bottom:3px;">Fail Rate</div>'
        f'<div style="font-family:JetBrains Mono,monospace;font-weight:700;color:{fr_color};">{local_fail_rate:.1f}%</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )


def _env_grid_card(cfg, is_conn):
    color = get_env_color(cfg.name)
    dot_color = COLORS["green"] if is_conn else COLORS["red"]
    status_text = "Connected" if is_conn else "Disconnected"
    return (
        f'<div style="'
        f'background:linear-gradient(180deg,rgba(255,255,255,0.02),rgba(255,255,255,0.00)),rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-left:4px solid {color};'
        f'border-radius:18px;padding:18px;min-height:170px;'
        f'box-shadow:0 16px 30px rgba(0,0,0,0.18);">'
        # title row
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">'
        f'<div>'
        f'<div style="font-size:0.96rem;font-weight:800;color:{COLORS["text_primary"]};">{cfg.name}</div>'
        f'<div style="font-size:0.64rem;color:{COLORS["text_muted"]};font-family:JetBrains Mono,monospace;">{cfg.account}</div>'
        f'</div>'
        # status badge
        f'<span style="font-size:0.6rem;font-weight:800;color:{dot_color};'
        f'background:{dot_color}15;border:1px solid {dot_color}33;'
        f'padding:4px 10px;border-radius:999px;">'
        f'{"● " if is_conn else "○ "}{status_text}'
        f'</span>'
        f'</div>'
        # pills row
        f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;">'
        f'<span style="font-size:0.66rem;font-weight:600;color:{COLORS["text_secondary"]};'
        f'background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);'
        f'padding:4px 10px;border-radius:10px;">👤 {cfg.user}</span>'
        f'<span style="font-size:0.66rem;font-weight:600;color:{COLORS["text_secondary"]};'
        f'background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);'
        f'padding:4px 10px;border-radius:10px;">🎭 {cfg.role}</span>'
        f'</div>'
        f'</div>'
    )


# ─── Manager ──────────────────────────────────────────────────────────────────

manager = SnowflakeConnectionManager()
configs = get_account_configs()

# ─── Sidebar ──────────────────────────────────────────────────────────────────

logo_path = load_logo()

# Logo / branding
with st.sidebar:
    if logo_path:
        st.image('Scripts/snowflake-monitor/pwc_logo.jpg', use_container_width=True)
        st.markdown(
            f'<div style="height:1px;background:{COLORS["border"]};margin:8px 0 12px 0;"></div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(f"""
        <div style="padding:20px 16px 12px;border-bottom:1px solid {COLORS['border']};margin-bottom:12px;">
            <div style="font-size:1rem;font-weight:800;color:{COLORS['text_primary']};">❄️ Snowflake Monitor</div>
            <div style="font-size:0.56rem;color:{COLORS['pwc_orange']};font-weight:800;text-transform:uppercase;letter-spacing:0.18em;">PwC Data &amp; AI</div>
            <div style="margin-top:8px;font-size:0.68rem;color:{COLORS['text_muted']};">Add logo → <code>assets/logo.png</code></div>
        </div>
        """, unsafe_allow_html=True)

    # Connection health bar
    connected_accounts = manager.get_connected_accounts()
    total_accounts = len(configs)
    connected_count = len(connected_accounts)
    conn_pct = int(connected_count / total_accounts * 100) \
        if total_accounts else 0
    health_color = (
        COLORS["green"] if conn_pct == 100
        else COLORS["yellow"] if conn_pct > 0
        else COLORS["red"]
    )
    health_label = (
        "Healthy" if conn_pct == 100
        else "Partial" if conn_pct > 0
        else "Offline"
    )

    st.markdown(f"""
    <div style="background:rgba(19,26,36,0.9);border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:14px;margin-bottom:14px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <span style="font-size:0.66rem;color:{COLORS['text_muted']};text-transform:uppercase;letter-spacing:0.12em;">Environment Health</span>
            <span style="font-size:0.66rem;font-weight:800;color:{health_color};">{health_label}</span>
        </div>
        <div style="display:flex;align-items:baseline;gap:6px;">
            <span style="font-family:JetBrains Mono,monospace;font-size:1.9rem;font-weight:800;color:{health_color};">{connected_count}</span>
            <span style="color:{COLORS['text_muted']};font-size:0.9rem;">/ {total_accounts}</span>
        </div>
        <div style="margin-top:10px;height:6px;background:{COLORS['border']};border-radius:999px;overflow:hidden;">
            <div style="width:{conn_pct}%;height:100%;background:linear-gradient(90deg,{COLORS['pwc_orange']},{COLORS['pwc_gold']});border-radius:999px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        f'<div style="font-size:0.62rem;color:{COLORS["text_muted"]};text-transform:uppercase;letter-spacing:0.14em;margin-bottom:6px;">Configured Accounts</div>',
        unsafe_allow_html=True
    )

    for cfg in configs:
        is_conn = manager.is_connected(cfg.name)
        st.markdown(
            _env_row(cfg.name, cfg.account, is_conn),
            unsafe_allow_html=True
        )

    st.markdown("---")

    with st.expander("➕ Add Environment", expanded=False):
        with st.form("add_account_form"):
            acc_name = st.text_input("Name", placeholder="Production")
            acc_id   = st.text_input("Account ID", placeholder="xy12345.us-east-1")
            acc_user = st.text_input("User")
            acc_pass = st.text_input("Password", type="password")
            acc_role = st.text_input("Role", value="ACCOUNTADMIN")
            acc_wh   = st.text_input("Warehouse", value="COMPUTE_WH")
            submitted = st.form_submit_button("Add Environment", type="primary")
            if submitted:
                if acc_name and acc_id and acc_user:
                    save_account_config(AccountConfig(
                        name=acc_name, account=acc_id,
                        user=acc_user, password=acc_pass,
                        role=acc_role, warehouse=acc_wh,
                    ))
                    st.rerun()
                else:
                    st.error("Name, Account ID and User are required.")

    sb1, sb2 = st.columns(2)
    with sb1:
        if st.button("🔌 Connect All", use_container_width=True, key="sb_conn"):
            for cfg in configs:
                if not manager.is_connected(cfg.name) and cfg.get_password():
                    manager.connect(cfg)
            st.rerun()
    with sb2:
        if st.button("⛔ Disconnect", use_container_width=True, key="sb_disc"):
            manager.disconnect_all()
            st.rerun()

# ─── Header ───────────────────────────────────────────────────────────────────

pwc_header(
    "Snowflake Executive Command Center",
    subtitle="Unified enterprise monitoring across environments, compute, storage, users, tasks and operational health"
)

# Status chips — each rendered independently, never nested
chip_cols = st.columns(4)
chips = [
    ("● Systems Health",        COLORS["green"]),
    ("◈ Multi-Account",         COLORS["blue"]),
    ("★ Snowflake Dashboard",   COLORS["pwc_gold"]),
    ("✦ Operational Intel",     COLORS["pwc_orange"]),
]
for col, (label, color) in zip(chip_cols, chips):
    with col:
        st.markdown(_chip(label, color), unsafe_allow_html=True)

st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

# ─── No configs guard ─────────────────────────────────────────────────────────

if not configs:
    st.markdown(
        _alert(
            "No environments configured. Use the sidebar to add your first Snowflake account.",
            COLORS["pwc_orange"], "🚀"
        ),
        unsafe_allow_html=True
    )
    st.stop()

# ─── Environment Command Grid ─────────────────────────────────────────────────

section_header("ENVIRONMENT COMMAND GRID")

grid_cols = st.columns(max(1, min(len(configs), 4)))
for i, cfg in enumerate(configs):
    is_conn = manager.is_connected(cfg.name)
    with grid_cols[i % len(grid_cols)]:
        # Card HTML — no nested helpers
        st.markdown(
            _env_grid_card(cfg, is_conn),
            unsafe_allow_html=True
        )

        if not is_conn:
            pwd = cfg.get_password()
            if not pwd:
                pwd = st.text_input(
                    f"Password for {cfg.name}",
                    type="password",
                    key=f"pwd_{cfg.name}",
                    label_visibility="collapsed",
                    placeholder=f"Password for {cfg.name}"
                )
                if pwd:
                    cfg.password = pwd
                    save_account_config(cfg)

            if st.button(
                f"Connect {cfg.name}",
                key=f"conn_{cfg.name}",
                type="primary",
                use_container_width=True
            ):
                with st.spinner(f"Connecting to {cfg.name}..."):
                    manager.connect(cfg)
                st.rerun()
        else:
            bc1, bc2 = st.columns(2)
            with bc1:
                if st.button("Disconnect", key=f"disc_{cfg.name}", use_container_width=True):
                    manager.disconnect(cfg.name)
                    st.rerun()
            with bc2:
                if st.button("Remove", key=f"rm_{cfg.name}", use_container_width=True):
                    manager.disconnect(cfg.name)
                    remove_account_config(cfg.name)
                    st.rerun()

# ─── No connected guard ───────────────────────────────────────────────────────

connected_accounts = manager.get_connected_accounts()
if not connected_accounts:
    st.markdown(
        _alert(
            "No accounts are connected. Connect at least one environment above to load executive analytics.",
            COLORS["yellow"], "🔌"
        ),
        unsafe_allow_html=True
    )
    st.stop()

# ─── Data Collection ──────────────────────────────────────────────────────────

@st.cache_data(ttl=120, show_spinner=False)
def collect_environment_data(_mid, connected_list):
    mgr = SnowflakeConnectionManager()
    data = {}

    for acc in connected_list:
        env = {"name": acc}

        df = mgr.execute_query(acc, "SHOW DATABASES")
        env["databases"] = len(df) if df is not None else 0

        df = mgr.execute_query(acc, "SHOW WAREHOUSES")
        env["warehouses"] = len(df) if df is not None else 0
        if df is not None and "state" in df.columns:
            st_s = df["state"].astype(str).str.upper()
            env["wh_running"]   = safe_int((st_s == "STARTED").sum())
            env["wh_suspended"] = safe_int((st_s == "SUSPENDED").sum())
        else:
            env["wh_running"]   = 0
            env["wh_suspended"] = 0

        df = mgr.execute_query(acc, "SHOW USERS")
        env["users"] = len(df) if df is not None else 0

        df = mgr.execute_query(acc, "SHOW ROLES")
        env["roles"] = len(df) if df is not None else 0

        try:
            df = mgr.execute_query(acc, """
                SELECT
                    STORAGE_BYTES/(1024*1024*1024) AS STORAGE_GB,
                    STAGE_BYTES/(1024*1024*1024)   AS STAGE_GB,
                    FAILSAFE_BYTES/(1024*1024*1024) AS FAILSAFE_GB
                FROM SNOWFLAKE.ACCOUNT_USAGE.STORAGE_USAGE
                ORDER BY USAGE_DATE DESC LIMIT 1
            """)
            if df is not None and not df.empty:
                env["storage_gb"]  = safe_float(df.iloc[0].get("STORAGE_GB", 0))
                env["stage_gb"]    = safe_float(df.iloc[0].get("STAGE_GB", 0))
                env["failsafe_gb"] = safe_float(df.iloc[0].get("FAILSAFE_GB", 0))
            else:
                env["storage_gb"] = env["stage_gb"] = env["failsafe_gb"] = 0
        except Exception:
            env["storage_gb"] = env["stage_gb"] = env["failsafe_gb"] = 0

        env["total_storage_gb"] = round(
            env["storage_gb"] + env["stage_gb"] + env["failsafe_gb"], 2)

        try:
            df = mgr.execute_query(acc, """
                SELECT
                    SUM(CREDITS_USED)                AS TOTAL_CREDITS,
                    SUM(CREDITS_USED_COMPUTE)         AS COMPUTE_CREDITS,
                    SUM(CREDITS_USED_CLOUD_SERVICES)  AS CLOUD_CREDITS
                FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
                WHERE START_TIME >= DATEADD('day',-30,CURRENT_TIMESTAMP())
            """)
            if df is not None and not df.empty:
                env["credits_30d"]      = safe_float(df.iloc[0].get("TOTAL_CREDITS", 0))
                env["compute_credits"]  = safe_float(df.iloc[0].get("COMPUTE_CREDITS", 0))
                env["cloud_credits"]    = safe_float(df.iloc[0].get("CLOUD_CREDITS", 0))
            else:
                env["credits_30d"] = env["compute_credits"] = env["cloud_credits"] = 0
        except Exception:
            env["credits_30d"] = env["compute_credits"] = env["cloud_credits"] = 0

        try:
            df = mgr.execute_query(acc, """
                SELECT
                    COUNT(*)                                              AS QUERY_COUNT,
                    SUM(CASE WHEN EXECUTION_STATUS='FAIL' THEN 1 ELSE 0 END) AS FAILED,
                    AVG(TOTAL_ELAPSED_TIME)/1000                          AS AVG_SEC
                FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
                WHERE START_TIME >= DATEADD('day',-7,CURRENT_TIMESTAMP())
            """)
            if df is not None and not df.empty:
                env["queries_7d"]      = safe_int(df.iloc[0].get("QUERY_COUNT", 0))
                env["failed_queries"]  = safe_int(df.iloc[0].get("FAILED", 0))
                env["avg_query_sec"]   = safe_float(df.iloc[0].get("AVG_SEC", 0))
            else:
                env["queries_7d"] = env["failed_queries"] = 0
                env["avg_query_sec"] = 0
        except Exception:
            env["queries_7d"] = env["failed_queries"] = 0
            env["avg_query_sec"] = 0

        data[acc] = env
    return data


with st.spinner("Loading executive metrics..."):
    env_data = collect_environment_data(
        id(manager), tuple(connected_accounts))

# ─── Executive KPIs ───────────────────────────────────────────────────────────

section_header("EXECUTIVE SUMMARY")

total_dbs     = sum(v["databases"]       for v in env_data.values())
total_wh      = sum(v["warehouses"]      for v in env_data.values())
total_users   = sum(v["users"]           for v in env_data.values())
total_storage = sum(v["total_storage_gb"]for v in env_data.values())
total_credits = sum(v["credits_30d"]     for v in env_data.values())
total_queries = sum(v["queries_7d"]      for v in env_data.values())
total_failed  = sum(v["failed_queries"]  for v in env_data.values())
wh_running    = sum(v["wh_running"]      for v in env_data.values())
fail_rate     = (total_failed / total_queries * 100) if total_queries else 0.0

kpis_row1 = [
    ("🌍", str(len(connected_accounts)), "Environments",  COLORS["pwc_orange"], "Connected estate"),
    ("🗄️", str(total_dbs),              "Databases",     COLORS["blue"],        "Catalog footprint"),
    ("⚙️", str(total_wh),               "Warehouses",    COLORS["pwc_gold"],    f"{wh_running} active"),
    ("👥", str(total_users),             "Users",         COLORS["purple"],      "Identity surface"),
]
kpis_row2 = [
    ("💾", f"{total_storage:.1f} GB",    "Storage",       COLORS["cyan"],        "Active + stage + failsafe"),
    ("💰", fmt_credits(total_credits),   "Credits 30d",   COLORS["pwc_orange"],  "Consumption baseline"),
    ("📈", fmt_num(total_queries),       "Queries 7d",    COLORS["green"],       "Workload volume"),
    ("❌", f"{fail_rate:.1f}%",          "Failure Rate",
     COLORS["red"] if fail_rate > 5 else COLORS["green"],
     f"{fmt_num(total_failed)} failed"),
]

r1 = st.columns(4)
for col, (ico, val, lbl, clr, sub) in zip(r1, kpis_row1):
    with col:
        st.markdown(_kpi(ico, val, lbl, clr, sub), unsafe_allow_html=True)

st.markdown(_section_divider(), unsafe_allow_html=True)

r2 = st.columns(4)
for col, (ico, val, lbl, clr, sub) in zip(r2, kpis_row2):
    with col:
        st.markdown(_kpi(ico, val, lbl, clr, sub), unsafe_allow_html=True)

# ─── Attention Center ─────────────────────────────────────────────────────────

st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
section_header("ATTENTION CENTER")

alerts = []
if fail_rate > 5:
    alerts.append(("High query failure rate detected across connected environments",             COLORS["red"],      "❌"))
if connected_count < total_accounts:
    alerts.append(("One or more configured environments are currently disconnected",             COLORS["yellow"],   "⚠️"))
if total_credits > 1000:
    alerts.append(("Credit consumption is elevated over the last 30 days",                     COLORS["pwc_gold"], "💰"))
if wh_running == 0:
    alerts.append(("No running warehouses detected",                                            COLORS["red"],      "🛑"))
if not alerts:
    alerts.append(("All monitored executive indicators are currently healthy",                  COLORS["green"],    "✅"))

for text, color, icon in alerts:
    st.markdown(_alert(text, color, icon), unsafe_allow_html=True)

# ─── Environment Comparison ───────────────────────────────────────────────────

st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
section_header("ENVIRONMENT COMPARISON")

for acc, e in env_data.items():
    local_fail_rate = (
        (e["failed_queries"] / e["queries_7d"] * 100)
        if e["queries_7d"] else 0.0
    )
    st.markdown(
        _env_comparison_card(acc, e, local_fail_rate),
        unsafe_allow_html=True
    )

# ─── Analytics Tabs ───────────────────────────────────────────────────────────

st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
section_header("EXECUTIVE ANALYTICS")

comp_df   = pd.DataFrame(env_data.values())
color_map = {n: get_env_color(n) for n in comp_df["name"]}

tab1, tab2, tab3, tab4 = st.tabs([
    "📊  Footprint",
    "💾  Storage",
    "💰  Credits",
    "📈  Query Activity",
])

with tab1:
    c1, c2 = st.columns(2)

    with c1:
        melted = comp_df.melt(
            id_vars=["name"],
            value_vars=["databases", "warehouses", "users", "roles"],
            var_name="Object", value_name="Count"
        )
        melted["Object"] = melted["Object"].str.title()
        fig1 = px.bar(
            melted, x="Object", y="Count",
            color="name", barmode="group",
            color_discrete_map=color_map,
            height=380,
            title="Object Footprint by Environment"
        )
        fig1.update_layout(xaxis_title="", yaxis_title="Count", legend_title_text="")
        st.plotly_chart(fig1, use_container_width=True, key="fp_bar")

    with c2:
        fig2    = go.Figure()
        cats    = ["Databases","Warehouses","Users","Roles","Storage","Credits","Queries"]
        maxvals = {
            "databases":        max(safe_float(comp_df["databases"].max()), 1),
            "warehouses":       max(safe_float(comp_df["warehouses"].max()), 1),
            "users":            max(safe_float(comp_df["users"].max()), 1),
            "roles":            max(safe_float(comp_df["roles"].max()), 1),
            "total_storage_gb": max(safe_float(comp_df["total_storage_gb"].max()), 1),
            "credits_30d":      max(safe_float(comp_df["credits_30d"].max()), 1),
            "queries_7d":       max(safe_float(comp_df["queries_7d"].max()), 1),
        }
        for _, row in comp_df.iterrows():
            clr  = get_env_color(row["name"])
            r_   = int(clr[1:3], 16)
            g_   = int(clr[3:5], 16)
            b_   = int(clr[5:7], 16)
            vals = [
                row["databases"]        / maxvals["databases"]        * 100,
                row["warehouses"]       / maxvals["warehouses"]       * 100,
                row["users"]            / maxvals["users"]            * 100,
                row["roles"]            / maxvals["roles"]            * 100,
                row["total_storage_gb"] / maxvals["total_storage_gb"] * 100,
                row["credits_30d"]      / maxvals["credits_30d"]      * 100,
                row["queries_7d"]       / maxvals["queries_7d"]       * 100,
            ]
            vals.append(vals[0])
            fig2.add_trace(go.Scatterpolar(
                r=vals,
                theta=cats + [cats[0]],
                name=row["name"],
                line=dict(color=clr, width=2.5),
                fill="toself",
                fillcolor=f"rgba({r_},{g_},{b_},0.09)"
            ))
        fig2.update_layout(
            title="Relative Environment Radar",
            height=380,
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100]),
                bgcolor="rgba(0,0,0,0)"
            ),
            legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"),
        )
        st.plotly_chart(fig2, use_container_width=True, key="fp_radar")

with tab2:
    c1, c2 = st.columns(2)
    with c1:
        sm = comp_df.melt(
            id_vars=["name"],
            value_vars=["storage_gb","stage_gb","failsafe_gb"],
            var_name="Type", value_name="GB"
        )
        sm["Type"] = sm["Type"].map({
            "storage_gb":"Database","stage_gb":"Stage","failsafe_gb":"Failsafe"})
        fig3 = px.bar(
            sm, x="name", y="GB", color="Type", barmode="stack",
            height=380, title="Storage Composition",
            color_discrete_sequence=[COLORS["blue"],COLORS["pwc_orange"],COLORS["red"]]
        )
        fig3.update_layout(xaxis_title="", yaxis_title="GB", legend_title_text="")
        st.plotly_chart(fig3, use_container_width=True, key="stor_stack")
    with c2:
        pdf = pd.DataFrame([
            {"Environment": k, "Storage": v["total_storage_gb"]}
            for k, v in env_data.items()
        ])
        fig4 = px.pie(
            pdf, values="Storage", names="Environment",
            hole=0.58, height=380,
            title="Storage Share",
            color="Environment", color_discrete_map=color_map
        )
        fig4.update_traces(textinfo="label+percent")
        st.plotly_chart(fig4, use_container_width=True, key="stor_pie")

with tab3:
    c1, c2 = st.columns(2)
    with c1:
        cm = comp_df.melt(
            id_vars=["name"],
            value_vars=["compute_credits","cloud_credits"],
            var_name="Type", value_name="Credits"
        )
        cm["Type"] = cm["Type"].map({
            "compute_credits":"Compute","cloud_credits":"Cloud Services"})
        fig5 = px.bar(
            cm, x="name", y="Credits", color="Type", barmode="stack",
            height=380, title="Credit Composition (30d)",
            color_discrete_sequence=[COLORS["pwc_orange"],COLORS["blue"]]
        )
        fig5.update_layout(xaxis_title="", yaxis_title="Credits", legend_title_text="")
        st.plotly_chart(fig5, use_container_width=True, key="cred_stack")
    with c2:
        fig6 = px.bar(
            comp_df.sort_values("credits_30d", ascending=False),
            x="name", y="credits_30d",
            color="name", color_discrete_map=color_map,
            height=380, title="Total Credits by Environment"
        )
        fig6.update_layout(xaxis_title="", yaxis_title="Credits", showlegend=False)
        st.plotly_chart(fig6, use_container_width=True, key="cred_total")

with tab4:
    c1, c2 = st.columns(2)
    with c1:
        qrows = []
        for _, row in comp_df.iterrows():
            qrows.append({"Environment": row["name"], "Type": "Success",
                          "Count": max(row["queries_7d"] - row["failed_queries"], 0)})
            qrows.append({"Environment": row["name"], "Type": "Failed",
                          "Count": row["failed_queries"]})
        qdf = pd.DataFrame(qrows)
        fig7 = px.bar(
            qdf, x="Environment", y="Count",
            color="Type", barmode="stack",
            height=380, title="Query Success vs Failure (7d)",
            color_discrete_map={"Success": COLORS["green"],"Failed": COLORS["red"]}
        )
        fig7.update_layout(xaxis_title="", yaxis_title="Queries", legend_title_text="")
        st.plotly_chart(fig7, use_container_width=True, key="q_stack")
    with c2:
        ddf = pd.DataFrame([
            {"Environment": k, "Avg Duration (s)": v["avg_query_sec"]}
            for k, v in env_data.items()
        ])
        fig8 = px.bar(
            ddf, x="Environment", y="Avg Duration (s)",
            color="Environment", color_discrete_map=color_map,
            height=380, title="Average Query Duration"
        )
        fig8.update_layout(xaxis_title="", showlegend=False)
        st.plotly_chart(fig8, use_container_width=True, key="q_dur")

# ─── Navigation Grid ──────────────────────────────────────────────────────────

st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
section_header("EXPLORE PLATFORM MODULES")

NAV_ITEMS = [
    ("📊", "Databases & Schemas",  "Browse database and schema structures",        "pages/1__Databases__and__Schemas.py",  COLORS["blue"]),
    ("📋", "Tables & Views",       "Create, alter and govern table structures",     "pages/2__Tables__and__Views.py",        COLORS["green"]),
    ("⚙️", "Warehouses",           "Manage compute and resource monitors",          "pages/3_⚙️_Warehouses.py",            COLORS["pwc_gold"]),
    ("👥", "Users & Roles",        "Identity, access and privilege controls",       "pages/4_👥_Users_&_Roles.py",         COLORS["purple"]),
    ("📈", "Query History",        "Performance analytics and investigation",       "pages/5_📈_Query_History.py",         COLORS["cyan"]),
    ("💾", "Storage Usage",        "Storage footprint and trends",                  "pages/6_💾_Storage_Usage.py",         COLORS["blue"]),
    ("💰", "Credit Consumption",   "Credit cost and spend management",              "pages/7_💰_Credit_Consumption.py",    COLORS["pwc_orange"]),
    ("🤖", "AI Assistant",         "Natural language help and insights",            "pages/8_🤖_AI_Assistant.py",          COLORS["pwc_gold"]),
    ("🔄", "Replication",          "Replication, failover and failback",            "pages/9_🔄_Replication.py",           COLORS["red"]),
    ("📥", "Data Ingestion",       "COPY, load history and Snowpipe",               "pages/10_📥_Data_Ingestion.py",       COLORS["green"]),
    ("⏰", "Task Manager",         "Task orchestration and scheduling",             "pages/11_⏰_Task_Manager.py",         COLORS["purple"]),
]

rows = [NAV_ITEMS[i:i+4] for i in range(0, len(NAV_ITEMS), 4)]
for row in rows:
    cols = st.columns(4)
    for col, (icon, title, desc, path, clr) in zip(cols, row):
        with col:
            st.markdown(
                _nav_card(icon, title, desc, clr),
                unsafe_allow_html=True
            )
            if st.button(f"Open {title}", key=f"nav_{title}", use_container_width=True):
                st.switch_page(path)

# ─── Footer ───────────────────────────────────────────────────────────────────

st.markdown(f"""
<div style="text-align:center;padding:30px 0 10px;border-top:1px solid {COLORS['border']};margin-top:32px;">
    <div style="font-size:0.78rem;font-weight:800;color:{COLORS['text_primary']};">
        ❄️ Snowflake Executive Command Center
        &nbsp;·&nbsp;
        <span style="color:{COLORS['pwc_orange']};font-weight:800;text-transform:uppercase;letter-spacing:0.12em;font-size:0.68rem;">
            Powered By PwC Data &amp; AI
        </span>
    </div>
    <div style="margin-top:4px;font-size:0.66rem;color:{COLORS['text_dim']};">
        {len(connected_accounts)} environment(s) connected · Premium Dashboard UI
    </div>
</div>
""", unsafe_allow_html=True)