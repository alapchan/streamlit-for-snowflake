"""
Snowflake Cortex AI Agent for Natural Language Querying.

Supports:
- Cortex Complete (LLM) for general Q&A and SQL generation
- Cortex Analyst for structured semantic-model-based queries
- Intelligent intent classification and routing
- Auto-visualization of results
- Conversation memory
"""

import json
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from typing import Optional, Dict, List, Tuple, Any
from snowflake_connector import SnowflakeConnectionManager
from config import get_cortex_config, CortexConfig


# ─── Metadata Collector ──────────────────────────────────────────────────────

class SnowflakeMetadataCollector:
    """
    Collects and caches Snowflake metadata to give the Cortex agent
    context about the objects that exist in connected accounts.
    """

    def __init__(self, manager: SnowflakeConnectionManager):
        self.manager = manager

    def get_metadata_summary(self, account_name: str) -> str:
        """Build a text summary of all Snowflake objects in an account."""
        if f"metadata_cache_{account_name}" in st.session_state:
            return st.session_state[f"metadata_cache_{account_name}"]

        sections = []

        # Databases
        db_df = self.manager.execute_query(account_name, "SHOW DATABASES")
        if db_df is not None and not db_df.empty:
            db_names = db_df["name"].tolist()
            sections.append(f"DATABASES ({len(db_names)}): {', '.join(db_names)}")

        # Warehouses
        wh_df = self.manager.execute_query(account_name, "SHOW WAREHOUSES")
        if wh_df is not None and not wh_df.empty:
            wh_info = []
            for _, row in wh_df.iterrows():
                info = f"{row.get('name','?')} (size={row.get('size','?')}, state={row.get('state','?')})"
                wh_info.append(info)
            sections.append(f"WAREHOUSES ({len(wh_info)}): {'; '.join(wh_info)}")

        # Users count
        user_df = self.manager.execute_query(account_name, "SHOW USERS")
        if user_df is not None and not user_df.empty:
            sections.append(f"USERS: {len(user_df)} total")

        # Roles count
        role_df = self.manager.execute_query(account_name, "SHOW ROLES")
        if role_df is not None and not role_df.empty:
            sections.append(f"ROLES: {len(role_df)} total")

        summary = f"Account: {account_name}\n" + "\n".join(sections)
        st.session_state[f"metadata_cache_{account_name}"] = summary
        return summary

    def get_all_metadata(self) -> str:
        """Get metadata summary for all connected accounts."""
        connected = self.manager.get_connected_accounts()
        summaries = []
        for acc in connected:
            try:
                summaries.append(self.get_metadata_summary(acc))
            except Exception as e:
                summaries.append(f"Account: {acc} - Error collecting metadata: {e}")
        return "\n\n".join(summaries)

    def clear_cache(self):
        """Clear metadata cache."""
        keys_to_remove = [k for k in st.session_state if k.startswith("metadata_cache_")]
        for key in keys_to_remove:
            del st.session_state[key]


# ─── Intent Classifier ───────────────────────────────────────────────────────

