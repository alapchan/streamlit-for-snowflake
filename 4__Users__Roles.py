"""
👥 Users & Roles — View, create and manage users,
   roles and grants across all connected environments.
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
    page_title="Users & Roles · PwC",
    page_icon="👥",
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
        f'{text}</div>'
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


def _user_avatar(name: str, color: str) -> str:
    initials = name[:2].upper() if len(name) >= 2 else name.upper()
    return (
        f'<div style="width:36px;height:36px;'
        f'border-radius:50%;'
        f'display:flex;align-items:center;'
        f'justify-content:center;'
        f'font-size:1rem;font-weight:700;flex-shrink:0;'
        f'background:{color}22;color:{color};'
        f'border:1px solid {color}44;">'
        f'{initials}</div>'
    )


def _user_card(u_name, u_email, u_role, u_wh,
               u_login, u_mfa, u_dis, u_lock,
               env_color) -> str:
    status_color = (
        c("red")    if u_dis
        else c("yellow") if u_lock
        else c("green")
    )
    status_text = (
        "DISABLED" if u_dis
        else "LOCKED" if u_lock
        else "ACTIVE"
    )
    mfa_color = c("green") if u_mfa else c("red")
    mfa_text  = "ON" if u_mfa else "OFF"

    initials = u_name[:2].upper() if len(u_name) >= 2 else u_name.upper()

    return (
        f'<div style="background:linear-gradient('
        f'180deg,rgba(255,255,255,0.02),'
        f'rgba(255,255,255,0.00)),rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-top:3px solid {status_color};'
        f'border-radius:18px;padding:16px;'
        f'box-shadow:0 14px 28px rgba(0,0,0,0.16);'
        f'margin-bottom:10px;">'
        # header row
        f'<div style="display:flex;align-items:center;'
        f'gap:12px;margin-bottom:10px;">'
        # avatar
        f'<div style="width:36px;height:36px;'
        f'border-radius:50%;flex-shrink:0;'
        f'display:flex;align-items:center;'
        f'justify-content:center;'
        f'font-size:1rem;font-weight:700;'
        f'background:{env_color}22;color:{env_color};'
        f'border:1px solid {env_color}44;">'
        f'{initials}</div>'
        # name + email
        f'<div style="flex:1;min-width:0;">'
        f'<div style="font-weight:700;font-size:0.9rem;'
        f'color:{c("text_primary")};'
        f'overflow:hidden;text-overflow:ellipsis;'
        f'white-space:nowrap;">{u_name}</div>'
        f'<div style="font-size:0.7rem;'
        f'color:{c("text_muted")};'
        f'overflow:hidden;text-overflow:ellipsis;'
        f'white-space:nowrap;">'
        f'{u_email or "No email"}</div>'
        f'</div>'
        # status badge
        f'<span style="font-size:0.62rem;font-weight:700;'
        f'color:{status_color};'
        f'background:{status_color}15;'
        f'border:1px solid {status_color}33;'
        f'padding:2px 8px;border-radius:10px;">'
        f'{status_text}</span>'
        f'</div>'
        # info grid
        f'<div style="display:grid;'
        f'grid-template-columns:1fr 1fr;gap:6px;">'
        f'<div style="font-size:0.68rem;'
        f'color:{c("text_muted")};">'
        f'🎭 Role: <b style="color:{c("text_secondary")};">'
        f'{u_role}</b></div>'
        f'<div style="font-size:0.68rem;'
        f'color:{c("text_muted")};">'
        f'⚙️ WH: <b style="color:{c("text_secondary")};">'
        f'{u_wh}</b></div>'
        f'<div style="font-size:0.68rem;'
        f'color:{c("text_muted")};">'
        f'🕐 Last Login: <b style="color:{c("text_secondary")};">'
        f'{u_login}</b></div>'
        f'<div style="font-size:0.68rem;'
        f'color:{c("text_muted")};">'
        f'🔐 MFA: <b style="color:{mfa_color};">'
        f'{mfa_text}</b></div>'
        f'</div>'
        f'</div>'
    )


def _role_card(r_name, r_owner, r_cmt,
               is_sys, env_color) -> str:
    card_color = c("pwc_gold") if is_sys else env_color
    sys_badge  = (
        f'<span style="font-size:0.6rem;'
        f'color:{c("pwc_gold")};'
        f'background:{c("pwc_gold")}15;'
        f'border:1px solid {c("pwc_gold")}33;'
        f'padding:2px 8px;border-radius:999px;">'
        f'⭐ SYSTEM</span>'
        if is_sys else ""
    )
    cmt_html = (
        f'<div style="font-size:0.65rem;'
        f'color:{c("text_muted")};margin-top:4px;'
        f'overflow:hidden;text-overflow:ellipsis;'
        f'white-space:nowrap;">{r_cmt}</div>'
        if r_cmt else ""
    )
    return (
        f'<div style="background:linear-gradient('
        f'180deg,rgba(255,255,255,0.02),'
        f'rgba(255,255,255,0.00)),rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-top:3px solid {card_color};'
        f'border-radius:14px;padding:14px 16px;'
        f'box-shadow:0 10px 24px rgba(0,0,0,0.16);'
        f'margin-bottom:8px;">'
        f'<div style="display:flex;align-items:center;'
        f'justify-content:space-between;margin-bottom:6px;">'
        f'<span style="font-weight:700;font-size:0.88rem;'
        f'color:{c("text_primary")};">🎭 {r_name}</span>'
        f'{sys_badge}'
        f'</div>'
        f'<div style="font-size:0.68rem;'
        f'color:{c("text_muted")};">'
        f'👤 Owner: <b style="color:{c("text_secondary")};">'
        f'{r_owner}</b></div>'
        f'{cmt_html}'
        f'</div>'
    )


def _env_overview_card(acc, n_users, n_roles,
                       n_active, n_dis,
                       env_color) -> str:
    body = (
        f'<div style="display:flex;align-items:center;'
        f'justify-content:space-between;margin-bottom:12px;">'
        f'<span style="font-size:0.9rem;font-weight:800;'
        f'color:{env_color};">{acc}</span>'
        f'</div>'
        f'<div style="display:grid;'
        f'grid-template-columns:repeat(4,1fr);'
        f'gap:10px;text-align:center;">'
        + _stat_cell(str(n_users),  "Users",    env_color)
        + _stat_cell(str(n_roles),  "Roles",    c("blue"))
        + _stat_cell(str(n_active), "Active",   c("green"))
        + _stat_cell(str(n_dis),    "Disabled", c("red"))
        + f'</div>'
    )
    return _card(body, border_color=env_color)


def _stat_cell(value, label, color) -> str:
    return (
        f'<div>'
        f'<div style="font-family:JetBrains Mono,monospace;'
        f'font-size:1.4rem;font-weight:700;color:{color};">'
        f'{value}</div>'
        f'<div style="font-size:0.6rem;'
        f'color:{c("text_muted")};'
        f'text-transform:uppercase;">{label}</div>'
        f'</div>'
    )


def _grant_row(label, color) -> str:
    return (
        f'<div style="display:flex;align-items:center;'
        f'padding:10px 14px;'
        f'background:rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-radius:8px;margin-bottom:6px;">'
        f'<span style="display:inline-flex;'
        f'align-items:center;gap:4px;'
        f'padding:2px 10px;border-radius:12px;'
        f'font-size:0.62rem;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.4px;'
        f'color:{color};background:{color}10;'
        f'border:1px solid {color}33;">'
        f'🎭 {label}</span>'
        f'</div>'
    )


def _priv_row(priv, obj_type, obj_name,
              p_color) -> str:
    return (
        f'<div style="display:flex;align-items:center;'
        f'justify-content:space-between;'
        f'padding:10px 14px;'
        f'background:rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-radius:8px;margin-bottom:6px;">'
        f'<div style="display:flex;align-items:center;'
        f'gap:8px;">'
        f'<span style="display:inline-flex;'
        f'align-items:center;padding:2px 8px;'
        f'border-radius:6px;font-size:0.62rem;'
        f'font-weight:700;text-transform:uppercase;'
        f'color:{p_color};background:{p_color}10;'
        f'border:1px solid {p_color}33;">'
        f'{priv}</span>'
        f'<span style="color:{c("text_muted")};'
        f'font-size:0.72rem;">ON {obj_type}</span>'
        f'<span style="color:{c("text_primary")};'
        f'font-weight:600;font-size:0.8rem;">'
        f'{obj_name}</span>'
        f'</div>'
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


@st.cache_data(ttl=60, show_spinner=False)
def fetch_users(_mid, account: str) -> pd.DataFrame:
    try:
        df = run_query(account, "SHOW USERS")
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def fetch_roles(_mid, account: str) -> pd.DataFrame:
    try:
        df = run_query(account, "SHOW ROLES")
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def fetch_grants_to_user(_mid, account, user):
    try:
        df = run_query(account,
                       f'SHOW GRANTS TO USER "{user}"')
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def fetch_grants_to_role(_mid, account, role):
    try:
        df = run_query(account,
                       f'SHOW GRANTS TO ROLE "{role}"')
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def fetch_grants_of_role(_mid, account, role):
    try:
        df = run_query(account,
                       f'SHOW GRANTS OF ROLE "{role}"')
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def fetch_warehouses(_mid, account: str):
    try:
        df = run_query(account, "SHOW WAREHOUSES")
        if df is not None and "name" in df.columns:
            return df["name"].tolist()
    except Exception:
        pass
    return []


@st.cache_data(ttl=60, show_spinner=False)
def fetch_databases(_mid, account: str):
    try:
        df = run_query(account, "SHOW DATABASES")
        if df is not None and "name" in df.columns:
            return df["name"].tolist()
    except Exception:
        pass
    return []


@st.cache_data(ttl=60, show_spinner=False)
def fetch_schemas(_mid, account: str, db: str):
    try:
        df = run_query(account,
                       f'SHOW SCHEMAS IN DATABASE "{db}"')
        if df is not None and "name" in df.columns:
            return [s for s in df["name"].tolist()
                    if s != "INFORMATION_SCHEMA"]
    except Exception:
        pass
    return []


@st.cache_data(ttl=60, show_spinner=False)
def fetch_login_history(_mid, account, days):
    try:
        df = run_query(account, f"""
            SELECT
                USER_NAME, EVENT_TYPE, IS_SUCCESS,
                ERROR_CODE, ERROR_MESSAGE,
                FIRST_AUTHENTICATION_FACTOR,
                SECOND_AUTHENTICATION_FACTOR,
                EVENT_TIMESTAMP, CLIENT_IP,
                REPORTED_CLIENT_TYPE,
                REPORTED_CLIENT_VERSION, CONNECTION
            FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
            WHERE EVENT_TIMESTAMP >=
                  DATEADD('day',{-days},CURRENT_TIMESTAMP())
            ORDER BY EVENT_TIMESTAMP DESC
            LIMIT 2000
        """)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def fetch_access_history(_mid, account, days):
    try:
        df = run_query(account, f"""
            SELECT
                USER_NAME, QUERY_ID, QUERY_START_TIME,
                DIRECT_OBJECTS_ACCESSED,
                BASE_OBJECTS_ACCESSED, OBJECTS_MODIFIED
            FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY
            WHERE QUERY_START_TIME >=
                  DATEADD('day',{-days},CURRENT_TIMESTAMP())
            ORDER BY QUERY_START_TIME DESC
            LIMIT 1000
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
        f'color:{c("text_primary")};">👥 Users &amp; Roles</div>'
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
    if st.button("🔄 Refresh",
                  use_container_width=True,
                  key="ur_refresh"):
        st.cache_data.clear()
        st.rerun()

