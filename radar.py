import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import phonenumbers
from phonenumbers import geocoder
import threading
import json
import hashlib

# ============================================================
# CONFIG
# ============================================================
URL               = "http://51.77.216.195/crapi/lamix/viewstats"
TOKEN             = "aXZ0gVZXgoCAc2loX4iFSl9mVWB8hVdgdFVhW3SVZXM="
TEAM_FILE         = "Numbers_Export.csv"
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyTHahQPjxjbuZGcIWiN2AgY8lHJEDm7Pyi2QnpSJVV436Q65DOlOtmA2Ilux8UkVgl/exec"
REGISTRY_URL      = "https://script.google.com/macros/s/AKfycbzo_Z_7CEVEeKA9fL-M3WXtznKrd19MyiXTksRlbSd1E8bNXh8nZF5HsLdedOjG2iVF/exec"
ADMIN_KEY         = "UTS_ADMIN_2024"

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(page_title="UTS HUNTERS", page_icon="\u26a1", layout="wide")

# ============================================================
# CSS — COMPLETE REDESIGN: CYBERPUNK COMMAND CENTER
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700;800&family=Orbitron:wght@400;600;700;800;900&family=Rajdhani:wght@300;400;500;600;700&display=swap');

    :root {
        --bg:#03060f; --bg2:#070d1c; --card:#0b1428; --card2:#0d1830;
        --b1:#152038; --b2:#1e2d4d; --b3:#2a3f66;
        --neon:#00f0ff; --neon-d:#0099bb; --neon-glow:rgba(0,240,255,.15);
        --purple:#b347ff; --purple-d:#7a1fbd;
        --gold:#ffd700; --gold-d:#c9a700;
        --silver:#d0d8e8; --bronze:#cd7f32;
        --green:#00ff88; --green-d:#00aa5a;
        --red:#ff2d55; --red-d:#cc1a3e;
        --orange:#ff8c00;
        --t1:#e0ecff; --t2:#6a8cb0; --t3:#3a5070; --t4:#1a2a45;
    }

    /* === BACKGROUND === */
    .stApp {
        background-color:var(--bg) !important;
        background-image:
            linear-gradient(rgba(0,240,255,.02) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,240,255,.02) 1px, transparent 1px),
            radial-gradient(ellipse at 15% 0%, rgba(0,240,255,.06) 0%, transparent 50%),
            radial-gradient(ellipse at 85% 100%, rgba(179,71,255,.05) 0%, transparent 50%),
            radial-gradient(ellipse at 50% 50%, rgba(0,100,200,.03) 0%, transparent 70%);
        background-size: 40px 40px, 40px 40px, 100% 100%, 100% 100%, 100% 100%;
        font-family:'Rajdhani',sans-serif;
    }

    /* === ANIMATED SCANLINE OVERLAY === */
    .stApp::before {
        content:""; position:fixed; top:0; left:0; right:0; bottom:0;
        background:linear-gradient(180deg, transparent 0%, rgba(0,240,255,.015) 50%, transparent 100%);
        background-size:100% 4px; pointer-events:none; z-index:9999;
        animation: scan 8s linear infinite;
    }
    @keyframes scan { 0%{background-position:0 0} 100%{background-position:0 100vh} }

    /* === HEADER === */
    .hdr {
        text-align:center; padding:40px 20px 12px; position:relative;
    }
    .hdr::after {
        content:""; position:absolute; bottom:0; left:50%; transform:translateX(-50%);
        width:60%; height:2px;
        background:linear-gradient(90deg, transparent, var(--neon), var(--purple), transparent);
        box-shadow:0 0 20px var(--neon-glow);
    }
    .badge {
        display:inline-block; position:relative;
        background:linear-gradient(135deg, var(--bg2), var(--card));
        border:1px solid var(--neon-d); border-radius:2px;
        padding:5px 24px; font-family:'Orbitron',monospace;
        font-size:10px; font-weight:700; color:var(--neon);
        letter-spacing:8px; text-transform:uppercase; margin-bottom:16px;
        box-shadow:0 0 15px rgba(0,240,255,.1), inset 0 0 15px rgba(0,240,255,.05);
    }
    .badge::before, .badge::after {
        content:""; position:absolute; top:50%; transform:translateY(-50%);
        width:30px; height:1px; background:var(--neon-d);
    }
    .badge::before { left:-35px; }
    .badge::after { right:-35px; }
    .title {
        font-family:'Orbitron',sans-serif; font-size:56px; font-weight:900;
        color:#fff; letter-spacing:2px; line-height:1; margin-bottom:8px;
        text-shadow:0 0 40px rgba(0,240,255,.3);
    }
    .title span {
        background:linear-gradient(135deg, var(--neon), var(--purple));
        -webkit-background-clip:text; -webkit-text-fill-color:transparent;
        background-clip:text; filter:drop-shadow(0 0 20px rgba(0,240,255,.4));
    }
    .sub {
        font-family:'JetBrains Mono',monospace; font-size:11px; color:var(--t2);
        letter-spacing:5px; text-transform:uppercase; margin-bottom:30px;
    }

    /* === OPERATOR BAR === */
    .opbar {
        display:flex; justify-content:center; align-items:center; gap:0;
        padding:0; margin-bottom:28px; font-family:'JetBrains Mono',monospace;
        font-size:11px; flex-wrap:wrap;
    }
    .op-item {
        display:flex; align-items:center; gap:8px;
        padding:10px 20px; color:var(--t2);
        background:linear-gradient(180deg, var(--bg2), var(--card));
        border-top:1px solid var(--b2); border-bottom:1px solid var(--b2);
        position:relative;
    }
    .op-item:first-child { border-left:1px solid var(--b2); border-radius:4px 0 0 4px; }
    .op-item:last-child { border-right:1px solid var(--b2); border-radius:0 4px 4px 0; }
    .op-item + .op-item { border-left:1px solid var(--b1); }
    .op-item span { color:var(--neon); font-weight:700; }
    .op-sep { color:var(--t4); }

    /* === PULSE DOT === */
    .pulse-dot {
        display:inline-block; width:8px; height:8px; border-radius:50%;
        background:var(--green); box-shadow:0 0 8px var(--green), 0 0 16px var(--green);
        animation:pulse 1.5s ease-in-out infinite; margin-right:8px;
    }
    @keyframes pulse {
        0%,100%{opacity:1;transform:scale(1);box-shadow:0 0 8px var(--green),0 0 16px var(--green)}
        50%{opacity:.5;transform:scale(.7);box-shadow:0 0 4px var(--green)}
    }

    /* === SECTION LABEL === */
    .sl {
        font-family:'Orbitron',monospace; font-size:12px; font-weight:700;
        color:var(--t1); letter-spacing:4px; text-transform:uppercase;
        margin-top:36px; margin-bottom:16px; padding:12px 0;
        display:flex; align-items:center; gap:12px;
        border-bottom:1px solid var(--b2); position:relative;
    }
    .sl::before {
        content:""; width:4px; height:18px; border-radius:1px;
        background:linear-gradient(180deg, var(--neon), var(--purple));
        box-shadow:0 0 10px var(--neon-glow);
    }
    .sl::after {
        content:""; position:absolute; bottom:-1px; left:0; width:80px; height:1px;
        background:linear-gradient(90deg, var(--neon), transparent);
    }

    /* === STAT CARDS === */
    .stat-grid {
        display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:28px;
    }
    .stat-card {
        background:linear-gradient(145deg, var(--card), var(--bg2));
        border:1px solid var(--b2); border-radius:8px; padding:18px 20px;
        text-align:center; position:relative; overflow:hidden;
        transition:all .3s ease;
    }
    .stat-card::before {
        content:""; position:absolute; top:0; left:0; right:0; height:2px;
        background:linear-gradient(90deg, transparent, var(--neon), transparent);
        opacity:.5;
    }
    .stat-card::after {
        content:""; position:absolute; bottom:0; left:0; right:0; height:1px;
        background:linear-gradient(90deg, transparent, var(--b3), transparent);
    }
    .stat-val {
        font-family:'Orbitron',monospace; font-size:32px; font-weight:800;
        background:linear-gradient(135deg, var(--neon), #80ffff);
        -webkit-background-clip:text; -webkit-text-fill-color:transparent;
        background-clip:text; line-height:1.1;
    }
    .stat-label {
        font-family:'JetBrains Mono',monospace; font-size:9px; color:var(--t2);
        letter-spacing:2px; text-transform:uppercase; margin-top:6px;
    }

    /* === LEADERBOARD === */
    .lb-grid {
        display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-bottom:28px;
    }
    .lb-card {
        background:linear-gradient(145deg, var(--card), var(--bg2));
        border:1px solid var(--b2); border-radius:10px; padding:24px 22px;
        position:relative; overflow:hidden;
        transition:all .3s ease;
    }
    .lb-card:hover { transform:translateY(-3px); border-color:var(--accent); }
    .lb-card::before {
        content:""; position:absolute; top:0; left:0; right:0; height:3px;
        background:var(--accent); box-shadow:0 0 15px var(--accent);
    }
    .lb-1 { --accent:var(--gold); border-left:3px solid var(--gold); }
    .lb-2 { --accent:var(--silver); border-left:3px solid var(--silver); }
    .lb-3 { --accent:var(--bronze); border-left:3px solid var(--bronze); }
    .lb-rank {
        position:absolute; right:18px; top:50%; transform:translateY(-50%);
        font-family:'Orbitron',sans-serif; font-size:64px; font-weight:900;
        color:var(--accent); opacity:.06;
    }
    .lb-label {
        font-family:'JetBrains Mono',monospace; font-size:10px; font-weight:700;
        letter-spacing:2px; text-transform:uppercase; margin-bottom:12px;
        color:var(--accent);
    }
    .lb-name {
        font-family:'Rajdhani',sans-serif; font-size:28px; font-weight:700;
        color:#fff; text-transform:uppercase; overflow:hidden;
        text-overflow:ellipsis; white-space:nowrap; margin-bottom:8px;
    }
    .lb-count {
        font-family:'JetBrains Mono',monospace; font-size:13px; font-weight:600;
        color:var(--neon);
    }
    .lb-count::before {
        content:"\u26a1 "; color:var(--accent);
    }

    /* === INPUTS === */
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        background:linear-gradient(145deg, var(--bg2), var(--card)) !important;
        color:var(--t1) !important;
        border:1px solid var(--b2) !important; border-radius:6px !important;
        font-family:'JetBrains Mono',monospace !important; font-size:13px !important;
        box-shadow:inset 0 0 10px rgba(0,240,255,.03) !important;
        transition:all .3s ease !important;
    }
    .stTextInput>div>div>input:focus, .stNumberInput>div>div>input:focus {
        border-color:var(--neon-d) !important;
        box-shadow:0 0 15px rgba(0,240,255,.1), inset 0 0 10px rgba(0,240,255,.05) !important;
    }
    label {
        color:var(--t2) !important; font-family:'JetBrains Mono',monospace !important;
        font-size:11px !important; letter-spacing:1px !important;
    }

    /* === TABS === */
    .stTabs [data-baseweb="tab-list"] {
        background:linear-gradient(180deg, var(--bg2), var(--card)) !important;
        border:1px solid var(--b2) !important; border-radius:8px !important;
        gap:0 !important; padding:4px !important; margin-bottom:8px !important;
    }
    .stTabs [data-baseweb="tab"] {
        background:transparent !important; color:var(--t2) !important;
        font-family:'Orbitron',monospace !important; font-size:11px !important;
        font-weight:600 !important; letter-spacing:3px !important;
        text-transform:uppercase !important; border-radius:6px !important;
        padding:12px 24px !important; border:1px solid transparent !important;
        transition:all .3s ease !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color:var(--t1) !important; background:rgba(0,240,255,.05) !important;
    }
    .stTabs [aria-selected="true"] {
        color:var(--neon) !important;
        background:linear-gradient(135deg, rgba(0,240,255,.08), rgba(179,71,255,.05)) !important;
        border:1px solid var(--neon-d) !important;
        box-shadow:0 0 15px rgba(0,240,255,.1) !important;
    }
    .stTabs [data-baseweb="tab-panel"] { background:transparent !important; padding-top:20px !important; }

    /* === BUTTONS === */
    .stButton>button {
        background:linear-gradient(135deg, var(--neon-d), var(--purple-d)) !important;
        color:#fff !important; border:1px solid var(--neon) !important;
        border-radius:6px !important; font-family:'Orbitron',monospace !important;
        font-size:12px !important; font-weight:700 !important; letter-spacing:2px !important;
        padding:10px 32px !important; text-transform:uppercase !important;
        box-shadow:0 0 15px rgba(0,240,255,.15) !important;
        transition:all .3s ease !important;
    }
    .stButton>button:hover {
        background:linear-gradient(135deg, var(--neon), var(--purple)) !important;
        box-shadow:0 0 25px rgba(0,240,255,.3) !important; transform:translateY(-1px);
    }

    /* === SCROLLBAR === */
    ::-webkit-scrollbar { width:6px; height:6px; }
    ::-webkit-scrollbar-track { background:var(--bg); }
    ::-webkit-scrollbar-thumb {
        background:linear-gradient(180deg, var(--neon-d), var(--purple-d));
        border-radius:3px;
    }

    /* === LOGIN CARD === */
    .login-card {
        background:linear-gradient(145deg, var(--card), var(--bg2));
        border:1px solid var(--b2); border-radius:16px; padding:52px 44px;
        box-shadow:0 30px 80px rgba(0,0,0,.6), 0 0 40px rgba(0,240,255,.05);
        position:relative; overflow:hidden;
    }
    .login-card::before {
        content:""; position:absolute; top:0; left:0; right:0; height:3px;
        background:linear-gradient(90deg, var(--neon), var(--purple), var(--neon));
        box-shadow:0 0 20px var(--neon-glow);
    }
    .login-card::after {
        content:""; position:absolute; bottom:0; left:0; right:0; height:1px;
        background:linear-gradient(90deg, transparent, var(--b3), transparent);
    }
    .login-icon {
        font-size:56px; text-align:center; margin-bottom:16px;
        filter:drop-shadow(0 0 20px rgba(0,240,255,.4));
        animation:glow-pulse 3s ease-in-out infinite;
    }
    @keyframes glow-pulse {
        0%,100%{filter:drop-shadow(0 0 15px rgba(0,240,255,.3))}
        50%{filter:drop-shadow(0 0 30px rgba(0,240,255,.6))}
    }
    .login-title {
        font-family:'Orbitron',sans-serif; font-size:28px; font-weight:900;
        color:#fff; text-align:center; margin-bottom:6px; letter-spacing:2px;
    }
    .login-sub {
        font-family:'JetBrains Mono',monospace; font-size:10px; color:var(--t3);
        letter-spacing:4px; text-transform:uppercase; text-align:center; margin-bottom:32px;
    }
    .login-error {
        background:linear-gradient(135deg, rgba(255,45,85,.08), rgba(255,45,85,.03));
        border:1px solid rgba(255,45,85,.3); border-radius:6px;
        padding:12px 18px; font-family:'JetBrains Mono',monospace;
        font-size:11px; color:var(--red); margin-top:14px;
        box-shadow:0 0 15px rgba(255,45,85,.05);
    }
    .login-footer {
        margin-top:24px; font-family:'JetBrains Mono',monospace; font-size:9px;
        color:var(--t4); text-align:center; line-height:2.2;
    }
    .login-footer span { color:var(--t3); }

    /* === ADMIN PANEL CARDS === */
    .admin-card {
        background:linear-gradient(145deg, var(--card), var(--bg2));
        border:1px solid var(--b2); border-radius:10px; padding:28px;
        margin-bottom:24px; position:relative; overflow:hidden;
    }
    .admin-card::before {
        content:""; position:absolute; top:0; left:0; right:0; height:2px;
        background:linear-gradient(90deg, var(--purple), var(--neon));
    }
    .admin-title {
        font-family:'Orbitron',monospace; font-size:12px; font-weight:700;
        color:var(--neon); letter-spacing:3px; text-transform:uppercase;
        margin-bottom:20px; padding-bottom:10px; border-bottom:1px solid var(--b2);
        display:flex; align-items:center; gap:10px;
    }
    .admin-title::before {
        content:""; width:6px; height:6px; border-radius:50%;
        background:var(--neon); box-shadow:0 0 8px var(--neon);
    }

    /* === DATAFRAME STYLING === */
    .stDataFrame { border:1px solid var(--b2); border-radius:8px; overflow:hidden; }

    /* === REFRESH INDICATOR === */
    .refresh-indicator {
        text-align:center; font-family:'JetBrains Mono',monospace; font-size:10px;
        color:var(--t3); margin-top:24px; padding:12px;
        border-top:1px solid var(--b1);
    }
    .refresh-indicator span { color:var(--neon); }

    /* === UTILITY === */
    .info-msg {
        text-align:center; padding:40px; font-family:'JetBrains Mono',monospace;
        font-size:13px; color:var(--t2);
    }
    .info-msg span { color:var(--neon); font-size:28px; display:block; margin-bottom:12px; }
    .error-msg {
        text-align:center; padding:30px; font-family:'JetBrains Mono',monospace;
        font-size:13px; color:var(--red);
    }
    .error-msg span { font-size:32px; display:block; margin-bottom:12px; }
    .warn-msg {
        text-align:center; padding:30px; font-family:'JetBrains Mono',monospace;
        font-size:13px; color:var(--orange);
    }
    .warn-msg span { font-size:32px; display:block; margin-bottom:12px; }

    /* === HIDE STREAMLIT BRANDING === */
    #MainMenu { visibility:hidden; }
    footer { visibility:hidden; }
    header[data-testid="stHeader"] { background:transparent !important; }
    .stDeployButton { display:none; }

    /* === DATAFRAME HEADER === */
    .stDataFrame [data-testid="stDataFrameResizable"] {
        border:1px solid var(--b2); border-radius:8px;
    }

    /* === SPINNER === */
    .stSpinner>div { border-color:var(--neon) !important; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# SERVER-SIDE DEVICE FINGERPRINT
# ============================================================
def get_server_side_fp() -> str:
    try:
        headers = st.context.headers
        ua      = headers.get("User-Agent", "unknown")
        lang    = headers.get("Accept-Language", "")
        enc     = headers.get("Accept-Encoding", "")
        raw = f"{ua}|{lang}|{enc}"
        fp  = "FP" + hashlib.sha256(raw.encode()).hexdigest()[:20].upper()
        return fp
    except Exception:
        try:
            import streamlit.web.server.websocket_headers as wh
            headers = wh.get_websocket_headers()
            ua   = headers.get("User-Agent", "unknown")
            raw  = f"{ua}"
            return "FP" + hashlib.sha256(raw.encode()).hexdigest()[:20].upper()
        except Exception:
            return "FP_FALLBACK"


# ============================================================
# REGISTRY API
# ============================================================
def check_code_api(code: str, fp: str) -> dict:
    try:
        payload = {"action": "check_code", "code": code.strip().upper(), "fp": fp, "ip": ""}
        r = requests.post(REGISTRY_URL, data=json.dumps(payload),
                          headers={"Content-Type": "application/json"}, timeout=15)
        return r.json()
    except Exception as e:
        return {"success": False, "msg": f"Connection error: {str(e)}"}

def generate_codes_api(count: int, prefix: str = "UTS") -> dict:
    try:
        payload = {"action": "generate_codes", "count": count,
                   "prefix": prefix, "admin_key": ADMIN_KEY}
        r = requests.post(REGISTRY_URL, data=json.dumps(payload),
                          headers={"Content-Type": "application/json"}, timeout=20)
        return r.json()
    except Exception as e:
        return {"success": False, "msg": str(e)}

def deactivate_code_api(code: str) -> dict:
    try:
        payload = {"action": "deactivate_code", "code": code, "admin_key": ADMIN_KEY}
        r = requests.post(REGISTRY_URL, data=json.dumps(payload),
                          headers={"Content-Type": "application/json"}, timeout=15)
        return r.json()
    except Exception as e:
        return {"success": False, "msg": str(e)}

def list_codes_api() -> dict:
    try:
        payload = {"action": "list_codes", "admin_key": ADMIN_KEY}
        r = requests.post(REGISTRY_URL, data=json.dumps(payload),
                          headers={"Content-Type": "application/json"}, timeout=15)
        return r.json()
    except Exception as e:
        return {"success": False, "msg": str(e)}


# ============================================================
# GET FINGERPRINT
# ============================================================
device_fp = get_server_side_fp()


# ============================================================
# AUTH FLOW
# ============================================================
if not st.session_state.get("authenticated"):

    st.markdown("""
    <div class="hdr">
        <div class="badge">UTS SYSTEMS</div>
        <div class="title">\u26a1 UTS <span>HUNTERS</span> \u26a1</div>
        <div class="sub">> Authorized Access Only</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("""
        <div class="login-icon">\u26a1</div>
        <div class="login-title">UTS HUNTERS</div>
        <div class="login-sub">Enter Activation Code</div>
        """, unsafe_allow_html=True)

        entered_code = st.text_input("\U0001f511 ACTIVATION CODE:", placeholder="UTS-XXXXXXXXXXXX", key="login_code")

        if st.button("\u25b6  ACTIVATE SESSION", key="login_btn"):
            if entered_code.strip():
                with st.spinner("Verifying..."):
                    result = check_code_api(entered_code.strip(), device_fp)
                if result.get("success"):
                    st.session_state["authenticated"]  = True
                    st.session_state["operator_name"]  = result.get("operator", "OPERATOR")
                    st.session_state["auth_code"]      = entered_code.strip().upper()
                    st.rerun()
                else:
                    msg = result.get("msg", "UNKNOWN ERROR")
                    st.markdown(f'<div class="login-error">\u26d4 ACCESS DENIED \u2014 {msg}</div>',
                                unsafe_allow_html=True)
            else:
                st.markdown('<div class="login-error">\u26a0 Enter your activation code.</div>',
                            unsafe_allow_html=True)

        st.markdown(f"""
        <div class="login-footer">
            \U0001f512 Device ID: {device_fp[:20]}...<br>
            <span>Each code is device-locked. Contact admin for access.</span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.stop()


# ============================================================
# AUTHENTICATED
# ============================================================
operator_name = st.session_state.get("operator_name", "OPERATOR")
is_admin      = (operator_name == "Umer Ali")


def get_country(num):
    try:
        parsed = phonenumbers.parse("+" + str(num).strip())
        return geocoder.description_for_number(parsed, "en")
    except:
        return "Global"

@st.cache_data(ttl=300)
def load_team_data():
    try:
        df = pd.read_csv(TEAM_FILE)
        df['Phone Number'] = df['Phone Number'].astype(str).str.split('.').str[0].str.strip()
        df['Status']       = df['Status'].fillna('')
        df['MemberName']   = df['Status'].str.replace('Allocated: ', '', case=False, regex=False).str.strip()
        return df.set_index('Phone Number')[['Range', 'MemberName']].to_dict('index')
    except:
        return {}

def get_team_info(num, team_data):
    n = str(num).split('.')[0].strip()
    if n in team_data:
        name = team_data[n]['MemberName']
        if name in ["UTS_Umer1", "UTS_Khadija"]: return "", ""
        return name, team_data[n]['Range']
    return "", ""

def highlight_team(row):
    if row.get('Team Member', '') != "":
        return ['background-color:rgba(0,240,255,.06);color:#00f0ff;font-weight:bold;border-right:3px solid #00f0ff'] * len(row)
    return [''] * len(row)

def stream_to_google_sheet(raw_data):
    try:
        bg = pd.DataFrame(raw_data)
        if bg.empty: return
        bg['dt'] = pd.to_datetime(bg['dt']).dt.strftime('%Y-%m-%d %H:%M:%S')
        for _, row in bg.head(20).iterrows():
            requests.post(GOOGLE_SCRIPT_URL,
                data=json.dumps({"Time": row['dt'], "App": row['cli'],
                    "Number": str(row['num']), "Country": get_country(row['num']),
                    "Message": str(row['message'])}),
                headers={'Content-Type': 'application/json'}, timeout=5)
    except: pass


# ============================================================
# HEADER
# ============================================================
st.markdown(f"""
<div class="hdr">
    <div class="badge">UTS SYSTEMS</div>
    <div class="title">\u26a1 UTS <span>HUNTERS</span> \u26a1</div>
    <div class="sub">> Database Integrated Control Panel</div>
</div>
<div class="opbar">
    <div class="op-item"><span class="pulse-dot"></span><span>LIVE</span></div>
    <div class="op-item">OPERATOR: <span>{operator_name.upper()}</span></div>
    <div class="op-item">SESSION: <span>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></div>
    <div class="op-item">STATUS: <span style="color:#00ff88">\u2713 AUTHORIZED</span></div>
    {"<div class='op-item'><span style='color:#ffd700'>\U0001f451 ADMIN MODE</span></div>" if is_admin else ""}
</div>
""", unsafe_allow_html=True)


# ============================================================
# TABS
# ============================================================
tab_labels = ["\U0001f4e1  LIVE MONITORING", "\U0001f4ca  SHEET DATABASE"]
if is_admin: tab_labels.append("\U0001f510  ADMIN PANEL")
tab_objs = st.tabs(tab_labels)
tab1, tab2 = tab_objs[0], tab_objs[1]
tab3 = tab_objs[2] if is_admin else None

with tab1:
    c1, c2 = st.columns([2, 1])
    with c1: target_cli = st.text_input("\u2699 TARGET AGENT (CLI):", "MYOB").strip()
    with c2: msg_limit  = st.number_input("\U0001f4e1 STREAM BUFFER:", min_value=1, max_value=2000, value=500)
    placeholder = st.empty()

with tab2:
    st.markdown('<div class="sl">REAL-TIME FILTERS \u2014 GOOGLE SHEET DATABASE</div>', unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    with f1: filter_cli = st.text_input("\U0001f50d App/CLI:", "").strip()
    with f2: filter_num = st.text_input("\U0001f4de Number:", "").strip()
    with f3: filter_msg = st.text_input("\U0001f4ac Message:", "").strip()
    history_placeholder = st.empty()

if is_admin and tab3:
    with tab3:
        st.markdown('<div class="sl">CODE GENERATION</div>', unsafe_allow_html=True)
        st.markdown('<div class="admin-card"><div class="admin-title">\u26a1 Generate New Codes</div>', unsafe_allow_html=True)
        g1, g2, g3 = st.columns([1, 1, 2])
        with g1: gen_count  = st.number_input("How many?", min_value=1, max_value=50, value=5)
        with g2: gen_prefix = st.text_input("Prefix:", value="UTS")
        with g3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("\u26a1 GENERATE", key="gen_btn"):
                with st.spinner("Generating..."):
                    res = generate_codes_api(int(gen_count), gen_prefix)
                if res.get("success"):
                    st.success(f"\u2705 {len(res['codes'])} codes generated!")
                    st.code("\n".join(res['codes']), language=None)
                    st.caption("Give each code to ONE person only.")
                else:
                    st.error(f"\u274c {res.get('msg')}")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="sl">ALL CODES</div>', unsafe_allow_html=True)
        col_r, _ = st.columns([1, 4])
        with col_r:
            if st.button("\U0001f504 REFRESH", key="ref_btn"):
                st.session_state["codes_list"] = None

        if st.button("\U0001f4cb LOAD ALL CODES", key="load_codes") or st.session_state.get("codes_list"):
            if not st.session_state.get("codes_list"):
                with st.spinner("Loading..."):
                    res = list_codes_api()
                if res.get("success"):
                    st.session_state["codes_list"] = res.get("codes", [])
                else:
                    st.error(f"Error: {res.get('msg')}")

            codes_list = st.session_state.get("codes_list", [])
            if codes_list:
                cdf = pd.DataFrame(codes_list)
                def cs(v):
                    if v == "ACTIVE":      return "color:#00ff88;font-weight:bold"
                    if v == "DEACTIVATED": return "color:#ff2d55;font-weight:bold"
                    return "color:#ffd700"
                st.dataframe(cdf.style.map(cs, subset=["status"]),
                    use_container_width=True, hide_index=True,
                    column_config={
                        "code":         st.column_config.TextColumn("ACTIVATION CODE", width="large"),
                        "operator":     st.column_config.TextColumn("OPERATOR",        width="medium"),
                        "status":       st.column_config.TextColumn("STATUS",          width="small"),
                        "created":      st.column_config.TextColumn("CREATED",         width="medium"),
                        "activated_at": st.column_config.TextColumn("LOCKED AT",       width="medium"),
                        "last_seen":    st.column_config.TextColumn("LAST SEEN",       width="medium"),
                    })

                st.markdown('<div class="admin-card"><div class="admin-title">\U0001f512 Deactivate / Reset Code</div>', unsafe_allow_html=True)
                d1, d2 = st.columns([2, 1])
                with d1:
                    deact_code = st.text_input("Code to deactivate:", placeholder="UTS-XXXXXXXXXXXX", key="deact_in")
                with d2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("\U0001f6ab DEACTIVATE", key="deact_btn"):
                        if deact_code.strip():
                            with st.spinner("Processing..."):
                                r2 = deactivate_code_api(deact_code.strip().upper())
                            if r2.get("success"):
                                st.success("\u2705 Deactivated! Device lock removed.")
                                st.session_state["codes_list"] = None
                                st.rerun()
                            else:
                                st.error(f"\u274c {r2.get('msg')}")
                st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# LOAD TEAM DATA & COLUMN CONFIG
# ============================================================
team_data = load_team_data()
col_cfg = {
    "Time":        st.column_config.TextColumn("TIMESTAMP",     width="medium"),
    "App":         st.column_config.TextColumn("IDENT/CLI",     width="small"),
    "Number":      st.column_config.TextColumn("DATA STREAM",   width="medium"),
    "Country":     st.column_config.TextColumn("LOCATION",      width="small"),
    "Message":     st.column_config.TextColumn("MESSAGE",       width="large"),
    "Team Member": st.column_config.TextColumn("OPERATOR",      width="medium"),
    "Range":       st.column_config.TextColumn("NETWORK RANGE", width="large"),
}


# ============================================================
# MAIN DATA FETCH (single pass, no while True loop)
# ============================================================
try:
    r = requests.get(URL, params={"token": TOKEN, "records": 500}, timeout=10)
    if r.status_code == 200:
        raw_json = r.json().get("data", [])
        df = pd.DataFrame(raw_json)
        if not df.empty:
            threading.Thread(target=stream_to_google_sheet, args=(raw_json,), daemon=True).start()
            df['dt'] = pd.to_datetime(df['dt'])
            now   = datetime.now()
            df_5m = df[df['dt'] >= now - timedelta(minutes=5)]

            t1n, t1c = "NO DATA", 0
            t2n, t2c = "NO DATA", 0
            t3n, t3c = "NO DATA", 0
            if not df_5m.empty and 'cli' in df_5m.columns:
                tc = df_5m['cli'].value_counts().head(3)
                if len(tc) >= 1: t1n, t1c = tc.index[0], int(tc.iloc[0])
                if len(tc) >= 2: t2n, t2c = tc.index[1], int(tc.iloc[1])
                if len(tc) >= 3: t3n, t3c = tc.index[2], int(tc.iloc[2])

            tr = len(df)
            uc = df['cli'].nunique() if 'cli' in df.columns else 0
            un = df['num'].nunique() if 'num' in df.columns else 0
            df_tgt = df[df['cli'].str.contains(target_cli, case=False, na=False)].copy()

            with placeholder.container():
                st.markdown(f"""
                <div class="stat-grid">
                    <div class="stat-card"><div class="stat-val">{tr}</div><div class="stat-label">Total Records</div></div>
                    <div class="stat-card"><div class="stat-val">{t1c}</div><div class="stat-label">Top CLI (5min)</div></div>
                    <div class="stat-card"><div class="stat-val">{uc}</div><div class="stat-label">Unique CLIs</div></div>
                    <div class="stat-card"><div class="stat-val">{un}</div><div class="stat-label">Unique Numbers</div></div>
                </div>
                <div class="lb-grid">
                    <div class="lb-card lb-1"><div class="lb-rank">1</div>
                        <div class="lb-label">\U0001f3c6 Top 1 \u2014 Last 5 Min</div>
                        <div class="lb-name">{t1n}</div><div class="lb-count">{t1c} OTPs</div></div>
                    <div class="lb-card lb-2"><div class="lb-rank">2</div>
                        <div class="lb-label">\U0001f948 Top 2 \u2014 Last 5 Min</div>
                        <div class="lb-name">{t2n}</div><div class="lb-count">{t2c} OTPs</div></div>
                    <div class="lb-card lb-3"><div class="lb-rank">3</div>
                        <div class="lb-label">\U0001f949 Top 3 \u2014 Last 5 Min</div>
                        <div class="lb-name">{t3n}</div><div class="lb-count">{t3c} OTPs</div></div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f'<div class="sl">LIVE TARGET TRACKER \u2014 AGENT: {target_cli.upper()}</div>', unsafe_allow_html=True)
                if not df_tgt.empty:
                    md = df_tgt.head(25).copy()
                    md[['Team Member', 'Range']] = md['num'].apply(lambda x: pd.Series(get_team_info(x, team_data)))
                    md['Country'] = md['num'].apply(get_country)
                    md = md[['dt','cli','num','Country','message','Team Member','Range']].copy()
                    md.columns = ['Time','App','Number','Country','Message','Team Member','Range']
                    md['Time'] = pd.to_datetime(md['Time'])
                    md = md.sort_values('Time', ascending=False)
                    md['Time'] = md['Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
                    st.dataframe(md.style.apply(highlight_team, axis=1),
                                 use_container_width=True, height=400, hide_index=True, column_config=col_cfg)
                else:
                    st.markdown('<div class="info-msg"><span>\u25b8</span>No packets for current target agent.</div>', unsafe_allow_html=True)

                st.markdown('<div class="sl">GLOBAL LIVE NETWORK STREAM</div>', unsafe_allow_html=True)
                gd = df.head(msg_limit).copy()
                gd[['Team Member', 'Range']] = gd['num'].apply(lambda x: pd.Series(get_team_info(x, team_data)))
                gd['Country'] = gd['num'].apply(get_country)
                gd = gd[['dt','cli','num','Country','message','Team Member','Range']].copy()
                gd.columns = ['Time','App','Number','Country','Message','Team Member','Range']
                gd['Time'] = pd.to_datetime(gd['Time'])
                gd = gd.sort_values('Time', ascending=False)
                gd['Time'] = gd['Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
                st.dataframe(gd.style.apply(highlight_team, axis=1),
                             use_container_width=True, height=700, hide_index=True, column_config=col_cfg)
        else:
            with placeholder.container():
                st.markdown('<div class="info-msg"><span>\u23f3</span>Waiting for data stream...</div>', unsafe_allow_html=True)
    else:
        with placeholder.container():
            st.markdown(f'<div class="warn-msg"><span>\u26a0</span>API returned status {r.status_code}. Retrying...</div>', unsafe_allow_html=True)
except requests.exceptions.ConnectionError:
    with placeholder.container():
        st.markdown('<div class="error-msg"><span>\U0001f6a7</span>Cannot connect to data server (51.77.216.195).<br>Check if the server is online.</div>', unsafe_allow_html=True)
except requests.exceptions.Timeout:
    with placeholder.container():
        st.markdown('<div class="warn-msg"><span>\u23f3</span>Data server timed out. Will retry on next refresh.</div>', unsafe_allow_html=True)
except Exception as e:
    with placeholder.container():
        st.markdown(f'<div class="error-msg"><span>\u274c</span>Error: {str(e)}</div>', unsafe_allow_html=True)


# ============================================================
# SHEET DATABASE (separate try/except)
# ============================================================
try:
    sr = requests.get(GOOGLE_SCRIPT_URL, timeout=10)
    if sr.status_code == 200:
        sd = sr.json()
        if sd:
            sdf = pd.DataFrame(sd)
            if filter_cli: sdf = sdf[sdf['App'].astype(str).str.contains(filter_cli, case=False, na=False)]
            if filter_num: sdf = sdf[sdf['Number'].astype(str).str.contains(filter_num, na=False)]
            if filter_msg: sdf = sdf[sdf['Message'].astype(str).str.contains(filter_msg, case=False, na=False)]
            with history_placeholder.container():
                st.markdown(f"""
                <div style="font-family:'JetBrains Mono',monospace;font-size:11px;
                     color:var(--t2);margin-bottom:14px;padding:8px 16px;
                     background:linear-gradient(135deg,var(--bg2),var(--card));
                     border:1px solid var(--b2);border-radius:6px;display:inline-block">
                    <span style="color:var(--neon);font-weight:700;font-size:14px">{len(sdf)}</span>
                    <span style="margin-left:6px">PERMANENT RECORDS</span>
                </div>
                """, unsafe_allow_html=True)
                if not sdf.empty:
                    try:
                        sdf['Time'] = pd.to_datetime(sdf['Time'])
                        sdf = sdf.sort_values('Time', ascending=False)
                        sdf['Time'] = sdf['Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
                    except: pass
                    sdf[['Team Member', 'Range']] = sdf['Number'].apply(
                        lambda x: pd.Series(get_team_info(x, team_data)))
                    st.dataframe(sdf.style.apply(highlight_team, axis=1),
                                 use_container_width=True, height=600, hide_index=True, column_config=col_cfg)
                else:
                    st.markdown('<div class="info-msg"><span>\U0001f4c4</span>No records match current filters.</div>', unsafe_allow_html=True)
except Exception:
    pass


# ============================================================
# AUTO-REFRESH (replaces while True + st.rerun() loop)
# ============================================================
REFRESH_SECONDS = 15
st.markdown(
    f'<div class="refresh-indicator">\u21bb Auto-refresh in <span>{REFRESH_SECONDS}s</span> \u2014 System Online</div>',
    unsafe_allow_html=True
)
time.sleep(REFRESH_SECONDS)
st.rerun()