class IntentClassifier:
    """
    Classifies user questions into intents so the agent can route
    them to the correct handler (metadata lookup, SQL query, chart, etc.).
    """

    INTENT_PATTERNS = {
        "database_info": [
            r"\b(database|databases|db|dbs)\b",
            r"\bhow many databases\b",
            r"\blist.*databases\b",
            r"\bshow.*databases\b",
        ],
        "schema_info": [
            r"\b(schema|schemas)\b",
            r"\bhow many schemas\b",
            r"\blist.*schemas\b",
        ],
        "table_info": [
            r"\b(table|tables)\b",
            r"\bhow many tables\b",
            r"\blist.*tables\b",
            r"\bbiggest.*table\b",
            r"\blargest.*table\b",
            r"\btable.*size\b",
            r"\btable.*row\b",
        ],
        "view_info": [
            r"\b(view|views)\b",
            r"\blist.*views\b",
        ],
        "warehouse_info": [
            r"\b(warehouse|warehouses|wh)\b",
            r"\bwarehouse.*status\b",
            r"\bwarehouse.*running\b",
            r"\bwarehouse.*suspend\b",
            r"\bcredit\b",
            r"\bcompute\b",
        ],
        "user_info": [
            r"\b(user|users)\b",
            r"\bhow many users\b",
            r"\blist.*users\b",
            r"\bwho.*logged\b",
            r"\blogin\b",
        ],
        "role_info": [
            r"\b(role|roles|grant|grants|privilege|privileges)\b",
        ],
        "query_history": [
            r"\b(query|queries)\b",
            r"\bslow.*quer\b",
            r"\bfailed.*quer\b",
            r"\bquery.*history\b",
            r"\blong.*running\b",
            r"\bquery.*performance\b",
        ],
        "storage_info": [
            r"\b(storage|disk|space|size)\b",
            r"\bhow much storage\b",
            r"\bstorage.*usage\b",
            r"\bdata.*size\b",
        ],
        "cost_info": [
            r"\b(cost|credit|credits|spend|spending|bill|billing|expensive)\b",
        ],
        "comparison": [
            r"\bcompar\b",
            r"\bdifference.*between\b",
            r"\bvs\b",
            r"\bacross.*account\b",
        ],
        "chart_request": [
            r"\b(chart|graph|plot|visual|dashboard|pie|bar|line|trend)\b",
            r"\bshow.*me\b",
        ],
        "sql_generation": [
            r"\bwrite.*sql\b",
            r"\bgenerate.*sql\b",
            r"\bsql.*for\b",
            r"\bquery.*for\b",
            r"\bcreate.*query\b",
        ],
        "general_help": [
            r"\b(help|what can you|how do i|explain)\b",
        ],
    }

    @staticmethod
    def classify(question: str) -> List[str]:
        """Classify the user question into one or more intents."""
        question_lower = question.lower()
        intents = []
        for intent, patterns in IntentClassifier.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    intents.append(intent)
                    break
        if not intents:
            intents = ["general"]
        return intents


# ─── Query Builder ────────────────────────────────────────────────────────────

