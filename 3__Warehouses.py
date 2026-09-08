"""
⚙️ Warehouses — View, create, manage warehouses
   and resource monitors across all environments.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import time
import math

from snowflake_connector import SnowflakeConnectionManager
from theme import (
    inject_css, COLORS, CHART_COLORS,
    get_env_color, pwc_header, section_header,
)

# ─── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Warehouses · PwC",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)
inject_css()

# ─── Safe HTML builders ───────────────────────────────────────────────────────
# Rule: every function returns ONE complete HTML string.
# Never call these inside another f-string or HTML block.

def _card(body: str, border_color: str = None,
          extra: str = "") -> str:
    bdr = f"border-left:4px solid {border_color};" \
        if border_color else ""
    return (
        f'<div style="background:linear-gradient('
        f'180deg,rgba(255,255,255,0.02),rgba(255,255,255,0.00)),'
        f'rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-radius:18px;padding:18px;'
        f'box-shadow:0 16px 30px rgba(0,0,0,0.18);'
        f'{bdr}{extra}">{body}</div>'
    )


def _kpi(icon, value, label, color, sub=""):
    sub_html = (
        f'<div style="margin-top:6px;font-size:0.72rem;'
        f'color:{COLORS["text_secondary"]};">{sub}</div>'
        if sub else ""
    )
    return (
        f'<div style="position:relative;overflow:hidden;'
        f'border-radius:18px;padding:18px 18px 16px;'
        f'background:linear-gradient(180deg,rgba(255,255,255,0.03),'
        f'rgba(255,255,255,0.00)),{COLORS["bg_card"]};'
        f'border:1px solid rgba(255,255,255,0.06);'
        f'box-shadow:0 14px 28px rgba(0,0,0,0.16);height:100%;">'
        f'<div style="position:absolute;inset:0 0 auto 0;'
        f'height:3px;background:{color};"></div>'
        f'<div style="font-size:1.1rem;margin-bottom:8px;">{icon}</div>'
        f'<div style="font-family:JetBrains Mono,monospace;'
        f'font-size:1.55rem;font-weight:700;color:{color};'
        f'line-height:1;">{value}</div>'
        f'<div style="margin-top:7px;font-size:0.66rem;'
        f'text-transform:uppercase;letter-spacing:0.12em;'
        f'color:{COLORS["text_muted"]};">{label}</div>'
        f'{sub_html}</div>'
    )


def _state_pill(state: str) -> str:
    s = str(state).upper()
    cfg = {
        "STARTED":   (COLORS["green"],  "▶ RUNNING"),
        "SUSPENDED": (COLORS["yellow"], "⏸ SUSPENDED"),
        "RESIZING":  (COLORS["blue"],   "↕ RESIZING"),
        "RESUMING":  (COLORS["cyan"],   "↺ RESUMING"),
    }
    color, label = cfg.get(s, (COLORS["text_muted"], s))
    return (
        f'<span style="display:inline-flex;align-items:center;'
        f'gap:5px;padding:4px 12px;border-radius:999px;'
        f'font-size:0.65rem;font-weight:700;'
        f'color:{color};background:{color}15;'
        f'border:1px solid {color}33;">{label}</span>'
    )


def _size_badge(size: str) -> str:
    s = str(size).upper()
    colors = {
        "X-SMALL":  COLORS["text_muted"],
        "SMALL":    COLORS["blue"],
        "MEDIUM":   COLORS["pwc_gold"],
        "LARGE":    COLORS["pwc_orange"],
        "X-LARGE":  COLORS["red"],
        "2X-LARGE": COLORS["red"],
        "3X-LARGE": COLORS["red"],
        "4X-LARGE": COLORS["red"],
    }
    c = colors.get(s, COLORS["text_muted"])
    return (
        f'<span style="display:inline-flex;align-items:center;'
        f'padding:2px 10px;border-radius:8px;'
        f'font-size:0.68rem;font-weight:700;'
        f'font-family:JetBrains Mono,monospace;'
        f'color:{c};background:{c}15;border:1px solid {c}33;">'
        f'{s}</span>'
    )


def _wh_card(name, state, size, wh_type, auto_s,
             auto_r, min_c, max_c, owner, rm,
             running, queued, comment, env_color) -> str:
    is_run     = str(state).upper() == "STARTED"
    auto_r_up  = str(auto_r).upper()
    ar_color   = COLORS["green"] if auto_r_up == "TRUE" else COLORS["red"]
    rm_color   = (COLORS["pwc_gold"]
                  if str(rm) not in ("—","nan","None","")
                  else COLORS["text_muted"])

    activity = ""
    if is_run:
        activity = (
            f'<div style="margin-top:8px;display:flex;gap:12px;">'
            f'<span style="font-size:0.68rem;color:{COLORS["blue"]};">▶ {running} running</span>'
            f'<span style="font-size:0.68rem;color:{COLORS["yellow"]};">⏳ {queued} queued</span>'
            f'</div>'
        )

    comment_row = ""
    if comment:
        comment_row = (
            f'<div style="font-size:0.65rem;'
            f'color:{COLORS["text_muted"]};'
            f'margin-top:6px;overflow:hidden;'
            f'text-overflow:ellipsis;white-space:nowrap;">'
            f'{comment}</div>'
        )

    return (
        f'<div style="background:linear-gradient('
        f'180deg,rgba(255,255,255,0.02),rgba(255,255,255,0.00)),'
        f'rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-left:4px solid {env_color};'
        f'border-radius:18px;padding:18px;'
        f'box-shadow:0 14px 28px rgba(0,0,0,0.16);'
        f'margin-bottom:10px;">'
        # top row
        f'<div style="display:flex;align-items:center;'
        f'justify-content:space-between;margin-bottom:10px;">'
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<span style="font-weight:700;font-size:0.92rem;'
        f'color:{COLORS["text_primary"]};">⚙️ {name}</span>'
        f'{_state_pill(state)}'
        f'</div>'
        f'{_size_badge(size)}'
        f'</div>'
        # info grid
        f'<div style="display:grid;'
        f'grid-template-columns:1fr 1fr;gap:6px;">'
        f'<div style="font-size:0.68rem;color:{COLORS["text_muted"]};">'
        f'🔧 Type: <b style="color:{COLORS["text_secondary"]};">{wh_type}</b></div>'
        f'<div style="font-size:0.68rem;color:{COLORS["text_muted"]};">'
        f'🔗 Clusters: <b style="color:{COLORS["text_secondary"]};">{min_c}–{max_c}</b></div>'
        f'<div style="font-size:0.68rem;color:{COLORS["text_muted"]};">'
        f'⏱ Auto-suspend: <b style="color:{COLORS["text_secondary"]};">{auto_s}s</b></div>'
        f'<div style="font-size:0.68rem;color:{COLORS["text_muted"]};">'
        f'▶ Auto-resume: <b style="color:{ar_color};">{auto_r_up}</b></div>'
        f'<div style="font-size:0.68rem;color:{COLORS["text_muted"]};">'
        f'👤 Owner: <b style="color:{COLORS["text_secondary"]};">{owner}</b></div>'
        f'<div style="font-size:0.68rem;color:{COLORS["text_muted"]};">'
        f'💰 Monitor: <b style="color:{rm_color};">{rm}</b></div>'
        f'</div>'
        f'{comment_row}'
        f'{activity}'
        f'</div>'
    )


def _rm_card(name, quota, used, remain,
             freq, sus_at, notif_at, pct,
             bar_color) -> str:
    return (
        f'<div style="background:linear-gradient('
        f'180deg,rgba(255,255,255,0.02),rgba(255,255,255,0.00)),'
        f'rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-radius:18px;padding:18px;'
        f'box-shadow:0 14px 28px rgba(0,0,0,0.16);'
        f'position:relative;overflow:hidden;">'
        # top accent
        f'<div style="position:absolute;inset:0 0 auto 0;'
        f'height:3px;background:{bar_color};"></div>'
        # title row
        f'<div style="display:flex;align-items:center;'
        f'justify-content:space-between;margin-bottom:10px;'
        f'margin-top:4px;">'
        f'<span style="font-weight:700;font-size:0.88rem;'
        f'color:{COLORS["text_primary"]};">💰 {name}</span>'
        f'<span style="font-size:0.65rem;'
        f'color:{COLORS["text_muted"]};'
        f'background:rgba(255,255,255,0.04);'
        f'border:1px solid rgba(255,255,255,0.08);'
        f'padding:2px 8px;border-radius:8px;">{freq}</span>'
        f'</div>'
        # pct + quota
        f'<div style="display:flex;align-items:baseline;'
        f'gap:6px;margin-bottom:4px;">'
        f'<span style="font-family:JetBrains Mono,monospace;'
        f'font-size:1.3rem;font-weight:700;'
        f'color:{bar_color};">{pct:.1f}%</span>'
        f'<span style="font-size:0.7rem;'
        f'color:{COLORS["text_muted"]};">of {quota:,.0f} credits</span>'
        f'</div>'
        # progress bar
        f'<div style="height:8px;background:{COLORS["border"]};'
        f'border-radius:6px;overflow:hidden;margin-bottom:10px;">'
        f'<div style="height:100%;width:{min(pct,100):.1f}%;'
        f'background:{bar_color};border-radius:6px;"></div>'
        f'</div>'
        # stats
        f'<div style="display:grid;'
        f'grid-template-columns:1fr 1fr;gap:4px;">'
        f'<div style="font-size:0.65rem;color:{COLORS["text_muted"]};">'
        f'Used: <b style="color:{bar_color};">{used:,.2f}</b></div>'
        f'<div style="font-size:0.65rem;color:{COLORS["text_muted"]};">'
        f'Remaining: <b style="color:{COLORS["green"]};">{remain:,.2f}</b></div>'
        f'<div style="font-size:0.65rem;color:{COLORS["text_muted"]};">'
        f'Suspend at: <b style="color:{COLORS["text_secondary"]};">{sus_at}%</b></div>'
        f'<div style="font-size:0.65rem;color:{COLORS["text_muted"]};">'
        f'Notify at: <b style="color:{COLORS["text_secondary"]};">{notif_at}%</b></div>'
        f'</div>'
        f'</div>'
    )


def _sql_block(sql: str) -> str:
    return (
        f'<div style="background:{COLORS["bg_secondary"]};'
        f'border:1px solid {COLORS["border"]};'
        f'border-left:3px solid {COLORS["pwc_orange"]};'
        f'border-radius:0 8px 8px 0;'
        f'padding:14px 16px;'
        f'font-family:JetBrains Mono,monospace;'
        f'font-size:0.75rem;'
        f'color:{COLORS["text_secondary"]};'
        f'line-height:1.7;white-space:pre-wrap;'
        f'word-break:break-all;margin:10px 0;">'
        f'{sql}'
        f'</div>'
    )


def _info_box(text: str, accent: str = None) -> str:
    accent = accent or COLORS["blue"]
    return (
        f'<div style="background:rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-left:4px solid {accent};'
        f'border-radius:14px;padding:14px 16px;">'
        f'<div style="font-size:0.82rem;'
        f'color:{COLORS["text_secondary"]};line-height:1.6;">'
        f'{text}</div></div>'
    )


def _step(num: int, title: str) -> str:
    return (
        f'<div style="display:flex;align-items:center;'
        f'gap:10px;margin-bottom:14px;margin-top:8px;">'
        f'<div style="width:26px;height:26px;border-radius:50%;'
        f'background:linear-gradient(135deg,'
        f'{COLORS["pwc_orange"]},{COLORS["pwc_orange_dark"]});'
        f'color:white;font-size:0.72rem;font-weight:700;'
        f'display:flex;align-items:center;justify-content:center;'
        f'flex-shrink:0;">{num}</div>'
        f'<div style="font-weight:700;color:{COLORS["text_primary"]};'
        f'font-size:0.9rem;">{title}</div>'
        f'</div>'
    )


def _alert(text: str, color: str, icon: str) -> str:
    return (
        f'<div style="background:rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-left:4px solid {color};'
        f'border-radius:14px;padding:12px 16px;'
        f'margin-bottom:8px;'
        f'display:flex;align-items:center;gap:10px;">'
        f'<span style="font-size:1rem;">{icon}</span>'
        f'<span style="font-size:0.82rem;font-weight:600;'
        f'color:{COLORS["text_primary"]};">{text}</span>'
        f'</div>'
    )


def _progress_bar(pct: float, color: str) -> str:
    return (
        f'<div style="height:6px;'
        f'background:{COLORS["border"]};'
        f'border-radius:999px;overflow:hidden;'
        f'margin-top:8px;">'
        f'<div style="width:{min(pct,100):.1f}%;height:100%;'
        f'background:linear-gradient(90deg,'
        f'{COLORS["pwc_orange"]},{COLORS["pwc_gold"]});'
        f'border-radius:999px;"></div>'
        f'</div>'
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

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


def fmt_credits(v):
    v = safe_float(v)
    return f"{v/1000:.1f}K" if v >= 1000 else f"{v:.2f}"


def fmt_dur(s):
    s = safe_float(s)
    if s < 60:   return f"{s:.1f}s"
    if s < 3600: return f"{s/60:.1f}m"
    return f"{s/3600:.1f}h"


def run_query(account, sql):
    return manager.execute_query(account, sql)


def run_statement(account, sql):
    conn = manager.get_connection(account)
    if not conn:
        return False, f"Not connected to {account}"
    try:
        cur  = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] \
               if cur.description else []
        cur.close()
        return True, (
            pd.DataFrame(rows, columns=cols)
            if cols else pd.DataFrame()
        )
    except Exception as e:
        return False, str(e)


@st.cache_data(ttl=30, show_spinner=False)
def fetch_warehouses(_mid, account):
    try:
        df = run_query(account, "SHOW WAREHOUSES")
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=30, show_spinner=False)
def fetch_resource_monitors(_mid, account):
    try:
        df = run_query(account, "SHOW RESOURCE MONITORS")
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def fetch_warehouses_list(_mid, account):
    df = fetch_warehouses(_mid, account)
    nc = next((c for c in ["name","NAME"]
                if c in df.columns), None)
    return df[nc].tolist() if nc and not df.empty else []


@st.cache_data(ttl=30, show_spinner=False)
def fetch_metering(_mid, account, days):
    try:
        df = run_query(account, f"""
            SELECT WAREHOUSE_NAME, START_TIME,
                   CREDITS_USED,
                   CREDITS_USED_COMPUTE,
                   CREDITS_USED_CLOUD_SERVICES
            FROM SNOWFLAKE.ACCOUNT_USAGE
                     .WAREHOUSE_METERING_HISTORY
            WHERE START_TIME >= DATEADD('day',{-days},
                  CURRENT_TIMESTAMP())
            ORDER BY START_TIME DESC
            LIMIT 5000
        """)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=30, show_spinner=False)
def fetch_load(_mid, account, days):
    try:
        df = run_query(account, f"""
            SELECT WAREHOUSE_NAME, START_TIME,
                   AVG_RUNNING, AVG_QUEUED_LOAD,
                   AVG_BLOCKED
            FROM SNOWFLAKE.ACCOUNT_USAGE
                     .WAREHOUSE_LOAD_HISTORY
            WHERE START_TIME >= DATEADD('day',{-days},
                  CURRENT_TIMESTAMP())
            ORDER BY START_TIME DESC
            LIMIT 5000
        """)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=30, show_spinner=False)
def fetch_query_history(_mid, account, wh, days):
    try:
        df = run_query(account, f"""
            SELECT QUERY_ID, QUERY_TEXT,
                   QUERY_TYPE, USER_NAME,
                   EXECUTION_STATUS, START_TIME,
                   TOTAL_ELAPSED_TIME/1000 AS DURATION_SEC,
                   BYTES_SCANNED, ROWS_PRODUCED
            FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
            WHERE WAREHOUSE_NAME = '{wh}'
              AND START_TIME >= DATEADD('day',{-days},
                  CURRENT_TIMESTAMP())
            ORDER BY START_TIME DESC
            LIMIT 1000
        """)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


# ─── Manager + Sidebar ────────────────────────────────────────────────────────

manager   = SnowflakeConnectionManager()
connected = manager.get_connected_accounts()

with st.sidebar:
    st.markdown(f"""
    <div style="padding:20px 16px 12px;
         border-bottom:1px solid {COLORS['border']};
         margin-bottom:12px;">
        <div style="font-size:1rem;font-weight:800;
             color:{COLORS['text_primary']};">⚙️ Warehouses</div>
        <div style="font-size:0.56rem;color:{COLORS['pwc_orange']};
             font-weight:800;text-transform:uppercase;
             letter-spacing:0.18em;">PwC Data &amp; AI</div>
    </div>
    """, unsafe_allow_html=True)

    for acc in connected:
        color = get_env_color(acc)
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;'
            f'padding:8px 10px;border-radius:10px;margin-bottom:4px;">'
            f'<div style="width:8px;height:8px;border-radius:50%;'
            f'background:{color};box-shadow:0 0 6px {color};'
            f'flex-shrink:0;"></div>'
            f'<span style="font-size:0.82rem;font-weight:600;'
            f'color:{color};">{acc}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    if not connected:
        st.warning("No accounts connected.")

    st.markdown("---")
    auto_refresh = st.checkbox("⚡ Auto-refresh (30s)",
                                value=False,
                                key="wh_auto_refresh")
    if st.button("🔄 Refresh", use_container_width=True,
                  key="wh_refresh"):
        st.cache_data.clear()
        st.rerun()

# ─── Header ───────────────────────────────────────────────────────────────────

pwc_header(
    "Warehouse Manager",
    subtitle="Create, manage, monitor warehouses "
             "and resource monitors across all environments"
)

if not connected:
    st.markdown(
        _alert("Connect at least one account to manage warehouses.",
               COLORS["pwc_orange"], "🔌"),
        unsafe_allow_html=True
    )
    st.stop()

if auto_refresh:
    st.markdown(
        _alert("Auto-refresh is ON — page reloads every 30 seconds.",
               COLORS["green"], "⚡"),
        unsafe_allow_html=True
    )
    time.sleep(30)
    st.rerun()

# ─── Tabs ─────────────────────────────────────────────────────────────────────

(tab_overview, tab_warehouses, tab_create,
 tab_manage, tab_performance,
 tab_resource_monitors, tab_create_rm) = st.tabs([
    "📊  Overview",
    "⚙️  Warehouses",
    "➕  Create",
    "🔧  Manage",
    "📈  Performance",
    "💰  Resource Monitors",
    "🆕  Create Monitor",
])

# ═══════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════

with tab_overview:
    section_header("WAREHOUSE OVERVIEW")

    ov_days = st.select_slider(
        "Metric window (days)",
        options=[1, 7, 14, 30], value=7,
        key="ov_days_wh"
    )

    # Aggregate across all accounts
    all_wh_dfs = []
    total_credits = 0.0
    total_compute = 0.0
    total_cloud   = 0.0

    for acc in connected:
        wdf = fetch_warehouses(id(manager), acc)
        if not wdf.empty:
            all_wh_dfs.append(wdf)
        mdf = fetch_metering(id(manager), acc, ov_days)
        if not mdf.empty:
            for col in ["CREDITS_USED",
                        "CREDITS_USED_COMPUTE",
                        "CREDITS_USED_CLOUD_SERVICES"]:
                if col in mdf.columns:
                    mdf[col] = pd.to_numeric(
                        mdf[col], errors="coerce"
                    ).fillna(0)
            total_credits += safe_float(
                mdf["CREDITS_USED"].sum()
                if "CREDITS_USED" in mdf.columns else 0)
            total_compute += safe_float(
                mdf["CREDITS_USED_COMPUTE"].sum()
                if "CREDITS_USED_COMPUTE"
                in mdf.columns else 0)
            total_cloud   += safe_float(
                mdf["CREDITS_USED_CLOUD_SERVICES"].sum()
                if "CREDITS_USED_CLOUD_SERVICES"
                in mdf.columns else 0)

    total_wh   = sum(len(d) for d in all_wh_dfs)
    running_wh = 0
    susp_wh    = 0
    if all_wh_dfs:
        all_wh = pd.concat(all_wh_dfs, ignore_index=True)
        sc     = next((c for c in ["state", "STATE"]
                        if c in all_wh.columns), None)
        if sc:
            running_wh = safe_int(
                (all_wh[sc].str.upper() == "STARTED").sum())
            susp_wh    = safe_int(
                (all_wh[sc].str.upper() == "SUSPENDED").sum())

    # KPI row
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    kpis = [
        ("⚙️", str(total_wh),             "Total Warehouses",   COLORS["pwc_orange"], ""),
        ("▶️", str(running_wh),            "Running",            COLORS["green"],      ""),
        ("⏸️", str(susp_wh),              "Suspended",          COLORS["yellow"],     ""),
        ("💰", fmt_credits(total_credits), f"Credits ({ov_days}d)",COLORS["pwc_gold"], ""),
        ("🖥️", fmt_credits(total_compute), "Compute Credits",    COLORS["blue"],       ""),
        ("☁️", fmt_credits(total_cloud),   "Cloud Credits",      COLORS["cyan"],       ""),
    ]
    for col, (ico, val, lbl, clr, sub) in zip(
            [k1,k2,k3,k4,k5,k6], kpis):
        with col:
            st.markdown(_kpi(ico, val, lbl, clr, sub),
                         unsafe_allow_html=True)

    st.markdown(
        '<div style="height:16px;"></div>',
        unsafe_allow_html=True
    )

    # Per-environment cards
    section_header("PER-ENVIRONMENT BREAKDOWN")

    for acc in connected:
        env_color = get_env_color(acc)
        wdf = fetch_warehouses(id(manager), acc)
        mdf = fetch_metering(id(manager), acc, ov_days)

        n_wh  = len(wdf)
        n_run = 0
        n_sus = 0
        if not wdf.empty:
            sc = next((c for c in ["state","STATE"]
                        if c in wdf.columns), None)
            if sc:
                n_run = safe_int(
                    (wdf[sc].str.upper() == "STARTED").sum())
                n_sus = safe_int(
                    (wdf[sc].str.upper() == "SUSPENDED").sum())

        env_creds = 0.0
        if not mdf.empty and "CREDITS_USED" in mdf.columns:
            mdf["CREDITS_USED"] = pd.to_numeric(
                mdf["CREDITS_USED"], errors="coerce"
            ).fillna(0)
            env_creds = safe_float(mdf["CREDITS_USED"].sum())

        pct_run = n_run / n_wh * 100 if n_wh > 0 else 0

        body = (
            f'<div style="display:flex;align-items:center;'
            f'justify-content:space-between;margin-bottom:12px;">'
            f'<span style="font-size:0.9rem;font-weight:800;'
            f'color:{env_color};">{acc}</span>'
            f'<span style="font-family:JetBrains Mono,monospace;'
            f'font-size:0.72rem;color:{COLORS["text_muted"]};">'
            f'{ov_days}d window</span>'
            f'</div>'
            f'<div style="display:grid;'
            f'grid-template-columns:repeat(5,1fr);'
            f'gap:10px;text-align:center;margin-bottom:10px;">'
            f'<div><div style="font-family:JetBrains Mono,monospace;'
            f'font-size:1.3rem;font-weight:700;color:{env_color};">'
            f'{n_wh}</div>'
            f'<div style="font-size:0.6rem;color:{COLORS["text_muted"]};'
            f'text-transform:uppercase;">Warehouses</div></div>'
            f'<div><div style="font-family:JetBrains Mono,monospace;'
            f'font-size:1.3rem;font-weight:700;color:{COLORS["green"]};">'
            f'{n_run}</div>'
            f'<div style="font-size:0.6rem;color:{COLORS["text_muted"]};'
            f'text-transform:uppercase;">Running</div></div>'
            f'<div><div style="font-family:JetBrains Mono,monospace;'
            f'font-size:1.3rem;font-weight:700;color:{COLORS["yellow"]};">'
            f'{n_sus}</div>'
            f'<div style="font-size:0.6rem;color:{COLORS["text_muted"]};'
            f'text-transform:uppercase;">Suspended</div></div>'
            f'<div><div style="font-family:JetBrains Mono,monospace;'
            f'font-size:1.3rem;font-weight:700;color:{COLORS["pwc_gold"]};">'
            f'{fmt_credits(env_creds)}</div>'
            f'<div style="font-size:0.6rem;color:{COLORS["text_muted"]};'
            f'text-transform:uppercase;">Credits</div></div>'
            f'<div><div style="font-family:JetBrains Mono,monospace;'
            f'font-size:1.3rem;font-weight:700;color:{COLORS["blue"]};">'
            f'{pct_run:.0f}%</div>'
            f'<div style="font-size:0.6rem;color:{COLORS["text_muted"]};'
            f'text-transform:uppercase;">Active %</div></div>'
            f'</div>'
            + _progress_bar(pct_run, env_color)
        )

        st.markdown(
            _card(body, border_color=env_color),
            unsafe_allow_html=True
        )

    # Credit trend chart
    meter_all = []
    for acc in connected:
        mdf2 = fetch_metering(id(manager), acc, ov_days)
        if not mdf2.empty:
            for col in ["CREDITS_USED"]:
                if col in mdf2.columns:
                    mdf2[col] = pd.to_numeric(
                        mdf2[col], errors="coerce"
                    ).fillna(0)
            if "START_TIME" in mdf2.columns:
                mdf2["START_TIME"] = pd.to_datetime(
                    mdf2["START_TIME"], errors="coerce")
            meter_all.append(mdf2)

    if meter_all:
        st.markdown(
            '<div style="height:8px;"></div>',
            unsafe_allow_html=True
        )
        section_header("CREDIT TREND")
        all_m = pd.concat(meter_all, ignore_index=True)
        all_m["DATE"] = all_m["START_TIME"].dt.date
        cmap  = {n: get_env_color(n)
                 for n in all_m["_ACCOUNT"].unique()}
        daily = all_m.groupby(
            ["DATE","_ACCOUNT"]
        )["CREDITS_USED"].sum().reset_index()
        fig = px.area(
            daily, x="DATE", y="CREDITS_USED",
            color="_ACCOUNT",
            color_discrete_map=cmap,
            title="Daily Credit Consumption",
            height=320
        )
        fig.update_traces(line=dict(width=2))
        fig.update_layout(
            xaxis_title="",
            yaxis_title="Credits",
            legend_title_text=""
        )
        st.plotly_chart(fig, use_container_width=True,
                         key="ov_credit_trend")


# ═══════════════════════════════════════════════════════
# TAB 2 — WAREHOUSES
# ═══════════════════════════════════════════════════════

with tab_warehouses:
    section_header("WAREHOUSE BROWSER")

    wf1, wf2, wf3 = st.columns(3)
    with wf1:
        wh_acc = st.selectbox("Environment",
                               connected,
                               key="wh_acc")
    with wf2:
        wh_state_f = st.selectbox(
            "State Filter",
            ["All","Running","Suspended"],
            key="wh_state_f"
        )
    with wf3:
        wh_search = st.text_input(
            "🔍 Search",
            key="wh_search",
            placeholder="Filter by name…"
        )

    wdf = fetch_warehouses(id(manager), wh_acc)
    env_color_wh = get_env_color(wh_acc)

    if wdf.empty:
        st.info("No warehouses found.")
    else:
        name_c   = next((c for c in ["name","NAME"]
                          if c in wdf.columns), None)
        state_c  = next((c for c in ["state","STATE"]
                          if c in wdf.columns), None)
        size_c   = next((c for c in ["size","SIZE"]
                          if c in wdf.columns), None)
        type_c   = next((c for c in ["type","TYPE"]
                          if c in wdf.columns), None)
        auto_s_c = next((c for c in [
            "auto_suspend","AUTO_SUSPEND"]
            if c in wdf.columns), None)
        auto_r_c = next((c for c in [
            "auto_resume","AUTO_RESUME"]
            if c in wdf.columns), None)
        min_cc_c = next((c for c in [
            "min_cluster_count","MIN_CLUSTER_COUNT"]
            if c in wdf.columns), None)
        max_cc_c = next((c for c in [
            "max_cluster_count","MAX_CLUSTER_COUNT"]
            if c in wdf.columns), None)
        owner_c  = next((c for c in ["owner","OWNER"]
                          if c in wdf.columns), None)
        rm_c     = next((c for c in [
            "resource_monitor","RESOURCE_MONITOR"]
            if c in wdf.columns), None)
        queued_c = next((c for c in [
            "queued","QUEUED"]
            if c in wdf.columns), None)
        running_c= next((c for c in [
            "running","RUNNING"]
            if c in wdf.columns), None)
        comment_c= next((c for c in [
            "comment","COMMENT"]
            if c in wdf.columns), None)

        filt = wdf.copy()
        if wh_state_f == "Running" and state_c:
            filt = filt[filt[state_c].str.upper() == "STARTED"]
        elif wh_state_f == "Suspended" and state_c:
            filt = filt[filt[state_c].str.upper() == "SUSPENDED"]
        if wh_search and name_c:
            filt = filt[filt[name_c].str.contains(
                wh_search, case=False, na=False)]

        st.markdown(
            f'<div style="font-size:0.72rem;'
            f'color:{COLORS["text_muted"]};margin-bottom:10px;">'
            f'{len(filt)} warehouse(s) shown</div>',
            unsafe_allow_html=True
        )

        rows = list(filt.iterrows())
        for idx in range(0, len(rows), 2):
            cols2 = st.columns(2)
            for ci, (_, wh) in enumerate(rows[idx:idx+2]):
                w_name   = wh.get(name_c,   "?")  if name_c    else "?"
                w_state  = wh.get(state_c,  "?")  if state_c   else "?"
                w_size   = wh.get(size_c,   "?")  if size_c    else "?"
                w_type   = wh.get(type_c,   "STANDARD") if type_c else "STANDARD"
                w_auto_s = wh.get(auto_s_c, "—")  if auto_s_c  else "—"
                w_auto_r = str(wh.get(auto_r_c,"")) if auto_r_c else "—"
                w_min_c  = wh.get(min_cc_c, "1")  if min_cc_c  else "1"
                w_max_c  = wh.get(max_cc_c, "1")  if max_cc_c  else "1"
                w_owner  = wh.get(owner_c,  "—")  if owner_c   else "—"
                w_rm     = wh.get(rm_c,     "—")  if rm_c      else "—"
                w_run    = safe_int(wh.get(running_c, 0) if running_c else 0)
                w_que    = safe_int(wh.get(queued_c,  0) if queued_c  else 0)
                w_cmt    = wh.get(comment_c, "") if comment_c else ""

                with cols2[ci]:
                    st.markdown(
                        _wh_card(
                            w_name, w_state, w_size,
                            w_type, w_auto_s, w_auto_r,
                            w_min_c, w_max_c, w_owner,
                            w_rm, w_run, w_que,
                            w_cmt, env_color_wh
                        ),
                        unsafe_allow_html=True
                    )

        with st.expander("📋 Full Warehouse Table"):
            st.dataframe(wdf, use_container_width=True,
                          hide_index=True, height=400)
            st.download_button(
                "📥 Download CSV",
                data=wdf.to_csv(index=False),
                file_name=f"warehouses_{wh_acc}_{datetime.date.today()}.csv",
                mime="text/csv",
                key="wh_dl"
            )


# ═══════════════════════════════════════════════════════
# TAB 3 — CREATE WAREHOUSE
# ═══════════════════════════════════════════════════════

with tab_create:
    section_header("CREATE NEW WAREHOUSE")

    st.markdown(
        _info_box(
            "Configure and create a new Snowflake virtual warehouse "
            "with full control over size, scaling, auto-suspend, "
            "resource monitors and more.",
            accent=COLORS["pwc_orange"]
        ),
        unsafe_allow_html=True
    )

    st.markdown(_step(1, "Identity"), unsafe_allow_html=True)
    cr1, cr2, cr3 = st.columns(3)
    with cr1:
        cr_acc  = st.selectbox("Account", connected, key="cr_wh_acc")
        cr_name = st.text_input("Warehouse Name *",
                                 placeholder="MY_WAREHOUSE",
                                 key="cr_wh_name")
    with cr2:
        cr_type = st.selectbox("Type",
                                ["STANDARD","SNOWPARK-OPTIMIZED"],
                                key="cr_wh_type")
        cr_size = st.selectbox(
            "Size",
            ["X-SMALL","SMALL","MEDIUM","LARGE",
             "X-LARGE","2X-LARGE","3X-LARGE","4X-LARGE"],
            index=1, key="cr_wh_size"
        )
    with cr3:
        cr_comment = st.text_area("Comment",
                                   placeholder="Purpose of this warehouse",
                                   height=80,
                                   key="cr_wh_comment")

    st.markdown(_step(2, "Auto-Suspend & Resume"), unsafe_allow_html=True)
    as1, as2, as3 = st.columns(3)
    with as1:
        cr_auto_s = st.number_input("Auto-Suspend (seconds)",
                                     min_value=0, value=300, step=60,
                                     key="cr_auto_suspend")
    with as2:
        cr_auto_r = st.checkbox("Enable Auto-Resume", value=True,
                                 key="cr_auto_resume")
    with as3:
        cr_init_s = st.checkbox("Initially Suspended", value=False,
                                 key="cr_init_susp")

    st.markdown(_step(3, "Multi-Cluster Scaling"), unsafe_allow_html=True)
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        cr_min_c = st.number_input("Min Clusters", min_value=1,
                                    max_value=10, value=1,
                                    key="cr_min_cluster")
    with sc2:
        cr_max_c = st.number_input("Max Clusters", min_value=1,
                                    max_value=10, value=1,
                                    key="cr_max_cluster")
    with sc3:
        cr_scale_policy = st.selectbox("Scaling Policy",
                                        ["STANDARD","ECONOMY"],
                                        key="cr_scaling_policy")

    st.markdown(_step(4, "Query Execution"), unsafe_allow_html=True)
    qe1, qe2, qe3 = st.columns(3)
    with qe1:
        cr_max_conc = st.number_input("Max Concurrency Level",
                                       min_value=1, max_value=10,
                                       value=8, key="cr_max_conc")
    with qe2:
        cr_stmt_timeout = st.number_input("Statement Timeout (s, 0=none)",
                                           min_value=0, value=0,
                                           key="cr_stmt_timeout")
    with qe3:
        cr_queued_timeout = st.number_input("Queued Timeout (s, 0=none)",
                                             min_value=0, value=0,
                                             key="cr_queued_timeout")

    st.markdown(_step(5, "Resource Monitor"), unsafe_allow_html=True)
    rm_df  = fetch_resource_monitors(id(manager), cr_acc)
    rm_nc  = next((c for c in ["name","NAME"]
                    if c in rm_df.columns), None)
    rm_list = rm_df[rm_nc].tolist() \
        if rm_nc and not rm_df.empty else []
    cr_rm = st.selectbox("Assign Resource Monitor",
                          options=["(none)"] + rm_list,
                          key="cr_wh_rm")

    # Build SQL
    if cr_name and cr_acc:
        props = [
            f"    WAREHOUSE_TYPE = {cr_type}",
            f"    WAREHOUSE_SIZE = '{cr_size}'",
            f"    AUTO_SUSPEND = {cr_auto_s}",
            f"    AUTO_RESUME = {'TRUE' if cr_auto_r else 'FALSE'}",
        ]
        if cr_init_s:
            props.append("    INITIALLY_SUSPENDED = TRUE")
        if cr_min_c > 1 or cr_max_c > 1:
            props.append(f"    MIN_CLUSTER_COUNT = {cr_min_c}")
            props.append(f"    MAX_CLUSTER_COUNT = {cr_max_c}")
            props.append(f"    SCALING_POLICY = {cr_scale_policy}")
        if cr_max_conc != 8:
            props.append(f"    MAX_CONCURRENCY_LEVEL = {cr_max_conc}")
        if cr_stmt_timeout > 0:
            props.append(f"    STATEMENT_TIMEOUT_IN_SECONDS = {cr_stmt_timeout}")
        if cr_queued_timeout > 0:
            props.append(f"    STATEMENT_QUEUED_TIMEOUT_IN_SECONDS = {cr_queued_timeout}")
        if cr_rm != "(none)":
            props.append(f"    RESOURCE_MONITOR = '{cr_rm}'")
        if cr_comment:
            props.append(f"    COMMENT = '{cr_comment}'")

        create_sql = (
            f'CREATE WAREHOUSE IF NOT EXISTS "{cr_name}"\n'
            + "\n".join(props) + ";"
        )

        section_header("GENERATED SQL")
        st.markdown(_sql_block(create_sql), unsafe_allow_html=True)

        cb1, cb2 = st.columns(2)
        with cb1:
            if st.button("▶️ Create Warehouse", type="primary",
                          key="btn_create_wh"):
                with st.status(f"Creating {cr_name}…",
                               expanded=True) as s:
                    st.write("Validating config…")
                    time.sleep(0.3)
                    ok, result = run_statement(cr_acc, create_sql)
                    time.sleep(0.3)
                    s.update(
                        label=f"✅ {cr_name} created!" if ok else "❌ Failed",
                        state="complete" if ok else "error",
                        expanded=False
                    )
                if ok:
                    st.success(f"✅ Warehouse **{cr_name}** created!")
                    st.cache_data.clear()
                    st.balloons()
                else:
                    st.error(f"❌ {result}")
        with cb2:
            if st.button("📋 Copy SQL", key="btn_copy_wh"):
                st.code(create_sql, language="sql")


# ═══════════════════════════════════════════════════════
# TAB 4 — MANAGE
# ═══════════════════════════════════════════════════════

with tab_manage:
    section_header("MANAGE WAREHOUSES")

    mg_acc = st.selectbox("Environment", connected, key="mg_wh_acc")
    mg_wdf = fetch_warehouses(id(manager), mg_acc)

    if mg_wdf.empty:
        st.info("No warehouses found.")
    else:
        mg_nc  = next((c for c in ["name","NAME"]
                        if c in mg_wdf.columns), None)
        mg_sc  = next((c for c in ["state","STATE"]
                        if c in mg_wdf.columns), None)
        mg_szc = next((c for c in ["size","SIZE"]
                        if c in mg_wdf.columns), None)

        for _, wh in mg_wdf.iterrows():
            w_name  = wh.get(mg_nc,  "?") if mg_nc  else "?"
            w_state = wh.get(mg_sc,  "?") if mg_sc  else "?"
            w_size  = wh.get(mg_szc, "?") if mg_szc else "?"
            is_run  = str(w_state).upper() == "STARTED"

            with st.expander(
                f"⚙️ {w_name}  ·  "
                f"{'▶ RUNNING' if is_run else '⏸ SUSPENDED'}"
                f"  [{w_size}]"
            ):
                mc1, mc2 = st.columns([2, 1])

                with mc1:
                    st.markdown(_state_pill(w_state),
                                 unsafe_allow_html=True)
                    st.markdown(
                        f'<div style="margin-top:8px;font-size:0.78rem;'
                        f'color:{COLORS["text_secondary"]};">'
                        f'Size: <b>{w_size}</b></div>',
                        unsafe_allow_html=True
                    )

                with mc2:
                    if not is_run:
                        if st.button("▶️ Resume",
                                      key=f"res_{mg_acc}_{w_name}",
                                      type="primary",
                                      use_container_width=True):
                            ok, msg = run_statement(
                                mg_acc,
                                f'ALTER WAREHOUSE "{w_name}" RESUME;'
                            )
                            if ok:
                                st.success("✅ Resumed")
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(f"❌ {msg}")
                    else:
                        if st.button("⏸️ Suspend",
                                      key=f"sus_{mg_acc}_{w_name}",
                                      use_container_width=True):
                            ok, msg = run_statement(
                                mg_acc,
                                f'ALTER WAREHOUSE "{w_name}" SUSPEND;'
                            )
                            if ok:
                                st.success("✅ Suspended")
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(f"❌ {msg}")

                    if st.button("🔄 Abort Queries",
                                  key=f"abort_{mg_acc}_{w_name}",
                                  use_container_width=True):
                        ok, msg = run_statement(
                            mg_acc,
                            f'ALTER WAREHOUSE "{w_name}" ABORT ALL QUERIES;'
                        )
                        if ok:
                            st.success("✅ Queries aborted")
                        else:
                            st.error(f"❌ {msg}")

                with st.expander("↕️ Resize"):
                    new_size = st.selectbox(
                        "New Size",
                        ["X-SMALL","SMALL","MEDIUM","LARGE",
                         "X-LARGE","2X-LARGE","3X-LARGE","4X-LARGE"],
                        key=f"resize_{mg_acc}_{w_name}"
                    )
                    if st.button("Apply Resize",
                                  key=f"apply_resize_{mg_acc}_{w_name}",
                                  type="primary"):
                        ok, msg = run_statement(
                            mg_acc,
                            f'ALTER WAREHOUSE "{w_name}" SET '
                            f"WAREHOUSE_SIZE = '{new_size}';"
                        )
                        if ok:
                            st.success(f"✅ Resized to {new_size}")
                            st.cache_data.clear()
                        else:
                            st.error(f"❌ {msg}")

                with st.expander("⚙️ Edit Settings"):
                    es1, es2 = st.columns(2)
                    with es1:
                        new_as = st.number_input(
                            "Auto-Suspend (s)", min_value=0,
                            value=300,
                            key=f"as_{mg_acc}_{w_name}"
                        )
                        new_ar = st.checkbox(
                            "Auto-Resume", value=True,
                            key=f"ar_{mg_acc}_{w_name}"
                        )
                    with es2:
                        new_mc = st.number_input(
                            "Max Concurrency", min_value=1,
                            max_value=10, value=8,
                            key=f"mc_{mg_acc}_{w_name}"
                        )
                        new_cmt = st.text_input(
                            "Comment",
                            key=f"cmt_{mg_acc}_{w_name}"
                        )
                    if st.button("💾 Save Settings",
                                  key=f"save_{mg_acc}_{w_name}",
                                  type="primary"):
                        cmt_part = (
                            f"\n    COMMENT = '{new_cmt}'"
                            if new_cmt else ""
                        )
                        set_sql = (
                            f'ALTER WAREHOUSE "{w_name}" SET\n'
                            f'    AUTO_SUSPEND = {new_as}\n'
                            f'    AUTO_RESUME = {"TRUE" if new_ar else "FALSE"}\n'
                            f'    MAX_CONCURRENCY_LEVEL = {new_mc}'
                            f'{cmt_part};'
                        )
                        ok, msg = run_statement(mg_acc, set_sql)
                        if ok:
                            st.success("✅ Settings saved!")
                            st.cache_data.clear()
                        else:
                            st.error(f"❌ {msg}")

                with st.expander("💰 Assign Resource Monitor"):
                    rm_df2  = fetch_resource_monitors(id(manager), mg_acc)
                    rm_nc2  = next((c for c in ["name","NAME"]
                                     if c in rm_df2.columns), None)
                    rm_list2= rm_df2[rm_nc2].tolist() \
                        if rm_nc2 and not rm_df2.empty else []
                    sel_rm  = st.selectbox(
                        "Resource Monitor",
                        options=["(none)"] + rm_list2,
                        key=f"sel_rm_{mg_acc}_{w_name}"
                    )
                    if st.button("Assign", type="primary",
                                  key=f"assign_rm_{mg_acc}_{w_name}"):
                        val = "null" if sel_rm == "(none)" \
                            else f'"{sel_rm}"'
                        ok, msg = run_statement(
                            mg_acc,
                            f'ALTER WAREHOUSE "{w_name}" '
                            f'SET RESOURCE_MONITOR = {val};'
                        )
                        if ok:
                            st.success("✅ Monitor assigned!")
                            st.cache_data.clear()
                        else:
                            st.error(f"❌ {msg}")

                with st.expander("🗑️ Drop Warehouse"):
                    st.warning(f"⚠️ Permanently drops **{w_name}**.")
                    if st.checkbox("Confirm drop",
                                    key=f"cfm_{mg_acc}_{w_name}"):
                        if st.button("🗑️ Drop",
                                      key=f"drop_{mg_acc}_{w_name}",
                                      type="primary"):
                            ok, msg = run_statement(
                                mg_acc,
                                f'DROP WAREHOUSE IF EXISTS "{w_name}";'
                            )
                            if ok:
                                st.success(f"✅ {w_name} dropped")
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(f"❌ {msg}")


# ═══════════════════════════════════════════════════════
# TAB 5 — PERFORMANCE
# ═══════════════════════════════════════════════════════

with tab_performance:
    section_header("PERFORMANCE ANALYTICS")

    pf1, pf2, pf3 = st.columns(3)
    with pf1:
        perf_acc = st.selectbox("Environment", connected, key="perf_acc")
    with pf2:
        perf_wdf    = fetch_warehouses(id(manager), perf_acc)
        perf_nc     = next((c for c in ["name","NAME"]
                             if c in perf_wdf.columns), None)
        perf_wh_list= (["ALL"] + perf_wdf[perf_nc].tolist()
                        if perf_nc and not perf_wdf.empty else ["ALL"])
        perf_wh = st.selectbox("Warehouse", perf_wh_list, key="perf_wh")
    with pf3:
        perf_days = st.selectbox(
            "Time Range",
            [1,7,14,30], index=1,
            format_func=lambda x: f"Last {x} days",
            key="perf_days"
        )

    meter_df = fetch_metering(id(manager), perf_acc, perf_days)
    load_df  = fetch_load(id(manager), perf_acc, perf_days)

    if not meter_df.empty:
        for col in ["CREDITS_USED","CREDITS_USED_COMPUTE",
                    "CREDITS_USED_CLOUD_SERVICES"]:
            if col in meter_df.columns:
                meter_df[col] = pd.to_numeric(
                    meter_df[col], errors="coerce").fillna(0)
        if "START_TIME" in meter_df.columns:
            meter_df["START_TIME"] = pd.to_datetime(
                meter_df["START_TIME"], errors="coerce")

        wh_nc2 = next((c for c in [
            "WAREHOUSE_NAME","warehouse_name"]
            if c in meter_df.columns), None)
        if perf_wh != "ALL" and wh_nc2:
            meter_df = meter_df[meter_df[wh_nc2] == perf_wh]

        total_c   = safe_float(meter_df["CREDITS_USED"].sum())
        compute_c = safe_float(
            meter_df["CREDITS_USED_COMPUTE"].sum()
            if "CREDITS_USED_COMPUTE" in meter_df.columns else 0)
        cloud_c   = safe_float(
            meter_df["CREDITS_USED_CLOUD_SERVICES"].sum()
            if "CREDITS_USED_CLOUD_SERVICES"
            in meter_df.columns else 0)

        pk1, pk2, pk3 = st.columns(3)
        with pk1:
            st.markdown(
                _kpi("💰", fmt_credits(total_c),
                     "Total Credits", COLORS["pwc_gold"]),
                unsafe_allow_html=True
            )
        with pk2:
            st.markdown(
                _kpi("🖥️", fmt_credits(compute_c),
                     "Compute Credits", COLORS["pwc_orange"]),
                unsafe_allow_html=True
            )
        with pk3:
            st.markdown(
                _kpi("☁️", fmt_credits(cloud_c),
                     "Cloud Credits", COLORS["blue"]),
                unsafe_allow_html=True
            )

        st.markdown('<div style="height:12px;"></div>',
                     unsafe_allow_html=True)

        pt1, pt2, pt3 = st.tabs([
            "💰 Credit Usage",
            "📊 Load & Queuing",
            "🔍 Query Analysis"
        ])

        with pt1:
            meter_df["DATE"] = meter_df["START_TIME"].dt.date
            c1, c2 = st.columns(2)
            with c1:
                if wh_nc2:
                    wh_creds = meter_df.groupby(wh_nc2)[
                        "CREDITS_USED"
                    ].sum().reset_index().nlargest(
                        15, "CREDITS_USED")
                    fig = px.bar(
                        wh_creds, x=wh_nc2, y="CREDITS_USED",
                        title="Credits by Warehouse", height=340,
                        color="CREDITS_USED",
                        color_continuous_scale=[
                            COLORS["bg_elevated"],
                            COLORS["pwc_orange"],
                            COLORS["red"]
                        ]
                    )
                    fig.update_layout(
                        xaxis_tickangle=-30,
                        xaxis_title="", yaxis_title="Credits",
                        coloraxis_showscale=False)
                    st.plotly_chart(fig, use_container_width=True,
                                     key="perf_wh_credits")
            with c2:
                if ("CREDITS_USED_COMPUTE" in meter_df.columns):
                    type_data = pd.DataFrame([
                        {"Type": "Compute", "Credits": compute_c},
                        {"Type": "Cloud Services", "Credits": cloud_c}
                    ])
                    fig2 = go.Figure(go.Pie(
                        labels=type_data["Type"],
                        values=type_data["Credits"],
                        hole=0.6,
                        marker_colors=[COLORS["pwc_orange"], COLORS["blue"]],
                        textinfo="label+percent"
                    ))
                    fig2.update_layout(
                        title="Credit Type Split", height=340,
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(color=COLORS["text_secondary"]))
                    st.plotly_chart(fig2, use_container_width=True,
                                     key="perf_credit_split")

            daily_m = meter_df.groupby("DATE")[
                "CREDITS_USED"].sum().reset_index()
            fig3 = px.area(
                daily_m, x="DATE", y="CREDITS_USED",
                title="Daily Credit Trend", height=300,
                color_discrete_sequence=[COLORS["pwc_orange"]]
            )
            fig3.update_traces(
                line=dict(width=2, color=COLORS["pwc_orange"]))
            fig3.update_layout(xaxis_title="", yaxis_title="Credits")
            st.plotly_chart(fig3, use_container_width=True,
                             key="perf_daily_trend")

        with pt2:
            if not load_df.empty:
                for col in ["AVG_RUNNING","AVG_QUEUED_LOAD","AVG_BLOCKED"]:
                    if col in load_df.columns:
                        load_df[col] = pd.to_numeric(
                            load_df[col], errors="coerce").fillna(0)
                if "START_TIME" in load_df.columns:
                    load_df["START_TIME"] = pd.to_datetime(
                        load_df["START_TIME"], errors="coerce")
                wh_lnc = next((c for c in [
                    "WAREHOUSE_NAME","warehouse_name"]
                    if c in load_df.columns), None)
                if perf_wh != "ALL" and wh_lnc:
                    load_df = load_df[load_df[wh_lnc] == perf_wh]

                y_cols = [c for c in
                          ["AVG_RUNNING","AVG_QUEUED_LOAD"]
                          if c in load_df.columns]
                if y_cols:
                    fig_load = px.area(
                        load_df, x="START_TIME", y=y_cols,
                        title="Warehouse Load Over Time",
                        height=380,
                        color_discrete_map={
                            "AVG_RUNNING": COLORS["green"],
                            "AVG_QUEUED_LOAD": COLORS["yellow"]
                        }
                    )
                    fig_load.update_layout(
                        xaxis_title="", yaxis_title="Avg Load",
                        legend_title_text="")
                    st.plotly_chart(fig_load, use_container_width=True,
                                     key="perf_load")
            else:
                st.info("Load history not available.")

        with pt3:
            if perf_wh != "ALL":
                q_df = fetch_query_history(
                    id(manager), perf_acc, perf_wh, perf_days)
                if not q_df.empty:
                    for col in ["DURATION_SEC","BYTES_SCANNED","ROWS_PRODUCED"]:
                        if col in q_df.columns:
                            q_df[col] = pd.to_numeric(
                                q_df[col], errors="coerce").fillna(0)

                    qk1, qk2, qk3, qk4 = st.columns(4)
                    with qk1:
                        st.markdown(
                            _kpi("📊", f"{len(q_df):,}",
                                 "Total Queries", COLORS["blue"]),
                            unsafe_allow_html=True)
                    with qk2:
                        avg_s = safe_float(
                            q_df["DURATION_SEC"].mean()
                            if "DURATION_SEC" in q_df.columns else 0)
                        st.markdown(
                            _kpi("⏱️", f"{avg_s:.1f}s",
                                 "Avg Duration", COLORS["pwc_gold"]),
                            unsafe_allow_html=True)
                    with qk3:
                        n_fail = safe_int(len(q_df[
                            q_df["EXECUTION_STATUS"] == "FAIL"])
                            if "EXECUTION_STATUS" in q_df.columns else 0)
                        st.markdown(
                            _kpi("❌", str(n_fail),
                                 "Failed Queries", COLORS["red"]),
                            unsafe_allow_html=True)
                    with qk4:
                        gb = safe_float(
                            q_df["BYTES_SCANNED"].sum() / 1e9
                            if "BYTES_SCANNED" in q_df.columns else 0)
                        st.markdown(
                            _kpi("💾", f"{gb:.1f} GB",
                                 "Data Scanned", COLORS["cyan"]),
                            unsafe_allow_html=True)

                    qa1, qa2 = st.columns(2)
                    with qa1:
                        if "QUERY_TYPE" in q_df.columns:
                            qt = q_df["QUERY_TYPE"].value_counts().head(10)
                            fig_qt = px.pie(
                                values=qt.values, names=qt.index,
                                hole=0.5, height=320,
                                title="Query Types",
                                color_discrete_sequence=CHART_COLORS
                            )
                            st.plotly_chart(fig_qt, use_container_width=True,
                                             key="perf_qt_pie")
                    with qa2:
                        if "DURATION_SEC" in q_df.columns:
                            top_slow = q_df.nlargest(10,"DURATION_SEC").copy()
                            if "QUERY_TEXT" in top_slow.columns:
                                top_slow["Q"] = (
                                    top_slow["QUERY_TEXT"]
                                    .astype(str).str[:40]
                                )
                            fig_slow = px.bar(
                                top_slow,
                                x="DURATION_SEC",
                                y="Q" if "Q" in top_slow.columns
                                else top_slow.index.astype(str),
                                orientation="h",
                                title="Top 10 Slowest",
                                height=320,
                                color="DURATION_SEC",
                                color_continuous_scale=[
                                    COLORS["bg_elevated"], COLORS["red"]]
                            )
                            fig_slow.update_layout(
                                yaxis_title="",
                                xaxis_title="Duration (s)",
                                coloraxis_showscale=False)
                            st.plotly_chart(fig_slow,
                                             use_container_width=True,
                                             key="perf_slow_q")
                else:
                    st.info("No query history for this warehouse.")
            else:
                st.info("Select a specific warehouse to view query analysis.")
    else:
        st.info("No metering data available.")


# ═══════════════════════════════════════════════════════
# TAB 6 — RESOURCE MONITORS
# ═══════════════════════════════════════════════════════

with tab_resource_monitors:
    section_header("RESOURCE MONITOR OVERVIEW")

    st.markdown(
        _info_box(
            "Resource Monitors track credit usage and trigger actions "
            "(notify, suspend, suspend_immediate) when thresholds are "
            "reached — protecting against unexpected cost overruns.",
            accent=COLORS["pwc_gold"]
        ),
        unsafe_allow_html=True
    )

    for acc in connected:
        env_color = get_env_color(acc)
        rm_df     = fetch_resource_monitors(id(manager), acc)

        st.markdown(
            f'<div style="font-size:0.8rem;font-weight:800;'
            f'color:{env_color};margin:12px 0 8px 0;">'
            f'{acc} — {len(rm_df)} monitor(s)</div>',
            unsafe_allow_html=True
        )

        if rm_df.empty:
            st.markdown(
                _alert("No resource monitors found. Create one in the 🆕 Create Monitor tab.",
                       COLORS["text_muted"], "ℹ️"),
                unsafe_allow_html=True
            )
            continue

        rm_nc    = next((c for c in ["name","NAME"]
                          if c in rm_df.columns), None)
        credit_q = next((c for c in ["credit_quota","CREDIT_QUOTA"]
                          if c in rm_df.columns), None)
        used_c   = next((c for c in ["used_credits","USED_CREDITS"]
                          if c in rm_df.columns), None)
        remain_c = next((c for c in ["remaining_credits","REMAINING_CREDITS"]
                          if c in rm_df.columns), None)
        freq_c   = next((c for c in ["frequency","FREQUENCY"]
                          if c in rm_df.columns), None)
        sus_at_c = next((c for c in ["suspend_at","SUSPEND_AT"]
                          if c in rm_df.columns), None)
        notif_c  = next((c for c in ["notify_at","NOTIFY_AT"]
                          if c in rm_df.columns), None)

        rm_rows = list(rm_df.iterrows())
        for idx in range(0, len(rm_rows), 3):
            rcols = st.columns(3)
            for ci, (_, rm) in enumerate(rm_rows[idx:idx+3]):
                r_name  = rm.get(rm_nc,    "?") if rm_nc    else "?"
                r_quota = safe_float(rm.get(credit_q, 0))
                r_used  = safe_float(rm.get(used_c,   0))
                r_remain= safe_float(rm.get(remain_c, 0))
                r_freq  = rm.get(freq_c,   "?") if freq_c   else "?"
                r_sus   = rm.get(sus_at_c, "—") if sus_at_c else "—"
                r_ntf   = rm.get(notif_c,  "—") if notif_c  else "—"

                pct       = min((r_used / r_quota * 100)
                                if r_quota > 0 else 0, 100)
                bar_color = (
                    COLORS["green"]  if pct < 50
                    else COLORS["yellow"] if pct < 80
                    else COLORS["red"]
                )

                with rcols[ci]:
                    st.markdown(
                        _rm_card(r_name, r_quota, r_used,
                                  r_remain, r_freq, r_sus,
                                  r_ntf, pct, bar_color),
                        unsafe_allow_html=True
                    )
                    with st.expander(f"⚙️ Manage {r_name}"):
                        ma1, ma2 = st.columns(2)
                        with ma1:
                            if st.button("🔄 Reset",
                                          key=f"rm_reset_{acc}_{r_name}",
                                          type="primary"):
                                ok, msg = run_statement(
                                    acc,
                                    f'ALTER RESOURCE MONITOR "{r_name}" '
                                    f'MODIFY CREDIT_QUOTA = {r_quota};'
                                )
                                if ok:
                                    st.success("✅ Reset")
                                    st.cache_data.clear()
                                else:
                                    st.error(f"❌ {msg}")
                        with ma2:
                            if st.checkbox("Confirm drop",
                                            key=f"cfm_rm_{acc}_{r_name}"):
                                if st.button("🗑️ Drop",
                                              key=f"drop_rm_{acc}_{r_name}",
                                              type="primary"):
                                    ok, msg = run_statement(
                                        acc,
                                        f'DROP RESOURCE MONITOR IF EXISTS "{r_name}";'
                                    )
                                    if ok:
                                        st.success("✅ Dropped")
                                        st.cache_data.clear()
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {msg}")
        st.markdown("---")


# ═══════════════════════════════════════════════════════
# TAB 7 — CREATE RESOURCE MONITOR
# ═══════════════════════════════════════════════════════

with tab_create_rm:
    section_header("CREATE RESOURCE MONITOR")

    st.markdown(
        _info_box(
            "A Resource Monitor tracks credit usage over a defined period "
            "and can notify, suspend, or immediately suspend warehouses "
            "when thresholds are reached.",
            accent=COLORS["pwc_gold"]
        ),
        unsafe_allow_html=True
    )

    st.markdown(_step(1, "Identity & Credit Quota"), unsafe_allow_html=True)
    rm1, rm2, rm3 = st.columns(3)
    with rm1:
        rm_acc  = st.selectbox("Account", connected, key="rm_create_acc")
        rm_name = st.text_input("Monitor Name *",
                                 placeholder="DEPT_MONTHLY_MONITOR",
                                 key="rm_name")
    with rm2:
        rm_quota = st.number_input("Credit Quota *",
                                    min_value=1, value=1000,
                                    key="rm_quota")
        rm_freq  = st.selectbox("Reset Frequency",
                                 ["MONTHLY","DAILY","WEEKLY",
                                  "YEARLY","NEVER"],
                                 key="rm_freq")
    with rm3:
        rm_start = st.date_input("Start Date",
                                  value=datetime.date.today(),
                                  key="rm_start")
        rm_end   = st.date_input("End Date (optional)",
                                  value=None, key="rm_end")

    st.markdown(_step(2, "Trigger Thresholds"), unsafe_allow_html=True)
    st.markdown(
        _info_box(
            "Thresholds are defined as % of credit quota. "
            "Multiple notification triggers can be set.",
            accent=COLORS["blue"]
        ),
        unsafe_allow_html=True
    )

    t1, t2 = st.columns(2)
    with t1:
        st.markdown(
            f'<div style="font-size:0.72rem;color:{COLORS["text_muted"]};'
            f'text-transform:uppercase;letter-spacing:1px;'
            f'margin-bottom:8px;">🔔 Notification Triggers (%)</div>',
            unsafe_allow_html=True
        )
        notif_pcts = st.multiselect(
            "Notify at (%)",
            options=[50,75,80,90,95,100,110,120,150],
            default=[75,90], key="rm_notif_pcts"
        )
    with t2:
        st.markdown(
            f'<div style="font-size:0.72rem;color:{COLORS["text_muted"]};'
            f'text-transform:uppercase;letter-spacing:1px;'
            f'margin-bottom:8px;">⏸ Action Triggers (%)</div>',
            unsafe_allow_html=True
        )
        sus_pct     = st.number_input("Suspend at (%) — 0=none",
                                       min_value=0, max_value=1000,
                                       value=100, key="rm_sus_pct")
        sus_imm_pct = st.number_input("Suspend Immediately (%) — 0=none",
                                       min_value=0, max_value=1000,
                                       value=110, key="rm_sus_imm_pct")

    st.markdown(_step(3, "Warehouse Assignment"), unsafe_allow_html=True)
    wa1, wa2 = st.columns(2)
    with wa1:
        rm_level = st.radio("Monitor Level",
                             ["Account Level","Specific Warehouses"],
                             horizontal=True, key="rm_level")
    with wa2:
        rm_wh_list = fetch_warehouses_list(id(manager), rm_acc)
        rm_sel_whs = st.multiselect(
            "Select Warehouses",
            options=rm_wh_list, key="rm_sel_whs",
            disabled=(rm_level == "Account Level")
        )

    st.markdown(_step(4, "Notification Settings"), unsafe_allow_html=True)
    nc1, nc2 = st.columns(2)
    with nc1:
        rm_notify_users = st.text_input(
            "Notify Users (comma-separated)",
            placeholder="ADMIN, FINANCE_USER",
            key="rm_notify_users"
        )
    with nc2:
        rm_notify_emails = st.text_input(
            "Notify Emails (comma-separated)",
            placeholder="admin@company.com",
            key="rm_notify_emails"
        )

    # Build SQL
    if rm_name and rm_acc and rm_quota > 0:
        triggers = []
        for p in sorted(notif_pcts):
            triggers.append(f"    ON {p} PERCENT DO NOTIFY")
        if sus_pct > 0:
            triggers.append(f"    ON {sus_pct} PERCENT DO SUSPEND")
        if sus_imm_pct > 0:
            triggers.append(
                f"    ON {sus_imm_pct} PERCENT DO SUSPEND_IMMEDIATE")

        notif_u = ""
        if rm_notify_users:
            ul = ", ".join(
                [f'"{u.strip()}"'
                 for u in rm_notify_users.split(",") if u.strip()])
            notif_u = f"\n    NOTIFY = ({ul})"

        end_c = (f"\n    END_TIMESTAMP = '{rm_end} 00:00:00'"
                  if rm_end else "")

        create_rm_sql = (
            f'CREATE OR REPLACE RESOURCE MONITOR "{rm_name}"\n'
            f'    CREDIT_QUOTA = {rm_quota}\n'
            f'    FREQUENCY = {rm_freq}\n'
            f"    START_TIMESTAMP = '{rm_start} 00:00:00'"
            f"{end_c}{notif_u}\n"
            f"TRIGGERS\n"
            + "\n".join(triggers) + ";"
        )

        assign_sqls = []
        if rm_level == "Account Level":
            assign_sqls.append(
                f'ALTER ACCOUNT SET RESOURCE_MONITOR = "{rm_name}";'
            )
        else:
            for wh in rm_sel_whs:
                assign_sqls.append(
                    f'ALTER WAREHOUSE "{wh}" SET '
                    f'RESOURCE_MONITOR = "{rm_name}";'
                )

        all_rm_sqls = [create_rm_sql] + assign_sqls

        section_header("GENERATED SQL")
        for sql in all_rm_sqls:
            st.markdown(_sql_block(sql), unsafe_allow_html=True)

        rmb1, rmb2 = st.columns(2)
        with rmb1:
            if st.button("▶️ Create & Assign Monitor",
                          type="primary", key="btn_create_rm"):
                results = []
                with st.status(f"Creating {rm_name}…",
                               expanded=True) as s:
                    for i, sql in enumerate(all_rm_sqls):
                        lbl = ("📝 Creating monitor…" if i == 0
                               else f"⚙️ Assigning ({i}/{len(assign_sqls)})…")
                        st.write(lbl)
                        ok, msg = run_statement(rm_acc, sql)
                        results.append({
                            "SQL": sql[:60] + "…" if len(sql) > 60 else sql,
                            "Status": "✅ OK" if ok else f"❌ {msg}"
                        })
                        time.sleep(0.15)

                    n_ok  = sum(1 for r in results if "✅" in r["Status"])
                    n_err = len(results) - n_ok
                    s.update(
                        label=(f"✅ {rm_name} created!" if n_err == 0
                               else f"⚠️ {n_err} error(s)"),
                        state="complete" if n_err == 0 else "error",
                        expanded=n_err > 0
                    )

                if n_err == 0:
                    st.success(
                        f"✅ Resource Monitor **{rm_name}** created "
                        f"with quota of **{rm_quota:,}** credits!")
                    st.cache_data.clear()
                    st.balloons()
                else:
                    st.dataframe(pd.DataFrame(results),
                                  use_container_width=True,
                                  hide_index=True)
        with rmb2:
            if st.button("📋 Copy SQL", key="btn_copy_rm"):
                st.code("\n".join(all_rm_sqls), language="sql")

# ─── Footer ───────────────────────────────────────────────────────────────────

st.markdown(f"""
<div style="text-align:center;padding:28px 0 10px;
     border-top:1px solid {COLORS['border']};margin-top:32px;">
    <div style="font-size:0.78rem;font-weight:800;color:{COLORS['text_primary']};">
        ⚙️ Warehouse Manager
        &nbsp;·&nbsp;
        <span style="color:{COLORS['pwc_orange']};font-weight:800;font-size:0.68rem;
              text-transform:uppercase;letter-spacing:0.12em;">
            Powered By PwC Data &amp; AI
        </span>
    </div>
    <div style="margin-top:4px;font-size:0.66rem;color:{COLORS['text_dim']};">
        {len(connected)} environment(s) connected
    </div>
</div>
""", unsafe_allow_html=True)