"""
⏰ Task Manager — View, create, run and monitor
   Snowflake tasks across all environments.
"""

import math
import datetime
import time
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from snowflake_connector import SnowflakeConnectionManager
from theme import (
    inject_css, COLORS, CHART_COLORS,
    get_env_color, pwc_header, section_header,
)

# ─── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Task Manager · PwC",
    page_icon="⏰",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# ─── Safe helpers ─────────────────────────────────────────────────────────────

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


def c(key: str, fallback: str = "#888888") -> str:
    """Safe COLORS lookup — never raises KeyError."""
    return COLORS.get(key, fallback)


def fmt_dur(seconds):
    s = safe_float(seconds)
    if s < 60:
        return f"{s:.1f}s"
    if s < 3600:
        return f"{s/60:.1f}m"
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


# ─── Safe HTML builders ───────────────────────────────────────────────────────
# Every function returns ONE complete self-contained HTML string.
# Never call these inside another f-string or HTML block.

def _kpi(icon, value, label, color, sub=""):
    sub_html = (
        f'<div style="margin-top:6px;font-size:0.72rem;'
        f'color:{c("text_secondary")};">{sub}</div>'
        if sub else ""
    )
    return (
        f'<div style="position:relative;overflow:hidden;'
        f'border-radius:18px;padding:18px 18px 16px;'
        f'background:linear-gradient(180deg,'
        f'rgba(255,255,255,0.03),rgba(255,255,255,0.00)),'
        f'{c("bg_card")};'
        f'border:1px solid rgba(255,255,255,0.06);'
        f'box-shadow:0 14px 28px rgba(0,0,0,0.16);'
        f'height:100%;">'
        f'<div style="position:absolute;inset:0 0 auto 0;'
        f'height:3px;background:{color};"></div>'
        f'<div style="font-size:1.1rem;margin-bottom:8px;">{icon}</div>'
        f'<div style="font-family:JetBrains Mono,monospace;'
        f'font-size:1.55rem;font-weight:700;color:{color};'
        f'line-height:1;">{value}</div>'
        f'<div style="margin-top:7px;font-size:0.66rem;'
        f'text-transform:uppercase;letter-spacing:0.12em;'
        f'color:{c("text_muted")};">{label}</div>'
        f'{sub_html}'
        f'</div>'
    )


def _card(body: str, border_color: str = None) -> str:
    bdr = (f"border-left:4px solid {border_color};"
           if border_color else "")
    return (
        f'<div style="background:linear-gradient('
        f'180deg,rgba(255,255,255,0.02),'
        f'rgba(255,255,255,0.00)),rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-radius:18px;padding:18px;'
        f'box-shadow:0 16px 30px rgba(0,0,0,0.18);'
        f'{bdr}">'
        f'{body}'
        f'</div>'
    )


def _alert(text: str, color: str, icon: str = "ℹ️") -> str:
    return (
        f'<div style="background:rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-left:4px solid {color};'
        f'border-radius:14px;padding:12px 16px;'
        f'margin-bottom:8px;'
        f'display:flex;align-items:center;gap:10px;">'
        f'<span style="font-size:1rem;">{icon}</span>'
        f'<span style="font-size:0.82rem;font-weight:600;'
        f'color:{c("text_primary")};">{text}</span>'
        f'</div>'
    )


def _info_box(text: str, accent: str = None) -> str:
    accent = accent or c("blue")
    return (
        f'<div style="background:rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-left:4px solid {accent};'
        f'border-radius:14px;padding:14px 16px;'
        f'margin-bottom:12px;">'
        f'<div style="font-size:0.82rem;'
        f'color:{c("text_secondary")};line-height:1.6;">'
        f'{text}'
        f'</div>'
        f'</div>'
    )


def _state_pill(state: str) -> str:
    s = str(state).upper()
    cfg = {
        "STARTED":   (c("green"),      "▶ STARTED"),
        "SUSPENDED": (c("yellow"),     "⏸ SUSPENDED"),
        "FAILED":    (c("red"),        "❌ FAILED"),
        "SUCCEEDED": (c("green"),      "✅ SUCCEEDED"),
        "RUNNING":   (c("blue"),       "⚡ RUNNING"),
        "SCHEDULED": (c("cyan"),       "🕒 SCHEDULED"),
        "CANCELLED": (c("text_muted"), "⊘ CANCELLED"),
        "SKIPPED":   (c("text_muted"), "⊘ SKIPPED"),
    }
    color, label = cfg.get(s, (c("text_muted"), s))
    return (
        f'<span style="display:inline-flex;align-items:center;'
        f'gap:5px;padding:4px 12px;border-radius:999px;'
        f'font-size:0.65rem;font-weight:700;'
        f'color:{color};background:{color}15;'
        f'border:1px solid {color}33;">'
        f'{label}'
        f'</span>'
    )


