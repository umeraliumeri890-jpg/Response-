import json
import streamlit as st
from datetime import datetime

TOKENS_FILE = "tokens.json"

def load_tokens():
    try:
        with open(TOKENS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("tokens.json nahi mili!")
        st.stop()

def save_tokens(tokens):
    with open(TOKENS_FILE, "w") as f:
        json.dump(tokens, f, indent=2)

def get_client_ip():
    try:
        headers = st.context.headers
        ip = headers.get("X-Forwarded-For", None)
        if ip:
            return ip.split(",")[0].strip()
        return headers.get("X-Real-Ip", "unknown")
    except:
        return "unknown"

def check_access():
    params = st.query_params
    token = params.get("token", "")

    if not token:
        st.markdown("""
        <div style="background:#020408; min-height:100vh; display:flex;
             align-items:center; justify-content:center;">
        <div style="border:1px solid #ff006e; border-radius:16px; padding:60px 50px;
             text-align:center; max-width:480px; background:rgba(255,0,110,0.05);
             font-family:monospace;">
            <div style="font-size:64px; margin-bottom:24px;">🔒</div>
            <div style="color:#ff006e; font-size:22px; font-weight:bold; letter-spacing:4px;">
                ACCESS DENIED
            </div>
            <div style="color:#555; margin-top:16px; font-size:13px; line-height:2;">
                Yeh system sirf authorized users ke liye hai.<br>
                Agar access chahiye to<br>
                <strong style="color:#fff;">Umer Ali</strong> se contact karo.
            </div>
        </div>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    tokens = load_tokens()

    if token not in tokens:
        st.markdown("""
        <div style="background:#020408; min-height:100vh; display:flex;
             align-items:center; justify-content:center;">
        <div style="border:1px solid #ff4444; border-radius:16px; padding:60px 50px;
             text-align:center; max-width:480px; background:rgba(255,68,68,0.05);
             font-family:monospace;">
            <div style="font-size:64px; margin-bottom:24px;">⛔</div>
            <div style="color:#ff4444; font-size:20px; font-weight:bold; letter-spacing:3px;">
                INVALID TOKEN
            </div>
            <div style="color:#555; margin-top:16px; font-size:13px;">
                Yeh link valid nahi hai ya expire ho chuka hai.<br>
                Admin se naya link mangwao.
            </div>
        </div>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    user = tokens[token]

    if not user.get("active", True):
        st.markdown(f"""
        <div style="background:#020408; min-height:100vh; display:flex;
             align-items:center; justify-content:center;">
        <div style="border:1px solid #ff8800; border-radius:16px; padding:60px 50px;
             text-align:center; max-width:480px; background:rgba(255,136,0,0.05);
             font-family:monospace;">
            <div style="font-size:64px; margin-bottom:24px;">🚫</div>
            <div style="color:#ff8800; font-size:20px; font-weight:bold; letter-spacing:3px;">
                ACCOUNT DISABLED
            </div>
            <div style="color:#555; margin-top:16px; font-size:13px;">
                <strong style="color:#fff;">{user['name']}</strong> — tera access band hai.<br>
                Umer Ali se rabta karo.
            </div>
        </div>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    expiry = datetime.strptime(user["expires"], "%Y-%m-%d")
    if datetime.now() > expiry:
        st.markdown(f"""
        <div style="background:#020408; min-height:100vh; display:flex;
             align-items:center; justify-content:center;">
        <div style="border:1px solid #ffdd00; border-radius:16px; padding:60px 50px;
             text-align:center; max-width:480px; background:rgba(255,221,0,0.05);
             font-family:monospace;">
            <div style="font-size:64px; margin-bottom:24px;">⏰</div>
            <div style="color:#ffdd00; font-size:20px; font-weight:bold; letter-spacing:3px;">
                TOKEN EXPIRED
            </div>
            <div style="color:#555; margin-top:16px; font-size:13px;">
                Tera token <strong style="color:#fff;">{user['expires']}</strong> ko expire ho gaya.<br>
                Admin se naya token mangwao.
            </div>
        </div>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    client_ip = get_client_ip()

    if user.get("locked_ip") is None:
        tokens[token]["locked_ip"] = client_ip
        save_tokens(tokens)
    elif client_ip != "unknown" and user["locked_ip"] != client_ip:
        st.markdown(f"""
        <div style="background:#020408; min-height:100vh; display:flex;
             align-items:center; justify-content:center;">
        <div style="border:1px solid #ff006e; border-radius:16px; padding:60px 50px;
             text-align:center; max-width:480px; background:rgba(255,0,110,0.07);
             font-family:monospace;">
            <div style="font-size:64px; margin-bottom:24px;">🚨</div>
            <div style="color:#ff006e; font-size:20px; font-weight:bold; letter-spacing:3px;">
                SECURITY VIOLATION
            </div>
            <div style="color:#555; margin-top:16px; font-size:13px; line-height:2;">
                Yeh token already kisi aur device par lock hai.<br>
                <strong style="color:#ff006e;">Token sharing detected!</strong><br>
                Umer Ali se contact karo.
            </div>
        </div>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    return user["name"]