# ─── Header ───────────────────────────────────────────────────────────────────

pwc_header(
    "Users & Roles",
    subtitle="Manage users, roles, grants and "
             "privileges across all environments"
)

if not connected:
    st.markdown(
        _alert("Connect at least one account to manage "
               "users and roles.",
               c("pwc_orange"), "🔌"),
        unsafe_allow_html=True
    )
    st.stop()

# ─── Tabs ─────────────────────────────────────────────────────────────────────

(tab_overview, tab_users, tab_create_user,
 tab_roles, tab_create_role,
 tab_grants, tab_activity) = st.tabs([
    "📊  Overview",
    "👤  Users",
    "➕  Create User",
    "🎭  Roles",
    "🆕  Create Role",
    "🔐  Grants",
    "📈  Activity",
])

# ═══════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════

with tab_overview:
    section_header("USERS & ROLES OVERVIEW")

    all_user_dfs = []
    all_role_dfs = []
    for acc in connected:
        udf = fetch_users(id(manager), acc)
        rdf = fetch_roles(id(manager), acc)
        if not udf.empty:
            all_user_dfs.append(udf)
        if not rdf.empty:
            all_role_dfs.append(rdf)

    total_users = sum(len(d) for d in all_user_dfs)
    total_roles = sum(len(d) for d in all_role_dfs)

    disabled = 0
    locked   = 0
    for udf in all_user_dfs:
        dis_c = next((col for col in ["disabled","DISABLED"]
                       if col in udf.columns), None)
        lck_c = next((col for col in [
            "locked_until_time","LOCKED_UNTIL_TIME"]
            if col in udf.columns), None)
        if dis_c:
            disabled += len(udf[
                udf[dis_c].astype(str).str.upper() == "TRUE"])
        if lck_c:
            locked += len(udf[
                udf[lck_c].notna() &
                (udf[lck_c].astype(str) != "") &
                (udf[lck_c].astype(str) != "nan")])

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    kpis = [
        ("👥", str(total_users),           "Total Users",     c("pwc_orange")),
        ("🎭", str(total_roles),           "Total Roles",     c("blue")),
        ("🌍", str(len(connected)),        "Environments",    c("pwc_gold")),
        ("✅", str(total_users - disabled),"Active Users",    c("green")),
        ("🚫", str(disabled),              "Disabled Users",  c("red")),
        ("🔒", str(locked),                "Locked Accounts", c("yellow")),
    ]
    for col, (ico, val, lbl, clr) in zip(
            [k1,k2,k3,k4,k5,k6], kpis):
        with col:
            st.markdown(_kpi(ico, val, lbl, clr),
                         unsafe_allow_html=True)

    st.markdown('<div style="height:12px;"></div>',
                 unsafe_allow_html=True)

    section_header("PER-ENVIRONMENT BREAKDOWN")

    for acc in connected:
        env_color = get_env_color(acc)
        udf = fetch_users(id(manager), acc)
        rdf = fetch_roles(id(manager), acc)

        n_users = len(udf)
        n_roles = len(rdf)
        n_dis   = 0
        if not udf.empty:
            dc = next((col for col in ["disabled","DISABLED"]
                        if col in udf.columns), None)
            if dc:
                n_dis = len(udf[
                    udf[dc].astype(str).str.upper() == "TRUE"])

        st.markdown(
            _env_overview_card(
                acc, n_users, n_roles,
                n_users - n_dis, n_dis, env_color
            ),
            unsafe_allow_html=True
        )

    if all_user_dfs or all_role_dfs:
        st.markdown('<div style="height:8px;"></div>',
                     unsafe_allow_html=True)
        section_header("DISTRIBUTION CHARTS")

        ch1, ch2 = st.columns(2)
        with ch1:
            env_data = pd.DataFrame([
                {"Environment": acc,
                 "Users": len(fetch_users(id(manager), acc)),
                 "Roles": len(fetch_roles(id(manager), acc))}
                for acc in connected
            ])
            melted = env_data.melt(
                id_vars="Environment",
                value_vars=["Users","Roles"],
                var_name="Type", value_name="Count"
            )
            fig = px.bar(
                melted, x="Environment",
                y="Count", color="Type",
                barmode="group", height=320,
                title="Users vs Roles per Environment",
                color_discrete_sequence=[
                    c("pwc_orange"), c("blue")]
            )
            fig.update_layout(
                xaxis_title="", yaxis_title="Count",
                legend_title_text="")
            st.plotly_chart(fig, use_container_width=True,
                             key="ov_usr_role_bar")

        with ch2:
            if all_user_dfs:
                all_users = pd.concat(
                    all_user_dfs, ignore_index=True)
                dc = next((col for col in [
                    "disabled","DISABLED"]
                    if col in all_users.columns), None)
                if dc:
                    sc = (all_users[dc].astype(str)
                          .str.upper()
                          .map({"TRUE":"Disabled",
                                "FALSE":"Active"})
                          .value_counts())
                    fig2 = go.Figure(go.Pie(
                        labels=sc.index,
                        values=sc.values,
                        hole=0.6,
                        marker_colors=[
                            c("green"), c("red")],
                        textinfo="label+percent"
                    ))
                    fig2.update_layout(
                        title="User Status Distribution",
                        height=320,
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(color=c("text_secondary"))
                    )
                    st.plotly_chart(
                        fig2, use_container_width=True,
                        key="ov_usr_status_pie")


