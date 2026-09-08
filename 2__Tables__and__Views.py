"""
📋 Tables & Views — Browse, create, alter, manage
   permissions and monitor schema evolution across
   all connected environments.
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
    .tbl-card {{
        background: {COLORS["bg_card"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 12px;
        padding: 16px 18px;
        margin-bottom: 10px;
        transition: all 0.3s ease;
        animation: fadeInUp 0.4s ease both;
        position: relative;
        overflow: hidden;
    }}
    .tbl-card:hover {{
        border-color: {COLORS["border_light"]};
        transform: translateY(-2px);
        box-shadow: 0 8px 28px rgba(0,0,0,0.3);
    }}
    .tbl-card .accent {{
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: var(--accent,
            {COLORS["pwc_orange"]});
    }}
    .col-row {{
        display: flex;
        align-items: center;
        padding: 8px 12px;
        background: {COLORS["bg_elevated"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 8px;
        margin-bottom: 5px;
        gap: 10px;
        font-size: 0.8rem;
        transition: all 0.2s ease;
    }}
    .col-row:hover {{
        border-color: {COLORS["border_light"]};
        background: {COLORS["bg_card_hover"]};
    }}
    .type-badge {{
        display: inline-flex;
        align-items: center;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.62rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.3px;
        border: 1px solid;
        font-family: 'JetBrains Mono', monospace;
        flex-shrink: 0;
    }}
    .pk-badge {{
        display: inline-flex;
        align-items: center;
        padding: 1px 6px;
        border-radius: 4px;
        font-size: 0.58rem;
        font-weight: 700;
        background: {COLORS["pwc_gold"]}22;
        color: {COLORS["pwc_gold"]};
        border: 1px solid {COLORS["pwc_gold"]}44;
        flex-shrink: 0;
    }}
    .nullable-dot {{
        width: 6px; height: 6px;
        border-radius: 50%;
        flex-shrink: 0;
    }}
    .sql-block {{
        background: {COLORS["bg_secondary"]};
        border: 1px solid {COLORS["border"]};
        border-left: 3px solid {COLORS["pwc_orange"]};
        border-radius: 0 8px 8px 0;
        padding: 14px 16px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: {COLORS["text_secondary"]};
        line-height: 1.7;
        white-space: pre-wrap;
        word-break: break-all;
        margin: 10px 0;
    }}
    .info-box {{
        background: {COLORS["bg_elevated"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 10px;
        padding: 14px 16px;
        font-size: 0.82rem;
        color: {COLORS["text_secondary"]};
        line-height: 1.6;
        margin: 10px 0;
    }}
    .step-header {{
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 14px;
        margin-top: 8px;
    }}
    .step-num {{
        width: 26px; height: 26px;
        border-radius: 50%;
        background: linear-gradient(135deg,
            {COLORS["pwc_orange"]},
            {COLORS["pwc_orange_dark"]});
        color: white;
        font-size: 0.72rem;
        font-weight: 700;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }}
    .step-title {{
        font-weight: 700;
        color: {COLORS["text_primary"]};
        font-size: 0.9rem;
    }}
    .change-row {{
        display: flex;
        align-items: flex-start;
        gap: 10px;
        padding: 10px 14px;
        background: {COLORS["bg_elevated"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 8px;
        margin-bottom: 6px;
        font-size: 0.8rem;
        transition: all 0.2s ease;
    }}
    .change-row:hover {{
        border-color: {COLORS["border_light"]};
    }}
    .priv-chip {{
        display: inline-flex;
        align-items: center;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.62rem;
        font-weight: 700;
        text-transform: uppercase;
        border: 1px solid;
        margin: 2px;
    }}
    .evolution-badge {{
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.65rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        border: 1px solid;
    }}
</style>
""", unsafe_allow_html=True)

# ─── Sidebar ──────────────────────────────────────────────────────────────────

manager   = SnowflakeConnectionManager()
connected = manager.get_connected_accounts()