class QueryBuilder:
    """
    Builds Snowflake SQL queries based on classified intents.
    Returns pre-built queries for common questions so the LLM
    doesn't need to generate SQL for simple lookups.
    """

    PREBUILT_QUERIES = {
        "database_count": "SELECT COUNT(*) AS DATABASE_COUNT FROM INFORMATION_SCHEMA.DATABASES",
        "database_list": "SHOW DATABASES",
        "schema_list": "SHOW SCHEMAS",
        "warehouse_list": "SHOW WAREHOUSES",
        "warehouse_running": "SHOW WAREHOUSES",  # filter after
        "user_list": "SHOW USERS",
        "user_count": "SHOW USERS",
        "role_list": "SHOW ROLES",
        "table_count": """
            SELECT TABLE_CATALOG AS DATABASE_NAME, TABLE_SCHEMA, COUNT(*) AS TABLE_COUNT
            FROM SNOWFLAKE.ACCOUNT_USAGE.TABLES
            WHERE DELETED IS NULL AND TABLE_TYPE = 'BASE TABLE'
            GROUP BY TABLE_CATALOG, TABLE_SCHEMA
            ORDER BY TABLE_COUNT DESC
        """,
        "largest_tables": """
            SELECT TABLE_CATALOG AS DATABASE_NAME, TABLE_SCHEMA, TABLE_NAME,
                   ROW_COUNT, BYTES / (1024*1024) AS SIZE_MB
            FROM SNOWFLAKE.ACCOUNT_USAGE.TABLES
            WHERE DELETED IS NULL AND TABLE_TYPE = 'BASE TABLE' AND BYTES > 0
            ORDER BY BYTES DESC
            LIMIT 20
        """,
        "view_list": """
            SELECT TABLE_CATALOG AS DATABASE_NAME, TABLE_SCHEMA, TABLE_NAME,
                   IS_SECURE, CREATED
            FROM SNOWFLAKE.ACCOUNT_USAGE.VIEWS
            WHERE DELETED IS NULL
            ORDER BY CREATED DESC
            LIMIT 100
        """,
        "slow_queries": """
            SELECT QUERY_ID, QUERY_TEXT, USER_NAME, WAREHOUSE_NAME,
                   TOTAL_ELAPSED_TIME/1000 AS DURATION_SEC,
                   START_TIME, EXECUTION_STATUS
            FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
            WHERE START_TIME >= DATEADD('day', -7, CURRENT_TIMESTAMP())
            ORDER BY TOTAL_ELAPSED_TIME DESC
            LIMIT 20
        """,
        "failed_queries": """
            SELECT QUERY_ID, QUERY_TEXT, USER_NAME, WAREHOUSE_NAME,
                   ERROR_CODE, ERROR_MESSAGE, START_TIME
            FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
            WHERE START_TIME >= DATEADD('day', -7, CURRENT_TIMESTAMP())
                  AND EXECUTION_STATUS = 'FAIL'
            ORDER BY START_TIME DESC
            LIMIT 50
        """,
        "query_volume": """
            SELECT DATE_TRUNC('hour', START_TIME) AS HOUR,
                   COUNT(*) AS QUERY_COUNT,
                   AVG(TOTAL_ELAPSED_TIME)/1000 AS AVG_DURATION_SEC
            FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
            WHERE START_TIME >= DATEADD('day', -7, CURRENT_TIMESTAMP())
            GROUP BY HOUR ORDER BY HOUR
        """,
        "storage_current": """
            SELECT USAGE_DATE,
                   STORAGE_BYTES/(1024*1024*1024) AS STORAGE_GB,
                   STAGE_BYTES/(1024*1024*1024) AS STAGE_GB,
                   FAILSAFE_BYTES/(1024*1024*1024) AS FAILSAFE_GB
            FROM SNOWFLAKE.ACCOUNT_USAGE.STORAGE_USAGE
            ORDER BY USAGE_DATE DESC LIMIT 1
        """,
        "storage_trend": """
            SELECT USAGE_DATE,
                   (STORAGE_BYTES+STAGE_BYTES+FAILSAFE_BYTES)/(1024*1024*1024) AS TOTAL_GB
            FROM SNOWFLAKE.ACCOUNT_USAGE.STORAGE_USAGE
            WHERE USAGE_DATE >= DATEADD('day', -90, CURRENT_DATE())
            ORDER BY USAGE_DATE
        """,
        "credit_usage": """
            SELECT WAREHOUSE_NAME, START_TIME::DATE AS USAGE_DATE,
                   SUM(CREDITS_USED) AS TOTAL_CREDITS
            FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
            WHERE START_TIME >= DATEADD('day', -30, CURRENT_TIMESTAMP())
            GROUP BY WAREHOUSE_NAME, USAGE_DATE
            ORDER BY USAGE_DATE DESC
        """,
        "credit_summary": """
            SELECT WAREHOUSE_NAME,
                   SUM(CREDITS_USED) AS TOTAL_CREDITS,
                   SUM(CREDITS_USED_COMPUTE) AS COMPUTE_CREDITS,
                   SUM(CREDITS_USED_CLOUD_SERVICES) AS CLOUD_CREDITS
            FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
            WHERE START_TIME >= DATEADD('day', -30, CURRENT_TIMESTAMP())
            GROUP BY WAREHOUSE_NAME
            ORDER BY TOTAL_CREDITS DESC
        """,
        "login_history": """
            SELECT USER_NAME, EVENT_TYPE, IS_SUCCESS, CLIENT_IP,
                   REPORTED_CLIENT_TYPE, EVENT_TIMESTAMP
            FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
            WHERE EVENT_TIMESTAMP >= DATEADD('day', -7, CURRENT_TIMESTAMP())
            ORDER BY EVENT_TIMESTAMP DESC
            LIMIT 200
        """,
        "database_storage": """
            SELECT DATABASE_NAME,
                   AVERAGE_DATABASE_BYTES/(1024*1024*1024) AS AVG_DB_GB,
                   AVERAGE_FAILSAFE_BYTES/(1024*1024*1024) AS AVG_FAILSAFE_GB
            FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASE_STORAGE_USAGE_HISTORY
            WHERE USAGE_DATE = CURRENT_DATE() - 1
            ORDER BY AVERAGE_DATABASE_BYTES DESC
        """,
    }

    @staticmethod
    def get_query_for_intent(intents: List[str], question: str) -> Optional[Tuple[str, str]]:
        """
        Map intents + question keywords to a pre-built query.
        Returns (query_key, sql) or None if no pre-built match.
        """
        q = question.lower()

        if "database_info" in intents:
            if any(w in q for w in ["how many", "count", "number"]):
                return ("database_count", QueryBuilder.PREBUILT_QUERIES["database_count"])
            if any(w in q for w in ["storage", "size", "space"]):
                return ("database_storage", QueryBuilder.PREBUILT_QUERIES["database_storage"])
            return ("database_list", QueryBuilder.PREBUILT_QUERIES["database_list"])

        if "schema_info" in intents:
            return ("schema_list", QueryBuilder.PREBUILT_QUERIES["schema_list"])

        if "table_info" in intents:
            if any(w in q for w in ["biggest", "largest", "top", "size", "heavy"]):
                return ("largest_tables", QueryBuilder.PREBUILT_QUERIES["largest_tables"])
            if any(w in q for w in ["how many", "count", "number"]):
                return ("table_count", QueryBuilder.PREBUILT_QUERIES["table_count"])
            return ("table_count", QueryBuilder.PREBUILT_QUERIES["table_count"])

        if "view_info" in intents:
            return ("view_list", QueryBuilder.PREBUILT_QUERIES["view_list"])

        if "warehouse_info" in intents:
            if any(w in q for w in ["credit", "cost", "spend", "usage", "meter"]):
                return ("credit_summary", QueryBuilder.PREBUILT_QUERIES["credit_summary"])
            if any(w in q for w in ["running", "active", "started"]):
                return ("warehouse_running", QueryBuilder.PREBUILT_QUERIES["warehouse_running"])
            return ("warehouse_list", QueryBuilder.PREBUILT_QUERIES["warehouse_list"])

        if "user_info" in intents:
            if any(w in q for w in ["login", "logged", "sign"]):
                return ("login_history", QueryBuilder.PREBUILT_QUERIES["login_history"])
            return ("user_list", QueryBuilder.PREBUILT_QUERIES["user_list"])

        if "role_info" in intents:
            return ("role_list", QueryBuilder.PREBUILT_QUERIES["role_list"])

        if "query_history" in intents:
            if any(w in q for w in ["slow", "long", "duration", "performance"]):
                return ("slow_queries", QueryBuilder.PREBUILT_QUERIES["slow_queries"])
            if any(w in q for w in ["fail", "error", "broken"]):
                return ("failed_queries", QueryBuilder.PREBUILT_QUERIES["failed_queries"])
            return ("query_volume", QueryBuilder.PREBUILT_QUERIES["query_volume"])

        if "storage_info" in intents:
            if any(w in q for w in ["trend", "over time", "history", "growth"]):
                return ("storage_trend", QueryBuilder.PREBUILT_QUERIES["storage_trend"])
            if any(w in q for w in ["database", "db"]):
                return ("database_storage", QueryBuilder.PREBUILT_QUERIES["database_storage"])
            return ("storage_current", QueryBuilder.PREBUILT_QUERIES["storage_current"])

        if "cost_info" in intents:
            if any(w in q for w in ["trend", "over time", "daily", "history"]):
                return ("credit_usage", QueryBuilder.PREBUILT_QUERIES["credit_usage"])
            return ("credit_summary", QueryBuilder.PREBUILT_QUERIES["credit_summary"])

        return None