# ═══════════════════════════════════════════════════════
# TAB 2 — USERS
# ═══════════════════════════════════════════════════════

with tab_users:
    section_header("USER MANAGEMENT")

    uf1, uf2, uf3 = st.columns(3)
    with uf1:
        usr_acc = st.selectbox(
            "Environment", connected, key="usr_acc")
    with uf2:
        usr_filter = st.selectbox(
            "Status",
            ["All","Active","Disabled","Locked"],
            key="usr_filter")
    with uf3:
        usr_search = st.text_input(
            "🔍 Search users", key="usr_search",
            placeholder="Name or email…")

    udf = fetch_users(id(manager), usr_acc)

    if udf.empty:
        st.info("No users found.")
    else:
        name_c   = next((col for col in ["name","NAME"]
                          if col in udf.columns), None)
        email_c  = next((col for col in ["email","EMAIL"]
                          if col in udf.columns), None)
        dis_c    = next((col for col in ["disabled","DISABLED"]
                          if col in udf.columns), None)
        lck_c    = next((col for col in [
            "locked_until_time","LOCKED_UNTIL_TIME"]
            if col in udf.columns), None)
        role_c   = next((col for col in [
            "default_role","DEFAULT_ROLE"]
            if col in udf.columns), None)
        wh_c     = next((col for col in [
            "default_warehouse","DEFAULT_WAREHOUSE"]
            if col in udf.columns), None)
        login_tc = next((col for col in [
            "last_success_login","LAST_SUCCESS_LOGIN"]
            if col in udf.columns), None)
        mfa_c    = next((col for col in [
            "has_mfa","HAS_MFA",
            "ext_authn_duo","EXT_AUTHN_DUO"]
            if col in udf.columns), None)

        filtered = udf.copy()
        if usr_filter == "Active" and dis_c:
            filtered = filtered[
                filtered[dis_c].astype(str)
                .str.upper() != "TRUE"]
        elif usr_filter == "Disabled" and dis_c:
            filtered = filtered[
                filtered[dis_c].astype(str)
                .str.upper() == "TRUE"]
        elif usr_filter == "Locked" and lck_c:
            filtered = filtered[
                filtered[lck_c].notna() &
                (filtered[lck_c].astype(str) != "") &
                (filtered[lck_c].astype(str) != "nan")]

        if usr_search and name_c:
            mask = filtered[name_c].str.contains(
                usr_search, case=False, na=False)
            if email_c:
                mask |= filtered[email_c].astype(str)\
                    .str.contains(usr_search,
                                   case=False, na=False)
            filtered = filtered[mask]

        env_color = get_env_color(usr_acc)
        st.markdown(
            f'<div style="font-size:0.72rem;'
            f'color:{c("text_muted")};margin-bottom:10px;">'
            f'{len(filtered)} user(s) shown</div>',
            unsafe_allow_html=True
        )

        user_list = list(filtered.iterrows())
        for idx in range(0, len(user_list), 2):
            row_cols = st.columns(2)
            for ci, (_, user) in enumerate(
                    user_list[idx:idx+2]):
                u_name  = user.get(name_c,  "?") if name_c  else "?"
                u_email = str(user.get(email_c,"")) if email_c else ""
                u_dis   = (str(user.get(dis_c,"FALSE")).upper() == "TRUE"
                            if dis_c else False)
                u_lock  = (str(user.get(lck_c,"")).strip()
                            not in ("","nan","None","NaT","NaN")
                            if lck_c else False)
                u_role  = user.get(role_c, "—") if role_c else "—"
                u_wh    = user.get(wh_c,   "—") if wh_c   else "—"
                u_login = str(user.get(login_tc,""))[:10] if login_tc else "—"
                u_mfa   = (str(user.get(mfa_c,"FALSE")).upper()
                            in ("TRUE","Y","1")
                            if mfa_c else False)

                with row_cols[ci]:
                    st.markdown(
                        _user_card(
                            u_name, u_email, u_role, u_wh,
                            u_login, u_mfa, u_dis, u_lock,
                            env_color
                        ),
                        unsafe_allow_html=True
                    )

        st.markdown('<div style="height:8px;"></div>',
                     unsafe_allow_html=True)
        section_header("QUICK ACTIONS")

        qa1, qa2 = st.columns(2)
        user_names = (filtered[name_c].tolist()
                       if name_c and not filtered.empty
                       else [])

        with qa1:
            with st.expander("🔑 Reset Password"):
                rp_user = st.selectbox(
                    "User", options=user_names,
                    key="rp_user")
                rp_pwd = st.text_input(
                    "New Password", type="password",
                    key="rp_pwd")
                rp_must = st.checkbox(
                    "Must change on next login",
                    value=True, key="rp_must")
                if st.button("🔑 Reset Password",
                              type="primary",
                              key="btn_reset_pwd"):
                    if rp_user and rp_pwd:
                        mc  = (" MUST_CHANGE_PASSWORD = TRUE"
                               if rp_must else "")
                        sql = (f'ALTER USER "{rp_user}" '
                               f"SET PASSWORD = '{rp_pwd}'{mc};")
                        ok, msg = run_statement(usr_acc, sql)
                        if ok:
                            st.success(f"✅ Password reset for {rp_user}")
                        else:
                            st.error(f"❌ {msg}")

            with st.expander("🔓 Unlock User"):
                ul_user = st.selectbox(
                    "User to Unlock", options=user_names,
                    key="ul_user")
                if st.button("🔓 Unlock", type="primary",
                              key="btn_unlock"):
                    ok, msg = run_statement(
                        usr_acc,
                        f'ALTER USER "{ul_user}" '
                        f'SET MINS_TO_UNLOCK = 0;')
                    if ok:
                        st.success(f"✅ {ul_user} unlocked")
                    else:
                        st.error(f"❌ {msg}")

        with qa2:
            with st.expander("🚫 Disable / Enable User"):
                de_user = st.selectbox(
                    "User", options=user_names,
                    key="de_user")
                de_action = st.radio(
                    "Action", ["Disable","Enable"],
                    horizontal=True, key="de_action")
                if st.button(
                    f"{'🚫' if de_action=='Disable' else '✅'} "
                    f"{de_action} User",
                    type="primary", key="btn_de_user"
                ):
                    val = ("TRUE" if de_action == "Disable"
                           else "FALSE")
                    ok, msg = run_statement(
                        usr_acc,
                        f'ALTER USER "{de_user}" '
                        f'SET DISABLED = {val};')
                    if ok:
                        st.success(
                            f"✅ {de_user} "
                            f"{'disabled' if val=='TRUE' else 'enabled'}")
                        st.cache_data.clear()
                    else:
                        st.error(f"❌ {msg}")

            with st.expander("🗑️ Drop User"):
                dr_user = st.selectbox(
                    "User to Drop", options=user_names,
                    key="dr_user")
                st.warning(f"⚠️ Permanently drops **{dr_user}**.")
                if st.checkbox("Confirm drop",
                                key="confirm_drop_user"):
                    if st.button("🗑️ Drop User",
                                  type="primary",
                                  key="btn_drop_user"):
                        ok, msg = run_statement(
                            usr_acc,
                            f'DROP USER IF EXISTS "{dr_user}";')
                        if ok:
                            st.success(f"✅ {dr_user} dropped")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")

        with st.expander("📋 Full User Table"):
            disp_cols = [col for col in [
                "name","login_name","email","display_name",
                "disabled","default_role","default_warehouse",
                "last_success_login","created_on",
                "has_mfa","owner","comment",
                "NAME","LOGIN_NAME","EMAIL","DISPLAY_NAME",
                "DISABLED","DEFAULT_ROLE","DEFAULT_WAREHOUSE",
                "LAST_SUCCESS_LOGIN","CREATED_ON",
                "HAS_MFA","OWNER","COMMENT"
            ] if col in udf.columns]
            st.dataframe(udf[disp_cols],
                          use_container_width=True,
                          hide_index=True, height=400)
            st.download_button(
                "📥 Download Users CSV",
                data=udf.to_csv(index=False),
                file_name=(f"users_{usr_acc}_"
                           f"{datetime.date.today()}.csv"),
                mime="text/csv", key="usr_dl")


