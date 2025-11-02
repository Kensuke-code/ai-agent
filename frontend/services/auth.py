from __future__ import annotations

from pathlib import Path
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
import streamlit as st


def _load_config() -> dict:
    """Load config.yaml located in the frontend project root.

    Returns:
        Parsed YAML config as dict.
    """
    config_path = Path(__file__).resolve().parents[1] / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.load(f, Loader=SafeLoader)


def create_authenticator() -> stauth.Authenticate:
    """Create and return a configured authenticator instance using bundled config."""
    config = _load_config()
    return stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
        auto_hash=False,
    )

# ログイン検証
def is_login() -> None:
    if st.session_state.get("authentication_status") is None:
        st.switch_page("pages/login.py")