# ─── Auto-Visualizer ─────────────────────────────────────────────────────────

class AutoVisualizer:
    """
    Automatically selects and creates the best chart type
    for a given DataFrame result.
    """

    @staticmethod
    def detect_chart_type(df: pd.DataFrame, query_key: str = "") -> str:
        """Detect the best chart type for the data."""
        if df.empty or len(df.columns) < 2:
            return "table"

        # Hint from query key
        if query_key in ("storage_trend", "query_volume", "credit_usage"):
            return "line"
        if query_key in ("credit_summary", "database_storage", "largest_tables", "table_count"):
            return "bar"
        if query_key in ("database_count", "user_count"):
            return "metric"

        # Heuristic based on column types
        date_cols = [c for c in df.columns if any(
            kw in c.lower() for kw in ["date", "time", "timestamp", "hour", "day"]
        )]
        num_cols = df.select_dtypes(include=["number"]).columns.tolist()
        num_cols = [c for c in num_cols if c != "_ACCOUNT"]
        cat_cols = [c for c in df.select_dtypes(include=["object", "category"]).columns
                    if c != "_ACCOUNT"]

        if date_cols and num_cols:
            return "line"
        if len(df) <= 10 and num_cols and cat_cols:
            return "pie"
        if cat_cols and num_cols:
            return "bar"
        return "table"

    @staticmethod
    def create_chart(df: pd.DataFrame, chart_type: str,
                     query_key: str = "", title: str = "") -> Optional[go.Figure]:
        """Create a Plotly chart from the DataFrame."""
        if df.empty:
            return None

        num_cols = df.select_dtypes(include=["number"]).columns.tolist()
        num_cols = [c for c in num_cols if c != "_ACCOUNT"]
        cat_cols = [c for c in df.select_dtypes(include=["object", "category"]).columns
                    if c != "_ACCOUNT"]
        date_cols = [c for c in df.columns if any(
            kw in c.lower() for kw in ["date", "time", "timestamp", "hour", "day"]
        )]

        has_account = "_ACCOUNT" in df.columns and df["_ACCOUNT"].nunique() > 1

        try:
            if chart_type == "line" and date_cols and num_cols:
                x = date_cols[0]
                y = num_cols[0]
                color = "_ACCOUNT" if has_account else (cat_cols[0] if cat_cols else None)
                fig = px.line(df, x=x, y=y, color=color, title=title, height=450)
                return fig

            elif chart_type == "bar":
                if cat_cols and num_cols:
                    x = cat_cols[0]
                    y = num_cols[0]
                    color = "_ACCOUNT" if has_account else (cat_cols[1] if len(cat_cols) > 1 else None)
                    fig = px.bar(df, x=x, y=y, color=color, title=title,
                                 barmode="group", height=450)
                    fig.update_layout(xaxis_tickangle=-45)
                    return fig

            elif chart_type == "pie":
                if num_cols and cat_cols:
                    fig = px.pie(df, values=num_cols[0], names=cat_cols[0],
                                 title=title, height=450)
                    return fig

        except Exception as e:
            st.warning(f"Could not create chart: {e}")
        return None


