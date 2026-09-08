# pages/sql_executor.py

"""
SQL Executor — Run SQL queries against any connected Snowflake account
with full context control (Database, Schema, Warehouse, Role).
"""

import streamlit as st
import pandas as pd
import time
from datetime import datetime
from typing import Optional, List, Dict

from snowflake_connector import SnowflakeConnectionManager
from config import get_account_configs, AccountConfig


# ══════════════════════════════════════════════════════════════════════════════
# INITIALISE
# ══════════════════════════════════════════════════════════════════════════════

conn_mgr = SnowflakeConnectionManager()


def init_sql_executor_state():
    """Initialise all session-state keys used by this page."""
    defaults = {
        # Context
        "sqlex_account":   None,
        "sqlex_database":  None,
        "sqlex_schema":    None,
        "sqlex_warehouse": None,
        "sqlex_role":      None,

        # Metadata lists
        "sqlex_databases":  [],
        "sqlex_schemas":    [],
        "sqlex_warehouses": [],
        "sqlex_roles":      [],

        # Editor
        "sqlex_sql": "-- Write your SQL here\nSELECT CURRENT_TIMESTAMP();",
        "sqlex_limit":   1000,
        "sqlex_timeout": 300,
        "sqlex_tag":     "",

        # Result
        "sqlex_result": None,

        # History  (max 50)
        "sqlex_history": [],

        # Saved queries
        "sqlex_saved":        [],
        "sqlex_show_library": False,

        # PROD guard
        "sqlex_prod_ok": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _env_for(account_name: str) -> str:
    """
    Derive a short environment label from the account name.
    Adjust these rules to match your naming convention.
    """
    n = account_name.lower()
    if "prod" in n or "production" in n:
        return "PROD"
    if "dev" in n or "development" in n:
        return "DEV"
    if "uat" in n:
        return "UAT"
    if "stag" in n:
        return "STAGING"
    if "test" in n:
        return "TEST"
    return "OTHER"


def _env_badge(env: str) -> str:
    return {"PROD": "🔴", "UAT": "🟡", "DEV": "🟢",
            "STAGING": "🟠", "TEST": "🔵"}.get(env, "⚪")


def _env_color(env: str) -> str:
    return {"PROD": "#ff4d4f", "UAT": "#faad14", "DEV": "#52c41a",
            "STAGING": "#fa8c16", "TEST": "#1890ff"}.get(env, "#888888")


def _wh_icon(state: str) -> str:
    return {"STARTED": "🟢", "SUSPENDED": "🔴",
            "RESIZING": "🟡"}.get(state.upper(), "⚪")


def _elapsed_str(ms: float) -> str:
    return f"{ms:.0f} ms" if ms < 1000 else f"{ms / 1000:.2f} s"


def _get_config_for(account_name: str) -> Optional[AccountConfig]:
    """Look up the AccountConfig for a connected account."""
    for cfg in get_account_configs():
        if cfg.name == account_name:
            return cfg
    return None


# ── Metadata fetchers (use the existing live connection) ──────────────────────

def _fetch(account_name: str, sql: str) -> List:
    """Run a SHOW command on an existing connection and return col-1 values."""
    conn = conn_mgr.get_connection(account_name)
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cur.close()
        return [r[1] if len(r) > 1 else r[0] for r in rows]
    except Exception:
        return []


def _fetch_warehouses(account_name: str) -> List[Dict]:
    conn = conn_mgr.get_connection(account_name)
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        cur.execute("SHOW WAREHOUSES")
        rows = cur.fetchall()
        cur.close()
        return [{"name": r[0], "state": r[1], "size": r[3]} for r in rows]
    except Exception:
        return []


def load_account_meta(account_name: str):
    """Populate databases, warehouses, roles for the chosen account."""
    with st.spinner("Loading account metadata…"):
        st.session_state.sqlex_databases  = _fetch(account_name, "SHOW DATABASES")
        st.session_state.sqlex_warehouses = _fetch_warehouses(account_name)
        st.session_state.sqlex_roles      = _fetch(account_name, "SHOW ROLES")


def load_schemas(account_name: str, database: str):
    with st.spinner(f"Loading schemas for {database}…"):
        st.session_state.sqlex_schemas = _fetch(
            account_name,
            f'SHOW SCHEMAS IN DATABASE "{database}"'
        )


def reset_context(level: str):
    if level == "account":
        for k in ("sqlex_database", "sqlex_schema",
                   "sqlex_warehouse", "sqlex_role"):
            st.session_state[k] = None
        for k in ("sqlex_databases", "sqlex_schemas",
                   "sqlex_warehouses", "sqlex_roles"):
            st.session_state[k] = []
    elif level == "database":
        st.session_state.sqlex_schema = None
        st.session_state.sqlex_schemas = []


# ── History ───────────────────────────────────────────────────────────────────

def _add_history(account: str, sql: str, result: dict):
    rec = {
        "ts":        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "account":   account,
        "env":       _env_for(account),
        "database":  st.session_state.sqlex_database  or "—",
        "schema":    st.session_state.sqlex_schema    or "—",
        "warehouse": st.session_state.sqlex_warehouse or "—",
        "role":      st.session_state.sqlex_role      or "—",
        "sql":       sql,
        "status":    result["status"],
        "elapsed":   result["elapsed_ms"],
        "rows":      result["row_count"],
        "qid":       result.get("query_id") or "—",
        "error":     result.get("error")    or "—",
    }
    st.session_state.sqlex_history = (
        [rec] + st.session_state.sqlex_history
    )[:50]


# ══════════════════════════════════════════════════════════════════════════════
# QUERY EXECUTION  (uses the existing connection, adds context USE commands)
# ══════════════════════════════════════════════════════════════════════════════

def run_query(account_name: str, sql: str) -> dict:
    """
    Execute SQL on the already-connected account.
    Applies the selected Database / Schema / Warehouse / Role via USE commands
    before running the user's query.
    """
    conn = conn_mgr.get_connection(account_name)
    if conn is None:
        return {
            "status": "failed", "query_id": None,
            "dataframe": pd.DataFrame(), "row_count": 0,
            "elapsed_ms": 0, "error": f"Not connected to {account_name}",
            "sql_executed": sql,
        }

    start = time.time()
    try:
        cur = conn.cursor()

        # ── Apply context ─────────────────────────────────────────────────
        if st.session_state.sqlex_role:
            cur.execute(f'USE ROLE "{st.session_state.sqlex_role}"')
        if st.session_state.sqlex_warehouse:
            cur.execute(f'USE WAREHOUSE "{st.session_state.sqlex_warehouse}"')
        if st.session_state.sqlex_database:
            cur.execute(f'USE DATABASE "{st.session_state.sqlex_database}"')
        if st.session_state.sqlex_schema:
            cur.execute(f'USE SCHEMA "{st.session_state.sqlex_schema}"')

        # ── Query tag / timeout ───────────────────────────────────────────
        if st.session_state.sqlex_tag:
            cur.execute(
                f"ALTER SESSION SET QUERY_TAG = '{st.session_state.sqlex_tag}'"
            )
        cur.execute(
            f"ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = "
            f"{st.session_state.sqlex_timeout}"
        )

        # ── Add LIMIT to SELECT if not already present ────────────────────
        exec_sql = sql.strip()
        limit    = st.session_state.sqlex_limit
        if (exec_sql.upper().startswith("SELECT")
                and limit > 0
                and "LIMIT" not in exec_sql.upper()):
            exec_sql = f"{exec_sql}\nLIMIT {limit}"

        # ── Execute ───────────────────────────────────────────────────────
        cur.execute(exec_sql)
        query_id = cur.sfqid
        elapsed  = round((time.time() - start) * 1000, 2)

        if cur.description:
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            df   = pd.DataFrame(rows, columns=cols)
        else:
            df = pd.DataFrame()

        cur.close()

        return {
            "status":       "success",
            "query_id":     query_id,
            "dataframe":    df,
            "row_count":    len(df),
            "elapsed_ms":   elapsed,
            "error":        None,
            "sql_executed": exec_sql,
        }

    except Exception as e:
        elapsed = round((time.time() - start) * 1000, 2)
        return {
            "status":       "failed",
            "query_id":     None,
            "dataframe":    pd.DataFrame(),
            "row_count":    0,
            "elapsed_ms":   elapsed,
            "error":        str(e),
            "sql_executed": sql,
        }


# ══════════════════════════════════════════════════════════════════════════════
# UI — PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════════

def render_header():
    st.markdown("## 🔷 SQL Executor")
    st.caption(
        "Execute SQL queries against any connected Snowflake account "
        "with full context control."
    )
    st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# UI — PROD WARNING
# ══════════════════════════════════════════════════════════════════════════════

def render_prod_warning():
    acct = st.session_state.sqlex_account
    if acct and _env_for(acct) == "PROD":
        st.error(
            "🚨 **WARNING — You are connected to a PRODUCTION account.** "
            "Review every query carefully before execution.",
            icon="⚠️",
        )


# ══════════════════════════════════════════════════════════════════════════════
# UI — CONTEXT PANEL
# ══════════════════════════════════════════════════════════════════════════════

def render_context_panel():
    st.markdown("### ⚙️ Execution Context")

    connected = conn_mgr.get_connected_accounts()

    if not connected:
        st.warning(
            "No accounts are connected. Go to the main page and "
            "connect to at least one account first."
        )
        return

    # Build label → name map
    label_map = {
        f"{_env_badge(_env_for(n))}  {n}  [{_env_for(n)}]": n
        for n in connected
    }
    labels = ["— Select Account —"] + list(label_map.keys())

    # Current index
    cur_label = next(
        (l for l, n in label_map.items()
         if n == st.session_state.sqlex_account), None
    )
    cur_idx = labels.index(cur_label) if cur_label else 0

    c1, c2, c3, c4, c5 = st.columns(5)

    # ── Account ───────────────────────────────────────────────────────────
    with c1:
        st.markdown("**Account**")
        pick = st.selectbox("Account", labels, index=cur_idx,
                            key="sqlex_w_acct", label_visibility="collapsed")

        if pick != "— Select Account —":
            name = label_map[pick]
            if name != st.session_state.sqlex_account:
                env = _env_for(name)
                if env == "PROD" and not st.session_state.sqlex_prod_ok:
                    st.warning("⚠️ You selected a **PRODUCTION** account.")
                    if st.checkbox("I confirm I want to connect to PROD",
                                   key="sqlex_prod_chk"):
                        st.session_state.sqlex_prod_ok = True
                        st.session_state.sqlex_account = name
                        reset_context("account")
                        load_account_meta(name)
                        st.rerun()
                else:
                    st.session_state.sqlex_prod_ok = False
                    st.session_state.sqlex_account = name
                    reset_context("account")
                    load_account_meta(name)
                    st.rerun()

    # ── Database ──────────────────────────────────────────────────────────
    with c2:
        st.markdown("**Database**")
        db_opts = ["— Select Database —"] + st.session_state.sqlex_databases
        db_idx  = (db_opts.index(st.session_state.sqlex_database)
                   if st.session_state.sqlex_database in db_opts else 0)

        db_pick = st.selectbox("Database", db_opts, index=db_idx,
                               key="sqlex_w_db", label_visibility="collapsed",
                               disabled=not st.session_state.sqlex_account)

        if db_pick != "— Select Database —":
            if db_pick != st.session_state.sqlex_database:
                st.session_state.sqlex_database = db_pick
                reset_context("database")
                load_schemas(st.session_state.sqlex_account, db_pick)
                st.rerun()

    # ── Schema ────────────────────────────────────────────────────────────
    with c3:
        st.markdown("**Schema**")
        sc_opts = ["— Select Schema —"] + st.session_state.sqlex_schemas
        sc_idx  = (sc_opts.index(st.session_state.sqlex_schema)
                   if st.session_state.sqlex_schema in sc_opts else 0)

        sc_pick = st.selectbox("Schema", sc_opts, index=sc_idx,
                               key="sqlex_w_sc", label_visibility="collapsed",
                               disabled=not st.session_state.sqlex_database)

        if sc_pick != "— Select Schema —":
            st.session_state.sqlex_schema = sc_pick

    # ── Warehouse ─────────────────────────────────────────────────────────
    with c4:
        st.markdown("**Warehouse**")
        wh_label_map = {
            f"{_wh_icon(w['state'])}  {w['name']}  ({w['size']})": w["name"]
            for w in st.session_state.sqlex_warehouses
        }
        wh_opts = ["— Select Warehouse —"] + list(wh_label_map.keys())
        cur_wh_label = next(
            (l for l, n in wh_label_map.items()
             if n == st.session_state.sqlex_warehouse), None
        )
        wh_idx = wh_opts.index(cur_wh_label) if cur_wh_label else 0

        wh_pick = st.selectbox("Warehouse", wh_opts, index=wh_idx,
                               key="sqlex_w_wh", label_visibility="collapsed",
                               disabled=not st.session_state.sqlex_account)

        if wh_pick != "— Select Warehouse —":
            st.session_state.sqlex_warehouse = wh_label_map[wh_pick]

    # ── Role ──────────────────────────────────────────────────────────────
    with c5:
        st.markdown("**Role**")
        r_opts = ["— Select Role —"] + st.session_state.sqlex_roles
        r_idx  = (r_opts.index(st.session_state.sqlex_role)
                  if st.session_state.sqlex_role in r_opts else 0)

        r_pick = st.selectbox("Role", r_opts, index=r_idx,
                              key="sqlex_w_rl", label_visibility="collapsed",
                              disabled=not st.session_state.sqlex_account)

        if r_pick != "— Select Role —":
            if r_pick != st.session_state.sqlex_role:
                st.session_state.sqlex_role = r_pick
                if st.session_state.sqlex_account:
                    load_account_meta(st.session_state.sqlex_account)
                    st.rerun()

    # ── Summary Bar ───────────────────────────────────────────────────────
    if st.session_state.sqlex_account:
        env   = _env_for(st.session_state.sqlex_account)
        badge = _env_badge(env)
        color = _env_color(env)

        parts = [f"{badge} <b>{st.session_state.sqlex_account}</b> "
                 f"<code>[{env}]</code>"]
        if st.session_state.sqlex_database:
            parts.append(
                f"🗄️ <b>DB:</b> <code>{st.session_state.sqlex_database}</code>")
        if st.session_state.sqlex_schema:
            parts.append(
                f"📂 <b>Schema:</b> <code>{st.session_state.sqlex_schema}</code>")
        if st.session_state.sqlex_warehouse:
            parts.append(
                f"⚡ <b>WH:</b> <code>{st.session_state.sqlex_warehouse}</code>")
        if st.session_state.sqlex_role:
            parts.append(
                f"👤 <b>Role:</b> <code>{st.session_state.sqlex_role}</code>")

        st.markdown("---")
        st.markdown(
            f'<div style="border-left:5px solid {color};padding:10px 18px;'
            f'background:#1a1a2e;border-radius:4px;font-size:14px;'
            f'line-height:1.8;color:#e0e0e0">'
            f'{"&nbsp;&nbsp;|&nbsp;&nbsp;".join(parts)}</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# UI — SQL EDITOR
# ══════════════════════════════════════════════════════════════════════════════

LIMIT_OPTIONS   = [100, 500, 1000, 5000, 10000]
TIMEOUT_OPTIONS = {
    "30 seconds": 30, "1 minute": 60, "5 minutes": 300,
    "15 minutes": 900, "30 minutes": 1800,
}


def render_editor() -> bool:
    """Render editor + settings. Returns True when Run is clicked."""
    st.markdown("### 📝 SQL Editor")

    # ── Settings row ──────────────────────────────────────────────────────
    s1, s2, s3 = st.columns(3)

    with s1:
        st.session_state.sqlex_limit = st.selectbox(
            "Row Limit", LIMIT_OPTIONS,
            index=LIMIT_OPTIONS.index(st.session_state.sqlex_limit)
                  if st.session_state.sqlex_limit in LIMIT_OPTIONS else 2,
            key="sqlex_w_lim",
        )

    with s2:
        t_label = st.selectbox(
            "Query Timeout", list(TIMEOUT_OPTIONS.keys()),
            index=list(TIMEOUT_OPTIONS.values()).index(
                st.session_state.sqlex_timeout)
                  if st.session_state.sqlex_timeout in TIMEOUT_OPTIONS.values()
                  else 2,
            key="sqlex_w_to",
        )
        st.session_state.sqlex_timeout = TIMEOUT_OPTIONS[t_label]

    with s3:
        st.session_state.sqlex_tag = st.text_input(
            "Query Tag (optional)",
            value=st.session_state.sqlex_tag,
            placeholder="e.g. monitoring, etl-debug",
            key="sqlex_w_tag",
        )

    # ── Text area ─────────────────────────────────────────────────────────
    sql_input = st.text_area(
        "SQL", value=st.session_state.sqlex_sql, height=280,
        placeholder="-- Type your SQL here…",
        key="sqlex_w_sql", label_visibility="collapsed",
    )
    st.session_state.sqlex_sql = sql_input

    # ── Buttons ───────────────────────────────────────────────────────────
    b1, b2, b3, b4, _ = st.columns([1.2, 1, 1, 1.4, 4])

    with b1:
        run = st.button(
            "▶️ Run Query", type="primary", use_container_width=True,
            disabled=(not st.session_state.sqlex_account
                      or not st.session_state.sqlex_sql.strip()),
            key="sqlex_run",
        )
    with b2:
        if st.button("🗑️ Clear", use_container_width=True, key="sqlex_clr"):
            st.session_state.sqlex_sql    = ""
            st.session_state.sqlex_result = None
            st.rerun()
    with b3:
        save = st.button(
            "💾 Save", use_container_width=True,
            disabled=not st.session_state.sqlex_sql.strip(),
            key="sqlex_sav",
        )
    with b4:
        if st.button("📂 Library", use_container_width=True,
                      key="sqlex_lib_toggle"):
            st.session_state.sqlex_show_library = (
                not st.session_state.sqlex_show_library
            )
            st.rerun()

    if save and st.session_state.sqlex_sql.strip():
        _render_save_form()

    return run


# ══════════════════════════════════════════════════════════════════════════════
# UI — SAVE / LIBRARY
# ══════════════════════════════════════════════════════════════════════════════

def _render_save_form():
    with st.expander("💾 Save Query", expanded=True):
        name = st.text_input("Query Name *", key="sqlex_sv_name",
                             placeholder="Daily Revenue Report")
        desc = st.text_area("Description", key="sqlex_sv_desc", height=60)
        tags = st.text_input("Tags (comma separated)", key="sqlex_sv_tags",
                             placeholder="monitoring, cost")
        if st.button("✅ Confirm Save", key="sqlex_sv_ok"):
            if not name.strip():
                st.error("Please enter a name.")
            else:
                st.session_state.sqlex_saved.append({
                    "name": name.strip(),
                    "desc": desc.strip(),
                    "sql":  st.session_state.sqlex_sql,
                    "tags": [t.strip() for t in tags.split(",") if t.strip()],
                    "ts":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                st.success(f"✅ Saved **{name.strip()}**")


def render_library():
    if not st.session_state.sqlex_show_library:
        return
    st.markdown("### 📂 Query Library")
    if not st.session_state.sqlex_saved:
        st.info("No saved queries yet.")
        return

    for i, q in enumerate(st.session_state.sqlex_saved):
        with st.expander(f"📄 {q['name']}  ·  {q['ts']}", expanded=False):
            if q["desc"]:
                st.markdown(f"**Description:** {q['desc']}")
            if q["tags"]:
                st.markdown("**Tags:** " +
                            " ".join(f"`{t}`" for t in q["tags"]))
            st.code(q["sql"], language="sql")

            lc, dc, _ = st.columns([1, 1, 6])
            with lc:
                if st.button("📥 Load", key=f"sqlex_ld_{i}"):
                    st.session_state.sqlex_sql = q["sql"]
                    st.session_state.sqlex_show_library = False
                    st.rerun()
            with dc:
                if st.button("🗑️ Del", key=f"sqlex_dl_{i}"):
                    st.session_state.sqlex_saved.pop(i)
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# EXECUTE
# ══════════════════════════════════════════════════════════════════════════════

def execute(run_clicked: bool):
    if not run_clicked:
        return

    sql  = st.session_state.sqlex_sql.strip()
    acct = st.session_state.sqlex_account

    if not sql:
        st.warning("Enter a SQL query.")
        return
    if not acct:
        st.error("Select an account first.")
        return

    env = _env_for(acct)
    with st.spinner(f"Executing on {acct} [{env}]…"):
        result = run_query(acct, sql)

    st.session_state.sqlex_result = result
    _add_history(acct, sql, result)


# ══════════════════════════════════════════════════════════════════════════════
# UI — RESULTS
# ══════════════════════════════════════════════════════════════════════════════

def render_results():
    st.markdown("### 📊 Results")

    result  = st.session_state.sqlex_result
    history = st.session_state.sqlex_history

    t_res, t_msg, t_hist = st.tabs([
        "📋 Results",
        "💬 Messages",
        f"🕐 History ({len(history)})",
    ])

    # ── Results ───────────────────────────────────────────────────────────
    with t_res:
        if result is None:
            st.info("▶️ Run a query to see results here.")
            return

        if result["status"] == "failed":
            st.error(f"❌ **Query Failed**\n\n```\n{result['error']}\n```")
            return

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Rows Returned", f"{result['row_count']:,}")
        with m2:
            st.metric("Elapsed", _elapsed_str(result["elapsed_ms"]))
        with m3:
            st.metric("Status", "✅ Success")
        with m4:
            qid = str(result.get("query_id") or "—")
            st.metric("Query ID", qid[:18] + "…" if len(qid) > 18 else qid)

        st.divider()

        df = result["dataframe"]
        if not df.empty:
            e1, e2, _ = st.columns([1, 1, 6])
            with e1:
                st.download_button(
                    "⬇️ CSV", df.to_csv(index=False),
                    file_name=f"results_{datetime.now():%Y%m%d_%H%M%S}.csv",
                    mime="text/csv", key="sqlex_dl_csv",
                )
            with e2:
                st.download_button(
                    "⬇️ JSON",
                    df.to_json(orient="records", indent=2),
                    file_name=f"results_{datetime.now():%Y%m%d_%H%M%S}.json",
                    mime="application/json", key="sqlex_dl_json",
                )

            st.dataframe(df, use_container_width=True, height=450)
        else:
            st.success("✅ Executed successfully — no rows returned (DDL/DML).")

    # ── Messages ──────────────────────────────────────────────────────────
    with t_msg:
        if result is None:
            st.info("No messages.")
        elif result["status"] == "success":
            st.success(
                f"✅ **Query completed**\n\n"
                f"- Rows: **{result['row_count']:,}**\n"
                f"- Elapsed: **{_elapsed_str(result['elapsed_ms'])}**\n"
                f"- Query ID: `{result.get('query_id', '—')}`"
            )
            st.markdown("**Executed SQL:**")
            st.code(result.get("sql_executed", ""), language="sql")
        else:
            st.error(f"❌ **Failed**\n\n```\n{result['error']}\n```")

    # ── History ───────────────────────────────────────────────────────────
    with t_hist:
        render_history()


# ══════════════════════════════════════════════════════════════════════════════
# UI — HISTORY
# ══════════════════════════════════════════════════════════════════════════════

def render_history():
    history = st.session_state.sqlex_history
    if not history:
        st.info("No history yet.")
        return

    hc, _ = st.columns([1, 7])
    with hc:
        if st.button("🗑️ Clear History", key="sqlex_clr_hist"):
            st.session_state.sqlex_history = []
            st.rerun()

    st.markdown("---")

    for i, r in enumerate(history):
        icon = "✅" if r["status"] == "success" else "❌"
        with st.expander(
            f"{icon}  {r['ts']}  |  "
            f"{_env_badge(r['env'])} {r['env']}  |  "
            f"⏱ {_elapsed_str(r['elapsed'])}  |  "
            f"Rows: {r['rows']:,}",
            expanded=False,
        ):
            x1, x2, x3, x4 = st.columns(4)
            with x1: st.markdown(f"**Account:** `{r['account']}`")
            with x2: st.markdown(f"**Database:** `{r['database']}`")
            with x3: st.markdown(f"**Warehouse:** `{r['warehouse']}`")
            with x4: st.markdown(f"**Role:** `{r['role']}`")

            st.markdown(f"**Query ID:** `{r['qid']}`")
            st.code(r["sql"], language="sql")

            if r["status"] == "failed" and r["error"] != "—":
                st.error(f"**Error:** {r['error']}")

            if st.button("📥 Load into Editor", key=f"sqlex_rlh_{i}"):
                st.session_state.sqlex_sql = r["sql"]
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    init_sql_executor_state()

    render_header()
    render_prod_warning()

    with st.container():
        render_context_panel()

    st.divider()

    with st.container():
        run_clicked = render_editor()

    render_library()
    st.divider()

    execute(run_clicked)

    with st.container():
        render_results()


# Works both standalone and when called from your main app.py
if __name__ == "__main__":
    st.set_page_config(
        page_title="SQL Executor | Snowflake Monitor",
        page_icon="🔷", layout="wide",
    )
    main()