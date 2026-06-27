import json
import streamlit as st
from datetime import datetime
import socket

TOKENS_FILE = "tokens.json"

def get_client_ip():
    """Client IP lao — Streamlit headers se"""
    try:
        # Streamlit Cloud / reverse proxy ke liye
        headers = st.context.headers
        ip = (
            headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or headers.get("X-Real-Ip", "")
            or "unknown"
        )
        return ip
    except Exception:
        return "unknown"

def ip_prefix(ip: str, octets: int = 3) -> str:
    """Sirf pehle N octets lo — e.g. '192.168.1' """
    parts = ip.split(".")
    return ".".join(parts[:octets]) if len(parts) >= octets else ip

def check_access():
    token = st.query_params.get("token", "")

    if token:
        st.session_state["auth_token"] = token
    elif "auth_token" in st.session_state:
        token = st.session_state["auth_token"]

    if not token:
        _show_error("🔒", "#ff006e", "ACCESS DENIED",
                    "Yeh system sirf authorized users ke liye hai.<br>"
                    "Agar access chahiye to <strong style='color:#fff;'>Umer Ali</strong> se contact karo.")
        st.stop()

    tokens = load_tokens()

    if token not in tokens:
        _show_error("⛔", "#ff4444", "INVALID TOKEN",
                    "Yeh link valid nahi hai.<br>Admin se naya link mangwao.")
        st.stop()

    user = tokens[token]

    if not user.get("active", True):
        _show_error("🚫", "#ff8800", "ACCOUNT DISABLED",
                    f"<strong style='color:#fff;'>{user['name']}</strong> — tera access band hai.<br>Umer Ali se rabta karo.")
        st.stop()

    expiry = datetime.strptime(user["expires"], "%Y-%m-%d")
    if datetime.now() > expiry:
        _show_error("⏰", "#ffdd00", "TOKEN EXPIRED",
                    f"Tera token <strong style='color:#fff;'>{user['expires']}</strong> ko expire ho gaya.<br>Admin se naya token mangwao.")
        st.stop()

    # ── IP Lock Logic ─────────────────────────────────────
    current_ip = get_client_ip()
    current_prefix = ip_prefix(current_ip, octets=3)  # sirf pehle 3 octets

    if "locked_ip_prefix" not in user or not user["locked_ip_prefix"]:
        # Pehli baar — IP prefix save karo
        tokens[token]["locked_ip_prefix"] = current_prefix
        tokens[token]["locked_ip_full"] = current_ip  # reference ke liye
        save_tokens(tokens)
    else:
        saved_prefix = user["locked_ip_prefix"]
        if current_prefix != saved_prefix:
            # ✅ Yahan SECURITY VIOLATION dena sahi hai
            _show_error("🚨", "#ff006e", "SECURITY VIOLATION",
                        "Yeh token already kisi aur device par lock hai.<br>"
                        "<strong style='color:#ff006e;'>Token sharing detected!</strong><br>"
                        "Umer Ali se contact karo.")
            st.stop()

    st.query_params["token"] = token
    return user["name"]


def _show_error(icon, color, title, message):
    st.markdown(f"""
    <div style="background:#020408; min-height:100vh; display:flex;
         align-items:center; justify-content:center;">
    <div style="border:1px solid {color}; border-radius:16px; padding:60px 50px;
         text-align:center; max-width:480px; background:{color}11;
         font-family:monospace;">
        <div style="font-size:64px; margin-bottom:24px;">{icon}</div>
        <div style="color:{color}; font-size:20px; font-weight:bold; letter-spacing:3px;">
            {title}
        </div>
        <div style="color:#555; margin-top:16px; font-size:13px; line-height:2;">
            {message}
        </div>
    </div>
    </div>
    """, unsafe_allow_html=True)