def _task_card(name, state, schedule, wh, db,
               schema, owner, pred, comment,
               env_color) -> str:
    state_color_map = {
        "STARTED":   c("green"),
        "SUSPENDED": c("yellow"),
        "FAILED":    c("red"),
    }
    state_color = state_color_map.get(
        str(state).upper(), c("text_muted")
    )

    pred_html = ""
    if pred and str(pred) not in ("", "nan", "None"):
        pred_html = (
            f'<div style="font-size:0.66rem;'
            f'color:{c("text_muted")};margin-top:6px;">'
            f'🔗 Predecessor: '
            f'<b style="color:{c("text_secondary")};">'
            f'{str(pred)[:60]}</b>'
            f'</div>'
        )

    cmt_html = ""
    if comment and str(comment) not in ("", "nan", "None"):
        cmt_html = (
            f'<div style="font-size:0.65rem;'
            f'color:{c("text_muted")};margin-top:4px;'
            f'overflow:hidden;text-overflow:ellipsis;'
            f'white-space:nowrap;">{comment}</div>'
        )

    return (
        f'<div style="background:linear-gradient('
        f'180deg,rgba(255,255,255,0.02),'
        f'rgba(255,255,255,0.00)),rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-left:4px solid {env_color};'
        f'border-radius:18px;padding:16px;'
        f'box-shadow:0 14px 28px rgba(0,0,0,0.16);'
        f'margin-bottom:10px;">'
        # title row
        f'<div style="display:flex;align-items:center;'
        f'justify-content:space-between;margin-bottom:8px;">'
        f'<span style="font-weight:700;font-size:0.88rem;'
        f'color:{c("text_primary")};">⏰ {name}</span>'
        f'<span style="display:inline-flex;align-items:center;'
        f'gap:5px;padding:4px 12px;border-radius:999px;'
        f'font-size:0.65rem;font-weight:700;'
        f'color:{state_color};background:{state_color}15;'
        f'border:1px solid {state_color}33;">'
        f'{str(state).upper()}</span>'
        f'</div>'
        # info grid
        f'<div style="display:grid;'
        f'grid-template-columns:1fr 1fr;gap:4px;">'
        f'<div style="font-size:0.68rem;color:{c("text_muted")};">'
        f'🕒 Schedule: <b style="color:{c("text_secondary")};">'
        f'{schedule}</b></div>'
        f'<div style="font-size:0.68rem;color:{c("text_muted")};">'
        f'⚙️ Warehouse: <b style="color:{c("text_secondary")};">'
        f'{wh}</b></div>'
        f'<div style="font-size:0.68rem;color:{c("text_muted")};">'
        f'🗄️ Database: <b style="color:{c("text_secondary")};">'
        f'{db}</b></div>'
        f'<div style="font-size:0.68rem;color:{c("text_muted")};">'
        f'📁 Schema: <b style="color:{c("text_secondary")};">'
        f'{schema}</b></div>'
        f'<div style="font-size:0.68rem;color:{c("text_muted")};">'
        f'👤 Owner: <b style="color:{c("text_secondary")};">'
        f'{owner}</b></div>'
        f'</div>'
        f'{pred_html}'
        f'{cmt_html}'
        f'</div>'
    )


def _run_card(name, state, scheduled, completed,
              return_val, duration_sec) -> str:
    state_color_map = {
        "SUCCEEDED": c("green"),
        "FAILED":    c("red"),
        "RUNNING":   c("blue"),
        "CANCELLED": c("text_muted"),
        "SKIPPED":   c("text_muted"),
    }
    state_color = state_color_map.get(
        str(state).upper(), c("text_muted")
    )

    dur_html = ""
    if duration_sec and safe_float(duration_sec) > 0:
        dur_html = (
            f'<span style="font-size:0.65rem;'
            f'color:{c("text_muted")};">'
            f'⏱ {fmt_dur(duration_sec)}</span>'
        )

    return (
        f'<div style="background:rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-left:4px solid {state_color};'
        f'border-radius:14px;padding:12px 14px;'
        f'margin-bottom:6px;">'
        f'<div style="display:flex;align-items:center;'
        f'justify-content:space-between;margin-bottom:4px;">'
        f'<span style="font-size:0.8rem;font-weight:700;'
        f'color:{c("text_primary")};">{name}</span>'
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'{dur_html}'
        f'<span style="font-size:0.65rem;font-weight:700;'
        f'color:{state_color};background:{state_color}15;'
        f'border:1px solid {state_color}33;'
        f'padding:2px 8px;border-radius:999px;">'
        f'{str(state).upper()}</span>'
        f'</div>'
        f'</div>'
        f'<div style="display:flex;gap:14px;">'
        f'<span style="font-size:0.65rem;'
        f'color:{c("text_muted")};">'
        f'Scheduled: {str(scheduled)[:16]}</span>'
        f'<span style="font-size:0.65rem;'
        f'color:{c("text_muted")};">'
        f'Completed: {str(completed)[:16]}</span>'
        f'</div>'
        f'</div>'
    )


def _sql_block(sql: str) -> str:
    return (
        f'<div style="background:{c("bg_secondary")};'
        f'border:1px solid {c("border")};'
        f'border-left:3px solid {c("pwc_orange")};'
        f'border-radius:0 8px 8px 0;'
        f'padding:14px 16px;'
        f'font-family:JetBrains Mono,monospace;'
        f'font-size:0.75rem;'
        f'color:{c("text_secondary")};'
        f'line-height:1.7;white-space:pre-wrap;'
        f'word-break:break-all;margin:10px 0;">'
        f'{sql}'
        f'</div>'
    )


def _step(num: int, title: str) -> str:
    return (
        f'<div style="display:flex;align-items:center;'
        f'gap:10px;margin-bottom:14px;margin-top:8px;">'
        f'<div style="width:26px;height:26px;'
        f'border-radius:50%;'
        f'background:linear-gradient(135deg,'
        f'{c("pwc_orange")},{c("pwc_orange_dark","#9F3600")});'
        f'color:white;font-size:0.72rem;font-weight:700;'
        f'display:flex;align-items:center;'
        f'justify-content:center;flex-shrink:0;">'
        f'{num}</div>'
        f'<div style="font-weight:700;'
        f'color:{c("text_primary")};'
        f'font-size:0.9rem;">{title}</div>'
        f'</div>'
    )
def _env_stat(label, value, color):
    return (
        f'<div>'
        f'<div style="font-family:JetBrains Mono,monospace;'
        f'font-size:1.2rem;font-weight:700;color:{color};">'
        f'{value}</div>'
        f'<div style="font-size:0.6rem;color:{c("text_muted")};'
        f'text-transform:uppercase;">{label}</div>'
        f'</div>'
    )


# ─── Data fetchers ────────────────────────────────────────────────────────────

@st.cache_data(ttl=30, show_spinner=False)
def fetch_tasks(_mid, account, db=None, schema=None):
    try:
        if db and schema:
            sql = f'SHOW TASKS IN SCHEMA "{db}"."{schema}"'
        elif db:
            sql = f'SHOW TASKS IN DATABASE "{db}"'
        else:
            sql = "SHOW TASKS IN ACCOUNT"
        df = run_query(account, sql)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=30, show_spinner=False)
def fetch_task_history(_mid, account, days=7):
    try:
        df = run_query(account, f"""
            SELECT
                NAME,
                STATE,
                SCHEDULED_TIME,
                COMPLETED_TIME,
                RETURN_VALUE,
                DATEDIFF('second',
                    SCHEDULED_TIME,
                    COMPLETED_TIME) AS DURATION_SEC
            FROM SNOWFLAKE.ACCOUNT_USAGE.TASK_HISTORY
            WHERE SCHEDULED_TIME >= DATEADD('day',
                {-days}, CURRENT_TIMESTAMP())
            ORDER BY SCHEDULED_TIME DESC
            LIMIT 2000
        """)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def fetch_databases(_mid, account):
    try:
        df = run_query(account, "SHOW DATABASES")
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def fetch_schemas(_mid, account, db):
    try:
        df = run_query(account, f'SHOW SCHEMAS IN DATABASE "{db}"')
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def fetch_warehouses(_mid, account):
    try:
        df = run_query(account, "SHOW WAREHOUSES")
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