# ═══════════════════════════════════════════════════════
# TAB 3 — CREATE USER
# ═══════════════════════════════════════════════════════

with tab_create_user:
    section_header("CREATE NEW USER")

    st.markdown(
        _info_box(
            "Create a new Snowflake user with full configuration "
            "options including authentication, defaults, "
            "network policies and role assignments.",
            accent=c("pwc_orange")
        ),
        unsafe_allow_html=True
    )

    st.markdown(_step(1, "Identity & Location"),
                 unsafe_allow_html=True)
    cu1, cu2, cu3 = st.columns(3)
    with cu1:
        cu_acc  = st.selectbox("Account", connected, key="cu_acc")
        cu_name = st.text_input("Username *",
                                 placeholder="john.doe",
                                 key="cu_name")
    with cu2:
        cu_login   = st.text_input("Login Name",
                                    placeholder="john.doe@company.com",
                                    key="cu_login")
        cu_display = st.text_input("Display Name",
                                    placeholder="John Doe",
                                    key="cu_display")
    with cu3:
        cu_email = st.text_input("Email",
                                  placeholder="john.doe@company.com",
                                  key="cu_email")
        cu_first = st.text_input("First Name", key="cu_first")
        cu_last  = st.text_input("Last Name",  key="cu_last")

    st.markdown(_step(2, "Authentication"),
                 unsafe_allow_html=True)
    auth_type = st.radio(
        "Authentication Method",
        ["Password","RSA Key","No Authentication"],
        horizontal=True, key="cu_auth_type")

    auth_clause = ""
    ac1, ac2 = st.columns(2)
    with ac1:
        if auth_type == "Password":
            cu_pwd = st.text_input("Password *",
                                    type="password",
                                    key="cu_pwd")
            cu_must_change = st.checkbox(
                "Must change password on first login",
                value=True, key="cu_must_change")
            auth_clause = (f"PASSWORD = '{cu_pwd}'"
                            if cu_pwd else "")
            if cu_must_change and cu_pwd:
                auth_clause += "\n    MUST_CHANGE_PASSWORD = TRUE"
        elif auth_type == "RSA Key":
            cu_rsa = st.text_area(
                "RSA Public Key",
                placeholder="-----BEGIN PUBLIC KEY-----\n...",
                height=100, key="cu_rsa")
            if cu_rsa:
                auth_clause = f"RSA_PUBLIC_KEY = '{cu_rsa}'"
        else:
            st.info("No password. Useful for service accounts.")
    with ac2:
        cu_disabled       = st.checkbox("Create as DISABLED",
                                         value=False,
                                         key="cu_disabled")
        cu_days_to_expiry = st.number_input(
            "Days until password expires (0=never)",
            min_value=0, value=0, key="cu_days_expiry")
        cu_mins_to_unlock = st.number_input(
            "Mins to unlock (0=no lockout)",
            min_value=0, value=0, key="cu_mins_unlock")

    st.markdown(_step(3, "Default Role & Warehouse"),
                 unsafe_allow_html=True)
    def_c1, def_c2, def_c3 = st.columns(3)

    roles_df  = fetch_roles(id(manager), cu_acc)
    r_nc      = next((col for col in ["name","NAME"]
                       if col in roles_df.columns), None)
    role_list = (roles_df[r_nc].tolist()
                  if r_nc and not roles_df.empty else [])
    wh_list   = fetch_warehouses(id(manager), cu_acc)
    db_list   = fetch_databases(id(manager), cu_acc)

    with def_c1:
        cu_def_role = st.selectbox("Default Role",
                                    options=["(none)"] + role_list,
                                    key="cu_def_role")
    with def_c2:
        cu_def_wh = st.selectbox("Default Warehouse",
                                   options=["(none)"] + wh_list,
                                   key="cu_def_wh")
    with def_c3:
        cu_def_ns = st.selectbox("Default Namespace (DB)",
                                   options=["(none)"] + db_list,
                                   key="cu_def_ns")

    st.markdown(_step(4, "Advanced Options"),
                 unsafe_allow_html=True)
    adv1, adv2, adv3 = st.columns(3)
    with adv1:
        cu_comment = st.text_area(
            "Comment",
            placeholder="Service account for ETL pipeline",
            height=80, key="cu_comment")
    with adv2:
        cu_network = st.text_input("Network Policy",
                                    placeholder="MY_NETWORK_POLICY",
                                    key="cu_network")
        cu_session_timeout = st.number_input(
            "Session Timeout (minutes, 0=default)",
            min_value=0, value=0, key="cu_session_timeout")
    with adv3:
        cu_timezone = st.text_input("Timezone",
                                     placeholder="America/New_York",
                                     key="cu_timezone")
        cu_date_format = st.text_input("Date Format",
                                        placeholder="YYYY-MM-DD",
                                        key="cu_date_format")

    st.markdown(_step(5, "Grant Roles to User"),
                 unsafe_allow_html=True)
    cu_grant_roles = st.multiselect(
        "Roles to grant after creation",
        options=role_list, key="cu_grant_roles")

    if cu_name and cu_acc:
        props = []
        if auth_clause:
            props.append(f"    {auth_clause}")
        if cu_login:
            props.append(f"    LOGIN_NAME = '{cu_login}'")
        if cu_display:
            props.append(f"    DISPLAY_NAME = '{cu_display}'")
        if cu_email:
            props.append(f"    EMAIL = '{cu_email}'")
        if cu_first:
            props.append(f"    FIRST_NAME = '{cu_first}'")
        if cu_last:
            props.append(f"    LAST_NAME = '{cu_last}'")
        if cu_def_role != "(none)":
            props.append(f"    DEFAULT_ROLE = '{cu_def_role}'")
        if cu_def_wh != "(none)":
            props.append(f"    DEFAULT_WAREHOUSE = '{cu_def_wh}'")
        if cu_def_ns != "(none)":
            props.append(f"    DEFAULT_NAMESPACE = '{cu_def_ns}'")
        if cu_disabled:
            props.append("    DISABLED = TRUE")
        if cu_days_to_expiry > 0:
            props.append(f"    DAYS_TO_EXPIRY = {cu_days_to_expiry}")
        if cu_mins_to_unlock > 0:
            props.append(f"    MINS_TO_UNLOCK = {cu_mins_to_unlock}")
        if cu_network:
            props.append(f"    NETWORK_POLICY = '{cu_network}'")
        if cu_session_timeout > 0:
            props.append(f"    SESSION_TIMEOUT_MINS = {cu_session_timeout}")
        if cu_timezone:
            props.append(f"    TIMEZONE = '{cu_timezone}'")
        if cu_date_format:
            props.append(f"    DATE_INPUT_FORMAT = '{cu_date_format}'")
        if cu_comment:
            props.append(f"    COMMENT = '{cu_comment}'")

        user_sql = (
            f'CREATE USER IF NOT EXISTS "{cu_name}"\n'
            + "\n".join(props) + ";"
        )
        grant_sqls = [
            f'GRANT ROLE "{r}" TO USER "{cu_name}";'
            for r in cu_grant_roles
        ]

        section_header("GENERATED SQL")
        st.markdown(_sql_block(user_sql),
                     unsafe_allow_html=True)
        for gs in grant_sqls:
            st.markdown(_sql_block(gs),
                         unsafe_allow_html=True)

        cb1, cb2 = st.columns(2)
        with cb1:
            create_user_btn = st.button(
                "▶️ Create User", type="primary",
                key="btn_create_user")
        with cb2:
            if st.button("📋 Copy SQL",
                          key="btn_copy_user_sql"):
                st.code(user_sql + "\n" +
                        "\n".join(grant_sqls),
                        language="sql")

        if create_user_btn:
            with st.status(f"Creating {cu_name}…",
                            expanded=True) as s:
                st.write("🔍 Validating…")
                time.sleep(0.3)
                ok, result = run_statement(cu_acc, user_sql)
                if ok:
                    for gs in grant_sqls:
                        rn = gs.split('"')[1]
                        st.write(f"🎭 Granting {rn}…")
                        run_statement(cu_acc, gs)
                        time.sleep(0.2)
                    s.update(
                        label=f"✅ {cu_name} created!",
                        state="complete", expanded=False)
                else:
                    s.update(
                        label="❌ Failed",
                        state="error", expanded=True)

            if ok:
                st.success(
                    f"✅ User **{cu_name}** created "
                    f"on **{cu_acc}**")
                st.cache_data.clear()
                st.balloons()
            else:
                st.error(f"❌ {result}")


