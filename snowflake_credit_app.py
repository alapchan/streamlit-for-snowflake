# snowflake_credit_app_enhanced.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from math import ceil
from datetime import datetime, timedelta

st.set_page_config(page_title="PwC's Snowflake Credit Explorer — Enhanced", layout="wide")

# -------------------------
# Reference excerpt shown in UI
# -------------------------
st.sidebar.markdown("**Reference (from attached CreditConsumptionTable.pdf):**")
st.sidebar.caption(
    "“Snowflake bills for Compute using purchasable credits... Virtual Warehouses and Compute Nodes ... use Snowflake Credits at certain rates...”"
)
st.sidebar.caption("“Cloud Services ... You will be charged **4.4 Credits per hour** of Cloud Services use.”")

# -------------------------
# Rate tables (seeded from PDF)
# Add or replace values with full tables as needed.
# -------------------------
STANDARD_WAREHOUSE_RATES = {"XS":1,"S":2,"M":4,"L":8,"XL":16,"2XL":32,"3XL":64,"4XL":128,"5XL":256,"6XL":512}
GEN2_RATES = {
    "AWS":{"XS":1.35,"S":2.7,"M":5.4,"L":10.8,"XL":21.6,"2XL":43.2,"3XL":86.4,"4XL":172.8},
    "Azure":{"XS":1.25,"S":2.5,"M":5.0,"L":10.0,"XL":20.0,"2XL":40.0,"3XL":80.0,"4XL":160.0},
    "GCP":{"XS":1.35,"S":2.7,"M":5.4,"L":10.8,"XL":21.6,"2XL":43.2,"3XL":86.4,"4XL":172.8}
}
INTERACTIVE_RATES = {"XS":0.6,"S":1.2,"M":2.4,"L":4.8,"XL":9.6,"2XL":19.2,"3XL":38.4,"4XL":76.8}
CLOUD_SERVICES_CREDITS_PER_HOUR = 4.4

# -------------------------
# On Demand Credit Pricing: AWS regions from your PDF (sample)
# Each tuple key: (CloudProvider, Region)
# Values: dict of edition -> USD per Credit
# -------------------------
ON_DEMAND_PRICING = {
    ("AWS","US East (Northern Virginia)"): {"Standard":2.00,"Enterprise":3.00,"Business Critical":4.00,"VPS":6.00},
    ("AWS","US West (Oregon)"): {"Standard":2.00,"Enterprise":3.00,"Business Critical":4.00,"VPS":6.00},
    ("AWS","EU Dublin"): {"Standard":2.60,"Enterprise":3.90,"Business Critical":5.20,"VPS":7.80},
    ("AWS","EU Frankfurt"): {"Standard":2.60,"Enterprise":3.90,"Business Critical":5.20,"VPS":7.80},
    ("AWS","AP Sydney"): {"Standard":2.75,"Enterprise":4.05,"Business Critical":5.50,"VPS":8.25},
    ("AWS","AP Singapore"): {"Standard":2.50,"Enterprise":3.70,"Business Critical":5.00,"VPS":7.50},
    ("AWS","Canada Central"): {"Standard":2.25,"Enterprise":3.50,"Business Critical":4.50,"VPS":6.75},
    ("AWS","US East 2 (Ohio)"): {"Standard":2.00,"Enterprise":3.00,"Business Critical":4.00,"VPS":6.00},
    ("AWS","AP Northeast 1 (Tokyo)"): {"Standard":2.85,"Enterprise":4.30,"Business Critical":5.70,"VPS":8.55},
    ("AWS","AP Mumbai"): {"Standard":2.00,"Enterprise":3.00,"Business Critical":4.00,"VPS":6.00},
    ("AWS","Europe (London)"): {"Standard":2.70,"Enterprise":4.00,"Business Critical":5.40,"VPS":8.10},
    ("AWS","Asia Pacific (Seoul)"): {"Standard":2.75,"Enterprise":4.05,"Business Critical":5.50,"VPS":8.25},
    ("AWS","Europe (Stockholm)"): {"Standard":2.40,"Enterprise":3.60,"Business Critical":4.80,"VPS":7.20},
    ("AWS","Asia Pacific (Osaka)"): {"Standard":2.85,"Enterprise":4.30,"Business Critical":5.70,"VPS":8.55},
    ("AWS","South America East 1 (São Paulo)"): {"Standard":3.10,"Enterprise":4.65,"Business Critical":6.20,"VPS":9.30},
    ("AWS","EU (Paris)"): {"Standard":2.60,"Enterprise":3.90,"Business Critical":5.20,"VPS":7.80},
    ("AWS","Asia Pacific (Jakarta)"): {"Standard":2.50,"Enterprise":3.70,"Business Critical":5.00,"VPS":7.50},
    ("AWS","EU (Zurich)"): {"Standard":3.10,"Enterprise":4.65,"Business Critical":6.20,"VPS":9.30},
    ("AWS","Africa (Cape Town)"): {"Standard":2.80,"Enterprise":4.20,"Business Critical":5.60,"VPS":8.40},
    ("AWS","Middle East (UAE)"): {"Standard":2.70,"Enterprise":4.00,"Business Critical":5.40,"VPS":8.10},
    # Gov and special regions (Business Critical/VPS prices shown in PDF)
    ("AWS","US Gov West 1"): {"Standard":None,"Enterprise":None,"Business Critical":5.60,"VPS":8.40},
    ("AWS","US Gov East 1 (Fedramp High Plus)"): {"Standard":None,"Enterprise":None,"Business Critical":5.60,"VPS":8.40},
    ("AWS","US Gov West 1 (DoD)"): {"Standard":None,"Enterprise":None,"Business Critical":5.60,"VPS":8.40},
    ("AWS","US West (Commercial Gov - Oregon)"): {"Standard":None,"Enterprise":None,"Business Critical":4.80,"VPS":7.20},
    # Add more AWS regions here if needed
}

