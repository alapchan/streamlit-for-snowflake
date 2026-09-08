"""
🏗️ Object Creator — Create any Snowflake object
   through guided forms with live SQL preview.
"""

import streamlit as st
import time
import pandas as pd

from snowflake_connector import SnowflakeConnectionManager
from theme import (
    inject_css, COLORS, get_env_color,
    pwc_header, section_header,
)

# ─── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Object Creator · PwC",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# ─── Safe color lookup ────────────────────────────────────────────────────────

def c(key: str, fallback: str = "#888888") -> str:
    return COLORS.get(key, fallback)

# ─── Safe HTML builders ───────────────────────────────────────────────────────

def _kpi(icon, value, label, color):
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
        f'</div>'
    )


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
        f'</div>'
    )


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
        f'</div>'
    )


def _sql_block(sql: str) -> str:
    return (
        f'<div style="background:{c("bg_secondary","#0d1117")};'
        f'border:1px solid {c("border")};'
        f'border-left:3px solid {c("pwc_orange")};'
        f'border-radius:0 8px 8px 0;'
        f'padding:16px 18px;'
        f'font-family:JetBrains Mono,monospace;'
        f'font-size:0.78rem;'
        f'color:{c("text_secondary")};'
        f'line-height:1.8;white-space:pre-wrap;'
        f'word-break:break-all;margin:12px 0;">'
        f'{sql}'
        f'</div>'
    )


def _section_card(title: str, icon: str,
                   desc: str, color: str) -> str:
    return (
        f'<div style="background:linear-gradient('
        f'180deg,rgba(255,255,255,0.02),'
        f'rgba(255,255,255,0.00)),rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-left:4px solid {color};'
        f'border-radius:14px;padding:16px 18px;'
        f'margin-bottom:12px;">'
        f'<div style="font-size:1rem;font-weight:800;'
        f'color:{color};margin-bottom:4px;">'
        f'{icon} {title}</div>'
        f'<div style="font-size:0.76rem;'
        f'color:{c("text_muted")};line-height:1.5;">'
        f'{desc}</div>'
        f'</div>'
    )


def _success_banner(text: str) -> str:
    return (
        f'<div style="background:{c("green")}15;'
        f'border:1px solid {c("green")}33;'
        f'border-left:4px solid {c("green")};'
        f'border-radius:14px;padding:14px 18px;'
        f'margin-top:12px;">'
        f'<span style="color:{c("green")};'
        f'font-weight:700;font-size:0.88rem;">'
        f'✅ {text}</span>'
        f'</div>'
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

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


def run_query(account: str, sql: str) -> pd.DataFrame:
    return manager.execute_query(account, sql)


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
            f'SHOW SCHEMAS IN DATABASE "{db}"')
        if df is not None and "name" in df.columns:
            return [s for s in df["name"].tolist()
                    if s != "INFORMATION_SCHEMA"]
    except Exception:
        pass
    return []


@st.cache_data(ttl=60, show_spinner=False)
def fetch_warehouses(_mid, account):
    try:
        df = run_query(account, "SHOW WAREHOUSES")
        if df is not None and "name" in df.columns:
            return df["name"].tolist()
    except Exception:
        pass
    return []


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
def fetch_integrations(_mid, account):
    try:
        df = run_query(account, "SHOW INTEGRATIONS")
        if df is not None and "name" in df.columns:
            return df["name"].tolist()
    except Exception:
        pass
    return []


@st.cache_data(ttl=60, show_spinner=False)
def fetch_stages(_mid, account):
    try:
        df = run_query(account, "SHOW STAGES IN ACCOUNT")
        if df is not None and "name" in df.columns:
            return df["name"].tolist()
    except Exception:
        pass
    return []


def execute_with_status(account, sql, label):
    """Run SQL with a status spinner and return ok, msg."""
    with st.status(f"Creating {label}…",
                    expanded=True) as s:
        st.write(f"🔍 Validating config…")
        time.sleep(0.3)
        st.write(f"⚙️ Executing SQL…")
        ok, result = run_statement(account, sql)
        s.update(
            label=(f"✅ {label} created!"
                   if ok else f"❌ Failed"),
            state="complete" if ok else "error",
            expanded=False)
    return ok, result


# ─── Object catalogue ─────────────────────────────────────────────────────────

OBJECT_GROUPS = {
    "☁️ Cloud & Integration": [
        "Storage Integration",
        "API Integration",
        "Notification Integration",
        "Security Integration",
    ],
    "📦 Data Storage": [
        "Database",
        "Schema",
        "Table",
        "Transient Table",
        "External Table",
        "Dynamic Table",
        "View",
        "Materialized View",
        "Sequence",
        "Stream",
    ],
    "📁 Staging & File Handling": [
        "Internal Stage",
        "External Stage",
        "File Format",
        "Pipe (Snowpipe)",
    ],
    "⚙️ Compute": [
        "Warehouse",
        "Resource Monitor",
        "Task",
    ],
    "🔐 Access Control": [
        "Role",
        "Row Access Policy",
        "Masking Policy",
        "Tag",
        "Network Policy",
    ],
    "🧠 Code & Logic": [
        "Stored Procedure (JavaScript)",
        "Stored Procedure (Python)",
        "UDF (JavaScript)",
        "UDF (Python)",
        "UDF (SQL)",
        "Snowpark Container Service",
    ],
    "🔗 Data Sharing": [
        "Share",
        "Failsafe / Clone",
    ],
    "📊 Governance": [
        "Classification Policy",
        "Aggregation Policy",
        "Projection Policy",
    ],
}

ALL_OBJECTS = [obj
               for grp in OBJECT_GROUPS.values()
               for obj in grp]

# ─── Manager ──────────────────────────────────────────────────────────────────

manager   = SnowflakeConnectionManager()
connected = manager.get_connected_accounts()

# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        f'<div style="padding:20px 16px 12px;'
        f'border-bottom:1px solid {c("border")};'
        f'margin-bottom:12px;">'
        f'<div style="font-size:1rem;font-weight:800;'
        f'color:{c("text_primary")};">🏗️ Object Creator</div>'
        f'<div style="font-size:0.56rem;'
        f'color:{c("pwc_orange")};font-weight:800;'
        f'text-transform:uppercase;letter-spacing:0.18em;">'
        f'PwC Data &amp; AI</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Connected accounts
    for acc in connected:
        color_acc = get_env_color(acc)
        st.markdown(
            f'<div style="display:flex;align-items:center;'
            f'gap:8px;padding:6px 10px;border-radius:10px;'
            f'margin-bottom:4px;">'
            f'<div style="width:7px;height:7px;'
            f'border-radius:50%;background:{color_acc};'
            f'box-shadow:0 0 6px {color_acc};'
            f'flex-shrink:0;"></div>'
            f'<span style="font-size:0.8rem;font-weight:600;'
            f'color:{color_acc};">{acc}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")

    # ── Object selector ───────────────────────────────────
    st.markdown(
        f'<div style="font-size:0.62rem;font-weight:800;'
        f'text-transform:uppercase;letter-spacing:0.14em;'
        f'color:{c("text_muted")};margin-bottom:8px;">'
        f'Select Object Type</div>',
        unsafe_allow_html=True
    )

    # Group selector
    selected_group = st.selectbox(
        "Category",
        list(OBJECT_GROUPS.keys()),
        key="obj_group",
        label_visibility="collapsed"
    )

    # Object selector within group
    selected_object = st.selectbox(
        "Object",
        OBJECT_GROUPS[selected_group],
        key="obj_type",
        label_visibility="collapsed"
    )

    st.markdown("---")

    # Account selector
    st.markdown(
        f'<div style="font-size:0.62rem;font-weight:800;'
        f'text-transform:uppercase;letter-spacing:0.14em;'
        f'color:{c("text_muted")};margin-bottom:6px;">'
        f'Target Environment</div>',
        unsafe_allow_html=True
    )
    if connected:
        target_account = st.selectbox(
            "Account",
            connected,
            key="target_account",
            label_visibility="collapsed"
        )
    else:
        st.warning("No accounts connected.")
        target_account = None

    st.markdown("---")

    if st.button("🔄 Refresh",
                  use_container_width=True,
                  key="oc_refresh"):
        st.cache_data.clear()
        st.rerun()

# ─── Header ───────────────────────────────────────────────────────────────────

pwc_header(
    "Object Creator",
    subtitle="Guided forms to create any Snowflake object "
             "with live SQL preview and one-click execution"
)

if not connected or not target_account:
    st.markdown(
        _info_box(
            "🔌 Connect at least one Snowflake account "
            "to start creating objects.",
            accent=c("pwc_orange")
        ),
        unsafe_allow_html=True
    )
    st.stop()

# ── Object type badge ─────────────────────────────────────────────────────────

env_color = get_env_color(target_account)

st.markdown(
    f'<div style="display:flex;align-items:center;'
    f'gap:12px;margin-bottom:18px;">'
    f'<div style="font-size:1.3rem;">'
    f'{selected_group.split()[0]}</div>'
    f'<div>'
    f'<div style="font-size:1rem;font-weight:800;'
    f'color:{c("text_primary")};">{selected_object}</div>'
    f'<div style="font-size:0.7rem;color:{c("text_muted")};">'
    f'Target: <span style="color:{env_color};font-weight:700;">'
    f'{target_account}</span></div>'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True
)

# ═══════════════════════════════════════════════════════
# OBJECT FORMS
# ═══════════════════════════════════════════════════════

# ── Helpers used by multiple forms ───────────────────────────────────────────

def _db_schema_selectors(key_prefix):
    """Returns (db, schema) selectboxes."""
    dbs = fetch_databases(id(manager), target_account)
    c1, c2 = st.columns(2)
    with c1:
        db = st.selectbox("Database *",
                           dbs or ["(none)"],
                           key=f"{key_prefix}_db")
    with c2:
        schemas = (fetch_schemas(id(manager),
                                  target_account, db)
                   if db and db != "(none)" else [])
        schema = st.selectbox("Schema *",
                               schemas or ["(none)"],
                               key=f"{key_prefix}_sc")
    return db, schema


def _or_replace_if_not_exists(key_prefix):
    r1, r2 = st.columns(2)
    with r1:
        replace = st.checkbox("OR REPLACE",
                               value=False,
                               key=f"{key_prefix}_replace")
    with r2:
        if_not = st.checkbox("IF NOT EXISTS",
                              value=True,
                              key=f"{key_prefix}_ifnot")
    return replace, if_not


def _comment_input(key_prefix):
    return st.text_input(
        "Comment (optional)",
        placeholder="Purpose of this object…",
        key=f"{key_prefix}_comment"
    )


def _build_comment(comment):
    return f"\nCOMMENT = '{comment}'" if comment else ""


def _execute_button(key, label, sql, account):
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"▶️ Create {label}",
                      type="primary", key=key):
            ok, result = execute_with_status(
                account, sql, label)
            if ok:
                st.markdown(
                    _success_banner(
                        f"{label} created successfully "
                        f"on {account}"),
                    unsafe_allow_html=True)
                st.cache_data.clear()
                if st.button("🎊 Create Another",
                              key=f"{key}_again"):
                    st.rerun()
            else:
                st.error(f"❌ {result}")
    with col2:
        if st.button("📋 Copy SQL", key=f"{key}_copy"):
            st.code(sql, language="sql")


