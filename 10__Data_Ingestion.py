"""
📥 Data Ingestion — Copy from external stages,
   monitor COPY history and load history across all environments.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
    page_title="Data Ingestion · PwC",
    page_icon="📥",
    layout="wide",
    initial_sidebar_state="expanded"
)
inject_css()

# ─── Safe color lookup ────────────────────────────────────────────────────────

def c(key: str, fallback: str = "#888888") -> str:
    return COLORS.get(key, fallback)

# ─── Safe HTML builders ───────────────────────────────────────────────────────
# Rule: every function returns ONE complete HTML string.
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
        f'<div style="font-size:1.1rem;margin-bottom:8px;">'
        f'{icon}</div>'
        f'<div style="font-family:JetBrains Mono,monospace;'
        f'font-size:1.55rem;font-weight:700;color:{color};'
        f'line-height:1;">{value}</div>'
        f'<div style="margin-top:7px;font-size:0.66rem;'
        f'text-transform:uppercase;letter-spacing:0.12em;'
        f'color:{c("text_muted")};">{label}</div>'
        f'{sub_html}'
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
        f'{text}</div>'
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


def _step(num: int, title: str) -> str:
    return (
        f'<div style="display:flex;align-items:center;'
        f'gap:10px;margin-bottom:14px;margin-top:12px;">'
        f'<div style="width:28px;height:28px;'
        f'border-radius:50%;'
        f'background:linear-gradient(135deg,'
        f'{c("pwc_orange")},{c("pwc_orange_dark","#9F3600")});'
        f'color:white;font-size:0.75rem;font-weight:700;'
        f'display:flex;align-items:center;'
        f'justify-content:center;flex-shrink:0;">'
        f'{num}</div>'
        f'<div style="font-weight:700;font-size:0.95rem;'
        f'color:{c("text_primary")};">{title}</div>'
        f'</div>'
    )


def _sql_block(sql: str) -> str:
    return (
        f'<div style="background:{c("bg_secondary","#0d1117")};'
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


def _stage_card(stage_name, stage_url, stage_db,
                stage_sc, s_icon, s_label,
                env_color) -> str:
    return (
        f'<div style="background:linear-gradient('
        f'180deg,rgba(255,255,255,0.02),'
        f'rgba(255,255,255,0.00)),rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-top:3px solid {env_color};'
        f'border-radius:14px;padding:16px;'
        f'margin-bottom:10px;'
        f'box-shadow:0 10px 24px rgba(0,0,0,0.16);">'
        f'<div style="display:flex;align-items:center;'
        f'justify-content:space-between;margin-bottom:10px;">'
        f'<div style="font-weight:700;'
        f'color:{c("text_primary")};font-size:0.88rem;">'
        f'{s_icon} {stage_name}</div>'
        f'<span style="font-size:0.68rem;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.5px;'
        f'color:{env_color};background:{env_color}10;'
        f'border:1px solid {env_color}33;'
        f'padding:2px 8px;border-radius:6px;">'
        f'{s_label}</span>'
        f'</div>'
        f'<div style="font-size:0.7rem;'
        f'color:{c("text_muted")};margin-bottom:3px;'
        f'font-family:JetBrains Mono,monospace;'
        f'overflow:hidden;text-overflow:ellipsis;'
        f'white-space:nowrap;">'
        f'📍 {stage_url or "Internal Stage"}</div>'
        f'<div style="font-size:0.7rem;'
        f'color:{c("text_muted")};">'
        f'🗄️ {stage_db}.{stage_sc}</div>'
        f'</div>'
    )


def _pipe_card(pipe_name, pipe_db, pipe_sc,
               pipe_own, pipe_ntf, env_color) -> str:
    ntf_html = ""
    if pipe_ntf:
        ntf_short = (str(pipe_ntf)[:40] + "…"
                     if len(str(pipe_ntf)) > 40
                     else str(pipe_ntf))
        ntf_html = (
            f'<div style="font-size:0.62rem;'
            f'color:{c("text_dim","#5f6b7c")};'
            f'margin-top:4px;">📡 {ntf_short}</div>'
        )
    return (
        f'<div style="background:linear-gradient('
        f'180deg,rgba(255,255,255,0.02),'
        f'rgba(255,255,255,0.00)),rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-top:3px solid {env_color};'
        f'border-radius:14px;padding:16px;'
        f'margin-bottom:10px;'
        f'box-shadow:0 10px 24px rgba(0,0,0,0.16);">'
        f'<div style="font-weight:700;'
        f'color:{c("text_primary")};font-size:0.88rem;'
        f'margin-bottom:8px;">🔁 {pipe_name}</div>'
        f'<div style="font-size:0.7rem;'
        f'color:{c("text_muted")};margin-bottom:3px;">'
        f'🗄️ {pipe_db}.{pipe_sc}</div>'
        f'<div style="font-size:0.7rem;'
        f'color:{c("text_muted")};margin-bottom:3px;">'
        f'👤 {pipe_own}</div>'
        f'{ntf_html}'
        f'</div>'
    )


def _env_ingestion_card(acc, tf, tr, tb, sr,
                         ff, success_color,
                         failed_color, env_color,
                         ov_days) -> str:
    bar_pct = min(sr, 100.0)
    return (
        f'<div style="background:linear-gradient('
        f'180deg,rgba(255,255,255,0.02),'
        f'rgba(255,255,255,0.00)),rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-left:4px solid {env_color};'
        f'border-radius:18px;padding:18px;'
        f'box-shadow:0 16px 30px rgba(0,0,0,0.18);'
        f'margin-bottom:12px;">'
        # header
        f'<div style="display:flex;align-items:center;'
        f'justify-content:space-between;margin-bottom:14px;">'
        f'<span style="font-size:0.9rem;font-weight:800;'
        f'color:{env_color};">{acc}</span>'
        f'<span style="font-family:JetBrains Mono,monospace;'
        f'font-size:0.72rem;color:{c("text_muted")};">'
        f'Last {ov_days} days · {tf:,} files</span>'
        f'</div>'
        # stats grid
        f'<div style="display:grid;'
        f'grid-template-columns:repeat(5,1fr);gap:10px;">'
        + _stat_cell(format_number(tf), "Files",   env_color)
        + _stat_cell(format_number(tr), "Rows",    c("blue"))
        + _stat_cell(format_bytes(tb),  "Data",    c("cyan"))
        + _stat_cell(f"{sr:.1f}%",      "Success", success_color)
        + _stat_cell(str(ff),           "Failed",  failed_color)
        + f'</div>'
        # progress bar
        f'<div style="height:6px;'
        f'background:{c("border")};'
        f'border-radius:4px;overflow:hidden;'
        f'margin-top:12px;">'
        f'<div style="width:{bar_pct:.1f}%;height:100%;'
        f'background:linear-gradient(90deg,'
        f'{env_color},{env_color}aa);'
        f'border-radius:4px;"></div>'
        f'</div>'
        f'</div>'
    )


def _stat_cell(value, label, color) -> str:
    return (
        f'<div style="text-align:center;">'
        f'<div style="font-family:JetBrains Mono,monospace;'
        f'font-size:1.2rem;font-weight:700;color:{color};">'
        f'{value}</div>'
        f'<div style="font-size:0.6rem;'
        f'color:{c("text_muted")};'
        f'text-transform:uppercase;">{label}</div>'
        f'</div>'
    )


def _copy_result_card(files_loaded, rows_loaded,
                       files_skipped, errors) -> str:
    err_color = c("red") if errors > 0 else c("green")
    return (
        f'<div style="background:rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-radius:14px;padding:16px;margin-top:12px;">'
        f'<div style="font-weight:700;'
        f'color:{c("text_primary")};margin-bottom:12px;">'
        f'📊 Result Summary</div>'
        f'<div style="display:grid;'
        f'grid-template-columns:repeat(4,1fr);'
        f'gap:10px;text-align:center;">'
        + _stat_cell(str(files_loaded), "Loaded",  c("green"))
        + _stat_cell(format_number(rows_loaded), "Rows", c("blue"))
        + _stat_cell(str(files_skipped), "Skipped", c("yellow"))
        + _stat_cell(str(errors),        "Errors",  err_color)
        + f'</div>'
        f'</div>'
    )


def _file_row(s_icon, s_color, status, file_n,
              acc_n, tbl_n, rows_n, size_n,
              load_t) -> str:
    file_display = (file_n[-60:] if len(file_n) > 60
                    else file_n)
    return (
        f'<div style="display:flex;align-items:center;'
        f'justify-content:space-between;'
        f'padding:10px 14px;'
        f'background:rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-radius:8px;margin-bottom:6px;">'
        # left
        f'<div style="display:flex;align-items:center;'
        f'gap:10px;flex:1;min-width:0;">'
        f'<span style="font-size:1rem;">{s_icon}</span>'
        f'<div style="min-width:0;">'
        f'<div style="font-weight:600;'
        f'color:{c("text_primary")};font-size:0.82rem;'
        f'overflow:hidden;text-overflow:ellipsis;'
        f'white-space:nowrap;">{file_display}</div>'
        f'<div style="font-size:0.68rem;'
        f'color:{c("text_muted")};">'
        f'<span style="color:{get_env_color(acc_n)};'
        f'font-weight:700;">{acc_n}</span>'
        f' → <b style="color:{c("text_secondary")};">'
        f'{tbl_n}</b></div>'
        f'</div>'
        f'</div>'
        # right
        f'<div style="display:flex;align-items:center;'
        f'gap:16px;flex-shrink:0;">'
        f'<span style="color:{c("text_muted")};'
        f'font-size:0.7rem;'
        f'font-family:JetBrains Mono,monospace;">'
        f'{rows_n} rows</span>'
        f'<span style="color:{c("text_muted")};'
        f'font-size:0.7rem;'
        f'font-family:JetBrains Mono,monospace;">'
        f'{size_n}</span>'
        f'<span style="color:{c("text_dim","#5f6b7c")};'
        f'font-size:0.68rem;">{load_t}</span>'
        f'<span style="color:{s_color};font-weight:700;'
        f'font-size:0.72rem;">{status}</span>'
        f'</div>'
        f'</div>'
    )


def _env_header(acc, count, label, env_color) -> str:
    return (
        f'<div style="display:flex;align-items:center;'
        f'gap:10px;margin-bottom:8px;margin-top:4px;">'
        f'<div style="width:8px;height:8px;'
        f'border-radius:50%;background:{env_color};'
        f'box-shadow:0 0 6px {env_color};'
        f'flex-shrink:0;"></div>'
        f'<span style="font-size:0.88rem;font-weight:800;'
        f'color:{env_color};">{acc}</span>'
        f'<span style="font-size:0.72rem;'
        f'color:{c("text_muted")};">'
        f'{count} {label}</span>'
        f'</div>'
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def safe_int(val, default: int = 0) -> int:
    try:
        if val is None:
            return default
        if isinstance(val, float) and (
                math.isnan(val) or math.isinf(val)):
            return default
        return int(val)
    except (ValueError, TypeError):
        return default


def safe_float(val, default: float = 0.0) -> float:
    try:
        if val is None:
            return default
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (ValueError, TypeError):
        return default


def format_bytes(b) -> str:
    b = safe_float(b)
    if b == 0:
        return "0 B"
    for u in ["B","KB","MB","GB","TB"]:
        if abs(b) < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} PB"


def format_number(n) -> str:
    n = safe_int(n)
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def stage_type_icon(url: str):
    url = str(url).lower()
    if url.startswith("s3://"):    return "🟠", "Amazon S3"
    if url.startswith("azure://"): return "🔵", "Azure Blob"
    if url.startswith("gcs://"):   return "🟡", "Google GCS"
    if url.startswith("@"):        return "❄️", "Snowflake Stage"
    return "💾", "External"


def _status_color_icon(status: str):
    s = str(status).upper()
    cfg = {
        "LOADED":           (c("green"),       "✅"),
        "SUCCESS":          (c("green"),       "✅"),
        "LOAD_FAILED":      (c("red"),         "❌"),
        "FAILED":           (c("red"),         "❌"),
        "LOAD_IN_PROGRESS": (c("blue"),        "🔄"),
        "RUNNING":          (c("blue"),        "🔄"),
        "PARTIALLY_LOADED": (c("yellow"),      "⚠️"),
        "SKIPPED":          (c("text_muted"),  "⏭️"),
    }
    return cfg.get(s, (c("text_muted"), "❓"))


def run_query(account: str, sql: str) -> pd.DataFrame:
    return manager.execute_query(account, sql)


def run_statement(account: str, sql: str):
    conn = manager.get_connection(account)
    if not conn:
        return False, f"Not connected to {account}"
    try:
        cur  = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cols = ([d[0] for d in cur.description]
                if cur.description else [])
        cur.close()
        return True, (pd.DataFrame(rows, columns=cols)
                      if cols else pd.DataFrame())
    except Exception as e:
        return False, str(e)


# ─── Data Fetchers ────────────────────────────────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def fetch_stages(_mid, account):
    try:
        df = run_query(account, "SHOW STAGES")
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def fetch_databases(_mid, account):
    try:
        df = run_query(account, "SHOW DATABASES")
        if df is not None and "name" in df.columns:
            return df["name"].tolist()
    except Exception:
        pass
    return []


@st.cache_data(ttl=60, show_spinner=False)
def fetch_schemas(_mid, account, database):
    try:
        df = run_query(
            account,
            f'SHOW SCHEMAS IN DATABASE "{database}"')
        if df is not None and "name" in df.columns:
            return [s for s in df["name"].tolist()
                    if s != "INFORMATION_SCHEMA"]
    except Exception:
        pass
    return []


@st.cache_data(ttl=60, show_spinner=False)
def fetch_tables(_mid, account, database, schema):
    try:
        df = run_query(
            account,
            f'SHOW TABLES IN "{database}"."{schema}"')
        if df is not None and "name" in df.columns:
            return df["name"].tolist()
    except Exception:
        pass
    return []


@st.cache_data(ttl=30, show_spinner=False)
def fetch_copy_history(_mid, account, days,
                        database=None, table=None,
                        schema=None):
    try:
        where = (
            f"WHERE LAST_LOAD_TIME >= "
            f"DATEADD('day',{-days},CURRENT_TIMESTAMP())"
        )
        if database:
            where += f" AND TABLE_CATALOG_NAME = '{database}'"
        if schema:
            where += f" AND TABLE_SCHEMA_NAME = '{schema}'"
        if table:
            where += f" AND TABLE_NAME = '{table}'"

        df = run_query(account, f"""
            SELECT
                FILE_NAME,
                STAGE_LOCATION,
                LAST_LOAD_TIME,
                ROW_COUNT,
                ROW_PARSED,
                FILE_SIZE,
                FIRST_ERROR_MESSAGE,
                ERROR_COUNT,
                STATUS,
                TABLE_NAME,
                TABLE_SCHEMA_NAME,
                TABLE_CATALOG_NAME,
                PIPE_NAME
            FROM SNOWFLAKE.ACCOUNT_USAGE.COPY_HISTORY
            {where}
            ORDER BY LAST_LOAD_TIME DESC
            LIMIT 2000
        """)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=30, show_spinner=False)
def fetch_load_history(_mid, account, database,
                        schema, table, days):
    try:
        df = run_query(account, f"""
            SELECT
                FILE_NAME, LAST_LOAD_TIME,
                ROW_COUNT, ROW_PARSED, FILE_SIZE,
                FIRST_ERROR_MESSAGE, ERROR_COUNT, STATUS
            FROM "{database}".INFORMATION_SCHEMA.LOAD_HISTORY
            WHERE TABLE_SCHEMA_NAME = '{schema}'
              AND TABLE_NAME  = '{table}'
              AND LAST_LOAD_TIME >=
                  DATEADD('day',{-days},CURRENT_TIMESTAMP())
            ORDER BY LAST_LOAD_TIME DESC
            LIMIT 1000
        """)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=30, show_spinner=False)
def fetch_pipe_status(_mid, account):
    try:
        df = run_query(account, "SHOW PIPES")
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=30, show_spinner=False)
def fetch_ingestion_kpis(_mid, account, days):
    try:
        df = run_query(account, f"""
            SELECT
                COUNT(*)                           AS TOTAL_FILES,
                SUM(ROW_COUNT)                     AS TOTAL_ROWS,
                SUM(FILE_SIZE)                     AS TOTAL_BYTES,
                SUM(ERROR_COUNT)                   AS TOTAL_ERRORS,
                COUNT(DISTINCT TABLE_NAME)         AS DISTINCT_TABLES,
                COUNT(DISTINCT STAGE_LOCATION)     AS DISTINCT_STAGES,
                SUM(CASE WHEN STATUS = 'LOADED'
                    THEN 1 ELSE 0 END)             AS SUCCESS_FILES,
                SUM(CASE WHEN STATUS = 'LOAD_FAILED'
                    THEN 1 ELSE 0 END)             AS FAILED_FILES
            FROM SNOWFLAKE.ACCOUNT_USAGE.COPY_HISTORY
            WHERE LAST_LOAD_TIME >=
                  DATEADD('day',{-days},CURRENT_TIMESTAMP())
        """)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


# ─── Manager + Sidebar ────────────────────────────────────────────────────────

manager   = SnowflakeConnectionManager()
connected = manager.get_connected_accounts()

with st.sidebar:
    st.markdown(
        f'<div style="padding:20px 16px 12px;'
        f'border-bottom:1px solid {c("border")};'
        f'margin-bottom:12px;">'
        f'<div style="font-size:1rem;font-weight:800;'
        f'color:{c("text_primary")};">📥 Data Ingestion</div>'
        f'<div style="font-size:0.56rem;'
        f'color:{c("pwc_orange")};font-weight:800;'
        f'text-transform:uppercase;letter-spacing:0.18em;">'
        f'PwC Data &amp; AI</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    for acc in connected:
        color_acc = get_env_color(acc)
        st.markdown(
            f'<div style="display:flex;align-items:center;'
            f'gap:8px;padding:8px 10px;border-radius:10px;'
            f'margin-bottom:4px;">'
            f'<div style="width:8px;height:8px;'
            f'border-radius:50%;background:{color_acc};'
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

    auto_refresh = st.checkbox(
        "⚡ Auto-refresh (60s)",
        value=False, key="ing_auto_refresh")

    hist_days_sb = st.selectbox(
        "Default History Window",
        [1, 3, 7, 14, 30], index=2,
        key="ing_hist_days")

    if st.button("🔄 Refresh Data",
                  use_container_width=True,
                  key="ing_refresh"):
        st.cache_data.clear()
        st.rerun()

# ─── Header ───────────────────────────────────────────────────────────────────

pwc_header(
    "Data Ingestion Center",
    subtitle="Copy from external stages · Monitor load history · "
             "Track file ingestion across all environments"
)

if not connected:
    st.markdown(
        _alert("Connect at least one account to manage "
               "data ingestion.", c("pwc_orange"), "🔌"),
        unsafe_allow_html=True
    )
    st.stop()

# ─── Tabs ─────────────────────────────────────────────────────────────────────

(tab_overview, tab_stages, tab_copy,
 tab_history, tab_load_hist, tab_pipes,
 tab_monitor) = st.tabs([
    "📊  Overview",
    "🗄️  Stages",
    "▶️  Run COPY",
    "📜  Copy History",
    "📋  Load History",
    "🔁  Snowpipe",
    "📡  Monitor",
])

# ═══════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════

with tab_overview:
    section_header("INGESTION OVERVIEW")

    ov_days = st.select_slider(
        "Time window",
        options=[1, 3, 7, 14, 30],
        value=7, key="ov_days_sel"
    )

    all_kpi_dfs = []
    for acc in connected:
        kdf = fetch_ingestion_kpis(id(manager), acc, ov_days)
        if not kdf.empty:
            kdf["_ACCOUNT"] = acc
            all_kpi_dfs.append(kdf)

    if all_kpi_dfs:
        kpi_df = pd.concat(all_kpi_dfs, ignore_index=True)

        num_cols = [
            "TOTAL_FILES","TOTAL_ROWS","TOTAL_BYTES",
            "TOTAL_ERRORS","SUCCESS_FILES","FAILED_FILES",
            "DISTINCT_TABLES","DISTINCT_STAGES","AVG_FILE_SIZE",
        ]
        for col in num_cols:
            if col in kpi_df.columns:
                kpi_df[col] = (
                    pd.to_numeric(kpi_df[col], errors="coerce")
                    .fillna(0))

        total_files   = safe_int(kpi_df["TOTAL_FILES"].sum())
        total_rows    = safe_int(
            kpi_df["TOTAL_ROWS"].sum()
            if "TOTAL_ROWS" in kpi_df.columns else 0)
        total_bytes   = safe_float(
            kpi_df["TOTAL_BYTES"].sum()
            if "TOTAL_BYTES" in kpi_df.columns else 0)
        total_errors  = safe_int(
            kpi_df["TOTAL_ERRORS"].sum()
            if "TOTAL_ERRORS" in kpi_df.columns else 0)
        success_files = safe_int(
            kpi_df["SUCCESS_FILES"].sum()
            if "SUCCESS_FILES" in kpi_df.columns else 0)
        failed_files  = safe_int(
            kpi_df["FAILED_FILES"].sum()
            if "FAILED_FILES" in kpi_df.columns else 0)
        success_rate  = (success_files / total_files * 100
                          if total_files > 0 else 0.0)

        sr_color = (c("green")  if success_rate > 95
                    else c("yellow") if success_rate > 80
                    else c("red"))

        r1 = st.columns(4)
        r2 = st.columns(4)

        kpis_r1 = [
            ("📁", format_number(total_files),
             "Files Loaded",  c("pwc_orange")),
            ("📊", format_number(total_rows),
             "Rows Ingested", c("blue")),
            ("💾", format_bytes(total_bytes),
             "Data Ingested", c("cyan")),
            ("✅", f"{success_rate:.1f}%",
             "Success Rate",  sr_color),
        ]
        kpis_r2 = [
            ("❌", str(failed_files),
             "Failed Files",  c("red")),
            ("⚠️", format_number(total_errors),
             "Total Errors",  c("yellow")),
            ("🗂️", str(safe_int(
                kpi_df["DISTINCT_TABLES"].sum()
                if "DISTINCT_TABLES" in kpi_df.columns else 0)),
             "Tables Loaded", c("purple")),
            ("🌐", str(safe_int(
                kpi_df["DISTINCT_STAGES"].sum()
                if "DISTINCT_STAGES" in kpi_df.columns else 0)),
             "Stages Used",   c("pwc_gold")),
        ]

        for col, (ico, val, lbl, clr) in zip(r1, kpis_r1):
            with col:
                st.markdown(_kpi(ico, val, lbl, clr),
                             unsafe_allow_html=True)
        st.markdown('<div style="height:8px;"></div>',
                     unsafe_allow_html=True)
        for col, (ico, val, lbl, clr) in zip(r2, kpis_r2):
            with col:
                st.markdown(_kpi(ico, val, lbl, clr),
                             unsafe_allow_html=True)

    st.markdown('<div style="height:12px;"></div>',
                 unsafe_allow_html=True)
    section_header("PER-ENVIRONMENT COMPARISON")

    if all_kpi_dfs:
        for acc in connected:
            env_color = get_env_color(acc)
            acc_kpi   = kpi_df[kpi_df["_ACCOUNT"] == acc]
            if acc_kpi.empty:
                continue

            row = acc_kpi.iloc[0]
            tf  = safe_int(row.get("TOTAL_FILES",   0))
            tr  = safe_int(row.get("TOTAL_ROWS",    0))
            tb  = safe_float(row.get("TOTAL_BYTES", 0))
            sf  = safe_int(row.get("SUCCESS_FILES", 0))
            ff  = safe_int(row.get("FAILED_FILES",  0))
            sr  = min((sf / tf * 100) if tf > 0 else 0.0, 100.0)

            sc_ = (c("green")  if sr > 95
                   else c("yellow") if sr > 80
                   else c("red"))
            fc_ = c("red") if ff > 0 else c("green")

            st.markdown(
                _env_ingestion_card(
                    acc, tf, tr, tb, sr, ff,
                    sc_, fc_, env_color, ov_days),
                unsafe_allow_html=True
            )
    else:
        st.markdown(
            _alert(
                "No ingestion data available. "
                "Try increasing the time range.",
                c("text_muted"), "ℹ️"),
            unsafe_allow_html=True
        )

    st.markdown('<div style="height:8px;"></div>',
                 unsafe_allow_html=True)
    section_header("DAILY INGESTION TREND")

    trend_dfs = []
    for acc in connected:
        ch = fetch_copy_history(id(manager), acc, ov_days)
        if not ch.empty and "LAST_LOAD_TIME" in ch.columns:
            ch["LAST_LOAD_TIME"] = pd.to_datetime(
                ch["LAST_LOAD_TIME"], errors="coerce")
            ch["DATE"] = ch["LAST_LOAD_TIME"].dt.date
            for col in ["ROW_COUNT","FILE_SIZE","ERROR_COUNT"]:
                if col in ch.columns:
                    ch[col] = (
                        pd.to_numeric(ch[col], errors="coerce")
                        .fillna(0))
            trend_dfs.append(ch)

    if trend_dfs:
        tdf   = pd.concat(trend_dfs, ignore_index=True)
        daily = tdf.groupby(["DATE","_ACCOUNT"]).agg(
            Files =("FILE_NAME",  "count"),
            Rows  =("ROW_COUNT",  "sum"),
            Bytes =("FILE_SIZE",  "sum"),
            Errors=("ERROR_COUNT","sum"),
        ).reset_index()

        cmap = {n: get_env_color(n)
                 for n in daily["_ACCOUNT"].unique()}

        tc1, tc2 = st.columns(2)
        with tc1:
            fig = px.area(
                daily, x="DATE", y="Files",
                color="_ACCOUNT",
                color_discrete_map=cmap,
                title="Files Loaded per Day",
                height=320)
            fig.update_traces(line=dict(width=2))
            fig.update_layout(
                xaxis_title="", yaxis_title="Files",
                legend_title_text="")
            st.plotly_chart(fig, use_container_width=True,
                             key="ov_files_trend")
        with tc2:
            daily["GB"] = daily["Bytes"] / 1e9
            fig2 = px.area(
                daily, x="DATE", y="GB",
                color="_ACCOUNT",
                color_discrete_map=cmap,
                title="Data Volume (GB) per Day",
                height=320)
            fig2.update_traces(line=dict(width=2))
            fig2.update_layout(
                xaxis_title="", yaxis_title="GB",
                legend_title_text="")
            st.plotly_chart(fig2, use_container_width=True,
                             key="ov_bytes_trend")
    else:
        st.info("No copy history available for trend charts.")


# ═══════════════════════════════════════════════════════
# TAB 2 — STAGES
# ═══════════════════════════════════════════════════════

with tab_stages:
    section_header("EXTERNAL STAGE BROWSER")

    for acc in connected:
        env_color = get_env_color(acc)
        stages_df = fetch_stages(id(manager), acc)

        st.markdown(
            _env_header(acc, len(stages_df),
                         "stage(s) found", env_color),
            unsafe_allow_html=True
        )

        if stages_df.empty:
            st.markdown(
                _alert("No stages found for this environment.",
                       c("text_muted"), "ℹ️"),
                unsafe_allow_html=True
            )
            continue

        url_col  = next((col for col in ["url","URL"]
                          if col in stages_df.columns), None)
        name_col = next((col for col in ["name","NAME"]
                          if col in stages_df.columns), None)
        db_col   = next((col for col in [
            "database_name","DATABASE_NAME"]
            if col in stages_df.columns), None)
        sc_col   = next((col for col in [
            "schema_name","TABLE_SCHEMA_NAME"]
            if col in stages_df.columns), None)

        stage_cols = st.columns(3)
        for idx, (_, row) in enumerate(stages_df.iterrows()):
            stage_name = row.get(name_col,"?") if name_col else "?"
            stage_url  = row.get(url_col, "") if url_col  else ""
            stage_db   = row.get(db_col,  "?") if db_col  else "?"
            stage_sc   = row.get(sc_col,  "?") if sc_col  else "?"
            s_icon, s_label = stage_type_icon(str(stage_url))

            with stage_cols[idx % 3]:
                st.markdown(
                    _stage_card(stage_name, stage_url,
                                 stage_db, stage_sc,
                                 s_icon, s_label,
                                 env_color),
                    unsafe_allow_html=True
                )

        with st.expander(f"📂 Browse Files — {acc}"):
            if name_col and not stages_df.empty:
                stage_list = stages_df[name_col].tolist()
                sel_stage  = st.selectbox(
                    "Select Stage", stage_list,
                    key=f"list_stage_{acc}")
                pattern = st.text_input(
                    "File Pattern (optional)",
                    placeholder="*.csv",
                    key=f"pattern_{acc}")
                if st.button("📂 List Files",
                              key=f"list_btn_{acc}",
                              type="primary"):
                    with st.spinner("Listing files…"):
                        list_sql = f'LIST @"{sel_stage}"'
                        if pattern:
                            list_sql += (
                                f" PATTERN='{pattern}'")
                        list_df = run_query(acc, list_sql)
                    if list_df is not None and not list_df.empty:
                        st.markdown(
                            f'<div style="margin-bottom:8px;">'
                            f'<span style="font-size:0.72rem;'
                            f'font-weight:700;'
                            f'color:{c("blue")};">'
                            f'📁 {len(list_df)} files found'
                            f'</span></div>',
                            unsafe_allow_html=True
                        )
                        if "size" in list_df.columns:
                            list_df["size"] = pd.to_numeric(
                                list_df["size"],
                                errors="coerce").fillna(0)
                            lc1,lc2,lc3 = st.columns(3)
                            lc1.metric("Total Files",
                                        len(list_df))
                            lc2.metric("Total Size",
                                        format_bytes(
                                            list_df["size"].sum()))
                            lc3.metric("Avg File Size",
                                        format_bytes(
                                            list_df["size"].mean()))
                        st.dataframe(list_df,
                                      use_container_width=True,
                                      hide_index=True, height=350)
                    else:
                        st.info("No files found.")
        st.markdown("---")

    section_header("CREATE EXTERNAL STAGE")

    with st.expander("➕ Create New External Stage"):
        csc1, csc2 = st.columns(2)
        with csc1:
            cs_account = st.selectbox("Account", connected,
                                       key="cs_acc")
            cs_dbs     = fetch_databases(id(manager), cs_account)
            cs_db      = st.selectbox("Database", cs_dbs,
                                       key="cs_db")
            cs_schemas = (fetch_schemas(id(manager),
                                         cs_account, cs_db)
                           if cs_db else [])
            cs_schema  = st.selectbox("Schema", cs_schemas,
                                       key="cs_schema")
            cs_name    = st.text_input("Stage Name",
                                        placeholder="MY_EXT_STAGE",
                                        key="cs_name")
        with csc2:
            cs_type = st.selectbox(
                "Stage Type",
                ["Amazon S3","Azure Blob Storage",
                 "Google Cloud Storage"],
                key="cs_type")
            placeholder_map = {
                "Amazon S3": "s3://my-bucket/path/",
                "Azure Blob Storage":
                    "azure://myaccount.blob.core.windows.net/container/",
                "Google Cloud Storage": "gcs://my-bucket/path/",
            }
            cs_url = st.text_input(
                "URL",
                placeholder=placeholder_map.get(cs_type, ""),
                key="cs_url")
            cs_comment = st.text_input("Comment (optional)",
                                        key="cs_comment")

        cr1, cr2 = st.columns(2)
        with cr1:
            if cs_type == "Amazon S3":
                cs_key_id = st.text_input("AWS Key ID",
                                           type="password",
                                           key="cs_key_id")
                cs_secret  = st.text_input("AWS Secret Key",
                                            type="password",
                                            key="cs_secret")
                creds_clause = (
                    f"\n    CREDENTIALS = "
                    f"(AWS_KEY_ID='{cs_key_id}' "
                    f"AWS_SECRET_KEY='{cs_secret}')"
                    if cs_key_id else "")
            elif cs_type == "Azure Blob Storage":
                cs_sas = st.text_input("SAS Token",
                                        type="password",
                                        key="cs_sas")
                creds_clause = (
                    f"\n    CREDENTIALS = "
                    f"(AZURE_SAS_TOKEN='{cs_sas}')"
                    if cs_sas else "")
            else:
                st.info("GCS uses Storage Integration.")
                cs_int = st.text_input(
                    "Storage Integration Name",
                    key="cs_int")
                creds_clause = (
                    f"\n    STORAGE_INTEGRATION = {cs_int}"
                    if cs_int else "")
        with cr2:
            cs_ff = st.selectbox(
                "Default File Format",
                ["CSV","JSON","PARQUET","AVRO","ORC",
                 "XML","None"],
                key="cs_file_format")
            ff_clause = (
                f"\n    FILE_FORMAT = "
                f"(TYPE = '{cs_ff}')"
                if cs_ff != "None" else "")

        if cs_name and cs_url and cs_db and cs_schema:
            cmt_c = (f"\n    COMMENT = '{cs_comment}'"
                      if cs_comment else "")
            create_stage_sql = (
                f'CREATE OR REPLACE STAGE '
                f'"{cs_db}"."{cs_schema}"."{cs_name}"\n'
                f"    URL = '{cs_url}'"
                f"{creds_clause}{ff_clause}{cmt_c};"
            )
            st.markdown(_sql_block(create_stage_sql),
                         unsafe_allow_html=True)
            if st.button("▶️ Create Stage", type="primary",
                          key="btn_create_stage"):
                with st.spinner(
                        f"Creating stage {cs_name}…"):
                    ok, result = run_statement(
                        cs_account, create_stage_sql)
                if ok:
                    st.success(
                        f"✅ Stage **{cs_name}** created!")
                    st.cache_data.clear()
                else:
                    st.error(f"❌ {result}")


# ═══════════════════════════════════════════════════════
# TAB 3 — RUN COPY
# ═══════════════════════════════════════════════════════

with tab_copy:
    section_header("COPY DATA FROM STAGE → TABLE")

    st.markdown(
        _info_box(
            "<b style='color:#D04A02;'>COPY INTO</b> "
            "loads files from an external or internal stage "
            "into a Snowflake table. Configure all options "
            "below and the SQL will be generated automatically.",
            accent=c("pwc_orange")
        ),
        unsafe_allow_html=True
    )

    st.markdown(_step(1, "Source — Stage & Files"),
                 unsafe_allow_html=True)
    s1a, s1b = st.columns(2)
    with s1a:
        copy_account   = st.selectbox("Account", connected,
                                       key="copy_acc")
        copy_stages_df = fetch_stages(id(manager), copy_account)
        copy_stage_col = next(
            (col for col in ["name","NAME"]
             if col in copy_stages_df.columns), None
        ) if not copy_stages_df.empty else None
        copy_stage_list = (copy_stages_df[copy_stage_col].tolist()
                            if copy_stage_col else [])
        copy_stage = st.selectbox(
            "Source Stage",
            options=copy_stage_list or ["(no stages found)"],
            key="copy_stage")
    with s1b:
        copy_pattern = st.text_input(
            "File Pattern (PATTERN=)",
            placeholder=r".*\.csv",
            key="copy_pattern")
        copy_files = st.text_input(
            "Specific Files (FILES=)",
            placeholder="'file1.csv','file2.csv'",
            key="copy_files")

    st.markdown(_step(2, "Target — Database.Schema.Table"),
                 unsafe_allow_html=True)
    t1, t2, t3 = st.columns(3)
    with t1:
        copy_dbs  = fetch_databases(id(manager), copy_account)
        copy_db   = st.selectbox("Database", copy_dbs,
                                   key="copy_db")
    with t2:
        copy_schemas = (
            fetch_schemas(id(manager), copy_account, copy_db)
            if copy_db else [])
        copy_schema = st.selectbox("Schema", copy_schemas,
                                    key="copy_schema")
    with t3:
        copy_tables = (
            fetch_tables(id(manager), copy_account,
                          copy_db, copy_schema)
            if copy_db and copy_schema else [])
        copy_table = st.text_input("Table Name",
                                    placeholder="MY_TABLE",
                                    key="copy_table")
        if copy_tables:
            sel = st.selectbox(
                "Or select existing",
                options=["(type above)"] + copy_tables,
                key="copy_table_sel")
            if sel != "(type above)":
                copy_table = sel

    st.markdown(_step(3, "File Format Options"),
                 unsafe_allow_html=True)
    ff1, ff2, ff3 = st.columns(3)
    with ff1:
        file_format_type = st.selectbox(
            "File Format",
            ["CSV","JSON","PARQUET","AVRO","ORC","XML"],
            key="ff_type")
    with ff2:
        if file_format_type == "CSV":
            field_delimiter = st.text_input(
                "Field Delimiter", value=",",
                key="ff_delim")
            skip_header = st.number_input(
                "Skip Header Rows", 0, 10, 1,
                key="ff_skip")
        else:
            field_delimiter = ","
            skip_header     = 0
    with ff3:
        compression = st.selectbox(
            "Compression",
            ["AUTO","GZIP","BROTLI","ZSTD",
             "DEFLATE","RAW_DEFLATE","NONE"],
            key="ff_compression")
        null_if = st.text_input("NULL IF", value="''",
                                  key="ff_null_if")

    st.markdown(_step(4, "Copy Options"),
                 unsafe_allow_html=True)
    co1, co2, co3, co4 = st.columns(4)
    with co1:
        on_error = st.selectbox(
            "ON_ERROR",
            ["ABORT_STATEMENT","CONTINUE",
             "SKIP_FILE","SKIP_FILE_<num>"],
            key="co_on_error")
    with co2:
        purge = st.checkbox("PURGE",  value=False,
                             key="co_purge")
        force = st.checkbox("FORCE",  value=False,
                             key="co_force")
    with co3:
        truncate     = st.checkbox("TRUNCATECOLUMNS",
                                    value=False,
                                    key="co_truncate")
        match_by_col = st.checkbox("MATCH_BY_COLUMN_NAME",
                                    value=False,
                                    key="co_match")
    with co4:
        size_limit = st.number_input(
            "SIZE_LIMIT (0=unlimited)",
            min_value=0, value=0,
            key="co_size_limit")

    with st.expander(
            "🗂️ Column Mapping / Transformation (optional)"):
        col_map_input = st.text_area(
            "Column mapping (SQL expressions)",
            placeholder="$1::INTEGER AS id,\n"
                         "UPPER($2) AS name",
            height=100, key="col_map")

    if (copy_stage and copy_stage != "(no stages found)"
            and copy_table and copy_db and copy_schema):

        if file_format_type == "CSV":
            ff_clause_copy = (
                f"TYPE = CSV\n"
                f"        FIELD_DELIMITER = '{field_delimiter}'\n"
                f"        SKIP_HEADER = {skip_header}\n"
                f"        NULL_IF = ({null_if})\n"
                f"        COMPRESSION = {compression}")
        else:
            ff_clause_copy = (
                f"TYPE = {file_format_type}\n"
                f"        NULL_IF = ({null_if})\n"
                f"        COMPRESSION = {compression}")

        source_q = f'@"{copy_stage}"'
        if copy_pattern:
            source_q += f"\n    PATTERN = '{copy_pattern}'"
        if copy_files:
            source_q += f"\n    FILES = ({copy_files})"

        col_map_c = ""
        if col_map_input.strip():
            col_map_c = f"\n    ({col_map_input.strip()})"

        opts = [f"ON_ERROR = '{on_error}'"]
        if purge:         opts.append("PURGE = TRUE")
        if force:         opts.append("FORCE = TRUE")
        if truncate:      opts.append("TRUNCATECOLUMNS = TRUE")
        if match_by_col:  opts.append(
            "MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE")
        if size_limit > 0:opts.append(
            f"SIZE_LIMIT = {size_limit}")

        copy_sql = (
            f'COPY INTO '
            f'"{copy_db}"."{copy_schema}"."{copy_table}"'
            f'{col_map_c}\n'
            f'FROM {source_q}\n'
            f'FILE_FORMAT = (\n'
            f'    {ff_clause_copy}\n'
            f')\n'
            f'COPY_OPTIONS = (\n'
            f'    ' + "\n    ".join(opts) + '\n);'
        )

        section_header("GENERATED SQL")
        st.markdown(_sql_block(copy_sql),
                     unsafe_allow_html=True)

        val_col, exec_col = st.columns(2)
        with val_col:
            if st.button("🔍 Validate", key="btn_validate"):
                val_sql = (copy_sql.rstrip(";")
                           + "\nVALIDATION_MODE = "
                             "RETURN_ERRORS;")
                with st.spinner("Validating…"):
                    ok_v, res_v = run_statement(
                        copy_account, val_sql)
                if ok_v:
                    if (isinstance(res_v, pd.DataFrame)
                            and not res_v.empty):
                        st.warning(
                            f"⚠️ {len(res_v)} error(s):")
                        st.dataframe(res_v,
                                      use_container_width=True)
                    else:
                        st.success("✅ Validation passed!")
                else:
                    st.error(f"❌ {res_v}")

        with exec_col:
            run_copy = st.button(
                "▶️ Execute COPY INTO",
                type="primary", key="btn_run_copy")

        if run_copy:
            with st.status("Running COPY INTO…",
                            expanded=True) as copy_status:
                st.write("📡 Connecting to stage…")
                time.sleep(0.5)
                st.write("🔄 Executing COPY INTO…")
                ok_c, res_c = run_statement(
                    copy_account, copy_sql)
                time.sleep(0.5)
                copy_status.update(
                    label=("✅ COPY INTO completed!"
                            if ok_c else "❌ COPY failed"),
                    state="complete" if ok_c else "error",
                    expanded=False)

            if ok_c:
                if (isinstance(res_c, pd.DataFrame)
                        and not res_c.empty):
                    rows_loaded = safe_int(
                        res_c["rows_loaded"].sum()
                        if "rows_loaded" in res_c.columns
                        else 0)
                    files_loaded = (
                        len(res_c[res_c["status"] == "LOADED"])
                        if "status" in res_c.columns else 0)
                    files_skipped = (
                        len(res_c[res_c["status"] == "SKIPPED"])
                        if "status" in res_c.columns else 0)
                    errors = safe_int(
                        res_c["errors_seen"].sum()
                        if "errors_seen" in res_c.columns else 0)

                    st.success(
                        f"✅ {len(res_c)} file(s) processed.")
                    st.markdown(
                        _copy_result_card(
                            files_loaded, rows_loaded,
                            files_skipped, errors),
                        unsafe_allow_html=True)

                    with st.expander("📋 Full Result"):
                        st.dataframe(res_c,
                                      use_container_width=True,
                                      hide_index=True)
                    st.cache_data.clear()
                else:
                    st.success("✅ COPY INTO executed!")
                    st.cache_data.clear()
            else:
                st.error(f"❌ {res_c}")


# ═══════════════════════════════════════════════════════
# TAB 4 — COPY HISTORY
# ═══════════════════════════════════════════════════════

with tab_history:
    section_header("COPY HISTORY — ACCOUNT_USAGE")

    fh1, fh2, fh3, fh4 = st.columns(4)
    with fh1:
        ch_accs = st.multiselect(
            "Environments", connected,
            default=connected, key="ch_accs")
    with fh2:
        ch_days = st.selectbox(
            "Time Range",
            [1,3,7,14,30], index=2,
            format_func=lambda x: f"Last {x} days",
            key="ch_days")
    with fh3:
        ch_status = st.multiselect(
            "Status",
            ["LOADED","LOAD_FAILED",
             "PARTIALLY_LOADED","SKIPPED"],
            default=[], key="ch_status")
    with fh4:
        ch_search = st.text_input(
            "🔍 Search table / file",
            key="ch_search",
            placeholder="Filter by name…")

    ch_dfs = []
    for acc in (ch_accs or connected):
        chdf = fetch_copy_history(id(manager), acc, ch_days)
        if not chdf.empty:
            ch_dfs.append(chdf)

    if not ch_dfs:
        st.info("No copy history found.")
    else:
        ch_df = pd.concat(ch_dfs, ignore_index=True)

        if ch_status and "STATUS" in ch_df.columns:
            ch_df = ch_df[ch_df["STATUS"].isin(ch_status)]
        if ch_search:
            mask = ch_df.apply(
                lambda r: r.astype(str).str.contains(
                    ch_search, case=False, na=False).any(),
                axis=1)
            ch_df = ch_df[mask]

        for col in ["ROW_COUNT", "ROW_PARSED",
                     "FILE_SIZE", "ERROR_COUNT"]:
            if col in ch_df.columns:
                ch_df[col] = (
                    pd.to_numeric(ch_df[col], errors="coerce")
                    .fillna(0))
        if "LAST_LOAD_TIME" in ch_df.columns:
            ch_df["LAST_LOAD_TIME"] = pd.to_datetime(
                ch_df["LAST_LOAD_TIME"], errors="coerce")

        total_ch  = len(ch_df)
        loaded    = safe_int(
            len(ch_df[ch_df["STATUS"] == "LOADED"])
            if "STATUS" in ch_df.columns else 0)
        failed    = safe_int(
            len(ch_df[ch_df["STATUS"] == "LOAD_FAILED"])
            if "STATUS" in ch_df.columns else 0)
        skipped   = safe_int(
            len(ch_df[ch_df["STATUS"] == "SKIPPED"])
            if "STATUS" in ch_df.columns else 0)
        tot_rows  = safe_int(
            ch_df["ROW_COUNT"].sum()
            if "ROW_COUNT" in ch_df.columns else 0)
        tot_bytes = safe_float(
            ch_df["FILE_SIZE"].sum()
            if "FILE_SIZE" in ch_df.columns else 0)

        sm1, sm2, sm3, sm4, sm5, sm6 = st.columns(6)
        sm1.metric("Total Files", f"{total_ch:,}")
        sm2.metric("Loaded",      f"{loaded:,}")
        sm3.metric("Failed",      f"{failed:,}")
        sm4.metric("Skipped",     f"{skipped:,}")
        sm5.metric("Rows Loaded", format_number(tot_rows))
        sm6.metric("Data Size",   format_bytes(tot_bytes))

        st.markdown('<div style="height:8px;"></div>',
                     unsafe_allow_html=True)

        cht1, cht2, cht3 = st.tabs([
            "📊 Charts",
            "🔬 Error Analysis",
            "📋 Raw Data",
        ])

        cmap_ch = {}
        if "_ACCOUNT" in ch_df.columns:
            cmap_ch = {n: get_env_color(n)
                        for n in ch_df["_ACCOUNT"].unique()}

        with cht1:
            c1, c2 = st.columns(2)
            with c1:
                if "STATUS" in ch_df.columns:
                    sc = ch_df["STATUS"].value_counts()
                    s_colors = {
                        "LOADED":           c("green"),
                        "LOAD_FAILED":      c("red"),
                        "PARTIALLY_LOADED": c("yellow"),
                        "SKIPPED":          c("text_muted"),
                    }
                    fig = go.Figure(go.Pie(
                        labels=sc.index,
                        values=sc.values,
                        hole=0.6,
                        marker_colors=[
                            s_colors.get(s, c("blue"))
                            for s in sc.index],
                        textinfo="label+percent"))
                    fig.update_layout(
                        title="File Load Status",
                        height=340,
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(
                            color=c("text_secondary")))
                    st.plotly_chart(
                        fig, use_container_width=True,
                        key="ch_status_pie")

            with c2:
                if "LAST_LOAD_TIME" in ch_df.columns:
                    ch_df["DATE"] = (
                        ch_df["LAST_LOAD_TIME"].dt.date)
                    grp_cols = (
                        ["DATE", "_ACCOUNT"]
                        if "_ACCOUNT" in ch_df.columns
                        else ["DATE"])
                    daily_ch = ch_df.groupby(grp_cols).agg(
                        Files=("FILE_NAME", "count"),
                        Bytes=("FILE_SIZE", "sum")
                    ).reset_index()
                    if "_ACCOUNT" in daily_ch.columns:
                        fig2 = px.bar(
                            daily_ch,
                            x="DATE", y="Files",
                            color="_ACCOUNT",
                            color_discrete_map=cmap_ch,
                            height=340,
                            title="Files Loaded per Day",
                            barmode="stack")
                    else:
                        fig2 = px.bar(
                            daily_ch,
                            x="DATE", y="Files",
                            height=340,
                            title="Files Loaded per Day")
                    fig2.update_layout(
                        xaxis_title="",
                        yaxis_title="Files",
                        legend_title_text="")
                    st.plotly_chart(
                        fig2, use_container_width=True,
                        key="ch_daily_bar")

            if "TABLE_NAME" in ch_df.columns:
                grp2 = (
                    ["TABLE_NAME", "_ACCOUNT"]
                    if "_ACCOUNT" in ch_df.columns
                    else ["TABLE_NAME"])
                top_t = (
                    ch_df.groupby(grp2)
                    .agg(
                        Files=("FILE_NAME", "count"),
                        Rows=("ROW_COUNT", "sum"))
                    .reset_index()
                    .nlargest(15, "Files"))
                if "_ACCOUNT" in top_t.columns:
                    fig3 = px.bar(
                        top_t,
                        x="TABLE_NAME", y="Files",
                        color="_ACCOUNT",
                        color_discrete_map=cmap_ch,
                        height=340,
                        title="Top 15 Tables by Files",
                        barmode="group")
                else:
                    fig3 = px.bar(
                        top_t,
                        x="TABLE_NAME", y="Files",
                        height=340,
                        title="Top 15 Tables by Files")
                fig3.update_layout(
                    xaxis_tickangle=-35,
                    xaxis_title="",
                    legend_title_text="")
                st.plotly_chart(
                    fig3, use_container_width=True,
                    key="ch_top_tables")

        with cht2:
            if "FIRST_ERROR_MESSAGE" in ch_df.columns:
                err_df = ch_df[
                    ch_df["FIRST_ERROR_MESSAGE"].notna() &
                    (ch_df["FIRST_ERROR_MESSAGE"] != "")
                ].copy()

                if not err_df.empty:
                    st.markdown(
                        _alert(
                            f"{len(err_df)} file(s) with errors",
                            c("red"), "❌"),
                        unsafe_allow_html=True)

                    ec1, ec2 = st.columns(2)
                    with ec1:
                        top_e = (
                            err_df["FIRST_ERROR_MESSAGE"]
                            .value_counts()
                            .head(10)
                            .reset_index())
                        top_e.columns = ["Error", "Count"]
                        fig_e = px.bar(
                            top_e,
                            x="Count", y="Error",
                            orientation="h",
                            height=380,
                            title="Top Error Messages",
                            color="Count",
                            color_continuous_scale=[
                                c("yellow"), c("red")])
                        fig_e.update_layout(
                            yaxis_title="",
                            coloraxis_showscale=False,
                            yaxis=dict(
                                tickfont=dict(size=9)))
                        st.plotly_chart(
                            fig_e,
                            use_container_width=True,
                            key="ch_err_bar")
                    with ec2:
                        if "TABLE_NAME" in err_df.columns:
                            ebt = (
                                err_df
                                .groupby("TABLE_NAME")[
                                    "FIRST_ERROR_MESSAGE"]
                                .count()
                                .reset_index())
                            ebt.columns = ["Table", "Errors"]
                            fig_et = px.pie(
                                ebt,
                                values="Errors",
                                names="Table",
                                height=380,
                                title="Errors by Table",
                                hole=0.5,
                                color_discrete_sequence=
                                CHART_COLORS)
                            st.plotly_chart(
                                fig_et,
                                use_container_width=True,
                                key="ch_err_pie")

                    err_cols = [col for col in [
                        "_ACCOUNT",
                        "TABLE_NAME",
                        "TABLE_SCHEMA_NAME",
                        "FILE_NAME",
                        "FIRST_ERROR_MESSAGE",
                        "ERROR_COUNT",
                        "LAST_LOAD_TIME",
                    ] if col in err_df.columns]
                    st.dataframe(
                        err_df[err_cols].head(100),
                        use_container_width=True,
                        hide_index=True,
                        height=400)
                else:
                    st.success(
                        "🎉 No errors in selected window!")

        with cht3:
            disp = [col for col in [
                "_ACCOUNT",
                "TABLE_CATALOG_NAME",
                "TABLE_SCHEMA_NAME",
                "TABLE_NAME",
                "FILE_NAME",
                "STAGE_LOCATION",
                "STATUS",
                "LAST_LOAD_TIME",
                "ROW_COUNT",
                "ROW_PARSED",
                "FILE_SIZE",
                "ERROR_COUNT",
                "FIRST_ERROR_MESSAGE",
                "PIPE_NAME",
            ] if col in ch_df.columns]

            st.dataframe(
                ch_df[disp].rename(columns={
                    "_ACCOUNT":            "Account",
                    "TABLE_CATALOG_NAME":       "DB",
                    "TABLE_SCHEMA_NAME":   "Schema",
                    "TABLE_NAME":          "Table",
                    "FILE_NAME":           "File",
                    "STAGE_LOCATION":      "Stage",
                    "STATUS":              "Status",
                    "LAST_LOAD_TIME":      "Load Time",
                    "ROW_COUNT":           "Rows",
                    "ROW_PARSED":          "Parsed",
                    "FILE_SIZE":           "Bytes",
                    "ERROR_COUNT":         "Errors",
                    "FIRST_ERROR_MESSAGE": "Error Msg",
                    "PIPE_NAME":           "Pipe",
                }),
                use_container_width=True,
                hide_index=True,
                height=550)

            st.download_button(
                "📥 Download Copy History CSV",
                data=ch_df.to_csv(index=False),
                file_name=(
                    f"copy_history_"
                    f"{datetime.date.today()}.csv"),
                mime="text/csv",
                key="ch_download")

# ═══════════════════════════════════════════════════════
# TAB 5 — LOAD HISTORY
# ═══════════════════════════════════════════════════════

with tab_load_hist:
    section_header("LOAD HISTORY — INFORMATION_SCHEMA")

    st.markdown(
        _info_box(
            "<b style='color:#3b82f6;'>"
            "INFORMATION_SCHEMA.LOAD_HISTORY</b> "
            "provides load history for a specific table "
            "within the last 14 days. For longer history "
            "use the Copy History tab (ACCOUNT_USAGE).",
            accent=c("blue")
        ),
        unsafe_allow_html=True
    )

    lh1, lh2 = st.columns(2)
    with lh1:
        lh_acc  = st.selectbox("Account", connected,
                                 key="lh_acc")
        lh_dbs  = fetch_databases(id(manager), lh_acc)
        lh_db   = st.selectbox("Database", lh_dbs,
                                 key="lh_db")
    with lh2:
        lh_schemas = (fetch_schemas(id(manager), lh_acc, lh_db)
                       if lh_db else [])
        lh_schema  = st.selectbox("Schema", lh_schemas,
                                    key="lh_schema")
        lh_tables  = (fetch_tables(id(manager), lh_acc,
                                    lh_db, lh_schema)
                       if lh_db and lh_schema else [])
        lh_table   = st.selectbox(
            "Table",
            lh_tables or ["(no tables found)"],
            key="lh_table")

    lh_days = st.select_slider(
        "History window (max 14 for INFORMATION_SCHEMA)",
        options=[1,3,7,14], value=7, key="lh_days")

    if (lh_table and lh_table != "(no tables found)"
            and lh_db and lh_schema):
        if st.button("🔍 Load History", type="primary",
                      key="btn_lh"):
            with st.spinner(
                    f"Fetching history for {lh_table}…"):
                lh_df = fetch_load_history(
                    id(manager), lh_acc,
                    lh_db, lh_schema, lh_table, lh_days)

            if lh_df is not None and not lh_df.empty:
                for col in ["ROW_COUNT","ROW_PARSED",
                             "FILE_SIZE","ERROR_COUNT"]:
                    if col in lh_df.columns:
                        lh_df[col] = (
                            pd.to_numeric(
                                lh_df[col], errors="coerce")
                            .fillna(0))

                lm1,lm2,lm3,lm4 = st.columns(4)
                lm1.metric("Files", f"{len(lh_df):,}")
                lm2.metric("Rows Loaded",
                            format_number(safe_int(
                                lh_df["ROW_COUNT"].sum()
                                if "ROW_COUNT" in lh_df.columns
                                else 0)))
                lm3.metric("Data Size",
                            format_bytes(safe_float(
                                lh_df["FILE_SIZE"].sum()
                                if "FILE_SIZE" in lh_df.columns
                                else 0)))
                lm4.metric("Errors",
                            str(safe_int(
                                lh_df["ERROR_COUNT"].sum()
                                if "ERROR_COUNT" in lh_df.columns
                                else 0)))

                if "LAST_LOAD_TIME" in lh_df.columns:
                    lh_df["LAST_LOAD_TIME"] = pd.to_datetime(
                        lh_df["LAST_LOAD_TIME"],
                        errors="coerce")
                    lh_df["DATE"] = (
                        lh_df["LAST_LOAD_TIME"].dt.date)
                    daily_lh = lh_df.groupby("DATE").agg(
                        Files=("FILE_NAME","count"),
                        Rows =("ROW_COUNT","sum")
                    ).reset_index()

                    lc1, lc2 = st.columns(2)
                    with lc1:
                        fig = px.bar(
                            daily_lh, x="DATE", y="Files",
                            height=280,
                            title=f"Daily Files — {lh_table}",
                            color_discrete_sequence=[
                                get_env_color(lh_acc)])
                        fig.update_layout(
                            xaxis_title="",
                            yaxis_title="Files")
                        st.plotly_chart(
                            fig, use_container_width=True,
                            key="lh_daily_files")
                    with lc2:
                        fig2 = px.line(
                            daily_lh, x="DATE", y="Rows",
                            height=280,
                            title=f"Daily Rows — {lh_table}",
                            color_discrete_sequence=[
                                get_env_color(lh_acc)],
                            markers=True)
                        fig2.update_layout(
                            xaxis_title="",
                            yaxis_title="Rows")
                        st.plotly_chart(
                            fig2, use_container_width=True,
                            key="lh_daily_rows")

                st.dataframe(lh_df,
                              use_container_width=True,
                              hide_index=True, height=450)
                st.download_button(
                    "📥 Download Load History",
                    data=lh_df.to_csv(index=False),
                    file_name=(
                        f"load_history_{lh_table}_"
                        f"{datetime.date.today()}.csv"),
                    mime="text/csv", key="lh_dl")
            else:
                st.info(
                    f"No load history found for "
                    f"**{lh_table}** in "
                    f"the last {lh_days} day(s).")


# ═══════════════════════════════════════════════════════
# TAB 6 — SNOWPIPE
# ═══════════════════════════════════════════════════════

with tab_pipes:
    section_header("SNOWPIPE STATUS & MANAGEMENT")

    st.markdown(
        _info_box(
            "<b style='color:#06b6d4;'>Snowpipe</b> "
            "enables continuous, automated data loading "
            "using micro-batch processing triggered by "
            "file arrival events.",
            accent=c("cyan")
        ),
        unsafe_allow_html=True
    )

    for acc in connected:
        env_color = get_env_color(acc)
        pipes_df  = fetch_pipe_status(id(manager), acc)

        st.markdown(
            _env_header(acc, len(pipes_df),
                         "pipe(s)", env_color),
            unsafe_allow_html=True
        )

        if pipes_df.empty:
            st.markdown(
                _alert("No Snowpipes found.",
                       c("text_muted"), "ℹ️"),
                unsafe_allow_html=True
            )
            continue

        name_col  = next((col for col in ["name","NAME"]
                           if col in pipes_df.columns), None)
        db_col    = next((col for col in [
            "database_name","DATABASE_NAME"]
            if col in pipes_df.columns), None)
        sc_col    = next((col for col in [
            "schema_name","TABLE_SCHEMA_NAME"]
            if col in pipes_df.columns), None)
        def_col   = next((col for col in [
            "definition","DEFINITION"]
            if col in pipes_df.columns), None)
        owner_col = next((col for col in ["owner","OWNER"]
                           if col in pipes_df.columns), None)
        notif_col = next((col for col in [
            "notification_channel","NOTIFICATION_CHANNEL"]
            if col in pipes_df.columns), None)

        pipe_grid = st.columns(min(3, max(1, len(pipes_df))))
        for idx, (_, pipe) in enumerate(pipes_df.iterrows()):
            pipe_name = (pipe.get(name_col,"?")
                          if name_col else "?")
            pipe_db   = (pipe.get(db_col,  "?")
                          if db_col   else "?")
            pipe_sc   = (pipe.get(sc_col,  "?")
                          if sc_col   else "?")
            pipe_def  = (pipe.get(def_col, "")
                          if def_col  else "")
            pipe_own  = (pipe.get(owner_col,"?")
                          if owner_col else "?")
            pipe_ntf  = (pipe.get(notif_col,"")
                          if notif_col else "")

            with pipe_grid[idx % 3]:
                st.markdown(
                    _pipe_card(pipe_name, pipe_db,
                                pipe_sc, pipe_own,
                                pipe_ntf, env_color),
                    unsafe_allow_html=True
                )

            with st.expander(f"⚙️ Manage: {pipe_name}"):
                pa1, pa2 = st.columns(2)
                with pa1:
                    if st.button(
                        "📊 Get Status",
                        key=f"ps_{acc}_{pipe_name}"):
                        ok_ps, res_ps = run_statement(
                            acc,
                            f"SELECT SYSTEM$PIPE_STATUS"
                            f"('{pipe_name}')")
                        if (ok_ps and isinstance(
                                res_ps, pd.DataFrame)):
                            st.code(
                                res_ps.iloc[0,0]
                                if not res_ps.empty
                                else "No status",
                                language="json")
                    if st.button(
                        "▶️ Resume",
                        key=f"pr_{acc}_{pipe_name}",
                        type="primary"):
                        ok_r, msg_r = run_statement(
                            acc,
                            f'ALTER PIPE "{pipe_name}" RESUME')
                        if ok_r:
                            st.success("✅ Pipe resumed")
                        else:
                            st.error(f"❌ {msg_r}")
                with pa2:
                    if st.button(
                        "⏸️ Pause",
                        key=f"pp_{acc}_{pipe_name}"):
                        ok_p, msg_p = run_statement(
                            acc,
                            f'ALTER PIPE "{pipe_name}" PAUSE')
                        if ok_p:
                            st.success("✅ Paused")
                        else:
                            st.error(f"❌ {msg_p}")
                    if st.button(
                        "🔄 Refresh",
                        key=f"prf_{acc}_{pipe_name}"):
                        ok_rf, msg_rf = run_statement(
                            acc,
                            f'ALTER PIPE "{pipe_name}" REFRESH')
                        if ok_rf:
                            st.success("✅ Refreshed")
                        else:
                            st.error(f"❌ {msg_rf}")

                if pipe_def:
                    st.markdown(_sql_block(pipe_def),
                                 unsafe_allow_html=True)

        st.markdown("---")

    section_header("CREATE SNOWPIPE")

    with st.expander("➕ Create New Snowpipe"):
        np1, np2 = st.columns(2)
        with np1:
            np_acc     = st.selectbox("Account", connected,
                                       key="np_acc")
            np_dbs     = fetch_databases(id(manager), np_acc)
            np_db      = st.selectbox("Database", np_dbs,
                                       key="np_db")
            np_schemas = (fetch_schemas(
                id(manager), np_acc, np_db)
                if np_db else [])
            np_schema  = st.selectbox("Schema", np_schemas,
                                       key="np_schema")
            np_name    = st.text_input("Pipe Name",
                                        key="np_name",
                                        placeholder="MY_PIPE")
        with np2:
            np_stage = st.text_input(
                "Source Stage", key="np_stage",
                placeholder="@MY_DB.MY_SCHEMA.MY_STAGE")
            np_tables = (fetch_tables(id(manager),
                                       np_acc, np_db, np_schema)
                          if np_db and np_schema else [])
            np_table  = st.selectbox(
                "Target Table",
                options=np_tables or ["(none)"],
                key="np_table")
            np_auto_ingest = st.checkbox(
                "Enable AUTO_INGEST",
                value=True, key="np_auto_ingest")
            np_comment = st.text_input("Comment",
                                        key="np_comment")

        if (np_name and np_stage
                and np_table and np_table != "(none)"):
            ai_c = "\nAUTO_INGEST = TRUE" if np_auto_ingest else ""
            cm_c = (f"\nCOMMENT = '{np_comment}'"
                     if np_comment else "")
            np_sql = (
                f'CREATE OR REPLACE PIPE '
                f'"{np_db}"."{np_schema}"."{np_name}"'
                f'{ai_c}{cm_c}\nAS\n'
                f'COPY INTO '
                f'"{np_db}"."{np_schema}"."{np_table}"\n'
                f'FROM {np_stage}\n'
                f"FILE_FORMAT = (TYPE = 'CSV' "
                f"SKIP_HEADER = 1);"
            )
            st.markdown(_sql_block(np_sql),
                         unsafe_allow_html=True)
            if st.button("▶️ Create Pipe", type="primary",
                          key="btn_create_pipe"):
                ok_np, msg_np = run_statement(np_acc, np_sql)
                if ok_np:
                    st.success(
                        f"✅ Snowpipe **{np_name}** created!")
                    st.cache_data.clear()
                else:
                    st.error(f"❌ {msg_np}")


# ═══════════════════════════════════════════════════════
# TAB 7 — LIVE MONITOR
# ═══════════════════════════════════════════════════════

with tab_monitor:
    section_header("LIVE INGESTION MONITOR")

    if auto_refresh:
        st.markdown(
            _alert("Auto-refresh active (60s)",
                   c("green"), "⚡"),
            unsafe_allow_html=True
        )
        time.sleep(60)
        st.rerun()

    mon_days = st.select_slider(
        "Window", [1,3,7], value=1,
        key="mon_days_sel")

    live_dfs = []
    for acc in connected:
        ldf = fetch_copy_history(id(manager), acc, mon_days)
        if not ldf.empty:
            live_dfs.append(ldf)

    if live_dfs:
        live_df = pd.concat(live_dfs, ignore_index=True)

        for col in ["ROW_COUNT","FILE_SIZE","ERROR_COUNT"]:
            if col in live_df.columns:
                live_df[col] = (
                    pd.to_numeric(live_df[col], errors="coerce")
                    .fillna(0))
        if "LAST_LOAD_TIME" in live_df.columns:
            live_df["LAST_LOAD_TIME"] = pd.to_datetime(
                live_df["LAST_LOAD_TIME"], errors="coerce")

        mon_cols_kpi = st.columns(4)
        mon_kpis = [
            ("📁", f"{len(live_df):,}",      "Files",  c("pwc_orange")),
            ("📊", format_number(safe_int(
                live_df["ROW_COUNT"].sum()
                if "ROW_COUNT" in live_df.columns else 0)),
             "Rows",   c("blue")),
            ("💾", format_bytes(safe_float(
                live_df["FILE_SIZE"].sum()
                if "FILE_SIZE" in live_df.columns else 0)),
             "Data",   c("cyan")),
            ("❌", str(safe_int(
                live_df["ERROR_COUNT"].sum()
                if "ERROR_COUNT" in live_df.columns else 0)),
             "Errors", c("red")),
        ]
        for col, (ico, val, lbl, clr) in zip(
                mon_cols_kpi, mon_kpis):
            with col:
                st.markdown(_kpi(ico, val, lbl, clr),
                             unsafe_allow_html=True)

        st.markdown('<div style="height:8px;"></div>',
                     unsafe_allow_html=True)

        if "LAST_LOAD_TIME" in live_df.columns:
            live_df["HOUR"]    = (
                live_df["LAST_LOAD_TIME"].dt.hour)
            live_df["WEEKDAY"] = (
                live_df["LAST_LOAD_TIME"].dt.day_name())
            hm_data = live_df.groupby(
                ["WEEKDAY","HOUR"]
            )["FILE_NAME"].count().reset_index()
            hm_data.columns = ["Day","Hour","Files"]
            day_order = ["Monday","Tuesday","Wednesday",
                          "Thursday","Friday","Saturday","Sunday"]
            pivot = hm_data.pivot_table(
                index="Day", columns="Hour",
                values="Files", aggfunc="sum"
            ).reindex([d for d in day_order
                        if d in hm_data["Day"].unique()])

            if not pivot.empty:
                fig_hm = px.imshow(
                    pivot,
                    labels=dict(x="Hour",y="Day",
                                 color="Files"),
                    color_continuous_scale=[
                        c("bg_primary","#07090d"),
                        c("pwc_orange"),
                        c("pwc_gold")],
                    height=300, aspect="auto",
                    title="File Load Heatmap")
                fig_hm.update_layout(
                    xaxis=dict(dtick=1),
                    margin=dict(l=10,r=10,t=40,b=10))
                st.plotly_chart(fig_hm,
                                 use_container_width=True,
                                 key="mon_heatmap")

        section_header("LATEST FILE LOADS")

        latest_cols = [col for col in [
            "_ACCOUNT","TABLE_NAME","FILE_NAME",
            "STATUS","LAST_LOAD_TIME",
            "ROW_COUNT","FILE_SIZE","ERROR_COUNT"
        ] if col in live_df.columns]

        for _, row in live_df[latest_cols].head(20).iterrows():
            status   = str(row.get("STATUS","")).upper()
            s_color, s_icon = _status_color_icon(status)
            acc_n    = row.get("_ACCOUNT","?")
            tbl_n    = row.get("TABLE_NAME","?")
            file_n   = str(row.get("FILE_NAME","?"))
            rows_n   = format_number(
                safe_int(row.get("ROW_COUNT",0)))
            size_n   = format_bytes(
                safe_float(row.get("FILE_SIZE",0)))
            load_t   = str(row.get("LAST_LOAD_TIME",""))[:19]

            st.markdown(
                _file_row(s_icon, s_color, status,
                           file_n, acc_n, tbl_n,
                           rows_n, size_n, load_t),
                unsafe_allow_html=True
            )
    else:
        st.info("No ingestion activity found in selected window.")

# ─── Footer ───────────────────────────────────────────────────────────────────

st.markdown(
    f'<div style="text-align:center;padding:28px 0 10px;'
    f'border-top:1px solid {c("border")};margin-top:32px;">'
    f'<div style="font-size:0.78rem;font-weight:800;'
    f'color:{c("text_primary")};">'
    f'📥 Data Ingestion Center'
    f'&nbsp;·&nbsp;'
    f'<span style="color:{c("pwc_orange")};font-weight:800;'
    f'font-size:0.68rem;text-transform:uppercase;'
    f'letter-spacing:0.12em;">'
    f'Powered By PwC Data &amp; AI</span>'
    f'</div>'
    f'<div style="margin-top:4px;font-size:0.66rem;'
    f'color:{c("text_dim","#5f6b7c")};">'
    f'{len(connected)} environment(s) connected'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True
)