# -------------------------
# Storage pricing sample (per TB / month) - seeded from PDF where available
# -------------------------
STORAGE_PRICING_TB = {
    ("AWS","US East (Northern Virginia)"): 23.00,
    ("AWS","US West (Oregon)"): 23.00,
    ("AWS","EU Dublin"): 23.00,
    ("AWS","EU Frankfurt"): 24.50,
    ("AWS","AP Sydney"): 25.00,
    ("AWS","AP Singapore"): 25.00,
    ("AWS","Canada Central"): 25.00,
    ("AWS","US East 2 (Ohio)"): 23.00,
    ("AWS","AP Northeast 1 (Tokyo)"): 25.00,
    ("AWS","AP Mumbai"): 23.00,
    ("AWS","Europe (London)"): 24.00,
    ("AWS","Asia Pacific (Seoul)"): 25.00,
    ("AWS","Europe (Stockholm)"): 23.00,
    ("AWS","Asia Pacific (Osaka)"): 25.00,
    ("AWS","South America East 1 (São Paulo)"): 40.50,
    ("AWS","EU (Paris)"): 24.00,
    ("AWS","Asia Pacific (Jakarta)"): 25.00,
    ("AWS","EU (Zurich)"): 26.95,
    ("AWS","Africa (Cape Town)"): 2.80 * 10,  # placeholder scaled (replace with exact)
    ("AWS","Middle East (UAE)"): 2.70 * 10,    # placeholder scaled (replace with exact)
}

# -------------------------
# AI sample rates (credits per 1M tokens)
# -------------------------
AI_FEATURES = {
    "openai-gpt-4.1": {"input_per_1M":1.00,"output_per_1M":4.00},
    "claude-4-opus": {"input_per_1M":7.50,"output_per_1M":37.50},
    "gemini-3-pro": {"input_per_1M":1.00,"output_per_1M":6.00}
}