# ══════════════════════════════════════════════════════════════════════════
# 1 — STORAGE INTEGRATION
# ══════════════════════════════════════════════════════════════════════════

if selected_object == "Storage Integration":
    st.markdown(
        _info_box(
            "A <b>Storage Integration</b> allows Snowflake to "
            "read/write data to cloud storage (S3, Azure Blob, "
            "GCS) without exposing credentials. "
            "Requires ACCOUNTADMIN.",
            accent=c("pwc_orange")
        ),
        unsafe_allow_html=True
    )

    st.markdown(_step(1, "Identity"), unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        si_name = st.text_input(
            "Integration Name *",
            placeholder="MY_S3_INTEGRATION",
            key="si_name")
        si_type = st.selectbox(
            "Cloud Provider",
            ["Amazon S3", "Azure Blob Storage",
             "Google Cloud Storage"],
            key="si_type")
    with c2:
        si_enabled = st.checkbox(
            "Enabled", value=True, key="si_enabled")
        si_comment = _comment_input("si")

    st.markdown(_step(2, "Allowed & Blocked Locations"),
                 unsafe_allow_html=True)
    si_allowed = st.text_area(
        "Allowed Locations *",
        placeholder=(
            "s3://my-bucket/path/\n"
            "s3://my-other-bucket/"),
        height=100, key="si_allowed",
        help="One URL per line"
    )
    si_blocked = st.text_area(
        "Blocked Locations (optional)",
        placeholder="s3://my-bucket/sensitive/",
        height=80, key="si_blocked",
        help="One URL per line"
    )

    if si_name and si_allowed:
        provider_map = {
            "Amazon S3":            "S3",
            "Azure Blob Storage":   "AZURE",
            "Google Cloud Storage": "GCS",
        }
        provider = provider_map[si_type]

        allowed_list = ", ".join(
            f"'{u.strip()}'"
            for u in si_allowed.strip().splitlines()
            if u.strip()
        )
        blocked_clause = ""
        if si_blocked.strip():
            blocked_list = ", ".join(
                f"'{u.strip()}'"
                for u in si_blocked.strip().splitlines()
                if u.strip()
            )
            blocked_clause = (
                f"\nSTORAGE_BLOCKED_LOCATIONS = "
                f"({blocked_list})")

        sql = (
            f"CREATE STORAGE INTEGRATION "
            f"IF NOT EXISTS {si_name}\n"
            f"    TYPE = EXTERNAL_STAGE\n"
            f"    STORAGE_PROVIDER = '{provider}'\n"
            f"    ENABLED = "
            f"{'TRUE' if si_enabled else 'FALSE'}\n"
            f"    STORAGE_ALLOWED_LOCATIONS = "
            f"({allowed_list})"
            f"{blocked_clause}"
            f"{_build_comment(si_comment)};"
        )

        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_si", "Storage Integration",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 2 — API INTEGRATION
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "API Integration":
    st.markdown(
        _info_box(
            "An <b>API Integration</b> defines authentication "
            "settings for calling external REST APIs via "
            "Snowflake External Functions.",
            accent=c("blue")
        ),
        unsafe_allow_html=True
    )

    st.markdown(_step(1, "Identity"), unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        ai_name = st.text_input("Integration Name *",
                                  placeholder="MY_API_INT",
                                  key="ai_name")
        ai_type = st.selectbox(
            "API Provider",
            ["aws_api_gateway",
             "aws_private_api_gateway",
             "azure_api_management",
             "google_api_gateway"],
            key="ai_type")
    with c2:
        ai_enabled = st.checkbox("Enabled", value=True,
                                  key="ai_enabled")
        ai_comment = _comment_input("ai")

    st.markdown(_step(2, "Endpoint & Auth"),
                 unsafe_allow_html=True)
    c3, c4 = st.columns(2)
    with c3:
        ai_endpoint = st.text_input(
            "API Allowed Prefixes *",
            placeholder="https://my-api.execute-api.us-east-1.amazonaws.com/",
            key="ai_endpoint")
    with c4:
        ai_role_arn = st.text_input(
            "API AWS Role ARN (if AWS)",
            placeholder="arn:aws:iam::123456789:role/my-role",
            key="ai_role_arn")

    if ai_name and ai_endpoint:
        role_clause = (
            f"\n    API_AWS_ROLE_ARN = '{ai_role_arn}'"
            if ai_role_arn else "")

        sql = (
            f"CREATE API INTEGRATION IF NOT EXISTS "
            f"{ai_name}\n"
            f"    API_PROVIDER = {ai_type}\n"
            f"    API_ALLOWED_PREFIXES = ('{ai_endpoint}')"
            f"{role_clause}\n"
            f"    ENABLED = "
            f"{'TRUE' if ai_enabled else 'FALSE'}"
            f"{_build_comment(ai_comment)};"
        )

        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_ai", "API Integration",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 3 — NOTIFICATION INTEGRATION
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "Notification Integration":
    st.markdown(
        _info_box(
            "A <b>Notification Integration</b> sends alerts "
            "to cloud messaging services (SNS, Azure Event Grid, "
            "GCS Pub/Sub) from Snowpipe or tasks.",
            accent=c("cyan")
        ),
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)
    with c1:
        ni_name = st.text_input("Integration Name *",
                                  placeholder="MY_NOTIF_INT",
                                  key="ni_name")
        ni_type = st.selectbox(
            "Provider",
            ["AWS_SNS", "AZURE_STORAGE_QUEUE",
             "GCP_PUBSUB"],
            key="ni_type")
        ni_enabled = st.checkbox("Enabled", value=True,
                                  key="ni_enabled")
    with c2:
        ni_topic = st.text_input(
            "Topic / Queue ARN *",
            placeholder="arn:aws:sns:us-east-1:123:my-topic",
            key="ni_topic")
        ni_comment = _comment_input("ni")

    if ni_name and ni_topic:
        sql = (
            f"CREATE NOTIFICATION INTEGRATION "
            f"IF NOT EXISTS {ni_name}\n"
            f"    ENABLED = "
            f"{'TRUE' if ni_enabled else 'FALSE'}\n"
            f"    TYPE = QUEUE\n"
            f"    NOTIFICATION_PROVIDER = {ni_type}\n"
            f"    DIRECTION = OUTBOUND\n"
            f"    AWS_SNS_TOPIC_ARN = '{ni_topic}'"
            f"{_build_comment(ni_comment)};"
        )
        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_ni",
                         "Notification Integration",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 4 — SECURITY INTEGRATION
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "Security Integration":
    st.markdown(
        _info_box(
            "A <b>Security Integration</b> configures SSO / "
            "OAuth / SCIM with external identity providers "
            "(Okta, Azure AD, etc.).",
            accent=c("red")
        ),
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)
    with c1:
        sec_name = st.text_input("Integration Name *",
                                   placeholder="MY_OKTA_SSO",
                                   key="sec_name")
        sec_type = st.selectbox(
            "Type",
            ["SAML2", "OAUTH", "SCIM"],
            key="sec_type")
    with c2:
        sec_enabled = st.checkbox("Enabled", value=True,
                                    key="sec_enabled")
        sec_comment = _comment_input("sec")

    if sec_type == "SAML2":
        c3, c4 = st.columns(2)
        with c3:
            sec_issuer = st.text_input(
                "SAML2 Issuer *",
                placeholder="https://www.okta.com/...",
                key="sec_issuer")
            sec_sso_url = st.text_input(
                "SSO URL *",
                placeholder="https://myorg.okta.com/app/.../sso/saml",
                key="sec_sso_url")
        with c4:
            sec_provider = st.selectbox(
                "SAML Provider",
                ["Okta","ADFS","AzureAD","OneLogin",
                 "Custom"],
                key="sec_provider")
            sec_x509 = st.text_area(
                "x509 Certificate *",
                placeholder="MIIDpDCCAoygAwIB...",
                height=100, key="sec_x509")

        if sec_name and sec_issuer and sec_sso_url:
            sql = (
                f"CREATE SECURITY INTEGRATION "
                f"IF NOT EXISTS {sec_name}\n"
                f"    TYPE = SAML2\n"
                f"    ENABLED = "
                f"{'TRUE' if sec_enabled else 'FALSE'}\n"
                f"    SAML2_ISSUER = '{sec_issuer}'\n"
                f"    SAML2_SSO_URL = '{sec_sso_url}'\n"
                f"    SAML2_PROVIDER = '{sec_provider}'\n"
                f"    SAML2_X509_CERT = '{sec_x509}'"
                f"{_build_comment(sec_comment)};"
            )
            section_header("GENERATED SQL")
            st.markdown(_sql_block(sql),
                         unsafe_allow_html=True)
            _execute_button("btn_sec",
                             "Security Integration",
                             sql, target_account)

    elif sec_type == "OAUTH":
        c3, c4 = st.columns(2)
        with c3:
            oauth_client = st.selectbox(
                "OAuth Client",
                ["LOOKER","TABLEAU_DESKTOP",
                 "TABLEAU_SERVER","POWER_BI",
                 "CUSTOM"],
                key="oauth_client")
        with c4:
            oauth_redirect = st.text_input(
                "Redirect URI (CUSTOM only)",
                key="oauth_redirect")

        if sec_name:
            redirect_c = (
                f"\n    OAUTH_REDIRECT_URI = "
                f"'{oauth_redirect}'"
                if oauth_redirect else "")
            sql = (
                f"CREATE SECURITY INTEGRATION "
                f"IF NOT EXISTS {sec_name}\n"
                f"    TYPE = OAUTH\n"
                f"    ENABLED = "
                f"{'TRUE' if sec_enabled else 'FALSE'}\n"
                f"    OAUTH_CLIENT = {oauth_client}"
                f"{redirect_c}"
                f"{_build_comment(sec_comment)};"
            )
            section_header("GENERATED SQL")
            st.markdown(_sql_block(sql),
                         unsafe_allow_html=True)
            _execute_button("btn_sec_oauth",
                             "OAuth Integration",
                             sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 5 — DATABASE
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "Database":
    st.markdown(
        _info_box(
            "Creates a new Snowflake <b>Database</b>. "
            "Optionally set a data retention period, "
            "default DDL collation, and transient flag.",
            accent=c("blue")
        ),
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        db_name = st.text_input("Database Name *",
                                  placeholder="MY_DATABASE",
                                  key="db_name")
        db_transient = st.checkbox("Transient (no Fail-safe)",
                                    value=False,
                                    key="db_transient")
    with c2:
        db_retention = st.number_input(
            "Data Retention (days)",
            min_value=0, max_value=90,
            value=1, key="db_retention")
        db_clone_from = st.text_input(
            "Clone From (optional)",
            placeholder="EXISTING_DB",
            key="db_clone_from")
    with c3:
        db_comment = _comment_input("db")
        replace, if_not = _or_replace_if_not_exists("db")

    if db_name:
        prefix = ("CREATE OR REPLACE "
                   if replace else "CREATE ")
        ifne   = ("IF NOT EXISTS "
                   if if_not and not replace else "")
        transient = "TRANSIENT " if db_transient else ""
        clone_c = (f"\nCLONE {db_clone_from}"
                    if db_clone_from else "")
        sql = (
            f"{prefix}{transient}DATABASE "
            f"{ifne}{db_name}"
            f"{clone_c}\n"
            f"    DATA_RETENTION_TIME_IN_DAYS = "
            f"{db_retention}"
            f"{_build_comment(db_comment)};"
        )
        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_db", "Database",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 6 — SCHEMA
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "Schema":
    st.markdown(
        _info_box(
            "Creates a new <b>Schema</b> inside a database. "
            "Schemas organise tables, views and other objects.",
            accent=c("blue")
        ),
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)
    with c1:
        dbs = fetch_databases(id(manager), target_account)
        sc_db = st.selectbox("Database *",
                               dbs or ["(none)"],
                               key="sc_db")
        sc_name = st.text_input("Schema Name *",
                                  placeholder="MY_SCHEMA",
                                  key="sc_name")
    with c2:
        sc_transient = st.checkbox("Transient",
                                    value=False,
                                    key="sc_transient")
        sc_managed   = st.checkbox("Managed Access",
                                    value=False,
                                    key="sc_managed")
        sc_retention = st.number_input(
            "Data Retention (days)",
            min_value=0, max_value=90,
            value=1, key="sc_retention")
        sc_comment = _comment_input("sc_obj")
        replace, if_not = _or_replace_if_not_exists("sc_obj")

    if sc_db and sc_db != "(none)" and sc_name:
        prefix    = "CREATE OR REPLACE " if replace else "CREATE "
        ifne      = ("IF NOT EXISTS "
                      if if_not and not replace else "")
        transient = "TRANSIENT " if sc_transient else ""
        managed_c = ("\nWITH MANAGED ACCESS"
                      if sc_managed else "")
        sql = (
            f'{prefix}{transient}SCHEMA '
            f'{ifne}"{sc_db}"."{sc_name}"'
            f'{managed_c}\n'
            f'    DATA_RETENTION_TIME_IN_DAYS = '
            f'{sc_retention}'
            f'{_build_comment(sc_comment)};'
        )
        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_sc", "Schema",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 7 — TABLE
# ══════════════════════════════════════════════════════════════════════════

elif selected_object in ("Table", "Transient Table"):
    is_transient = selected_object == "Transient Table"
    st.markdown(
        _info_box(
            f"Creates a {'<b>Transient Table</b> (no Fail-safe)' if is_transient else '<b>Permanent Table</b>'} "
            f"with column definitions, constraints and options.",
            accent=c("blue")
        ),
        unsafe_allow_html=True
    )

    st.markdown(_step(1, "Location"), unsafe_allow_html=True)
    tbl_db, tbl_sc = _db_schema_selectors("tbl")
    tbl_name = st.text_input("Table Name *",
                               placeholder="MY_TABLE",
                               key="tbl_name")

    st.markdown(_step(2, "Columns"), unsafe_allow_html=True)

    if "tbl_cols" not in st.session_state:
        st.session_state.tbl_cols = [
            {"name": "ID",         "type": "NUMBER",
             "nullable": False,    "default": "",
             "comment": ""},
            {"name": "CREATED_AT", "type": "TIMESTAMP_NTZ",
             "nullable": True,     "default": "CURRENT_TIMESTAMP()",
             "comment": ""},
        ]

    col_add, col_clear = st.columns(2)
    with col_add:
        if st.button("➕ Add Column", key="tbl_add_col"):
            st.session_state.tbl_cols.append(
                {"name": f"COL_{len(st.session_state.tbl_cols)+1}",
                 "type": "VARCHAR(255)",
                 "nullable": True,
                 "default": "",
                 "comment": ""})
    with col_clear:
        if st.button("🗑️ Clear All", key="tbl_clear_cols"):
            st.session_state.tbl_cols = []

    SNOW_TYPES = [
        "NUMBER", "FLOAT", "VARCHAR(255)", "VARCHAR(512)",
        "VARCHAR(4096)", "TEXT", "BOOLEAN",
        "DATE", "TIME", "TIMESTAMP_NTZ", "TIMESTAMP_TZ",
        "TIMESTAMP_LTZ", "VARIANT", "OBJECT", "ARRAY",
        "BINARY", "GEOGRAPHY", "GEOMETRY"
    ]

    cols_to_remove = []
    for i, col in enumerate(st.session_state.tbl_cols):
        cc1, cc2, cc3, cc4, cc5, cc6 = st.columns(
            [2.5, 2, 1, 2, 2, 0.5])
        with cc1:
            col["name"] = st.text_input(
                "Name", value=col["name"],
                key=f"col_name_{i}",
                label_visibility="collapsed"
                if i > 0 else "visible")
        with cc2:
            col["type"] = st.selectbox(
                "Type", SNOW_TYPES,
                index=SNOW_TYPES.index(col["type"])
                if col["type"] in SNOW_TYPES else 0,
                key=f"col_type_{i}",
                label_visibility="collapsed"
                if i > 0 else "visible")
        with cc3:
            col["nullable"] = st.checkbox(
                "NULL",
                value=col["nullable"],
                key=f"col_null_{i}")
        with cc4:
            col["default"] = st.text_input(
                "Default",
                value=col["default"],
                key=f"col_def_{i}",
                label_visibility="collapsed"
                if i > 0 else "visible")
        with cc5:
            col["comment"] = st.text_input(
                "Comment",
                value=col["comment"],
                key=f"col_cmt_{i}",
                label_visibility="collapsed"
                if i > 0 else "visible")
        with cc6:
            if st.button("✕", key=f"col_rm_{i}"):
                cols_to_remove.append(i)

    for idx in sorted(cols_to_remove, reverse=True):
        st.session_state.tbl_cols.pop(idx)

    st.markdown(_step(3, "Options"), unsafe_allow_html=True)
    o1, o2, o3 = st.columns(3)
    with o1:
        tbl_cluster = st.text_input(
            "Cluster By (optional)",
            placeholder="COL1, COL2",
            key="tbl_cluster")
    with o2:
        tbl_retention = st.number_input(
            "Data Retention (days)",
            min_value=0, max_value=90,
            value=0 if is_transient else 1,
            key="tbl_retention",
            disabled=is_transient)
    with o3:
        tbl_comment = _comment_input("tbl_obj")
        replace, if_not = _or_replace_if_not_exists("tbl_obj")

    if (tbl_db and tbl_db != "(none)"
            and tbl_sc and tbl_sc != "(none)"
            and tbl_name
            and st.session_state.tbl_cols):

        col_defs = []
        for col in st.session_state.tbl_cols:
            parts = [f'    "{col["name"]}" {col["type"]}']
            if not col["nullable"]:
                parts.append("NOT NULL")
            if col["default"]:
                parts.append(f'DEFAULT {col["default"]}')
            if col["comment"]:
                parts.append(f"COMMENT '{col['comment']}'")
            col_defs.append(" ".join(parts))

        prefix    = "CREATE OR REPLACE " if replace else "CREATE "
        ifne      = ("IF NOT EXISTS "
                      if if_not and not replace else "")
        transient = "TRANSIENT " if is_transient else ""
        cluster_c = (f"\nCLUSTER BY ({tbl_cluster})"
                      if tbl_cluster else "")
        ret_c     = (f"\nDATA_RETENTION_TIME_IN_DAYS = "
                      f"{tbl_retention}"
                      if not is_transient else "")

        sql = (
            f'{prefix}{transient}TABLE '
            f'{ifne}"{tbl_db}"."{tbl_sc}"."{tbl_name}" (\n'
            + ",\n".join(col_defs)
            + f'\n){cluster_c}{ret_c}'
            f'{_build_comment(tbl_comment)};'
        )
        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_tbl",
                         selected_object,
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 8 — VIEW
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "View":
    st.markdown(
        _info_box(
            "Creates a <b>View</b> — a stored SQL query "
            "that appears as a virtual table.",
            accent=c("blue")
        ),
        unsafe_allow_html=True
    )

    vw_db, vw_sc = _db_schema_selectors("vw")
    c1, c2 = st.columns(2)
    with c1:
        vw_name    = st.text_input("View Name *",
                                    placeholder="MY_VIEW",
                                    key="vw_name")
    with c2:
        vw_secure  = st.checkbox("SECURE View",
                                  value=False, key="vw_secure")
        replace, _ = _or_replace_if_not_exists("vw")
        vw_comment = _comment_input("vw")

    vw_sql_body = st.text_area(
        "SELECT Statement *",
        placeholder=(
            "SELECT\n"
            "    ID,\n"
            "    NAME,\n"
            "    CREATED_AT\n"
            "FROM MY_TABLE\n"
            "WHERE STATUS = 'ACTIVE'"),
        height=200, key="vw_sql_body")

    if (vw_db and vw_db != "(none)"
            and vw_sc and vw_sc != "(none)"
            and vw_name and vw_sql_body):
        prefix = "CREATE OR REPLACE " if replace else "CREATE "
        secure = "SECURE " if vw_secure else ""
        sql = (
            f'{prefix}{secure}VIEW '
            f'"{vw_db}"."{vw_sc}"."{vw_name}"'
            f'{_build_comment(vw_comment)}\nAS\n'
            f'{vw_sql_body};'
        )
        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_vw", "View",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 9 — MATERIALIZED VIEW
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "Materialized View":
    st.markdown(
        _info_box(
            "A <b>Materialized View</b> pre-computes and stores "
            "query results. Automatically refreshed by Snowflake. "
            "Requires Enterprise edition.",
            accent=c("cyan")
        ),
        unsafe_allow_html=True
    )

    mv_db, mv_sc = _db_schema_selectors("mv")
    c1, c2 = st.columns(2)
    with c1:
        mv_name   = st.text_input("View Name *",
                                   placeholder="MY_MV",
                                   key="mv_name")
        mv_wh     = st.selectbox(
            "Warehouse",
            fetch_warehouses(id(manager), target_account)
            or ["(default)"],
            key="mv_wh")
    with c2:
        mv_secure = st.checkbox("SECURE", value=False,
                                  key="mv_secure")
        mv_cluster = st.text_input("Cluster By",
                                    placeholder="COL1",
                                    key="mv_cluster")
        mv_comment = _comment_input("mv")
        replace, _ = _or_replace_if_not_exists("mv")

    mv_body = st.text_area(
        "SELECT Statement *",
        placeholder="SELECT ID, SUM(AMOUNT) AS TOTAL\nFROM ORDERS\nGROUP BY ID",
        height=160, key="mv_body")

    if (mv_db and mv_db != "(none)"
            and mv_sc and mv_sc != "(none)"
            and mv_name and mv_body):
        prefix  = "CREATE OR REPLACE " if replace else "CREATE "
        secure  = "SECURE " if mv_secure else ""
        cluster_c = (f"\nCLUSTER BY ({mv_cluster})"
                      if mv_cluster else "")
        sql = (
            f'{prefix}{secure}MATERIALIZED VIEW '
            f'"{mv_db}"."{mv_sc}"."{mv_name}"'
            f'{cluster_c}'
            f'{_build_comment(mv_comment)}\nAS\n'
            f'{mv_body};'
        )
        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_mv", "Materialized View",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 10 — SEQUENCE
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "Sequence":
    seq_db, seq_sc = _db_schema_selectors("seq")
    c1, c2, c3 = st.columns(3)
    with c1:
        seq_name  = st.text_input("Sequence Name *",
                                   placeholder="MY_SEQ",
                                   key="seq_name")
    with c2:
        seq_start = st.number_input("Start Value",
                                     value=1, key="seq_start")
        seq_incr  = st.number_input("Increment",
                                     value=1, key="seq_incr")
    with c3:
        seq_order   = st.checkbox("ORDER", value=False,
                                   key="seq_order")
        seq_comment = _comment_input("seq")
        replace, if_not = _or_replace_if_not_exists("seq")

    if (seq_db and seq_db != "(none)"
            and seq_sc and seq_sc != "(none)"
            and seq_name):
        prefix = "CREATE OR REPLACE " if replace else "CREATE "
        ifne   = ("IF NOT EXISTS "
                   if if_not and not replace else "")
        order_c = "\nORDER" if seq_order else "\nNOORDER"
        sql = (
            f'{prefix}SEQUENCE {ifne}'
            f'"{seq_db}"."{seq_sc}"."{seq_name}"\n'
            f'    START = {seq_start}\n'
            f'    INCREMENT = {seq_incr}'
            f'{order_c}'
            f'{_build_comment(seq_comment)};'
        )
        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_seq", "Sequence",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 11 — STREAM
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "Stream":
    st.markdown(
        _info_box(
            "A <b>Stream</b> records DML changes "
            "(INSERT/UPDATE/DELETE) to a source table "
            "for CDC pipelines.",
            accent=c("blue")
        ),
        unsafe_allow_html=True
    )

    str_db, str_sc = _db_schema_selectors("str")
    c1, c2, c3 = st.columns(3)
    with c1:
        str_name = st.text_input("Stream Name *",
                                   placeholder="MY_STREAM",
                                   key="str_name")
    with c2:
        str_src = st.text_input(
            "Source Table/View *",
            placeholder='"MY_DB"."MY_SCHEMA"."MY_TABLE"',
            key="str_src")
    with c3:
        str_mode = st.selectbox(
            "Stream Mode",
            ["DEFAULT", "APPEND_ONLY", "INSERT_ONLY"],
            key="str_mode")
        str_comment = _comment_input("str")
        replace, if_not = _or_replace_if_not_exists("str")

    if (str_db and str_db != "(none)"
            and str_sc and str_sc != "(none)"
            and str_name and str_src):
        prefix = "CREATE OR REPLACE " if replace else "CREATE "
        ifne   = ("IF NOT EXISTS "
                   if if_not and not replace else "")
        mode_c = (f"\n    {str_mode} = TRUE"
                   if str_mode != "DEFAULT" else "")
        sql = (
            f'{prefix}STREAM {ifne}'
            f'"{str_db}"."{str_sc}"."{str_name}"\n'
            f'    ON TABLE {str_src}'
            f'{mode_c}'
            f'{_build_comment(str_comment)};'
        )
        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_str", "Stream",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 12 — FILE FORMAT
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "File Format":
    st.markdown(
        _info_box(
            "A <b>File Format</b> object defines how Snowflake "
            "reads/writes external files. Reuse across multiple "
            "stages and COPY statements.",
            accent=c("pwc_orange")
        ),
        unsafe_allow_html=True
    )

    ff_db, ff_sc = _db_schema_selectors("ff")
    c1, c2 = st.columns(2)
    with c1:
        ff_name = st.text_input("File Format Name *",
                                  placeholder="MY_CSV_FORMAT",
                                  key="ff_name")
        ff_type = st.selectbox(
            "Format Type *",
            ["CSV", "JSON", "PARQUET",
             "AVRO", "ORC", "XML"],
            key="ff_type_obj")
    with c2:
        ff_comment = _comment_input("ff")
        replace, if_not = _or_replace_if_not_exists("ff")

    # Dynamic options per format
    opts = []

    if ff_type == "CSV":
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            ff_delim = st.text_input(
                "Field Delimiter",
                value=",", key="ff_delim")
            ff_record = st.text_input(
                "Record Delimiter",
                value="\\n", key="ff_record")
            ff_skip   = st.number_input(
                "Skip Header", 0, 10, 1,
                key="ff_skip")
        with fc2:
            ff_quote = st.text_input(
                "Field Optionally Enclosed By",
                value='"', key="ff_quote")
            ff_null  = st.text_input(
                "NULL IF", value="''",
                key="ff_null")
            ff_empty_null = st.checkbox(
                "Empty Field As Null",
                value=True, key="ff_empty_null")
        with fc3:
            ff_compress = st.selectbox(
                "Compression",
                ["AUTO","GZIP","BZ2","BROTLI",
                 "ZSTD","DEFLATE","NONE"],
                key="ff_compress")
            ff_trim = st.checkbox(
                "Trim Space", value=False,
                key="ff_trim")
            ff_err_limit = st.number_input(
                "Error Limit", 0, 10000, 0,
                key="ff_err_limit")

        opts = [
            f"    FIELD_DELIMITER = '{ff_delim}'",
            f"    RECORD_DELIMITER = '{ff_record}'",
            f"    SKIP_HEADER = {ff_skip}",
            f"    FIELD_OPTIONALLY_ENCLOSED_BY = '{ff_quote}'",
            f"    NULL_IF = ({ff_null})",
            f"    EMPTY_FIELD_AS_NULL = "
            f"{'TRUE' if ff_empty_null else 'FALSE'}",
            f"    COMPRESSION = {ff_compress}",
            f"    TRIM_SPACE = "
            f"{'TRUE' if ff_trim else 'FALSE'}",
        ]
        if ff_err_limit > 0:
            opts.append(f"    ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE")

    elif ff_type == "JSON":
        jc1, jc2 = st.columns(2)
        with jc1:
            ff_compress_j = st.selectbox(
                "Compression",
                ["AUTO","GZIP","BROTLI","ZSTD","NONE"],
                key="ff_compress_j")
            ff_strip_outer = st.checkbox(
                "Strip Outer Array",
                value=False, key="ff_strip_outer")
        with jc2:
            ff_strip_null = st.checkbox(
                "Strip Null Values",
                value=False, key="ff_strip_null")
            ff_ignore_utf = st.checkbox(
                "Ignore UTF-8 Errors",
                value=False, key="ff_ignore_utf")

        opts = [
            f"    COMPRESSION = {ff_compress_j}",
            f"    STRIP_OUTER_ARRAY = "
            f"{'TRUE' if ff_strip_outer else 'FALSE'}",
            f"    STRIP_NULL_VALUES = "
            f"{'TRUE' if ff_strip_null else 'FALSE'}",
            f"    IGNORE_UTF8_ERRORS = "
            f"{'TRUE' if ff_ignore_utf else 'FALSE'}",
        ]

    elif ff_type == "PARQUET":
        pc1, pc2 = st.columns(2)
        with pc1:
            ff_snappy = st.checkbox(
                "SNAPPY Compression",
                value=True, key="ff_snappy")
        with pc2:
            ff_binary = st.checkbox(
                "Binary As Text",
                value=True, key="ff_binary")
        opts = [
            f"    SNAPPY_COMPRESSION = "
            f"{'TRUE' if ff_snappy else 'FALSE'}",
            f"    BINARY_AS_TEXT = "
            f"{'TRUE' if ff_binary else 'FALSE'}",
        ]

    else:
        ff_compress_g = st.selectbox(
            "Compression",
            ["AUTO","GZIP","BROTLI","ZSTD","NONE"],
            key="ff_compress_g")
        opts = [f"    COMPRESSION = {ff_compress_g}"]

    if (ff_db and ff_db != "(none)"
            and ff_sc and ff_sc != "(none)"
            and ff_name):
        prefix = "CREATE OR REPLACE " if replace else "CREATE "
        ifne   = ("IF NOT EXISTS "
                   if if_not and not replace else "")
        opts_str = "\n".join(opts)
        sql = (
            f'{prefix}FILE FORMAT {ifne}'
            f'"{ff_db}"."{ff_sc}"."{ff_name}"\n'
            f'    TYPE = {ff_type}\n'
            f'{opts_str}'
            f'{_build_comment(ff_comment)};'
        )
        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_ff", "File Format",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 13 — INTERNAL STAGE
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "Internal Stage":
    ist_db, ist_sc = _db_schema_selectors("ist")
    c1, c2 = st.columns(2)
    with c1:
        ist_name = st.text_input("Stage Name *",
                                   placeholder="MY_STAGE",
                                   key="ist_name")
        ist_encrypt = st.selectbox(
            "Encryption Type",
            ["SNOWFLAKE_FULL",
             "SNOWFLAKE_SSE", "NONE"],
            key="ist_encrypt")
    with c2:
        ist_comment = _comment_input("ist")
        replace, if_not = _or_replace_if_not_exists("ist")

    if (ist_db and ist_db != "(none)"
            and ist_sc and ist_sc != "(none)"
            and ist_name):
        prefix = "CREATE OR REPLACE " if replace else "CREATE "
        ifne   = ("IF NOT EXISTS "
                   if if_not and not replace else "")
        sql = (
            f'{prefix}STAGE {ifne}'
            f'"{ist_db}"."{ist_sc}"."{ist_name}"\n'
            f'    ENCRYPTION = '
            f'(TYPE = \'{ist_encrypt}\')'
            f'{_build_comment(ist_comment)};'
        )
        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_ist", "Internal Stage",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 14 — EXTERNAL STAGE
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "External Stage":
    est_db, est_sc = _db_schema_selectors("est")
    c1, c2 = st.columns(2)
    with c1:
        est_name = st.text_input("Stage Name *",
                                   placeholder="MY_EXT_STAGE",
                                   key="est_name")
        est_provider = st.selectbox(
            "Cloud Provider",
            ["Amazon S3", "Azure Blob",
             "Google Cloud Storage"],
            key="est_provider")
    with c2:
        est_url = st.text_input(
            "URL *",
            placeholder="s3://my-bucket/path/",
            key="est_url")
        est_comment = _comment_input("est")
        replace, if_not = _or_replace_if_not_exists("est")

    ec1, ec2 = st.columns(2)
    with ec1:
        est_int = st.text_input(
            "Storage Integration (recommended)",
            placeholder="MY_STORAGE_INTEGRATION",
            key="est_int")
    with ec2:
        est_ff = st.selectbox(
            "Default File Format",
            ["(none)", "CSV", "JSON",
             "PARQUET", "AVRO", "ORC"],
            key="est_ff")

    if (est_db and est_db != "(none)"
            and est_sc and est_sc != "(none)"
            and est_name and est_url):
        prefix   = "CREATE OR REPLACE " if replace else "CREATE "
        ifne     = ("IF NOT EXISTS "
                     if if_not and not replace else "")
        int_c    = (f"\n    STORAGE_INTEGRATION = {est_int}"
                     if est_int else "")
        ff_c     = (f"\n    FILE_FORMAT = (TYPE = '{est_ff}')"
                     if est_ff != "(none)" else "")
        sql = (
            f'{prefix}STAGE {ifne}'
            f'"{est_db}"."{est_sc}"."{est_name}"\n'
            f"    URL = '{est_url}'"
            f'{int_c}{ff_c}'
            f'{_build_comment(est_comment)};'
        )
        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_est", "External Stage",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 15 — WAREHOUSE
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "Warehouse":
    st.markdown(
        _info_box(
            "Creates a virtual <b>Warehouse</b> (compute cluster). "
            "Configure size, auto-suspend, auto-resume and "
            "scaling policy.",
            accent=c("pwc_gold")
        ),
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        wh_name = st.text_input("Warehouse Name *",
                                  placeholder="MY_WH",
                                  key="wh_name")
        wh_size = st.selectbox(
            "Size *",
            ["X-SMALL","SMALL","MEDIUM","LARGE",
             "X-LARGE","2X-LARGE","3X-LARGE","4X-LARGE",
             "5X-LARGE","6X-LARGE"],
            index=1, key="wh_size")
        wh_type = st.selectbox(
            "Type",
            ["STANDARD", "SNOWPARK-OPTIMIZED"],
            key="wh_type")
    with c2:
        wh_auto_suspend = st.number_input(
            "Auto Suspend (seconds)",
            min_value=0, value=300, step=60,
            key="wh_auto_suspend")
        wh_auto_resume = st.checkbox(
            "Auto Resume", value=True,
            key="wh_auto_resume")
        wh_init_susp = st.checkbox(
            "Initially Suspended",
            value=False, key="wh_init_susp")
    with c3:
        wh_min_cluster = st.number_input(
            "Min Clusters (multi-cluster)",
            min_value=1, value=1,
            key="wh_min_cluster")
        wh_max_cluster = st.number_input(
            "Max Clusters",
            min_value=1, value=1,
            key="wh_max_cluster")
        wh_scaling = st.selectbox(
            "Scaling Policy",
            ["STANDARD", "ECONOMY"],
            key="wh_scaling")
        wh_comment = _comment_input("wh")
        replace, if_not = _or_replace_if_not_exists("wh")

    if wh_name:
        prefix = "CREATE OR REPLACE " if replace else "CREATE "
        ifne   = ("IF NOT EXISTS "
                   if if_not and not replace else "")
        multi_c = ""
        if wh_max_cluster > 1:
            multi_c = (
                f"\n    MIN_CLUSTER_COUNT = {wh_min_cluster}"
                f"\n    MAX_CLUSTER_COUNT = {wh_max_cluster}"
                f"\n    SCALING_POLICY = {wh_scaling}")
        init_c = ("\n    INITIALLY_SUSPENDED = TRUE"
                   if wh_init_susp else "")

        sql = (
            f'{prefix}WAREHOUSE {ifne}{wh_name}\n'
            f'    WAREHOUSE_SIZE = {wh_size}\n'
            f'    WAREHOUSE_TYPE = {wh_type}\n'
            f'    AUTO_SUSPEND = {wh_auto_suspend}\n'
            f'    AUTO_RESUME = '
            f"{'TRUE' if wh_auto_resume else 'FALSE'}"
            f'{multi_c}{init_c}'
            f'{_build_comment(wh_comment)};'
        )
        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_wh", "Warehouse",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 16 — RESOURCE MONITOR
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "Resource Monitor":
    st.markdown(
        _info_box(
            "A <b>Resource Monitor</b> sets credit usage "
            "limits on warehouses and triggers alerts or "
            "suspensions when thresholds are reached.",
            accent=c("red")
        ),
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        rm_name   = st.text_input("Monitor Name *",
                                    placeholder="MY_RM",
                                    key="rm_name")
        rm_credit = st.number_input(
            "Credit Quota *",
            min_value=1, value=100,
            key="rm_credit")
    with c2:
        rm_freq = st.selectbox(
            "Frequency",
            ["MONTHLY","DAILY","WEEKLY",
             "YEARLY","NEVER"],
            key="rm_freq")
        rm_start = st.date_input(
            "Start Timestamp",
            key="rm_start")
    with c3:
        rm_notify    = st.multiselect(
            "Notify at % thresholds",
            [50, 75, 90, 100, 110, 120, 150],
            default=[75, 90, 100],
            key="rm_notify")
        rm_suspend   = st.number_input(
            "Suspend at % (0=never)",
            min_value=0, value=100,
            key="rm_suspend")
        rm_suspend_i = st.number_input(
            "Suspend Immediately at %",
            min_value=0, value=0,
            key="rm_suspend_i")

    if rm_name:
        notify_str = (
            ", ".join(str(t) for t in sorted(rm_notify))
            if rm_notify else "")
        notify_c = (
            f"\n    NOTIFY = ({notify_str})"
            if notify_str else "")
        sus_c = (
            f"\n    SUSPEND_TRIGGERS = ({rm_suspend})"
            if rm_suspend > 0 else "")
        sus_i_c = (
            f"\n    SUSPEND_IMMEDIATE_TRIGGERS = "
            f"({rm_suspend_i})"
            if rm_suspend_i > 0 else "")

        sql = (
            f"CREATE OR REPLACE RESOURCE MONITOR {rm_name}\n"
            f"    CREDIT_QUOTA = {rm_credit}\n"
            f"    FREQUENCY = {rm_freq}\n"
            f"    START_TIMESTAMP = "
            f"'{rm_start} 00:00 UTC'"
            f"{notify_c}{sus_c}{sus_i_c};"
        )
        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_rm", "Resource Monitor",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 17 — TASK
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "Task":
    task_db, task_sc = _db_schema_selectors("task")
    c1, c2 = st.columns(2)
    with c1:
        task_name = st.text_input("Task Name *",
                                    placeholder="MY_TASK",
                                    key="task_name")
        wh_list   = fetch_warehouses(
            id(manager), target_account)
        task_wh   = st.selectbox(
            "Warehouse *",
            wh_list or ["(none)"],
            key="task_wh")
    with c2:
        sched_type = st.radio(
            "Schedule Type",
            ["CRON", "Minutes"],
            horizontal=True, key="task_sched_type")
        if sched_type == "CRON":
            task_cron = st.text_input(
                "CRON Expression",
                value="0 2 * * *",
                key="task_cron")
            task_tz = st.text_input(
                "Timezone", value="UTC",
                key="task_tz")
            schedule_val = (
                f"USING CRON {task_cron} {task_tz}")
        else:
            task_mins = st.number_input(
                "Every N Minutes",
                min_value=1, value=60,
                key="task_mins")
            schedule_val = f"{task_mins} MINUTE"

    c3, c4 = st.columns(2)
    with c3:
        task_pred = st.text_input(
            "Predecessor Task (optional)",
            placeholder="PARENT_TASK",
            key="task_pred")
        task_overlap = st.checkbox(
            "Allow Overlapping Execution",
            value=False, key="task_overlap")
    with c4:
        task_comment = _comment_input("task")
        replace, if_not = _or_replace_if_not_exists("task")
        task_init_susp = st.checkbox(
            "Initially Suspended",
            value=True, key="task_init_susp")

    task_sql_body = st.text_area(
        "SQL Statement *",
        placeholder="INSERT INTO MY_TABLE SELECT * FROM MY_SOURCE;",
        height=120, key="task_sql_body")

    if (task_db and task_db != "(none)"
            and task_sc and task_sc != "(none)"
            and task_name and task_sql_body
            and task_wh and task_wh != "(none)"):
        prefix = "CREATE OR REPLACE " if replace else "CREATE "
        ifne   = ("IF NOT EXISTS "
                   if if_not and not replace else "")
        sched_c = (
            f"\n    AFTER "
            f'"{task_db}"."{task_sc}"."{task_pred}"'
            if task_pred
            else f"\n    SCHEDULE = '{schedule_val}'")
        overlap_c = (
            "\n    ALLOW_OVERLAPPING_EXECUTION = TRUE"
            if task_overlap else "")
        init_c = (
            "\n    INITIALLY_SUSPENDED = TRUE"
            if task_init_susp else "")

        sql = (
            f'{prefix}TASK {ifne}'
            f'"{task_db}"."{task_sc}"."{task_name}"\n'
            f'    WAREHOUSE = "{task_wh}"'
            f'{sched_c}{overlap_c}{init_c}'
            f'{_build_comment(task_comment)}\n'
            f'AS\n{task_sql_body};'
        )
        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_task", "Task",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 18 — ROLE
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "Role":
    c1, c2 = st.columns(2)
    with c1:
        role_name = st.text_input("Role Name *",
                                    placeholder="MY_ROLE",
                                    key="role_name")
        role_comment = _comment_input("role")
        replace, if_not = _or_replace_if_not_exists("role")
    with c2:
        parent_roles = fetch_roles(
            id(manager), target_account)
        role_parent = st.selectbox(
            "Grant to Parent Role (optional)",
            options=["(none)"] + parent_roles,
            key="role_parent")
        users_df = manager.execute_query(
            target_account, "SHOW USERS") or pd.DataFrame()
        u_nc = next((col for col in ["name","NAME"]
                      if col in users_df.columns), None)
        user_list = (users_df[u_nc].tolist()
                      if u_nc and not users_df.empty else [])
        role_users = st.multiselect(
            "Grant to Users",
            options=user_list,
            key="role_users")

    if role_name:
        prefix = "CREATE OR REPLACE " if replace else "CREATE "
        ifne   = ("IF NOT EXISTS "
                   if if_not and not replace else "")
        sql = (
            f'{prefix}ROLE {ifne}"{role_name}"'
            f'{_build_comment(role_comment)};'
        )
        extra = []
        if role_parent != "(none)":
            extra.append(
                f'GRANT ROLE "{role_name}" '
                f'TO ROLE "{role_parent}";')
        for u in role_users:
            extra.append(
                f'GRANT ROLE "{role_name}" '
                f'TO USER "{u}";')

        all_sql = "\n".join([sql] + extra)
        section_header("GENERATED SQL")
        st.markdown(_sql_block(all_sql),
                     unsafe_allow_html=True)
        _execute_button("btn_role", "Role",
                         all_sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 19 — MASKING POLICY
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "Masking Policy":
    st.markdown(
        _info_box(
            "A <b>Masking Policy</b> dynamically masks "
            "column data based on the querying role. "
            "Requires Enterprise edition.",
            accent=c("red")
        ),
        unsafe_allow_html=True
    )

    mp_db, mp_sc = _db_schema_selectors("mp")
    c1, c2 = st.columns(2)
    with c1:
        mp_name = st.text_input("Policy Name *",
                                  placeholder="MASK_EMAIL",
                                  key="mp_name")
        mp_data_type = st.selectbox(
            "Data Type to Mask",
            ["STRING", "NUMBER", "DATE",
             "TIMESTAMP_NTZ", "VARIANT"],
            key="mp_data_type")
    with c2:
        mp_exempt_roles = st.text_input(
            "Exempt Roles (comma separated)",
            placeholder="SYSADMIN, ANALYST_ROLE",
            key="mp_exempt_roles")
        mp_comment = _comment_input("mp")
        replace, _ = _or_replace_if_not_exists("mp")

    exempt_list = [
        r.strip()
        for r in mp_exempt_roles.split(",")
        if r.strip()
    ] if mp_exempt_roles else []

    exempt_conditions = "\n        ".join([
        f"WHEN CURRENT_ROLE() = '{r}' THEN val"
        for r in exempt_list
    ])
    default_mask = (
        "'****@****.***'"
        if "STRING" in mp_data_type
        else "NULL"
    )

    if (mp_db and mp_db != "(none)"
            and mp_sc and mp_sc != "(none)"
            and mp_name):
        prefix   = "CREATE OR REPLACE " if replace else "CREATE "
        body = (
            f"    CASE\n"
            f"        {exempt_conditions}\n"
            f"        ELSE {default_mask}\n"
            f"    END"
            if exempt_conditions
            else f"    {default_mask}"
        )
        sql = (
            f'{prefix}MASKING POLICY '
            f'"{mp_db}"."{mp_sc}"."{mp_name}"\n'
            f'    AS (val {mp_data_type}) RETURNS '
            f'{mp_data_type} ->\n'
            f'{body}'
            f'{_build_comment(mp_comment)};'
        )
        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_mp", "Masking Policy",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 20 — ROW ACCESS POLICY
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "Row Access Policy":
    st.markdown(
        _info_box(
            "A <b>Row Access Policy</b> filters rows "
            "returned to the querying user based on "
            "role or session context.",
            accent=c("red")
        ),
        unsafe_allow_html=True
    )

    rap_db, rap_sc = _db_schema_selectors("rap")
    c1, c2 = st.columns(2)
    with c1:
        rap_name = st.text_input("Policy Name *",
                                   placeholder="MY_ROW_POLICY",
                                   key="rap_name")
        rap_col  = st.text_input(
            "Filter Column Name *",
            placeholder="REGION",
            key="rap_col")
        rap_col_type = st.selectbox(
            "Filter Column Type",
            ["VARCHAR", "NUMBER", "BOOLEAN"],
            key="rap_col_type")
    with c2:
        rap_allowed_roles = st.text_input(
            "Roles that see ALL rows",
            placeholder="SYSADMIN, ANALYST",
            key="rap_allowed_roles")
        rap_comment = _comment_input("rap")
        replace, _ = _or_replace_if_not_exists("rap")

    allowed = [
        r.strip()
        for r in rap_allowed_roles.split(",")
        if r.strip()
    ] if rap_allowed_roles else []

    allow_cond = " OR ".join(
        [f"CURRENT_ROLE() = '{r}'" for r in allowed]
    ) if allowed else "FALSE"

    if (rap_db and rap_db != "(none)"
            and rap_sc and rap_sc != "(none)"
            and rap_name and rap_col):
        prefix = "CREATE OR REPLACE " if replace else "CREATE "
        sql = (
            f'{prefix}ROW ACCESS POLICY '
            f'"{rap_db}"."{rap_sc}"."{rap_name}"\n'
            f'    AS ({rap_col} {rap_col_type}) '
            f'RETURNS BOOLEAN ->\n'
            f'    CASE\n'
            f'        WHEN {allow_cond} THEN TRUE\n'
            f'        ELSE {rap_col} = '
            f"CURRENT_USER()\n"
            f'    END'
            f'{_build_comment(rap_comment)};'
        )
        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_rap", "Row Access Policy",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 21 — NETWORK POLICY
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "Network Policy":
    st.markdown(
        _info_box(
            "A <b>Network Policy</b> restricts Snowflake "
            "access to specific IP ranges.",
            accent=c("red")
        ),
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)
    with c1:
        np_name = st.text_input("Policy Name *",
                                  placeholder="MY_NETWORK_POLICY",
                                  key="np_name_obj")
    with c2:
        np_comment = _comment_input("np_obj")
        replace, if_not = _or_replace_if_not_exists("np_obj")

    np_allowed = st.text_area(
        "Allowed IP List *",
        placeholder=(
            "192.168.1.0/24\n"
            "10.0.0.0/8\n"
            "203.0.113.5"),
        height=120, key="np_allowed",
        help="One CIDR or IP per line")
    np_blocked = st.text_area(
        "Blocked IP List (optional)",
        placeholder="192.168.1.99",
        height=80, key="np_blocked")

    if np_name and np_allowed:
        allowed_list = ", ".join(
            f"'{ip.strip()}'"
            for ip in np_allowed.strip().splitlines()
            if ip.strip()
        )
        blocked_clause = ""
        if np_blocked.strip():
            blocked_list = ", ".join(
                f"'{ip.strip()}'"
                for ip in np_blocked.strip().splitlines()
                if ip.strip()
            )
            blocked_clause = (
                f"\n    BLOCKED_IP_LIST = "
                f"({blocked_list})")
        prefix = "CREATE OR REPLACE " if replace else "CREATE "
        ifne   = ("IF NOT EXISTS "
                   if if_not and not replace else "")
        sql = (
            f'{prefix}NETWORK POLICY {ifne}{np_name}\n'
            f'    ALLOWED_IP_LIST = ({allowed_list})'
            f'{blocked_clause}'
            f'{_build_comment(np_comment)};'
        )
        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_np", "Network Policy",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 22 — TAG
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "Tag":
    tag_db, tag_sc = _db_schema_selectors("tag")
    c1, c2 = st.columns(2)
    with c1:
        tag_name = st.text_input("Tag Name *",
                                   placeholder="SENSITIVITY",
                                   key="tag_name")
    with c2:
        tag_allowed = st.text_input(
            "Allowed Values (comma separated, optional)",
            placeholder="PII, CONFIDENTIAL, PUBLIC",
            key="tag_allowed")
        tag_comment = _comment_input("tag")
        replace, if_not = _or_replace_if_not_exists("tag")

    if (tag_db and tag_db != "(none)"
            and tag_sc and tag_sc != "(none)"
            and tag_name):
        prefix = "CREATE OR REPLACE " if replace else "CREATE "
        ifne   = ("IF NOT EXISTS "
                   if if_not and not replace else "")
        allowed_c = ""
        if tag_allowed.strip():
            vals = ", ".join(
                f"'{v.strip()}'"
                for v in tag_allowed.split(",")
                if v.strip()
            )
            allowed_c = f"\n    ALLOWED_VALUES {vals}"
        sql = (
            f'{prefix}TAG {ifne}'
            f'"{tag_db}"."{tag_sc}"."{tag_name}"'
            f'{allowed_c}'
            f'{_build_comment(tag_comment)};'
        )
        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_tag", "Tag",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 23 — STORED PROCEDURE (JavaScript)
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "Stored Procedure (JavaScript)":
    sp_db, sp_sc = _db_schema_selectors("sp_js")
    c1, c2 = st.columns(2)
    with c1:
        sp_name = st.text_input("Procedure Name *",
                                  placeholder="MY_PROC",
                                  key="sp_js_name")
        sp_return = st.selectbox(
            "Return Type",
            ["STRING", "NUMBER", "VARIANT",
             "BOOLEAN", "FLOAT", "ARRAY"],
            key="sp_js_return")
    with c2:
        sp_execute_as = st.selectbox(
            "Execute As",
            ["CALLER", "OWNER"],
            key="sp_js_exec_as")
        sp_comment = _comment_input("sp_js")
        replace, _ = _or_replace_if_not_exists("sp_js")

    sp_params = st.text_input(
        "Parameters (optional)",
        placeholder="PARAM1 STRING, PARAM2 NUMBER",
        key="sp_js_params")

    sp_body = st.text_area(
        "JavaScript Body *",
        value=(
            "var result = '';\n"
            "try {\n"
            "    // your code here\n"
            "    result = 'success';\n"
            "} catch(err) {\n"
            "    result = err.message;\n"
            "}\n"
            "return result;"),
        height=200, key="sp_js_body")

    if (sp_db and sp_db != "(none)"
            and sp_sc and sp_sc != "(none)"
            and sp_name and sp_body):
        prefix = "CREATE OR REPLACE " if replace else "CREATE "
        params = sp_params or ""
        sql = (
            f'{prefix}PROCEDURE '
            f'"{sp_db}"."{sp_sc}"."{sp_name}"({params})\n'
            f'    RETURNS {sp_return}\n'
            f'    LANGUAGE JAVASCRIPT\n'
            f'    EXECUTE AS {sp_execute_as}'
            f'{_build_comment(sp_comment)}\n'
            f'    AS\n'
            f"    $$\n"
            f"{sp_body}\n"
            f"    $$;"
        )
        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_sp_js",
                         "Stored Procedure",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 24 — STORED PROCEDURE (Python)
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "Stored Procedure (Python)":
    spy_db, spy_sc = _db_schema_selectors("sp_py")
    c1, c2, c3 = st.columns(3)
    with c1:
        spy_name = st.text_input("Procedure Name *",
                                   placeholder="MY_PY_PROC",
                                   key="spy_name")
        spy_return = st.selectbox(
            "Return Type",
            ["str", "int", "float",
             "bool", "list", "dict", "variant"],
            key="spy_return")
    with c2:
        spy_runtime = st.selectbox(
            "Python Runtime",
            ["3.11", "3.10", "3.9", "3.8"],
            key="spy_runtime")
        spy_packages = st.text_input(
            "Packages (comma separated)",
            placeholder="snowflake-snowpark-python,pandas",
            key="spy_packages")
    with c3:
        spy_handler = st.text_input(
            "Handler Function *",
            value="main",
            key="spy_handler")
        spy_execute_as = st.selectbox(
            "Execute As",
            ["CALLER", "OWNER"],
            key="spy_exec_as")
        spy_comment = _comment_input("sp_py")
        replace, _ = _or_replace_if_not_exists("sp_py")

    spy_params = st.text_input(
        "Parameters (optional)",
        placeholder="session: snowflake.snowpark.Session, name: str",
        key="spy_params")

    spy_body = st.text_area(
        "Python Function Body *",
        value=(
            "import snowflake.snowpark as snowpark\n\n"
            "def main(session: snowpark.Session) -> str:\n"
            "    # your code here\n"
            "    df = session.table('MY_TABLE')\n"
            "    return f'Row count: {df.count()}'"),
        height=220, key="spy_body")

    if (spy_db and spy_db != "(none)"
            and spy_sc and spy_sc != "(none)"
            and spy_name and spy_body and spy_handler):
        prefix = "CREATE OR REPLACE " if replace else "CREATE "
        params = spy_params or ""
        pkgs   = (
            "', '".join(
                p.strip()
                for p in spy_packages.split(",")
                if p.strip())
            if spy_packages else
            "snowflake-snowpark-python"
        )
        sql = (
            f'{prefix}PROCEDURE '
            f'"{spy_db}"."{spy_sc}"."{spy_name}"({params})\n'
            f'    RETURNS {spy_return}\n'
            f'    LANGUAGE PYTHON\n'
            f"    RUNTIME_VERSION = '{spy_runtime}'\n"
            f"    PACKAGES = ('{pkgs}')\n"
            f'    HANDLER = \'{spy_handler}\'\n'
            f'    EXECUTE AS {spy_execute_as}'
            f'{_build_comment(spy_comment)}\n'
            f'    AS\n'
            f"    $$\n"
            f"{spy_body}\n"
            f"    $$;"
        )
        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_spy",
                         "Python Procedure",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 25 — UDF (JavaScript / Python / SQL)
# ══════════════════════════════════════════════════════════════════════════

elif selected_object in ("UDF (JavaScript)",
                          "UDF (Python)",
                          "UDF (SQL)"):
    lang = (selected_object
            .replace("UDF (","")
            .replace(")",""))

    udf_db, udf_sc = _db_schema_selectors("udf")
    c1, c2, c3 = st.columns(3)
    with c1:
        udf_name = st.text_input("UDF Name *",
                                   placeholder="MY_UDF",
                                   key="udf_name")
        udf_return = st.selectbox(
            "Return Type",
            ["STRING", "NUMBER", "FLOAT",
             "BOOLEAN", "VARIANT",
             "TABLE(col STRING)"],
            key="udf_return")
    with c2:
        udf_params = st.text_input(
            "Parameters",
            placeholder="x FLOAT, y FLOAT",
            key="udf_params")
        if lang == "Python":
            udf_runtime = st.selectbox(
                "Runtime",
                ["3.11","3.10","3.9"],
                key="udf_runtime")
            udf_handler = st.text_input(
                "Handler", value="compute",
                key="udf_handler")
    with c3:
        udf_immutable = st.checkbox(
            "IMMUTABLE (deterministic)",
            value=True, key="udf_immut")
        udf_comment   = _comment_input("udf")
        replace, _    = _or_replace_if_not_exists("udf")

    if lang == "SQL":
        default_body = "RETURN x + y;"
    elif lang == "JavaScript":
        default_body = "return x + y;"
    else:
        default_body = (
            "def compute(x: float, y: float) -> float:\n"
            "    return x + y")

    udf_body = st.text_area(
        "Function Body *",
        value=default_body,
        height=160, key="udf_body")

    if (udf_db and udf_db != "(none)"
            and udf_sc and udf_sc != "(none)"
            and udf_name and udf_body):
        prefix  = "CREATE OR REPLACE " if replace else "CREATE "
        immut_c = "\n    IMMUTABLE" if udf_immutable else ""
        params  = udf_params or ""

        if lang == "SQL":
            sql = (
                f'{prefix}FUNCTION '
                f'"{udf_db}"."{udf_sc}"."{udf_name}"'
                f'({params})\n'
                f'    RETURNS {udf_return}{immut_c}'
                f'{_build_comment(udf_comment)}\n'
                f'    AS\n'
                f"    $$\n{udf_body}\n    $$;"
            )
        elif lang == "JavaScript":
            sql = (
                f'{prefix}FUNCTION '
                f'"{udf_db}"."{udf_sc}"."{udf_name}"'
                f'({params})\n'
                f'    RETURNS {udf_return}\n'
                f'    LANGUAGE JAVASCRIPT{immut_c}'
                f'{_build_comment(udf_comment)}\n'
                f'    AS\n'
                f"    $$\n{udf_body}\n    $$;"
            )
        else:  # Python
            handler  = udf_handler if udf_handler else "compute"
            runtime  = udf_runtime if udf_runtime else "3.11"
            sql = (
                f'{prefix}FUNCTION '
                f'"{udf_db}"."{udf_sc}"."{udf_name}"'
                f'({params})\n'
                f'    RETURNS {udf_return}\n'
                f'    LANGUAGE PYTHON\n'
                f"    RUNTIME_VERSION = '{runtime}'\n"
                f"    PACKAGES = "
                f"('snowflake-snowpark-python')\n"
                f"    HANDLER = '{handler}'{immut_c}"
                f'{_build_comment(udf_comment)}\n'
                f'    AS\n'
                f"    $$\n{udf_body}\n    $$;"
            )

        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button(f"btn_udf_{lang}", f"{lang} UDF",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 26 — SHARE
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "Share":
    st.markdown(
        _info_box(
            "A <b>Share</b> allows you to securely share "
            "Snowflake data with other accounts without "
            "copying data.",
            accent=c("cyan")
        ),
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)
    with c1:
        share_name = st.text_input("Share Name *",
                                    placeholder="MY_SHARE",
                                    key="share_name")
        share_comment = _comment_input("share")
        replace, _ = _or_replace_if_not_exists("share")
    with c2:
        share_accounts = st.text_area(
            "Consumer Accounts (one per line)",
            placeholder="ORG.CONSUMER_ACCOUNT1\nORG.CONSUMER_ACCOUNT2",
            height=100, key="share_accounts")

    share_objects = st.text_area(
        "Objects to Share (one per line)",
        placeholder=(
            'DATABASE MY_DB\n'
            'SCHEMA MY_DB.MY_SCHEMA\n'
            'TABLE MY_DB.MY_SCHEMA.MY_TABLE'),
        height=120, key="share_objects")

    if share_name:
        prefix = "CREATE OR REPLACE " if replace else "CREATE "
        sql_lines = [
            f'{prefix}SHARE "{share_name}"'
            f'{_build_comment(share_comment)};'
        ]
        if share_objects.strip():
            for obj in share_objects.strip().splitlines():
                if obj.strip():
                    sql_lines.append(
                        f'GRANT USAGE ON {obj.strip()} '
                        f'TO SHARE "{share_name}";')
        if share_accounts.strip():
            for acc in share_accounts.strip().splitlines():
                if acc.strip():
                    sql_lines.append(
                        f'ALTER SHARE "{share_name}" '
                        f'ADD ACCOUNT = {acc.strip()};')

        all_sql = "\n".join(sql_lines)
        section_header("GENERATED SQL")
        st.markdown(_sql_block(all_sql),
                     unsafe_allow_html=True)
        _execute_button("btn_share", "Share",
                         all_sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 27 — FAILSAFE / CLONE
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "Failsafe / Clone":
    st.markdown(
        _info_box(
            "<b>Zero-copy Clone</b> creates an instant "
            "snapshot of any Snowflake object (DB, schema, "
            "table) without duplicating storage.",
            accent=c("pwc_gold")
        ),
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)
    with c1:
        clone_type = st.selectbox(
            "Object Type to Clone",
            ["DATABASE", "SCHEMA", "TABLE",
             "STREAM", "STAGE"],
            key="clone_type")
        clone_src = st.text_input(
            "Source Object *",
            placeholder='"MY_DB"."MY_SCHEMA"."MY_TABLE"',
            key="clone_src")
    with c2:
        clone_target = st.text_input(
            "Clone Name *",
            placeholder='"MY_DB"."MY_SCHEMA"."MY_TABLE_CLONE"',
            key="clone_target")
        clone_at = st.text_input(
            "AT / BEFORE (optional)",
            placeholder="TIMESTAMP => '2024-01-01 00:00:00'",
            key="clone_at")
        replace, _ = _or_replace_if_not_exists("clone")

    if clone_src and clone_target:
        prefix = "CREATE OR REPLACE " if replace else "CREATE "
        at_c   = (f"\n    AT ({clone_at})"
                   if clone_at else "")
        sql = (
            f'{prefix}{clone_type} {clone_target}\n'
            f'    CLONE {clone_src}{at_c};'
        )
        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_clone", "Clone",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 28 — PIPE (SNOWPIPE)
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "Pipe (Snowpipe)":
    pip_db, pip_sc = _db_schema_selectors("pip")
    c1, c2 = st.columns(2)
    with c1:
        pip_name = st.text_input("Pipe Name *",
                                   placeholder="MY_PIPE",
                                   key="pip_name")
        pip_auto = st.checkbox("AUTO_INGEST",
                                value=True,
                                key="pip_auto")
    with c2:
        pip_stage = st.text_input(
            "Source Stage *",
            placeholder="@MY_DB.MY_SCHEMA.MY_STAGE",
            key="pip_stage")
        pip_comment = _comment_input("pip")
        replace, _ = _or_replace_if_not_exists("pip")

    pip_table = st.text_input(
        "Target Table *",
        placeholder='"MY_DB"."MY_SCHEMA"."MY_TABLE"',
        key="pip_table")
    pip_copy_opts = st.text_input(
        "Additional COPY options (optional)",
        placeholder="FILE_FORMAT = (TYPE = 'CSV' SKIP_HEADER = 1)",
        key="pip_copy_opts")

    if (pip_db and pip_db != "(none)"
            and pip_sc and pip_sc != "(none)"
            and pip_name and pip_stage and pip_table):
        prefix = "CREATE OR REPLACE " if replace else "CREATE "
        auto_c = "\n    AUTO_INGEST = TRUE" if pip_auto else ""
        copy_opts_c = (f"\n{pip_copy_opts}"
                        if pip_copy_opts else "")
        sql = (
            f'{prefix}PIPE '
            f'"{pip_db}"."{pip_sc}"."{pip_name}"'
            f'{auto_c}'
            f'{_build_comment(pip_comment)}\n'
            f'AS\n'
            f'COPY INTO {pip_table}\n'
            f'FROM {pip_stage}'
            f'{copy_opts_c};'
        )
        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_pip", "Snowpipe",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 29 — DYNAMIC TABLE
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "Dynamic Table":
    st.markdown(
        _info_box(
            "A <b>Dynamic Table</b> automatically refreshes "
            "based on a target lag and a defining query. "
            "Replaces complex pipelines with declarative SQL.",
            accent=c("cyan")
        ),
        unsafe_allow_html=True
    )

    dt_db, dt_sc = _db_schema_selectors("dt")
    c1, c2, c3 = st.columns(3)
    with c1:
        dt_name = st.text_input("Table Name *",
                                  placeholder="MY_DYN_TABLE",
                                  key="dt_name")
        dt_wh   = st.selectbox(
            "Warehouse *",
            fetch_warehouses(id(manager), target_account)
            or ["(none)"],
            key="dt_wh")
    with c2:
        dt_lag_unit = st.selectbox(
            "Target Lag Unit",
            ["MINUTE", "HOUR", "DAY",
             "DOWNSTREAM"],
            key="dt_lag_unit")
        dt_lag_val = st.number_input(
            "Lag Value (ignored if DOWNSTREAM)",
            min_value=1, value=5,
            key="dt_lag_val")
    with c3:
        dt_refresh = st.selectbox(
            "Refresh Mode",
            ["AUTO", "FULL", "INCREMENTAL"],
            key="dt_refresh")
        dt_init = st.selectbox(
            "Initialize",
            ["ON_CREATE", "ON_SCHEDULE"],
            key="dt_init")
        dt_comment = _comment_input("dt")
        replace, _ = _or_replace_if_not_exists("dt")

    dt_body = st.text_area(
        "Defining Query *",
        placeholder=(
            "SELECT\n"
            "    ID,\n"
            "    SUM(AMOUNT) AS TOTAL\n"
            "FROM SOURCE_TABLE\n"
            "GROUP BY ID"),
        height=180, key="dt_body")

    if (dt_db and dt_db != "(none)"
            and dt_sc and dt_sc != "(none)"
            and dt_name and dt_body
            and dt_wh and dt_wh != "(none)"):
        prefix = "CREATE OR REPLACE " if replace else "CREATE "
        lag_c  = (
            "DOWNSTREAM"
            if dt_lag_unit == "DOWNSTREAM"
            else f"{dt_lag_val} {dt_lag_unit}")
        sql = (
            f'{prefix}DYNAMIC TABLE '
            f'"{dt_db}"."{dt_sc}"."{dt_name}"\n'
            f'    TARGET_LAG = \'{lag_c}\'\n'
            f'    WAREHOUSE = {dt_wh}\n'
            f'    REFRESH_MODE = {dt_refresh}\n'
            f'    INITIALIZE = {dt_init}'
            f'{_build_comment(dt_comment)}\n'
            f'AS\n{dt_body};'
        )
        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_dt", "Dynamic Table",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# 30 — EXTERNAL TABLE
# ══════════════════════════════════════════════════════════════════════════

elif selected_object == "External Table":
    st.markdown(
        _info_box(
            "An <b>External Table</b> queries data directly "
            "from external cloud storage without loading it "
            "into Snowflake.",
            accent=c("pwc_gold")
        ),
        unsafe_allow_html=True
    )

    et_db, et_sc = _db_schema_selectors("et")
    c1, c2 = st.columns(2)
    with c1:
        et_name  = st.text_input("Table Name *",
                                   placeholder="MY_EXT_TABLE",
                                   key="et_name")
        et_stage = st.text_input(
            "Stage Location *",
            placeholder="@MY_DB.MY_SCHEMA.MY_STAGE/path/",
            key="et_stage")
    with c2:
        et_format = st.selectbox(
            "File Format",
            ["CSV", "JSON", "PARQUET", "AVRO", "ORC"],
            key="et_format")
        et_partition = st.text_input(
            "Partition By (optional)",
            placeholder="to_date(split_part(metadata$filename,'/',3),'YYYYMMDD')",
            key="et_partition")
        et_comment = _comment_input("et")
        replace, if_not = _or_replace_if_not_exists("et")

    et_cols = st.text_area(
        "Column Definitions *",
        placeholder=(
            "ID NUMBER AS (VALUE:id::NUMBER),\n"
            "NAME STRING AS (VALUE:name::STRING),\n"
            "TS TIMESTAMP AS (VALUE:ts::TIMESTAMP)"),
        height=130, key="et_cols")

    if (et_db and et_db != "(none)"
            and et_sc and et_sc != "(none)"
            and et_name and et_stage and et_cols):
        prefix = "CREATE OR REPLACE " if replace else "CREATE "
        ifne   = ("IF NOT EXISTS "
                   if if_not and not replace else "")
        part_c = (f"\n    PARTITION BY ({et_partition})"
                   if et_partition else "")
        sql = (
            f'{prefix}EXTERNAL TABLE {ifne}'
            f'"{et_db}"."{et_sc}"."{et_name}" (\n'
            f'    {et_cols}\n'
            f')\n'
            f"    WITH LOCATION = {et_stage}"
            f'{part_c}\n'
            f"    FILE_FORMAT = (TYPE = '{et_format}')"
            f'{_build_comment(et_comment)};'
        )
        section_header("GENERATED SQL")
        st.markdown(_sql_block(sql), unsafe_allow_html=True)
        _execute_button("btn_et", "External Table",
                         sql, target_account)


# ══════════════════════════════════════════════════════════════════════════
# CATCH-ALL for objects not yet implemented
# ══════════════════════════════════════════════════════════════════════════

else:
    st.markdown(
        _info_box(
            f"The guided form for <b>{selected_object}</b> "
            f"is coming soon. In the meantime you can write "
            f"the SQL directly below and execute it.",
            accent=c("pwc_gold")
        ),
        unsafe_allow_html=True
    )

    raw_sql = st.text_area(
        "SQL Statement",
        placeholder=f"CREATE {selected_object.upper()} ...",
        height=200, key="raw_sql")

    if raw_sql.strip():
        section_header("PREVIEW")
        st.markdown(_sql_block(raw_sql.strip()),
                     unsafe_allow_html=True)
        if st.button("▶️ Execute SQL", type="primary",
                      key="btn_raw"):
            ok, result = execute_with_status(
                target_account,
                raw_sql.strip(),
                selected_object)
            if ok:
                st.markdown(
                    _success_banner(
                        f"{selected_object} executed "
                        f"on {target_account}"),
                    unsafe_allow_html=True)
                st.cache_data.clear()
            else:
                st.error(f"❌ {result}")

# ─── Footer ───────────────────────────────────────────────────────────────────

st.markdown(
    f'<div style="text-align:center;padding:28px 0 10px;'
    f'border-top:1px solid {c("border")};margin-top:32px;">'
    f'<div style="font-size:0.78rem;font-weight:800;'
    f'color:{c("text_primary")};">'
    f'🏗️ Object Creator'
    f'&nbsp;·&nbsp;'
    f'<span style="color:{c("pwc_orange")};font-weight:800;'
    f'font-size:0.68rem;text-transform:uppercase;'
    f'letter-spacing:0.12em;">'
    f'Powered By PwC Data &amp; AI</span>'
    f'</div>'
    f'<div style="margin-top:4px;font-size:0.66rem;'
    f'color:{c("text_dim","#5f6b7c")};">'
    f'{len(connected)} environment(s) · '
    f'{sum(len(v) for v in OBJECT_GROUPS.values())} '
    f'object types available'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True
)