# ─── Manager + Sidebar ────────────────────────────────────────────────────────

manager   = SnowflakeConnectionManager()
connected = manager.get_connected_accounts()

with st.sidebar:
    st.markdown(f"""
    <div style="padding:20px 16px 12px;
         border-bottom:1px solid {c("border")};
         margin-bottom:12px;">
        <div style="font-size:1rem;font-weight:800;
             color:{c("text_primary")};">⏰ Task Manager</div>
        <div style="font-size:0.56rem;
             color:{c("pwc_orange")};
             font-weight:800;text-transform:uppercase;
             letter-spacing:0.18em;">PwC Data &amp; AI</div>
    </div>
    """, unsafe_allow_html=True)

    for acc in connected:
        color_acc = get_env_color(acc)
        st.markdown(
            f'<div style="display:flex;align-items:center;'
            f'gap:8px;padding:8px 10px;border-radius:10px;'
            f'margin-bottom:4px;">'
            f'<div style="width:8px;height:8px;border-radius:50%;'
            f'background:{color_acc};'
            f'box-shadow:0 0 6px {color_acc};'
            f'flex-shrink:0;"></div>'
            f'<span style="font-size:0.82rem;font-weight:600;'
            f'color:{color_acc};">{acc}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    if not connected:
        st.warning("No accounts connected.")

    st.markdown("---")

    if st.button("🔄 Refresh Data", use_container_width=True,
                  key="task_refresh"):
        st.cache_data.clear()
        st.rerun()

# ─── Header ───────────────────────────────────────────────────────────────────

pwc_header(
    "Task Manager",
    subtitle="Create, monitor and manage Snowflake tasks "
             "and DAGs across all environments"
)

if not connected:
    st.markdown(
        _alert("Connect at least one account to manage tasks.",
               c("pwc_orange"), "🔌"),
        unsafe_allow_html=True
    )
    st.stop()

# ─── Tabs ─────────────────────────────────────────────────────────────────────

(tab_overview, tab_tasks, tab_history,
 tab_create, tab_manage, tab_dag) = st.tabs([
    "📊  Overview",
    "⏰  Tasks",
    "📋  Run History",
    "➕  Create Task",
    "🔧  Manage",
    "🔗  DAG View",
])

# ═══════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════

with tab_overview:
    section_header("TASK ESTATE OVERVIEW")

    ov_days = st.select_slider(
        "History window",
        options=[1, 3, 7, 14, 30],
        value=7, key="task_ov_days"
    )

    all_tasks  = []
    all_hist   = []

    for acc in connected:
        tdf = fetch_tasks(id(manager), acc)
        if not tdf.empty:
            all_tasks.append(tdf)
        hdf = fetch_task_history(id(manager), acc, ov_days)
        if not hdf.empty:
            all_hist.append(hdf)

    total_tasks  = sum(len(d) for d in all_tasks)
    total_runs   = sum(len(d) for d in all_hist)

    started_count  = 0
    suspended_count= 0
    success_count  = 0
    failed_count   = 0

    if all_tasks:
        cat = pd.concat(all_tasks, ignore_index=True)
        sc  = next((col for col in ["state","STATE"]
                     if col in cat.columns), None)
        if sc:
            started_count   = safe_int(
                (cat[sc].str.upper() == "STARTED").sum())
            suspended_count = safe_int(
                (cat[sc].str.upper() == "SUSPENDED").sum())

    if all_hist:
        cah = pd.concat(all_hist, ignore_index=True)
        stc = next((col for col in ["STATE","state"]
                     if col in cah.columns), None)
        if stc:
            success_count = safe_int(
                (cah[stc].str.upper() == "SUCCEEDED").sum())
            failed_count  = safe_int(
                (cah[stc].str.upper() == "FAILED").sum())

    fail_rate = (failed_count / total_runs * 100
                 if total_runs else 0.0)

    # KPI row
    k1,k2,k3,k4,k5,k6 = st.columns(6)
    kpis = [
        ("⏰", str(total_tasks),      "Total Tasks",    c("pwc_orange"), ""),
        ("▶️", str(started_count),   "Active",         c("green"),      ""),
        ("⏸️", str(suspended_count), "Suspended",      c("yellow"),     ""),
        ("📋", str(total_runs),      f"Runs ({ov_days}d)", c("blue"),   ""),
        ("✅", str(success_count),   "Succeeded",      c("green"),      ""),
        ("❌", f"{fail_rate:.1f}%",  "Fail Rate",
         c("red") if fail_rate > 10 else c("green"),    ""),
    ]
    for col, (ico, val, lbl, clr, sub) in zip(
            [k1,k2,k3,k4,k5,k6], kpis):
        with col:
            st.markdown(_kpi(ico, val, lbl, clr, sub),
                         unsafe_allow_html=True)

    st.markdown('<div style="height:16px;"></div>',
                 unsafe_allow_html=True)

    # Per-environment breakdown
    section_header("PER-ENVIRONMENT BREAKDOWN")

    for acc in connected:
        env_color = get_env_color(acc)
        tdf2 = fetch_tasks(id(manager), acc)
        hdf2 = fetch_task_history(id(manager), acc, ov_days)

        n_tasks = len(tdf2)
        n_start = 0
        n_susp  = 0
        n_succ  = 0
        n_fail  = 0
        n_runs  = len(hdf2)

        if not tdf2.empty:
            sc2 = next((col for col in ["state","STATE"]
                         if col in tdf2.columns), None)
            if sc2:
                n_start = safe_int(
                    (tdf2[sc2].str.upper() == "STARTED").sum())
                n_susp  = safe_int(
                    (tdf2[sc2].str.upper() == "SUSPENDED").sum())

        if not hdf2.empty:
            stc2 = next((col for col in ["STATE","state"]
                          if col in hdf2.columns), None)
            if stc2:
                n_succ = safe_int(
                    (hdf2[stc2].str.upper() == "SUCCEEDED").sum())
                n_fail = safe_int(
                    (hdf2[stc2].str.upper() == "FAILED").sum())

        efr = n_fail / n_runs * 100 if n_runs else 0

        body = (
            f'<div style="display:flex;align-items:center;'
            f'justify-content:space-between;margin-bottom:12px;">'
            f'<span style="font-size:0.9rem;font-weight:800;'
            f'color:{env_color};">{acc}</span>'
            f'<span style="font-size:0.7rem;'
            f'color:{c("text_muted")};">'
            f'{ov_days}-day window</span>'
            f'</div>'
            f'<div style="display:grid;'
            f'grid-template-columns:repeat(6,1fr);'
            f'gap:8px;text-align:center;">'
            + _env_stat("Tasks",      str(n_tasks), env_color)
            + _env_stat("Active",     str(n_start), c("green"))
            + _env_stat("Suspended",  str(n_susp),  c("yellow"))
            + _env_stat("Runs",       str(n_runs),  c("blue"))
            + _env_stat("Succeeded",  str(n_succ),  c("green"))
            + _env_stat("Fail Rate",  f"{efr:.1f}%",
                         c("red") if efr > 10 else c("green"))
            + f'</div>'
        )
        st.markdown(_card(body, border_color=env_color),
                     unsafe_allow_html=True)

    # Charts
    if all_hist:
        st.markdown('<div style="height:8px;"></div>',
                     unsafe_allow_html=True)
        section_header("EXECUTION TRENDS")

        cah2 = pd.concat(all_hist, ignore_index=True)

        stc3 = next((col for col in ["STATE","state"]
                      if col in cah2.columns), None)
        dtc  = next((col for col in
                      ["SCHEDULED_TIME","scheduled_time"]
                      if col in cah2.columns), None)
        ntc  = next((col for col in ["NAME","name"]
                      if col in cah2.columns), None)

        if stc3 and dtc:
            cah2["DATE"] = pd.to_datetime(
                cah2[dtc], errors="coerce").dt.date
            daily_states = cah2.groupby(
                ["DATE", stc3]
            ).size().reset_index(name="Count")

            fig1 = px.bar(
                daily_states,
                x="DATE", y="Count",
                color=stc3,
                height=320,
                title="Daily Task Runs by State",
                color_discrete_map={
                    "SUCCEEDED": c("green"),
                    "FAILED":    c("red"),
                    "CANCELLED": c("text_muted"),
                    "SKIPPED":   c("text_muted"),
                    "RUNNING":   c("blue"),
                }
            )
            fig1.update_layout(
                xaxis_title="",
                yaxis_title="Runs",
                legend_title_text=""
            )
            st.plotly_chart(fig1, use_container_width=True,
                             key="task_daily_states")

        if ntc and stc3:
            top_fail = (
                cah2[cah2[stc3].str.upper() == "FAILED"]
                .groupby(ntc).size()
                .reset_index(name="Failures")
                .nlargest(10, "Failures")
            )
            if not top_fail.empty:
                ch1, ch2 = st.columns(2)
                with ch1:
                    fig2 = px.bar(
                        top_fail,
                        x="Failures", y=ntc,
                        orientation="h",
                        height=340,
                        title="Top 10 Most Failed Tasks",
                        color="Failures",
                        color_continuous_scale=[
                            c("bg_elevated"), c("red")
                        ]
                    )
                    fig2.update_layout(
                        yaxis_title="",
                        xaxis_title="Failures",
                        coloraxis_showscale=False
                    )
                    st.plotly_chart(fig2, use_container_width=True,
                                     key="task_top_fail")

                with ch2:
                    state_counts = cah2[stc3].value_counts()
                    fig3 = go.Figure(go.Pie(
                        labels=state_counts.index,
                        values=state_counts.values,
                        hole=0.55,
                        marker_colors=[
                            c("green"), c("red"),
                            c("text_muted"), c("blue")
                        ][:len(state_counts)],
                        textinfo="label+percent"
                    ))
                    fig3.update_layout(
                        title="Run State Distribution",
                        height=340,
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(color=c("text_secondary"))
                    )
                    st.plotly_chart(fig3, use_container_width=True,
                                     key="task_state_pie")


def _env_stat(label, value, color):
    return (
        f'<div>'
        f'<div style="font-family:JetBrains Mono,monospace;'
        f'font-size:1.2rem;font-weight:700;color:{color};">'
        f'{value}</div>'
        f'<div style="font-size:0.6rem;color:{c("text_muted")};'
        f'text-transform:uppercase;">{label}</div>'
        f'</div>'
    )


# ═══════════════════════════════════════════════════════
# TAB 2 — TASKS
# ═══════════════════════════════════════════════════════

with tab_tasks:
    section_header("TASK BROWSER")

    tf1, tf2, tf3, tf4 = st.columns(4)
    with tf1:
        task_acc = st.selectbox("Environment",
                                 connected,
                                 key="task_acc")
    with tf2:
        db_df  = fetch_databases(id(manager), task_acc)
        db_nc  = next((c_ for c_ in ["name","NAME"]
                        if c_ in db_df.columns), None)
        db_list= (["(All)"] + db_df[db_nc].tolist()
                   if db_nc and not db_df.empty else ["(All)"])
        task_db= st.selectbox("Database", db_list, key="task_db")
    with tf3:
        sch_list = ["(All)"]
        if task_db != "(All)":
            sch_df = fetch_schemas(id(manager), task_acc, task_db)
            sch_nc = next((c_ for c_ in ["name","NAME"]
                            if c_ in sch_df.columns), None)
            if sch_nc and not sch_df.empty:
                sch_list = ["(All)"] + sch_df[sch_nc].tolist()
        task_sch = st.selectbox("Schema", sch_list, key="task_sch")
    with tf4:
        task_state_f = st.selectbox(
            "State",
            ["All","Started","Suspended","Failed"],
            key="task_state_f"
        )

    db_arg  = None if task_db  == "(All)" else task_db
    sch_arg = None if task_sch == "(All)" else task_sch

    tdf = fetch_tasks(id(manager), task_acc, db_arg, sch_arg)
    env_color_t = get_env_color(task_acc)

    task_search = st.text_input("🔍 Search tasks",
                                  placeholder="Filter by name…",
                                  key="task_search")

    if tdf.empty:
        st.markdown(
            _alert("No tasks found in the selected scope.",
                   c("text_muted"), "ℹ️"),
            unsafe_allow_html=True
        )
    else:
        nc_  = next((col for col in ["name","NAME"]
                      if col in tdf.columns), None)
        sc_  = next((col for col in ["state","STATE"]
                      if col in tdf.columns), None)
        sch_ = next((col for col in ["schedule","SCHEDULE"]
                      if col in tdf.columns), None)
        wh_  = next((col for col in [
            "warehouse","WAREHOUSE"]
            if col in tdf.columns), None)
        db_  = next((col for col in [
            "database_name","DATABASE_NAME"]
            if col in tdf.columns), None)
        sc2_ = next((col for col in [
            "schema_name","SCHEMA_NAME"]
            if col in tdf.columns), None)
        ow_  = next((col for col in ["owner","OWNER"]
                      if col in tdf.columns), None)
        pr_  = next((col for col in [
            "predecessors","PREDECESSORS"]
            if col in tdf.columns), None)
        cm_  = next((col for col in ["comment","COMMENT"]
                      if col in tdf.columns), None)

        filt = tdf.copy()
        if task_state_f != "All" and sc_:
            filt = filt[
                filt[sc_].str.upper() ==
                task_state_f.upper()
            ]
        if task_search and nc_:
            filt = filt[
                filt[nc_].str.contains(
                    task_search, case=False, na=False)
            ]

        st.markdown(
            f'<div style="font-size:0.72rem;'
            f'color:{c("text_muted")};margin-bottom:10px;">'
            f'{len(filt)} task(s) shown</div>',
            unsafe_allow_html=True
        )

        rows = list(filt.iterrows())
        for idx in range(0, len(rows), 2):
            pair = st.columns(2)
            for ci, (_, task) in enumerate(rows[idx:idx+2]):
                t_name  = task.get(nc_,  "?") if nc_  else "?"
                t_state = task.get(sc_,  "?") if sc_  else "?"
                t_sch   = task.get(sch_, "—") if sch_ else "—"
                t_wh    = task.get(wh_,  "—") if wh_  else "—"
                t_db    = task.get(db_,  "—") if db_  else "—"
                t_sc2   = task.get(sc2_, "—") if sc2_ else "—"
                t_ow    = task.get(ow_,  "—") if ow_  else "—"
                t_pr    = task.get(pr_,  "")  if pr_  else ""
                t_cm    = task.get(cm_,  "")  if cm_  else ""

                with pair[ci]:
                    st.markdown(
                        _task_card(
                            t_name, t_state, t_sch,
                            t_wh, t_db, t_sc2,
                            t_ow, t_pr, t_cm,
                            env_color_t
                        ),
                        unsafe_allow_html=True
                    )

        with st.expander("📋 Full Task Table"):
            st.dataframe(tdf, use_container_width=True,
                          hide_index=True, height=400)
            st.download_button(
                "📥 Download CSV",
                data=tdf.to_csv(index=False),
                file_name=(
                    f"tasks_{task_acc}_"
                    f"{datetime.date.today()}.csv"
                ),
                mime="text/csv",
                key="task_dl"
            )


# ═══════════════════════════════════════════════════════
# TAB 3 — RUN HISTORY
# ═══════════════════════════════════════════════════════

with tab_history:
    section_header("TASK RUN HISTORY")

    h1, h2, h3 = st.columns(3)
    with h1:
        hist_acc  = st.selectbox("Environment",
                                   connected,
                                   key="hist_acc")
    with h2:
        hist_days = st.selectbox(
            "Time Range",
            [1, 3, 7, 14, 30], index=2,
            format_func=lambda x: f"Last {x} days",
            key="hist_days"
        )
    with h3:
        hist_state = st.selectbox(
            "State Filter",
            ["All","SUCCEEDED","FAILED",
             "CANCELLED","RUNNING","SKIPPED"],
            key="hist_state"
        )

    hdf = fetch_task_history(id(manager), hist_acc, hist_days)

    if hdf.empty:
        st.markdown(
            _alert("No task history found.",
                   c("text_muted"), "ℹ️"),
            unsafe_allow_html=True
        )
    else:
        stc_ = next((col for col in ["STATE","state"]
                      if col in hdf.columns), None)
        if hist_state != "All" and stc_:
            hdf = hdf[hdf[stc_].str.upper() == hist_state]

        hist_search = st.text_input(
            "🔍 Filter by task name",
            key="hist_search",
            placeholder="Task name…"
        )
        ntc_ = next((col for col in ["NAME","name"]
                      if col in hdf.columns), None)
        if hist_search and ntc_:
            hdf = hdf[hdf[ntc_].str.contains(
                hist_search, case=False, na=False)]

        st.markdown(
            f'<div style="font-size:0.72rem;'
            f'color:{c("text_muted")};margin-bottom:10px;">'
            f'{len(hdf)} run(s) shown</div>',
            unsafe_allow_html=True
        )

        dtc_ = next((col for col in [
            "SCHEDULED_TIME","scheduled_time"]
            if col in hdf.columns), None)
        ctc_ = next((col for col in [
            "COMPLETED_TIME","completed_time"]
            if col in hdf.columns), None)
        etc_ = next((col for col in [
            "RETURN_VALUE","return_value"]
            if col in hdf.columns), None)
        dur_ = next((col for col in [
            "DURATION_SEC","duration_sec"]
            if col in hdf.columns), None)

        for _, run in hdf.head(100).iterrows():
            r_name = run.get(ntc_, "?") if ntc_ else "?"
            r_st   = run.get(stc_, "?") if stc_ else "?"
            r_sch  = run.get(dtc_, "—") if dtc_ else "—"
            r_cmp  = run.get(ctc_, "—") if ctc_ else "—"
            r_ret  = run.get(etc_, "")  if etc_ else ""
            r_dur  = run.get(dur_, 0)   if dur_ else 0

            st.markdown(
                _run_card(r_name, r_st, r_sch, r_cmp,
                           r_ret, r_dur),
                unsafe_allow_html=True
            )

        if len(hdf) > 100:
            st.markdown(
                _alert(
                    f"Showing 100 of {len(hdf)} runs. "
                    f"Download CSV for full history.",
                    c("text_muted"), "ℹ️"
                ),
                unsafe_allow_html=True
            )

        with st.expander("📋 Full History Table"):
            st.dataframe(hdf, use_container_width=True,
                          hide_index=True, height=400)
            st.download_button(
                "📥 Download CSV",
                data=hdf.to_csv(index=False),
                file_name=(
                    f"task_history_{hist_acc}_"
                    f"{datetime.date.today()}.csv"
                ),
                mime="text/csv",
                key="hist_dl"
            )


# ═══════════════════════════════════════════════════════
# TAB 4 — CREATE TASK
# ═══════════════════════════════════════════════════════

with tab_create:
    section_header("CREATE NEW TASK")

    st.markdown(
        _info_box(
            "Create a Snowflake task with a defined schedule or "
            "as part of a DAG (predecessor-based). Tasks execute "
            "SQL statements or stored procedure calls on a schedule.",
            accent=c("pwc_orange")
        ),
        unsafe_allow_html=True
    )

    st.markdown(_step(1, "Identity"), unsafe_allow_html=True)
    ci1, ci2, ci3 = st.columns(3)
    with ci1:
        ct_acc    = st.selectbox("Account", connected, key="ct_acc")
        ct_name   = st.text_input("Task Name *",
                                   placeholder="MY_DAILY_TASK",
                                   key="ct_name")
    with ci2:
        ct_db_df  = fetch_databases(id(manager), ct_acc)
        ct_db_nc  = next((c_ for c_ in ["name","NAME"]
                           if c_ in ct_db_df.columns), None)
        ct_db_lst = (ct_db_df[ct_db_nc].tolist()
                      if ct_db_nc and not ct_db_df.empty
                      else [])
        ct_db = st.selectbox("Database *",
                               ct_db_lst if ct_db_lst else ["—"],
                               key="ct_db")
    with ci3:
        ct_sch_df  = (fetch_schemas(id(manager), ct_acc, ct_db)
                       if ct_db and ct_db != "—"
                       else pd.DataFrame())
        ct_sch_nc  = next((c_ for c_ in ["name","NAME"]
                            if c_ in ct_sch_df.columns), None)
        ct_sch_lst = (ct_sch_df[ct_sch_nc].tolist()
                       if ct_sch_nc and not ct_sch_df.empty
                       else [])
        ct_schema  = st.selectbox(
            "Schema *",
            ct_sch_lst if ct_sch_lst else ["—"],
            key="ct_schema"
        )

    st.markdown(_step(2, "Warehouse"), unsafe_allow_html=True)
    wh_df  = fetch_warehouses(id(manager), ct_acc)
    wh_nc_ = next((c_ for c_ in ["name","NAME"]
                    if c_ in wh_df.columns), None)
    wh_lst = (wh_df[wh_nc_].tolist()
               if wh_nc_ and not wh_df.empty else [])
    ct_wh  = st.selectbox("Warehouse *",
                            wh_lst if wh_lst else ["—"],
                            key="ct_wh")

    st.markdown(_step(3, "Schedule"), unsafe_allow_html=True)
    sc1, sc2 = st.columns(2)
    with sc1:
        ct_sched_type = st.radio(
            "Schedule Type",
            ["CRON", "Minutes Interval", "Predecessor"],
            horizontal=True, key="ct_sched_type"
        )
    with sc2:
        if ct_sched_type == "CRON":
            ct_cron = st.text_input(
                "CRON Expression",
                value="0 2 * * *",
                placeholder="0 2 * * *",
                help="minute hour day month weekday",
                key="ct_cron"
            )
            ct_tz = st.text_input(
                "Timezone", value="UTC", key="ct_tz"
            )
            ct_schedule_val = f"USING CRON {ct_cron} {ct_tz}"
        elif ct_sched_type == "Minutes Interval":
            ct_mins = st.number_input(
                "Every N Minutes",
                min_value=1, value=60,
                key="ct_mins"
            )
            ct_schedule_val = f"{ct_mins} MINUTE"
        else:
            ct_pred = st.text_input(
                "Predecessor Task(s)",
                placeholder="PARENT_TASK",
                key="ct_pred"
            )
            ct_schedule_val = None

    st.markdown(_step(4, "SQL Statement"), unsafe_allow_html=True)
    ct_sql = st.text_area(
        "SQL to Execute *",
        placeholder=(
            "SELECT COUNT(*) FROM MY_TABLE;\n"
            "-- or CALL my_procedure();"
        ),
        height=120, key="ct_sql"
    )

    st.markdown(_step(5, "Options"), unsafe_allow_html=True)
    op1, op2, op3 = st.columns(3)
    with op1:
        ct_overlap = st.checkbox("Allow Overlapping Execution",
                                  value=False, key="ct_overlap")
    with op2:
        ct_timeout = st.number_input("Timeout (ms, 0=none)",
                                      min_value=0, value=0,
                                      key="ct_timeout")
    with op3:
        ct_comment = st.text_input("Comment",
                                    placeholder="Purpose…",
                                    key="ct_comment")
        ct_init_susp = st.checkbox("Initially Suspended",
                                    value=True,
                                    key="ct_init_susp")

    # Build SQL preview
    if (ct_name and ct_db and ct_schema
            and ct_db != "—" and ct_schema != "—"
            and ct_wh and ct_sql):

        sched_part = ""
        if ct_sched_type == "Predecessor":
            if ct_pred:
                sched_part = (
                    f"\n    AFTER "
                    f'"{ct_db}"."{ct_schema}"."{ct_pred}"'
                )
        else:
            sched_part = f"\n    SCHEDULE = '{ct_schedule_val}'"

        opts = []
        if ct_overlap:
            opts.append("    ALLOW_OVERLAPPING_EXECUTION = TRUE")
        if ct_timeout > 0:
            opts.append(f"    USER_TASK_TIMEOUT_MS = {ct_timeout}")
        if ct_comment:
            opts.append(f"    COMMENT = '{ct_comment}'")
        if ct_init_susp:
            opts.append("    INITIALLY_SUSPENDED = TRUE")

        create_sql = (
            f'CREATE TASK IF NOT EXISTS '
            f'"{ct_db}"."{ct_schema}"."{ct_name}"\n'
            f'    WAREHOUSE = "{ct_wh}"'
            f'{sched_part}'
        )
        if opts:
            create_sql += "\n" + "\n".join(opts)
        create_sql += f"\nAS\n{ct_sql};"

        section_header("GENERATED SQL")
        st.markdown(_sql_block(create_sql),
                     unsafe_allow_html=True)

        cb1, cb2 = st.columns(2)
        with cb1:
            if st.button("▶️ Create Task",
                          type="primary", key="btn_create_task"):
                with st.status(f"Creating {ct_name}…",
                               expanded=True) as s:
                    st.write("Validating config…")
                    time.sleep(0.3)
                    ok, result = run_statement(ct_acc, create_sql)
                    s.update(
                        label=(f"✅ {ct_name} created!"
                               if ok else "❌ Failed"),
                        state="complete" if ok else "error",
                        expanded=False
                    )
                if ok:
                    st.success(f"✅ Task **{ct_name}** created!")
                    st.cache_data.clear()
                    st.balloons()
                else:
                    st.error(f"❌ {result}")
        with cb2:
            if st.button("📋 Copy SQL", key="btn_copy_task"):
                st.code(create_sql, language="sql")


# ═══════════════════════════════════════════════════════
# TAB 5 — MANAGE
# ═══════════════════════════════════════════════════════

with tab_manage:
    section_header("MANAGE TASKS")

    mg1, mg2 = st.columns(2)
    with mg1:
        mg_acc = st.selectbox("Environment",
                               connected, key="mg_task_acc")
    with mg2:
        mg_db_df = fetch_databases(id(manager), mg_acc)
        mg_db_nc = next((c_ for c_ in ["name","NAME"]
                          if c_ in mg_db_df.columns), None)
        mg_db_lst= (["(All)"] + mg_db_df[mg_db_nc].tolist()
                     if mg_db_nc and not mg_db_df.empty
                     else ["(All)"])
        mg_db    = st.selectbox("Database", mg_db_lst,
                                  key="mg_task_db")

    mg_db_arg = None if mg_db == "(All)" else mg_db
    mg_tdf    = fetch_tasks(id(manager), mg_acc, mg_db_arg)

    if mg_tdf.empty:
        st.markdown(
            _alert("No tasks found.", c("text_muted"), "ℹ️"),
            unsafe_allow_html=True
        )
    else:
        mg_nc = next((col for col in ["name","NAME"]
                       if col in mg_tdf.columns), None)
        mg_sc = next((col for col in ["state","STATE"]
                       if col in mg_tdf.columns), None)
        mg_dbc= next((col for col in [
            "database_name","DATABASE_NAME"]
            if col in mg_tdf.columns), None)
        mg_scc= next((col for col in [
            "schema_name","SCHEMA_NAME"]
            if col in mg_tdf.columns), None)

        for _, task in mg_tdf.iterrows():
            t_name  = task.get(mg_nc, "?") if mg_nc else "?"
            t_state = task.get(mg_sc, "?") if mg_sc else "?"
            t_db2   = task.get(mg_dbc,"?") if mg_dbc else "?"
            t_sc3   = task.get(mg_scc,"?") if mg_scc else "?"
            is_run  = str(t_state).upper() == "STARTED"

            full_name = (
                f'"{t_db2}"."{t_sc3}"."{t_name}"'
                if t_db2 != "?" and t_sc3 != "?"
                else f'"{t_name}"'
            )

            with st.expander(
                f"⏰ {t_name}  ·  "
                f"{'▶ STARTED' if is_run else '⏸ SUSPENDED'}"
            ):
                mc1, mc2 = st.columns([3, 1])

                with mc1:
                    st.markdown(
                        _state_pill(t_state),
                        unsafe_allow_html=True
                    )

                with mc2:
                    if is_run:
                        if st.button(
                            "⏸️ Suspend",
                            key=f"sus_task_{mg_acc}_{t_name}",
                            use_container_width=True
                        ):
                            ok, msg = run_statement(
                                mg_acc,
                                f"ALTER TASK {full_name} SUSPEND;"
                            )
                            if ok:
                                st.success("✅ Suspended")
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(f"❌ {msg}")
                    else:
                        if st.button(
                            "▶️ Resume",
                            key=f"res_task_{mg_acc}_{t_name}",
                            type="primary",
                            use_container_width=True
                        ):
                            ok, msg = run_statement(
                                mg_acc,
                                f"ALTER TASK {full_name} RESUME;"
                            )
                            if ok:
                                st.success("✅ Resumed")
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(f"❌ {msg}")

                    if st.button(
                        "▶️ Run Once",
                        key=f"run_task_{mg_acc}_{t_name}",
                        use_container_width=True
                    ):
                        ok, msg = run_statement(
                            mg_acc,
                            f"EXECUTE TASK {full_name};"
                        )
                        if ok:
                            st.success("✅ Triggered")
                        else:
                            st.error(f"❌ {msg}")

                with st.expander(f"🗑️ Drop {t_name}"):
                    st.warning(
                        f"⚠️ Permanently drops **{t_name}**.")
                    if st.checkbox("Confirm drop",
                                    key=f"cfm_task_{mg_acc}_{t_name}"):
                        if st.button(
                            "🗑️ Drop Task",
                            key=f"drop_task_{mg_acc}_{t_name}",
                            type="primary"
                        ):
                            ok, msg = run_statement(
                                mg_acc,
                                f"DROP TASK IF EXISTS {full_name};"
                            )
                            if ok:
                                st.success(f"✅ {t_name} dropped")
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(f"❌ {msg}")


# ═══════════════════════════════════════════════════════
# TAB 6 — DAG VIEW
# ═══════════════════════════════════════════════════════

with tab_dag:
    section_header("TASK DAG VISUALIZER")

    st.markdown(
        _info_box(
            "Visualize task dependencies as a Directed Acyclic Graph (DAG). "
            "Root tasks appear at the top; child tasks branch below them.",
            accent=c("blue")
        ),
        unsafe_allow_html=True
    )

    dg1, dg2 = st.columns(2)
    with dg1:
        dag_acc = st.selectbox("Environment",
                                connected, key="dag_acc")
    with dg2:
        dag_db_df  = fetch_databases(id(manager), dag_acc)
        dag_db_nc  = next((c_ for c_ in ["name", "NAME"]
                            if c_ in dag_db_df.columns), None)
        dag_db_lst = (
            ["(All)"] + dag_db_df[dag_db_nc].tolist()
            if dag_db_nc and not dag_db_df.empty
            else ["(All)"]
        )
        dag_db = st.selectbox("Database", dag_db_lst,
                               key="dag_db")

    dag_db_arg = None if dag_db == "(All)" else dag_db
    dag_tdf    = fetch_tasks(id(manager), dag_acc, dag_db_arg)

    if dag_tdf.empty:
        st.markdown(
            _alert("No tasks found.", c("text_muted"), "ℹ️"),
            unsafe_allow_html=True
        )
    else:
        dag_nc = next((col for col in ["name", "NAME"]
                        if col in dag_tdf.columns), None)
        dag_pr = next((col for col in [
            "predecessors", "PREDECESSORS"]
            if col in dag_tdf.columns), None)
        dag_sc = next((col for col in ["state", "STATE"]
                        if col in dag_tdf.columns), None)

        if dag_nc and dag_pr:
            nodes = []
            edges = []

            for _, task in dag_tdf.iterrows():
                name  = task.get(dag_nc, "?")
                state = str(task.get(dag_sc, ""))
                if state.upper() == "STARTED":
                    clr = c("green")
                elif state.upper() == "SUSPENDED":
                    clr = c("yellow")
                elif state.upper() == "FAILED":
                    clr = c("red")
                else:
                    clr = c("text_muted")

                nodes.append({"name": name, "color": clr})

                pred = task.get(dag_pr, "")
                if pred and str(pred) not in ("", "nan", "None"):
                    for p in str(pred).split(","):
                        p = p.strip()
                        if p:
                            edges.append((p, name))

            all_names = [n["name"] for n in nodes]

            if edges:
                edge_df = pd.DataFrame(
                    edges, columns=["from", "to"]
                )
            else:
                edge_df = pd.DataFrame(
                    columns=["from", "to"]
                )

            # Find root nodes
            if not edge_df.empty:
                roots = [
                    n for n in all_names
                    if n not in edge_df["to"].values
                ]
            else:
                roots = list(all_names)

            if not roots:
                roots = list(all_names)

            # Assign levels via BFS
            levels  = {}
            visited = set()

            def set_level(node, lvl):
                if node in visited:
                    return
                visited.add(node)
                levels[node] = max(levels.get(node, 0), lvl)
                if not edge_df.empty:
                    children = edge_df[
                        edge_df["from"] == node
                    ]["to"].tolist()
                    for ch in children:
                        set_level(ch, lvl + 1)

            for r in roots:
                set_level(r, 0)

            for n in all_names:
                if n not in levels:
                    levels[n] = 0

            max_level = max(levels.values()) if levels else 0

            # Group nodes by level
            level_groups = {}
            for n, lv in levels.items():
                level_groups.setdefault(lv, []).append(n)

            # Assign x/y positions
            node_x = {}
            node_y = {}
            for lv in range(max_level + 1):
                grp = level_groups.get(lv, [])
                for i, nm in enumerate(grp):
                    node_x[nm] = (i - len(grp) / 2) * 2.5
                    node_y[nm] = -lv * 1.5

            # Node color lookup
            nc_map = {n["name"]: n["color"] for n in nodes}
            node_colors_list = [
                nc_map.get(nm, c("text_muted"))
                for nm in all_names
            ]

            fig_dag = go.Figure()

            # Draw edges
            if not edge_df.empty:
                for _, row in edge_df.iterrows():
                    fx = node_x.get(row["from"])
                    fy = node_y.get(row["from"])
                    tx = node_x.get(row["to"])
                    ty = node_y.get(row["to"])
                    if all(v is not None
                           for v in [fx, fy, tx, ty]):
                        fig_dag.add_trace(go.Scatter(
                            x=[fx, tx, None],
                            y=[fy, ty, None],
                            mode="lines",
                            line=dict(
                                color=c("border_light",
                                         "#364255"),
                                width=1.5
                            ),
                            showlegend=False,
                            hoverinfo="skip"
                        ))

            # Draw nodes
            xs = [node_x.get(n, 0) for n in all_names]
            ys = [node_y.get(n, 0) for n in all_names]

            fig_dag.add_trace(go.Scatter(
                x=xs,
                y=ys,
                mode="markers+text",
                text=all_names,
                textposition="top center",
                marker=dict(
                    color=node_colors_list,
                    size=18,
                    line=dict(
                        color=c("border_light", "#364255"),
                        width=1.5
                    )
                ),
                hovertext=[
                    f"{n['name']}" for n in nodes
                ],
                hoverinfo="text",
                showlegend=False
            ))

            fig_dag.update_layout(
                height=max(400, (max_level + 2) * 120),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(
                    showgrid=False,
                    zeroline=False,
                    showticklabels=False
                ),
                yaxis=dict(
                    showgrid=False,
                    zeroline=False,
                    showticklabels=False
                ),
                margin=dict(l=20, r=20, t=30, b=20),
                font=dict(
                    color=c("text_secondary"),
                    size=11
                )
            )

            st.plotly_chart(
                fig_dag,
                use_container_width=True,
                key="task_dag"
            )

            # Legend row
            leg1, leg2, leg3, leg4 = st.columns(4)
            legend_items = [
                (leg1, "▶ Active",    c("green")),
                (leg2, "⏸ Suspended", c("yellow")),
                (leg3, "❌ Failed",   c("red")),
                (leg4, "○ Unknown",   c("text_muted")),
            ]
            for col_, lbl, clr in legend_items:
                with col_:
                    st.markdown(
                        f'<div style="display:flex;'
                        f'align-items:center;gap:8px;'
                        f'font-size:0.72rem;color:{clr};">'
                        f'<div style="width:10px;height:10px;'
                        f'border-radius:50%;'
                        f'background:{clr};"></div>'
                        f'{lbl}</div>',
                        unsafe_allow_html=True
                    )

        else:
            st.markdown(
                _alert(
                    "Task predecessor data not available. "
                    "DAG view requires PREDECESSORS column.",
                    c("text_muted"), "ℹ️"
                ),
                unsafe_allow_html=True
            )
# ─── Footer ───────────────────────────────────────────────────────────────────

st.markdown(f"""
<div style="text-align:center;padding:28px 0 10px;
     border-top:1px solid {c("border")};
     margin-top:32px;">
    <div style="font-size:0.78rem;font-weight:800;
         color:{c("text_primary")};">
        ⏰ Task Manager
        &nbsp;·&nbsp;
        <span style="color:{c("pwc_orange")};
              font-weight:800;font-size:0.68rem;
              text-transform:uppercase;
              letter-spacing:0.12em;">
            Powered By PwC Data &amp; AI
        </span>
    </div>
    <div style="margin-top:4px;font-size:0.66rem;
         color:{c("text_dim","#5f6b7c")};">
        {len(connected)} environment(s) connected
    </div>
</div>
""", unsafe_allow_html=True)