st.sidebar.markdown(f"""
<div style="padding:20px 16px 12px;
     border-bottom:1px solid {COLORS['border']};">
    <div style="display:flex; align-items:center;
         gap:10px;">
        <span style="font-size:1.6rem;">📋</span>
        <div>
            <div style="font-size:0.95rem;
                 font-weight:700;
                 color:{COLORS['text_primary']};">
                 Tables & Views</div>
            <div style="font-size:0.55rem;
                 color:{COLORS['pwc_orange']};
                 font-weight:700;
                 text-transform:uppercase;
                 letter-spacing:2px;">
                 PwC Data & AI</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

for acc in connected:
    color = get_env_color(acc)
    st.sidebar.markdown(f"""
    <div style="display:flex; align-items:center;
         gap:8px; padding:8px 10px;
         border-radius:8px; margin-bottom:4px;">
        <div style="width:8px; height:8px;
             border-radius:50%;
             background:{color};
             box-shadow:0 0 6px {color};
             flex-shrink:0;
             animation:pulse 2s ease infinite;">
        </div>
        <span style="font-size:0.82rem;
              font-weight:600;
              color:{color};">{acc}</span>
    </div>""", unsafe_allow_html=True)

if not connected:
    st.sidebar.warning("No accounts connected.")

st.sidebar.markdown("---")
if st.sidebar.button(
    "🔄 Refresh",
    use_container_width=True,
    key="tv_refresh"
):
    st.cache_data.clear()
    st.rerun()

# ─── Header ───────────────────────────────────────────────────────────────────

pwc_header(
    "Tables & Views",
    subtitle="Browse, create, alter tables & views, "
             "manage permissions and monitor schema evolution"
)

if not connected:
    st.markdown(f"""
    <div style="background:{COLORS['bg_card']};
         border:2px dashed {COLORS['border_light']};
         border-radius:12px; padding:60px;
         text-align:center;">
        <div style="font-size:2.5rem;
             margin-bottom:12px;">🔌</div>
        <div style="color:{COLORS['text_secondary']};">
            Connect to at least one account
        </div>
    </div>""", unsafe_allow_html=True)
    st.stop()

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


def fmt_bytes(b) -> str:
    b = safe_float(b)
    if b == 0:
        return "0 B"
    for u in ["B","KB","MB","GB","TB"]:
        if abs(b) < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} PB"


def fmt_num(n) -> str:
    n = safe_int(n)
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


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
        return True, (
            pd.DataFrame(rows, columns=cols)
            if cols else pd.DataFrame()
        )
    except Exception as e:
        return False, str(e)


def type_badge(dtype: str) -> str:
    d = str(dtype).upper()
    if any(t in d for t in ["VARCHAR","TEXT","STRING","CHAR"]):
        color = COLORS["blue"]
    elif any(t in d for t in ["NUMBER","INT","FLOAT","DECIMAL","DOUBLE","NUMERIC"]):
        color = COLORS["pwc_orange"]
    elif any(t in d for t in ["DATE","TIME","TIMESTAMP"]):
        color = COLORS["purple"]
    elif any(t in d for t in ["BOOLEAN","BOOL"]):
        color = COLORS["cyan"]
    elif any(t in d for t in ["VARIANT","OBJECT","ARRAY"]):
        color = COLORS["pwc_gold"]
    else:
        color = COLORS["text_muted"]
    return (f'<span class="type-badge" '
            f'style="color:{color}; '
            f'border-color:{color}33; '
            f'background:{color}10;">{dtype}</span>')


def priv_chip(priv: str) -> str:
    p = str(priv).upper()
    cfg = {
        "SELECT":      COLORS["green"],
        "INSERT":      COLORS["blue"],
        "UPDATE":      COLORS["pwc_gold"],
        "DELETE":      COLORS["red"],
        "TRUNCATE":    COLORS["red"],
        "REFERENCES":  COLORS["purple"],
        "OWNERSHIP":   COLORS["pwc_orange"],
        "ALL PRIVILEGES": COLORS["red"],
    }
    color = cfg.get(p, COLORS["text_muted"])
    return (f'<span class="priv-chip" '
            f'style="color:{color}; '
            f'border-color:{color}33; '
            f'background:{color}10;">{p}</span>')


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
def fetch_schemas(_mid, account, db):
    try:
        df = run_query(
            account,
            f'SHOW SCHEMAS IN DATABASE "{db}"'
        )
        if df is not None and "name" in df.columns:
            return [s for s in df["name"].tolist()
                    if s != "INFORMATION_SCHEMA"]
    except Exception:
        pass
    return []


@st.cache_data(ttl=60, show_spinner=False)
def fetch_tables(_mid, account, db, schema):
    try:
        df = run_query(
            account,
            f'SHOW TABLES IN "{db}"."{schema}"'
        )
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def fetch_views(_mid, account, db, schema):
    try:
        df = run_query(
            account,
            f'SHOW VIEWS IN "{db}"."{schema}"'
        )
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def fetch_columns(_mid, account, db, schema, table):
    try:
        df = run_query(
            account,
            f'SHOW COLUMNS IN TABLE '
            f'"{db}"."{schema}"."{table}"'
        )
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def fetch_grants_on_table(
        _mid, account, db, schema, table):
    try:
        df = run_query(
            account,
            f'SHOW GRANTS ON TABLE '
            f'"{db}"."{schema}"."{table}"'
        )
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def fetch_roles(_mid, account):
    try:
        df = run_query(account, "SHOW ROLES")
        if df is not None and "name" in df.columns:
            return df["name"].tolist()
    except Exception:
        pass
    return []


@st.cache_data(ttl=60, show_spinner=False)
def fetch_table_storage(_mid, account, db):
    try:
        df = run_query(account, f"""
            SELECT
                TABLE_SCHEMA,
                TABLE_NAME,
                TABLE_TYPE,
                ROW_COUNT,
                BYTES,
                LAST_ALTERED,
                CREATED,
                RETENTION_TIME,
                CLUSTERING_KEY,
                COMMENT
            FROM "{db}".INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE IN
                  ('BASE TABLE','VIEW')
            ORDER BY BYTES DESC NULLS LAST
            LIMIT 500
        """)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=30, show_spinner=False)
def fetch_schema_evolution(_mid, account, days):
    try:
        df = run_query(account, f"""
            SELECT
                QUERY_ID,
                QUERY_TEXT,
                DATABASE_NAME,
                SCHEMA_NAME,
                QUERY_TYPE,
                USER_NAME,
                ROLE_NAME,
                WAREHOUSE_NAME,
                START_TIME,
                EXECUTION_STATUS,
                TOTAL_ELAPSED_TIME/1000 AS DURATION_SEC
            FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
            WHERE QUERY_TYPE IN (
                'CREATE_TABLE','ALTER_TABLE',
                'DROP_TABLE','RENAME_TABLE',
                'CREATE_VIEW','ALTER_VIEW',
                'DROP_VIEW','CREATE_SCHEMA',
                'DROP_SCHEMA','ALTER_SCHEMA',
                'ADD_COLUMN','DROP_COLUMN',
                'RENAME_COLUMN','MODIFY_COLUMN'
            )
            AND START_TIME >=
                DATEADD('day',{-days},
                CURRENT_TIMESTAMP())
            ORDER BY START_TIME DESC
            LIMIT 2000
        """)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=30, show_spinner=False)
def fetch_table_dml(_mid, account, db,
                     schema, table, days):
    try:
        df = run_query(account, f"""
            SELECT
                QUERY_TYPE,
                START_TIME::DATE AS DATE,
                COUNT(*)        AS QUERY_COUNT,
                SUM(ROWS_PRODUCED) AS ROWS_AFFECTED
            FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
            WHERE QUERY_TYPE IN (
                'INSERT','UPDATE','DELETE',
                'MERGE','COPY','TRUNCATE_TABLE')
            AND DATABASE_NAME = '{db}'
            AND SCHEMA_NAME   = '{schema}'
            AND START_TIME >=
                DATEADD('day',{-days},
                CURRENT_TIMESTAMP())
            GROUP BY 1,2 ORDER BY 2 DESC
        """)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


# ─── Tabs ─────────────────────────────────────────────────────────────────────

(tab_overview, tab_browse, tab_create,
 tab_alter, tab_permissions,
 tab_evolution, tab_dml) = st.tabs([
    "📊  Overview",
    "🔍  Browse",
    "➕  Create",
    "✏️  Alter",
    "🔐  Permissions",
    "🧬  Schema Evolution",
    "📈  DML Activity",
])

# ═══════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════

with tab_overview:
    section_header("TABLES & VIEWS OVERVIEW")

    ov_acc = st.selectbox(
        "Environment", connected, key="ov_acc")
    ov_dbs = fetch_databases(id(manager), ov_acc)
    ov_db  = st.selectbox(
        "Database", ov_dbs or ["(none)"],
        key="ov_db")

    if ov_db and ov_db != "(none)":
        storage_df = fetch_table_storage(
            id(manager), ov_acc, ov_db)

        if not storage_df.empty:
            for col in ["ROW_COUNT","BYTES"]:
                if col in storage_df.columns:
                    storage_df[col] = pd.to_numeric(
                        storage_df[col],
                        errors="coerce"
                    ).fillna(0)

            n_tables = safe_int(len(storage_df[
                storage_df["TABLE_TYPE"]
                == "BASE TABLE"])
                if "TABLE_TYPE" in storage_df.columns
                else len(storage_df))
            n_views  = safe_int(len(storage_df[
                storage_df["TABLE_TYPE"] == "VIEW"])
                if "TABLE_TYPE" in storage_df.columns
                else 0)
            total_rows = safe_int(
                storage_df["ROW_COUNT"].sum()
                if "ROW_COUNT" in storage_df.columns
                else 0)
            total_bytes= safe_float(
                storage_df["BYTES"].sum()
                if "BYTES" in storage_df.columns
                else 0)
            n_schemas  = safe_int(
                storage_df["TABLE_SCHEMA"].nunique()
                if "TABLE_SCHEMA" in storage_df.columns
                else 0)
            avg_rows   = safe_float(
                storage_df[
                    storage_df["TABLE_TYPE"]
                    == "BASE TABLE"
                ]["ROW_COUNT"].mean()
                if "TABLE_TYPE" in storage_df.columns
                else 0)

            k1,k2,k3,k4,k5,k6 = st.columns(6)
            kpis = [
                ("📋", str(n_tables),
                 "Tables",       COLORS["pwc_orange"]),
                ("👁️", str(n_views),
                 "Views",        COLORS["blue"]),
                ("🗂️", str(n_schemas),
                 "Schemas",      COLORS["pwc_gold"]),
                ("📊", fmt_num(total_rows),
                 "Total Rows",   COLORS["green"]),
                ("💾", fmt_bytes(total_bytes),
                 "Total Storage",COLORS["cyan"]),
                ("📈", fmt_num(safe_int(avg_rows)),
                 "Avg Rows/Table",COLORS["purple"]),
            ]
            for col, (ico,val,lbl,clr) in zip(
                    [k1,k2,k3,k4,k5,k6], kpis):
                with col:
                    st.markdown(
                        kpi_card(ico,val,lbl,clr),
                        unsafe_allow_html=True)

            st.markdown(
                "<div style='height:12px'></div>",
                unsafe_allow_html=True)

            # Charts
            section_header("STORAGE ANALYTICS")

            sc1, sc2 = st.columns(2)
            with sc1:
                # Top tables by size
                if "BYTES" in storage_df.columns:
                    top_sz = storage_df[
                        storage_df["TABLE_TYPE"]
                        == "BASE TABLE"
                    ].nlargest(15,"BYTES").copy()
                    if "TABLE_NAME" in top_sz.columns:
                        top_sz["GB"] = (
                            top_sz["BYTES"] / 1e9)
                        fig = px.bar(
                            top_sz,
                            x="TABLE_NAME",
                            y="GB",
                            title="Top 15 Tables by Size (GB)",
                            height=340,
                            color="GB",
                            color_continuous_scale=[
                                COLORS["bg_elevated"],
                                COLORS["pwc_orange"],
                                COLORS["red"]
                            ]
                        )
                        fig.update_layout(
                            xaxis_tickangle=-35,
                            xaxis_title="",
                            yaxis_title="GB",
                            coloraxis_showscale=False
                        )
                        st.plotly_chart(
                            fig,
                            use_container_width=True,
                            key="ov_top_size")

            with sc2:
                # Schema distribution
                if ("TABLE_SCHEMA" in storage_df.columns
                        and "BYTES" in storage_df.columns):
                    schema_sz = storage_df.groupby(
                        "TABLE_SCHEMA"
                    )["BYTES"].sum().reset_index()
                    schema_sz["GB"] = (
                        schema_sz["BYTES"] / 1e9)
                    fig2 = go.Figure(go.Pie(
                        labels=schema_sz["TABLE_SCHEMA"],
                        values=schema_sz["GB"],
                        hole=0.55,
                        textinfo="label+percent",
                        marker_colors=CHART_COLORS
                    ))
                    fig2.update_layout(
                        title="Storage by Schema",
                        height=340,
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(
                            color=COLORS["text_secondary"])
                    )
                    st.plotly_chart(
                        fig2,
                        use_container_width=True,
                        key="ov_schema_pie")

            # Top tables by rows
            if ("ROW_COUNT" in storage_df.columns
                    and "TABLE_NAME" in storage_df.columns):
                top_rows = storage_df[
                    storage_df["TABLE_TYPE"]
                    == "BASE TABLE"
                ].nlargest(20,"ROW_COUNT")
                fig3 = px.bar(
                    top_rows,
                    x="TABLE_NAME",
                    y="ROW_COUNT",
                    title="Top 20 Tables by Row Count",
                    height=300,
                    color="ROW_COUNT",
                    color_continuous_scale=[
                        COLORS["bg_elevated"],
                        COLORS["blue"],
                        COLORS["pwc_orange"]
                    ]
                )
                fig3.update_layout(
                    xaxis_tickangle=-35,
                    xaxis_title="",
                    yaxis_title="Rows",
                    coloraxis_showscale=False
                )
                st.plotly_chart(
                    fig3,
                    use_container_width=True,
                    key="ov_top_rows")

            # Full table
            with st.expander("📋 All Tables & Views"):
                st.dataframe(
                    storage_df,
                    use_container_width=True,
                    hide_index=True,
                    height=400
                )
        else:
            st.info(
                "No tables found or "
                "INFORMATION_SCHEMA not accessible.")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 2 — BROWSE
# ═══════════════════════════════════════════════════════════════════════════

with tab_browse:
    section_header("BROWSE TABLES & VIEWS")

    br1, br2, br3, br4 = st.columns(4)
    with br1:
        br_acc = st.selectbox(
            "Account", connected, key="br_acc")
    with br2:
        br_dbs = fetch_databases(id(manager), br_acc)
        br_db  = st.selectbox(
            "Database",
            br_dbs or ["(none)"],
            key="br_db"
        )
    with br3:
        br_schemas = (
            fetch_schemas(id(manager), br_acc, br_db)
            if br_db and br_db != "(none)" else []
        )
        br_schema = st.selectbox(
            "Schema",
            br_schemas or ["(none)"],
            key="br_schema"
        )
    with br4:
        br_type = st.selectbox(
            "Object Type",
            ["Tables","Views","Both"],
            key="br_type"
        )

    br_search = st.text_input(
        "🔍 Search tables / views",
        key="br_search",
        placeholder="Filter by name…"
    )

    if (br_db and br_db != "(none)"
            and br_schema and br_schema != "(none)"):

        t_df = pd.DataFrame()
        v_df = pd.DataFrame()
        env_c = get_env_color(br_acc)

        if br_type in ("Tables","Both"):
            t_df = fetch_tables(
                id(manager), br_acc,
                br_db, br_schema)
        if br_type in ("Views","Both"):
            v_df = fetch_views(
                id(manager), br_acc,
                br_db, br_schema)

        # ── Tables ───────────────────────────────────
        if not t_df.empty:
            t_nc   = next((c for c in ["name","NAME"]
                            if c in t_df.columns), None)
            t_rows = next((c for c in [
                "rows","ROWS"]
                if c in t_df.columns), None)
            t_bytes= next((c for c in [
                "bytes","BYTES"]
                if c in t_df.columns), None)
            t_kind = next((c for c in [
                "kind","KIND"]
                if c in t_df.columns), None)
            t_crt  = next((c for c in [
                "created_on","CREATED_ON"]
                if c in t_df.columns), None)
            t_alt  = next((c for c in [
                "last_altered","LAST_ALTERED"]
                if c in t_df.columns), None)
            t_clst = next((c for c in [
                "cluster_by","CLUSTER_BY"]
                if c in t_df.columns), None)
            t_cmt  = next((c for c in [
                "comment","COMMENT"]
                if c in t_df.columns), None)

            filtered_t = t_df.copy()
            if br_search and t_nc:
                filtered_t = filtered_t[
                    filtered_t[t_nc].str.contains(
                        br_search, case=False, na=False)]

            if not filtered_t.empty:
                section_header(
                    f"TABLES ({len(filtered_t)})")

                for _, tbl in filtered_t.iterrows():
                    tname = (tbl.get(t_nc,"?")
                             if t_nc else "?")
                    trows = safe_int(
                        tbl.get(t_rows,0)
                        if t_rows else 0)
                    tbytes= safe_float(
                        tbl.get(t_bytes,0)
                        if t_bytes else 0)
                    tkind = (tbl.get(t_kind,"TABLE")
                             if t_kind else "TABLE")
                    tcrt  = (str(tbl.get(t_crt,""))[:10]
                             if t_crt else "—")
                    talt  = (str(tbl.get(t_alt,""))[:10]
                             if t_alt else "—")
                    tclst = (tbl.get(t_clst,"")
                             if t_clst else "")
                    tcmt  = (tbl.get(t_cmt,"")
                             if t_cmt else "")

                    with st.expander(
                        f"📋 {tname}   "
                        f"[{fmt_num(trows)} rows · "
                        f"{fmt_bytes(tbytes)}]"
                    ):
                        ec1, ec2 = st.columns([3,1])
                        with ec1:
                            st.markdown(f"""
                            <div style="display:grid;
                                 grid-template-columns:
                                 repeat(4,1fr);
                                 gap:8px; margin-bottom:12px;">
                                <div>
                                    <div style="font-size:0.6rem;
                                         color:{COLORS['text_muted']};
                                         text-transform:uppercase;">
                                         Rows</div>
                                    <div style="font-family:
                                         'JetBrains Mono',monospace;
                                         font-size:0.85rem;
                                         font-weight:700;
                                         color:{COLORS['blue']};">
                                         {fmt_num(trows)}</div>
                                </div>
                                <div>
                                    <div style="font-size:0.6rem;
                                         color:{COLORS['text_muted']};
                                         text-transform:uppercase;">
                                         Size</div>
                                    <div style="font-family:
                                         'JetBrains Mono',monospace;
                                         font-size:0.85rem;
                                         font-weight:700;
                                         color:{COLORS['cyan']};">
                                         {fmt_bytes(tbytes)}</div>
                                </div>
                                <div>
                                    <div style="font-size:0.6rem;
                                         color:{COLORS['text_muted']};
                                         text-transform:uppercase;">
                                         Created</div>
                                    <div style="font-size:0.78rem;
                                         color:{COLORS['text_secondary']};">
                                         {tcrt}</div>
                                </div>
                                <div>
                                    <div style="font-size:0.6rem;
                                         color:{COLORS['text_muted']};
                                         text-transform:uppercase;">
                                         Last Altered</div>
                                    <div style="font-size:0.78rem;
                                         color:{COLORS['text_secondary']};">
                                         {talt}</div>
                                </div>
                            </div>
                            {f'<div style="font-size:0.7rem; color:{COLORS["text_muted"]}; margin-bottom:8px;">🗂 Cluster by: <b>{tclst}</b></div>' if tclst else ''}
                            {f'<div style="font-size:0.7rem; color:{COLORS["text_muted"]};">{tcmt}</div>' if tcmt else ''}
                            """, unsafe_allow_html=True)

                            # Columns
                            col_df = fetch_columns(
                                id(manager), br_acc,
                                br_db, br_schema, tname)
                            if not col_df.empty:
                                st.markdown(f"""
                                <div style="font-size:0.72rem;
                                     color:{COLORS['text_muted']};
                                     text-transform:uppercase;
                                     letter-spacing:1px;
                                     margin-bottom:6px;">
                                     Columns ({len(col_df)})
                                </div>""",
                                unsafe_allow_html=True)

                                cn_c  = next((c for c in [
                                    "column_name",
                                    "COLUMN_NAME"]
                                    if c in col_df.columns),
                                    None)
                                dt_c  = next((c for c in [
                                    "data_type",
                                    "DATA_TYPE"]
                                    if c in col_df.columns),
                                    None)
                                nl_c  = next((c for c in [
                                    "null?","NULL?",
                                    "is_nullable",
                                    "IS_NULLABLE"]
                                    if c in col_df.columns),
                                    None)
                                def_c = next((c for c in [
                                    "default","DEFAULT"]
                                    if c in col_df.columns),
                                    None)

                                for _, col in col_df.iterrows():
                                    cname = (col.get(cn_c,"?")
                                             if cn_c else "?")
                                    cdtype= (col.get(dt_c,"?")
                                             if dt_c else "?")
                                    cnull = (str(col.get(
                                        nl_c,"Y")).upper()
                                        in ("Y","YES","TRUE")
                                        if nl_c else True)
                                    cdef  = (col.get(def_c,"")
                                             if def_c else "")

                                    # Parse data_type JSON
                                    dtype_str = str(cdtype)
                                    try:
                                        import json
                                        parsed = json.loads(
                                            dtype_str)
                                        dtype_str = parsed.get(
                                            "type", dtype_str)
                                    except Exception:
                                        pass

                                    st.markdown(f"""
                                    <div class="col-row">
                                        <div class="nullable-dot"
                                             style="background:{COLORS['green'] if cnull else COLORS['yellow']};"></div>
                                        <span style="flex:1;
                                              font-weight:600;
                                              color:{COLORS['text_primary']};">
                                              {cname}</span>
                                        {type_badge(dtype_str)}
                                        {f'<span style="font-size:0.65rem; color:{COLORS["text_muted"]};">{str(cdef)[:20]}</span>' if cdef else ''}
                                    </div>
                                    """, unsafe_allow_html=True)

                        with ec2:
                            # Quick actions
                            if st.button(
                                "📊 Row Preview",
                                key=f"prev_{br_acc}_{tname}",
                                use_container_width=True
                            ):
                                preview = run_query(
                                    br_acc,
                                    f'SELECT * FROM '
                                    f'"{br_db}"."{br_schema}"'
                                    f'."{tname}" LIMIT 20'
                                )
                                if (preview is not None
                                        and not preview.empty):
                                    st.dataframe(
                                        preview,
                                        use_container_width=True,
                                        height=300
                                    )

                            # DDL
                            if st.button(
                                "📄 Show DDL",
                                key=f"ddl_{br_acc}_{tname}",
                                use_container_width=True
                            ):
                                ddl = run_query(
                                    br_acc,
                                    f'SELECT GET_DDL('
                                    f"'TABLE',"
                                    f'"{br_db}".'
                                    f'"{br_schema}".'
                                    f'"{tname}")'
                                )
                                if (ddl is not None
                                        and not ddl.empty):
                                    st.code(
                                        str(ddl.iloc[0,0]),
                                        language="sql"
                                    )

        # ── Views ─────────────────────────────────────
        if not v_df.empty and br_type in ("Views","Both"):
            v_nc  = next((c for c in ["name","NAME"]
                           if c in v_df.columns), None)
            v_crt = next((c for c in [
                "created_on","CREATED_ON"]
                if c in v_df.columns), None)
            v_cmt = next((c for c in [
                "comment","COMMENT"]
                if c in v_df.columns), None)
            v_text= next((c for c in [
                "text","TEXT"]
                if c in v_df.columns), None)

            filtered_v = v_df.copy()
            if br_search and v_nc:
                filtered_v = filtered_v[
                    filtered_v[v_nc].str.contains(
                        br_search, case=False, na=False)]

            if not filtered_v.empty:
                section_header(
                    f"VIEWS ({len(filtered_v)})")
                env_c2 = get_env_color(br_acc)

                for _, view in filtered_v.iterrows():
                    vname = (view.get(v_nc,"?")
                             if v_nc else "?")
                    vcrt  = (str(view.get(v_crt,""))[:10]
                             if v_crt else "—")
                    vcmt  = (view.get(v_cmt,"")
                             if v_cmt else "")
                    vtxt  = (view.get(v_text,"")
                             if v_text else "")

                    with st.expander(f"👁️ {vname}"):
                        vc1, vc2 = st.columns([3,1])
                        with vc1:
                            st.markdown(f"""
                            <div style="font-size:0.7rem;
                                 color:{COLORS['text_muted']};
                                 margin-bottom:8px;">
                                 Created: {vcrt}
                                 {f'&nbsp;|&nbsp; {vcmt}' if vcmt else ''}
                            </div>""",
                            unsafe_allow_html=True)
                            if vtxt:
                                st.code(str(vtxt)[:2000],
                                        language="sql")
                        with vc2:
                            if st.button(
                                "📊 Preview",
                                key=f"vprev_{br_acc}_{vname}",
                                use_container_width=True
                            ):
                                prev = run_query(
                                    br_acc,
                                    f'SELECT * FROM '
                                    f'"{br_db}".'
                                    f'"{br_schema}".'
                                    f'"{vname}" LIMIT 20'
                                )
                                if (prev is not None
                                        and not prev.empty):
                                    st.dataframe(
                                        prev,
                                        use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 3 — CREATE
# ═══════════════════════════════════════════════════════════════════════════

with tab_create:
    section_header("CREATE TABLE / VIEW")

    cr_obj_type = st.radio(
        "Object to create",
        ["📋 Table","👁️ View",
         "🌊 Dynamic Table","❄️ External Table"],
        horizontal=True,
        key="cr_obj_type"
    )

    # ── Common location ───────────────────────────────
    st.markdown(f"""
    <div class="step-header">
        <div class="step-num">1</div>
        <div class="step-title">Location</div>
    </div>""", unsafe_allow_html=True)

    l1,l2,l3,l4 = st.columns(4)
    with l1:
        cr_acc = st.selectbox(
            "Account", connected, key="cr_acc")
    with l2:
        cr_dbs = fetch_databases(id(manager), cr_acc)
        cr_db  = st.selectbox(
            "Database",
            cr_dbs or ["(none)"],
            key="cr_db"
        )
    with l3:
        cr_schemas = (
            fetch_schemas(id(manager), cr_acc, cr_db)
            if cr_db and cr_db != "(none)" else []
        )
        cr_schema = st.selectbox(
            "Schema",
            cr_schemas or ["(none)"],
            key="cr_schema"
        )
    with l4:
        cr_name = st.text_input(
            "Object Name *",
            placeholder="MY_TABLE",
            key="cr_obj_name"
        )

    # ── TABLE ────────────────────────────────────────
    if "Table" in cr_obj_type:

        st.markdown(f"""
        <div class="step-header">
            <div class="step-num">2</div>
            <div class="step-title">
                Column Definitions</div>
        </div>""", unsafe_allow_html=True)

        # Dynamic column builder
        if "tbl_columns" not in st.session_state:
            st.session_state.tbl_columns = [
                {"name":"ID","type":"NUMBER",
                 "nullable":False,"pk":True,
                 "default":"","comment":""},
                {"name":"CREATED_AT","type":"TIMESTAMP_NTZ",
                 "nullable":True,"pk":False,
                 "default":"CURRENT_TIMESTAMP()",
                 "comment":""},
            ]

        col_add, col_clear = st.columns([1,4])
        with col_add:
            if st.button("➕ Add Column",
                          key="add_col"):
                st.session_state.tbl_columns.append(
                    {"name":"","type":"VARCHAR(255)",
                     "nullable":True,"pk":False,
                     "default":"","comment":""}
                )

        DATA_TYPES = [
            "NUMBER","INTEGER","BIGINT","SMALLINT",
            "FLOAT","DOUBLE","DECIMAL(18,2)",
            "VARCHAR(255)","VARCHAR(1000)","TEXT",
            "STRING","CHAR(1)",
            "BOOLEAN",
            "DATE","TIME","TIMESTAMP_NTZ",
            "TIMESTAMP_TZ","TIMESTAMP_LTZ",
            "VARIANT","OBJECT","ARRAY",
            "BINARY","GEOGRAPHY"
        ]

        cols_to_delete = []
        st.markdown(f"""
        <div style="display:grid;
             grid-template-columns:
             2fr 2fr 80px 60px 1fr 1fr 50px;
             gap:6px; padding:8px 12px;
             background:{COLORS['bg_elevated']};
             border-radius:8px; margin-bottom:6px;
             font-size:0.62rem;
             color:{COLORS['text_muted']};
             text-transform:uppercase;
             letter-spacing:0.8px;">
            <div>Column Name</div>
            <div>Data Type</div>
            <div>Nullable</div>
            <div>PK</div>
            <div>Default</div>
            <div>Comment</div>
            <div></div>
        </div>""", unsafe_allow_html=True)

        for i, col_def in enumerate(
                st.session_state.tbl_columns):
            cc = st.columns([2,2,1,1,2,2,0.5])
            with cc[0]:
                col_def["name"] = st.text_input(
                    "", value=col_def["name"],
                    key=f"cn_{i}",
                    label_visibility="collapsed"
                )
            with cc[1]:
                col_def["type"] = st.selectbox(
                    "", DATA_TYPES,
                    index=(DATA_TYPES.index(
                        col_def["type"])
                        if col_def["type"]
                        in DATA_TYPES else 0),
                    key=f"ct_{i}",
                    label_visibility="collapsed"
                )
            with cc[2]:
                col_def["nullable"] = st.checkbox(
                    "", value=col_def["nullable"],
                    key=f"cnl_{i}",
                    label_visibility="collapsed"
                )
            with cc[3]:
                col_def["pk"] = st.checkbox(
                    "", value=col_def["pk"],
                    key=f"cpk_{i}",
                    label_visibility="collapsed"
                )
            with cc[4]:
                col_def["default"] = st.text_input(
                    "", value=col_def["default"],
                    key=f"cdf_{i}",
                    label_visibility="collapsed"
                )
            with cc[5]:
                col_def["comment"] = st.text_input(
                    "", value=col_def["comment"],
                    key=f"cmt_{i}",
                    label_visibility="collapsed"
                )
            with cc[6]:
                if st.button("🗑",
                              key=f"del_col_{i}"):
                    cols_to_delete.append(i)

        for i in sorted(cols_to_delete, reverse=True):
            st.session_state.tbl_columns.pop(i)

        # Step 3 — Table Properties
        st.markdown(f"""
        <div class="step-header">
            <div class="step-num">3</div>
            <div class="step-title">
                Table Properties</div>
        </div>""", unsafe_allow_html=True)

        tp1, tp2, tp3, tp4 = st.columns(4)
        with tp1:
            tbl_data_retention = st.number_input(
                "Data Retention (days)",
                min_value=0, max_value=90, value=1,
                key="tbl_retention"
            )
        with tp2:
            tbl_cluster_by = st.text_input(
                "Cluster By (optional)",
                placeholder="CREATED_AT, REGION",
                key="tbl_cluster"
            )
        with tp3:
            tbl_change_tracking = st.checkbox(
                "Enable Change Tracking",
                value=False,
                key="tbl_change_track"
            )
        with tp4:
            tbl_comment = st.text_input(
                "Table Comment",
                key="tbl_comment"
            )

        # Build SQL
        if (cr_name and cr_db != "(none)"
                and cr_schema != "(none)"):
            col_defs = []
            pk_cols  = []

            for cd in st.session_state.tbl_columns:
                if not cd["name"]:
                    continue
                parts = [f'    "{cd["name"]}" {cd["type"]}']
                if not cd["nullable"]:
                    parts.append("NOT NULL")
                if cd["default"]:
                    parts.append(
                        f'DEFAULT {cd["default"]}')
                if cd["comment"]:
                    parts.append(
                        f"COMMENT '{cd['comment']}'")
                col_defs.append(" ".join(parts))
                if cd["pk"]:
                    pk_cols.append(f'"{cd["name"]}"')

            if pk_cols:
                col_defs.append(
                    f'    PRIMARY KEY '
                    f'({", ".join(pk_cols)})'
                )

            props = []
            if tbl_data_retention != 1:
                props.append(
                    f"DATA_RETENTION_TIME_IN_DAYS = "
                    f"{tbl_data_retention}")
            if tbl_cluster_by:
                props.append(
                    f"CLUSTER BY ({tbl_cluster_by})")
            if tbl_change_tracking:
                props.append(
                    "CHANGE_TRACKING = TRUE")
            if tbl_comment:
                props.append(
                    f"COMMENT = '{tbl_comment}'")

            create_tbl_sql = (
                f'CREATE OR REPLACE TABLE '
                f'"{cr_db}"."{cr_schema}".'
                f'"{cr_name}" (\n'
                + ",\n".join(col_defs) + "\n)"
                + ("\n" + "\n".join(props)
                   if props else "")
                + ";"
            )

            section_header("GENERATED SQL")
            st.markdown(
                f'<div class="sql-block">'
                f'{create_tbl_sql}</div>',
                unsafe_allow_html=True)

            cb1, cb2 = st.columns(2)
            with cb1:
                create_tbl_btn = st.button(
                    "▶️ Create Table",
                    type="primary",
                    key="btn_create_tbl"
                )
            with cb2:
                if st.button("📋 Copy SQL",
                              key="btn_copy_tbl"):
                    st.code(create_tbl_sql,
                            language="sql")

            if create_tbl_btn:
                with st.status(
                    f"Creating {cr_name}…",
                    expanded=True
                ) as cstatus:
                    st.write("🔍 Validating…")
                    time.sleep(0.3)
                    ok, result = run_statement(
                        cr_acc, create_tbl_sql)
                    time.sleep(0.3)
                    if ok:
                        cstatus.update(
                            label=(
                                f"✅ Table "
                                f"{cr_name} created!"),
                            state="complete",
                            expanded=False
                        )
                    else:
                        cstatus.update(
                            label="❌ Failed",
                            state="error",
                            expanded=True
                        )
                if ok:
                    st.success(
                        f"✅ Table **{cr_name}** "
                        f"created!")
                    st.session_state.tbl_columns = []
                    st.cache_data.clear()
                    st.balloons()
                else:
                    st.error(f"❌ {result}")

    # ── VIEW ─────────────────────────────────────────
    elif "View" in cr_obj_type:

        st.markdown(f"""
        <div class="step-header">
            <div class="step-num">2</div>
            <div class="step-title">
                View Definition</div>
        </div>""", unsafe_allow_html=True)

        vw1, vw2 = st.columns(2)
        with vw1:
            view_secure = st.checkbox(
                "Secure View",
                value=False,
                key="vw_secure"
            )
            view_recursive = st.checkbox(
                "Recursive",
                value=False,
                key="vw_recursive"
            )
        with vw2:
            view_comment = st.text_input(
                "Comment", key="vw_comment")

        view_sql = st.text_area(
            "View SELECT Statement *",
            placeholder=(
                "SELECT\n"
                "    t.id,\n"
                "    t.name,\n"
                "    t.created_at\n"
                "FROM source_table t\n"
                "WHERE t.active = TRUE"
            ),
            height=180,
            key="vw_sql"
        )

        if (cr_name and cr_db != "(none)"
                and cr_schema != "(none)"
                and view_sql):
            secure_clause = (
                " SECURE" if view_secure else "")
            recursive_c   = (
                " RECURSIVE"
                if view_recursive else "")
            comment_c     = (
                f"\n    COMMENT = '{view_comment}'"
                if view_comment else "")
            create_vw_sql = (
                f'CREATE OR REPLACE{secure_clause}'
                f'{recursive_c} VIEW '
                f'"{cr_db}"."{cr_schema}".'
                f'"{cr_name}"{comment_c}\nAS\n'
                f'{view_sql};'
            )

            st.markdown(
                f'<div class="sql-block">'
                f'{create_vw_sql}</div>',
                unsafe_allow_html=True)

            if st.button("▶️ Create View",
                          type="primary",
                          key="btn_create_vw"):
                ok, result = run_statement(
                    cr_acc, create_vw_sql)
                if ok:
                    st.success(
                        f"✅ View **{cr_name}** "
                        f"created!")
                    st.cache_data.clear()
                    st.balloons()
                else:
                    st.error(f"❌ {result}")

    # ── DYNAMIC TABLE ─────────────────────────────────
    elif "Dynamic" in cr_obj_type:

        st.markdown(f"""
        <div class="info-box">
            <b style="color:{COLORS['pwc_gold']};">
            Dynamic Tables</b> automatically refresh
            on a schedule to reflect upstream changes —
            ideal for materialization pipelines.
        </div>""", unsafe_allow_html=True)

        dt1, dt2, dt3 = st.columns(3)
        with dt1:
            dt_wh = st.text_input(
                "Warehouse",
                placeholder="COMPUTE_WH",
                key="dt_wh"
            )
        with dt2:
            dt_lag = st.text_input(
                "Target Lag",
                value="1 minute",
                key="dt_lag",
                help="e.g. '5 minutes', '1 hour'"
            )
        with dt3:
            dt_refresh = st.selectbox(
                "Refresh Mode",
                ["AUTO","FULL","INCREMENTAL"],
                key="dt_refresh"
            )

        dt_sql = st.text_area(
            "AS SELECT …",
            placeholder=(
                "SELECT id, name, amount\n"
                "FROM source_table"
            ),
            height=140,
            key="dt_sql"
        )

        if (cr_name and cr_db != "(none)"
                and cr_schema != "(none)"
                and dt_wh and dt_sql):
            create_dt_sql = (
                f'CREATE OR REPLACE DYNAMIC TABLE '
                f'"{cr_db}"."{cr_schema}".'
                f'"{cr_name}"\n'
                f'    TARGET_LAG = \'{dt_lag}\'\n'
                f'    WAREHOUSE = {dt_wh}\n'
                f'    REFRESH_MODE = {dt_refresh}\n'
                f'AS\n{dt_sql};'
            )
            st.markdown(
                f'<div class="sql-block">'
                f'{create_dt_sql}</div>',
                unsafe_allow_html=True)

            if st.button("▶️ Create Dynamic Table",
                          type="primary",
                          key="btn_create_dt"):
                ok, result = run_statement(
                    cr_acc, create_dt_sql)
                if ok:
                    st.success(
                        f"✅ Dynamic Table "
                        f"**{cr_name}** created!")
                    st.cache_data.clear()
                    st.balloons()
                else:
                    st.error(f"❌ {result}")

    # ── EXTERNAL TABLE ────────────────────────────────
    elif "External" in cr_obj_type:

        st.markdown(f"""
        <div class="info-box">
            <b style="color:{COLORS['blue']};">
            External Tables</b> expose files in an
            external stage as a queryable table.
        </div>""", unsafe_allow_html=True)

        et1, et2 = st.columns(2)
        with et1:
            et_location = st.text_input(
                "Location (Stage)",
                placeholder=
                "@MY_DB.MY_SCHEMA.MY_STAGE/prefix/",
                key="et_location"
            )
            et_file_format = st.selectbox(
                "File Format",
                ["CSV","JSON","PARQUET",
                 "AVRO","ORC"],
                key="et_ff"
            )
        with et2:
            et_pattern = st.text_input(
                "File Pattern",
                placeholder=r".*\.parquet",
                key="et_pattern"
            )
            et_auto_refresh = st.checkbox(
                "Auto Refresh",
                value=True,
                key="et_auto_refresh"
            )

        et_col_def = st.text_area(
            "Column definitions",
            placeholder=(
                "VALUE VARIANT AS "
                "(VALUE:id::INTEGER),\n"
                "METADATA$FILENAME VARCHAR"
            ),
            height=100,
            key="et_col_def"
        )

        if (cr_name and cr_db != "(none)"
                and cr_schema != "(none)"
                and et_location):
            ar_c = (
                "\n    AUTO_REFRESH = TRUE"
                if et_auto_refresh else ""
            )
            pat_c = (
                f"\n    PATTERN = '{et_pattern}'"
                if et_pattern else ""
            )
            col_c = (
                f" (\n    {et_col_def}\n)"
                if et_col_def else ""
            )
            create_et_sql = (
                f'CREATE OR REPLACE EXTERNAL TABLE '
                f'"{cr_db}"."{cr_schema}".'
                f'"{cr_name}"{col_c}\n'
                f'    WITH LOCATION = {et_location}'
                f'\n    FILE_FORMAT = '
                f'(TYPE = \'{et_file_format}\')'
                f'{pat_c}{ar_c};'
            )
            st.markdown(
                f'<div class="sql-block">'
                f'{create_et_sql}</div>',
                unsafe_allow_html=True)

            if st.button(
                "▶️ Create External Table",
                type="primary",
                key="btn_create_et"
            ):
                ok, result = run_statement(
                    cr_acc, create_et_sql)
                if ok:
                    st.success(
                        f"✅ External Table "
                        f"**{cr_name}** created!")
                    st.cache_data.clear()
                    st.balloons()
                else:
                    st.error(f"❌ {result}")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 4 — ALTER
# ═══════════════════════════════════════════════════════════════════════════

with tab_alter:
    section_header("ALTER TABLE / VIEW")

    al1, al2, al3, al4 = st.columns(4)
    with al1:
        al_acc = st.selectbox(
            "Account", connected, key="al_acc")
    with al2:
        al_dbs = fetch_databases(id(manager), al_acc)
        al_db  = st.selectbox(
            "Database",
            al_dbs or ["(none)"],
            key="al_db"
        )
    with al3:
        al_schemas = (
            fetch_schemas(id(manager), al_acc, al_db)
            if al_db and al_db != "(none)" else []
        )
        al_schema = st.selectbox(
            "Schema",
            al_schemas or ["(none)"],
            key="al_schema"
        )
    with al4:
        al_tbl_df = (
            fetch_tables(
                id(manager), al_acc, al_db, al_schema)
            if al_db != "(none)"
            and al_schema != "(none)" else pd.DataFrame()
        )
        al_nc  = next((c for c in ["name","NAME"]
                        if c in al_tbl_df.columns), None)
        al_tbl_list = (
            al_tbl_df[al_nc].tolist()
            if al_nc and not al_tbl_df.empty else []
        )
        al_table = st.selectbox(
            "Table",
            al_tbl_list or ["(none)"],
            key="al_table"
        )

    if (al_table and al_table != "(none)"
            and al_db != "(none)"
            and al_schema != "(none)"):

        # Show current columns
        cur_cols = fetch_columns(
            id(manager), al_acc,
            al_db, al_schema, al_table)

        cur_col_names = []
        if not cur_cols.empty:
            cn_c = next((c for c in [
                "column_name","COLUMN_NAME"]
                if c in cur_cols.columns), None)
            if cn_c:
                cur_col_names = (
                    cur_cols[cn_c].tolist())
            st.markdown(f"""
            <div style="font-size:0.72rem;
                 color:{COLORS['text_muted']};
                 margin-bottom:8px;">
                 Current columns: {len(cur_cols)}
            </div>""", unsafe_allow_html=True)

        # Alter operations
        alter_op = st.selectbox(
            "Operation",
            [
                "➕ Add Column",
                "🗑️ Drop Column",
                "✏️ Rename Column",
                "🔄 Modify Column Type",
                "🔤 Rename Table",
                "💬 Set Comment",
                "🔑 Add Primary Key",
                "🚫 Drop Primary Key",
                "🗂️ Set Clustering Key",
                "📦 Set Data Retention",
                "📡 Enable Change Tracking",
                "🔃 Swap With",
                "📋 Custom SQL",
            ],
            key="alter_op"
        )

        alter_sql = ""

        if "Add Column" in alter_op:
            ac1, ac2, ac3, ac4 = st.columns(4)
            with ac1:
                new_col_name = st.text_input(
                    "Column Name",
                    key="ac_name"
                )
            with ac2:
                new_col_type = st.selectbox(
                    "Data Type",
                    ["VARCHAR(255)","NUMBER",
                     "BOOLEAN","DATE","TIMESTAMP_NTZ",
                     "VARIANT","TEXT","FLOAT"],
                    key="ac_type"
                )
            with ac3:
                new_col_null = st.checkbox(
                    "Nullable",
                    value=True, key="ac_null")
                new_col_def  = st.text_input(
                    "Default",
                    key="ac_default"
                )
            with ac4:
                new_col_cmt  = st.text_input(
                    "Comment",
                    key="ac_comment"
                )
                after_col    = st.selectbox(
                    "After Column",
                    ["(end)"] + cur_col_names,
                    key="ac_after"
                )
            if new_col_name:
                null_c  = ("" if new_col_null
                           else " NOT NULL")
                def_c   = (f" DEFAULT {new_col_def}"
                           if new_col_def else "")
                cmt_c   = (
                    f" COMMENT '{new_col_cmt}'"
                    if new_col_cmt else "")
                after_c = (
                    f" AFTER \"{after_col}\""
                    if after_col != "(end)" else "")
                alter_sql = (
                    f'ALTER TABLE "{al_db}".'
                    f'"{al_schema}"."{al_table}"\n'
                    f'    ADD COLUMN '
                    f'"{new_col_name}" '
                    f'{new_col_type}'
                    f'{null_c}{def_c}{cmt_c}'
                    f'{after_c};'
                )

        elif "Drop Column" in alter_op:
            drop_col = st.selectbox(
                "Column to Drop",
                cur_col_names,
                key="drop_col"
            )
            st.warning(
                f"⚠️ Dropping **{drop_col}** "
                f"is irreversible.")
            if drop_col:
                alter_sql = (
                    f'ALTER TABLE "{al_db}".'
                    f'"{al_schema}"."{al_table}"\n'
                    f'    DROP COLUMN "{drop_col}";'
                )

        elif "Rename Column" in alter_op:
            rc1, rc2 = st.columns(2)
            with rc1:
                old_col = st.selectbox(
                    "Old Column Name",
                    cur_col_names, key="rc_old")
            with rc2:
                new_col = st.text_input(
                    "New Column Name",
                    key="rc_new"
                )
            if old_col and new_col:
                alter_sql = (
                    f'ALTER TABLE "{al_db}".'
                    f'"{al_schema}"."{al_table}"\n'
                    f'    RENAME COLUMN '
                    f'"{old_col}" TO "{new_col}";'
                )

        elif "Modify Column Type" in alter_op:
            mc1, mc2, mc3 = st.columns(3)
            with mc1:
                mod_col = st.selectbox(
                    "Column",
                    cur_col_names, key="mod_col")
            with mc2:
                mod_type = st.selectbox(
                    "New Type",
                    ["VARCHAR(255)","VARCHAR(1000)",
                     "NUMBER","BIGINT","FLOAT",
                     "BOOLEAN","TEXT","VARIANT"],
                    key="mod_type"
                )
            with mc3:
                mod_null = st.radio(
                    "Nullability",
                    ["No change","SET NULL",
                     "SET NOT NULL"],
                    key="mod_null"
                )
            if mod_col:
                null_c = (
                    " SET NULL"
                    if mod_null == "SET NULL"
                    else " SET NOT NULL"
                    if mod_null == "SET NOT NULL"
                    else ""
                )
                alter_sql = (
                    f'ALTER TABLE "{al_db}".'
                    f'"{al_schema}"."{al_table}"\n'
                    f'    ALTER COLUMN "{mod_col}"\n'
                    f'    SET DATA TYPE {mod_type}'
                    f'{null_c};'
                )

        elif "Rename Table" in alter_op:
            new_tbl_name = st.text_input(
                "New Table Name", key="rt_new")
            if new_tbl_name:
                alter_sql = (
                    f'ALTER TABLE "{al_db}".'
                    f'"{al_schema}"."{al_table}"\n'
                    f'    RENAME TO '
                    f'"{new_tbl_name}";'
                )

        elif "Set Comment" in alter_op:
            tbl_cmt = st.text_area(
                "New Comment",
                height=80, key="tbl_cmt_new"
            )
            if tbl_cmt:
                alter_sql = (
                    f'ALTER TABLE "{al_db}".'
                    f'"{al_schema}"."{al_table}"\n'
                    f"    SET COMMENT = '{tbl_cmt}';"
                )

        elif "Add Primary Key" in alter_op:
            pk_cols = st.multiselect(
                "Primary Key Columns",
                cur_col_names, key="pk_cols")
            if pk_cols:
                pk_str = ", ".join(
                    [f'"{c}"' for c in pk_cols])
                alter_sql = (
                    f'ALTER TABLE "{al_db}".'
                    f'"{al_schema}"."{al_table}"\n'
                    f'    ADD PRIMARY KEY ({pk_str});'
                )

        elif "Drop Primary Key" in alter_op:
            alter_sql = (
                f'ALTER TABLE "{al_db}".'
                f'"{al_schema}"."{al_table}"\n'
                f'    DROP PRIMARY KEY;'
            )

        elif "Set Clustering Key" in alter_op:
            clust_cols = st.multiselect(
                "Clustering Key Columns",
                cur_col_names,
                key="clust_cols"
            )
            if clust_cols:
                ck_str = ", ".join(
                    [f'"{c}"' for c in clust_cols])
                alter_sql = (
                    f'ALTER TABLE "{al_db}".'
                    f'"{al_schema}"."{al_table}"\n'
                    f'    CLUSTER BY ({ck_str});'
                )

        elif "Set Data Retention" in alter_op:
            ret_days = st.number_input(
                "Data Retention Days",
                min_value=0,
                max_value=90, value=1,
                key="ret_days"
            )
            alter_sql = (
                f'ALTER TABLE "{al_db}".'
                f'"{al_schema}"."{al_table}"\n'
                f'    SET DATA_RETENTION_TIME_IN_DAYS'
                f' = {ret_days};'
            )

        elif "Change Tracking" in alter_op:
            ct_enable = st.radio(
                "Change Tracking",
                ["ENABLE","DISABLE"],
                horizontal=True,
                key="ct_enable"
            )
            alter_sql = (
                f'ALTER TABLE "{al_db}".'
                f'"{al_schema}"."{al_table}"\n'
                f'    SET CHANGE_TRACKING = '
                f'{"TRUE" if ct_enable == "ENABLE" else "FALSE"};'
            )

        elif "Swap With" in alter_op:
            swap_tbl = st.selectbox(
                "Swap With Table",
                al_tbl_list,
                key="swap_tbl"
            )
            if swap_tbl and swap_tbl != al_table:
                alter_sql = (
                    f'ALTER TABLE "{al_db}".'
                    f'"{al_schema}"."{al_table}"\n'
                    f'    SWAP WITH '
                    f'"{al_db}"."{al_schema}".'
                    f'"{swap_tbl}";'
                )

        elif "Custom SQL" in alter_op:
            alter_sql = st.text_area(
                "Custom ALTER SQL",
                placeholder=(
                    f'ALTER TABLE "{al_db}".'
                    f'"{al_schema}"."{al_table}"\n'
                    f'    SET ...;'
                ),
                height=140,
                key="custom_alter_sql"
            )

        if alter_sql:
            st.markdown(
                f'<div class="sql-block">'
                f'{alter_sql}</div>',
                unsafe_allow_html=True)

            if st.button(
                "▶️ Execute ALTER",
                type="primary",
                key="btn_alter_tbl"
            ):
                ok, result = run_statement(
                    al_acc, alter_sql)
                if ok:
                    st.success(
                        "✅ ALTER executed "
                        "successfully!")
                    st.cache_data.clear()
                else:
                    st.error(f"❌ {result}")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 5 — PERMISSIONS
# ═══════════════════════════════════════════════════════════════════════════

with tab_permissions:
    section_header("TABLE & VIEW PERMISSIONS")

    pm_tab1, pm_tab2, pm_tab3 = st.tabs([
        "🔍 View Grants",
        "➕ Grant Privileges",
        "➖ Revoke Privileges"
    ])

    with pm_tab1:
        p1,p2,p3,p4 = st.columns(4)
        with p1:
            pm_acc = st.selectbox(
                "Account", connected, key="pm_acc")
        with p2:
            pm_dbs = fetch_databases(
                id(manager), pm_acc)
            pm_db  = st.selectbox(
                "Database",
                pm_dbs or ["(none)"],
                key="pm_db"
            )
        with p3:
            pm_schemas = (
                fetch_schemas(
                    id(manager), pm_acc, pm_db)
                if pm_db != "(none)" else []
            )
            pm_schema = st.selectbox(
                "Schema",
                pm_schemas or ["(none)"],
                key="pm_schema"
            )
        with p4:
            pm_tdf = (
                fetch_tables(
                    id(manager), pm_acc,
                    pm_db, pm_schema)
                if pm_db != "(none)"
                and pm_schema != "(none)"
                else pd.DataFrame()
            )
            pm_nc = next((c for c in ["name","NAME"]
                           if c in pm_tdf.columns),
                         None)
            pm_tbl_list = (
                pm_tdf[pm_nc].tolist()
                if pm_nc and not pm_tdf.empty else []
            )
            pm_table = st.selectbox(
                "Table",
                pm_tbl_list or ["(none)"],
                key="pm_table"
            )

        if (pm_table and pm_table != "(none)"):
            grants = fetch_grants_on_table(
                id(manager), pm_acc,
                pm_db, pm_schema, pm_table)

            if not grants.empty:
                priv_c    = next((c for c in [
                    "privilege","PRIVILEGE"]
                    if c in grants.columns), None)
                grantee_c = next((c for c in [
                    "grantee_name","GRANTEE_NAME"]
                    if c in grants.columns), None)
                granton_c = next((c for c in [
                    "granted_on","GRANTED_ON"]
                    if c in grants.columns), None)
                grantby_c = next((c for c in [
                    "granted_by","GRANTED_BY"]
                    if c in grants.columns), None)

                st.markdown(f"""
                <div style="font-size:0.72rem;
                     color:{COLORS['text_muted']};
                     margin-bottom:10px;">
                     {len(grants)} grant(s) on
                     <b style="color:{COLORS['text_primary']};">
                     {pm_table}</b>
                </div>""", unsafe_allow_html=True)

                for _, g in grants.iterrows():
                    priv    = (g.get(priv_c,"?")
                               if priv_c else "?")
                    grantee = (g.get(grantee_c,"?")
                               if grantee_c else "?")
                    gby     = (g.get(grantby_c,"?")
                               if grantby_c else "?")

                    st.markdown(f"""
                    <div class="change-row">
                        {priv_chip(priv)}
                        <div style="flex:1;">
                            <span style="font-weight:600;
                                  color:{COLORS['text_primary']};
                                  font-size:0.82rem;">
                                  {grantee}</span>
                        </div>
                        <span style="font-size:0.68rem;
                              color:{COLORS['text_muted']};">
                              by {gby}</span>
                    </div>
                    """, unsafe_allow_html=True)

                # Download
                csv = grants.to_csv(index=False)
                st.download_button(
                    "📥 Download Grants",
                    data=csv,
                    file_name=(
                        f"grants_{pm_table}_"
                        f"{datetime.date.today()}.csv"),
                    mime="text/csv",
                    key="pm_grants_dl"
                )
            else:
                st.info(
                    f"No grants found on {pm_table}")

    with pm_tab2:
        gp1, gp2 = st.columns(2)
        with gp1:
            gp_acc = st.selectbox(
                "Account", connected, key="gp_acc")
            gp_dbs = fetch_databases(
                id(manager), gp_acc)
            gp_db  = st.selectbox(
                "Database",
                gp_dbs or ["(none)"],
                key="gp_db"
            )
            gp_schemas = (
                fetch_schemas(
                    id(manager), gp_acc, gp_db)
                if gp_db != "(none)" else []
            )
            gp_schema = st.selectbox(
                "Schema",
                gp_schemas or ["(none)"],
                key="gp_schema"
            )

        with gp2:
            gp_roles = fetch_roles(
                id(manager), gp_acc)
            gp_role  = st.selectbox(
                "Grant To Role",
                gp_roles or ["(none)"],
                key="gp_role"
            )
            gp_privs = st.multiselect(
                "Privileges",
                ["SELECT","INSERT","UPDATE","DELETE",
                 "TRUNCATE","REFERENCES",
                 "ALL PRIVILEGES"],
                default=["SELECT"],
                key="gp_privs"
            )

        gp_scope = st.radio(
            "Scope",
            ["Specific Table","All Tables in Schema",
             "All Views in Schema",
             "All Tables & Views",
             "Future Tables","Future Views"],
            horizontal=True,
            key="gp_scope"
        )

        grant_sqls = []
        if "Specific" in gp_scope:
            gp_tdf2 = (
                fetch_tables(
                    id(manager), gp_acc,
                    gp_db, gp_schema)
                if gp_db != "(none)"
                and gp_schema != "(none)"
                else pd.DataFrame()
            )
            gp_nc2 = next((c for c in ["name","NAME"]
                            if c in gp_tdf2.columns),
                          None)
            gp_tbl_list2 = (
                gp_tdf2[gp_nc2].tolist()
                if gp_nc2 and not gp_tdf2.empty
                else []
            )
            gp_table2 = st.selectbox(
                "Table",
                gp_tbl_list2 or ["(none)"],
                key="gp_table2"
            )
            if (gp_table2 != "(none)"
                    and gp_privs and gp_role
                    and gp_role != "(none)"):
                privs = ", ".join(gp_privs)
                grant_sqls.append(
                    f'GRANT {privs} ON TABLE '
                    f'"{gp_db}"."{gp_schema}".'
                    f'"{gp_table2}" '
                    f'TO ROLE "{gp_role}";'
                )
        elif "All Tables in Schema" in gp_scope:
            if (gp_privs and gp_role
                    and gp_role != "(none)"
                    and gp_db != "(none)"
                    and gp_schema != "(none)"):
                privs = ", ".join(gp_privs)
                grant_sqls.append(
                    f'GRANT {privs} ON ALL TABLES '
                    f'IN SCHEMA '
                    f'"{gp_db}"."{gp_schema}" '
                    f'TO ROLE "{gp_role}";'
                )
        elif "All Views in Schema" in gp_scope:
            if (gp_privs and gp_role
                    and gp_role != "(none)"
                    and gp_db != "(none)"
                    and gp_schema != "(none)"):
                privs = ", ".join(gp_privs)
                grant_sqls.append(
                    f'GRANT {privs} ON ALL VIEWS '
                    f'IN SCHEMA '
                    f'"{gp_db}"."{gp_schema}" '
                    f'TO ROLE "{gp_role}";'
                )
        elif "All Tables & Views" in gp_scope:
            if (gp_privs and gp_role
                    and gp_role != "(none)"
                    and gp_db != "(none)"
                    and gp_schema != "(none)"):
                privs = ", ".join(gp_privs)
                grant_sqls += [
                    f'GRANT {privs} ON ALL TABLES '
                    f'IN SCHEMA '
                    f'"{gp_db}"."{gp_schema}" '
                    f'TO ROLE "{gp_role}";',
                    f'GRANT {privs} ON ALL VIEWS '
                    f'IN SCHEMA '
                    f'"{gp_db}"."{gp_schema}" '
                    f'TO ROLE "{gp_role}";',
                ]
        elif "Future Tables" in gp_scope:
            if (gp_privs and gp_role
                    and gp_role != "(none)"
                    and gp_db != "(none)"
                    and gp_schema != "(none)"):
                privs = ", ".join(gp_privs)
                grant_sqls.append(
                    f'GRANT {privs} ON FUTURE TABLES '
                    f'IN SCHEMA '
                    f'"{gp_db}"."{gp_schema}" '
                    f'TO ROLE "{gp_role}";'
                )
        elif "Future Views" in gp_scope:
            if (gp_privs and gp_role
                    and gp_role != "(none)"
                    and gp_db != "(none)"
                    and gp_schema != "(none)"):
                privs = ", ".join(gp_privs)
                grant_sqls.append(
                    f'GRANT {privs} ON FUTURE VIEWS '
                    f'IN SCHEMA '
                    f'"{gp_db}"."{gp_schema}" '
                    f'TO ROLE "{gp_role}";'
                )

        gp_with_grant = st.checkbox(
            "WITH GRANT OPTION",
            value=False,
            key="gp_with_grant"
        )
        if gp_with_grant:
            grant_sqls = [
                s.rstrip(";")
                + " WITH GRANT OPTION;"
                for s in grant_sqls
            ]

        if grant_sqls:
            for gs in grant_sqls:
                st.markdown(
                    f'<div class="sql-block">'
                    f'{gs}</div>',
                    unsafe_allow_html=True)

            if st.button(
                "▶️ Execute Grant",
                type="primary",
                key="btn_grant_tbl"
            ):
                for gs in grant_sqls:
                    ok, msg = run_statement(
                        gp_acc, gs)
                    if ok:
                        st.success("✅ Granted!")
                    else:
                        st.error(f"❌ {msg}")

    with pm_tab3:
        rv1, rv2 = st.columns(2)
        with rv1:
            rv_acc = st.selectbox(
                "Account", connected, key="rv_acc")
            rv_dbs = fetch_databases(
                id(manager), rv_acc)
            rv_db  = st.selectbox(
                "Database",
                rv_dbs or ["(none)"],
                key="rv_db"
            )
            rv_schemas = (
                fetch_schemas(
                    id(manager), rv_acc, rv_db)
                if rv_db != "(none)" else []
            )
            rv_schema = st.selectbox(
                "Schema",
                rv_schemas or ["(none)"],
                key="rv_schema"
            )
        with rv2:
            rv_roles = fetch_roles(
                id(manager), rv_acc)
            rv_role  = st.selectbox(
                "Revoke From Role",
                rv_roles or ["(none)"],
                key="rv_role"
            )
            rv_privs = st.multiselect(
                "Privileges to Revoke",
                ["SELECT","INSERT","UPDATE","DELETE",
                 "TRUNCATE","REFERENCES",
                 "ALL PRIVILEGES"],
                key="rv_privs"
            )

        rv_tdf = (
            fetch_tables(
                id(manager), rv_acc, rv_db, rv_schema)
            if rv_db != "(none)"
            and rv_schema != "(none)"
            else pd.DataFrame()
        )
        rv_nc  = next((c for c in ["name","NAME"]
                        if c in rv_tdf.columns), None)
        rv_tbl_list = (
            rv_tdf[rv_nc].tolist()
            if rv_nc and not rv_tdf.empty else []
        )
        rv_table = st.selectbox(
            "Table",
            rv_tbl_list or ["(none)"],
            key="rv_table"
        )

        rv_cascade = st.checkbox(
            "CASCADE",
            value=False, key="rv_cascade"
        )

        if (rv_table != "(none)"
                and rv_privs
                and rv_role != "(none)"):
            privs_r = ", ".join(rv_privs)
            casc_c  = (
                " CASCADE" if rv_cascade else "")
            revoke_sql = (
                f'REVOKE {privs_r} ON TABLE '
                f'"{rv_db}"."{rv_schema}".'
                f'"{rv_table}" '
                f'FROM ROLE "{rv_role}"'
                f'{casc_c};'
            )
            st.markdown(
                f'<div class="sql-block">'
                f'{revoke_sql}</div>',
                unsafe_allow_html=True)

            if st.button(
                "▶️ Execute Revoke",
                type="primary",
                key="btn_revoke_tbl"
            ):
                ok, msg = run_statement(
                    rv_acc, revoke_sql)
                if ok:
                    st.success("✅ Revoked!")
                else:
                    st.error(f"❌ {msg}")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 6 — SCHEMA EVOLUTION
# ═══════════════════════════════════════════════════════════════════════════

with tab_evolution:
    section_header("SCHEMA EVOLUTION MONITORING")

    st.markdown(f"""
    <div class="info-box">
        Track all DDL changes (CREATE, ALTER, DROP)
        to tables, views and schemas across all
        environments. Detect unplanned schema
        drift before it causes pipeline failures.
    </div>
    """, unsafe_allow_html=True)

    ev1, ev2, ev3 = st.columns(3)
    with ev1:
        ev_accs = st.multiselect(
            "Environments",
            connected, default=connected,
            key="ev_accs"
        )
    with ev2:
        ev_days = st.selectbox(
            "Time Range",
            [1,7,14,30,60,90], index=2,
            format_func=lambda x: f"Last {x} days",
            key="ev_days"
        )
    with ev3:
        ev_search = st.text_input(
            "🔍 Search",
            key="ev_search",
            placeholder="Table or schema name…"
        )

    ev_dfs = []
    for acc in (ev_accs or connected):
        edf = fetch_schema_evolution(
            id(manager), acc, ev_days)
        if not edf.empty:
            ev_dfs.append(edf)

    if not ev_dfs:
        st.info(
            "No schema changes detected "
            "in the selected window.")
    else:
        ev_df = pd.concat(
            ev_dfs, ignore_index=True)

        # Apply search
        if ev_search:
            mask = ev_df.apply(
                lambda r: r.astype(str).str.contains(
                    ev_search, case=False, na=False
                ).any(), axis=1
            )
            ev_df = ev_df[mask]

        # Numeric
        if "DURATION_SEC" in ev_df.columns:
            ev_df["DURATION_SEC"] = pd.to_numeric(
                ev_df["DURATION_SEC"],
                errors="coerce"
            ).fillna(0)
        if "START_TIME" in ev_df.columns:
            ev_df["START_TIME"] = pd.to_datetime(
                ev_df["START_TIME"], errors="coerce")

        # KPIs
        n_total = len(ev_df)
        n_creates= safe_int(len(ev_df[
            ev_df["QUERY_TYPE"].str.contains(
                "CREATE", na=False)])
            if "QUERY_TYPE" in ev_df.columns else 0)
        n_alters = safe_int(len(ev_df[
            ev_df["QUERY_TYPE"].str.contains(
                "ALTER", na=False)])
            if "QUERY_TYPE" in ev_df.columns else 0)
        n_drops  = safe_int(len(ev_df[
            ev_df["QUERY_TYPE"].str.contains(
                "DROP", na=False)])
            if "QUERY_TYPE" in ev_df.columns else 0)
        n_users  = safe_int(
            ev_df["USER_NAME"].nunique()
            if "USER_NAME" in ev_df.columns else 0)

        ek1,ek2,ek3,ek4,ek5 = st.columns(5)
        ek1.metric("Total Changes", f"{n_total:,}")
        ek2.metric("Creates",  f"{n_creates:,}")
        ek3.metric("Alters",   f"{n_alters:,}")
        ek4.metric("Drops",    f"{n_drops:,}")
        ek5.metric("Users",    f"{n_users}")

        st.markdown(
            "<div style='height:8px'></div>",
            unsafe_allow_html=True)

        # Charts
        ev_t1, ev_t2, ev_t3 = st.tabs([
            "📊 Trend Charts",
            "🔥 Change Heatmap",
            "📋 Change Log"
        ])

        cmap_ev = {n: get_env_color(n)
                   for n in ev_df["_ACCOUNT"].unique()}

        with ev_t1:
            if "START_TIME" in ev_df.columns:
                ev_df["DATE"] = ev_df[
                    "START_TIME"].dt.date

                ec1, ec2 = st.columns(2)
                with ec1:
                    # DDL type trend
                    if "QUERY_TYPE" in ev_df.columns:
                        type_cats = {
                            "CREATE": COLORS["green"],
                            "ALTER":  COLORS["pwc_gold"],
                            "DROP":   COLORS["red"],
                        }
                        ev_df["CHANGE_CAT"] = (
                            ev_df["QUERY_TYPE"].apply(
                                lambda x:
                                "CREATE"
                                if "CREATE" in str(x)
                                else "ALTER"
                                if "ALTER" in str(x)
                                else "DROP"
                                if "DROP" in str(x)
                                else "OTHER"
                            )
                        )
                        daily_ev = ev_df.groupby(
                            ["DATE","CHANGE_CAT"]
                        ).size().reset_index(
                            name="Count")
                        fig = px.bar(
                            daily_ev,
                            x="DATE", y="Count",
                            color="CHANGE_CAT",
                            color_discrete_map=type_cats,
                            title="DDL Changes by Type",
                            height=340,
                            barmode="stack"
                        )
                        fig.update_layout(
                            xaxis_title="",
                            yaxis_title="Changes",
                            legend_title_text=""
                        )
                        st.plotly_chart(
                            fig,
                            use_container_width=True,
                            key="ev_type_bar")

                with ec2:
                    # By user
                    if "USER_NAME" in ev_df.columns:
                        top_users = ev_df.groupby(
                            "USER_NAME"
                        ).size().reset_index(
                            name="Changes"
                        ).nlargest(10,"Changes")
                        fig2 = px.bar(
                            top_users,
                            x="Changes",
                            y="USER_NAME",
                            orientation="h",
                            title="Top Users by DDL Changes",
                            height=340,
                            color="Changes",
                            color_continuous_scale=[
                                COLORS["bg_elevated"],
                                COLORS["pwc_orange"]
                            ]
                        )
                        fig2.update_layout(
                            yaxis_title="",
                            coloraxis_showscale=False
                        )
                        st.plotly_chart(
                            fig2,
                            use_container_width=True,
                            key="ev_user_bar")

                # By database
                if "DATABASE_NAME" in ev_df.columns:
                    db_ev = ev_df.groupby(
                        ["DATABASE_NAME","_ACCOUNT"]
                    ).size().reset_index(name="Changes")
                    fig3 = px.treemap(
                        db_ev,
                        path=["_ACCOUNT","DATABASE_NAME"],
                        values="Changes",
                        title="Schema Changes by Database",
                        height=350,
                        color="Changes",
                        color_continuous_scale=[
                            COLORS["bg_elevated"],
                            COLORS["pwc_orange"],
                            COLORS["red"]
                        ]
                    )
                    st.plotly_chart(
                        fig3,
                        use_container_width=True,
                        key="ev_db_tree")

        with ev_t2:
            # Hour × weekday heatmap
            if "START_TIME" in ev_df.columns:
                ev_df["HOUR"]    = (
                    ev_df["START_TIME"].dt.hour)
                ev_df["WEEKDAY"] = (
                    ev_df["START_TIME"].dt.day_name())
                hm = ev_df.groupby(
                    ["WEEKDAY","HOUR"]
                ).size().reset_index(name="Changes")
                day_order = [
                    "Monday","Tuesday","Wednesday",
                    "Thursday","Friday",
                    "Saturday","Sunday"
                ]
                pivot = hm.pivot_table(
                    index="WEEKDAY", columns="HOUR",
                    values="Changes", aggfunc="sum"
                ).reindex([
                    d for d in day_order
                    if d in hm["WEEKDAY"].unique()
                ])
                if not pivot.empty:
                    fig_hm = px.imshow(
                        pivot,
                        labels=dict(
                            x="Hour of Day",
                            y="Day",
                            color="Changes"
                        ),
                        color_continuous_scale=[
                            COLORS["bg_primary"],
                            COLORS["pwc_orange"],
                            COLORS["red"]
                        ],
                        height=340,
                        title="DDL Activity Heatmap",
                        aspect="auto"
                    )
                    fig_hm.update_layout(
                        xaxis=dict(dtick=1))
                    st.plotly_chart(
                        fig_hm,
                        use_container_width=True,
                        key="ev_heatmap")

        with ev_t3:
            # Change log
            ev_cols = [c for c in [
                "_ACCOUNT","DATABASE_NAME",
                "SCHEMA_NAME","QUERY_TYPE",
                "USER_NAME","ROLE_NAME",
                "START_TIME","EXECUTION_STATUS",
                "QUERY_TEXT","QUERY_ID"
            ] if c in ev_df.columns]

            # Color-code rows
            display_ev = ev_df[ev_cols].copy()
            st.dataframe(
                display_ev.rename(columns={
                    "_ACCOUNT":       "Account",
                    "DATABASE_NAME":  "Database",
                    "SCHEMA_NAME":    "Schema",
                    "QUERY_TYPE":     "Operation",
                    "USER_NAME":      "User",
                    "ROLE_NAME":      "Role",
                    "START_TIME":     "Time",
                    "EXECUTION_STATUS":"Status",
                    "QUERY_TEXT":     "SQL",
                    "QUERY_ID":       "Query ID",
                }),
                use_container_width=True,
                hide_index=True,
                height=550
            )

            csv_ev = ev_df.to_csv(index=False)
            st.download_button(
                "📥 Download Evolution Log",
                data=csv_ev,
                file_name=(
                    f"schema_evolution_"
                    f"{datetime.date.today()}.csv"),
                mime="text/csv",
                key="ev_dl"
            )


# ═══════════════════════════════════════════════════════════════════════════
# TAB 7 — DML ACTIVITY
# ═══════════════════════════════════════════════════════════════════════════

with tab_dml:
    section_header("DML ACTIVITY MONITOR")

    st.markdown(f"""
    <div class="info-box">
        Monitor INSERT, UPDATE, DELETE, MERGE,
        TRUNCATE and COPY operations on tables.
        Detect anomalous write patterns and
        track data modification trends.
    </div>
    """, unsafe_allow_html=True)

    dm1, dm2, dm3, dm4 = st.columns(4)
    with dm1:
        dm_acc = st.selectbox(
            "Account", connected, key="dm_acc")
    with dm2:
        dm_dbs = fetch_databases(id(manager), dm_acc)
        dm_db  = st.selectbox(
            "Database",
            dm_dbs or ["(none)"],
            key="dm_db"
        )
    with dm3:
        dm_schemas = (
            fetch_schemas(id(manager), dm_acc, dm_db)
            if dm_db != "(none)" else []
        )
        dm_schema = st.selectbox(
            "Schema",
            dm_schemas or ["(none)"],
            key="dm_schema"
        )
    with dm4:
        dm_days = st.selectbox(
            "Time Range",
            [1,7,14,30], index=1,
            format_func=lambda x: f"Last {x} days",
            key="dm_days"
        )

    if (dm_db != "(none)"
            and dm_schema != "(none)"):

        dml_df = fetch_table_dml(
            id(manager), dm_acc,
            dm_db, dm_schema, "(any)", dm_days
        )

        # Cross-env DML
        all_dml = []
        for acc2 in connected:
            xdf = fetch_table_dml(
                id(manager), acc2,
                dm_db, dm_schema,
                "(any)", dm_days
            )
            if not xdf.empty:
                all_dml.append(xdf)

        if all_dml:
            dml_all = pd.concat(
                all_dml, ignore_index=True)

            for col in ["QUERY_COUNT",
                        "ROWS_AFFECTED"]:
                if col in dml_all.columns:
                    dml_all[col] = pd.to_numeric(
                        dml_all[col],
                        errors="coerce"
                    ).fillna(0)

            if "DATE" in dml_all.columns:
                dml_all["DATE"] = pd.to_datetime(
                    dml_all["DATE"], errors="coerce")

            # DML summary
            dm_k1,dm_k2,dm_k3,dm_k4 = st.columns(4)
            dm_k1.metric(
                "Total DML Ops",
                f"{safe_int(dml_all['QUERY_COUNT'].sum()):,}"
                if "QUERY_COUNT" in dml_all.columns
                else "N/A")
            dm_k2.metric(
                "Rows Affected",
                fmt_num(safe_int(
                    dml_all["ROWS_AFFECTED"].sum()))
                if "ROWS_AFFECTED" in dml_all.columns
                else "N/A")
            dm_k3.metric(
                "DML Types",
                str(dml_all["QUERY_TYPE"].nunique())
                if "QUERY_TYPE" in dml_all.columns
                else "N/A")
            dm_k4.metric(
                "Days Tracked",
                str(dm_days))

            st.markdown(
                "<div style='height:8px'></div>",
                unsafe_allow_html=True)

            # Charts
            dml_c1, dml_c2 = st.columns(2)
            dml_colors = {
                "INSERT":       COLORS["green"],
                "UPDATE":       COLORS["pwc_gold"],
                "DELETE":       COLORS["red"],
                "MERGE":        COLORS["blue"],
                "TRUNCATE_TABLE":COLORS["yellow"],
                "COPY":         COLORS["cyan"],
            }

            with dml_c1:
                if ("DATE" in dml_all.columns
                        and "QUERY_TYPE"
                        in dml_all.columns
                        and "QUERY_COUNT"
                        in dml_all.columns):
                    fig = px.bar(
                        dml_all,
                        x="DATE",
                        y="QUERY_COUNT",
                        color="QUERY_TYPE",
                        color_discrete_map=dml_colors,
                        title="DML Operations per Day",
                        height=340,
                        barmode="stack"
                    )
                    fig.update_layout(
                        xaxis_title="",
                        yaxis_title="Operations",
                        legend_title_text=""
                    )
                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                        key="dml_ops_bar")

            with dml_c2:
                if "QUERY_TYPE" in dml_all.columns:
                    dml_type = dml_all.groupby(
                        "QUERY_TYPE"
                    )["QUERY_COUNT"].sum(
                    ).reset_index()
                    fig2 = go.Figure(go.Pie(
                        labels=dml_type["QUERY_TYPE"],
                        values=dml_type["QUERY_COUNT"],
                        hole=0.55,
                        marker_colors=[
                            dml_colors.get(
                                t, COLORS["text_muted"])
                            for t in
                            dml_type["QUERY_TYPE"]
                        ],
                        textinfo="label+percent"
                    ))
                    fig2.update_layout(
                        title="DML Type Distribution",
                        height=340,
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(
                            color=COLORS["text_secondary"])
                    )
                    st.plotly_chart(
                        fig2,
                        use_container_width=True,
                        key="dml_type_pie")

            # Rows affected trend
            if ("DATE" in dml_all.columns
                    and "ROWS_AFFECTED"
                    in dml_all.columns):
                rows_trend = dml_all.groupby(
                    "DATE"
                )["ROWS_AFFECTED"].sum().reset_index()
                fig3 = px.area(
                    rows_trend,
                    x="DATE",
                    y="ROWS_AFFECTED",
                    title="Rows Affected per Day",
                    height=280,
                    color_discrete_sequence=[
                        COLORS["pwc_orange"]]
                )
                fig3.update_traces(
                    line=dict(
                        width=2,
                        color=COLORS["pwc_orange"]))
                fig3.update_layout(
                    xaxis_title="",
                    yaxis_title="Rows"
                )
                st.plotly_chart(
                    fig3,
                    use_container_width=True,
                    key="dml_rows_trend")

            # Raw data
            st.dataframe(
                dml_all.rename(columns={
                    "_ACCOUNT":     "Account",
                    "QUERY_TYPE":   "Operation",
                    "DATE":         "Date",
                    "QUERY_COUNT":  "Count",
                    "ROWS_AFFECTED":"Rows Affected",
                }),
                use_container_width=True,
                hide_index=True,
                height=400
            )
        else:
            st.info(
                "No DML activity found. "
                "Ensure ACCOUNT_USAGE access.")
    else:
        st.info(
            "Select a Database and Schema "
            "to view DML activity.")

# ─── Footer ───────────────────────────────────────────────────────────────────

st.markdown(f"""
<div style="text-align:center; padding:28px 0 10px;
     border-top:1px solid {COLORS['border']};
     margin-top:32px;">
    <span style="font-size:0.65rem;
          color:{COLORS['text_dim']};">
        📋 Tables & Views &nbsp;·&nbsp;
        <span style="color:{COLORS['pwc_orange']};
              font-weight:700;">
              Powered By PwC Data & AI</span>
        &nbsp;·&nbsp; {len(connected)} environment(s)
    </span>
</div>
""", unsafe_allow_html=True)