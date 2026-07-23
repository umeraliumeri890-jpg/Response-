"""
UTS HUNTERS ENTERPRISE
Enterprise Streamlit SOC dashboard for multi-API OTP intelligence.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is importable on Streamlit Cloud / local
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(
    page_title="UTS HUNTERS ENTERPRISE",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

from streamlit_option_menu import option_menu

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:  # pragma: no cover
    st_autorefresh = None

from admin import render_admin
from api import load_live_data
from auth import is_admin, logout, require_auth
from config import APP_NAME, APP_VERSION, REFRESH_OPTIONS, SIDEBAR_PAGES, get_settings
from dashboard import (
    error_boundary,
    page_analytics,
    page_cli,
    page_countries,
    page_dashboard,
    page_exports,
    page_live_monitor,
    page_search,
    page_settings,
    render_header,
    _notify_events,
)
from utils import inject_css, log_event, touch_activity

try:
    from whatsapp_alert import process_otp_alerts
except Exception:  # pragma: no cover
    process_otp_alerts = None  # type: ignore


def _init_state() -> None:
    defaults = {
        "theme": "Cyber",
        "refresh_label": "15 sec",
        "refresh_sec": 15,
        "timezone": "UTC",
        "page_size": 50,
        "notifications_enabled": True,
        "desktop_notify": False,
        "high_traffic_threshold": 80,
        "cache_bust": 0,
        "stream_buffer": 500,
        "target_cli": "MYOB",
        "search_history": [],
        "favorite_filters": [],
        "page": "Dashboard",
        "wa_alerts_enabled": True,
        "wa_threshold": 50,
        "wa_window_min": 5,
        "wa_cooldown_min": 5,
        "wa_alert_history": [],
        "wa_cli_cooldown_until": {},
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def _sidebar(operator: str, admin: bool) -> str:
    logo = ROOT / "assets" / "logo.png"
    with st.sidebar:
        if logo.exists():
            st.image(str(logo), width=96)
        st.markdown(
            f"""
            <div style="font-family:Orbitron,sans-serif;font-size:16px;font-weight:800;color:#00D4FF;letter-spacing:2px;margin-bottom:2px">
              UTS HUNTERS
            </div>
            <div style="font-family:JetBrains Mono,monospace;font-size:10px;color:#5A7AA0;letter-spacing:2px;margin-bottom:12px">
              ENTERPRISE v{APP_VERSION}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(f"Operator · **{operator}**")

        pages = [p for p, _ in SIDEBAR_PAGES if p != "Admin" or admin]
        icons = [ic for p, ic in SIDEBAR_PAGES if p != "Admin" or admin]
        default_idx = pages.index(st.session_state.get("page", "Dashboard")) if st.session_state.get("page", "Dashboard") in pages else 0

        selected = option_menu(
            menu_title=None,
            options=pages,
            icons=icons,
            menu_icon="cast",
            default_index=default_idx,
            orientation="vertical",
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "#00D4FF", "font-size": "16px"},
                "nav-link": {
                    "font-size": "13px",
                    "text-align": "left",
                    "margin": "2px 0",
                    "color": "#A8B4C8",
                    "font-family": "Inter, sans-serif",
                    "border-radius": "8px",
                },
                "nav-link-selected": {
                    "background": "linear-gradient(90deg, rgba(0,212,255,.18), rgba(109,93,252,.18))",
                    "color": "#00D4FF",
                    "font-weight": "700",
                    "border": "1px solid rgba(0,212,255,.35)",
                },
            },
            key="nav_menu",
        )
        st.session_state["page"] = selected

        st.markdown("---")
        refresh_label = st.selectbox(
            "Auto refresh",
            list(REFRESH_OPTIONS.keys()),
            index=list(REFRESH_OPTIONS.keys()).index(st.session_state.get("refresh_label", "15 sec")),
            key="sidebar_refresh",
        )
        st.session_state["refresh_label"] = refresh_label
        st.session_state["refresh_sec"] = REFRESH_OPTIONS[refresh_label]

        c1, c2 = st.columns(2)
        with c1:
            if st.button("↻ Refresh", use_container_width=True):
                load_live_data(force=True)
                touch_activity()
                st.rerun()
        with c2:
            if st.button("⎋ Logout", use_container_width=True):
                logout()
                st.rerun()

        st.caption("SOC · Streamlit Cloud ready")
    return selected


def _maybe_autorefresh() -> None:
    sec = int(st.session_state.get("refresh_sec", 0) or 0)
    if sec > 0 and st_autorefresh is not None:
        # No infinite sleep/rerun loop — component-driven refresh only
        st_autorefresh(interval=sec * 1000, key="uts_autorefresh", limit=None)


def main() -> None:
    _init_state()
    inject_css(ROOT / "styles.css")

    # Auth gate
    require_auth()

    operator = st.session_state.get("operator_name", "OPERATOR")
    admin = is_admin()
    page = _sidebar(operator, admin)
    _maybe_autorefresh()

    # Data load with error boundary
    try:
        df, health = load_live_data(force=False)
    except Exception as exc:
        log_event("fatal_load", str(exc))
        error_boundary(exc)
        return

    render_header(operator, admin, health or {})
    try:
        _notify_events(df, health or {})
    except Exception:
        pass

    # In-session WhatsApp OTP alerts (only while a real browser tab is open).
    # 24/7 delivery is handled by alert_worker.py via GitHub Actions —
    # HTTP keep-alive pings never execute this block.
    if process_otp_alerts is not None:
        try:
            process_otp_alerts(df)
        except Exception as exc:
            log_event("wa_engine_error", str(exc))

    try:
        if page == "Dashboard":
            page_dashboard(df, health or {})
        elif page == "Live Monitor":
            page_live_monitor(df)
        elif page == "Analytics":
            page_analytics(df)
        elif page == "Countries":
            page_countries(df)
        elif page == "CLI Analysis":
            page_cli(df)
        elif page == "Search":
            page_search(df)
        elif page == "Exports":
            page_exports(df)
        elif page == "Settings":
            page_settings()
        elif page == "Admin":
            render_admin()
        else:
            page_dashboard(df, health or {})
    except Exception as exc:
        log_event("page_error", str(exc), page=page)
        error_boundary(exc)

    # Footer
    settings = get_settings()
    missing = [k for k in ("lamix_token", "purple_token", "registry_url", "admin_key") if not settings.get(k)]
    if missing:
        st.caption(
            f"⚠ Secrets incomplete ({', '.join(missing)}). "
            "Configure `.streamlit/secrets.toml` or Streamlit Cloud secrets."
        )
    st.caption(f"{APP_NAME} v{APP_VERSION} · multi-threaded failover · no hard-coded tokens")


if __name__ == "__main__":
    main()
