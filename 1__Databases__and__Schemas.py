"""
Databases & Schemas monitoring page.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from theme import inject_grafana_css, COLORS, grafana_panel
inject_grafana_css()
from utils import get_manager_and_check, apply_account_filter
from theme import (
    inject_css, COLORS, CHART_COLORS, get_env_color,
    pwc_header, section_header, grafana_panel,
    kpi_card, stat_card, env_badge_html, env_badge, status_dot,
    premium_info_box
)

st.set_page_config(
    page_title="Your Page · PwC",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded"
)
inject_css()

pwc_header(
    "DATABASE and SCHEMA CENTER",
    subtitle="Snowflake Operational Monitoring Experience"
)

st.set_page_config(page_title="Databases & Schemas", page_icon="📊", layout="wide")
st.title("📊 Databases & Schemas")

manager, connected = get_manager_and_check()
selected_accounts = apply_account_filter(manager, connected)



# ─── Databases ────────────────────────────────────────────────────────────────

st.header("Databases")

all_databases = []
for acc in selected_accounts:
    df = manager.execute_query(acc, """
        SHOW DATABASES
    """)
    if df is not None and not df.empty:
        all_databases.append(df)

if all_databases:
    db_df = pd.concat(all_databases, ignore_index=True)

    # Display key columns
    display_cols = ["_ACCOUNT", "name", "origin", "owner", "retention_time",
                    "created_on", "options", "comment"]
    available_cols = [c for c in display_cols if c in db_df.columns]

    col1, col2 = st.columns([1, 2])

    with col1:
        # Database count per account
        db_counts = db_df.groupby("_ACCOUNT").size().reset_index(name="Count")
        fig = px.pie(db_counts, values="Count", names="_ACCOUNT",
                     title="Databases per Account")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.dataframe(
            db_df[available_cols].rename(columns={"_ACCOUNT": "Account", "name": "Database"}),
            use_container_width=True,
            height=400
        )

    # ─── Schemas ──────────────────────────────────────────────────────────────

    st.header("Schemas")

    # Filter by database
    selected_db = st.selectbox(
        "Select Database to view schemas",
        options=["All"] + sorted(db_df["name"].unique().tolist())
    )

    all_schemas = []
    for acc in selected_accounts:
        if selected_db == "All":
            # Get schemas from all databases
            databases = db_df[db_df["_ACCOUNT"] == acc]["name"].tolist()
        else:
            databases = [selected_db]

        for db_name in databases:
            try:
                df = manager.execute_query(acc, f'SHOW SCHEMAS IN DATABASE "{db_name}"')
                if df is not None and not df.empty:
                    df["DATABASE"] = db_name
                    all_schemas.append(df)
            except Exception:
                continue

    if all_schemas:
        schema_df = pd.concat(all_schemas, ignore_index=True)

        schema_display_cols = ["_ACCOUNT", "DATABASE", "name", "owner",
                               "retention_time", "created_on", "options"]
        available_schema_cols = [c for c in schema_display_cols if c in schema_df.columns]

        # Schema count by database
        schema_counts = schema_df.groupby(["_ACCOUNT", "DATABASE"]).size().reset_index(name="Schema Count")

        fig = px.bar(
            schema_counts, x="DATABASE", y="Schema Count", color="_ACCOUNT",
            barmode="group", title="Schema Count by Database",
            height=400
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            schema_df[available_schema_cols].rename(columns={
                "_ACCOUNT": "Account", "name": "Schema", "DATABASE": "Database"
            }),
            use_container_width=True,
            height=400
        )
    else:
        st.info("No schemas found.")
else:
    st.warning("No databases found across selected accounts.")