# ═══════════════════════════════════════════════════════
# TAB 4 — ROLES
# ═══════════════════════════════════════════════════════

with tab_roles:
    section_header("ROLE BROWSER")

    rf1, rf2 = st.columns(2)
    with rf1:
        role_acc = st.selectbox("Environment",
                                  connected, key="role_acc")
    with rf2:
        role_search = st.text_input("🔍 Search roles",
                                     key="role_search",
                                     placeholder="Filter by name…")

    rdf     = fetch_roles(id(manager), role_acc)
    env_c   = get_env_color(role_acc)

    SYSTEM_ROLES = {
        "ACCOUNTADMIN","SYSADMIN","SECURITYADMIN",
        "USERADMIN","PUBLIC","ORGADMIN"
    }

    if rdf.empty:
        st.info("No roles found.")
    else:
        r_name_c  = next((col for col in ["name","NAME"]
                           if col in rdf.columns), None)
        r_owner_c = next((col for col in ["owner","OWNER"]
                           if col in rdf.columns), None)
        r_comment = next((col for col in ["comment","COMMENT"]
                           if col in rdf.columns), None)

        filtered_r = rdf.copy()
        if role_search and r_name_c:
            filtered_r = filtered_r[
                filtered_r[r_name_c].str.contains(
                    role_search, case=False, na=False)]

        role_list_items = list(filtered_r.iterrows())
        for idx in range(0, len(role_list_items), 3):
            row_cols = st.columns(3)
            for ci, (_, role) in enumerate(
                    role_list_items[idx:idx+3]):
                r_name  = role.get(r_name_c,"?") if r_name_c  else "?"
                r_owner = role.get(r_owner_c,"—") if r_owner_c else "—"
                r_cmt   = role.get(r_comment,"")  if r_comment else ""
                is_sys  = r_name in SYSTEM_ROLES

                with row_cols[ci]:
                    st.markdown(
                        _role_card(r_name, r_owner,
                                    r_cmt, is_sys, env_c),
                        unsafe_allow_html=True
                    )

        st.markdown('<div style="height:8px;"></div>',
                     unsafe_allow_html=True)
        section_header("ROLE DRILL-DOWN")

        sel_role = st.selectbox(
            "Select role to inspect",
            options=(filtered_r[r_name_c].tolist()
                     if r_name_c else []),
            key="role_drill")

        if sel_role:
            drill_tab1, drill_tab2 = st.tabs([
                "📋 Privileges", "👥 Members"])

            with drill_tab1:
                grants_to = fetch_grants_to_role(
                    id(manager), role_acc, sel_role)
                if grants_to.empty:
                    st.info(f"No privileges for {sel_role}.")
                else:
                    st.markdown(
                        f'<div style="font-size:0.72rem;'
                        f'color:{c("text_muted")};'
                        f'margin-bottom:8px;">'
                        f'{len(grants_to)} privilege(s)</div>',
                        unsafe_allow_html=True
                    )
                    st.dataframe(grants_to,
                                  use_container_width=True,
                                  hide_index=True, height=350)

            with drill_tab2:
                grants_of = fetch_grants_of_role(
                    id(manager), role_acc, sel_role)
                if grants_of.empty:
                    st.info(f"No members in {sel_role}.")
                else:
                    st.markdown(
                        f'<div style="font-size:0.72rem;'
                        f'color:{c("text_muted")};'
                        f'margin-bottom:8px;">'
                        f'{len(grants_of)} member(s)</div>',
                        unsafe_allow_html=True
                    )
                    st.dataframe(grants_of,
                                  use_container_width=True,
                                  hide_index=True, height=350)


# ═══════════════════════════════════════════════════════
# TAB 5 — CREATE ROLE
# ═══════════════════════════════════════════════════════