# -------------------------
# Helper functions
# -------------------------
def get_compute_credits_per_hour(provider, family, size):
    if family == "Standard":
        return STANDARD_WAREHOUSE_RATES.get(size, 0)
    if family == "Gen2":
        return GEN2_RATES.get(provider, {}).get(size, 0)
    if family == "Interactive":
        return INTERACTIVE_RATES.get(size, 0)
    if family == "Snowpark Optimized":
        # default MEMORY_1X baseline
        sp = {"XS":1.0,"S":2.0,"M":4.0,"L":8.0,"XL":16.0,"2XL":32.0,"3XL":64.0,"4XL":128.0}
        return sp.get(size, 0)
    return 0

def get_on_demand_price(provider, region, edition):
    return ON_DEMAND_PRICING.get((provider, region), {}).get(edition, None)

def get_storage_price(provider, region):
    return STORAGE_PRICING_TB.get((provider, region), None)

# per-day bucket helper
def split_into_days(start_dt, total_seconds):
    days = []
    remaining = total_seconds
    cur = start_dt
    while remaining > 0:
        # seconds until midnight
        end_of_day = datetime(cur.year, cur.month, cur.day) + timedelta(days=1)
        sec_today = int((end_of_day - cur).total_seconds())
        take = min(sec_today, remaining)
        days.append((cur.date(), take))
        remaining -= take
        cur = end_of_day
    return days

# -------------------------
# UI inputs
# -------------------------
st.sidebar.header("Scenario inputs")
cloud_provider = st.sidebar.selectbox("Cloud Provider", ["AWS","Azure","GCP"])
# show all AWS regions added above if AWS selected
if cloud_provider == "AWS":
    region_options = sorted({k[1] for k in ON_DEMAND_PRICING.keys() if k[0]=="AWS"})
else:
    # fallback sample regions
    region_options = ["US East (Northern Virginia)","EU Dublin","East US 2 (Virginia)","US Central 1 (Iowa)"]
region = st.sidebar.selectbox("Region", region_options)
edition = st.sidebar.selectbox("Edition", ["Standard","Enterprise","Business Critical","VPS"])
warehouse_family = st.sidebar.selectbox("Warehouse Family", ["Standard","Gen2","Snowpark Optimized","Interactive"])
size = st.sidebar.selectbox("Warehouse Size", ["XS","S","M","L","XL","2XL","3XL","4XL","5XL","6XL"])
clusters = st.sidebar.number_input("Number of running clusters", min_value=1, max_value=50, value=1, step=1)
# allow start time and duration to simulate daily buckets
start_time = st.sidebar.datetime_input("Start time (for daily adjustment simulation)", value=datetime.utcnow())
duration_hours = st.sidebar.number_input("Total run duration (hours)", min_value=0.0, value=1.0, step=0.25)
simulate_start_resume = st.sidebar.checkbox("Apply start/resume minimum-charge rules", value=True)

st.sidebar.markdown("---")
use_serverless = st.sidebar.checkbox("Include Serverless feature", value=False)
serverless_compute_hours = st.sidebar.number_input("Serverless compute-hours", min_value=0.0, value=0.0, step=0.25)
use_ai = st.sidebar.checkbox("Include AI feature", value=False)
ai_model = st.sidebar.selectbox("AI model", list(AI_FEATURES.keys()))
ai_input_tokens = st.sidebar.number_input("AI input tokens (tokens)", min_value=0.0, value=0.0, step=100.0)
ai_output_tokens = st.sidebar.number_input("AI output tokens (tokens)", min_value=0.0, value=0.0, step=100.0)

storage_tb = st.sidebar.number_input("Storage (TB)", min_value=0.0, value=0.0, step=0.1)
use_data_transfer = st.sidebar.checkbox("Include Data Transfer", value=False)
dt_tb = st.sidebar.number_input("Data transfer (TB)", min_value=0.0, value=0.0, step=0.1)
dt_destination = st.sidebar.selectbox("Data transfer destination", ["Same region","Same provider different region","Internet / different cloud"])

# -------------------------
# Core calculation
# -------------------------
# compute credits per hour for selected warehouse
credits_per_hour = get_compute_credits_per_hour(cloud_provider, warehouse_family, size)
# convert to credits per second
credits_per_second = credits_per_hour / 3600.0

# total seconds requested
total_seconds = int(duration_hours * 3600)

