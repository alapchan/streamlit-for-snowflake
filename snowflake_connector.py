"""
Snowflake connection management and query execution.
"""

import snowflake.connector
import pandas as pd
import streamlit as st
from typing import Optional, List
from config import AccountConfig


class SnowflakeConnectionManager:
    """Manages Snowflake connections for multiple accounts."""

    def __init__(self):
        if "connections" not in st.session_state:
            st.session_state.connections = {}
        if "connection_status" not in st.session_state:
            st.session_state.connection_status = {}

    def connect(self, config: AccountConfig) -> bool:
        """Establish connection to a Snowflake account."""
        try:
            password = config.get_password()
            if not password:
                st.session_state.connection_status[config.name] = "No password provided"
                return False

            conn = snowflake.connector.connect(
                account=config.account,
                user=config.user,
                password=password,
                role=config.role,
                warehouse=config.warehouse,
                client_session_keep_alive=True,
            )
            st.session_state.connections[config.name] = conn
            st.session_state.connection_status[config.name] = "Connected"
            return True
        except Exception as e:
            st.session_state.connection_status[config.name] = f"Error: {str(e)}"
            return False

    def disconnect(self, account_name: str):
        """Disconnect from a Snowflake account."""
        if account_name in st.session_state.connections:
            try:
                st.session_state.connections[account_name].close()
            except Exception:
                pass
            del st.session_state.connections[account_name]
            st.session_state.connection_status[account_name] = "Disconnected"

    def disconnect_all(self):
        """Disconnect from all accounts."""
        for name in list(st.session_state.connections.keys()):
            self.disconnect(name)

    def is_connected(self, account_name: str) -> bool:
        """Check if connected to an account."""
        if account_name not in st.session_state.connections:
            return False
        try:
            conn = st.session_state.connections[account_name]
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return True
        except Exception:
            if account_name in st.session_state.connections:
                del st.session_state.connections[account_name]
            st.session_state.connection_status[account_name] = "Disconnected"
            return False

    def get_connection(self, account_name: str):
        """Get an active connection for an account."""
        if self.is_connected(account_name):
            return st.session_state.connections.get(account_name)
        return None

    def execute_query(self, account_name: str, query: str) -> Optional[pd.DataFrame]:
        """Execute a query on a specific account and return results as DataFrame."""
        conn = self.get_connection(account_name)
        if conn is None:
            return None
        try:
            cursor = conn.cursor()
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            data = cursor.fetchall()
            cursor.close()
            if columns:
                df = pd.DataFrame(data, columns=columns)
                df["_ACCOUNT"] = account_name
                return df
            return pd.DataFrame()
        except Exception as e:
            st.error(f"Query error on {account_name}: {str(e)}")
            return None

    def execute_query_all(self, query: str, connected_only: bool = True) -> pd.DataFrame:
        """Execute a query across all connected accounts and combine results."""
        all_dfs = []
        for account_name in list(st.session_state.connections.keys()):
            if connected_only and not self.is_connected(account_name):
                continue
            df = self.execute_query(account_name, query)
            if df is not None and not df.empty:
                all_dfs.append(df)
        if all_dfs:
            return pd.concat(all_dfs, ignore_index=True)
        return pd.DataFrame()

    def get_connected_accounts(self) -> List[str]:
        """Return list of connected account names."""
        return [
            name for name in st.session_state.connections.keys()
            if self.is_connected(name)
        ]