with tab_create_role:
    section_header("CREATE NEW ROLE")

    st.markdown(
        _info_box(
            "Create a new Snowflake role, optionally grant "
            "privileges on objects, and assign the role "
            "to users or parent roles — all in one workflow.",
            accent=c("pwc_orange")
        ),
        unsafe_allow_html=True
    )

    st.markdown(_step(1, "Role Identity"),
                 unsafe_allow_html=True)
    cr_r1, cr_r2, cr_r3 = st.columns(3)
    with cr_r1:
        cr_role_acc  = st.selectbox("Account", connected,
                                     key="cr_role_acc")
        cr_role_name = st.text_input("Role Name *",
                                      placeholder="DATA_ANALYST_ROLE",
                                      key="cr_role_name")
    with cr_r2:
        cr_role_comment = st.text_area("Comment",
                                        placeholder="Read-only access",
                                        height=80,
                                        key="cr_role_comment")
    with cr_r3:
        parent_roles_df  = fetch_roles(id(manager), cr_role_acc)
        pr_nc            = next((col for col in ["name","NAME"]
                                  if col in parent_roles_df.columns),
                                None)
        parent_role_list = (parent_roles_df[pr_nc].tolist()
                             if pr_nc and not parent_roles_df.empty
                             else [])
        cr_parent_role = st.selectbox(
            "Grant this role TO (parent role)",
            options=["(none)"] + parent_role_list,
            key="cr_parent_role")

    st.markdown(_step(2, "Grant Privileges to Role"),
                 unsafe_allow_html=True)

    priv_tabs     = st.tabs(["🗄️ Database","📋 Schema",
                               "📁 Table/View","⚙️ Warehouse",
                               "🔧 Account Level"])
    all_priv_sqls = []
    cr_dbs_list   = fetch_databases(id(manager), cr_role_acc)

    with priv_tabs[0]:
        p1, p2, p3 = st.columns(3)
        with p1:
            priv_db = st.selectbox("Database",
                                    ["(none)"] + cr_dbs_list,
                                    key="priv_db")
        with p2:
            db_privs = st.multiselect(
                "Privileges",
                ["USAGE","CREATE SCHEMA","MODIFY",
                 "MONITOR","ALL PRIVILEGES"],
                key="priv_db_privs")
        with p3:
            db_future = st.checkbox("Include FUTURE SCHEMAS",
                                     key="priv_db_future")

        if priv_db != "(none)" and db_privs and cr_role_name:
            for p in db_privs:
                all_priv_sqls.append(
                    f'GRANT {p} ON DATABASE "{priv_db}" '
                    f'TO ROLE "{cr_role_name}";')
            if db_future:
                all_priv_sqls.append(
                    f'GRANT USAGE ON FUTURE SCHEMAS '
                    f'IN DATABASE "{priv_db}" '
                    f'TO ROLE "{cr_role_name}";')

    with priv_tabs[1]:
        ps1, ps2, ps3 = st.columns(3)
        with ps1:
            priv_sc_db = st.selectbox("Database",
                                       ["(none)"] + cr_dbs_list,
                                       key="priv_sc_db")
            priv_sc_schemas = (
                fetch_schemas(id(manager), cr_role_acc, priv_sc_db)
                if priv_sc_db != "(none)" else [])
            priv_sc = st.selectbox("Schema",
                                    ["ALL","(none)"] + priv_sc_schemas,
                                    key="priv_sc")
        with ps2:
            sc_privs = st.multiselect(
                "Privileges",
                ["USAGE","CREATE TABLE","CREATE VIEW",
                 "CREATE STAGE","MODIFY","ALL PRIVILEGES"],
                key="priv_sc_privs")
        with ps3:
            sc_future_tbl  = st.checkbox("FUTURE TABLES",
                                          key="sc_future_tbl")
            sc_future_view = st.checkbox("FUTURE VIEWS",
                                          key="sc_future_view")

        if priv_sc_db != "(none)" and sc_privs and cr_role_name:
            sc_ref = (
                f'ALL SCHEMAS IN DATABASE "{priv_sc_db}"'
                if priv_sc == "ALL"
                else f'SCHEMA "{priv_sc_db}"."{priv_sc}"')
            for p in sc_privs:
                all_priv_sqls.append(
                    f'GRANT {p} ON {sc_ref} '
                    f'TO ROLE "{cr_role_name}";')
            if sc_future_tbl and priv_sc != "ALL":
                all_priv_sqls.append(
                    f'GRANT SELECT ON FUTURE TABLES '
                    f'IN SCHEMA "{priv_sc_db}"."{priv_sc}" '
                    f'TO ROLE "{cr_role_name}";')
            if sc_future_view and priv_sc != "ALL":
                all_priv_sqls.append(
                    f'GRANT SELECT ON FUTURE VIEWS '
                    f'IN SCHEMA "{priv_sc_db}"."{priv_sc}" '
                    f'TO ROLE "{cr_role_name}";')

    with priv_tabs[2]:
        pt1, pt2, pt3 = st.columns(3)
        with pt1:
            priv_tbl_db = st.selectbox("Database",
                                        ["(none)"] + cr_dbs_list,
                                        key="priv_tbl_db")
            priv_tbl_schemas = (
                fetch_schemas(id(manager), cr_role_acc, priv_tbl_db)
                if priv_tbl_db != "(none)" else [])
            priv_tbl_sc = st.selectbox("Schema",
                                        ["ALL","(none)"] + priv_tbl_schemas,
                                        key="priv_tbl_sc")
        with pt2:
            tbl_privs = st.multiselect(
                "Privileges",
                ["SELECT","INSERT","UPDATE","DELETE",
                 "TRUNCATE","REFERENCES","ALL PRIVILEGES"],
                default=["SELECT"], key="priv_tbl_privs")
        with pt3:
            tbl_scope = st.radio(
                "Scope",
                ["All Tables","All Views","All Tables & Views"],
                key="priv_tbl_scope")

        if priv_tbl_db != "(none)" and tbl_privs and cr_role_name:
            privs_str = ", ".join(tbl_privs)
            sc_part   = (
                f'ALL SCHEMAS IN DATABASE "{priv_tbl_db}"'
                if priv_tbl_sc == "ALL"
                else f'SCHEMA "{priv_tbl_db}"."{priv_tbl_sc}"')
            if "Tables" in tbl_scope:
                all_priv_sqls.append(
                    f'GRANT {privs_str} ON ALL TABLES '
                    f'IN {sc_part} TO ROLE "{cr_role_name}";')
            if "Views" in tbl_scope:
                all_priv_sqls.append(
                    f'GRANT {privs_str} ON ALL VIEWS '
                    f'IN {sc_part} TO ROLE "{cr_role_name}";')

    with priv_tabs[3]:
        pw1, pw2 = st.columns(2)
        with pw1:
            wh_list_r = fetch_warehouses(id(manager), cr_role_acc)
            priv_whs  = st.multiselect("Warehouses",
                                        options=wh_list_r,
                                        key="priv_whs")
        with pw2:
            wh_privs = st.multiselect(
                "Privileges",
                ["USAGE","MODIFY","MONITOR",
                 "OPERATE","ALL PRIVILEGES"],
                default=["USAGE"], key="priv_wh_privs")

        if priv_whs and wh_privs and cr_role_name:
            for wh in priv_whs:
                all_priv_sqls.append(
                    f'GRANT {", ".join(wh_privs)} '
                    f'ON WAREHOUSE "{wh}" '
                    f'TO ROLE "{cr_role_name}";')

    with priv_tabs[4]:
        acct_privs = st.multiselect(
            "Account-Level Privileges",
            ["CREATE DATABASE","CREATE WAREHOUSE",
             "CREATE USER","CREATE ROLE",
             "CREATE INTEGRATION","MANAGE GRANTS",
             "MONITOR USAGE","EXECUTE TASK",
             "IMPORT SHARE","CREATE SHARE"],
            key="priv_acct")
        if acct_privs and cr_role_name:
            for ap in acct_privs:
                all_priv_sqls.append(
                    f'GRANT {ap} ON ACCOUNT '
                    f'TO ROLE "{cr_role_name}";')

    st.markdown(_step(3, "Assign Role to Users & Roles"),
                 unsafe_allow_html=True)
    assign_c1, assign_c2 = st.columns(2)
    with assign_c1:
        users_df2 = fetch_users(id(manager), cr_role_acc)
        u_nc2     = next((col for col in ["name","NAME"]
                           if col in users_df2.columns), None)
        cr_assign_users = st.multiselect(
            "Grant role to users",
            options=(users_df2[u_nc2].tolist()
                     if u_nc2 and not users_df2.empty else []),
            key="cr_assign_users")
    with assign_c2:
        cr_assign_roles = st.multiselect(
            "Grant role to roles (inheritance)",
            options=parent_role_list,
            key="cr_assign_roles")

    if cr_role_name:
        cmt_part = (f"\n    COMMENT = '{cr_role_comment}'"
                     if cr_role_comment else "")
        create_role_sql = (
            f'CREATE ROLE IF NOT EXISTS '
            f'"{cr_role_name}"{cmt_part};')

        parent_sql = (
            f'GRANT ROLE "{cr_role_name}" '
            f'TO ROLE "{cr_parent_role}";'
            if cr_parent_role != "(none)" else "")

        user_grant_sqls = [
            f'GRANT ROLE "{cr_role_name}" TO USER "{u}";'
            for u in cr_assign_users]
        role_grant_sqls = [
            f'GRANT ROLE "{cr_role_name}" TO ROLE "{r}";'
            for r in cr_assign_roles]

        all_sqls = (
            [create_role_sql]
            + ([parent_sql] if parent_sql else [])
            + all_priv_sqls
            + user_grant_sqls
            + role_grant_sqls
        )

        section_header("GENERATED SQL")
        for sql in all_sqls:
            st.markdown(_sql_block(sql),
                         unsafe_allow_html=True)

        st.markdown(
            f'<div style="font-size:0.75rem;'
            f'color:{c("text_muted")};margin:8px 0;">'
            f'{len(all_sqls)} SQL statement(s) will be executed'
            f'</div>',
            unsafe_allow_html=True
        )

        crb1, crb2 = st.columns(2)
        with crb1:
            create_role_btn = st.button(
                "▶️ Create Role & Apply Grants",
                type="primary", key="btn_create_role")
        with crb2:
            if st.button("📋 Copy SQL",
                          key="btn_copy_role_sql"):
                st.code("\n".join(all_sqls), language="sql")

        if create_role_btn:
            results = []
            with st.status(f"Creating {cr_role_name}…",
                            expanded=True) as cr_s:
                for i, sql in enumerate(all_sqls):
                    st.write(f"⚙️ Step {i+1}/{len(all_sqls)}…")
                    ok, msg = run_statement(cr_role_acc, sql)
                    results.append({
                        "SQL": sql[:60] + "…" if len(sql) > 60 else sql,
                        "Status": "✅ OK" if ok else f"❌ {msg}"
                    })
                    time.sleep(0.15)

                n_err = sum(1 for r in results
                             if "❌" in r["Status"])
                cr_s.update(
                    label=(f"✅ {cr_role_name} created!"
                            if n_err == 0
                            else f"⚠️ {n_err} error(s)"),
                    state="complete" if n_err == 0 else "error",
                    expanded=n_err > 0)

            if n_err == 0:
                st.success(
                    f"✅ Role **{cr_role_name}** created!")
                st.cache_data.clear()
                st.balloons()
            else:
                st.dataframe(pd.DataFrame(results),
                              use_container_width=True,
                              hide_index=True)


