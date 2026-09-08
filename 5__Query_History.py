"""
Query History monitoring page.
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
    "History Of the Queries",
    subtitle="Snowflake Operational Monitoring Experience"
)

manager, connected = get_manager_and_check()
selected_accounts = apply_account_filter(manager, connected)

# ─── Filters ──────────────────────────────────────────────────────────────────

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Query Filters")

days_back = st.sidebar.slider("Days Back", 1, 30, 7)
limit = st.sidebar.number_input("Max Results per Account", 100, 10000, 1000, step=100)
min_duration = st.sidebar.number_input("Min Duration (seconds)", 0, 3600, 0, step=10)

query_type_filter = st.sidebar.multiselect(
    "Query Type",
    ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER",
     "MERGE", "COPY", "CALL", "OTHER"],
    default=[]
)

user_filter = st.sidebar.text_input("User (optional)", "")

# ─── Fetch Query History ─────────────────────────────────────────────────────

all_history = []

for acc in selected_accounts:
    try:
        where_clauses = [f"START_TIME >= DATEADD('day', -{days_back}, CURRENT_TIMESTAMP())"]

        if min_duration > 0:
            where_clauses.append(f"TOTAL_ELAPSED_TIME >= {min_duration * 1000}")
        if user_filter:
            where_clauses.append(f"USER_NAME = '{user_filter.upper()}'")
        if query_type_filter:
            types = ",".join([f"'{t}'" for t in query_type_filter])
            where_clauses.append(f"QUERY_TYPE IN ({types})")

        where_str = " AND ".join(where_clauses)

        query = f"""
            SELECT
                QUERY_ID,
                QUERY_TEXT,
                QUERY_TYPE,
                DATABASE_NAME,
                SCHEMA_NAME,
                WAREHOUSE_NAME,
                USER_NAME,
                ROLE_NAME,
                EXECUTION_STATUS,
                ERROR_CODE,
                ERROR_MESSAGE,
                START_TIME,
                END_TIME,
                TOTAL_ELAPSED_TIME / 1000.0 AS DURATION_SECONDS,
                BYTES_SCANNED,
                ROWS_PRODUCED,
                COMPILATION_TIME / 1000.0 AS COMPILATION_SECONDS,
                EXECUTION_TIME / 1000.0 AS EXECUTION_SECONDS,
                QUEUED_OVERLOAD_TIME / 1000.0 AS QUEUED_SECONDS,
                BYTES_WRITTEN_TO_RESULT,
                PERCENTAGE_SCANNED_FROM_CACHE,
                PARTITIONS_SCANNED,
                PARTITIONS_TOTAL
            FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
            WHERE {where_str}
            ORDER BY START_TIME DESC
            LIMIT {limit}
        """

        df = manager.execute_query(acc, query)
        if df is not None and not df.empty:
            all_history.append(df)
    except Exception as e:
        st.warning(f"Could not fetch query history for {acc}: {e}")

if not all_history:
    st.info("No query history found for the selected filters.")
    st.stop()

history_df = pd.concat(all_history, ignore_index=True)

# Convert types
for col in ["DURATION_SECONDS", "BYTES_SCANNED", "ROWS_PRODUCED",
            "COMPILATION_SECONDS", "EXECUTION_SECONDS", "QUEUED_SECONDS",
            "PERCENTAGE_SCANNED_FROM_CACHE"]:
    if col in history_df.columns:
        history_df[col] = pd.to_numeric(history_df[col], errors="coerce")

if "START_TIME" in history_df.columns:
    history_df["START_TIME"] = pd.to_datetime(history_df["START_TIME"])

# ─── Overview ─────────────────────────────────────────────────────────────────

st.header("Overview")

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Queries", len(history_df))
m2.metric("Avg Duration (s)", f"{history_df['DURATION_SECONDS'].mean():.2f}" if "DURATION_SECONDS" in history_df.columns else "N/A")
m3.metric("Max Duration (s)", f"{history_df['DURATION_SECONDS'].max():.2f}" if "DURATION_SECONDS" in history_df.columns else "N/A")

if "EXECUTION_STATUS" in history_df.columns:
    failed = len(history_df[history_df["EXECUTION_STATUS"] != "SUCCESS"])
    m4.metric("Failed Queries", failed)
    m5.metric("Success Rate", f"{(1 - failed/len(history_df))*100:.1f}%")

# ─── Charts ───────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Distribution", "🐌 Slow Queries", "❌ Failed Queries", "📋 Full History"
])

with tab1:
    col1, col2 = st.columns(2)

    with col1:
        if "QUERY_TYPE" in history_df.columns:
            type_counts = history_df.groupby(["_ACCOUNT", "QUERY_TYPE"]).size().reset_index(name="Count")
            fig = px.bar(type_counts, x="QUERY_TYPE", y="Count", color="_ACCOUNT",
                         title="Queries by Type", barmode="group", height=400)
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "WAREHOUSE_NAME" in history_df.columns:
            wh_counts = history_df.groupby(["_ACCOUNT", "WAREHOUSE_NAME"]).size().reset_index(name="Count")
            fig = px.bar(wh_counts, x="WAREHOUSE_NAME", y="Count", color="_ACCOUNT",
                         title="Queries by Warehouse", barmode="group", height=400)
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

    # Timeline
    if "START_TIME" in history_df.columns:
        history_df["HOUR"] = history_df["START_TIME"].dt.floor("h")
        hourly = history_df.groupby(["_ACCOUNT", "HOUR"]).size().reset_index(name="Query Count")
        fig = px.line(hourly, x="HOUR", y="Query Count", color="_ACCOUNT",
                      title="Query Volume Over Time", height=400)
        st.plotly_chart(fig, use_container_width=True)

    # User activity
    if "USER_NAME" in history_df.columns:
        user_counts = history_df.groupby(["_ACCOUNT", "USER_NAME"]).size().reset_index(name="Count")
        user_counts = user_counts.sort_values("Count", ascending=False).head(20)
        fig = px.bar(user_counts, x="USER_NAME", y="Count", color="_ACCOUNT",
                     title="Top 20 Most Active Users", height=400)
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("🐌 Slowest Queries")
    if "DURATION_SECONDS" in history_df.columns:
        slow = history_df.nlargest(50, "DURATION_SECONDS")
        display_cols = ["_ACCOUNT", "QUERY_ID", "QUERY_TYPE", "USER_NAME",
                        "WAREHOUSE_NAME", "DURATION_SECONDS", "COMPILATION_SECONDS",
                        "EXECUTION_SECONDS", "QUEUED_SECONDS", "ROWS_PRODUCED",
                        "BYTES_SCANNED", "START_TIME"]
        available = [c for c in display_cols if c in slow.columns]
        st.dataframe(slow[available], use_container_width=True, height=500)

        # Duration distribution
        fig = px.histogram(history_df, x="DURATION_SECONDS", color="_ACCOUNT",
                           title="Query Duration Distribution", nbins=50, height=400)
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("❌ Failed Queries")
    if "EXECUTION_STATUS" in history_df.columns:
        failed_df = history_df[history_df["EXECUTION_STATUS"] != "SUCCESS"]
        if not failed_df.empty:
            display_cols = ["_ACCOUNT", "QUERY_ID", "QUERY_TYPE", "USER_NAME",
                            "EXECUTION_STATUS", "ERROR_CODE", "ERROR_MESSAGE",
                            "START_TIME", "QUERY_TEXT"]
            available = [c for c in display_cols if c in failed_df.columns]
            st.dataframe(failed_df[available], use_container_width=True, height=500)

            # Error distribution
            if "ERROR_CODE" in failed_df.columns:
                error_counts = failed_df["ERROR_CODE"].value_counts().head(10).reset_index()
                error_counts.columns = ["Error Code", "Count"]
                fig = px.bar(error_counts, x="Error Code", y="Count",
                             title="Top Error Codes", height=300)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("No failed queries! 🎉")

with tab4:
    st.subheader("📋 Full Query History")

    search = st.text_input("🔍 Search query text", key="query_search")
    filtered = history_df
    if search:
        filtered = filtered[filtered["QUERY_TEXT"].str.contains(search, case=False, na=False)]

    st.dataframe(filtered, use_container_width=True, height=600)

    # Download button
    csv = filtered.to_csv(index=False)
    st.download_button(
        label="📥 Download Query History CSV",
        data=csv,
        file_name="query_history.csv",
        mime="text/csv"
    )