# ─── Cortex LLM Client ───────────────────────────────────────────────────────

class CortexLLMClient:
    """
    Communicates with Snowflake Cortex LLM functions:
    - SNOWFLAKE.CORTEX.COMPLETE for general Q&A / SQL generation
    - SNOWFLAKE.CORTEX.ANALYST (if semantic model configured)
    """

    def __init__(self, manager: SnowflakeConnectionManager, config: CortexConfig):
        self.manager = manager
        self.config = config

    def _pick_account(self) -> Optional[str]:
        """Pick the first connected account to run Cortex functions against."""
        connected = self.manager.get_connected_accounts()
        return connected[0] if connected else None

    def complete(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """Call Cortex COMPLETE for general LLM completions."""
        account = self._pick_account()
        if not account:
            return None

        # Escape single quotes
        safe_system = system_prompt.replace("'", "''").replace("\\", "\\\\")
        safe_prompt = prompt.replace("'", "''").replace("\\", "\\\\")

        # Build the options JSON
        messages = []
        if safe_system:
            messages.append({"role": "system", "content": safe_system})
        messages.append({"role": "user", "content": safe_prompt})

        messages_json = json.dumps(messages).replace("'", "''")

        query = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                '{self.config.model}',
                PARSE_JSON('{messages_json}'),
                OBJECT_CONSTRUCT(
                    'temperature', {self.config.temperature},
                    'max_tokens', {self.config.max_tokens}
                )
            ) AS RESPONSE
        """

        df = self.manager.execute_query(account, query)
        if df is not None and not df.empty:
            response = df.iloc[0]["RESPONSE"]
            # Parse if JSON
            try:
                parsed = json.loads(response)
                if isinstance(parsed, dict):
                    return parsed.get("choices", [{}])[0].get("messages", "") or \
                           parsed.get("messages", "") or \
                           parsed.get("content", "") or str(parsed)
            except (json.JSONDecodeError, TypeError, IndexError):
                pass
            return str(response)
        return None

    def generate_sql(self, question: str, metadata: str) -> Optional[str]:
        """Use Cortex to generate a Snowflake SQL query for a user question."""
        system_prompt = f"""You are a Snowflake SQL expert assistant. Generate ONLY a valid Snowflake SQL query to answer the user's question.