# ═══════════════════════════════════════════════════════
# TAB 6 — GRANTS
# ═══════════════════════════════════════════════════════

with tab_grants:
    section_header("GRANTS MANAGEMENT")

    gr_tab1, gr_tab2, gr_tab3 = st.tabs([
        "👤 User Grants",
        "🎭 Role Grants",
        "➕ Grant / Revoke",
    ])

    with gr_tab1:
        gc1, gc2 = st.columns(2)
        with gc1:
            gr_usr_acc = st.selectbox("Account", connected,
                                       key="gr_usr_acc")
        with gc2:
            gr_udf     = fetch_users(id(manager), gr_usr_acc)
            gr_u_nc    = next((col for col in ["name","NAME"]
                                if col in gr_udf.columns), None)
            gr_user_list = (gr_udf[gr_u_nc].tolist()
                             if gr_u_nc and not gr_udf.empty else [])
            gr_user_sel = st.selectbox(
                "Select User",
                options=gr_user_list or ["(none)"],
                key="gr_user_sel")

        if gr_user_sel and gr_user_sel != "(none)":
            ug = fetch_grants_to_user(
                id(manager), gr_usr_acc, gr_user_sel)
            if not ug.empty:
                role_c = next((col for col in ["role","ROLE"]
                                if col in ug.columns), None)
                if role_c:
                    env_c2 = get_env_color(gr_usr_acc)
                    for r in ug[role_c].tolist():
                        st.markdown(
                            _grant_row(r, env_c2),
                            unsafe_allow_html=True)
                else:
                    st.dataframe(ug, use_container_width=True,
                                  hide_index=True)
            else:
                st.info(f"No roles granted to {gr_user_sel}.")

    with gr_tab2:
        grc1, grc2 = st.columns(2)
        with grc1:
            gr_role_acc = st.selectbox("Account", connected,
                                        key="gr_role_acc")
        with grc2:
            gr_rdf      = fetch_roles(id(manager), gr_role_acc)
            gr_r_nc     = next((col for col in ["name","NAME"]
                                 if col in gr_rdf.columns), None)
            gr_role_list = (gr_rdf[gr_r_nc].tolist()
                             if gr_r_nc and not gr_rdf.empty else [])
            gr_role_sel = st.selectbox(
                "Select Role",
                options=gr_role_list or ["(none)"],
                key="gr_role_sel")

        if gr_role_sel and gr_role_sel != "(none)":
            rt1, rt2 = st.tabs(["Privileges","Members"])

            with rt1:
                rg_privs = fetch_grants_to_role(
                    id(manager), gr_role_acc, gr_role_sel)
                if not rg_privs.empty:
                    priv_c = next((col for col in [
                        "privilege","PRIVILEGE"]
                        if col in rg_privs.columns), None)
                    obj_c  = next((col for col in [
                        "granted_on","GRANTED_ON"]
                        if col in rg_privs.columns), None)
                    n_c    = next((col for col in ["name","NAME"]
                                    if col in rg_privs.columns), None)

                    if priv_c and obj_c:
                        for _, g in rg_privs.iterrows():
                            priv    = g.get(priv_c, "?")
                            obj_typ = g.get(obj_c, "?")
                            obj_n   = g.get(n_c,"?") if n_c else "?"
                            p_color = (
                                c("green")
                                if priv in ("SELECT","USAGE")
                                else c("pwc_orange")
                                if priv in ("INSERT","UPDATE",
                                             "DELETE","MODIFY")
                                else c("red")
                                if priv == "ALL PRIVILEGES"
                                else c("blue")
                            )
                            st.markdown(
                                _priv_row(priv, obj_typ,
                                           obj_n, p_color),
                                unsafe_allow_html=True)
                    else:
                        st.dataframe(rg_privs,
                                      use_container_width=True,
                                      hide_index=True)
                else:
                    st.info(f"No privileges for {gr_role_sel}.")

            with rt2:
                rg_members = fetch_grants_of_role(
                    id(manager), gr_role_acc, gr_role_sel)
                if not rg_members.empty:
                    st.dataframe(rg_members,
                                  use_container_width=True,
                                  hide_index=True)
                else:
                    st.info(f"No members in {gr_role_sel}.")

    with gr_tab3:
        section_header("GRANT / REVOKE")

        action = st.radio("Action", ["Grant","Revoke"],
                           horizontal=True, key="gr_action")
        gc_a1, gc_a2 = st.columns(2)

        with gc_a1:
            gr_acc3 = st.selectbox("Account", connected,
                                    key="gr_acc3")
            gr_type = st.selectbox(
                "Grant Type",
                ["Role to User","Role to Role",
                 "Privilege to Role"],
                key="gr_type")

        with gc_a2:
            all_roles_df  = fetch_roles(id(manager), gr_acc3)
            all_r_nc      = next((col for col in ["name","NAME"]
                                   if col in all_roles_df.columns),
                                 None)
            all_role_names = (all_roles_df[all_r_nc].tolist()
                               if all_r_nc and not all_roles_df.empty
                               else [])

            if gr_type == "Role to User":
                gr_role3  = st.selectbox("Role",
                                          all_role_names,
                                          key="gr_role3")
                all_u_df  = fetch_users(id(manager), gr_acc3)
                au_nc     = next((col for col in ["name","NAME"]
                                   if col in all_u_df.columns), None)
                gr_to_user3 = st.selectbox(
                    "User",
                    (all_u_df[au_nc].tolist()
                     if au_nc and not all_u_df.empty else []),
                    key="gr_to_user3")
                if gr_role3 and gr_to_user3:
                    v   = "GRANT" if action == "Grant" else "REVOKE"
                    p   = "TO"    if action == "Grant" else "FROM"
                    sql = (f'{v} ROLE "{gr_role3}" '
                           f'{p} USER "{gr_to_user3}";')
                    st.markdown(_sql_block(sql),
                                 unsafe_allow_html=True)
                    if st.button(f"▶️ {action}", type="primary",
                                  key="btn_grant_role_user"):
                        ok, msg = run_statement(gr_acc3, sql)
                        if ok:
                            st.success(f"✅ {action}ed!")
                            st.cache_data.clear()
                        else:
                            st.error(f"❌ {msg}")

            elif gr_type == "Role to Role":
                gr_child  = st.selectbox("Child Role",
                                          all_role_names,
                                          key="gr_child_role")
                gr_parent = st.selectbox("Parent Role",
                                          all_role_names,
                                          key="gr_parent_role2")
                if gr_child and gr_parent:
                    v   = "GRANT" if action == "Grant" else "REVOKE"
                    p   = "TO"    if action == "Grant" else "FROM"
                    sql = (f'{v} ROLE "{gr_child}" '
                           f'{p} ROLE "{gr_parent}";')
                    st.markdown(_sql_block(sql),
                                 unsafe_allow_html=True)
                    if st.button(f"▶️ {action}", type="primary",
                                  key="btn_grant_role_role"):
                        ok, msg = run_statement(gr_acc3, sql)
                        if ok:
                            st.success(f"✅ {action}ed!")
                            st.cache_data.clear()
                        else:
                            st.error(f"❌ {msg}")

            else:
                priv_role = st.selectbox("Target Role",
                                          all_role_names,
                                          key="priv_role3")
                priv_type = st.selectbox(
                    "Privilege",
                    ["SELECT","INSERT","UPDATE","DELETE",
                     "USAGE","CREATE TABLE","MONITOR",
                     "OPERATE","ALL PRIVILEGES"],
                    key="priv_type3")
                obj_type  = st.selectbox(
                    "Object Type",
                    ["TABLE","VIEW","SCHEMA","DATABASE",
                     "WAREHOUSE","STAGE","PROCEDURE","FUNCTION"],
                    key="obj_type3")
                obj_name  = st.text_input(
                    "Object Name (fully qualified)",
                    placeholder='"MY_DB"."MY_SCHEMA"."MY_TABLE"',
                    key="obj_name3")
                if priv_role and priv_type and obj_name:
                    v   = "GRANT" if action == "Grant" else "REVOKE"
                    p   = "TO"    if action == "Grant" else "FROM"
                    sql = (f'{v} {priv_type} ON '
                           f'{obj_type} {obj_name} '
                           f'{p} ROLE "{priv_role}";')
                    st.markdown(_sql_block(sql),
                                 unsafe_allow_html=True)
                    if st.button(f"▶️ {action}", type="primary",
                                  key="btn_grant_priv"):
                        ok, msg = run_statement(gr_acc3, sql)
                        if ok:
                            st.success(f"✅ {action}ed!")
                            st.cache_data.clear()
                        else:
                            st.error(f"❌ {msg}")


