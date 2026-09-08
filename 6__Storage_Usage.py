"""
💾 Storage Usage — Account, Database, Table storage analysis
   with Stage browser and File Upload capabilities.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import time
import tempfile
import os
import math

from snowflake_connector import SnowflakeConnectionManager
from theme import (
    inject_css, COLORS, CHART_COLORS, get_env_color,
    pwc_header, section_header,
)

# ─── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Storage Usage · PwC",
    page_icon="💾",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# ─── Safe color lookup ────────────────────────────────────────────────────────

def c(key: str, fallback: str = "#888888") -> str:
    return COLORS.get(key, fallback)

# ─── Safe HTML builders ───────────────────────────────────────────────────────

def _kpi(icon, value, label, color, sub=""):
    sub_html = ""
    if sub:
        sub_html = (
            f'<div style="margin-top:6px;font-size:0.72rem;'
            f'color:{c("text_secondary")};">{sub}</div>')
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
        f'</div>')


def _info_box(text: str, accent: str = None) -> str:
    accent = accent or c("blue")
    return (
        f'<div style="background:rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-left:4px solid {accent};'
        f'border-radius:14px;padding:14px 16px;'
        f'margin-bottom:14px;">'
        f'<div style="font-size:0.82rem;'
        f'color:{c("text_secondary")};line-height:1.6;">'
        f'{text}</div>'
        f'</div>')


def _step(num: int, title: str) -> str:
    return (
        f'<div style="display:flex;align-items:center;'
        f'gap:10px;margin-bottom:14px;margin-top:14px;">'
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
        f'</div>')


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
        f'{sql}</div>')


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
        f'color:{c("text_muted")};">{count} {label}</span>'
        f'</div>')


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
        f'</div>')


def _stat_cell(value, label, color) -> str:
    return (
        f'<div style="text-align:center;">'
        f'<div style="font-family:JetBrains Mono,monospace;'
        f'font-size:1.2rem;font-weight:700;color:{color};">'
        f'{value}</div>'
        f'<div style="font-size:0.6rem;'
        f'color:{c("text_muted")};'
        f'text-transform:uppercase;">{label}</div>'
        f'</div>')


def _upload_card(icon, title, desc, color) -> str:
    return (
        f'<div style="background:linear-gradient('
        f'180deg,rgba(255,255,255,0.02),'
        f'rgba(255,255,255,0.00)),rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-left:4px solid {color};'
        f'border-radius:14px;padding:18px;'
        f'margin-bottom:12px;'
        f'box-shadow:0 12px 24px rgba(0,0,0,0.14);">'
        f'<div style="display:flex;align-items:center;'
        f'gap:10px;margin-bottom:8px;">'
        f'<span style="font-size:1.2rem;">{icon}</span>'
        f'<span style="font-size:0.92rem;font-weight:800;'
        f'color:{c("text_primary")};">{title}</span>'
        f'</div>'
        f'<div style="font-size:0.76rem;'
        f'color:{c("text_muted")};line-height:1.5;">'
        f'{desc}</div>'
        f'</div>')


def _file_item(fname, fsize, ftype, status_icon,
               status_text, status_color) -> str:
    return (
        f'<div style="display:flex;align-items:center;'
        f'justify-content:space-between;'
        f'padding:10px 14px;'
        f'background:rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-radius:10px;margin-bottom:6px;">'
        f'<div style="display:flex;align-items:center;'
        f'gap:10px;flex:1;min-width:0;">'
        f'<span style="font-size:1rem;">'
        f'{_file_icon(ftype)}</span>'
        f'<div style="min-width:0;">'
        f'<div style="font-weight:600;'
        f'color:{c("text_primary")};font-size:0.82rem;'
        f'overflow:hidden;text-overflow:ellipsis;'
        f'white-space:nowrap;">{fname}</div>'
        f'<div style="font-size:0.68rem;'
        f'color:{c("text_muted")};">'
        f'{format_bytes(fsize)} · {ftype}</div>'
        f'</div>'
        f'</div>'
        f'<div style="display:flex;align-items:center;'
        f'gap:8px;flex-shrink:0;">'
        f'<span style="font-size:0.8rem;">'
        f'{status_icon}</span>'
        f'<span style="font-size:0.72rem;font-weight:700;'
        f'color:{status_color};">{status_text}</span>'
        f'</div>'
        f'</div>')


def _file_icon(ftype: str) -> str:
    ftype = ftype.lower()
    icons = {
        "csv": "📊", "json": "📋", "parquet": "🗂️",
        "avro": "🔷", "orc": "🔶", "xml": "📄",
        "gz": "📦", "gzip": "📦", "bz2": "📦",
        "zst": "📦", "zip": "📦", "txt": "📝",
        "tsv": "📊", "log": "📝", "yaml": "⚙️",
        "yml": "⚙️", "sql": "🗃️",
        "py": "🐍", "ipynb": "🐍",
        "r": "📈", "rmd": "📈",
        "sh": "🖥️", "bat": "🖥️",
        "jar": "☕", "class": "☕",
        "sas": "📊", "sas7bdat": "📊",
        "xls": "📗", "xlsx": "📗", "xlsm": "📗",
        "doc": "📘", "docx": "📘", "pdf": "📕",
        "png": "🖼️", "jpg": "🖼️", "jpeg": "🖼️",
        "gif": "🖼️", "svg": "🖼️",
        "mp4": "🎬", "mp3": "🎵", "wav": "🎵",
    }
    return icons.get(ftype, "📁")


def _upload_summary(total_files, success, failed,
                     total_bytes, elapsed) -> str:
    sc_ = c("green") if failed == 0 else c("yellow")
    fc_ = c("red")   if failed > 0  else c("green")
    return (
        f'<div style="background:linear-gradient('
        f'180deg,rgba(255,255,255,0.02),'
        f'rgba(255,255,255,0.00)),rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-top:3px solid {sc_};'
        f'border-radius:14px;padding:18px;'
        f'margin-top:14px;'
        f'box-shadow:0 14px 28px rgba(0,0,0,0.16);">'
        f'<div style="font-weight:800;'
        f'color:{c("text_primary")};'
        f'margin-bottom:12px;font-size:0.95rem;">'
        f'📊 Upload Summary</div>'
        f'<div style="display:grid;'
        f'grid-template-columns:repeat(5,1fr);'
        f'gap:12px;text-align:center;">'
        + _stat_cell(str(total_files), "Total Files", c("pwc_orange"))
        + _stat_cell(str(success),     "Success",     sc_)
        + _stat_cell(str(failed),      "Failed",      fc_)
        + _stat_cell(format_bytes(total_bytes), "Data", c("blue"))
        + _stat_cell(f"{elapsed:.1f}s", "Duration", c("cyan"))
        + f'</div></div>')


def _stage_card(sname, sdb, ssc, stype, surl,
                env_color) -> str:
    is_int = "INTERNAL" in str(stype).upper()
    icon   = "🏠" if is_int else "☁️"
    label  = "Internal" if is_int else "External"
    url_display = surl if surl else "Internal Stage"
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
        f'justify-content:space-between;margin-bottom:8px;">'
        f'<div style="font-weight:700;'
        f'color:{c("text_primary")};font-size:0.88rem;">'
        f'{icon} {sname}</div>'
        f'<span style="font-size:0.65rem;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.5px;'
        f'color:{env_color};background:{env_color}10;'
        f'border:1px solid {env_color}33;'
        f'padding:2px 8px;border-radius:6px;">'
        f'{label}</span>'
        f'</div>'
        f'<div style="font-size:0.7rem;'
        f'color:{c("text_muted")};margin-bottom:3px;'
        f'font-family:JetBrains Mono,monospace;'
        f'overflow:hidden;text-overflow:ellipsis;'
        f'white-space:nowrap;">📍 {url_display}</div>'
        f'<div style="font-size:0.7rem;'
        f'color:{c("text_muted")};">'
        f'🗄️ {sdb}.{ssc}</div>'
        f'</div>')


# ─── Utility functions ────────────────────────────────────────────────────────

def safe_int(val, default=0):
    try:
        if val is None:
            return default
        if isinstance(val, float) and (
                math.isnan(val) or math.isinf(val)):
            return default
        return int(val)
    except (ValueError, TypeError):
        return default


def safe_float(val, default=0.0):
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
    for u in ["B", "KB", "MB", "GB", "TB"]:
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


def run_query(account, sql):
    return manager.execute_query(account, sql)


def run_statement(account, sql):
    conn = manager.get_connection(account)
    if not conn:
        return False, f"Not connected to {account}"
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cols = ([d[0] for d in cur.description]
                if cur.description else [])
        cur.close()
        return True, (pd.DataFrame(rows, columns=cols)
                      if cols else pd.DataFrame())
    except Exception as e:
        return False, str(e)


def put_file_to_stage(account, local_path, stage_path,
                       auto_compress=True, overwrite=False,
                       parallel=4):
    conn = manager.get_connection(account)
    if not conn:
        return False, f"Not connected to {account}", None
    try:
        cur = conn.cursor()
        compress_opt  = ("AUTO_COMPRESS=TRUE"
                          if auto_compress else
                          "AUTO_COMPRESS=FALSE")
        overwrite_opt = ("OVERWRITE=TRUE"
                          if overwrite else
                          "OVERWRITE=FALSE")
        # Snowflake PUT requires forward slashes
        safe_path = local_path.replace("\\", "/")
        put_sql = (
            f"PUT 'file://{safe_path}' '{stage_path}' "
            f"{compress_opt} {overwrite_opt} "
            f"PARALLEL={parallel}")
        cur.execute(put_sql)
        rows = cur.fetchall()
        cols = ([d[0] for d in cur.description]
                if cur.description else [])
        cur.close()
        result_df = (pd.DataFrame(rows, columns=cols)
                      if cols else pd.DataFrame())
        if not result_df.empty:
            status_col = next(
                (col for col in ["status", "STATUS"]
                 if col in result_df.columns), None)
            if status_col:
                statuses = result_df[status_col].str.upper().tolist()
                if any("ERROR" in s for s in statuses):
                    return False, "Upload had errors", result_df
                return True, "Upload successful", result_df
        return True, "Upload completed", result_df
    except Exception as e:
        return False, str(e), None


# ─── Cached Data Fetchers ─────────────────────────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def fetch_account_storage(_mid, account):
    try:
        df = run_query(account, """
            SELECT
                USAGE_DATE,
                STORAGE_BYTES / (1024*1024*1024)    AS STORAGE_GB,
                STAGE_BYTES / (1024*1024*1024)      AS STAGE_GB,
                FAILSAFE_BYTES / (1024*1024*1024)   AS FAILSAFE_GB,
                (STORAGE_BYTES + STAGE_BYTES + FAILSAFE_BYTES)
                    / (1024*1024*1024)               AS TOTAL_GB
            FROM SNOWFLAKE.ACCOUNT_USAGE.STORAGE_USAGE
            WHERE USAGE_DATE >= DATEADD('day', -90, CURRENT_DATE())
            ORDER BY USAGE_DATE DESC
        """)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def fetch_db_storage(_mid, account):
    try:
        df = run_query(account, """
            SELECT
                DATABASE_NAME,
                AVERAGE_DATABASE_BYTES / (1024*1024*1024)
                    AS AVG_DB_GB,
                AVERAGE_FAILSAFE_BYTES / (1024*1024*1024)
                    AS AVG_FAILSAFE_GB,
                (AVERAGE_DATABASE_BYTES + AVERAGE_FAILSAFE_BYTES)
                    / (1024*1024*1024)
                    AS TOTAL_GB
            FROM SNOWFLAKE.ACCOUNT_USAGE
                     .DATABASE_STORAGE_USAGE_HISTORY
            WHERE USAGE_DATE = CURRENT_DATE() - 1
            ORDER BY AVERAGE_DATABASE_BYTES DESC
        """)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def fetch_table_storage(_mid, account):
    try:
        df = run_query(account, """
            SELECT
                TABLE_CATALOG      AS DATABASE_NAME,
                TABLE_SCHEMA       AS SCHEMA_NAME,
                TABLE_NAME,
                ROW_COUNT,
                ACTIVE_BYTES       / (1024*1024) AS ACTIVE_MB,
                TIME_TRAVEL_BYTES  / (1024*1024) AS TIME_TRAVEL_MB,
                FAILSAFE_BYTES     / (1024*1024) AS FAILSAFE_MB,
                RETAINED_FOR_CLONE_BYTES / (1024*1024) AS CLONE_MB,
                (ACTIVE_BYTES + TIME_TRAVEL_BYTES
                 + FAILSAFE_BYTES + RETAINED_FOR_CLONE_BYTES)
                    / (1024*1024) AS TOTAL_MB,
                TABLE_CREATED,
                LAST_ALTERED
            FROM SNOWFLAKE.ACCOUNT_USAGE.TABLE_STORAGE_METRICS
            WHERE ACTIVE_BYTES > 0
            ORDER BY ACTIVE_BYTES DESC
            LIMIT 500
        """)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def fetch_stages(_mid, account):
    try:
        df = run_query(account, "SHOW STAGES IN ACCOUNT")
        return df if df is not None else pd.DataFrame()
    except Exception:
        try:
            df = run_query(account, "SHOW STAGES")
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
        f'color:{c("text_primary")};">💾 Storage Usage</div>'
        f'<div style="font-size:0.56rem;'
        f'color:{c("pwc_orange")};font-weight:800;'
        f'text-transform:uppercase;letter-spacing:0.18em;">'
        f'PwC Data &amp; AI</div>'
        f'</div>',
        unsafe_allow_html=True)

    for acc in connected:
        color_acc = get_env_color(acc)
        st.markdown(
            f'<div style="display:flex;align-items:center;'
            f'gap:8px;padding:6px 10px;border-radius:10px;'
            f'margin-bottom:4px;">'
            f'<div style="width:8px;height:8px;'
            f'border-radius:50%;background:{color_acc};'
            f'box-shadow:0 0 6px {color_acc};'
            f'flex-shrink:0;"></div>'
            f'<span style="font-size:0.82rem;font-weight:600;'
            f'color:{color_acc};">{acc}</span>'
            f'</div>',
            unsafe_allow_html=True)

    st.markdown("---")

    selected_accounts = st.multiselect(
        "Environments",
        connected,
        default=connected,
        key="stor_accounts")

    if st.button("🔄 Refresh Data",
                  use_container_width=True,
                  key="stor_refresh"):
        st.cache_data.clear()
        st.rerun()

# ─── Header ───────────────────────────────────────────────────────────────────

pwc_header(
    "Storage Usage",
    subtitle="Account, database & table storage analysis · "
             "Stage browser · File upload"
)

if not connected:
    st.markdown(
        _alert("Connect at least one account.",
               c("pwc_orange"), "🔌"),
        unsafe_allow_html=True)
    st.stop()

# ─── Tabs ─────────────────────────────────────────────────────────────────────

(tab_account, tab_database, tab_tables,
 tab_stages, tab_upload) = st.tabs([
    "📊  Account Storage",
    "📁  Database Storage",
    "📋  Table Storage",
    "🗄️  Stages",
    "📤  File Upload",
])

# ═══════════════════════════════════════════════════════
# TAB 1 — ACCOUNT STORAGE
# ═══════════════════════════════════════════════════════

with tab_account:
    section_header("ACCOUNT-LEVEL STORAGE USAGE")

    all_storage = []
    for acc in selected_accounts:
        df = fetch_account_storage(id(manager), acc)
        if not df.empty:
            all_storage.append(df)

    if all_storage:
        storage_df = pd.concat(all_storage, ignore_index=True)
        for col in ["STORAGE_GB", "STAGE_GB",
                     "FAILSAFE_GB", "TOTAL_GB"]:
            if col in storage_df.columns:
                storage_df[col] = (
                    pd.to_numeric(storage_df[col], errors="coerce")
                    .fillna(0))
        if "USAGE_DATE" in storage_df.columns:
            storage_df["USAGE_DATE"] = pd.to_datetime(
                storage_df["USAGE_DATE"], errors="coerce")

        # Latest per account
        latest = (storage_df
                   .sort_values("USAGE_DATE")
                   .groupby("_ACCOUNT")
                   .last()
                   .reset_index())

        # KPI row
        total_all = safe_float(latest["TOTAL_GB"].sum())
        total_db  = safe_float(latest["STORAGE_GB"].sum())
        total_stg = safe_float(latest["STAGE_GB"].sum())
        total_fs  = safe_float(latest["FAILSAFE_GB"].sum())

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(
                _kpi("💾", f"{total_all:.1f} GB",
                     "Total Storage", c("pwc_orange")),
                unsafe_allow_html=True)
        with k2:
            st.markdown(
                _kpi("🗄️", f"{total_db:.1f} GB",
                     "Database", c("blue")),
                unsafe_allow_html=True)
        with k3:
            st.markdown(
                _kpi("📦", f"{total_stg:.1f} GB",
                     "Stage", c("cyan")),
                unsafe_allow_html=True)
        with k4:
            st.markdown(
                _kpi("🛡️", f"{total_fs:.1f} GB",
                     "Failsafe", c("yellow")),
                unsafe_allow_html=True)

        st.markdown('<div style="height:12px;"></div>',
                     unsafe_allow_html=True)

        # Per-environment cards
        for acc in selected_accounts:
            env_color = get_env_color(acc)
            acc_data  = latest[latest["_ACCOUNT"] == acc]
            if acc_data.empty:
                continue
            row = acc_data.iloc[0]
            st.markdown(
                f'<div style="background:linear-gradient('
                f'180deg,rgba(255,255,255,0.02),'
                f'rgba(255,255,255,0.00)),rgba(19,26,36,0.9);'
                f'border:1px solid rgba(255,255,255,0.07);'
                f'border-left:4px solid {env_color};'
                f'border-radius:18px;padding:18px;'
                f'box-shadow:0 16px 30px rgba(0,0,0,0.18);'
                f'margin-bottom:12px;">'
                f'<div style="font-size:0.9rem;font-weight:800;'
                f'color:{env_color};margin-bottom:12px;">'
                f'{acc}</div>'
                f'<div style="display:grid;'
                f'grid-template-columns:repeat(4,1fr);'
                f'gap:12px;">'
                + _stat_cell(f'{safe_float(row.get("TOTAL_GB",0)):.2f} GB',
                              "Total", env_color)
                + _stat_cell(f'{safe_float(row.get("STORAGE_GB",0)):.2f} GB',
                              "Database", c("blue"))
                + _stat_cell(f'{safe_float(row.get("STAGE_GB",0)):.2f} GB',
                              "Stage", c("cyan"))
                + _stat_cell(f'{safe_float(row.get("FAILSAFE_GB",0)):.2f} GB',
                              "Failsafe", c("yellow"))
                + f'</div></div>',
                unsafe_allow_html=True)

        st.markdown('<div style="height:12px;"></div>',
                     unsafe_allow_html=True)

        # Trend chart
        cmap = {n: get_env_color(n)
                for n in storage_df["_ACCOUNT"].unique()}

        fig = px.line(
            storage_df, x="USAGE_DATE", y="TOTAL_GB",
            color="_ACCOUNT",
            color_discrete_map=cmap,
            title="Total Storage Trend (Last 90 Days)",
            height=380)
        fig.update_traces(line=dict(width=2))
        fig.update_layout(
            xaxis_title="", yaxis_title="GB",
            legend_title_text="")
        st.plotly_chart(fig, use_container_width=True,
                         key="stor_trend")

        # Breakdown charts
        bc1, bc2 = st.columns(2)
        with bc1:
            melted = latest.melt(
                id_vars=["_ACCOUNT"],
                value_vars=["STORAGE_GB", "STAGE_GB",
                             "FAILSAFE_GB"],
                var_name="Type", value_name="GB")
            fig2 = px.bar(
                melted, x="_ACCOUNT", y="GB",
                color="Type", barmode="stack",
                title="Storage Breakdown by Type",
                height=380,
                color_discrete_sequence=CHART_COLORS)
            fig2.update_layout(
                xaxis_title="", legend_title_text="")
            st.plotly_chart(fig2, use_container_width=True,
                             key="stor_breakdown")

        with bc2:
            for acc in selected_accounts:
                acc_lat = latest[latest["_ACCOUNT"] == acc]
                if acc_lat.empty:
                    continue
                row = acc_lat.iloc[0]
                fig3 = px.pie(
                    values=[
                        safe_float(row.get("STORAGE_GB", 0)),
                        safe_float(row.get("STAGE_GB", 0)),
                        safe_float(row.get("FAILSAFE_GB", 0)),
                    ],
                    names=["Database", "Stage", "Failsafe"],
                    title=f"Distribution — {acc}",
                    height=300,
                    hole=0.5,
                    color_discrete_sequence=CHART_COLORS)
                st.plotly_chart(fig3, use_container_width=True,
                                 key=f"stor_pie_{acc}")
    else:
        st.info("No storage usage data available.")


# ═══════════════════════════════════════════════════════
# TAB 2 — DATABASE STORAGE
# ═══════════════════════════════════════════════════════

with tab_database:
    section_header("DATABASE-LEVEL STORAGE")

    all_db = []
    for acc in selected_accounts:
        df = fetch_db_storage(id(manager), acc)
        if not df.empty:
            all_db.append(df)

    if all_db:
        db_df = pd.concat(all_db, ignore_index=True)
        for col in ["AVG_DB_GB", "AVG_FAILSAFE_GB", "TOTAL_GB"]:
            if col in db_df.columns:
                db_df[col] = (
                    pd.to_numeric(db_df[col], errors="coerce")
                    .fillna(0))

        cmap_db = {n: get_env_color(n)
                    for n in db_df["_ACCOUNT"].unique()}

        fig = px.bar(
            db_df.nlargest(20, "TOTAL_GB"),
            x="DATABASE_NAME", y="TOTAL_GB",
            color="_ACCOUNT",
            color_discrete_map=cmap_db,
            title="Top 20 Databases by Storage (GB)",
            height=400)
        fig.update_layout(xaxis_tickangle=-45,
                           xaxis_title="",
                           legend_title_text="")
        st.plotly_chart(fig, use_container_width=True,
                         key="db_stor_bar")

        st.dataframe(
            db_df.rename(columns={
                "_ACCOUNT":        "Account",
                "DATABASE_NAME":   "Database",
                "AVG_DB_GB":       "Database GB",
                "AVG_FAILSAFE_GB": "Failsafe GB",
                "TOTAL_GB":        "Total GB",
            }),
            use_container_width=True,
            hide_index=True,
            height=400)
    else:
        st.info("No database storage data available.")


# ═══════════════════════════════════════════════════════
# TAB 3 — TABLE STORAGE
# ═══════════════════════════════════════════════════════

with tab_tables:
    section_header("TABLE-LEVEL STORAGE")

    st.markdown(
        _info_box(
            "Showing top 500 tables by active storage "
            "per environment. Large accounts may take "
            "a moment to load.",
            accent=c("blue")),
        unsafe_allow_html=True)

    for acc in selected_accounts:
        env_color = get_env_color(acc)
        tdf = fetch_table_storage(id(manager), acc)

        st.markdown(
            _env_header(acc, len(tdf), "tables", env_color),
            unsafe_allow_html=True)

        if tdf.empty:
            st.info(f"No table storage data for {acc}.")
            continue

        for col in ["ACTIVE_MB", "TIME_TRAVEL_MB",
                     "FAILSAFE_MB", "CLONE_MB",
                     "TOTAL_MB", "ROW_COUNT"]:
            if col in tdf.columns:
                tdf[col] = (
                    pd.to_numeric(tdf[col], errors="coerce")
                    .fillna(0))

        tm1, tm2, tm3 = st.columns(3)
        tm1.metric("Tables", f"{len(tdf):,}")
        tm2.metric("Total Size",
                    f"{safe_float(tdf['TOTAL_MB'].sum()):.0f} MB")
        tm3.metric("Avg Table Size",
                    f"{safe_float(tdf['TOTAL_MB'].mean()):.2f} MB")

        # Treemap
        if ({"DATABASE_NAME", "SCHEMA_NAME", "TABLE_NAME", "TOTAL_MB"}
                .issubset(tdf.columns)):
            fig_tm = px.treemap(
                tdf.head(100),
                path=["DATABASE_NAME", "SCHEMA_NAME",
                       "TABLE_NAME"],
                values="TOTAL_MB",
                title=f"Table Size Treemap — {acc} (Top 100)",
                height=500,
                color="TOTAL_MB",
                color_continuous_scale=[
                    c("bg_primary", "#07090d"),
                    c("pwc_orange"),
                    c("pwc_gold")])
            fig_tm.update_layout(
                coloraxis_showscale=False)
            st.plotly_chart(fig_tm, use_container_width=True,
                             key=f"tbl_tree_{acc}")

        st.dataframe(
            tdf.rename(columns={
                "DATABASE_NAME":  "Database",
                "SCHEMA_NAME":    "Schema",
                "TABLE_NAME":     "Table",
                "ROW_COUNT":      "Rows",
                "ACTIVE_MB":      "Active MB",
                "TIME_TRAVEL_MB": "Time Travel MB",
                "FAILSAFE_MB":    "Failsafe MB",
                "CLONE_MB":       "Clone MB",
                "TOTAL_MB":       "Total MB",
            }),
            use_container_width=True,
            hide_index=True,
            height=400)

        st.markdown("---")


# ═══════════════════════════════════════════════════════
# TAB 4 — STAGES
# ═══════════════════════════════════════════════════════

with tab_stages:
    section_header("STAGE BROWSER")

    for acc in selected_accounts:
        env_color  = get_env_color(acc)
        stages_df  = fetch_stages(id(manager), acc)

        st.markdown(
            _env_header(acc, len(stages_df),
                         "stage(s)", env_color),
            unsafe_allow_html=True)

        if stages_df.empty:
            st.info(f"No stages found for {acc}.")
            continue

        name_col = next(
            (col for col in ["name", "NAME"]
             if col in stages_df.columns), None)
        url_col  = next(
            (col for col in ["url", "URL"]
             if col in stages_df.columns), None)
        db_col   = next(
            (col for col in ["database_name", "DATABASE_NAME"]
             if col in stages_df.columns), None)
        sc_col   = next(
            (col for col in ["schema_name", "SCHEMA_NAME"]
             if col in stages_df.columns), None)
        type_col = next(
            (col for col in ["type", "TYPE"]
             if col in stages_df.columns), None)

        stage_cols = st.columns(3)
        for idx, (_, row) in enumerate(stages_df.iterrows()):
            sn = row.get(name_col, "?") if name_col else "?"
            su = row.get(url_col,  "")  if url_col  else ""
            sd = row.get(db_col,   "?") if db_col   else "?"
            ss = row.get(sc_col,   "?") if sc_col   else "?"
            st_ = row.get(type_col,"?") if type_col else "?"
            with stage_cols[idx % 3]:
                st.markdown(
                    _stage_card(sn, sd, ss, st_, su, env_color),
                    unsafe_allow_html=True)

        # List files in stage
        with st.expander(f"📂 Browse Files — {acc}"):
            if name_col and not stages_df.empty:
                stage_list = stages_df[name_col].tolist()
                sel_stage  = st.selectbox(
                    "Select Stage", stage_list,
                    key=f"stg_list_{acc}")
                pattern = st.text_input(
                    "File Pattern (optional)",
                    placeholder="*.csv",
                    key=f"stg_patt_{acc}")
                if st.button("📂 List Files",
                              key=f"stg_btn_{acc}",
                              type="primary"):
                    with st.spinner("Listing files…"):
                        list_sql = f'LIST @"{sel_stage}"'
                        if pattern:
                            list_sql += f" PATTERN='{pattern}'"
                        list_df = run_query(acc, list_sql)
                    if list_df is not None and not list_df.empty:
                        if "size" in list_df.columns:
                            list_df["size"] = pd.to_numeric(
                                list_df["size"],
                                errors="coerce").fillna(0)
                            lc1, lc2, lc3 = st.columns(3)
                            lc1.metric("Files", len(list_df))
                            lc2.metric("Total Size",
                                        format_bytes(
                                            list_df["size"].sum()))
                            lc3.metric("Avg Size",
                                        format_bytes(
                                            list_df["size"].mean()))
                        st.dataframe(list_df,
                                      use_container_width=True,
                                      hide_index=True,
                                      height=350)
                    else:
                        st.info("No files found.")

        st.markdown("---")


# ═══════════════════════════════════════════════════════
# TAB 5 — FILE UPLOAD
# ═══════════════════════════════════════════════════════

with tab_upload:
    section_header("UPLOAD FILES TO STAGES")

    st.markdown(
        _info_box(
            "<b style='color:#D04A02;'>PUT</b> files from your "
            "local machine directly into Snowflake internal or "
            "external stages. Supports CSV, JSON, Parquet, Avro, "
            "ORC, XML and compressed archives.",
            accent=c("pwc_orange")),
        unsafe_allow_html=True)

    # Sub-tabs
    (up_single, up_bulk, up_history) = st.tabs([
        "📄  Single File",
        "📦  Bulk Upload",
        "📜  Upload History",
    ])

    # ── Helper: build stage option list ───────────────
    def _build_stage_options(account):
        sdf = fetch_stages(id(manager), account)
        nc = next((col for col in ["name", "NAME"]
                    if col in sdf.columns), None
        ) if not sdf.empty else None
        dbc = next((col for col in [
            "database_name", "DATABASE_NAME"]
            if col in sdf.columns), None
        ) if not sdf.empty else None
        scc = next((col for col in [
            "schema_name", "SCHEMA_NAME"]
            if col in sdf.columns), None
        ) if not sdf.empty else None
        tc = next((col for col in ["type", "TYPE"]
                    if col in sdf.columns), None
        ) if not sdf.empty else None
        uc = next((col for col in ["url", "URL"]
                    if col in sdf.columns), None
        ) if not sdf.empty else None

        options = []
        if nc and not sdf.empty:
            for _, row in sdf.iterrows():
                sn  = row.get(nc,  "?")
                sd  = row.get(dbc, "?") if dbc else "?"
                ss  = row.get(scc, "?") if scc else "?"
                st_ = row.get(tc,  "?") if tc  else "?"
                su  = row.get(uc,  "")  if uc  else ""
                is_int = "INTERNAL" in str(st_).upper()
                icon = "🏠" if is_int else "☁️"
                options.append({
                    "label": f"{icon} {sd}.{ss}.{sn}",
                    "fqn":   f'@"{sd}"."{ss}"."{sn}"',
                    "name":  sn, "type": st_, "url": su,
                })
        return options

    UPLOAD_TYPES = [
        "csv", "json", "parquet", "avro", "orc", "xml",
        "txt", "tsv", "log", "gz", "gzip", "bz2", "zst",
        "zip", "sql", "yaml", "yml", "py", "ipynb",
        "sh", "bat", "jar", "class", "r", "rmd",
        "sas", "sas7bdat", "xls", "xlsx", "xlsm",
        "doc", "docx", "pdf", "png", "jpg", "jpeg",
        "gif", "svg", "mp4", "mp3", "wav",
    ]

    # ────────────────────────────────────────────────────
    # SINGLE FILE UPLOAD
    # ────────────────────────────────────────────────────
    with up_single:
        st.markdown(
            _upload_card(
                "📄", "Single File Upload",
                "Upload one file with full control over "
                "destination, compression, and overwrite.",
                c("blue")),
            unsafe_allow_html=True)

        st.markdown(_step(1, "Select Target"),
                     unsafe_allow_html=True)

        s1, s2 = st.columns(2)
        with s1:
            up_acc = st.selectbox(
                "Account", selected_accounts,
                key="up_s_acc")
        with s2:
            stage_opts = _build_stage_options(up_acc)
            if stage_opts:
                sel_idx = st.selectbox(
                    "Target Stage",
                    range(len(stage_opts)),
                    format_func=lambda i: stage_opts[i]["label"],
                    key="up_s_stage")
                sel_stage = stage_opts[sel_idx]
            else:
                st.warning("No stages found.")
                sel_stage = None

        if sel_stage:
            stage_type = str(sel_stage.get("type", "")).upper()
            is_internal = "INTERNAL" in stage_type

            st.markdown(
                f'<div style="background:rgba(19,26,36,0.9);'
                f'border:1px solid rgba(255,255,255,0.07);'
                f'border-radius:10px;padding:10px 14px;'
                f'margin:8px 0;">'
                f'<span style="font-size:0.75rem;'
                f'font-weight:700;color:{c("blue")};">'
                f'{"🏠 Internal" if is_internal else "☁️ External"}'
                f' Stage</span>'
                f'<span style="font-size:0.68rem;'
                f'color:{c("text_muted")};'
                f'font-family:JetBrains Mono,monospace;'
                f'margin-left:10px;">'
                f'{sel_stage["fqn"]}</span>'
                f'</div>',
                unsafe_allow_html=True)

            sub_path = st.text_input(
                "Subdirectory (optional)",
                placeholder="data/2024/raw/",
                key="up_s_sub")

            st.markdown(_step(2, "Upload Options"),
                         unsafe_allow_html=True)

            o1, o2, o3, o4 = st.columns(4)
            with o1:
                auto_compress = st.checkbox(
                    "Auto Compress", value=True,
                    key="up_s_compress")
            with o2:
                overwrite = st.checkbox(
                    "Overwrite Existing", value=False,
                    key="up_s_overwrite")
            with o3:
                parallel = st.selectbox(
                    "Parallel Threads",
                    [1, 2, 4, 8, 16], index=2,
                    key="up_s_parallel")
            with o4:
                src_compression = st.selectbox(
                    "Source Compression",
                    ["AUTO_DETECT", "GZIP", "BZ2",
                     "BROTLI", "ZSTD", "DEFLATE", "NONE"],
                    key="up_s_src_comp")

            st.markdown(_step(3, "Select File"),
                         unsafe_allow_html=True)

            uploaded_file = st.file_uploader(
                "Choose a file",
                type=UPLOAD_TYPES,
                key="up_s_file")

            if uploaded_file:
                file_ext = (uploaded_file.name.rsplit(".", 1)[-1]
                             if "." in uploaded_file.name
                             else "unknown")

                st.markdown(
                    _file_item(
                        uploaded_file.name,
                        uploaded_file.size,
                        file_ext,
                        "📎", "Ready", c("blue")),
                    unsafe_allow_html=True)

                dest = sel_stage["fqn"]
                if sub_path:
                    dest = f'{dest}/{sub_path.strip().strip("/")}'

                compress_flag = ("AUTO_COMPRESS=TRUE"
                                  if auto_compress else
                                  "AUTO_COMPRESS=FALSE")
                overwrite_flag = ("OVERWRITE=TRUE"
                                   if overwrite else
                                   "OVERWRITE=FALSE")
                src_flag = (
                    f"SOURCE_COMPRESSION={src_compression}"
                    if src_compression != "AUTO_DETECT" else "")

                put_preview = (
                    f"PUT 'file://{uploaded_file.name}' "
                    f"'{dest}'\n"
                    f"    {compress_flag}\n"
                    f"    {overwrite_flag}\n"
                    f"    PARALLEL={parallel}")
                if src_flag:
                    put_preview += f"\n    {src_flag}"
                put_preview += ";"

                with st.expander("🔍 Preview PUT Command"):
                    st.markdown(
                        _sql_block(put_preview),
                        unsafe_allow_html=True)

                if st.button(
                    f"📤 Upload {uploaded_file.name}",
                    type="primary",
                    key="btn_s_upload"
                ):
                    with tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix=f".{file_ext}"
                    ) as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name

                    try:
                        with st.status(
                            f"Uploading {uploaded_file.name}…",
                            expanded=True
                        ) as upload_status:
                            st.write(
                                f"📁 **{uploaded_file.name}** "
                                f"({format_bytes(uploaded_file.size)})")
                            st.write(f"🎯 Destination: `{dest}`")
                            st.write("⬆️ Uploading…")

                            t0 = time.time()
                            ok, msg, res_df = put_file_to_stage(
                                up_acc,
                                tmp_path.replace("\\", "/"),
                                dest,
                                auto_compress=auto_compress,
                                overwrite=overwrite,
                                parallel=parallel)
                            elapsed = time.time() - t0

                            upload_status.update(
                                label=("✅ Upload complete!"
                                        if ok else
                                        "❌ Upload failed"),
                                state="complete" if ok else "error",
                                expanded=False)

                        if ok:
                            st.markdown(
                                _upload_summary(
                                    1, 1, 0,
                                    uploaded_file.size, elapsed),
                                unsafe_allow_html=True)
                            st.markdown(
                                _file_item(
                                    uploaded_file.name,
                                    uploaded_file.size,
                                    file_ext,
                                    "✅", "Uploaded", c("green")),
                                unsafe_allow_html=True)

                            if (res_df is not None
                                    and not res_df.empty):
                                with st.expander("📋 PUT Result"):
                                    st.dataframe(
                                        res_df,
                                        use_container_width=True,
                                        hide_index=True)

                            if "upload_history" not in st.session_state:
                                st.session_state.upload_history = []
                            st.session_state.upload_history.append({
                                "file": uploaded_file.name,
                                "size": uploaded_file.size,
                                "stage": dest,
                                "account": up_acc,
                                "status": "SUCCESS",
                                "time": datetime.datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S"),
                                "duration": f"{elapsed:.1f}s",
                            })
                        else:
                            st.error(f"❌ {msg}")
                            st.markdown(
                                _file_item(
                                    uploaded_file.name,
                                    uploaded_file.size,
                                    file_ext,
                                    "❌", "Failed", c("red")),
                                unsafe_allow_html=True)

                            if (res_df is not None
                                    and not res_df.empty):
                                st.dataframe(
                                    res_df,
                                    use_container_width=True,
                                    hide_index=True)

                            if "upload_history" not in st.session_state:
                                st.session_state.upload_history = []
                            st.session_state.upload_history.append({
                                "file": uploaded_file.name,
                                "size": uploaded_file.size,
                                "stage": dest,
                                "account": up_acc,
                                "status": f"FAILED: {msg}",
                                "time": datetime.datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S"),
                                "duration": f"{elapsed:.1f}s",
                            })
                    finally:
                        try:
                            os.unlink(tmp_path)
                        except Exception:
                            pass

    # ────────────────────────────────────────────────────
    # BULK UPLOAD
    # ────────────────────────────────────────────────────
    with up_bulk:
        st.markdown(
            _upload_card(
                "📦", "Bulk File Upload",
                "Upload multiple files at once to the same "
                "stage location with progress tracking.",
                c("pwc_orange")),
            unsafe_allow_html=True)

        st.markdown(_step(1, "Select Target"),
                     unsafe_allow_html=True)

        b1, b2 = st.columns(2)
        with b1:
            bk_acc = st.selectbox(
                "Account", selected_accounts,
                key="up_b_acc")
        with b2:
            bk_opts = _build_stage_options(bk_acc)
            if bk_opts:
                bk_sel = st.selectbox(
                    "Target Stage",
                    range(len(bk_opts)),
                    format_func=lambda i: bk_opts[i]["label"],
                    key="up_b_stage")
                bk_stage = bk_opts[bk_sel]
            else:
                st.warning("No stages found.")
                bk_stage = None

        if bk_stage:
            bk_sub = st.text_input(
                "Subdirectory",
                placeholder="bulk/2024/",
                key="up_b_sub")

            st.markdown(_step(2, "Options"),
                         unsafe_allow_html=True)

            bo1, bo2, bo3 = st.columns(3)
            with bo1:
                bk_compress  = st.checkbox(
                    "Auto Compress", value=True,
                    key="up_b_compress")
            with bo2:
                bk_overwrite = st.checkbox(
                    "Overwrite", value=False,
                    key="up_b_overwrite")
            with bo3:
                bk_parallel  = st.selectbox(
                    "Parallel",
                    [1, 2, 4, 8, 16], index=2,
                    key="up_b_parallel")

            st.markdown(_step(3, "Select Files"),
                         unsafe_allow_html=True)

            bulk_files = st.file_uploader(
                "Choose files (multi-select)",
                type=UPLOAD_TYPES,
                accept_multiple_files=True,
                key="up_b_files")

            if bulk_files:
                total_size = sum(f.size for f in bulk_files)

                st.markdown(
                    f'<div style="padding:10px 14px;'
                    f'background:rgba(19,26,36,0.9);'
                    f'border:1px solid rgba(255,255,255,0.07);'
                    f'border-radius:10px;margin:10px 0;">'
                    f'<span style="font-weight:700;'
                    f'color:{c("text_primary")};'
                    f'font-size:0.85rem;">'
                    f'📦 {len(bulk_files)} files selected</span>'
                    f'<span style="margin-left:12px;'
                    f'font-size:0.75rem;'
                    f'color:{c("text_muted")};">'
                    f'{format_bytes(total_size)} total</span>'
                    f'</div>',
                    unsafe_allow_html=True)

                # Preview files
                for f in bulk_files:
                    ext = (f.name.rsplit(".", 1)[-1]
                            if "." in f.name else "unknown")
                    st.markdown(
                        _file_item(
                            f.name, f.size, ext,
                            "📎", "Ready", c("blue")),
                        unsafe_allow_html=True)

                if st.button(
                    f"📤 Upload All {len(bulk_files)} Files",
                    type="primary",
                    key="btn_b_upload"
                ):
                    dest = bk_stage["fqn"]
                    if bk_sub:
                        dest = f'{dest}/{bk_sub.strip().strip("/")}'

                    success_count = 0
                    fail_count    = 0
                    total_bytes   = 0
                    t0 = time.time()

                    progress = st.progress(0, text="Starting…")

                    if "upload_history" not in st.session_state:
                        st.session_state.upload_history = []

                    for idx, f in enumerate(bulk_files):
                        pct = (idx + 1) / len(bulk_files)
                        progress.progress(
                            pct,
                            text=f"Uploading {f.name} "
                                 f"({idx+1}/{len(bulk_files)})…")

                        ext = (f.name.rsplit(".", 1)[-1]
                                if "." in f.name else "unknown")

                        with tempfile.NamedTemporaryFile(
                            delete=False,
                            suffix=f".{ext}"
                        ) as tmp:
                            tmp.write(f.getvalue())
                            tmp_path = tmp.name

                        try:
                            ok, msg, res_df = put_file_to_stage(
                                bk_acc,
                                tmp_path.replace("\\", "/"),
                                dest,
                                auto_compress=bk_compress,
                                overwrite=bk_overwrite,
                                parallel=bk_parallel)

                            if ok:
                                success_count += 1
                                total_bytes += f.size
                                status = "SUCCESS"
                            else:
                                fail_count += 1
                                status = f"FAILED: {msg}"

                            st.session_state.upload_history.append({
                                "file": f.name,
                                "size": f.size,
                                "stage": dest,
                                "account": bk_acc,
                                "status": status,
                                "time": datetime.datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S"),
                                "duration": "",
                            })
                        finally:
                            try:
                                os.unlink(tmp_path)
                            except Exception:
                                pass

                    elapsed = time.time() - t0
                    progress.empty()

                    st.markdown(
                        _upload_summary(
                            len(bulk_files),
                            success_count, fail_count,
                            total_bytes, elapsed),
                        unsafe_allow_html=True)

                    # Show per-file results
                    for f in bulk_files:
                        ext = (f.name.rsplit(".", 1)[-1]
                                if "." in f.name else "unknown")
                        # Find the matching history entry
                        entry = next(
                            (h for h in reversed(
                                st.session_state.upload_history)
                             if h["file"] == f.name),
                            None)
                        if entry and entry["status"] == "SUCCESS":
                            st.markdown(
                                _file_item(
                                    f.name, f.size, ext,
                                    "✅", "Uploaded", c("green")),
                                unsafe_allow_html=True)
                        else:
                            err_msg = (entry["status"]
                                        if entry else "Unknown")
                            st.markdown(
                                _file_item(
                                    f.name, f.size, ext,
                                    "❌", "Failed", c("red")),
                                unsafe_allow_html=True)

    # ────────────────────────────────────────────────────
    # UPLOAD HISTORY
    # ────────────────────────────────────────────────────
    with up_history:
        st.markdown(
            _upload_card(
                "📜", "Upload History",
                "View all file uploads performed in this "
                "session. History is cleared when you "
                "refresh the page.",
                c("cyan")),
            unsafe_allow_html=True)

        history = st.session_state.get("upload_history", [])

        if history:
            # Summary KPIs
            total_h   = len(history)
            success_h = sum(
                1 for h in history
                if h["status"] == "SUCCESS")
            failed_h  = total_h - success_h
            bytes_h   = sum(h["size"] for h in history)

            hk1, hk2, hk3, hk4 = st.columns(4)
            with hk1:
                st.markdown(
                    _kpi("📦", str(total_h),
                         "Total Uploads", c("pwc_orange")),
                    unsafe_allow_html=True)
            with hk2:
                st.markdown(
                    _kpi("✅", str(success_h),
                         "Successful", c("green")),
                    unsafe_allow_html=True)
            with hk3:
                st.markdown(
                    _kpi("❌", str(failed_h),
                         "Failed", c("red")),
                    unsafe_allow_html=True)
            with hk4:
                st.markdown(
                    _kpi("💾", format_bytes(bytes_h),
                         "Data Uploaded", c("blue")),
                    unsafe_allow_html=True)

            st.markdown('<div style="height:12px;"></div>',
                         unsafe_allow_html=True)

            # History table
            hist_df = pd.DataFrame(history)
            hist_df = hist_df.sort_values(
                "time", ascending=False)

            # Color-code status column
            st.dataframe(
                hist_df.rename(columns={
                    "file":     "File",
                    "size":     "Size (bytes)",
                    "stage":    "Stage",
                    "account":  "Account",
                    "status":   "Status",
                    "time":     "Timestamp",
                    "duration": "Duration",
                }),
                use_container_width=True,
                hide_index=True,
                height=450)

            # Per-file visual list
            section_header("DETAILED FILE LIST")

            for h in reversed(history):
                ext = (h["file"].rsplit(".", 1)[-1]
                        if "." in h["file"] else "unknown")
                is_ok = h["status"] == "SUCCESS"
                st.markdown(
                    _file_item(
                        h["file"], h["size"], ext,
                        "✅" if is_ok else "❌",
                        "Uploaded" if is_ok else "Failed",
                        c("green") if is_ok else c("red")),
                    unsafe_allow_html=True)

            st.markdown('<div style="height:12px;"></div>',
                         unsafe_allow_html=True)

            # Download history
            csv_hist = hist_df.to_csv(index=False)
            st.download_button(
                "📥 Download Upload History",
                data=csv_hist,
                file_name=(
                    f"upload_history_"
                    f"{datetime.date.today()}.csv"),
                mime="text/csv",
                key="dl_upload_hist")

            # Clear history
            if st.button("🗑️ Clear History",
                          key="btn_clear_hist"):
                st.session_state.upload_history = []
                st.rerun()
        else:
            st.markdown(
                _alert(
                    "No uploads yet. Use the Single File or "
                    "Bulk Upload tabs to upload files to stages.",
                    c("text_muted"), "ℹ️"),
                unsafe_allow_html=True)


# ─── Footer ───────────────────────────────────────────────────────────────────

st.markdown(
    f'<div style="text-align:center;padding:28px 0 10px;'
    f'border-top:1px solid {c("border")};margin-top:32px;">'
    f'<div style="font-size:0.78rem;font-weight:800;'
    f'color:{c("text_primary")};">'
    f'💾 Storage Usage'
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
    unsafe_allow_html=True)