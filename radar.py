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
st.set_page_config(page_title="UTS HUNTERS", page_icon="\u26a1", layout="wide",
                   initial_sidebar_state="expanded")

# ============================================================
# CSS — V4 "OBSIDIAN" — Deep Slate + Amber/Gold + Teal
# Completely new structure: sidebar nav, split login, hex stats
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500;600;700&family=Russo+One&display=swap');

    :root {
        --bg:#0c0f14; --bg2:#11161e; --card:#161c26; --card2:#1c2430;
        --b1:#222b38; --b2:#2e3a4c; --b3:#3d4d63;
        --amber:#f5a623; --amber-d:#c97e0a; --amber-glow:rgba(245,166,35,.1);
        --teal:#2dd4bf; --teal-d:#14a89a; --teal-glow:rgba(45,212,191,.1);
        --rose:#f43f5e; --rose-d:#cc2a45;
        --gold:#fbbf24; --silver:#cbd5e1; --bronze:#b87333;
        --green:#22c55e; --red:#ef4444; --orange:#f97316;
        --t1:#e2e8f0; --t2:#64748b; --t3:#334155; --t4:#1e293b;
    }

    /* === BACKGROUND — subtle layered === */
    .stApp {
        background-color:var(--bg) !important;
        background-image:
            radial-gradient(circle at 0% 0%, rgba(245,166,35,.03) 0%, transparent 35%),
            radial-gradient(circle at 100% 100%, rgba(45,212,191,.03) 0%, transparent 35%);
        font-family:'Chakra Petch',sans-serif;
    }

    /* === SIDEBAR === */
    section[data-testid="stSidebar"] {
        background:linear-gradient(180deg, var(--bg2), var(--bg)) !important;
        border-right:1px solid var(--b1) !important;
    }
    section[data-testid="stSidebar"] .stMarkdown {
        font-family:'Chakra Petch',sans-serif;
    }

    /* === SIDEBAR NAV ITEMS === */
    .nav-header {
        font-family:'Russo One',sans-serif; font-size:18px; font-weight:400;
        color:var(--amber); letter-spacing:2px; text-transform:uppercase;
        padding:20px 0 10px; border-bottom:1px solid var(--b1); margin-bottom:16px;
    }
    .nav-item {
        display:flex; align-items:center; gap:12px;
        padding:12px 16px; margin:4px 0; border-radius:8px;
        font-family:'Chakra Petch',sans-serif; font-size:13px; font-weight:500;
        color:var(--t2); cursor:pointer; transition:all .2s ease;
        border:1px solid transparent;
    }
    .nav-item:hover {
        background:var(--card); color:var(--t1); border-color:var(--b1);
    }
    .nav-item.active {
        background:rgba(245,166,35,.06); color:var(--amber);
        border-color:var(--amber-d);
    }
    .nav-item .nav-icon { font-size:18px; }
    .nav-divider { height:1px; background:var(--b1); margin:16px 0; }
    .nav-stat {
        padding:12px 16px; font-family:'JetBrains Mono',monospace;
        font-size:10px; color:var(--t3); line-height:2;
    }
    .nav-stat span { color:var(--teal); font-weight:600; }

    /* === TOP BAR === */
    .topbar {
        display:flex; justify-content:space-between; align-items:center;
        padding:16px 28px; background:var(--card);
        border:1px solid var(--b1); border-radius:12px; margin-bottom:24px;
    }
    .topbar-left {
        display:flex; align-items:center; gap:16px;
    }
    .topbar-logo {
        font-family:'Russo One',sans-serif; font-size:22px; font-weight:400;
        color:var(--t1); letter-spacing:2px;
    }
    .topbar-logo span { color:var(--amber); }
    .topbar-badge {
        font-family:'JetBrains Mono',monospace; font-size:9px; font-weight:600;
        color:var(--teal); background:rgba(45,212,191,.08);
        border:1px solid var(--teal-d); border-radius:4px;
        padding:3px 10px; letter-spacing:2px; text-transform:uppercase;
    }
    .topbar-right {
        display:flex; align-items:center; gap:20px;
        font-family:'JetBrains Mono',monospace; font-size:11px; color:var(--t2);
    }
    .topbar-right .live-dot {
        display:inline-block; width:8px; height:8px; border-radius:50%;
        background:var(--green); box-shadow:0 0 8px var(--green);
        animation:blink 1.5s infinite; margin-right:6px;
    }
    @keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }
    .topbar-right span { color:var(--amber); font-weight:600; }

    /* === SECTION HEADER === */
    .sec-h {
        font-family:'Russo One',sans-serif; font-size:16px; font-weight:400;
        color:var(--t1); letter-spacing:3px; text-transform:uppercase;
        margin:28px 0 16px; display:flex; align-items:center; gap:14px;
    }
    .sec-h::before {
        content:""; width:24px; height:2px; border-radius:1px;
        background:var(--amber);
    }
    .sec-h::after {
        content:""; flex:1; height:1px; background:var(--b1);
    }

    /* === STAT TILES — hexagon-inspired rounded === */
    .stat-row {
        display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:28px;
    }
    .stat-tile {
        background:var(--card); border:1px solid var(--b1); border-radius:16px;
        padding:24px 20px; text-align:center; position:relative; overflow:hidden;
        transition:all .3s ease;
    }
    .stat-tile:hover { border-color:var(--b2); transform:translateY(-2px); }
    .stat-tile::before {
        content:""; position:absolute; top:0; left:50%; transform:translateX(-50%);
        width:40%; height:3px; border-radius:0 0 4px 4px;
        background:var(--tile-c, var(--amber));
    }
    .stat-tile.t1 { --tile-c:var(--amber); }
    .stat-tile.t2 { --tile-c:var(--teal); }
    .stat-tile.t3 { --tile-c:var(--rose); }
    .stat-tile.t4 { --tile-c:var(--green); }
    .stat-num {
        font-family:'Russo One',sans-serif; font-size:34px; font-weight:400;
        color:var(--tile-c, var(--amber)); line-height:1.1; margin-bottom:4px;
    }
    .stat-txt {
        font-family:'JetBrains Mono',monospace; font-size:9px; color:var(--t2);
        letter-spacing:2px; text-transform:uppercase;
    }

    /* === PODIUM — Top 3 === */
    .podium {
        display:grid; grid-template-columns:1fr 1.2fr 1fr; gap:16px;
        margin-bottom:28px; align-items:end;
    }
    .pod {
        background:var(--card); border:1px solid var(--b1); border-radius:16px;
        padding:24px 20px; position:relative; overflow:hidden;
        transition:all .3s ease; text-align:center;
    }
    .pod:hover { transform:translateY(-3px); border-color:var(--pod-c); }
    .pod::before {
        content:""; position:absolute; top:0; left:0; right:0; height:4px;
        background:var(--pod-c); border-radius:16px 16px 0 0;
    }
    .pod-1 { --pod-c:var(--gold); padding:32px 20px; }
    .pod-2 { --pod-c:var(--silver); }
    .pod-3 { --pod-c:var(--bronze); }
    .pod-medal {
        font-family:'Russo One',sans-serif; font-size:14px; color:var(--pod-c);
        letter-spacing:3px; text-transform:uppercase; margin-bottom:12px;
    }
    .pod-name {
        font-family:'Chakra Petch',sans-serif; font-size:24px; font-weight:600;
        color:var(--t1); text-transform:uppercase; overflow:hidden;
        text-overflow:ellipsis; white-space:nowrap; margin-bottom:10px;
    }
    .pod-1 .pod-name { font-size:28px; }
    .pod-score {
        font-family:'Russo One',sans-serif; font-size:36px; font-weight:400;
        color:var(--pod-c); line-height:1;
    }
    .pod-label {
        font-family:'JetBrains Mono',monospace; font-size:9px; color:var(--t2);
        letter-spacing:2px; text-transform:uppercase; margin-top:6px;
    }
    .pod-watermark {
        position:absolute; right:10px; bottom:0;
        font-family:'Russo One',sans-serif; font-size:72px; font-weight:400;
        color:var(--pod-c); opacity:.04; line-height:1;
    }

    /* === INPUTS === */
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        background:var(--card) !important; color:var(--t1) !important;
        border:1px solid var(--b1) !important; border-radius:10px !important;
        font-family:'JetBrains Mono',monospace !important; font-size:13px !important;
        transition:all .2s ease !important;
    }
    .stTextInput>div>div>input:focus, .stNumberInput>div>div>input:focus {
        border-color:var(--amber-d) !important;
        box-shadow:0 0 0 3px rgba(245,166,35,.08) !important;
    }
    label {
        color:var(--t2) !important; font-family:'JetBrains Mono',monospace !important;
        font-size:11px !important; letter-spacing:1px !important;
    }

    /* === TABS — pill style === */
    .stTabs [data-baseweb="tab-list"] {
        background:var(--card) !important; border:1px solid var(--b1) !important;
        border-radius:12px !important; gap:4px !important; padding:6px !important;
    }
    .stTabs [data-baseweb="tab"] {
        background:transparent !important; color:var(--t2) !important;
        font-family:'Chakra Petch',sans-serif !important; font-size:12px !important;
        font-weight:500 !important; letter-spacing:2px !important;
        text-transform:uppercase !important; border-radius:8px !important;
        padding:10px 24px !important; border:1px solid transparent !important;
        transition:all .2s ease !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color:var(--t1) !important; background:rgba(245,166,35,.04) !important;
    }
    .stTabs [aria-selected="true"] {
        color:var(--amber) !important;
        background:rgba(245,166,35,.06) !important;
        border:1px solid var(--amber-d) !important;
    }
    .stTabs [data-baseweb="tab-panel"] { background:transparent !important; padding-top:20px !important; }

    /* === BUTTONS === */
    .stButton>button {
        background:linear-gradient(135deg, var(--amber-d), var(--amber)) !important;
        color:var(--bg) !important; border:none !important; border-radius:10px !important;
        font-family:'Chakra Petch',sans-serif !important; font-size:13px !important;
        font-weight:600 !important; letter-spacing:1px !important;
        padding:12px 36px !important; text-transform:uppercase !important;
        transition:all .2s ease !important;
    }
    .stButton>button:hover {
        box-shadow:0 4px 20px rgba(245,166,35,.25) !important; transform:translateY(-1px);
    }

    /* === SCROLLBAR === */
    ::-webkit-scrollbar { width:6px; height:6px; }
    ::-webkit-scrollbar-track { background:var(--bg); }
    ::-webkit-scrollbar-thumb { background:var(--b2); border-radius:3px; }
    ::-webkit-scrollbar-thumb:hover { background:var(--b3); }

    /* === LOGIN — SPLIT SCREEN === */
    .login-wrap {
        display:flex; min-height:500px; border-radius:20px; overflow:hidden;
        border:1px solid var(--b1); box-shadow:0 30px 80px rgba(0,0,0,.4);
    }
    .login-left {
        flex:1; background:linear-gradient(135deg, var(--card2), var(--bg2));
        padding:48px 40px; display:flex; flex-direction:column;
        justify-content:center; align-items:center; text-align:center;
        position:relative; overflow:hidden;
    }
    .login-left::before {
        content:""; position:absolute; top:0; left:0; right:0; height:3px;
        background:linear-gradient(90deg, var(--amber), var(--teal));
    }
    .login-left::after {
        content:""; position:absolute; bottom:0; left:0; right:0; height:1px;
        background:linear-gradient(90deg, transparent, var(--b2), transparent);
    }
    .login-icon-big {
        font-size:64px; margin-bottom:20px;
        animation:bob 3s ease-in-out infinite;
    }
    @keyframes bob { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-8px)} }
    .login-brand {
        font-family:'Russo One',sans-serif; font-size:32px; font-weight:400;
        color:var(--t1); letter-spacing:3px; margin-bottom:8px;
    }
    .login-brand span { color:var(--amber); }
    .login-tagline {
        font-family:'JetBrains Mono',monospace; font-size:10px; color:var(--t3);
        letter-spacing:4px; text-transform:uppercase; margin-bottom:32px;
    }
    .login-features {
        font-family:'Chakra Petch',sans-serif; font-size:13px; color:var(--t2);
        line-height:2.2; text-align:left; width:100%; max-width:280px;
    }
    .login-features div { display:flex; align-items:center; gap:10px; }
    .login-features div::before {
        content:"\u25c6"; color:var(--amber); font-size:10px;
    }
    .login-right {
        flex:1; background:var(--card); padding:48px 40px;
        display:flex; flex-direction:column; justify-content:center;
    }
    .login-right-title {
        font-family:'Russo One',sans-serif; font-size:20px; font-weight:400;
        color:var(--t1); letter-spacing:2px; margin-bottom:6px;
    }
    .login-right-sub {
        font-family:'JetBrains Mono',monospace; font-size:10px; color:var(--t3);
        letter-spacing:3px; text-transform:uppercase; margin-bottom:32px;
    }
    .login-error {
        background:rgba(239,68,68,.06); border:1px solid rgba(239,68,68,.2);
        border-radius:10px; padding:14px 18px; font-family:'JetBrains Mono',monospace;
        font-size:11px; color:var(--red); margin-top:14px;
    }
    .login-footer {
        margin-top:28px; font-family:'JetBrains Mono',monospace; font-size:9px;
        color:var(--t3); line-height:2.2;
    }

    /* === ADMIN CARDS === */
    .adm-card {
        background:var(--card); border:1px solid var(--b1); border-radius:14px;
        padding:28px; margin-bottom:24px; position:relative; overflow:hidden;
    }
    .adm-card::before {
        content:""; position:absolute; top:0; left:0; right:0; height:2px;
        background:linear-gradient(90deg, var(--amber), var(--teal));
    }
    .adm-title {
        font-family:'Russo One',sans-serif; font-size:13px; font-weight:400;
        color:var(--amber); letter-spacing:2px; text-transform:uppercase;
        margin-bottom:20px; padding-bottom:10px; border-bottom:1px solid var(--b1);
        display:flex; align-items:center; gap:10px;
    }
    .adm-title::before {
        content:""; width:6px; height:6px; border-radius:50%;
        background:var(--amber); box-shadow:0 0 6px var(--amber);
    }

    /* === DATAFRAME === */
    .stDataFrame { border:1px solid var(--b1); border-radius:12px; overflow:hidden; }

    /* === REFRESH BAR === */
    .refresh-bar {
        text-align:center; font-family:'JetBrains Mono',monospace; font-size:10px;
        color:var(--t3); margin-top:28px; padding:16px;
        border-top:1px solid var(--b1);
    }
    .refresh-bar span { color:var(--amber); }

    /* === UTILITY MESSAGES === */
    .info-msg {
        text-align:center; padding:56px; font-family:'Chakra Petch',sans-serif;
        font-size:14px; color:var(--t2);
    }
    .info-msg span { color:var(--amber); font-size:40px; display:block; margin-bottom:16px; }
    .error-msg {
        text-align:center; padding:40px; font-family:'Chakra Petch',sans-serif;
        font-size:14px; color:var(--red);
    }
    .error-msg span { font-size:44px; display:block; margin-bottom:16px; }
    .warn-msg {
        text-align:center; padding:40px; font-family:'Chakra Petch',sans-serif;
        font-size:14px; color:var(--orange);
    }
    .warn-msg span { font-size:44px; display:block; margin-bottom:16px; }

    /* === HIDE BRANDING === */
    #MainMenu { visibility:hidden; }
    footer { visibility:hidden; }
    header[data-testid="stHeader"] { background:transparent !important; }
    .stDeployButton { display:none; }

    /* === SPINNER === */
    .stSpinner>div { border-color:var(--amber) !important; }

    /* === SIDEBAR RADIO === */
    .stRadio>div { gap:4px; }
    .stRadio label {
        font-family:'Chakra Petch',sans-serif !important; font-size:13px !important;
        color:var(--t2) !important; padding:8px 12px !important;
        border-radius:8px; transition:all .2s ease;
    }
    .stRadio label:hover { background:var(--card); color:var(--t1) !important; }
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
# AUTH FLOW — SPLIT SCREEN LOGIN
# ============================================================
if not st.session_state.get("authenticated"):

    st.markdown("""
    <div class="login-wrap">
        <div class="login-left">
            <div class="login-icon-big">\u26a1</div>
            <div class="login-brand">UTS <span>HUNTERS</span></div>
            <div class="login-tagline">> Authorized Access Only</div>
            <div class="login-features">
                <div>Real-time OTP Monitoring</div>
                <div>Live Network Stream</div>
                <div>Team Member Tracking</div>
                <div>Google Sheet Database</div>
                <div>Admin Code Management</div>
            </div>
        </div>
        <div class="login-right">
            <div class="login-right-title">ACCESS PORTAL</div>
            <div class="login-right-sub">Enter your activation code</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Input below the visual card
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
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
            Each code is device-locked. Contact admin for access.
        </div>
        """, unsafe_allow_html=True)

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
        return ['background-color:rgba(245,166,35,.06);color:#f5a623;font-weight:bold;border-right:3px solid #f5a623'] * len(row)
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
# SIDEBAR NAVIGATION
# ============================================================
with st.sidebar:
    st.markdown('<div class="nav-header">\u26a1 UTS HUNTERS</div>', unsafe_allow_html=True)

    nav_options = ["\U0001f4e1  Live Monitor", "\U0001f4ca  Sheet Database"]
    if is_admin:
        nav_options.append("\U0001f510  Admin Panel")

    nav_choice = st.radio("NAVIGATION", nav_options, label_visibility="collapsed")

    st.markdown('<div class="nav-divider"></div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="nav-stat">
        OPERATOR: <span>{operator_name.upper()}</span><br>
        SESSION: <span>{datetime.now().strftime("%H:%M:%S")}</span><br>
        STATUS: <span>\u2713 ONLINE</span><br>
        {"ADMIN: <span>\U0001f451 YES</span><br>" if is_admin else ""}
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="nav-divider"></div>', unsafe_allow_html=True)

    if "\U0001f4e1" in nav_choice:
        st.markdown("**\u2699 TARGET AGENT (CLI):**")
        target_cli = st.text_input("", value="MYOB", key="sb_cli", label_visibility="collapsed").strip()
        st.markdown("**\U0001f4e1 STREAM BUFFER:**")
        msg_limit = st.number_input("", min_value=1, max_value=2000, value=500, key="sb_limit", label_visibility="collapsed")
    elif "\U0001f4ca" in nav_choice:
        st.markdown("**\U0001f50d FILTERS**")
        filter_cli = st.text_input("App/CLI:", "", key="sb_fcli").strip()
        filter_num = st.text_input("Number:", "", key="sb_fnum").strip()
        filter_msg = st.text_input("Message:", "", key="sb_fmsg").strip()


# ============================================================
# TOP BAR
# ============================================================
st.markdown(f"""
<div class="topbar">
    <div class="topbar-left">
        <div class="topbar-logo">UTS <span>HUNTERS</span></div>
        <div class="topbar-badge">v4 OBSIDIAN</div>
    </div>
    <div class="topbar-right">
        <div><span class="live-dot"></span>LIVE</div>
        <div>OPERATOR: <span>{operator_name.upper()}</span></div>
        <div>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
        {"<div><span>\U0001f451 ADMIN</span></div>" if is_admin else ""}
    </div>
</div>
""", unsafe_allow_html=True)


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

# Initialize placeholders
placeholder = st.empty()
history_placeholder = st.empty()


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

            # === LIVE MONITOR TAB ===
            if "\U0001f4e1" in nav_choice:
                with placeholder.container():
                    st.markdown("""
                    <div class="stat-row">
                        <div class="stat-tile t1"><div class="stat-num">""" + str(tr) + """</div><div class="stat-txt">Total Records</div></div>
                        <div class="stat-tile t2"><div class="stat-num">""" + str(t1c) + """</div><div class="stat-txt">Top CLI (5min)</div></div>
                        <div class="stat-tile t3"><div class="stat-num">""" + str(uc) + """</div><div class="stat-txt">Unique CLIs</div></div>
                        <div class="stat-tile t4"><div class="stat-num">""" + str(un) + """</div><div class="stat-txt">Unique Numbers</div></div>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown("""
                    <div class="podium">
                        <div class="pod pod-2"><div class="pod-watermark">2</div>
                            <div class="pod-medal">\U0001f948 SILVER</div>
                            <div class="pod-name">""" + str(t2n) + """</div>
                            <div class="pod-score">""" + str(t2c) + """</div>
                            <div class="pod-label">OTPs (5min)</div></div>
                        <div class="pod pod-1"><div class="pod-watermark">1</div>
                            <div class="pod-medal">\U0001f3c6 GOLD</div>
                            <div class="pod-name">""" + str(t1n) + """</div>
                            <div class="pod-score">""" + str(t1c) + """</div>
                            <div class="pod-label">OTPs (5min)</div></div>
                        <div class="pod pod-3"><div class="pod-watermark">3</div>
                            <div class="pod-medal">\U0001f949 BRONZE</div>
                            <div class="pod-name">""" + str(t3n) + """</div>
                            <div class="pod-score">""" + str(t3c) + """</div>
                            <div class="pod-label">OTPs (5min)</div></div>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown(f'<div class="sec-h">LIVE TARGET TRACKER \u2014 {target_cli.upper()}</div>', unsafe_allow_html=True)
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

                    st.markdown('<div class="sec-h">GLOBAL LIVE NETWORK STREAM</div>', unsafe_allow_html=True)
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

            # === SHEET DATABASE TAB ===
            elif "\U0001f4ca" in nav_choice:
                with placeholder.container():
                    st.markdown('<div class="sec-h">GOOGLE SHEET DATABASE</div>', unsafe_allow_html=True)
                    st.info("Loading database from Google Sheets...")

            # === ADMIN PANEL TAB ===
            elif "\U0001f510" in nav_choice and is_admin:
                with placeholder.container():
                    st.markdown('<div class="sec-h">CODE GENERATION</div>', unsafe_allow_html=True)
                    st.markdown('<div class="adm-card"><div class="adm-title">\u26a1 Generate New Codes</div>', unsafe_allow_html=True)
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

                    st.markdown('<div class="sec-h">ALL CODES</div>', unsafe_allow_html=True)
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
                                if v == "ACTIVE":      return "color:#22c55e;font-weight:bold"
                                if v == "DEACTIVATED": return "color:#ef4444;font-weight:bold"
                                return "color:#fbbf24"
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

                            st.markdown('<div class="adm-card"><div class="adm-title">\U0001f512 Deactivate / Reset Code</div>', unsafe_allow_html=True)
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
# SHEET DATABASE (separate try/except, only when on that tab)
# ============================================================
if "\U0001f4ca" in nav_choice:
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
                         color:var(--t2);margin-bottom:16px;padding:10px 20px;
                         background:var(--card);border:1px solid var(--b1);
                         border-radius:10px;display:inline-block">
                        <span style="color:var(--amber);font-weight:600;font-size:16px">{len(sdf)}</span>
                        <span style="margin-left:8px">PERMANENT RECORDS</span>
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
# AUTO-REFRESH
# ============================================================
REFRESH_SECONDS = 15
st.markdown(
    f'<div class="refresh-bar">\u21bb Auto-refresh in <span>{REFRESH_SECONDS}s</span> \u2014 System Online</div>',
    unsafe_allow_html=True
)
time.sleep(REFRESH_SECONDS)
st.rerun()