RULES:
1. Return ONLY the SQL query, no explanations or markdown.
2. Use Snowflake syntax (e.g., DATEADD, DATEDIFF, FLATTEN, VARIANT, etc.).
3. Prefer SNOWFLAKE.ACCOUNT_USAGE views for monitoring queries.
4. Always add LIMIT clause (max 1000) unless aggregating.
5. Use proper quoting for identifiers if they contain special characters.
6. Do NOT use DELETE, UPDATE, INSERT, DROP, CREATE, ALTER, or GRANT statements.
7. Only generate SELECT or SHOW statements.

Available metadata:
{metadata}
"""
        response = self.complete(question, system_prompt)
        if response:
            # Extract SQL from response (remove markdown fences if present)
            sql = response.strip()
            sql = re.sub(r'^```(?:sql)?\s*', '', sql)
            sql = re.sub(r'\s*```$', '', sql)
            sql = sql.strip()

            # Safety check
            first_word = sql.split()[0].upper() if sql.split() else ""
            if first_word in ("SELECT", "SHOW", "DESCRIBE", "DESC", "WITH", "LIST"):
                return sql
        return None

    def explain_results(self, question: str, data_summary: str) -> Optional[str]:
        """Ask Cortex to explain query results in natural language."""
        system_prompt = """You are a friendly data analyst assistant helping non-technical users understand Snowflake monitoring data.

RULES:
1. Explain the data in simple, clear language.
2. Highlight key findings, trends, or anomalies.
3. Use bullet points for clarity.
4. If relevant, suggest actions or things to investigate further.
5. Keep the response concise (under 300 words).
6. Use emojis sparingly to make it more readable.
"""
        prompt = f"""The user asked: "{question}"

Here is a summary of the data results:
{data_summary}

Please provide a clear, non-technical explanation of these results."""

        return self.complete(prompt, system_prompt)

    def suggest_followups(self, question: str, context: str) -> Optional[List[str]]:
        """Generate follow-up question suggestions."""
        system_prompt = """Generate exactly 3 follow-up questions a non-technical user might ask after seeing Snowflake monitoring data. Return ONLY a JSON array of 3 strings. No other text."""

        prompt = f"""Original question: "{question}"
