"""
Configuration management for Snowflake Multi-Account Monitor.
"""

import os
import yaml
import streamlit as st
from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class AccountConfig:
    """Represents a single Snowflake account configuration."""
    name: str
    account: str
    user: str
    password: str = ""
    role: str = "ACCOUNTADMIN"
    warehouse: str = "COMPUTE_WH"
    env_password_key: str = ""

    def get_password(self) -> str:
        """Get password from environment variable or stored value."""
        if self.env_password_key:
            env_pass = os.getenv(self.env_password_key, "")
            if env_pass:
                return env_pass
        return self.password


@dataclass
class CortexConfig:
    """Configuration for Snowflake Cortex AI."""
    model: str = "llama3.1-70b"
    temperature: float = 0.1
    max_tokens: int = 4096
    analyst_semantic_models: List[str] = field(default_factory=list)


def load_config_from_yaml(filepath: str = "accounts_config.yaml") -> dict:
    """Load full configuration from YAML file."""
    try:
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                return yaml.safe_load(f) or {}
    except Exception as e:
        st.warning(f"Could not load config file: {e}")
    return {}


def load_accounts_from_yaml(filepath: str = "accounts_config.yaml") -> List[AccountConfig]:
    """Load account configurations from YAML file."""
    accounts = []
    config = load_config_from_yaml(filepath)
    if "accounts" in config:
        for acc in config["accounts"]:
            accounts.append(AccountConfig(**acc))
    return accounts


def load_cortex_config(filepath: str = "accounts_config.yaml") -> CortexConfig:
    """Load Cortex AI configuration from YAML file."""
    config = load_config_from_yaml(filepath)
    if "cortex" in config:
        return CortexConfig(**config["cortex"])
    return CortexConfig()


def get_account_configs() -> List[AccountConfig]:
    """Get account configurations from session state, YAML, or defaults."""
    if "account_configs" not in st.session_state:
        st.session_state.account_configs = load_accounts_from_yaml()
    return st.session_state.account_configs


def get_cortex_config() -> CortexConfig:
    """Get Cortex AI configuration."""
    if "cortex_config" not in st.session_state:
        st.session_state.cortex_config = load_cortex_config()
    return st.session_state.cortex_config


def save_account_config(account: AccountConfig):
    """Add or update an account configuration in session state."""
    configs = get_account_configs()
    for i, cfg in enumerate(configs):
        if cfg.name == account.name:
            configs[i] = account
            return
    configs.append(account)
    st.session_state.account_configs = configs


def remove_account_config(account_name: str):
    """Remove an account configuration."""
    configs = get_account_configs()
    st.session_state.account_configs = [c for c in configs if c.name != account_name]