# apply minimum start/resume rules: define minimum seconds per start
if simulate_start_resume:
    if warehouse_family == "Interactive":
        min_seconds_per_start = 3600  # 60 minutes
    elif warehouse_family in ["Snowpark Optimized"]:
        min_seconds_per_start = 60
    else:
        min_seconds_per_start = 60
else:
    min_seconds_per_start = 0

# For simplicity assume single start event at start_time; if duration < min_seconds, charge min_seconds
billed_seconds = total_seconds
if total_seconds > 0 and total_seconds < min_seconds_per_start:
    billed_seconds = min_seconds_per_start

# compute credits for compute
compute_credits = credits_per_second * billed_seconds * clusters

# Cloud Services: compute per-day buckets and apply 10% rule per day
# Cloud services credits are 4.4 credits per hour => per second:
cloud_services_per_second = CLOUD_SERVICES_CREDITS_PER_HOUR / 3600.0

# split into days
day_buckets = split_into_days(start_time, billed_seconds) if billed_seconds>0 else []
cloud_services_credits = 0.0
vw_credits_total = 0.0
# compute per-day
for day, seconds_in_day in day_buckets:
    day_vw_credits = credits_per_second * seconds_in_day * clusters
    day_cloud = cloud_services_per_second * seconds_in_day
    # apply adjustment: if daily cloud services <= 10% of daily vw credits -> waived
    if day_vw_credits > 0 and day_cloud <= 0.10 * day_vw_credits:
        day_cloud = 0.0
    cloud_services_credits += day_cloud
    vw_credits_total += day_vw_credits

# Serverless credits (assume serverless_compute_hours billed at 1 credit per compute-hour baseline unless otherwise)
serverless_credits = serverless_compute_hours * 1.0 if use_serverless else 0.0

# AI credits
ai_credits = 0.0
if use_ai and ai_model in AI_FEATURES:
    model = AI_FEATURES[ai_model]
    ai_credits = (model["input_per_1M"] * (ai_input_tokens / 1_000_000.0)) + (model["output_per_1M"] * (ai_output_tokens / 1_000_000.0))

# Storage cost USD and credits
storage_cost_usd = 23
storage_credits = 0.0
storage_price = get_storage_price(cloud_provider, region)
if storage_tb > 0 and storage_price:
    # monthly cost; convert to pro-rated for duration_hours (approx)
    months_fraction = max(duration_hours / (24*30), 1/720.0)  # avoid zero; assume at least 1 hour pro-rate
    storage_cost_usd = storage_tb * storage_price * months_fraction
    credit_price = get_on_demand_price(cloud_provider, region, edition) or 2.0
    storage_credits = storage_cost_usd / credit_price

# Data transfer cost USD and credits (simple mapping; extend with full table)
def get_data_transfer_cost(provider, region, dest, tb):
    # sample conservative defaults; replace with full table if available
    if dest == "Same region":
        per_tb = 0.0
    elif dest == "Same provider different region":
        per_tb = 20.0
    else:
        per_tb = 90.0
    return per_tb * tb

data_transfer_cost_usd = get_data_transfer_cost(cloud_provider, region, dt_destination, dt_tb) if use_data_transfer else 0.0
data_transfer_credits = 0.0
if data_transfer_cost_usd > 0:
    credit_price = get_on_demand_price(cloud_provider, region, edition) or 2.0
    data_transfer_credits = data_transfer_cost_usd / credit_price

# totals
total_credits = compute_credits + cloud_services_credits + serverless_credits + ai_credits + storage_credits + data_transfer_credits
credit_price = get_on_demand_price(cloud_provider, region, edition) or 2.0
estimated_usd = total_credits * credit_price

# -------------------------
# Output UI
# -------------------------
st.title("Snowflake Credit Explorer — Enhanced")
st.markdown("Interactive scenario explorer with corrected billing math and advanced visuals.")

left, right = st.columns([2,1])