Context: {context}
Return a JSON array of 3 follow-up questions."""

        response = self.complete(prompt, system_prompt)
        if response:
            try:
                # Try to find JSON array in response
                match = re.search(r'\[.*\]', response, re.DOTALL)
                if match:
                    return json.loads(match.group())
            except (json.JSONDecodeError, AttributeError):
                pass
        return [
            "What are the most expensive warehouses?",
            "Show me the storage trend over time",
            "Are there any failed queries this week?"
        ]


# ─── Main Agent Orchestrator ─────────────────────────────────────────────────

class CortexAgent:
    """
    Main agent that orchestrates the full NLP pipeline:
    1. Classify intent
    2. Try pre-built query or generate SQL via Cortex
    3. Execute query across accounts
    4. Auto-visualize results
    5. Generate natural language explanation
    6. Suggest follow-ups
    """

    def __init__(self, manager: SnowflakeConnectionManager):
        self.manager = manager
        self.config = get_cortex_config()
        self.metadata_collector = SnowflakeMetadataCollector(manager)
        self.llm = CortexLLMClient(manager, self.config)
        self.visualizer = AutoVisualizer()
        self.query_builder = QueryBuilder()

        # Initialize conversation history
        if "agent_messages" not in st.session_state:
            st.session_state.agent_messages = []
        if "agent_context" not in st.session_state:
            st.session_state.agent_context = ""

    def process_question(self, question: str, target_accounts: List[str] = None) -> Dict[str, Any]:
        """
        Process a user question end-to-end.

        Returns dict with:
            - answer: str (natural language)
            - data: pd.DataFrame or None
            - chart: plotly Figure or None
            - sql: str or None
            - query_key: str
            - followups: list of str
            - intents: list of str
        """
        result = {
            "answer": "",
            "data": None,
            "chart": None,
            "sql": None,
            "query_key": "",
            "followups": [],
            "intents": [],
        }

        connected = target_accounts or self.manager.get_connected_accounts()
        if not connected:
            result["answer"] = "❌ No accounts are connected. Please connect to at least one Snowflake account first."
            return result

        # Step 1: Classify intent
        intents = IntentClassifier.classify(question)
        result["intents"] = intents

        # Step 2: Handle help / general
        if "general_help" in intents and len(intents) == 1:
            result["answer"] = self._get_help_text()
            result["followups"] = [
                "How many databases do I have?",
                "Show me warehouse credit usage",
                "What are the largest tables?",
            ]
            return result

        # Step 3: Try pre-built query
        prebuilt = self.query_builder.get_query_for_intent(intents, question)
        sql = None
        query_key = ""

        if prebuilt:
            query_key, sql = prebuilt
            result["query_key"] = query_key
        else:
            # Step 4: Use Cortex to generate SQL
            try:
                metadata = self.metadata_collector.get_all_metadata()
                generated = self.llm.generate_sql(question, metadata)
                if generated:
                    sql = generated
                    query_key = "cortex_generated"
                    result["query_key"] = query_key
            except Exception as e:
                st.warning(f"Cortex SQL generation unavailable: {e}")

        # Step 5: Execute query
        if sql:
            result["sql"] = sql
            all_dfs = []
            for acc in connected:
                try:
                    df = self.manager.execute_query(acc, sql)
                    if df is not None and not df.empty:
                        all_dfs.append(df)
                except Exception as e:
                    st.caption(f"⚠️ Query skipped for {acc}: {e}")

            if all_dfs:
                combined = pd.concat(all_dfs, ignore_index=True)
                result["data"] = combined

                # Step 6: Auto-visualize
                wants_chart = "chart_request" in intents or len(combined) > 1
                if wants_chart:
                    chart_type = self.visualizer.detect_chart_type(combined, query_key)
                    if chart_type != "table":
                        chart = self.visualizer.create_chart(
                            combined, chart_type, query_key,
                            title=question.capitalize()
                        )
                        result["chart"] = chart

                # Step 7: Generate explanation
                try:
                    data_summary = self._summarize_dataframe(combined, query_key)
                    explanation = self.llm.explain_results(question, data_summary)
                    if explanation:
                        result["answer"] = explanation
                    else:
                        result["answer"] = self._simple_answer(combined, query_key, question)
                except Exception:
                    result["answer"] = self._simple_answer(combined, query_key, question)

                # Step 8: Generate follow-up suggestions
                try:
                    followups = self.llm.suggest_followups(
                        question, self._summarize_dataframe(combined, query_key)
                    )
                    if followups:
                        result["followups"] = followups
                except Exception:
                    result["followups"] = self._default_followups(intents)
            else:
                result["answer"] = "🔍 The query executed but returned no results. Try rephrasing your question or checking if the relevant data exists."
        else:
            # No SQL - try pure LLM answer
            try:
                metadata = self.metadata_collector.get_all_metadata()
                answer = self.llm.complete(
                    question,
                    f"You are a Snowflake monitoring assistant. Here's the current environment:\n{metadata}\n\nAnswer the user's question helpfully."
                )
                result["answer"] = answer or "I couldn't find a good answer. Could you rephrase your question?"
            except Exception:
                result["answer"] = "I'm sorry, I couldn't process that question. Please try asking about databases, tables, warehouses, users, storage, queries, or costs."
            result["followups"] = self._default_followups(intents)

        # Save to context
        st.session_state.agent_context = f"Q: {question}\nA: {result['answer'][:500]}"

        return result

    def _summarize_dataframe(self, df: pd.DataFrame, query_key: str) -> str:
        """Create a text summary of a DataFrame for the LLM."""
        lines = [f"Result shape: {df.shape[0]} rows × {df.shape[1]} columns"]
        lines.append(f"Columns: {', '.join(df.columns.tolist())}")

        if "_ACCOUNT" in df.columns:
            lines.append(f"Accounts: {', '.join(df['_ACCOUNT'].unique())}")

        # Add first few rows
        lines.append(f"First rows:\n{df.head(10).to_string(index=False)}")

        # Numeric summaries
        num_cols = df.select_dtypes(include=["number"]).columns.tolist()
        for col in num_cols[:5]:
            lines.append(f"{col}: min={df[col].min():.2f}, max={df[col].max():.2f}, "
                         f"mean={df[col].mean():.2f}, sum={df[col].sum():.2f}")

        return "\n".join(lines)

    def _simple_answer(self, df: pd.DataFrame, query_key: str, question: str) -> str:
        """Generate a simple answer without Cortex (fallback)."""
        rows = len(df)
        accounts = df["_ACCOUNT"].unique().tolist() if "_ACCOUNT" in df.columns else ["Unknown"]

        answer = f"📊 Found **{rows} results** across {len(accounts)} account(s).\n\n"

        if query_key == "database_list":
            answer += f"You have **{rows}** databases total."
        elif query_key == "warehouse_list":
            if "state" in df.columns:
                running = len(df[df["state"].str.upper() == "STARTED"])
                answer += f"**{rows}** warehouses total, **{running}** currently running."
        elif query_key == "largest_tables":
            if "SIZE_MB" in df.columns and "TABLE_NAME" in df.columns:
                top = df.nlargest(3, "SIZE_MB")
                for _, r in top.iterrows():
                    answer += f"\n- **{r['TABLE_NAME']}**: {r['SIZE_MB']:.1f} MB"
        elif query_key == "credit_summary":
            if "TOTAL_CREDITS" in df.columns:
                total = df["TOTAL_CREDITS"].sum()
                answer += f"Total credit usage (last 30 days): **{total:.2f} credits**"

        return answer

    def _default_followups(self, intents: List[str]) -> List[str]:
        """Generate default follow-up suggestions based on intents."""
        suggestions = {
            "database_info": ["How much storage does each database use?", "Show me schemas in each database"],
            "table_info": ["What are the largest tables by size?", "Show table counts by schema"],
            "warehouse_info": ["Show warehouse credit usage trends", "Which warehouses are currently running?"],
            "user_info": ["Who logged in recently?", "How many active users are there?"],
            "query_history": ["Show me the slowest queries", "Are there any failed queries?"],
            "storage_info": ["Show storage growth over time", "Which databases use the most storage?"],
            "cost_info": ["What's the credit usage trend?", "Which warehouse is most expensive?"],
        }

        followups = []
        for intent in intents:
            followups.extend(suggestions.get(intent, []))

        if not followups:
            followups = [
                "Show me an overview of all databases",
                "What's the current storage usage?",
                "Are there any slow queries this week?",
            ]
        return followups[:4]

    def _get_help_text(self) -> str:
        return """👋 **Hi! I'm your Snowflake AI Assistant.** I can help you explore and understand your Snowflake environment using plain English.

Here are some things you can ask me:

**📊 Databases & Tables**
- "How many databases do I have?"
- "What are the largest tables?"
- "Show me all schemas"

**⚙️ Warehouses & Costs**
- "Which warehouses are running?"
- "Show warehouse credit usage"
- "What's the most expensive warehouse?"

**👥 Users & Security**
- "How many users are there?"
- "Who logged in recently?"
- "List all roles"

**📈 Queries & Performance**
- "Show me slow queries this week"
- "Are there any failed queries?"
- "What's the query volume trend?"

**💾 Storage**
- "How much storage am I using?"
- "Show storage growth over time"
- "Which database uses the most space?"

**📊 Visualizations**
- "Show me a chart of credit usage"
- "Graph the storage trend"
- "Compare databases across accounts"

Just type your question below! 🚀"""

    def clear_history(self):
        """Clear conversation history."""
        st.session_state.agent_messages = []
        st.session_state.agent_context = ""
        self.metadata_collector.clear_cache()