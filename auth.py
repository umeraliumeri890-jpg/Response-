"""Activation-code authentication + device lock via Google Apps Script registry."""
from __future__ import annotations

import json
from typing import Any

import requests
import streamlit as st

from config import ADMIN_OPERATOR, APP_NAME, get_settings
from utils import get_server_side_fp, log_event, session_expired, touch_activity


def _registry_post(payload: dict[str, Any], timeout: int = 15) -> dict[str, Any]:
    settings = get_settings()
    url = settings["registry_url"]
    if not url:
        return {"success": False, "msg": "REGISTRY_URL missing in secrets"}
    try:
        r = requests.post(
            url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
        try:
            return r.json()
        except Exception:
            return {"success": False, "msg": f"Invalid registry response ({r.status_code})"}
    except Exception as exc:
        log_event("registry_error", str(exc), action=payload.get("action"))
        return {"success": False, "msg": f"Connection error: {exc}"}


def check_code(code: str, fp: str) -> dict[str, Any]:
    return _registry_post(
        {"action": "check_code", "code": code.strip().upper(), "fp": fp, "ip": ""},
        timeout=15,
    )


def generate_codes(count: int, prefix: str = "UTS") -> dict[str, Any]:
    settings = get_settings()
    return _registry_post(
        {
            "action": "generate_codes",
            "count": int(count),
            "prefix": prefix,
            "admin_key": settings["admin_key"],
        },
        timeout=20,
    )


def deactivate_code(code: str) -> dict[str, Any]:
    settings = get_settings()
    return _registry_post(
        {
            "action": "deactivate_code",
            "code": code.strip().upper(),
            "admin_key": settings["admin_key"],
        },
        timeout=15,
    )


def list_codes() -> dict[str, Any]:
    settings = get_settings()
    return _registry_post(
        {"action": "list_codes", "admin_key": settings["admin_key"]},
        timeout=15,
    )


def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated"))


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
    """Drop session after inactivity timeout."""
    if not is_authenticated():
        return
    settings = get_settings()
    # Auto-login mode never times out the synthetic session
    if settings.get("auth_disabled"):
        touch_activity()
        return
    if session_expired(settings["session_timeout_min"]):
        log_event("session_timeout", "inactivity timeout")
        logout()
        st.warning("Session expired due to inactivity. Please log in again.")
        st.stop()
    touch_activity()


def render_login() -> None:
    """Full-page activation gate."""
    fp = get_server_side_fp()
    st.session_state["device_fp"] = fp

    st.markdown(
        f"""
        <div class="login-wrap">
          <div class="login-card glass">
            <div class="login-logo">⚡</div>
            <div class="login-badge">UTS SYSTEMS</div>
            <h1 class="login-title">{APP_NAME}</h1>
            <p class="login-sub">Authorized Access Only · Device Locked Sessions</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        with st.form("login_form", clear_on_submit=False):
            code = st.text_input(
                "🔑 Activation Code",
                placeholder="UTS-XXXXXXXXXXXX",
                key="login_code_input",
            )
            submitted = st.form_submit_button("▶ ACTIVATE SESSION", use_container_width=True)
            if submitted:
                if not code.strip():
                    st.error("Enter your activation code.")
                else:
                    with st.spinner("Verifying activation code & device lock..."):
                        result = check_code(code.strip(), fp)
                    if result.get("success"):
                        st.session_state["authenticated"] = True
                        st.session_state["operator_name"] = result.get("operator", "OPERATOR")
                        st.session_state["auth_code"] = code.strip().upper()
                        touch_activity()
                        log_event(
                            "login_success",
                            "activated",
                            operator=st.session_state["operator_name"],
                            fp=fp[:12],
                        )
                        st.success("Access granted.")
                        st.rerun()
                    else:
                        msg = result.get("msg", "UNKNOWN ERROR")
                        log_event("login_denied", msg, fp=fp[:12])
                        st.error(f"ACCESS DENIED — {msg}")

        st.caption(f"🔒 Device ID: `{fp[:24]}…`  ·  Each code is device-locked.")


def _auto_login() -> None:
    """Synthetic session when AUTH_DISABLED=true (dashboard open without code)."""
    if is_authenticated():
        return
    st.session_state["authenticated"] = True
    st.session_state["operator_name"] = ADMIN_OPERATOR
    st.session_state["auth_code"] = "AUTO"
    touch_activity()
    log_event("auto_login", "AUTH_DISABLED — session granted", operator=ADMIN_OPERATOR)


def require_auth() -> None:
    settings = get_settings()
    if settings.get("auth_disabled", True):
        _auto_login()
        enforce_session()
        return
    if not is_authenticated():
        render_login()
        st.stop()
    enforce_session()