with left:
    st.subheader("Scenario summary")
    st.markdown(f"**Provider:** {cloud_provider} • **Region:** {region} • **Edition:** {edition}")
    st.markdown(f"**Warehouse:** {warehouse_family} {size} • **Clusters:** {clusters} • **Requested hours:** {duration_hours:.2f}h • **Billed seconds:** {billed_seconds}s")
    st.metric("Total Credits", f"{total_credits:,.4f}")
    st.metric("Estimated USD (On Demand)", f"${estimated_usd:,.2f}")

    # breakdown table
    breakdown = pd.DataFrame([
        {"Category":"Compute","Credits":compute_credits},
        {"Category":"Cloud Services","Credits":cloud_services_credits},
        {"Category":"Serverless","Credits":serverless_credits},
        {"Category":"AI","Credits":ai_credits},
        {"Category":"Storage","Credits":storage_credits},
        {"Category":"Data Transfer","Credits":data_transfer_credits}
    ])
    st.dataframe(breakdown.style.format({"Credits":"{:.6f}"}), height=260)

    # Plotly stacked bar
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Compute', x=['Credits'], y=[compute_credits]))
    fig.add_trace(go.Bar(name='Cloud Services', x=['Credits'], y=[cloud_services_credits]))
    fig.add_trace(go.Bar(name='Serverless', x=['Credits'], y=[serverless_credits]))
    fig.add_trace(go.Bar(name='AI', x=['Credits'], y=[ai_credits]))
    fig.add_trace(go.Bar(name='Storage', x=['Credits'], y=[storage_credits]))
    fig.add_trace(go.Bar(name='Data Transfer', x=['Credits'], y=[data_transfer_credits]))
    fig.update_layout(barmode='stack', title_text='Credits by Category', height=420)
    st.plotly_chart(fig, use_container_width=True)

    # donut chart
    fig2 = px.pie(breakdown, names='Category', values='Credits', title='Credits share', hole=0.45)
    st.plotly_chart(fig2, use_container_width=True)

with right:
    st.subheader("USD details")
    st.write(f"**Credit price used:** ${credit_price:.2f} per Credit")
    st.write(f"**Compute credits:** {compute_credits:,.4f}")
    st.write(f"**Cloud Services credits:** {cloud_services_credits:,.4f}")
    st.write(f"**Storage cost (USD, pro-rated):** ${storage_cost_usd:,.2f}")
    st.write(f"**Data transfer cost (USD):** ${data_transfer_cost_usd:,.2f}")
    st.write("---")
    st.write("**AI details**")
    st.write(f"AI model: {ai_model} • Input tokens: {ai_input_tokens:,} • Output tokens: {ai_output_tokens:,}")
    st.write(f"AI credits: {ai_credits:,.6f}")

# Time-series simulation (per-minute aggregation) for visualization of daily adjustment
if billed_seconds > 0:
    # build per-minute series
    times = []
    compute_series = []
    cloud_series = []
    cur = start_time
    remaining = billed_seconds
    while remaining > 0:
        step = min(60, remaining)
        times.append(cur)
        compute_series.append(credits_per_second * step * clusters)
        cloud_series.append(cloud_services_per_second * step)
        remaining -= step
        cur = cur + timedelta(seconds=step)
    df_ts = pd.DataFrame({"time": times, "compute_credits": compute_series, "cloud_credits": cloud_series})
    df_ts['cum_compute'] = df_ts['compute_credits'].cumsum()
    df_ts['cum_cloud'] = df_ts['cloud_credits'].cumsum()

    fig_ts = go.Figure()
    fig_ts.add_trace(go.Scatter(x=df_ts['time'], y=df_ts['cum_compute'], name='Cumulative Compute Credits'))
    fig_ts.add_trace(go.Scatter(x=df_ts['time'], y=df_ts['cum_cloud'], name='Cumulative Cloud Credits'))
    fig_ts.update_layout(title="Cumulative credits over time", xaxis_title="Time", yaxis_title="Credits", height=420)
    st.plotly_chart(fig_ts, use_container_width=True)

st.markdown("---")
st.caption("This enhanced app includes corrected billing math and AWS regions from your PDF. Replace seeded tables with the full PDF tables for complete coverage.")
