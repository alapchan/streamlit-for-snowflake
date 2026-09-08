"""
🤖 AI Assistant - Cortex-powered Natural Language Interface
Allows non-technical users to query Snowflake using plain English.
"""

import streamlit as st
import pandas as pd
import time
from utils import get_manager_and_check, apply_account_filter
from cortex_agent import CortexAgent
from config import get_cortex_config
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
    "Your Page Title",
    subtitle="Snowflake Operational Monitoring Experience"
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .assistant-header {
        background: linear-gradient(135deg, #29B5E8 0%, #6C63FF 100%);
        padding: 30px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 30px;
    }
    .assistant-header h1 {
        color: white;
        margin: 0;
        font-size: 2rem;
    }
    .assistant-header p {
        color: rgba(255,255,255,0.9);
        margin: 10px 0 0 0;
        font-size: 1.1rem;
    }
    .suggestion-chip {
        display: inline-block;
        padding: 8px 16px;
        margin: 4px;
        border-radius: 20px;
        background-color: #f0f2f6;
        border: 1px solid #ddd;
        cursor: pointer;
        font-size: 0.85rem;
        transition: all 0.2s;
    }
    .suggestion-chip:hover {
        background-color: #29B5E8;
        color: white;
        border-color: #29B5E8;
    }
    .stChatMessage [data-testid="chatAvatarIcon-assistant"] {
        background-color: #29B5E8;
    }
    .intent-badge {
        display: inline-block;
        padding: 2px 8px;
        margin: 2px;
        border-radius: 10px;
        font-size: 0.7rem;
        background-color: #e8f4f8;
        color: #1a6b8a;
    }
    .sql-expander {
        background-color: #1e1e1e;
        border-radius: 8px;
        padding: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ─── Connection Check ────────────────────────────────────────────────────────

manager, connected = get_manager_and_check()
selected_accounts = apply_account_filter(manager, connected)

# ─── Initialize Agent ────────────────────────────────────────────────────────

agent = CortexAgent(manager)
cortex_config = get_cortex_config()

# ─── Sidebar Configuration ───────────────────────────────────────────────────

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 AI Settings")

# Model selection
model_options = [
    "llama3.1-70b",
    "llama3.1-405b",
    "mistral-large2",
    "snowflake-arctic",
    "llama3.1-8b",
    "mistral-7b",
    "gemma-7b",
]
selected_model = st.sidebar.selectbox(
    "Cortex Model",
    options=model_options,
    index=model_options.index(cortex_config.model) if cortex_config.model in model_options else 0,
    help="Select the Cortex LLM model to use for AI responses"
)
cortex_config.model = selected_model

# Temperature
cortex_config.temperature = st.sidebar.slider(
    "Temperature",
    min_value=0.0,
    max_value=1.0,
    value=cortex_config.temperature,
    step=0.1,
    help="Lower = more deterministic, Higher = more creative"
)

# Show SQL toggle
show_sql = st.sidebar.checkbox("Show Generated SQL", value=True,
                                help="Display the SQL queries being executed")

# Auto-chart toggle
auto_chart = st.sidebar.checkbox("Auto-generate Charts", value=True,
                                  help="Automatically create visualizations for results")

# Clear conversation
if st.sidebar.button("🗑️ Clear Conversation", use_container_width=True):
    agent.clear_history()
    st.rerun()

if st.sidebar.button("🔄 Refresh Metadata Cache", use_container_width=True):
    agent.metadata_collector.clear_cache()
    st.success("Metadata cache cleared!")

# ─── Header ──────────────────────────────────────────────────────────────────

st.markdown("""
<div class="assistant-header">
    <h1>🤖 Snowflake AI Assistant</h1>
    <p>Ask me anything about your Snowflake environment in plain English</p>
</div>
""", unsafe_allow_html=True)

# ─── Quick Info Bar ──────────────────────────────────────────────────────────

info_col1, info_col2, info_col3 = st.columns(3)
with info_col1:
    st.info(f"🔗 Connected to **{len(selected_accounts)}** account(s)")
with info_col2:
    st.info(f"🧠 Model: **{cortex_config.model}**")
with info_col3:
    msg_count = len(st.session_state.get("agent_messages", []))
    st.info(f"💬 Messages: **{msg_count}**")

# ─── Starter Suggestions ────────────────────────────────────────────────────

if not st.session_state.get("agent_messages"):
    st.markdown("### 💡 Try asking me:")

    suggestions = [
        ("📊", "How many databases do I have?"),
        ("📋", "What are the largest tables?"),
        ("⚙️", "Which warehouses are running?"),
        ("💰", "Show me credit usage by warehouse"),
        ("👥", "How many users are active?"),
        ("📈", "Are there any slow queries this week?"),
        ("💾", "What's the current storage usage?"),
        ("📊", "Compare databases across accounts"),
        ("❌", "Show me failed queries"),
        ("📈", "Graph the storage trend over time"),
        ("🔍", "What tables are in the production database?"),
        ("💡", "What can you help me with?"),
    ]

    # Display as clickable buttons in a grid
    cols = st.columns(3)
    for i, (emoji, suggestion) in enumerate(suggestions):
        col = cols[i % 3]
        with col:
            if st.button(f"{emoji} {suggestion}", key=f"suggest_{i}", use_container_width=True):
                st.session_state.agent_messages.append({"role": "user", "content": suggestion})
                st.rerun()

    st.markdown("---")

# ─── Chat Display ────────────────────────────────────────────────────────────

# Display conversation history
for i, message in enumerate(st.session_state.get("agent_messages", [])):
    role = message["role"]

    if role == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(message["content"])

    elif role == "assistant":
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(message.get("content", ""))

            # Display chart if exists
            if "chart" in message and message["chart"] is not None:
                st.plotly_chart(message["chart"], use_container_width=True, key=f"chart_{i}")

            # Display data table if exists
            if "data" in message and message["data"] is not None:
                with st.expander(f"📋 View Data ({len(message['data'])} rows)", expanded=False):
                    st.dataframe(message["data"], use_container_width=True, height=400)

                    # Download button
                    csv = message["data"].to_csv(index=False)
                    st.download_button(
                        "📥 Download CSV",
                        data=csv,
                        file_name="ai_assistant_results.csv",
                        mime="text/csv",
                        key=f"download_{i}"
                    )

            # Display SQL if enabled and exists
            if show_sql and "sql" in message and message["sql"]:
                with st.expander("🔍 View SQL Query", expanded=False):
                    st.code(message["sql"], language="sql")

            # Display intent badges
            if "intents" in message and message["intents"]:
                intent_html = " ".join(
                    [f'<span class="intent-badge">{intent}</span>'
                     for intent in message["intents"]]
                )
                st.markdown(f"**Detected intents:** {intent_html}", unsafe_allow_html=True)

            # Display follow-up suggestions
            if "followups" in message and message["followups"]:
                st.markdown("**💡 Follow-up questions:**")
                followup_cols = st.columns(len(message["followups"]))
                for j, (col, followup) in enumerate(zip(followup_cols, message["followups"])):
                    with col:
                        if st.button(
                            f"❓ {followup}",
                            key=f"followup_{i}_{j}",
                            use_container_width=True
                        ):
                            st.session_state.agent_messages.append(
                                {"role": "user", "content": followup}
                            )
                            st.rerun()

# ─── Chat Input ──────────────────────────────────────────────────────────────

user_input = st.chat_input(
    "Ask me anything about your Snowflake environment...",
    key="ai_chat_input"
)

if user_input:
    # Add user message
    st.session_state.agent_messages.append({"role": "user", "content": user_input})

    # Display the user message immediately
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    # Process with the agent
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("🧠 Thinking..."):
            start_time = time.time()
            result = agent.process_question(user_input, selected_accounts)
            elapsed = time.time() - start_time

        # Display the answer
        st.markdown(result["answer"])

        # Display chart
        if auto_chart and result["chart"] is not None:
            st.plotly_chart(result["chart"], use_container_width=True)

        # Display data
        if result["data"] is not None and not result["data"].empty:
            with st.expander(f"📋 View Data ({len(result['data'])} rows)", expanded=False):
                st.dataframe(result["data"], use_container_width=True, height=400)

                csv = result["data"].to_csv(index=False)
                st.download_button(
                    "📥 Download CSV",
                    data=csv,
                    file_name="ai_assistant_results.csv",
                    mime="text/csv",
                    key=f"download_latest"
                )

        # Display SQL
        if show_sql and result["sql"]:
            with st.expander("🔍 View SQL Query", expanded=False):
                st.code(result["sql"], language="sql")

        # Intent badges
        if result["intents"]:
            intent_html = " ".join(
                [f'<span class="intent-badge">{intent}</span>'
                 for intent in result["intents"]]
            )
            st.markdown(f"**Detected intents:** {intent_html}", unsafe_allow_html=True)

        # Timing
        st.caption(f"⏱️ Processed in {elapsed:.1f}s")

        # Follow-up suggestions
        if result["followups"]:
            st.markdown("**💡 Follow-up questions:**")
            msg_idx = len(st.session_state.agent_messages)
            followup_cols = st.columns(min(len(result["followups"]), 3))
            for j, (col, followup) in enumerate(zip(followup_cols, result["followups"])):
                with col:
                    if st.button(
                        f"❓ {followup}",
                        key=f"followup_latest_{j}",
                        use_container_width=True
                    ):
                        st.session_state.agent_messages.append(
                            {"role": "user", "content": followup}
                        )
                        st.rerun()

    # Save assistant message to history
    st.session_state.agent_messages.append({
        "role": "assistant",
        "content": result["answer"],
        "data": result["data"],
        "chart": result["chart"],
        "sql": result["sql"],
        "intents": result["intents"],
        "followups": result["followups"],
    })

# ─── Advanced Mode (Bottom Expander) ─────────────────────────────────────────

st.markdown("---")

with st.expander("🔧 Advanced: Run Custom SQL via AI", expanded=False):
    st.markdown("""
    Describe what you want to query in plain English, and the AI will generate
    and execute the SQL for you.
    """)

    custom_col1, custom_col2 = st.columns([2, 1])

    with custom_col1:
        custom_question = st.text_area(
            "Describe your query",
            placeholder="e.g., Show me the top 10 users by number of queries run in the last 30 days, grouped by warehouse",
            height=100,
            key="custom_query_input"
        )

    with custom_col2:
        custom_account = st.selectbox(
            "Target Account",
            options=selected_accounts,
            key="custom_query_account"
        )
        execute_custom = st.button("🚀 Generate & Execute", type="primary",
                                    use_container_width=True, key="execute_custom")

    if execute_custom and custom_question:
        with st.spinner("🧠 Generating SQL..."):
            metadata = agent.metadata_collector.get_all_metadata()
            generated_sql = agent.llm.generate_sql(custom_question, metadata)

        if generated_sql:
            st.subheader("Generated SQL")
            st.code(generated_sql, language="sql")

            # Allow editing
            edited_sql = st.text_area("Edit SQL if needed:", value=generated_sql, height=150,
                                       key="edited_sql")

            if st.button("▶️ Execute Query", key="execute_edited"):
                with st.spinner("Running query..."):
                    result_df = manager.execute_query(custom_account, edited_sql)

                if result_df is not None and not result_df.empty:
                    st.success(f"✅ Returned {len(result_df)} rows")
                    st.dataframe(result_df, use_container_width=True, height=400)

                    csv = result_df.to_csv(index=False)
                    st.download_button("📥 Download Results", data=csv,
                                       file_name="custom_query_results.csv", mime="text/csv")

                    # Try to auto-visualize
                    if auto_chart:
                        viz = agent.visualizer
                        chart_type = viz.detect_chart_type(result_df)
                        if chart_type != "table":
                            chart = viz.create_chart(result_df, chart_type, title=custom_question)
                            if chart:
                                st.plotly_chart(chart, use_container_width=True)
                else:
                    st.warning("Query returned no results.")
        else:
            st.error("Could not generate SQL for that question. Please try rephrasing.")

# ─── Page Navigation Help ────────────────────────────────────────────────────

with st.expander("🗺️ Navigate to Detailed Pages", expanded=False):
    st.markdown("""
    While I can answer most questions, the dedicated pages offer richer
    interactive exploration:

    | Page | What You'll Find |
    |------|-----------------|
    | 📊 **Databases & Schemas** | Browse all databases and schemas with schema counts |
    | 📋 **Tables & Views** | Explore tables with column details, search, and sizing |
    | ⚙️ **Warehouses** | Real-time status, sizing, and credit metering |
    | 👥 **Users & Roles** | User management, login history, and grant investigation |
    | 📈 **Query History** | Analyze patterns, slow queries, failures with filters |
    | 💾 **Storage Usage** | Account, database, and table-level storage treemaps |

    Use the **sidebar navigation** to switch between pages.
    """)

# ─── Footer ──────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #888; font-size: 0.85rem;'>"
    "🤖 Powered by Snowflake Cortex AI | "
    f"Model: {cortex_config.model} | "
    f"Connected to {len(selected_accounts)} account(s)"
    "</div>",
    unsafe_allow_html=True
)