"""
💰 Credit Consumption — Detailed credit analysis
   across all environments.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from snowflake_connector import SnowflakeConnectionManager
from theme import (
    inject_css, COLORS, CHART_COLORS,
    get_env_color, pwc_header, section_header,
)

# ─── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Credit Consumption · PwC",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# ─── Safe color lookup ────────────────────────────────────────────────────────

def c(key: str, fallback: str = "#888888") -> str:
    return COLORS.get(key, fallback)

# ─── Safe HTML builders ───────────────────────────────────────────────────────

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


def _panel(title: str) -> str:
    return (
        f'<div style="display:flex;align-items:center;'
        f'gap:10px;margin:18px 0 10px 0;">'
        f'<div style="height:3px;width:28px;'
        f'background:linear-gradient(90deg,'
        f'{c("pwc_orange")},{c("pwc_gold")});'
        f'border-radius:2px;flex-shrink:0;"></div>'
        f'<div style="font-size:0.65rem;font-weight:800;'
        f'text-transform:uppercase;letter-spacing:0.18em;'
        f'color:{c("text_muted")};">{title}</div>'
        f'<div style="flex:1;height:1px;'
        f'background:linear-gradient(90deg,'
        f'rgba(255,255,255,0.08),transparent);"></div>'
        f'</div>'
    )


def _alert_row(alert_type, acc, message, color) -> str:
    return (
        f'<div style="background:rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-left:4px solid {color};'
        f'border-radius:14px;padding:12px 16px;'
        f'margin-bottom:8px;'
        f'display:flex;align-items:center;gap:12px;">'
        f'<span style="font-size:0.8rem;font-weight:700;'
        f'white-space:nowrap;color:{color};">'
        f'{alert_type}</span>'
        f'<span style="font-size:0.72rem;font-weight:700;'
        f'color:{get_env_color(acc)};'
        f'background:{get_env_color(acc)}15;'
        f'border:1px solid {get_env_color(acc)}33;'
        f'padding:2px 8px;border-radius:8px;">'
        f'{acc}</span>'
        f'<span style="font-size:0.82rem;'
        f'color:{c("text_secondary")};">'
        f'{message}</span>'
        f'</div>'
    )


def _ok_banner(text: str) -> str:
    return (
        f'<div style="background:rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-left:4px solid {c("green")};'
        f'border-radius:14px;padding:14px 18px;'
        f'text-align:center;">'
        f'<span style="color:{c("green")};font-weight:600;">'
        f'{text}</span>'
        f'</div>'
    )


def _env_credit_card(acc, acc_total, acc_cost,
                      pct, env_color) -> str:
    bar_pct = min(pct, 100)
    return (
        f'<div style="background:linear-gradient('
        f'180deg,rgba(255,255,255,0.02),'
        f'rgba(255,255,255,0.00)),rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-top:3px solid {env_color};'
        f'border-radius:18px;padding:20px;'
        f'box-shadow:0 14px 28px rgba(0,0,0,0.16);">'
        # env name
        f'<div style="font-size:0.88rem;font-weight:800;'
        f'color:{env_color};margin-bottom:10px;">{acc}</div>'
        # credits
        f'<div style="font-family:JetBrains Mono,monospace;'
        f'font-size:1.8rem;font-weight:700;color:{env_color};">'
        f'{acc_total:,.0f}</div>'
        f'<div style="font-size:0.72rem;'
        f'color:{c("text_muted")};'
        f'text-transform:uppercase;margin-bottom:8px;">'
        f'Credits</div>'
        # cost
        f'<div style="font-size:1rem;font-weight:600;'
        f'color:{c("red")};">'
        f'${acc_cost:,.0f}</div>'
        f'<div style="font-size:0.72rem;'
        f'color:{c("text_muted")};margin-bottom:10px;">'
        f'estimated cost</div>'
        # progress bar
        f'<div style="height:8px;'
        f'background:{c("border")};'
        f'border-radius:4px;overflow:hidden;">'
        f'<div style="width:{bar_pct:.1f}%;height:100%;'
        f'background:{env_color};border-radius:4px;"></div>'
        f'</div>'
        f'<div style="font-size:0.72rem;'
        f'color:{c("text_muted")};margin-top:4px;">'
        f'{pct:.1f}% of total</div>'
        f'</div>'
    )


def _forecast_card(acc, recent_7d, credit_price,
                    proj_30d, proj_yearly,
                    avg_daily, trend, env_color) -> str:
    return (
        f'<div style="background:linear-gradient('
        f'180deg,rgba(255,255,255,0.02),'
        f'rgba(255,255,255,0.00)),rgba(19,26,36,0.9);'
        f'border:1px solid rgba(255,255,255,0.07);'
        f'border-top:3px solid {env_color};'
        f'border-radius:18px;padding:20px;'
        f'box-shadow:0 14px 28px rgba(0,0,0,0.16);">'
        # header
        f'<div style="display:flex;align-items:center;'
        f'gap:8px;margin-bottom:12px;">'
        f'<span style="font-size:0.88rem;font-weight:800;'
        f'color:{env_color};">{acc}</span>'
        f'<span style="font-size:1rem;">{trend}</span>'
        f'</div>'
        # grid
        f'<div style="display:grid;'
        f'grid-template-columns:1fr 1fr;gap:10px;">'
        # daily avg
        f'<div>'
        f'<div style="font-size:0.68rem;'
        f'color:{c("text_muted")};'
        f'text-transform:uppercase;margin-bottom:2px;">'
        f'Daily Avg</div>'
        f'<div style="font-family:JetBrains Mono,monospace;'
        f'font-size:1.1rem;font-weight:600;'
        f'color:{c("text_primary")};">'
        f'{recent_7d:,.1f}</div>'
        f'</div>'
        # daily cost
        f'<div>'
        f'<div style="font-size:0.68rem;'
        f'color:{c("text_muted")};'
        f'text-transform:uppercase;margin-bottom:2px;">'
        f'Daily Cost</div>'
        f'<div style="font-family:JetBrains Mono,monospace;'
        f'font-size:1.1rem;font-weight:600;'
        f'color:{c("red")};">'
        f'${recent_7d * credit_price:,.0f}</div>'
        f'</div>'
        # 30-day proj
        f'<div>'
        f'<div style="font-size:0.68rem;'
        f'color:{c("text_muted")};'
        f'text-transform:uppercase;margin-bottom:2px;">'
        f'30-Day Proj</div>'
        f'<div style="font-family:JetBrains Mono,monospace;'
        f'font-size:1.1rem;font-weight:600;'
        f'color:{c("pwc_orange")};">'
        f'${proj_30d * credit_price:,.0f}</div>'
        f'</div>'
        # annual proj
        f'<div>'
        f'<div style="font-size:0.68rem;'
        f'color:{c("text_muted")};'
        f'text-transform:uppercase;margin-bottom:2px;">'
        f'Annual Proj</div>'
        f'<div style="font-family:JetBrains Mono,monospace;'
        f'font-size:1.1rem;font-weight:600;'
        f'color:{c("red")};">'
        f'${proj_yearly * credit_price:,.0f}</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )


# ─── Manager + Sidebar ────────────────────────────────────────────────────────

manager   = SnowflakeConnectionManager()
connected = manager.get_connected_accounts()

with st.sidebar:
    st.markdown(
        f'<div style="padding:20px 16px 12px;'
        f'border-bottom:1px solid {c("border")};'
        f'margin-bottom:12px;">'
        f'<div style="font-size:1rem;font-weight:800;'
        f'color:{c("text_primary")};">💰 Credit Consumption</div>'
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

    selected_accounts = st.multiselect(
        "Filter Environments",
        connected,
        default=connected,
        key="credit_env_filter"
    )

    days_back = st.selectbox(
        "Time Range",
        [7, 14, 30, 60, 90],
        index=2,
        format_func=lambda x: f"Last {x} days"
    )

    credit_price = st.number_input(
        "Credit Price ($)",
        value=3.00,
        step=0.10,
        help="Approximate cost per Snowflake credit"
    )

    st.markdown("---")
    if st.button("🔄 Refresh", use_container_width=True,
                  key="credit_refresh"):
        st.cache_data.clear()
        st.rerun()

# ─── Header ───────────────────────────────────────────────────────────────────

pwc_header(
    "Credit Consumption",
    subtitle="Detailed credit analysis and cost "
             "forecasting across all environments"
)

if not selected_accounts:
    st.warning("Select at least one environment.")
    st.stop()

# top info bar
st.markdown(
    f'<div style="background:linear-gradient('
    f'180deg,rgba(255,255,255,0.02),'
    f'rgba(255,255,255,0.00)),rgba(19,26,36,0.9);'
    f'border:1px solid rgba(255,255,255,0.07);'
    f'border-radius:14px;padding:16px 24px;'
    f'margin-bottom:20px;'
    f'display:flex;align-items:center;'
    f'justify-content:space-between;">'
    f'<div>'
    f'<div style="font-size:1.1rem;font-weight:700;'
    f'color:{c("text_primary")};">'
    f'💰 Credit Consumption Analysis</div>'
    f'<div style="font-size:0.78rem;'
    f'color:{c("text_muted")};margin-top:2px;">'
    f'Monitoring {len(selected_accounts)} environment(s) '
    f'· Last {days_back} days</div>'
    f'</div>'
    f'<div style="text-align:right;">'
    f'<div style="font-size:0.7rem;color:{c("text_muted")};">'
    f'Credit Price</div>'
    f'<div style="font-size:1.1rem;font-weight:600;'
    f'color:{c("pwc_orange")};">'
    f'${credit_price:.2f}/credit</div>'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True
)

# ─── Data Fetchers ────────────────────────────────────────────────────────────

@st.cache_data(ttl=120, show_spinner="Loading credit data...")
def fetch_credit_data(_mgr_id, accounts, days):
    mgr = SnowflakeConnectionManager()
    summary_list  = []
    daily_list    = []
    hourly_list   = []
    warehouse_list= []

    for acc in accounts:
        try:
            df = mgr.execute_query(acc, f"""
                SELECT
                    SUM(CREDITS_USED)                AS TOTAL_CREDITS,
                    SUM(CREDITS_USED_COMPUTE)         AS COMPUTE_CREDITS,
                    SUM(CREDITS_USED_CLOUD_SERVICES)  AS CLOUD_CREDITS,
                    COUNT(DISTINCT WAREHOUSE_NAME)    AS WAREHOUSE_COUNT,
                    MIN(START_TIME)                   AS FIRST_USAGE,
                    MAX(END_TIME)                     AS LAST_USAGE
                FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
                WHERE START_TIME >= DATEADD('day',{-days},CURRENT_TIMESTAMP())
            """)
            if df is not None and not df.empty:
                summary_list.append(df)
        except Exception:
            pass

        try:
            df = mgr.execute_query(acc, f"""
                SELECT
                    START_TIME::DATE                  AS USAGE_DATE,
                    SUM(CREDITS_USED)                 AS DAILY_CREDITS,
                    SUM(CREDITS_USED_COMPUTE)          AS COMPUTE_CREDITS,
                    SUM(CREDITS_USED_CLOUD_SERVICES)   AS CLOUD_CREDITS
                FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
                WHERE START_TIME >= DATEADD('day',{-days},CURRENT_TIMESTAMP())
                GROUP BY USAGE_DATE
                ORDER BY USAGE_DATE
            """)
            if df is not None and not df.empty:
                df["USAGE_DATE"] = pd.to_datetime(
                    df["USAGE_DATE"])
                for col in ["DAILY_CREDITS",
                             "COMPUTE_CREDITS",
                             "CLOUD_CREDITS"]:
                    df[col] = pd.to_numeric(
                        df[col], errors="coerce")
                daily_list.append(df)
        except Exception:
            pass

        try:
            df = mgr.execute_query(acc, f"""
                SELECT
                    HOUR(START_TIME)    AS HOUR_OF_DAY,
                    DAYNAME(START_TIME) AS DAY_NAME,
                    SUM(CREDITS_USED)   AS CREDITS
                FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
                WHERE START_TIME >= DATEADD('day',-7,CURRENT_TIMESTAMP())
                GROUP BY HOUR_OF_DAY, DAY_NAME
                ORDER BY HOUR_OF_DAY
            """)
            if df is not None and not df.empty:
                df["CREDITS"] = pd.to_numeric(
                    df["CREDITS"], errors="coerce")
                hourly_list.append(df)
        except Exception:
            pass

        try:
            df = mgr.execute_query(acc, f"""
                SELECT
                    WAREHOUSE_NAME,
                    SUM(CREDITS_USED)                AS TOTAL_CREDITS,
                    SUM(CREDITS_USED_COMPUTE)         AS COMPUTE_CREDITS,
                    SUM(CREDITS_USED_CLOUD_SERVICES)  AS CLOUD_CREDITS,
                    COUNT(*)                          AS METERING_EVENTS,
                    AVG(CREDITS_USED)                 AS AVG_CREDITS_PER_EVENT
                FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
                WHERE START_TIME >= DATEADD('day',{-days},CURRENT_TIMESTAMP())
                GROUP BY WAREHOUSE_NAME
                ORDER BY TOTAL_CREDITS DESC
            """)
            if df is not None and not df.empty:
                for col in ["TOTAL_CREDITS","COMPUTE_CREDITS",
                             "CLOUD_CREDITS",
                             "AVG_CREDITS_PER_EVENT"]:
                    df[col] = pd.to_numeric(
                        df[col], errors="coerce")
                warehouse_list.append(df)
        except Exception:
            pass

    return {
        "summary": (
            pd.concat(summary_list, ignore_index=True)
            if summary_list else pd.DataFrame()),
        "daily": (
            pd.concat(daily_list, ignore_index=True)
            if daily_list else pd.DataFrame()),
        "hourly": (
            pd.concat(hourly_list, ignore_index=True)
            if hourly_list else pd.DataFrame()),
        "warehouse": (
            pd.concat(warehouse_list, ignore_index=True)
            if warehouse_list else pd.DataFrame()),
    }


with st.spinner("Loading credit data..."):
    data = fetch_credit_data(
        id(manager), tuple(selected_accounts), days_back)

# ═══════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════

st.markdown(_panel("💰 CREDIT SUMMARY"),
             unsafe_allow_html=True)

if data["summary"].empty:
    st.warning("No credit data available.")
    st.stop()

summary = data["summary"]

for col in ["TOTAL_CREDITS","COMPUTE_CREDITS",
             "CLOUD_CREDITS"]:
    if col in summary.columns:
        summary[col] = pd.to_numeric(
            summary[col], errors="coerce").fillna(0)

if "_ACCOUNT" in summary.columns:
    total_credits_series = summary.groupby(
        "_ACCOUNT")["TOTAL_CREDITS"].sum()
else:
    total_credits_series = pd.Series(
        {"(unknown)": float(
            summary["TOTAL_CREDITS"].sum()
            if "TOTAL_CREDITS" in summary.columns else 0)})

grand_total      = float(total_credits_series.sum())
total_cost       = grand_total * credit_price
avg_daily        = grand_total / days_back if days_back else 0
projected_monthly= avg_daily * 30
projected_cost   = projected_monthly * credit_price

k1, k2, k3, k4, k5, k6 = st.columns(6)
kpis = [
    ("💰", f"{grand_total:,.0f}",       "Total Credits",    c("pwc_orange")),
    ("💵", f"${total_cost:,.0f}",        "Estimated Cost",   c("red")),
    ("📅", f"{avg_daily:,.1f}",          "Daily Average",    c("blue")),
    ("📆", f"{projected_monthly:,.0f}",  "Proj Monthly",     c("purple")),
    ("💳", f"${projected_cost:,.0f}",    "Proj Cost/Mo",     c("red")),
    ("🌍", str(len(selected_accounts)),  "Environments",     c("cyan")),
]
for col, (ico, val, lbl, clr) in zip(
        [k1,k2,k3,k4,k5,k6], kpis):
    with col:
        st.markdown(_kpi(ico, val, lbl, clr),
                     unsafe_allow_html=True)

st.markdown('<div style="height:14px;"></div>',
             unsafe_allow_html=True)

st.markdown(_panel("PER-ENVIRONMENT CREDITS"),
             unsafe_allow_html=True)

env_cols = st.columns(max(1, len(selected_accounts)))
for i, acc in enumerate(selected_accounts):
    acc_total = float(total_credits_series.get(acc, 0))
    acc_cost  = acc_total * credit_price
    pct       = (acc_total / grand_total * 100
                  if grand_total > 0 else 0)
    env_color = get_env_color(acc)
    with env_cols[i]:
        st.markdown(
            _env_credit_card(acc, acc_total,
                              acc_cost, pct, env_color),
            unsafe_allow_html=True
        )

# ═══════════════════════════════════════════════════════
# DAILY TREND
# ═══════════════════════════════════════════════════════

st.markdown('<div style="height:8px;"></div>',
             unsafe_allow_html=True)
st.markdown(_panel("📈 DAILY CREDIT TREND"),
             unsafe_allow_html=True)

if not data["daily"].empty:
    daily     = data["daily"]
    color_map = {}
    if "_ACCOUNT" in daily.columns:
        color_map = {n: get_env_color(n)
                      for n in daily["_ACCOUNT"].unique()}

    tab1, tab2, tab3 = st.tabs([
        "📈 Trend Line",
        "📊 Stacked Area",
        "📉 Compute vs Cloud",
    ])

    with tab1:
        if "_ACCOUNT" in daily.columns:
            fig = px.line(
                daily,
                x="USAGE_DATE", y="DAILY_CREDITS",
                color="_ACCOUNT",
                color_discrete_map=color_map,
                height=400
            )
        else:
            fig = px.line(
                daily,
                x="USAGE_DATE", y="DAILY_CREDITS",
                height=400
            )
        fig.update_traces(line=dict(width=2.5))
        fig.update_layout(
            xaxis_title="", yaxis_title="Credits",
            legend_title_text="Environment")

        if "_ACCOUNT" in daily.columns:
            for acc in daily["_ACCOUNT"].unique():
                acc_data = daily[daily["_ACCOUNT"] == acc]
                avg = acc_data["DAILY_CREDITS"].mean()
                fig.add_hline(
                    y=avg, line_dash="dot",
                    opacity=0.4,
                    annotation_text=f"{acc} avg: {avg:.1f}",
                    annotation_position="top left",
                    line_color=color_map.get(
                        acc, c("blue")))

        st.plotly_chart(fig, use_container_width=True,
                         key="credit_trend_line")

    with tab2:
        if "_ACCOUNT" in daily.columns:
            fig2 = px.area(
                daily,
                x="USAGE_DATE", y="DAILY_CREDITS",
                color="_ACCOUNT",
                color_discrete_map=color_map,
                height=400
            )
        else:
            fig2 = px.area(
                daily,
                x="USAGE_DATE", y="DAILY_CREDITS",
                height=400
            )
        fig2.update_layout(
            xaxis_title="", yaxis_title="Credits",
            legend_title_text="Environment")
        st.plotly_chart(fig2, use_container_width=True,
                         key="credit_stacked_area")

    with tab3:
        fig3 = make_subplots(
            rows=1, cols=2,
            subplot_titles=(
                "Compute Credits",
                "Cloud Service Credits"))

        accs = (daily["_ACCOUNT"].unique()
                 if "_ACCOUNT" in daily.columns
                 else ["(all)"])

        for acc in accs:
            acc_data = (
                daily[daily["_ACCOUNT"] == acc]
                if "_ACCOUNT" in daily.columns
                else daily
            )
            clr = color_map.get(acc, c("blue"))
            fig3.add_trace(
                go.Scatter(
                    x=acc_data["USAGE_DATE"],
                    y=acc_data.get(
                        "COMPUTE_CREDITS",
                        acc_data["DAILY_CREDITS"]),
                    name=acc,
                    line=dict(color=clr, width=2),
                    showlegend=True
                ), row=1, col=1)
            fig3.add_trace(
                go.Scatter(
                    x=acc_data["USAGE_DATE"],
                    y=acc_data.get(
                        "CLOUD_CREDITS",
                        acc_data["DAILY_CREDITS"] * 0),
                    name=acc,
                    line=dict(color=clr, width=2,
                               dash="dot"),
                    showlegend=False
                ), row=1, col=2)

        fig3.update_layout(
            height=400, legend_title_text="")
        st.plotly_chart(fig3, use_container_width=True,
                         key="credit_compute_vs_cloud")

    with st.expander("📋 Daily Breakdown Table"):
        if "_ACCOUNT" in daily.columns:
            try:
                pivot = daily.pivot_table(
                    index="USAGE_DATE",
                    columns="_ACCOUNT",
                    values="DAILY_CREDITS",
                    aggfunc="sum"
                ).reset_index()
                pivot["USAGE_DATE"] = (
                    pivot["USAGE_DATE"]
                    .dt.strftime("%Y-%m-%d"))
                accs_in_pivot = [
                    a for a in selected_accounts
                    if a in pivot.columns]
                if accs_in_pivot:
                    pivot["Total"] = pivot[
                        accs_in_pivot].sum(axis=1)
                    pivot["Cost ($)"] = (
                        pivot["Total"] * credit_price)
                st.dataframe(
                    pivot.sort_values(
                        "USAGE_DATE", ascending=False),
                    use_container_width=True,
                    height=400)
                st.download_button(
                    "📥 Download Daily Data",
                    pivot.to_csv(index=False),
                    "daily_credits.csv",
                    "text/csv",
                    key="dl_daily"
                )
            except Exception:
                st.dataframe(daily,
                              use_container_width=True,
                              height=400)
        else:
            st.dataframe(daily,
                          use_container_width=True,
                          height=400)

# ═══════════════════════════════════════════════════════
# WAREHOUSE BREAKDOWN
# ═══════════════════════════════════════════════════════

st.markdown('<div style="height:8px;"></div>',
             unsafe_allow_html=True)
st.markdown(_panel("🏭 WAREHOUSE-LEVEL BREAKDOWN"),
             unsafe_allow_html=True)

if not data["warehouse"].empty:
    wh_data = data["warehouse"]

    tab_wh1, tab_wh2, tab_wh3 = st.tabs([
        "📊 By Environment",
        "🏆 Top Consumers",
        "📋 Full Table",
    ])

    with tab_wh1:
        for acc in selected_accounts:
            if "_ACCOUNT" not in wh_data.columns:
                acc_wh = wh_data
            else:
                acc_wh = wh_data[
                    wh_data["_ACCOUNT"] == acc
                ].sort_values(
                    "TOTAL_CREDITS", ascending=False)

            if not acc_wh.empty:
                env_color = get_env_color(acc)

                st.markdown(
                    f'<div style="font-size:0.88rem;'
                    f'font-weight:800;color:{env_color};'
                    f'margin:10px 0 6px 0;">'
                    f'{acc} — {len(acc_wh)} warehouses · '
                    f'{acc_wh["TOTAL_CREDITS"].sum():,.0f}'
                    f' total credits</div>',
                    unsafe_allow_html=True
                )

                fig_wh = px.bar(
                    acc_wh,
                    x="WAREHOUSE_NAME",
                    y=["COMPUTE_CREDITS","CLOUD_CREDITS"],
                    color_discrete_sequence=[
                        env_color, c("purple")],
                    barmode="stack", height=300)
                fig_wh.update_layout(
                    xaxis_title="",
                    yaxis_title="Credits",
                    legend_title_text="",
                    xaxis_tickangle=-45)
                st.plotly_chart(
                    fig_wh, use_container_width=True,
                    key=f"wh_bar_{acc}")

    with tab_wh2:
        top_wh    = wh_data.nlargest(15, "TOTAL_CREDITS").copy()
        top_wh["COST"] = top_wh["TOTAL_CREDITS"] * credit_price

        if "_ACCOUNT" in top_wh.columns:
            cmap2 = {n: get_env_color(n)
                      for n in top_wh["_ACCOUNT"].unique()}
            fig_top = px.bar(
                top_wh,
                x="WAREHOUSE_NAME",
                y="TOTAL_CREDITS",
                color="_ACCOUNT",
                color_discrete_map=cmap2,
                height=400,
                text=top_wh["TOTAL_CREDITS"].apply(
                    lambda x: f"{x:,.0f}")
            )
        else:
            fig_top = px.bar(
                top_wh,
                x="WAREHOUSE_NAME",
                y="TOTAL_CREDITS",
                height=400,
                text=top_wh["TOTAL_CREDITS"].apply(
                    lambda x: f"{x:,.0f}")
            )

        fig_top.update_traces(textposition="outside")
        fig_top.update_layout(
            xaxis_title="", yaxis_title="Credits",
            xaxis_tickangle=-45,
            legend_title_text="Environment")
        st.plotly_chart(fig_top, use_container_width=True,
                         key="wh_top_bar")

        path_cols = (
            ["_ACCOUNT","WAREHOUSE_NAME"]
            if "_ACCOUNT" in wh_data.columns
            else ["WAREHOUSE_NAME"])
        fig_tree = px.treemap(
            wh_data, path=path_cols,
            values="TOTAL_CREDITS",
            color="TOTAL_CREDITS",
            color_continuous_scale=[
                c("bg_elevated","#1b2431"),
                c("pwc_orange"),
                c("red")],
            height=450)
        fig_tree.update_layout(
            margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_tree, use_container_width=True,
                         key="wh_treemap")

    with tab_wh3:
        wh_display = wh_data.copy()
        wh_display["COST ($)"] = (
            wh_display["TOTAL_CREDITS"] * credit_price)
        wh_display = wh_display.sort_values(
            "TOTAL_CREDITS", ascending=False)

        display_cols = [col for col in [
            "_ACCOUNT","WAREHOUSE_NAME","TOTAL_CREDITS",
            "COMPUTE_CREDITS","CLOUD_CREDITS","COST ($)",
            "METERING_EVENTS","AVG_CREDITS_PER_EVENT"
        ] if col in wh_display.columns]

        rename_map = {
            "_ACCOUNT":              "Environment",
            "WAREHOUSE_NAME":        "Warehouse",
            "TOTAL_CREDITS":         "Total Credits",
            "COMPUTE_CREDITS":       "Compute",
            "CLOUD_CREDITS":         "Cloud Services",
            "METERING_EVENTS":       "Events",
            "AVG_CREDITS_PER_EVENT": "Avg/Event",
        }
        st.dataframe(
            wh_display[display_cols].rename(
                columns=rename_map),
            use_container_width=True, height=500)
        st.download_button(
            "📥 Download Warehouse Data",
            wh_display.to_csv(index=False),
            "warehouse_credits.csv",
            "text/csv",
            key="dl_wh"
        )

# ═══════════════════════════════════════════════════════
# HOURLY HEATMAP
# ═══════════════════════════════════════════════════════

st.markdown('<div style="height:8px;"></div>',
             unsafe_allow_html=True)
st.markdown(_panel("🕐 USAGE PATTERN HEATMAP (LAST 7 DAYS)"),
             unsafe_allow_html=True)

if not data["hourly"].empty:
    hourly    = data["hourly"]
    day_order = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

    for acc in selected_accounts:
        if "_ACCOUNT" in hourly.columns:
            acc_hourly = hourly[hourly["_ACCOUNT"] == acc]
        else:
            acc_hourly = hourly

        if not acc_hourly.empty:
            env_color = get_env_color(acc)
            st.markdown(
                f'<div style="font-size:0.88rem;'
                f'font-weight:800;color:{env_color};'
                f'margin:8px 0 4px 0;">{acc}</div>',
                unsafe_allow_html=True
            )

            pivot_h = acc_hourly.pivot_table(
                index="DAY_NAME",
                columns="HOUR_OF_DAY",
                values="CREDITS",
                aggfunc="sum"
            ).reindex(day_order)

            fig_h = px.imshow(
                pivot_h,
                labels=dict(
                    x="Hour of Day",
                    y="Day",
                    color="Credits"),
                color_continuous_scale=[
                    c("bg_primary","#07090d"),
                    c("pwc_orange"),
                    c("red")],
                height=280, aspect="auto"
            )
            fig_h.update_layout(
                xaxis=dict(dtick=1),
                margin=dict(l=10,r=10,t=10,b=10))
            st.plotly_chart(fig_h,
                             use_container_width=True,
                             key=f"heatmap_{acc}")
else:
    st.info("Hourly pattern data not available.")

# ═══════════════════════════════════════════════════════
# COST FORECAST
# ═══════════════════════════════════════════════════════

st.markdown('<div style="height:8px;"></div>',
             unsafe_allow_html=True)
st.markdown(_panel("🔮 COST PROJECTION"),
             unsafe_allow_html=True)

if not data["daily"].empty:
    daily = data["daily"]

    forecast_cols = st.columns(
        max(1, len(selected_accounts)))

    for i, acc in enumerate(selected_accounts):
        if "_ACCOUNT" in daily.columns:
            acc_daily = daily[daily["_ACCOUNT"] == acc]
        else:
            acc_daily = daily

        if not acc_daily.empty:
            avg_daily_c  = acc_daily["DAILY_CREDITS"].mean()
            recent_7d    = (
                acc_daily.tail(7)["DAILY_CREDITS"].mean()
                if len(acc_daily) >= 7 else avg_daily_c)
            trend = (
                "📈" if recent_7d > avg_daily_c
                else "📉" if recent_7d < avg_daily_c
                else "➡️")
            proj_30d    = recent_7d * 30
            proj_yearly = recent_7d * 365
            env_color   = get_env_color(acc)

            with forecast_cols[i]:
                st.markdown(
                    _forecast_card(
                        acc, recent_7d, credit_price,
                        proj_30d, proj_yearly,
                        avg_daily_c, trend, env_color
                    ),
                    unsafe_allow_html=True
                )

# ═══════════════════════════════════════════════════════
# ANOMALY DETECTION
# ═══════════════════════════════════════════════════════

st.markdown('<div style="height:8px;"></div>',
             unsafe_allow_html=True)
st.markdown(_panel("⚠️ CREDIT ANOMALIES & ALERTS"),
             unsafe_allow_html=True)

if not data["daily"].empty:
    daily  = data["daily"]
    alerts = []

    for acc in selected_accounts:
        if "_ACCOUNT" in daily.columns:
            acc_daily = daily[daily["_ACCOUNT"] == acc]
        else:
            acc_daily = daily

        if len(acc_daily) >= 7:
            mean   = acc_daily["DAILY_CREDITS"].mean()
            std    = acc_daily["DAILY_CREDITS"].std()
            recent = acc_daily.tail(1)["DAILY_CREDITS"].values[0]

            if std > 0 and recent > mean + 2 * std:
                alerts.append({
                    "env":     acc,
                    "type":    "🔴 CRITICAL",
                    "message": (
                        f"Yesterday's usage "
                        f"({recent:,.0f} credits) is "
                        f"{((recent-mean)/mean*100):.0f}% "
                        f"above average ({mean:,.0f})"),
                    "color": c("red"),
                })
            elif std > 0 and recent > mean + std:
                alerts.append({
                    "env":     acc,
                    "type":    "🟡 WARNING",
                    "message": (
                        f"Yesterday's usage "
                        f"({recent:,.0f} credits) is "
                        f"above normal range "
                        f"({mean:,.0f} avg)"),
                    "color": c("pwc_orange"),
                })

            acc_copy = acc_daily.copy()
            acc_copy["DOW"] = (
                acc_copy["USAGE_DATE"].dt.dayofweek)
            weekend = acc_copy[acc_copy["DOW"] >= 5]
            if (not weekend.empty
                    and weekend["DAILY_CREDITS"].mean()
                    > mean * 0.5):
                alerts.append({
                    "env":     acc,
                    "type":    "🟡 INFO",
                    "message": "Significant weekend "
                               "credit usage detected",
                    "color": c("yellow"),
                })

    if alerts:
        for alert in alerts:
            st.markdown(
                _alert_row(
                    alert["type"],
                    alert["env"],
                    alert["message"],
                    alert["color"]
                ),
                unsafe_allow_html=True
            )
    else:
        st.markdown(
            _ok_banner(
                "✅ No anomalies detected — "
                "credit usage is within normal range"
            ),
            unsafe_allow_html=True
        )

# ─── Footer ───────────────────────────────────────────────────────────────────

st.markdown(
    f'<div style="text-align:center;padding:28px 0 10px;'
    f'border-top:1px solid {c("border")};margin-top:32px;">'
    f'<div style="font-size:0.78rem;font-weight:800;'
    f'color:{c("text_primary")};">'
    f'💰 Credit Consumption'
    f'&nbsp;·&nbsp;'
    f'<span style="color:{c("pwc_orange")};font-weight:800;'
    f'font-size:0.68rem;text-transform:uppercase;'
    f'letter-spacing:0.12em;">'
    f'Powered By PwC Data &amp; AI</span>'
    f'</div>'
    f'<div style="margin-top:4px;font-size:0.66rem;'
    f'color:{c("text_dim","#5f6b7c")};">'
    f'{len(selected_accounts)} environment(s) · '
    f'Last {days_back} days · '
    f'${credit_price:.2f}/credit'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True
)