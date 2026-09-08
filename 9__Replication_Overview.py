"""
🔄 Replication Management
Set up, initiate, and monitor Snowflake replication across environments.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import time

from snowflake_connector import SnowflakeConnectionManager
from theme import (
    inject_css, COLORS, CHART_COLORS, get_env_color,
    pwc_header, section_header, grafana_panel,
    kpi_card, stat_card, env_badge_html, env_badge, status_dot,
    premium_info_box
)
# ─── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Your Page · PwC",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded"
)
inject_css()


# ─── Extra CSS ────────────────────────────────────────────────────────────────

st.markdown(f"""
<style>
    /* Replication-specific styles */
    .repl-status-card {{
        background: {COLORS["bg_card"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 12px;
        padding: 20px;
        position: relative;
        overflow: hidden;
        transition: all 0.3s ease;
        animation: fadeInUp 0.4s ease both;
    }}
    .repl-status-card:hover {{
        border-color: {COLORS["border_light"]};
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.3);
    }}
    .repl-status-card .accent-bar {{
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
    }}
    .repl-progress-track {{
        background: {COLORS["border"]};
        border-radius: 6px;
        height: 8px;
        overflow: hidden;
        margin: 8px 0;
    }}
    .repl-progress-fill {{
        height: 100%;
        border-radius: 6px;
        transition: width 0.6s cubic-bezier(0.4,0,0.2,1);
        position: relative;
    }}
    .repl-progress-fill::after {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: linear-gradient(90deg,
            transparent 0%, rgba(255,255,255,0.15) 50%, transparent 100%);
        animation: shimmer 1.5s infinite;
    }}
    @keyframes shimmer {{
        0%   {{ transform: translateX(-100%); }}
        100% {{ transform: translateX(100%); }}
    }}
    .timeline-item {{
        display: flex;
        gap: 14px;
        padding: 12px 0;
        border-bottom: 1px solid {COLORS["border"]};
        animation: fadeInUp 0.3s ease;
    }}
    .timeline-item:last-child {{ border-bottom: none; }}
    .timeline-dot {{
        width: 10px; height: 10px;
        border-radius: 50%;
        margin-top: 4px;
        flex-shrink: 0;
    }}
    .timeline-connector {{
        width: 2px;
        background: {COLORS["border"]};
        margin: 0 4px;
        flex-shrink: 0;
    }}
    .setup-step {{
        background: {COLORS["bg_card"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 12px;
        transition: all 0.3s ease;
    }}
    .setup-step:hover {{
        border-color: {COLORS["pwc_orange"]}55;
    }}
    .setup-step-num {{
        width: 28px; height: 28px;
        border-radius: 50%;
        background: {COLORS["pwc_orange"]};
        color: white;
        font-size: 0.75rem;
        font-weight: 700;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        margin-right: 10px;
        flex-shrink: 0;
    }}
    .info-pill {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.68rem;
        font-weight: 600;
        border: 1px solid;
    }}
    .sql-block {{
        background: {COLORS["bg_secondary"]};
        border: 1px solid {COLORS["border"]};
        border-left: 3px solid {COLORS["pwc_orange"]};
        border-radius: 0 8px 8px 0;
        padding: 14px 16px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        color: {COLORS["text_secondary"]};
        line-height: 1.6;
        white-space: pre-wrap;
        word-break: break-all;
    }}
    .alert-banner {{
        padding: 12px 16px;
        border-radius: 8px;
        border: 1px solid;
        display: flex;
        align-items: flex-start;
        gap: 10px;
        margin-bottom: 12px;
        animation: fadeInUp 0.3s ease;
    }}
</style>
""", unsafe_allow_html=True)

# ─── Sidebar ──────────────────────────────────────────────────────────────────

manager = SnowflakeConnectionManager()
connected = manager.get_connected_accounts()

st.sidebar.markdown(f"""
<div style="padding:20px 16px 12px; border-bottom:1px solid {COLORS['border']};">
    <div style="display:flex; align-items:center; gap:10px;">
        <span style="font-size:1.6rem;">🔄</span>
        <div>
            <div style="font-size:0.95rem; font-weight:700;
                 color:{COLORS['text_primary']};">Replication</div>
            <div style="font-size:0.55rem; color:{COLORS['pwc_orange']};
                 font-weight:700; text-transform:uppercase; letter-spacing:2px;">
                 PwC Data & AI</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"""
<div style="padding:12px 16px 4px;
     font-size:0.6rem; color:{COLORS['text_muted']};
     text-transform:uppercase; letter-spacing:1.2px;">
     Connected Environments</div>
""", unsafe_allow_html=True)

for acc in connected:
    color = get_env_color(acc)
    st.sidebar.markdown(f"""
    <div class="sb-account">
        <div style="width:8px; height:8px; border-radius:50%;
             background:{color}; box-shadow:0 0 6px {color};
             flex-shrink:0;"></div>
        <div style="font-size:0.82rem; font-weight:600;
             color:{color};">{acc}</div>
    </div>""", unsafe_allow_html=True)

if not connected:
    st.sidebar.warning("No accounts connected.")

st.sidebar.markdown("---")
auto_refresh = st.sidebar.checkbox("⚡ Auto-refresh (30s)", value=False)
if st.sidebar.button("🔄 Refresh Now", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# ─── Header ───────────────────────────────────────────────────────────────────

pwc_header(
    "Replication Management",
    subtitle="Set up, initiate and monitor Snowflake database replication across environments"
)

if not connected:
    st.markdown(f"""
    <div style="background:{COLORS['bg_card']};
         border:2px dashed {COLORS['border_light']};
         border-radius:12px; padding:60px; text-align:center;">
        <div style="font-size:2.5rem; margin-bottom:12px;">🔌</div>
        <div style="color:{COLORS['text_secondary']}; font-weight:500;">
            Connect to at least two accounts to manage replication</div>
    </div>""", unsafe_allow_html=True)
    st.stop()

# ─── Helper Functions ─────────────────────────────────────────────────────────

def run_query(account: str, sql: str) -> pd.DataFrame:
    """Execute a SQL statement on an account."""
    return manager.execute_query(account, sql)


def run_statement(account: str, sql: str) -> tuple[bool, str]:
    """Execute a DDL/DML statement. Returns (success, message)."""
    conn = manager.get_connection(account)
    if not conn:
        return False, f"Not connected to {account}"
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        cursor.close()
        return True, "Success"
    except Exception as e:
        return False, str(e)


@st.cache_data(ttl=30, show_spinner=False)
def fetch_replication_databases(_mgr_id: int, account: str) -> pd.DataFrame:
    """Fetch all databases with replication info."""
    try:
        df = run_query(account, "SHOW REPLICATION DATABASES")
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=30, show_spinner=False)
def fetch_replication_groups(_mgr_id: int, account: str) -> pd.DataFrame:
    """Fetch replication groups."""
    try:
        df = run_query(account, "SHOW REPLICATION GROUPS")
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=30, show_spinner=False)
def fetch_failover_groups(_mgr_id: int, account: str) -> pd.DataFrame:
    """Fetch failover groups."""
    try:
        df = run_query(account, "SHOW FAILOVER GROUPS")
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=30, show_spinner=False)
def fetch_replication_history(_mgr_id: int, account: str,
                               days: int = 7) -> pd.DataFrame:
    """Fetch replication history from ACCOUNT_USAGE."""
    try:
        df = run_query(account, f"""
            SELECT
                DATABASE_NAME,
                REPLICATION_GROUP_NAME,
                JOB_UUID,
                PHASE_NAME,
                START_TIME,
                END_TIME,
                TOTAL_BYTES_REPLICATED,
                TOTAL_OBJECT_COUNT,
                CREDITS_USED,
                STATUS,
                ERROR_CODE,
                ERROR_MESSAGE,
                DATEDIFF('second', START_TIME, END_TIME) AS DURATION_SEC
            FROM SNOWFLAKE.ACCOUNT_USAGE.REPLICATION_USAGE_HISTORY
            WHERE START_TIME >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
            ORDER BY START_TIME DESC
            LIMIT 500
        """)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=30, show_spinner=False)
def fetch_replication_group_usage(_mgr_id: int, account: str,
                                   days: int = 7) -> pd.DataFrame:
    """Fetch replication group refresh history."""
    try:
        df = run_query(account, f"""
            SELECT
                REPLICATION_GROUP_NAME,
                CREDITS_USED,
                BYTES_TRANSFERRED,
                OBJECT_COUNT,
                START_TIME,
                END_TIME,
                PHASE_NAME,
                STATUS,
                DATEDIFF('second', START_TIME, END_TIME) AS DURATION_SEC
            FROM SNOWFLAKE.ACCOUNT_USAGE.REPLICATION_GROUP_USAGE_HISTORY
            WHERE START_TIME >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
            ORDER BY START_TIME DESC
            LIMIT 500
        """)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=30, show_spinner=False)
def fetch_databases(_mgr_id: int, account: str) -> list:
    """Get list of databases for an account."""
    try:
        df = run_query(account, "SHOW DATABASES")
        if df is not None and not df.empty and "name" in df.columns:
            return df["name"].tolist()
    except Exception:
        pass
    return []


def get_account_identifier(account: str) -> str:
    """Get the full account identifier (org.account)."""
    try:
        df = run_query(account, """
            SELECT CURRENT_ORGANIZATION_NAME() || '.' ||
                   CURRENT_ACCOUNT_NAME() AS FULL_IDENTIFIER
        """)
        if df is not None and not df.empty:
            return str(df.iloc[0]["FULL_IDENTIFIER"])
    except Exception:
        pass
    return account


def format_bytes(b: float) -> str:
    if not b or b == 0:
        return "0 B"
    for unit in ["B","KB","MB","GB","TB"]:
        if abs(b) < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


def status_badge(status: str) -> str:
    s = str(status).upper() if status else "UNKNOWN"
    if s in ("SUCCESS", "SUCCEEDED", "COMPLETED"):
        return (f'<span class="info-pill" style="color:{COLORS["green"]}; '
                f'border-color:{COLORS["green"]}33; '
                f'background:{COLORS["green"]}10;">✅ {s}</span>')
    elif s in ("FAILED", "ERROR", "FAIL"):
        return (f'<span class="info-pill" style="color:{COLORS["red"]}; '
                f'border-color:{COLORS["red"]}33; '
                f'background:{COLORS["red"]}10;">❌ {s}</span>')
    elif s in ("RUNNING", "IN_PROGRESS", "EXECUTING"):
        return (f'<span class="info-pill" style="color:{COLORS["blue"]}; '
                f'border-color:{COLORS["blue"]}33; '
                f'background:{COLORS["blue"]}10;">'
                f'🔄 {s}</span>')
    else:
        return (f'<span class="info-pill" style="color:{COLORS["text_muted"]}; '
                f'border-color:{COLORS["border"]}; '
                f'background:{COLORS["bg_elevated"]};">⏸ {s}</span>')


# ─── Main Tabs ────────────────────────────────────────────────────────────────

tab_overview, tab_setup, tab_groups, tab_initiate, tab_monitor, tab_history, tab_failover, tab_failback = st.tabs([
    "📊  Overview",
    "⚙️  Setup",
    "🗂️  Groups",
    "▶️  Initiate",
    "📡  Monitor",
    "📜  History",
    "🔀  Failover",
    "↩️  Failback",
])

# ─── Extra Helper Functions for Failover/Failback ────────────────────────────