# ═══════════════════════════════════════════════════════
# TAB 7 — ACTIVITY
# ═══════════════════════════════════════════════════════

with tab_activity:
    section_header("USER ACTIVITY & LOGIN HISTORY")

    ac_c1, ac_c2 = st.columns(2)
    with ac_c1:
        act_acc  = st.selectbox("Account", connected,
                                  key="act_acc")
    with ac_c2:
        act_days = st.selectbox(
            "Time Range", [1,7,14,30,90], index=2,
            format_func=lambda x: f"Last {x} days",
            key="act_days")

    login_df  = fetch_login_history(
        id(manager), act_acc, act_days)
    access_df = fetch_access_history(
        id(manager), act_acc, act_days)

    if not login_df.empty:
        succ_c = next((col for col in ["is_success","IS_SUCCESS"]
                        if col in login_df.columns), None)
        user_c = next((col for col in ["user_name","USER_NAME"]
                        if col in login_df.columns), None)
        ts_c   = next((col for col in [
            "event_timestamp","EVENT_TIMESTAMP"]
            if col in login_df.columns), None)

        n_total   = len(login_df)
        n_success = (len(login_df[
            login_df[succ_c].astype(str).str.upper() == "YES"])
            if succ_c else 0)
        n_failed  = n_total - n_success
        n_unique  = login_df[user_c].nunique() if user_c else 0

        lk1, lk2, lk3, lk4 = st.columns(4)
        lk1.metric("Total Logins",  f"{n_total:,}")
        lk2.metric("Successful",    f"{n_success:,}")
        lk3.metric("Failed",        f"{n_failed:,}")
        lk4.metric("Unique Users",  f"{n_unique}")

        st.markdown('<div style="height:8px;"></div>',
                     unsafe_allow_html=True)

        act_t1, act_t2, act_t3 = st.tabs([
            "📊 Login Analytics",
            "👤 User Activity",
            "🔍 Access History",
        ])

        with act_t1:
            if ts_c:
                login_df[ts_c] = pd.to_datetime(
                    login_df[ts_c], errors="coerce")
                login_df["DATE"] = login_df[ts_c].dt.date

                a1, a2 = st.columns(2)
                with a1:
                    if succ_c:
                        daily = login_df.groupby(
                            ["DATE", succ_c]
                        ).size().reset_index(name="Count")
                        daily["Status"] = (
                            daily[succ_c].astype(str)
                            .str.upper()
                            .map({"YES":"Success","NO":"Failed"}))
                        fig = px.bar(
                            daily, x="DATE", y="Count",
                            color="Status",
                            color_discrete_map={
                                "Success": c("green"),
                                "Failed":  c("red")},
                            title="Login Attempts per Day",
                            height=320, barmode="stack")
                        fig.update_layout(
                            xaxis_title="", yaxis_title="Logins",
                            legend_title_text="")
                        st.plotly_chart(
                            fig, use_container_width=True,
                            key="act_login_bar")
                with a2:
                    if user_c:
                        top_u = (login_df.groupby(user_c)
                                  .size()
                                  .reset_index(name="Logins")
                                  .nlargest(10,"Logins"))
                        fig2 = px.bar(
                            top_u, x="Logins", y=user_c,
                            orientation="h", height=320,
                            title="Top 10 Users by Logins",
                            color="Logins",
                            color_continuous_scale=[
                                c("bg_elevated","#1b2431"),
                                c("pwc_orange")])
                        fig2.update_layout(
                            yaxis_title="",
                            coloraxis_showscale=False)
                        st.plotly_chart(
                            fig2, use_container_width=True,
                            key="act_top_users")

                if succ_c and n_failed > 0:
                    failed_df = login_df[
                        login_df[succ_c].astype(str)
                        .str.upper() == "NO"]
                    st.markdown(
                        _alert(
                            f"⚠️ {n_failed} failed login "
                            f"attempt(s) detected",
                            c("red"), "❌"),
                        unsafe_allow_html=True)
                    fail_cols = [col for col in [
                        "USER_NAME","ERROR_MESSAGE",
                        "CLIENT_IP","EVENT_TIMESTAMP",
                        "REPORTED_CLIENT_TYPE"]
                        if col in failed_df.columns]
                    st.dataframe(failed_df[fail_cols].head(50),
                                  use_container_width=True,
                                  hide_index=True)

        with act_t2:
            if user_c and succ_c and ts_c:
                summary = (login_df.groupby(user_c)
                            .agg(
                                Total=(user_c,"count"),
                                Success=(succ_c,
                                          lambda x: (
                                              x.astype(str)
                                              .str.upper()
                                              == "YES").sum()),
                                Last_Login=(ts_c,"max"))
                            .reset_index())
                summary["Failed"]   = (summary["Total"]
                                        - summary["Success"])
                summary["Success%"] = (summary["Success"]
                                        / summary["Total"]
                                        * 100).round(1)
                st.dataframe(
                    summary.sort_values(
                        "Total", ascending=False),
                    use_container_width=True,
                    hide_index=True, height=450)

        with act_t3:
            if not access_df.empty:
                st.markdown(
                    f'<div style="font-size:0.72rem;'
                    f'color:{c("text_muted")};'
                    f'margin-bottom:8px;">'
                    f'{len(access_df)} access event(s)</div>',
                    unsafe_allow_html=True)
                st.dataframe(access_df,
                              use_container_width=True,
                              hide_index=True, height=450)
            else:
                st.info("Access history requires Enterprise edition.")
    else:
        st.info("No login history found.")

# ─── Footer ───────────────────────────────────────────────────────────────────

st.markdown(
    f'<div style="text-align:center;padding:28px 0 10px;'
    f'border-top:1px solid {c("border")};margin-top:32px;">'
    f'<div style="font-size:0.78rem;font-weight:800;'
    f'color:{c("text_primary")};">'
    f'👥 Users &amp; Roles'
    f'&nbsp;·&nbsp;'
    f'<span style="color:{c("pwc_orange")};font-weight:800;'
    f'font-size:0.68rem;text-transform:uppercase;'
    f'letter-spacing:0.12em;">Powered By PwC Data &amp; AI</span>'
    f'</div>'
    f'<div style="margin-top:4px;font-size:0.66rem;'
    f'color:{c("text_dim","#5f6b7c")};">'
    f'{len(connected)} environment(s) connected'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True
)