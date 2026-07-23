"""Activation-code authentication - DISABLED (auto-login)."""
from __future__ import annotations

import json
from typing import Any

import requests
import streamlit as st

from config import ADMIN_OPERATOR, APP_NAME, get_settings
from utils import get_server_side_fp, log_event, session_expired, touch_activity


def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated", True))  # Always True


def is_admin() -> bool:
    return st.session_state.get("operator_name") == ADMIN_OPERATOR


def logout() -> None:
    keys = [
        "authenticated",
        "operator_name",
        "auth_code",
        "last_activity",
        "codes_list",
        "page",
    ]
    for k in keys:
        st.session_state.pop(k, None)
    log_event("logout", "user logged out")


def enforce_session() -> None:
    # Auto-login if not authenticated
    if not st.session_state.get("authenticated"):
        st.session_state["authenticated"] = True
        st.session_state["operator_name"] = "OPERATOR"
        touch_activity()
    
    settings = get_settings()
    if session_expired(settings["session_timeout_min"]):
        log_event("session_timeout", "inactivity timeout")
        # Auto-login again
        st.session_state["authenticated"] = True
        st.session_state["operator_name"] = "OPERATOR"
        touch_activity()
    touch_activity()


def render_login() -> None:
    """Auto-login - no login page."""
    enforce_session()
    st.rerun()


def require_auth() -> None:
    """Auto-login - no auth required."""
    if not st.session_state.get("authenticated"):
        st.session_state["authenticated"] = True
        st.session_state["operator_name"] = "OPERATOR"
        touch_activity()
    enforce_session()


# Keep other functions for compatibility
def check_code(code: str, fp: str) -> dict[str, Any]:
    return {"success": True, "operator": "OPERATOR"}


def generate_codes(count: int, prefix: str = "UTS") -> dict[str, Any]:
    return {"success": True, "codes": []}


def deactivate_code(code: str) -> dict[str, Any]:
    return {"success": True}


def list_codes() -> dict[str, Any]:
    return {"success": True, "codes": []}