@st.cache_data(ttl=30, show_spinner=False)
def fetch_failover_group_status(_mgr_id: int, account: str) -> pd.DataFrame:
    """Fetch detailed failover group status including primary/secondary role."""
    try:
        df = run_query(account, "SHOW FAILOVER GROUPS")
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=30, show_spinner=False)
def fetch_failover_history(_mgr_id: int, account: str,
                            days: int = 30) -> pd.DataFrame:
    """Fetch failover/failback history from ACCOUNT_USAGE."""
    try:
        df = run_query(account, f"""
            SELECT
                REPLICATION_GROUP_NAME,
                JOB_UUID,
                PHASE_NAME,
                START_TIME,
                END_TIME,
                CREDITS_USED,
                BYTES_TRANSFERRED,
                OBJECT_COUNT,
                STATUS,
                ERROR_CODE,
                ERROR_MESSAGE,
                DATEDIFF('second', START_TIME, END_TIME) AS DURATION_SEC
            FROM SNOWFLAKE.ACCOUNT_USAGE.REPLICATION_GROUP_USAGE_HISTORY
            WHERE START_TIME >= DATEADD('day', -{days}, CURRENT_TIMESTAMP())
            ORDER BY START_TIME DESC
            LIMIT 200
        """)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def get_all_failover_groups_with_role() -> dict:
    """
    Returns dict of:
    { account_name: { group_name: { is_primary, object_types, allowed_accounts } } }
    """
    result = {}
    for acc in connected:
        fg_df = fetch_failover_group_status(id(manager), acc)
        if fg_df.empty:
            result[acc] = {}
            continue
        groups = {}
        for _, row in fg_df.iterrows():
            name = row.get("name", "?")
            groups[name] = {
                "is_primary":      str(row.get("is_primary",      "")).upper() == "Y",
                "object_types":    row.get("object_types",    "N/A"),
                "allowed_accounts":row.get("allowed_accounts", "N/A"),
                "primary_url":     row.get("primary",          "N/A"),
                "comment":         row.get("comment",           ""),
                "raw":             row.to_dict(),
            }
        result[acc] = groups
    return result

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═════════════════════════════════════════════════════════════════════════════

