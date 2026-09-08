"""
Utility functions with Grafana theme integration.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from theme import inject_grafana_css, COLORS, CHART_COLORS, get_env_color, grafana_panel


def format_bytes(size_bytes: float) -> str:
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {units[i]}"


def display_connection_sidebar():
    from snowflake_connector import SnowflakeConnectionManager
    manager = SnowflakeConnectionManager()
    connected = manager.get_connected_accounts()

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"""
    <div style="font-size:0.75rem; color:{COLORS['text_muted']}; text-transform:uppercase;
         letter-spacing:1px; margin-bottom:8px;">Connected Accounts</div>
    """, unsafe_allow_html=True)

    if connected:
        for acc in connected:
            color = get_env_color(acc)
            st.sidebar.markdown(
                f'<span style="color:{color}; font-weight:500;">● {acc}</span>',
                unsafe_allow_html=True
            )
    else:
        st.sidebar.warning("No accounts connected.")
    return manager, connected


def get_manager_and_check():
    inject_grafana_css()
    manager, connected = display_connection_sidebar()
    if not connected:
        st.warning("⚠️ No accounts connected. Go to the main page to connect.")
        st.stop()
    return manager, connected


def apply_account_filter(manager, connected):
    selected = st.sidebar.multiselect("Filter Environments", options=connected,
                                       default=connected, key="account_filter")
    return selected if selected else connected