with tab_overview:
    section_header("REPLICATION OVERVIEW")

    # KPI row
    all_repl_dbs   = []
    all_repl_groups = []

    for acc in connected:
        rdb = fetch_replication_databases(id(manager), acc)
        if not rdb.empty:
            all_repl_dbs.append(rdb)
        rg = fetch_replication_groups(id(manager), acc)
        if not rg.empty:
            all_repl_groups.append(rg)

    total_repl_dbs    = sum(len(d) for d in all_repl_dbs)
    total_repl_groups = sum(len(g) for g in all_repl_groups)

    kpi_cols = st.columns(4)
    kpis = [
        ("🌍", str(len(connected)),      "Environments",       COLORS["pwc_orange"], None),
        ("🗄️",  str(total_repl_dbs),     "Replicated DBs",     COLORS["blue"],       None),
        ("🗂️",  str(total_repl_groups),  "Replication Groups", COLORS["pwc_gold"],   None),
        ("❄️",  str(len(connected)),     "Connected Accounts", COLORS["cyan"],       None),
    ]
    for col, (ico, val, lbl, clr, sub) in zip(kpi_cols, kpis):
        with col:
            st.markdown(kpi_card(ico, val, lbl, clr, sub), unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Per-account replication status
    section_header("PER-ENVIRONMENT REPLICATION STATUS")

    for acc in connected:
        env_color = get_env_color(acc)
        repl_dbs  = fetch_replication_databases(id(manager), acc)

        with st.expander(
            f"{'🟢' if not repl_dbs.empty else '⚪'} {acc} — "
            f"{len(repl_dbs)} replicated database(s)",
            expanded=True
        ):
            if repl_dbs.empty:
                st.markdown(f"""
                <div style="background:{COLORS['bg_elevated']};
                     border:1px dashed {COLORS['border_light']};
                     border-radius:8px; padding:24px; text-align:center;">
                    <div style="color:{COLORS['text_muted']}; font-size:0.85rem;">
                        No replication configured for this environment.
                        Use the ⚙️ Setup tab to enable replication.
                    </div>
                </div>""", unsafe_allow_html=True)
            else:
                # Show replication databases table
                disp_cols = [c for c in [
                    "name", "origin", "owner", "replication_allowed_to_accounts",
                    "failover_allowed_to_accounts", "comment"
                ] if c in repl_dbs.columns]

                if "_ACCOUNT" in repl_dbs.columns:
                    repl_dbs = repl_dbs.drop(columns=["_ACCOUNT"])

                st.dataframe(
                    repl_dbs[disp_cols] if disp_cols else repl_dbs,
                    use_container_width=True,
                    hide_index=True
                )

    # Replication history summary
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    section_header("RECENT REPLICATION ACTIVITY")

    days_sel = st.select_slider(
        "History window",
        options=[1, 3, 7, 14, 30],
        value=7,
        key="ov_days"
    )

    hist_dfs = []
    for acc in connected:
        hdf = fetch_replication_history(id(manager), acc, days_sel)
        if not hdf.empty:
            hist_dfs.append(hdf)

    if hist_dfs:
        hist_df = pd.concat(hist_dfs, ignore_index=True)

        # Numeric conversions
        for col in ["TOTAL_BYTES_REPLICATED", "CREDITS_USED",
                    "DURATION_SEC", "TOTAL_OBJECT_COUNT"]:
            if col in hist_df.columns:
                hist_df[col] = pd.to_numeric(hist_df[col], errors="coerce")

        # Summary metrics
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Jobs", len(hist_df))
        m2.metric("Data Transferred",
                  format_bytes(hist_df["TOTAL_BYTES_REPLICATED"].sum()
                               if "TOTAL_BYTES_REPLICATED" in hist_df.columns else 0))
        m3.metric("Credits Used",
                  f"{hist_df['CREDITS_USED'].sum():.2f}"
                  if "CREDITS_USED" in hist_df.columns else "N/A")
        m4.metric("Avg Duration",
                  f"{hist_df['DURATION_SEC'].mean():.0f}s"
                  if "DURATION_SEC" in hist_df.columns else "N/A")
        if "STATUS" in hist_df.columns:
            fails = len(hist_df[hist_df["STATUS"].str.upper().isin(
                ["FAILED","ERROR","FAIL"])])
            m5.metric("Failed Jobs", fails,
                      delta=f"{fails/len(hist_df)*100:.0f}% fail rate",
                      delta_color="inverse")

        # Timeline chart
        if "START_TIME" in hist_df.columns:
            hist_df["START_TIME"] = pd.to_datetime(hist_df["START_TIME"])
            hist_df["DATE"] = hist_df["START_TIME"].dt.date
            daily = hist_df.groupby(["DATE", "_ACCOUNT"]).agg(
                Jobs=("STATUS", "count"),
                Bytes=("TOTAL_BYTES_REPLICATED", "sum"),
                Credits=("CREDITS_USED", "sum")
            ).reset_index()

            c1, c2 = st.columns(2)
            with c1:
                cmap = {n: get_env_color(n)
                        for n in daily["_ACCOUNT"].unique()}
                fig  = px.bar(
                    daily, x="DATE", y="Jobs", color="_ACCOUNT",
                    color_discrete_map=cmap,
                    title="Replication Jobs per Day",
                    height=320, barmode="group"
                )
                fig.update_layout(xaxis_title="", yaxis_title="Jobs",
                                  legend_title_text="")
                st.plotly_chart(fig, use_container_width=True,
                                key="ov_jobs_day")
            with c2:
                fig2 = px.area(
                    daily, x="DATE", y="Credits", color="_ACCOUNT",
                    color_discrete_map=cmap,
                    title="Replication Credits per Day",
                    height=320
                )
                fig2.update_layout(xaxis_title="", yaxis_title="Credits",
                                   legend_title_text="")
                st.plotly_chart(fig2, use_container_width=True,
                                key="ov_cred_day")
    else:
        st.info("No replication history found. "
                "Replication may not be configured yet.")


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — SETUP
# ═════════════════════════════════════════════════════════════════════════════

with tab_setup:
    section_header("ENABLE DATABASE REPLICATION")

    st.markdown(f"""
    <div class="alert-banner"
         style="border-color:{COLORS['pwc_gold']}44;
                background:{COLORS['pwc_gold']}08; color:{COLORS['text_secondary']};">
        <span style="font-size:1.2rem;">💡</span>
        <div>
            <div style="font-weight:600; color:{COLORS['pwc_gold']};
                 margin-bottom:4px;">How Snowflake Replication Works</div>
            <div style="font-size:0.82rem; line-height:1.6;">
                1. <b>Enable replication</b> on the primary database and specify target accounts.<br>
                2. <b>Create a secondary database</b> on the target account as a replica.<br>
                3. <b>Refresh</b> the secondary database to pull latest changes.<br>
                4. Optionally create a <b>Replication Group</b> to replicate multiple objects together.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Step 1: Enable replication on primary ──────────────────────────────

    st.markdown(f"""
    <div class="setup-step">
        <div style="display:flex; align-items:center; margin-bottom:14px;">
            <span class="setup-step-num">1</span>
            <span style="font-weight:700; color:{COLORS['text_primary']};
                  font-size:0.95rem;">
                  Enable Replication on Primary Database</span>
        </div>
    """, unsafe_allow_html=True)

    s1c1, s1c2 = st.columns(2)
    with s1c1:
        primary_account = st.selectbox(
            "Primary Account (source)",
            options=connected,
            key="setup_primary_acc",
            help="The account that holds the source database"
        )
    with s1c2:
        primary_dbs = fetch_databases(id(manager), primary_account) \
            if primary_account else []
        primary_db = st.selectbox(
            "Database to Replicate",
            options=primary_dbs,
            key="setup_primary_db"
        )

    # Target accounts (all connected except primary)
    target_options = [a for a in connected if a != primary_account]
    target_accounts_sel = st.multiselect(
        "Allow Replication To (target accounts)",
        options=target_options,
        default=target_options[:1] if target_options else [],
        key="setup_targets",
        help="Select which accounts can replicate this database"
    )

    ignore_edition = st.checkbox(
        "Ignore edition check (IGNORE EDITION CHECK)",
        value=True,
        key="setup_ignore_edition",
        help="Required when replicating between different Snowflake editions"
    )

    if primary_db and target_accounts_sel:
        # Build target account identifiers
        target_ids = []
        for ta in target_accounts_sel:
            tid = get_account_identifier(ta)
            target_ids.append(tid)

        targets_str   = ", ".join(target_ids)
        ignore_clause = "IGNORE EDITION CHECK" if ignore_edition else ""
        enable_sql    = (
            f'ALTER DATABASE "{primary_db}"\n'
            f'    ENABLE REPLICATION TO ACCOUNTS {targets_str}\n'
            f'    {ignore_clause};'
        ).strip()

        st.markdown(f'<div class="sql-block">{enable_sql}</div>',
                    unsafe_allow_html=True)

        if st.button("▶️ Enable Replication", type="primary",
                      key="btn_enable_repl"):
            with st.spinner(f"Enabling replication on {primary_db}…"):
                ok, msg = run_statement(primary_account, enable_sql)
            if ok:
                st.success(
                    f"✅ Replication enabled on **{primary_db}** "
                    f"→ {', '.join(target_accounts_sel)}"
                )
                st.cache_data.clear()
            else:
                st.error(f"❌ {msg}")

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Step 2: Create secondary database ─────────────────────────────────

    st.markdown(f"""
    <div class="setup-step">
        <div style="display:flex; align-items:center; margin-bottom:14px;">
            <span class="setup-step-num">2</span>
            <span style="font-weight:700; color:{COLORS['text_primary']};
                  font-size:0.95rem;">
                  Create Secondary (Replica) Database on Target</span>
        </div>
    """, unsafe_allow_html=True)

    s2c1, s2c2 = st.columns(2)
    with s2c1:
        secondary_account = st.selectbox(
            "Target Account (secondary)",
            options=connected,
            key="setup_sec_acc",
            help="Account that will receive the replica"
        )
    with s2c2:
        secondary_db_name = st.text_input(
            "Secondary Database Name",
            placeholder="e.g., MY_DB_REPLICA",
            key="setup_sec_db_name",
            help="Name for the replica database on the target account"
        )

    primary_full_name_input = st.text_input(
        "Primary Database Full Name (org.account.database)",
        placeholder="e.g., MYORG.PROD_ACCOUNT.MY_DATABASE",
        key="setup_primary_full",
        help=(
            "Full identifier of the primary database. "
            "Format: <org_name>.<account_name>.<db_name>"
        )
    )

    auto_refresh_sec = st.checkbox(
        "Enable AUTO REFRESH (data sharing)",
        value=False,
        key="setup_auto_refresh"
    )

    if secondary_db_name and primary_full_name_input:
        ar_clause   = "\n    DATA_RETENTION_TIME_IN_DAYS = 1\n    AUTO_REFRESH_MATERIALIZED_VIEWS_ON_SECONDARY = TRUE" \
                      if auto_refresh_sec else ""
        create_sql  = (
            f'CREATE DATABASE "{secondary_db_name}"\n'
            f'    AS REPLICA OF {primary_full_name_input}{ar_clause};'
        )
        st.markdown(f'<div class="sql-block">{create_sql}</div>',
                    unsafe_allow_html=True)

        if st.button("▶️ Create Secondary Database", type="primary",
                      key="btn_create_secondary"):
            with st.spinner(
                f"Creating secondary database on {secondary_account}…"
            ):
                ok, msg = run_statement(secondary_account, create_sql)
            if ok:
                st.success(
                    f"✅ Secondary database **{secondary_db_name}** "
                    f"created on **{secondary_account}**"
                )
                st.cache_data.clear()
            else:
                st.error(f"❌ {msg}")

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Step 3: Disable replication ───────────────────────────────────────

    with st.expander("🚫 Disable Replication (Advanced)"):
        d1, d2 = st.columns(2)
        with d1:
            disable_acc = st.selectbox("Account", connected, key="dis_acc")
        with d2:
            dis_dbs = fetch_databases(id(manager), disable_acc)
            disable_db = st.selectbox("Database", dis_dbs, key="dis_db")

        if disable_db:
            dis_sql = f'ALTER DATABASE "{disable_db}" DISABLE REPLICATION;'
            st.code(dis_sql, language="sql")
            if st.button("🚫 Disable Replication", key="btn_disable",
                          type="primary"):
                ok, msg = run_statement(disable_acc, dis_sql)
                if ok:
                    st.success(f"✅ Replication disabled on {disable_db}")
                    st.cache_data.clear()
                else:
                    st.error(f"❌ {msg}")


# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — REPLICATION GROUPS
# ═════════════════════════════════════════════════════════════════════════════

with tab_groups:
    section_header("REPLICATION & FAILOVER GROUPS")

    st.markdown(f"""
    <div class="alert-banner"
         style="border-color:{COLORS['blue']}44;
                background:{COLORS['blue']}08;
                color:{COLORS['text_secondary']};">
        <span style="font-size:1.2rem;">ℹ️</span>
        <div style="font-size:0.82rem; line-height:1.6;">
            <b style="color:{COLORS['blue']};">Replication Groups</b>
            allow you to replicate multiple Snowflake objects
            (databases, shares, integrations) together as a unit,
            with a single refresh operation.
        </div>
    </div>
    """, unsafe_allow_html=True)

    grp_tab1, grp_tab2, grp_tab3 = st.tabs([
        "📋 View Groups", "➕ Create Group", "🗑️ Drop Group"
    ])

    # View existing groups
    with grp_tab1:
        for acc in connected:
            env_color = get_env_color(acc)
            rg_df     = fetch_replication_groups(id(manager), acc)
            fg_df     = fetch_failover_groups(id(manager), acc)

            st.markdown(f"""
            <div style="margin-bottom:6px;">
                {env_badge_html(acc, True)}
            </div>""", unsafe_allow_html=True)

            r1, r2 = st.columns(2)
            with r1:
                st.markdown(f"""
                <div style="font-size:0.72rem; color:{COLORS['text_muted']};
                     text-transform:uppercase; letter-spacing:1px;
                     margin-bottom:8px;">
                     Replication Groups ({len(rg_df)})</div>
                """, unsafe_allow_html=True)
                if not rg_df.empty:
                    disp = [c for c in ["name","type","object_types",
                                         "allowed_accounts","primary",
                                         "is_primary","comment"]
                            if c in rg_df.columns]
                    st.dataframe(
                        rg_df[disp] if disp else rg_df,
                        use_container_width=True, hide_index=True
                    )
                else:
                    st.info("No replication groups found.")

            with r2:
                st.markdown(f"""
                <div style="font-size:0.72rem; color:{COLORS['text_muted']};
                     text-transform:uppercase; letter-spacing:1px;
                     margin-bottom:8px;">
                     Failover Groups ({len(fg_df)})</div>
                """, unsafe_allow_html=True)
                if not fg_df.empty:
                    disp = [c for c in ["name","type","object_types",
                                         "allowed_accounts","primary",
                                         "is_primary","comment"]
                            if c in fg_df.columns]
                    st.dataframe(
                        fg_df[disp] if disp else fg_df,
                        use_container_width=True, hide_index=True
                    )
                else:
                    st.info("No failover groups found.")

            st.markdown("---")

    # Create group
    with grp_tab2:
        gc1, gc2 = st.columns(2)
        with gc1:
            grp_source_acc = st.selectbox(
                "Primary Account",
                connected, key="grp_src_acc"
            )
            grp_name = st.text_input(
                "Group Name",
                placeholder="e.g., PROD_REPLICATION_GROUP",
                key="grp_name"
            )
            grp_type = st.selectbox(
                "Group Type",
                ["REPLICATION GROUP", "FAILOVER GROUP"],
                key="grp_type"
            )
        with gc2:
            grp_object_types = st.multiselect(
                "Object Types to Replicate",
                options=[
                    "DATABASES",
                    "SHARES",
                    "RESOURCE MONITORS",
                    "WAREHOUSES",
                    "GLOBAL SHARE",
                    "ACCOUNT PARAMETERS",
                    "NETWORK POLICIES",
                    "ROLES",
                    "USERS",
                    "INTEGRATIONS",
                    "NOTIFICATION SUBSCRIPTIONS",
                ],
                default=["DATABASES"],
                key="grp_obj_types"
            )
            grp_target_accs = [a for a in connected if a != grp_source_acc]
            grp_targets = st.multiselect(
                "Allowed Target Accounts",
                options=grp_target_accs,
                default=grp_target_accs[:1] if grp_target_accs else [],
                key="grp_targets"
            )

        # Databases to include
        if "DATABASES" in grp_object_types:
            grp_dbs_available = fetch_databases(id(manager), grp_source_acc)
            grp_dbs_selected  = st.multiselect(
                "Databases to include",
                options=grp_dbs_available,
                key="grp_dbs"
            )
        else:
            grp_dbs_selected = []

        if grp_name and grp_object_types and grp_targets:
            obj_types_str = ", ".join(grp_object_types)
            tgt_ids = []
            for ta in grp_targets:
                tgt_ids.append(get_account_identifier(ta))
            tgt_str = ", ".join(tgt_ids)

            if grp_dbs_selected:
                db_str = ", ".join(
                    [f'"{db}"' for db in grp_dbs_selected]
                )
                grp_sql = (
                    f'CREATE {grp_type} "{grp_name}"\n'
                    f'    OBJECT_TYPES = {obj_types_str}\n'
                    f'    ALLOWED_DATABASES = {db_str}\n'
                    f'    ALLOWED_ACCOUNTS = {tgt_str};'
                )
            else:
                grp_sql = (
                    f'CREATE {grp_type} "{grp_name}"\n'
                    f'    OBJECT_TYPES = {obj_types_str}\n'
                    f'    ALLOWED_ACCOUNTS = {tgt_str};'
                )

            st.markdown(f'<div class="sql-block">{grp_sql}</div>',
                        unsafe_allow_html=True)

            if st.button(f"▶️ Create {grp_type}", type="primary",
                          key="btn_create_grp"):
                with st.spinner(f"Creating {grp_name}…"):
                    ok, msg = run_statement(grp_source_acc, grp_sql)
                if ok:
                    st.success(f"✅ {grp_type} **{grp_name}** created!")
                    st.cache_data.clear()
                else:
                    st.error(f"❌ {msg}")

    # Drop group
    with grp_tab3:
        dr1, dr2 = st.columns(2)
        with dr1:
            drop_acc  = st.selectbox("Account", connected, key="drop_grp_acc")
            drop_type = st.selectbox(
                "Group Type",
                ["REPLICATION GROUP", "FAILOVER GROUP"],
                key="drop_grp_type"
            )
        with dr2:
            # Fetch existing group names
            existing_grp_df = fetch_replication_groups(id(manager), drop_acc)
            grp_names = existing_grp_df["name"].tolist() \
                        if not existing_grp_df.empty and "name" in existing_grp_df.columns \
                        else []
            drop_grp_name = st.selectbox(
                "Group Name",
                options=grp_names if grp_names else ["(none found)"],
                key="drop_grp_name"
            )

        if drop_grp_name and drop_grp_name != "(none found)":
            drop_sql = f'DROP {drop_type} "{drop_grp_name}";'
            st.code(drop_sql, language="sql")

            st.warning(
                f"⚠️ This will permanently drop **{drop_grp_name}**. "
                "This action cannot be undone."
            )
            confirm = st.checkbox("I understand, proceed with drop",
                                   key="confirm_drop_grp")
            if confirm:
                if st.button("🗑️ Drop Group", type="primary",
                              key="btn_drop_grp"):
                    ok, msg = run_statement(drop_acc, drop_sql)
                    if ok:
                        st.success(f"✅ {drop_type} **{drop_grp_name}** dropped.")
                        st.cache_data.clear()
                    else:
                        st.error(f"❌ {msg}")


# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — INITIATE REPLICATION
# ═════════════════════════════════════════════════════════════════════════════

with tab_initiate:
    section_header("INITIATE REPLICATION REFRESH")

    init_tab1, init_tab2 = st.tabs([
        "🗄️ Database Refresh", "🗂️ Group Refresh"
    ])

    # Database refresh
    with init_tab1:
        st.markdown(f"""
        <div class="alert-banner"
             style="border-color:{COLORS['green']}44;
                    background:{COLORS['green']}08;
                    color:{COLORS['text_secondary']};">
            <span>🔄</span>
            <div style="font-size:0.82rem;">
                Refresh a secondary database to pull the latest changes
                from the primary. Run this on the <b>target (secondary)</b> account.
            </div>
        </div>
        """, unsafe_allow_html=True)

        ir1, ir2 = st.columns(2)
        with ir1:
            refresh_acc = st.selectbox(
                "Target Account (secondary)",
                connected,
                key="refresh_acc",
                help="Run refresh on the secondary/replica side"
            )
        with ir2:
            refresh_dbs = fetch_databases(id(manager), refresh_acc)
            refresh_db  = st.selectbox(
                "Secondary Database",
                options=refresh_dbs,
                key="refresh_db"
            )

        resume_suspend = st.checkbox(
            "Auto-suspend warehouse after refresh",
            value=False, key="refresh_suspend"
        )

        if refresh_db:
            refresh_sql = f'ALTER DATABASE "{refresh_db}" REFRESH;'
            st.markdown(f'<div class="sql-block">{refresh_sql}</div>',
                        unsafe_allow_html=True)

            col_btn, col_status = st.columns([1, 3])
            with col_btn:
                run_refresh = st.button(
                    "▶️ Run Refresh", type="primary",
                    key="btn_db_refresh"
                )

            if run_refresh:
                progress_bar = st.progress(0, text="Initiating refresh…")
                with st.spinner(
                    f"Refreshing **{refresh_db}** on **{refresh_acc}**…"
                ):
                    ok, msg = run_statement(refresh_acc, refresh_sql)

                for pct in range(0, 101, 5):
                    time.sleep(0.03)
                    progress_bar.progress(
                        pct,
                        text=f"Running: {pct}%"
                        if pct < 100 else "Refresh complete!"
                    )

                if ok:
                    st.success(
                        f"✅ Refresh initiated for **{refresh_db}** "
                        f"on **{refresh_acc}**"
                    )
                    st.balloons()
                    st.cache_data.clear()
                else:
                    st.error(f"❌ Refresh failed: {msg}")

    # Group refresh
    with init_tab2:
        st.markdown(f"""
        <div class="alert-banner"
             style="border-color:{COLORS['blue']}44;
                    background:{COLORS['blue']}08;
                    color:{COLORS['text_secondary']};">
            <span>🗂️</span>
            <div style="font-size:0.82rem;">
                Refresh a replication or failover group to sync
                all included objects to the secondary account.
            </div>
        </div>
        """, unsafe_allow_html=True)

        gr1, gr2, gr3 = st.columns(3)
        with gr1:
            grp_refresh_acc = st.selectbox(
                "Account", connected, key="grp_refresh_acc"
            )
        with gr2:
            grp_type_sel = st.selectbox(
                "Group Type",
                ["REPLICATION GROUP", "FAILOVER GROUP"],
                key="grp_refresh_type"
            )
        with gr3:
            existing_grps = fetch_replication_groups(
                id(manager), grp_refresh_acc
            )
            grp_list = existing_grps["name"].tolist() \
                       if not existing_grps.empty and "name" in existing_grps.columns \
                       else []
            grp_refresh_name = st.selectbox(
                "Group Name",
                options=grp_list if grp_list else ["(none found)"],
                key="grp_refresh_name"
            )

        if grp_refresh_name and grp_refresh_name != "(none found)":
            grp_refresh_sql = (
                f'ALTER {grp_type_sel} "{grp_refresh_name}" REFRESH;'
            )
            st.markdown(f'<div class="sql-block">{grp_refresh_sql}</div>',
                        unsafe_allow_html=True)

            if st.button("▶️ Refresh Group", type="primary",
                          key="btn_grp_refresh"):
                progress_bar2 = st.progress(0, text="Starting group refresh…")
                with st.spinner(f"Refreshing group **{grp_refresh_name}**…"):
                    ok, msg = run_statement(grp_refresh_acc, grp_refresh_sql)

                for pct in range(0, 101, 5):
                    time.sleep(0.03)
                    progress_bar2.progress(pct)

                if ok:
                    st.success(
                        f"✅ Group **{grp_refresh_name}** refresh initiated!"
                    )
                    st.cache_data.clear()
                else:
                    st.error(f"❌ {msg}")

    # ── Batch Refresh ─────────────────────────────────────────────────────

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    section_header("BATCH REFRESH")

    with st.expander("🚀 Refresh Multiple Databases at Once"):
        batch_acc = st.selectbox(
            "Target Account",
            connected, key="batch_acc"
        )
        batch_dbs_available = fetch_databases(id(manager), batch_acc)
        batch_dbs_selected  = st.multiselect(
            "Select Databases to Refresh",
            options=batch_dbs_available,
            key="batch_dbs"
        )

        if batch_dbs_selected:
            st.markdown(
                f"**{len(batch_dbs_selected)} database(s) will be refreshed:**"
            )
            for db in batch_dbs_selected:
                st.markdown(
                    f'<div class="sql-block">'
                    f'ALTER DATABASE "{db}" REFRESH;</div>',
                    unsafe_allow_html=True
                )

            if st.button("▶️ Run Batch Refresh", type="primary",
                          key="btn_batch"):
                results = []
                prog = st.progress(0)
                for i, db in enumerate(batch_dbs_selected):
                    with st.spinner(f"Refreshing {db}… ({i+1}/{len(batch_dbs_selected)})"):
                        ok, msg = run_statement(
                            batch_acc, f'ALTER DATABASE "{db}" REFRESH;'
                        )
                    results.append({
                        "Database": db,
                        "Status":   "✅ Success" if ok else f"❌ {msg}"
                    })
                    prog.progress((i + 1) / len(batch_dbs_selected))

                st.dataframe(
                    pd.DataFrame(results),
                    use_container_width=True,
                    hide_index=True
                )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 5 — MONITOR (Live)
# ═════════════════════════════════════════════════════════════════════════════

with tab_monitor:
    section_header("LIVE REPLICATION MONITORING")

    # Auto-refresh
    if auto_refresh:
        st.markdown(f"""
        <div class="alert-banner"
             style="border-color:{COLORS['green']}44;
                    background:{COLORS['green']}08;">
            <span class="dot connected"
                  style="width:8px;height:8px;"></span>
            <span style="color:{COLORS['green']}; font-size:0.82rem;
                  font-weight:600;">Auto-refresh is ON (30s)</span>
        </div>
        """, unsafe_allow_html=True)
        time.sleep(30)
        st.rerun()

    mon_cols = st.columns(len(connected))
    for col_idx, acc in enumerate(connected):
        env_color = get_env_color(acc)
        with mon_cols[col_idx]:
            st.markdown(f"""
            <div style="background:{COLORS['bg_card']};
                 border:1px solid {COLORS['border']};
                 border-top:3px solid {env_color};
                 border-radius:12px; padding:16px;
                 margin-bottom:12px;">
                <div style="font-weight:700; color:{COLORS['text_primary']};
                     margin-bottom:12px; font-size:0.9rem;">
                    {env_badge_html(acc, True)} Live Status
                </div>
            </div>""", unsafe_allow_html=True)

            # Current replication groups and status
            rg_df = fetch_replication_groups(id(manager), acc)
            if not rg_df.empty:
                for _, grp in rg_df.iterrows():
                    grp_name   = grp.get("name", "?")
                    is_primary = str(grp.get("is_primary", "")).upper()
                    role_badge = (
                        f'<span class="info-pill" style="color:{COLORS["green"]}; '
                        f'border-color:{COLORS["green"]}33; '
                        f'background:{COLORS["green"]}10;">🏆 PRIMARY</span>'
                        if is_primary == "Y" else
                        f'<span class="info-pill" style="color:{COLORS["blue"]}; '
                        f'border-color:{COLORS["blue"]}33; '
                        f'background:{COLORS["blue"]}10;">🔄 SECONDARY</span>'
                    )
                    st.markdown(f"""
                    <div style="background:{COLORS['bg_elevated']};
                         border:1px solid {COLORS['border']};
                         border-radius:8px; padding:12px; margin-bottom:8px;">
                        <div style="font-weight:600; color:{COLORS['text_primary']};
                             margin-bottom:6px; font-size:0.85rem;">
                             🗂️ {grp_name}</div>
                        <div style="margin-bottom:6px;">{role_badge}</div>
                        <div style="font-size:0.7rem; color:{COLORS['text_muted']};">
                            Objects: {grp.get('object_types','N/A')}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background:{COLORS['bg_elevated']};
                     border:1px dashed {COLORS['border_light']};
                     border-radius:8px; padding:20px; text-align:center;">
                    <div style="color:{COLORS['text_muted']};
                         font-size:0.8rem;">No active groups</div>
                </div>""", unsafe_allow_html=True)

    # Live metrics from ACCOUNT_USAGE
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    section_header("REAL-TIME METRICS")

    mon_days = st.select_slider(
        "Monitoring window",
        options=[1, 3, 7], value=1,
        key="mon_days"
    )

    all_mon_hist = []
    for acc in connected:
        mh = fetch_replication_history(id(manager), acc, mon_days)
        if not mh.empty:
            all_mon_hist.append(mh)

    if all_mon_hist:
        mdf = pd.concat(all_mon_hist, ignore_index=True)

        for col in ["TOTAL_BYTES_REPLICATED", "CREDITS_USED",
                    "DURATION_SEC", "TOTAL_OBJECT_COUNT"]:
            if col in mdf.columns:
                mdf[col] = pd.to_numeric(mdf[col], errors="coerce")

        # Mini KPIs
        mk1, mk2, mk3, mk4 = st.columns(4)
        mk1.metric("Total Jobs",
                   len(mdf))
        mk2.metric("Data Moved",
                   format_bytes(mdf["TOTAL_BYTES_REPLICATED"].sum()
                                if "TOTAL_BYTES_REPLICATED" in mdf.columns else 0))
        mk3.metric("Credits Used",
                   f"{mdf['CREDITS_USED'].sum():.3f}"
                   if "CREDITS_USED" in mdf.columns else "N/A")
        if "STATUS" in mdf.columns:
            ok_count = len(mdf[mdf["STATUS"].str.upper()
                              .isin(["SUCCESS","SUCCEEDED","COMPLETED"])])
            mk4.metric("Success Rate",
                       f"{ok_count/len(mdf)*100:.0f}%")

        # Phase breakdown chart
        if "PHASE_NAME" in mdf.columns and "DURATION_SEC" in mdf.columns:
            phase_df = mdf.groupby(
                ["_ACCOUNT","PHASE_NAME"]
            )["DURATION_SEC"].mean().reset_index()
            phase_df.columns = ["Account","Phase","Avg Duration (s)"]

            c1, c2 = st.columns(2)
            with c1:
                cmap = {n: get_env_color(n)
                        for n in phase_df["Account"].unique()}
                fig  = px.bar(
                    phase_df, x="Phase",
                    y="Avg Duration (s)",
                    color="Account",
                    color_discrete_map=cmap,
                    height=320,
                    title="Avg Duration by Replication Phase",
                    barmode="group"
                )
                fig.update_layout(xaxis_title="",
                                  xaxis_tickangle=-30,
                                  legend_title_text="")
                st.plotly_chart(fig, use_container_width=True,
                                key="mon_phase_dur")
            with c2:
                if "TOTAL_BYTES_REPLICATED" in mdf.columns:
                    bytes_df = mdf.groupby(
                        "_ACCOUNT"
                    )["TOTAL_BYTES_REPLICATED"].sum().reset_index()
                    bytes_df["GB"] = bytes_df["TOTAL_BYTES_REPLICATED"] / 1e9
                    fig2 = px.pie(
                        bytes_df, values="GB", names="_ACCOUNT",
                        color="_ACCOUNT",
                        color_discrete_map={
                            n: get_env_color(n)
                            for n in bytes_df["_ACCOUNT"].unique()
                        },
                        height=320,
                        title="Data Transferred by Environment",
                        hole=0.55
                    )
                    st.plotly_chart(fig2, use_container_width=True,
                                    key="mon_bytes_pie")

        # Latest jobs table
        st.markdown(f"""
        <div style="font-size:0.7rem; color:{COLORS['text_muted']};
             text-transform:uppercase; letter-spacing:1px;
             margin:14px 0 8px;">Latest Replication Jobs</div>
        """, unsafe_allow_html=True)

        display_cols = [c for c in [
            "_ACCOUNT","DATABASE_NAME","PHASE_NAME",
            "STATUS","START_TIME","DURATION_SEC",
            "TOTAL_BYTES_REPLICATED","CREDITS_USED"
        ] if c in mdf.columns]

        st.dataframe(
            mdf[display_cols].rename(columns={
                "_ACCOUNT": "Account",
                "DATABASE_NAME": "Database",
                "PHASE_NAME": "Phase",
                "STATUS": "Status",
                "START_TIME": "Start Time",
                "DURATION_SEC": "Duration (s)",
                "TOTAL_BYTES_REPLICATED": "Bytes",
                "CREDITS_USED": "Credits"
            }).head(50),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info(
            "No replication activity found in the selected window. "
            "Try increasing the monitoring window or running a refresh."
        )

#-----------------------------------------------------------------------------
# TAB 7 - FAILOVER AND FAILBACK
#-----------------------------------------------------------------------------

# ═════════════════════════════════════════════════════════════════════════════
# TAB 7 — FAILOVER
# ═════════════════════════════════════════════════════════════════════════════

with tab_failover:

    # ── Extra CSS for failover/failback ───────────────────────────────────
    st.markdown(f"""
    <style>
        .fo-card {{
            background: {COLORS["bg_card"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 12px;
            transition: all 0.3s ease;
            animation: fadeInUp 0.4s ease both;
        }}
        .fo-card:hover {{
            border-color: {COLORS["border_light"]};
            box-shadow: 0 6px 24px rgba(0,0,0,0.3);
        }}
        .fo-primary {{
            border-left: 4px solid {COLORS["green"]};
        }}
        .fo-secondary {{
            border-left: 4px solid {COLORS["blue"]};
        }}
        .fo-warning {{
            border-left: 4px solid {COLORS["pwc_orange"]};
        }}
        .role-pill {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .checklist-item {{
            display: flex;
            align-items: flex-start;
            gap: 10px;
            padding: 10px 14px;
            background: {COLORS["bg_elevated"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 8px;
            margin-bottom: 8px;
            font-size: 0.82rem;
            color: {COLORS["text_secondary"]};
            transition: all 0.2s ease;
        }}
        .checklist-item:hover {{
            border-color: {COLORS["border_light"]};
        }}
        .checklist-icon {{ font-size: 1rem; flex-shrink: 0; margin-top: 1px; }}
        .impact-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 14px;
            background: {COLORS["bg_elevated"]};
            border-radius: 8px;
            margin-bottom: 6px;
            font-size: 0.82rem;
        }}
    </style>
    """, unsafe_allow_html=True)

    section_header("FAILOVER — PROMOTE SECONDARY TO PRIMARY")

    # ── What is failover banner ────────────────────────────────────────────
    st.markdown(f"""
    <div class="fo-card fo-warning">
        <div style="display:flex; align-items:flex-start; gap:14px;">
            <span style="font-size:1.8rem;">🔀</span>
            <div>
                <div style="font-weight:700; color:{COLORS['pwc_orange']};
                     font-size:0.95rem; margin-bottom:6px;">
                     What is Failover?</div>
                <div style="font-size:0.82rem; color:{COLORS['text_secondary']};
                     line-height:1.7;">
                    Failover <b>promotes a secondary (replica) failover group to
                    become the new primary</b>. The original primary becomes a
                    secondary. This is used for:
                    <ul style="margin:6px 0 0 0; padding-left:18px;">
                        <li>Disaster recovery when the primary account is unavailable</li>
                        <li>Planned maintenance on the primary account</li>
                        <li>Business continuity testing</li>
                    </ul>
                    <div style="margin-top:8px; color:{COLORS['pwc_gold']};
                         font-weight:600; font-size:0.78rem;">
                        ⚠️ Failover causes the secondary to become read-write and
                        the primary to become read-only temporarily.
                    </div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Current State Visualizer ───────────────────────────────────────────
    section_header("CURRENT FAILOVER GROUP TOPOLOGY")

    all_fg_roles = get_all_failover_groups_with_role()

    # Build a visual topology
    primary_groups   = {}   # { group_name: account }
    secondary_groups = {}   # { group_name: [accounts] }

    for acc, groups in all_fg_roles.items():
        for grp_name, grp_info in groups.items():
            if grp_info["is_primary"]:
                primary_groups[grp_name] = acc
            else:
                secondary_groups.setdefault(grp_name, []).append(acc)

    all_group_names = list(set(
        list(primary_groups.keys()) + list(secondary_groups.keys())
    ))

    if not all_group_names:
        st.markdown(f"""
        <div style="background:{COLORS['bg_elevated']};
             border:2px dashed {COLORS['border_light']};
             border-radius:12px; padding:40px; text-align:center;">
            <div style="font-size:2rem; margin-bottom:10px;">🗂️</div>
            <div style="color:{COLORS['text_muted']}; font-size:0.85rem;">
                No failover groups found across connected environments.<br>
                Create one in the <b>🗂️ Groups</b> tab first.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for grp_name in all_group_names:
            prim_acc = primary_groups.get(grp_name, "Unknown")
            sec_accs = secondary_groups.get(grp_name, [])
            prim_color = get_env_color(prim_acc)

            st.markdown(f"""
            <div class="fo-card" style="margin-bottom:16px;">
                <div style="display:flex; align-items:center;
                     gap:10px; margin-bottom:14px;">
                    <span style="font-size:1.2rem;">🗂️</span>
                    <span style="font-weight:700; color:{COLORS['text_primary']};
                          font-size:1rem;">{grp_name}</span>
                    <span class="info-pill"
                          style="color:{COLORS['cyan']}; font-size:0.65rem;
                                 border-color:{COLORS['cyan']}33;
                                 background:{COLORS['cyan']}10;">
                          FAILOVER GROUP</span>
                </div>
                <!-- Topology flow -->
                <div style="display:flex; align-items:center;
                     gap:0; flex-wrap:wrap;">
                    <!-- Primary node -->
                    <div style="background:{prim_color}15;
                         border:2px solid {prim_color}44;
                         border-radius:10px; padding:14px 20px;
                         text-align:center; min-width:140px;">
                        <div style="font-size:1.4rem; margin-bottom:4px;">🏆</div>
                        <div style="font-weight:700; color:{prim_color};
                             font-size:0.85rem;">{prim_acc}</div>
                        <span class="role-pill"
                              style="background:{COLORS['green']}15;
                                     color:{COLORS['green']};
                                     border:1px solid {COLORS['green']}33;
                                     margin-top:6px;">
                            ● PRIMARY
                        </span>
                    </div>
            """, unsafe_allow_html=True)

            # Arrow + secondary nodes
            for sec_acc in sec_accs:
                sec_color = get_env_color(sec_acc)
                st.markdown(f"""
                    <!-- Arrow -->
                    <div style="flex:1; display:flex; align-items:center;
                         justify-content:center; padding:0 8px; min-width:60px;">
                        <div style="height:2px; flex:1;
                             background:linear-gradient(90deg,
                                 {prim_color}, {sec_color});"></div>
                        <span style="font-size:1rem; color:{COLORS['text_muted']};
                               padding:0 4px;">⟶</span>
                    </div>
                    <!-- Secondary node -->
                    <div style="background:{sec_color}15;
                         border:2px solid {sec_color}44;
                         border-radius:10px; padding:14px 20px;
                         text-align:center; min-width:140px;">
                        <div style="font-size:1.4rem; margin-bottom:4px;">🔄</div>
                        <div style="font-weight:700; color:{sec_color};
                             font-size:0.85rem;">{sec_acc}</div>
                        <span class="role-pill"
                              style="background:{COLORS['blue']}15;
                                     color:{COLORS['blue']};
                                     border:1px solid {COLORS['blue']}33;
                                     margin-top:6px;">
                            ● SECONDARY
                        </span>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("</div></div>", unsafe_allow_html=True)

    # ── Pre-Failover Checklist ─────────────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    section_header("PRE-FAILOVER CHECKLIST")

    checklist_items = [
        ("⚠️", "Confirm the primary account is unreachable or planned maintenance is scheduled"),
        ("🔄", "Ensure the secondary has been recently refreshed (check Monitor tab)"),
        ("👥", "Notify all users of the upcoming failover window"),
        ("💾", "Verify all critical data has been replicated (check bytes transferred)"),
        ("⚙️", "Confirm warehouses are available on the secondary account"),
        ("🔐", "Validate users, roles, and permissions exist on secondary"),
        ("📋", "Document the current primary account for failback reference"),
        ("🧪", "Run a test query on the secondary before promoting"),
    ]

    checks_done = []
    check_cols = st.columns(2)
    for i, (icon, text) in enumerate(checklist_items):
        with check_cols[i % 2]:
            done = st.checkbox(text, key=f"fo_check_{i}")
            checks_done.append(done)

    all_checked  = all(checks_done)
    n_checked    = sum(checks_done)
    check_pct    = int(n_checked / len(checklist_items) * 100)
    bar_color    = (COLORS["green"] if all_checked
                    else COLORS["pwc_gold"] if check_pct >= 50
                    else COLORS["red"])

    st.markdown(f"""
    <div style="background:{COLORS['bg_elevated']};
         border:1px solid {COLORS['border']};
         border-radius:10px; padding:14px; margin:12px 0;">
        <div style="display:flex; align-items:center;
             justify-content:space-between; margin-bottom:8px;">
            <span style="font-size:0.78rem; color:{COLORS['text_secondary']};
                  font-weight:600;">Checklist Progress</span>
            <span style="font-family:'JetBrains Mono',monospace;
                  font-size:0.82rem; color:{bar_color};
                  font-weight:700;">{n_checked}/{len(checklist_items)}</span>
        </div>
        <div class="repl-progress-track">
            <div class="repl-progress-fill"
                 style="width:{check_pct}%;
                        background:linear-gradient(90deg,
                            {bar_color}, {bar_color}cc);">
            </div>
        </div>
        <div style="font-size:0.72rem; color:{bar_color};
             margin-top:6px; font-weight:500;">
            {'✅ All checks passed — safe to proceed' if all_checked
             else f'Complete {len(checklist_items) - n_checked} more item(s) before failover'}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Failover Execution ─────────────────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    section_header("EXECUTE FAILOVER")

    fo_c1, fo_c2 = st.columns(2)
    with fo_c1:
        fo_target_acc = st.selectbox(
            "Target Account (will become new PRIMARY)",
            options=connected,
            key="fo_target_acc",
            help="Select the secondary account you want to promote to primary"
        )
        fo_group_options = list(
            all_fg_roles.get(fo_target_acc, {}).keys()
        ) or ["(no failover groups found)"]
        fo_group_name = st.selectbox(
            "Failover Group to Promote",
            options=fo_group_options,
            key="fo_group_name"
        )

    with fo_c2:
        fo_force = st.checkbox(
            "FORCE failover (skip lag check)",
            value=False,
            key="fo_force",
            help=(
                "Use FORCE when the primary is completely unavailable. "
                "May result in some data loss."
            )
        )
        fo_move_primary = st.checkbox(
            "MOVE PRIMARY (no data loss failover)",
            value=False,
            key="fo_move_primary",
            help=(
                "Performs a graceful failover by first syncing "
                "remaining data. Takes longer but no data loss."
            )
        )

    if fo_group_name and fo_group_name != "(no failover groups found)":
        # Build SQL
        if fo_move_primary:
            fo_sql = (
                f'ALTER FAILOVER GROUP "{fo_group_name}"\n'
                f'    MOVE PRIMARY TO {fo_target_acc};'
            )
            fo_type = "MOVE PRIMARY (graceful)"
            fo_color = COLORS["green"]
        elif fo_force:
            fo_sql = (
                f'ALTER FAILOVER GROUP "{fo_group_name}"\n'
                f'    PRIMARY;'
            )
            fo_type = "FORCE FAILOVER"
            fo_color = COLORS["red"]
        else:
            fo_sql = (
                f'ALTER FAILOVER GROUP "{fo_group_name}"\n'
                f'    PRIMARY;'
            )
            fo_type = "STANDARD FAILOVER"
            fo_color = COLORS["pwc_orange"]

        # Impact preview
        st.markdown(f"""
        <div style="background:{COLORS['bg_elevated']};
             border:1px solid {COLORS['border']};
             border-radius:10px; padding:16px; margin-bottom:14px;">
            <div style="font-size:0.72rem; color:{COLORS['text_muted']};
                 text-transform:uppercase; letter-spacing:1px;
                 margin-bottom:10px;">Impact Preview</div>
            <div class="impact-row">
                <span style="color:{COLORS['text_secondary']};">Failover Type</span>
                <span style="color:{fo_color}; font-weight:700;">{fo_type}</span>
            </div>
            <div class="impact-row">
                <span style="color:{COLORS['text_secondary']};">Group</span>
                <span style="color:{COLORS['text_primary']};
                       font-weight:600;">{fo_group_name}</span>
            </div>
            <div class="impact-row">
                <span style="color:{COLORS['text_secondary']};">New Primary</span>
                <span style="color:{COLORS['green']};
                       font-weight:700;">🏆 {fo_target_acc}</span>
            </div>
            <div class="impact-row">
                <span style="color:{COLORS['text_secondary']};">
                    Expected Downtime</span>
                <span style="color:{COLORS['pwc_gold']}; font-weight:600;">
                    {'~0s (graceful)' if fo_move_primary
                     else '~30-120s (estimated)'}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(
            f'<div class="sql-block">{fo_sql}</div>',
            unsafe_allow_html=True
        )

        # Double confirmation for safety
        confirm1 = st.checkbox(
            f"✅ I confirm I want to promote **{fo_target_acc}** to PRIMARY",
            key="fo_confirm1"
        )
        confirm2 = st.checkbox(
            "✅ I understand this will change the replication topology",
            key="fo_confirm2"
        )
        impact_understood = st.checkbox(
            f"✅ I have completed the pre-failover checklist "
            f"({n_checked}/{len(checklist_items)} done)",
            key="fo_confirm3",
            disabled=not all_checked
        )

        can_execute = confirm1 and confirm2 and impact_understood

        if not can_execute:
            st.markdown(f"""
            <div style="padding:10px 14px; border-radius:8px;
                 background:{COLORS['bg_elevated']};
                 border:1px solid {COLORS['border']};
                 color:{COLORS['text_muted']};
                 font-size:0.8rem;">
                🔒 Complete all confirmations and checklist to enable failover
            </div>
            """, unsafe_allow_html=True)

        fo_btn = st.button(
            f"🔀 Execute Failover → {fo_target_acc}",
            type="primary",
            key="btn_execute_failover",
            disabled=not can_execute
        )

        if fo_btn and can_execute:
            # Animated execution
            with st.status(
                f"Executing {fo_type} for **{fo_group_name}**…",
                expanded=True
            ) as status:
                st.write("🔍 Validating failover group state…")
                time.sleep(0.8)

                st.write("🔄 Suspending writes on current primary…")
                time.sleep(0.6)

                st.write(f"📡 Promoting **{fo_target_acc}** to PRIMARY…")
                ok, msg = run_statement(fo_target_acc, fo_sql)
                time.sleep(0.8)

                if ok:
                    st.write("✅ Role swap complete!")
                    time.sleep(0.4)
                    st.write("🔄 Reconfiguring replication topology…")
                    time.sleep(0.5)
                    status.update(
                        label="✅ Failover completed successfully!",
                        state="complete",
                        expanded=False
                    )
                else:
                    status.update(
                        label=f"❌ Failover failed: {msg}",
                        state="error",
                        expanded=True
                    )

            if ok:
                st.success(
                    f"✅ **{fo_group_name}** successfully failed over to "
                    f"**{fo_target_acc}**."
                )
                st.markdown(f"""
                <div class="fo-card fo-primary" style="margin-top:12px;">
                    <div style="font-weight:700; color:{COLORS['green']};
                         margin-bottom:10px;">🎉 Failover Complete</div>
                    <div class="impact-row">
                        <span>New Primary</span>
                        <span style="color:{COLORS['green']};
                               font-weight:700;">🏆 {fo_target_acc}</span>
                    </div>
                    <div class="impact-row">
                        <span>Group</span>
                        <span style="font-weight:600;">{fo_group_name}</span>
                    </div>
                    <div class="impact-row">
                        <span>Time</span>
                        <span style="font-family:'JetBrains Mono',monospace;">
                            {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                        </span>
                    </div>
                    <div style="margin-top:10px; font-size:0.78rem;
                         color:{COLORS['text_muted']};">
                        👉 Remember to update your application connection strings
                        to point to <b>{fo_target_acc}</b>.
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.cache_data.clear()
                st.balloons()
            else:
                st.error(f"❌ Failover failed: {msg}")

    # ── Failover History ───────────────────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    section_header("FAILOVER HISTORY")

    fo_hist_days = st.select_slider(
        "Window", [7, 14, 30, 60, 90],
        value=30, key="fo_hist_days"
    )

    fo_hist_dfs = []
    for acc in connected:
        fh = fetch_failover_history(id(manager), acc, fo_hist_days)
        if not fh.empty:
            fo_hist_dfs.append(fh)

    if fo_hist_dfs:
        fo_hist_df = pd.concat(fo_hist_dfs, ignore_index=True)

        for col in ["CREDITS_USED", "BYTES_TRANSFERRED",
                    "DURATION_SEC", "OBJECT_COUNT"]:
            if col in fo_hist_df.columns:
                fo_hist_df[col] = pd.to_numeric(
                    fo_hist_df[col], errors="coerce"
                )

        fh_c1, fh_c2, fh_c3 = st.columns(3)
        fh_c1.metric("Total Events",  len(fo_hist_df))
        fh_c2.metric("Credits Used",
                     f"{fo_hist_df['CREDITS_USED'].sum():.2f}"
                     if "CREDITS_USED" in fo_hist_df.columns else "N/A")
        fh_c3.metric("Data Transferred",
                     format_bytes(fo_hist_df["BYTES_TRANSFERRED"].sum()
                                  if "BYTES_TRANSFERRED" in fo_hist_df.columns
                                  else 0))

        disp_cols = [c for c in [
            "_ACCOUNT","REPLICATION_GROUP_NAME","PHASE_NAME",
            "STATUS","START_TIME","END_TIME","DURATION_SEC",
            "BYTES_TRANSFERRED","CREDITS_USED",
            "ERROR_CODE","ERROR_MESSAGE"
        ] if c in fo_hist_df.columns]

        st.dataframe(
            fo_hist_df[disp_cols].rename(columns={
                "_ACCOUNT":               "Account",
                "REPLICATION_GROUP_NAME": "Group",
                "PHASE_NAME":             "Phase",
                "STATUS":                 "Status",
                "START_TIME":             "Start",
                "END_TIME":               "End",
                "DURATION_SEC":           "Duration (s)",
                "BYTES_TRANSFERRED":      "Bytes",
                "CREDITS_USED":           "Credits",
                "ERROR_CODE":             "Err Code",
                "ERROR_MESSAGE":          "Error",
            }),
            use_container_width=True,
            hide_index=True,
            height=400
        )
    else:
        st.info("No failover history found in the selected window.")


# ═════════════════════════════════════════════════════════════════════════════
# TAB 8 — FAILBACK
# ═════════════════════════════════════════════════════════════════════════════

with tab_failback:

    section_header("FAILBACK — RESTORE ORIGINAL PRIMARY")

    # ── What is failback banner ────────────────────────────────────────────
    st.markdown(f"""
    <div class="fo-card" style="border-left:4px solid {COLORS['blue']};">
        <div style="display:flex; align-items:flex-start; gap:14px;">
            <span style="font-size:1.8rem;">↩️</span>
            <div>
                <div style="font-weight:700; color:{COLORS['blue']};
                     font-size:0.95rem; margin-bottom:6px;">
                     What is Failback?</div>
                <div style="font-size:0.82rem; color:{COLORS['text_secondary']};
                     line-height:1.7;">
                    Failback <b>restores the original primary account</b>
                    to its primary role after a failover event. This is used:
                    <ul style="margin:6px 0 0 0; padding-left:18px;">
                        <li>After the original primary has been repaired/restored</li>
                        <li>To return to the standard replication topology</li>
                        <li>After completing planned maintenance</li>
                    </ul>
                    <div style="margin-top:8px; color:{COLORS['pwc_gold']};
                         font-weight:600; font-size:0.78rem;">
                        ℹ️ Failback is simply another failover operation —
                        you promote the original primary (now secondary)
                        back to the primary role.
                    </div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Current Topology (post-failover state) ─────────────────────────────
    section_header("CURRENT TOPOLOGY (POST-FAILOVER STATE)")

    all_fg_roles_fb = get_all_failover_groups_with_role()

    fb_primary_groups   = {}
    fb_secondary_groups = {}
    for acc, groups in all_fg_roles_fb.items():
        for grp_name, grp_info in groups.items():
            if grp_info["is_primary"]:
                fb_primary_groups[grp_name] = acc
            else:
                fb_secondary_groups.setdefault(grp_name, []).append(acc)

    fb_all_groups = list(set(
        list(fb_primary_groups.keys()) +
        list(fb_secondary_groups.keys())
    ))

    if not fb_all_groups:
        st.info("No failover groups found. "
                "Create one in the 🗂️ Groups tab first.")
    else:
        for grp in fb_all_groups:
            curr_primary = fb_primary_groups.get(grp, "Unknown")
            curr_secs    = fb_secondary_groups.get(grp, [])
            cp_color     = get_env_color(curr_primary)

            st.markdown(f"""
            <div class="fo-card" style="margin-bottom:14px;">
                <div style="display:flex; align-items:center;
                     justify-content:space-between; margin-bottom:12px;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-weight:700; color:{COLORS['text_primary']};">
                            🗂️ {grp}</span>
                    </div>
                    <span class="info-pill"
                          style="color:{COLORS['text_muted']};
                                 border-color:{COLORS['border']};
                                 background:{COLORS['bg_elevated']};
                                 font-size:0.62rem;">
                          Current State
                    </span>
                </div>
                <div style="display:flex; gap:20px; flex-wrap:wrap;">
                    <div style="background:{cp_color}15;
                         border:2px solid {cp_color}44;
                         border-radius:10px; padding:12px 18px;
                         text-align:center; min-width:130px;">
                        <div style="font-size:1.2rem;">🏆</div>
                        <div style="font-weight:700; color:{cp_color};
                             font-size:0.82rem; margin:4px 0;">{curr_primary}</div>
                        <span class="role-pill"
                              style="background:{COLORS['green']}15;
                                     color:{COLORS['green']};
                                     border:1px solid {COLORS['green']}33;
                                     font-size:0.6rem;">
                            CURRENT PRIMARY</span>
                    </div>
                    {''.join([
                        f"""<div style="background:{get_env_color(s)}15;
                             border:2px solid {get_env_color(s)}44;
                             border-radius:10px; padding:12px 18px;
                             text-align:center; min-width:130px;">
                            <div style="font-size:1.2rem;">🔄</div>
                            <div style="font-weight:700; color:{get_env_color(s)};
                                 font-size:0.82rem; margin:4px 0;">{s}</div>
                            <span class="role-pill"
                                  style="background:{COLORS['blue']}15;
                                         color:{COLORS['blue']};
                                         border:1px solid {COLORS['blue']}33;
                                         font-size:0.6rem;">
                                SECONDARY</span>
                        </div>"""
                        for s in curr_secs
                    ])}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ── Pre-Failback Readiness Check ───────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    section_header("PRE-FAILBACK READINESS CHECK")

    fb_readiness = [
        ("🔧", "Original primary account is fully restored and healthy"),
        ("🌐", "Network connectivity to original primary is stable"),
        ("🔄", "Run a final refresh on original primary (now secondary)"),
        ("👥", "Users on original primary account are ready to resume"),
        ("⚙️", "All warehouses on original primary are operational"),
        ("📊", "Verify data consistency between current primary and original"),
        ("🔐", "Security policies and network policies are in place"),
        ("📋", "Change management approval obtained for failback"),
    ]

    fb_checks = []
    fb_check_cols = st.columns(2)
    for i, (icon, text) in enumerate(fb_readiness):
        with fb_check_cols[i % 2]:
            done = st.checkbox(text, key=f"fb_check_{i}")
            fb_checks.append(done)

    fb_all_checked = all(fb_checks)
    fb_n_checked   = sum(fb_checks)
    fb_pct         = int(fb_n_checked / len(fb_readiness) * 100)
    fb_bar_color   = (COLORS["green"]    if fb_all_checked
                      else COLORS["blue"] if fb_pct >= 50
                      else COLORS["red"])

    st.markdown(f"""
    <div style="background:{COLORS['bg_elevated']};
         border:1px solid {COLORS['border']};
         border-radius:10px; padding:14px; margin:12px 0;">
        <div style="display:flex; align-items:center;
             justify-content:space-between; margin-bottom:8px;">
            <span style="font-size:0.78rem; color:{COLORS['text_secondary']};
                  font-weight:600;">Readiness Progress</span>
            <span style="font-family:'JetBrains Mono',monospace;
                  font-size:0.82rem; color:{fb_bar_color};
                  font-weight:700;">{fb_n_checked}/{len(fb_readiness)}</span>
        </div>
        <div class="repl-progress-track">
            <div class="repl-progress-fill"
                 style="width:{fb_pct}%;
                        background:linear-gradient(90deg,
                            {fb_bar_color}, {fb_bar_color}cc);"></div>
        </div>
        <div style="font-size:0.72rem; color:{fb_bar_color};
             margin-top:6px; font-weight:500;">
            {'✅ System ready for failback' if fb_all_checked
             else f'Complete {len(fb_readiness)-fb_n_checked} more item(s)'}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Failback Execution ─────────────────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    section_header("EXECUTE FAILBACK")

    fb_c1, fb_c2 = st.columns(2)

    with fb_c1:
        fb_original_acc = st.selectbox(
            "Original Primary Account (restore to PRIMARY)",
            options=connected,
            key="fb_original_acc",
            help="Select the account that was the original primary before failover"
        )
        fb_grp_options  = list(
            all_fg_roles_fb.get(fb_original_acc, {}).keys()
        ) or ["(no groups found)"]
        fb_group_name   = st.selectbox(
            "Failover Group",
            options=fb_grp_options,
            key="fb_group_name"
        )

    with fb_c2:
        fb_strategy = st.radio(
            "Failback Strategy",
            [
                "🔄 MOVE PRIMARY (graceful, recommended)",
                "⚡ FORCE PRIMARY (immediate, possible data loss)",
            ],
            key="fb_strategy"
        )
        fb_sync_before = st.checkbox(
            "Refresh secondary before failback (recommended)",
            value=True,
            key="fb_sync_before",
            help="Runs a final refresh to minimize data loss"
        )

    if fb_group_name and fb_group_name != "(no groups found)":
        use_move = "MOVE PRIMARY" in fb_strategy

        if use_move:
            fb_sql = (
                f'ALTER FAILOVER GROUP "{fb_group_name}"\n'
                f'    MOVE PRIMARY TO {fb_original_acc};'
            )
            fb_type_label = "MOVE PRIMARY (Graceful Failback)"
            fb_type_color = COLORS["green"]
        else:
            fb_sql = (
                f'ALTER FAILOVER GROUP "{fb_group_name}"\n'
                f'    PRIMARY;'
            )
            fb_type_label = "FORCE PRIMARY (Immediate Failback)"
            fb_type_color = COLORS["red"]

        refresh_sql = (
            f'ALTER FAILOVER GROUP "{fb_group_name}" REFRESH;'
        )

        # Execution plan preview
        st.markdown(f"""
        <div style="background:{COLORS['bg_elevated']};
             border:1px solid {COLORS['border']};
             border-radius:10px; padding:16px; margin-bottom:14px;">
            <div style="font-size:0.72rem; color:{COLORS['text_muted']};
                 text-transform:uppercase; letter-spacing:1px;
                 margin-bottom:12px;">Failback Execution Plan</div>
        """, unsafe_allow_html=True)

        steps = []
        if fb_sync_before:
            steps.append((
                "1", COLORS["blue"],
                f"Refresh group <b>{fb_group_name}</b> "
                f"on <b>{fb_original_acc}</b>",
                f'<code style="font-size:0.7rem;">{refresh_sql}</code>'
            ))
        steps.append((
            str(len(steps) + 1), fb_type_color,
            f"Execute {fb_type_label}: Promote "
            f"<b>{fb_original_acc}</b> back to PRIMARY",
            f'<code style="font-size:0.7rem;">{fb_sql}</code>'
        ))
        steps.append((
            str(len(steps) + 1), COLORS["green"],
            "Verify new topology — original primary is restored",
            ""
        ))

        for step_num, step_color, step_text, step_code in steps:
            st.markdown(f"""
            <div class="impact-row" style="flex-direction:column;
                 align-items:flex-start; gap:6px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <div style="width:22px; height:22px; border-radius:50%;
                         background:{step_color}; color:white;
                         font-size:0.7rem; font-weight:700;
                         display:flex; align-items:center;
                         justify-content:center; flex-shrink:0;">{step_num}</div>
                    <div style="font-size:0.82rem;
                         color:{COLORS['text_secondary']};">{step_text}</div>
                </div>
                {f'<div style="margin-left:30px;">{step_code}</div>'
                 if step_code else ''}
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # Confirm + Execute
        fb_confirm1 = st.checkbox(
            f"✅ Confirm restore of **{fb_original_acc}** to PRIMARY",
            key="fb_confirm1"
        )
        fb_confirm2 = st.checkbox(
            "✅ I have completed the pre-failback readiness checklist",
            key="fb_confirm2",
            disabled=not fb_all_checked
        )
        fb_confirm3 = st.checkbox(
            "✅ Application teams are ready for the topology change",
            key="fb_confirm3"
        )

        fb_can_exec = fb_confirm1 and fb_confirm2 and fb_confirm3

        fb_btn = st.button(
            f"↩️ Execute Failback → {fb_original_acc}",
            type="primary",
            key="btn_execute_failback",
            disabled=not fb_can_exec
        )

        if fb_btn and fb_can_exec:
            with st.status(
                f"Executing failback for **{fb_group_name}**…",
                expanded=True
            ) as fb_status:

                if fb_sync_before:
                    st.write(
                        f"🔄 Running final refresh on "
                        f"**{fb_original_acc}**…"
                    )
                    ok_sync, msg_sync = run_statement(
                        fb_original_acc, refresh_sql
                    )
                    time.sleep(1.0)
                    if not ok_sync:
                        st.write(
                            f"⚠️ Refresh warning: {msg_sync} "
                            f"(continuing with failback)"
                        )

                st.write("🔍 Validating original primary health…")
                time.sleep(0.7)

                st.write(
                    f"↩️ Promoting **{fb_original_acc}** "
                    f"back to PRIMARY…"
                )
                ok_fb, msg_fb = run_statement(fb_original_acc, fb_sql)
                time.sleep(0.8)

                if ok_fb:
                    st.write("✅ Role restored!")
                    time.sleep(0.4)
                    st.write("🔄 Updating replication topology…")
                    time.sleep(0.5)
                    fb_status.update(
                        label="✅ Failback completed successfully!",
                        state="complete",
                        expanded=False
                    )
                else:
                    fb_status.update(
                        label=f"❌ Failback failed: {msg_fb}",
                        state="error",
                        expanded=True
                    )

            if ok_fb:
                st.success(
                    f"✅ **{fb_group_name}** successfully failed back to "
                    f"**{fb_original_acc}**!"
                )
                st.markdown(f"""
                <div class="fo-card fo-primary" style="margin-top:12px;">
                    <div style="font-weight:700; color:{COLORS['green']};
                         margin-bottom:12px; font-size:0.95rem;">
                         🎉 Failback Complete — Original Topology Restored</div>
                    <div class="impact-row">
                        <span>Restored Primary</span>
                        <span style="color:{COLORS['green']};
                               font-weight:700;">🏆 {fb_original_acc}</span>
                    </div>
                    <div class="impact-row">
                        <span>Group</span>
                        <span style="font-weight:600;">{fb_group_name}</span>
                    </div>
                    <div class="impact-row">
                        <span>Strategy Used</span>
                        <span style="color:{fb_type_color};
                               font-weight:600;">{fb_type_label}</span>
                    </div>
                    <div class="impact-row">
                        <span>Completed At</span>
                        <span style="font-family:'JetBrains Mono',monospace;
                               font-size:0.78rem;">
                            {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                        </span>
                    </div>
                    <div style="margin-top:12px; padding:10px 14px;
                         background:{COLORS['bg_secondary']};
                         border-radius:8px; font-size:0.78rem;
                         color:{COLORS['text_muted']}; line-height:1.6;">
                        📋 <b>Next Steps:</b><br>
                        1. Update application connection strings back to
                           <b>{fb_original_acc}</b><br>
                        2. Monitor replication lag on the new secondary<br>
                        3. Document the failover/failback event for the runbook
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.cache_data.clear()
                st.balloons()
            else:
                st.error(f"❌ Failback failed: {msg_fb}")

    # ── Post-Failback Verification ─────────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    with st.expander("🔍 Post-Failback Verification Queries"):
        verify_acc = st.selectbox(
            "Run on account", connected, key="verify_acc"
        )

        verif_queries = {
            "Check Failover Groups Status":
                "SHOW FAILOVER GROUPS;",
            "Check Replication Groups":
                "SHOW REPLICATION GROUPS;",
            "Check Replication Databases":
                "SHOW REPLICATION DATABASES;",
            "Recent Replication Activity (1 day)": """
                SELECT REPLICATION_GROUP_NAME, PHASE_NAME,
                       STATUS, START_TIME, END_TIME,
                       BYTES_TRANSFERRED, CREDITS_USED
                FROM SNOWFLAKE.ACCOUNT_USAGE.REPLICATION_GROUP_USAGE_HISTORY
                WHERE START_TIME >= DATEADD('day',-1,CURRENT_TIMESTAMP())
                ORDER BY START_TIME DESC LIMIT 20;
            """,
        }

        sel_query = st.selectbox(
            "Select Verification Query",
            list(verif_queries.keys()),
            key="verif_query_sel"
        )
        st.code(verif_queries[sel_query], language="sql")

        if st.button("▶️ Run Verification", key="btn_verify",
                      type="primary"):
            with st.spinner("Running…"):
                vdf = run_query(verify_acc, verif_queries[sel_query])
            if vdf is not None and not vdf.empty:
                st.success(f"✅ {len(vdf)} row(s) returned")
                st.dataframe(vdf, use_container_width=True,
                             hide_index=True)
            else:
                st.info("Query returned no results.")

# ═════════════════════════════════════════════════════════════════════════════
# TAB 6 — HISTORY & ANALYTICS
# ═════════════════════════════════════════════════════════════════════════════

with tab_history:
    section_header("REPLICATION HISTORY & ANALYTICS")

    h_col1, h_col2, h_col3 = st.columns(3)
    with h_col1:
        hist_acc = st.multiselect(
            "Environments",
            connected, default=connected,
            key="hist_acc"
        )
    with h_col2:
        hist_days = st.selectbox(
            "Time Range",
            [7, 14, 30, 60, 90],
            index=2,
            format_func=lambda x: f"Last {x} days",
            key="hist_days"
        )
    with h_col3:
        hist_status = st.multiselect(
            "Status Filter",
            ["SUCCESS","SUCCEEDED","FAILED","RUNNING"],
            default=[],
            key="hist_status"
        )

    hist_all = []
    for acc in (hist_acc or connected):
        hd = fetch_replication_history(id(manager), acc, hist_days)
        if not hd.empty:
            hist_all.append(hd)

    if not hist_all:
        st.info("No replication history found.")
        st.stop()

    h_df = pd.concat(hist_all, ignore_index=True)

    # Apply status filter
    if hist_status and "STATUS" in h_df.columns:
        h_df = h_df[h_df["STATUS"].str.upper().isin(
            [s.upper() for s in hist_status]
        )]

    # Numeric conversions
    for col in ["TOTAL_BYTES_REPLICATED", "CREDITS_USED",
                "DURATION_SEC", "TOTAL_OBJECT_COUNT"]:
        if col in h_df.columns:
            h_df[col] = pd.to_numeric(h_df[col], errors="coerce")

    if "START_TIME" in h_df.columns:
        h_df["START_TIME"] = pd.to_datetime(h_df["START_TIME"])

    # Summary metrics
    section_header(f"SUMMARY — LAST {hist_days} DAYS")
    sm1, sm2, sm3, sm4, sm5, sm6 = st.columns(6)

    total_jobs  = len(h_df)
    total_bytes = h_df["TOTAL_BYTES_REPLICATED"].sum() \
                  if "TOTAL_BYTES_REPLICATED" in h_df.columns else 0
    total_creds = h_df["CREDITS_USED"].sum() \
                  if "CREDITS_USED" in h_df.columns else 0
    avg_dur     = h_df["DURATION_SEC"].mean() \
                  if "DURATION_SEC" in h_df.columns else 0
    n_failed    = len(h_df[h_df["STATUS"].str.upper()
                           .isin(["FAILED","ERROR","FAIL"])]) \
                  if "STATUS" in h_df.columns else 0
    n_ok        = total_jobs - n_failed

    sm1.metric("Total Jobs",   total_jobs)
    sm2.metric("Successful",   n_ok)
    sm3.metric("Failed",       n_failed)
    sm4.metric("Data Moved",   format_bytes(total_bytes))
    sm5.metric("Credits",      f"{total_creds:.2f}")
    sm6.metric("Avg Duration", f"{avg_dur:.0f}s")

    # Charts
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    ht1, ht2, ht3 = st.tabs(["📈 Trends", "🔬 Drill-down", "📋 Raw Data"])

    with ht1:
        if "START_TIME" in h_df.columns:
            h_df["DATE"] = h_df["START_TIME"].dt.date
            cmap = {n: get_env_color(n)
                    for n in h_df["_ACCOUNT"].unique()}

            daily_agg = h_df.groupby(["DATE","_ACCOUNT"]).agg(
                Jobs       =("STATUS","count"),
                Bytes      =("TOTAL_BYTES_REPLICATED","sum"),
                Credits    =("CREDITS_USED","sum"),
                Avg_Dur    =("DURATION_SEC","mean"),
            ).reset_index()

            fig_t1 = make_subplots(
                rows=2, cols=2,
                subplot_titles=[
                    "Jobs per Day", "Data Transferred (GB)",
                    "Credits Used", "Avg Duration (s)"
                ]
            )
            for acc_n in daily_agg["_ACCOUNT"].unique():
                sub = daily_agg[daily_agg["_ACCOUNT"] == acc_n]
                clr = get_env_color(acc_n)

                fig_t1.add_trace(go.Scatter(
                    x=sub["DATE"], y=sub["Jobs"],
                    name=acc_n, line=dict(color=clr, width=2),
                    showlegend=True
                ), row=1, col=1)

                fig_t1.add_trace(go.Scatter(
                    x=sub["DATE"], y=sub["Bytes"] / 1e9,
                    name=acc_n, line=dict(color=clr, width=2),
                    showlegend=False
                ), row=1, col=2)

                fig_t1.add_trace(go.Bar(
                    x=sub["DATE"], y=sub["Credits"],
                    name=acc_n, marker_color=clr,
                    showlegend=False
                ), row=2, col=1)

                fig_t1.add_trace(go.Scatter(
                    x=sub["DATE"], y=sub["Avg_Dur"],
                    name=acc_n, line=dict(color=clr, width=2),
                    showlegend=False
                ), row=2, col=2)

            fig_t1.update_layout(
                height=600,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=COLORS["text_secondary"]),
                legend_title_text="Environment"
            )
            for i in range(1, 5):
                row = 1 if i <= 2 else 2
                col = i if i <= 2 else i - 2
                fig_t1.update_xaxes(
                    gridcolor=COLORS["border"],
                    linecolor=COLORS["border"],
                    row=row, col=col
                )
                fig_t1.update_yaxes(
                    gridcolor=COLORS["border"],
                    linecolor=COLORS["border"],
                    row=row, col=col
                )
            st.plotly_chart(fig_t1, use_container_width=True,
                            key="hist_trends")

    with ht2:
        dd1, dd2 = st.columns(2)

        with dd1:
            # Status distribution
            if "STATUS" in h_df.columns:
                status_counts = h_df["STATUS"].str.upper().value_counts()
                colors_status = [
                    COLORS["green"] if s in ("SUCCESS","SUCCEEDED","COMPLETED")
                    else COLORS["red"] if s in ("FAILED","ERROR","FAIL")
                    else COLORS["blue"]
                    for s in status_counts.index
                ]
                fig_status = go.Figure(go.Pie(
                    labels=status_counts.index,
                    values=status_counts.values,
                    hole=0.6,
                    marker_colors=colors_status,
                    textinfo="label+percent"
                ))
                fig_status.update_layout(
                    title="Job Status Distribution",
                    height=320,
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color=COLORS["text_secondary"])
                )
                st.plotly_chart(fig_status, use_container_width=True,
                                key="hist_status_pie")

        with dd2:
            # Phase duration
            if "PHASE_NAME" in h_df.columns:
                phase_dur = h_df.groupby("PHASE_NAME")[
                    "DURATION_SEC"
                ].mean().sort_values(ascending=True).reset_index()
                fig_phase = px.bar(
                    phase_dur, x="DURATION_SEC", y="PHASE_NAME",
                    orientation="h", height=320,
                    title="Avg Duration by Phase (s)",
                    color="DURATION_SEC",
                    color_continuous_scale=[
                        COLORS["bg_elevated"],
                        COLORS["pwc_orange"],
                        COLORS["red"]
                    ]
                )
                fig_phase.update_layout(
                    xaxis_title="Seconds",
                    yaxis_title="",
                    coloraxis_showscale=False
                )
                st.plotly_chart(fig_phase, use_container_width=True,
                                key="hist_phase_dur")

        # Database-level breakdown
        if "DATABASE_NAME" in h_df.columns:
            db_summary = h_df.groupby(
                ["_ACCOUNT","DATABASE_NAME"]
            ).agg(
                Jobs           =("STATUS","count"),
                Total_Bytes    =("TOTAL_BYTES_REPLICATED","sum"),
                Total_Credits  =("CREDITS_USED","sum"),
                Avg_Duration   =("DURATION_SEC","mean"),
            ).reset_index().sort_values("Total_Bytes", ascending=False)

            db_summary["Data"] = db_summary["Total_Bytes"].apply(format_bytes)

            cmap2 = {n: get_env_color(n)
                     for n in db_summary["_ACCOUNT"].unique()}
            fig_db = px.bar(
                db_summary.head(20),
                x="DATABASE_NAME", y="Total_Bytes",
                color="_ACCOUNT", color_discrete_map=cmap2,
                height=350,
                title="Top Databases by Data Replicated",
                barmode="group",
                labels={"Total_Bytes": "Bytes", "_ACCOUNT": "Env"}
            )
            fig_db.update_layout(xaxis_tickangle=-30, xaxis_title="",
                                  legend_title_text="")
            st.plotly_chart(fig_db, use_container_width=True,
                            key="hist_db_bytes")

    with ht3:
        # Full raw table with search
        search = st.text_input("🔍 Search", key="hist_search",
                               placeholder="Filter by database, status…")

        display_df = h_df.copy()
        if search:
            mask = display_df.apply(
                lambda r: r.astype(str).str.contains(
                    search, case=False, na=False
                ).any(), axis=1
            )
            display_df = display_df[mask]

        raw_cols = [c for c in [
            "_ACCOUNT","DATABASE_NAME","REPLICATION_GROUP_NAME",
            "PHASE_NAME","STATUS","START_TIME","END_TIME",
            "DURATION_SEC","TOTAL_BYTES_REPLICATED",
            "TOTAL_OBJECT_COUNT","CREDITS_USED",
            "ERROR_CODE","ERROR_MESSAGE"
        ] if c in display_df.columns]

        st.dataframe(
            display_df[raw_cols].rename(columns={
                "_ACCOUNT":                 "Account",
                "DATABASE_NAME":            "Database",
                "REPLICATION_GROUP_NAME":   "Group",
                "PHASE_NAME":               "Phase",
                "STATUS":                   "Status",
                "START_TIME":               "Start",
                "END_TIME":                 "End",
                "DURATION_SEC":             "Duration (s)",
                "TOTAL_BYTES_REPLICATED":   "Bytes",
                "TOTAL_OBJECT_COUNT":       "Objects",
                "CREDITS_USED":             "Credits",
                "ERROR_CODE":               "Err Code",
                "ERROR_MESSAGE":            "Error",
            }),
            use_container_width=True,
            hide_index=True,
            height=500
        )

        csv = display_df.to_csv(index=False)
        st.download_button(
            "📥 Download CSV",
            data=csv,
            file_name=f"replication_history_{datetime.date.today()}.csv",
            mime="text/csv",
            key="hist_download"
        )

# ─── Footer ───────────────────────────────────────────────────────────────────

st.markdown(f"""
<div style="text-align:center; padding:28px 0 10px;
     border-top:1px solid {COLORS['border']}; margin-top:32px;">
    <span style="font-size:0.65rem; color:{COLORS['text_dim']};">
        🔄 Replication Management &nbsp;·&nbsp;
        <span style="color:{COLORS['pwc_orange']}; font-weight:700;">
            Powered By PwC Data & AI</span>
        &nbsp;·&nbsp; {len(connected)} environment(s)
    </span>
</div>
""", unsafe_allow_html=True)