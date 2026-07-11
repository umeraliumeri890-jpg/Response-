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
# CSS — V3 REDESIGN: "NEXUS COMMAND" — Dark Glass + Emerald/Coral
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500;600;700&family=Audiowide&display=swap');

    :root {
        --bg:#0a0e14; --bg2:#0f1419; --card:#131922; --card2:#171e29;
        --b1:#1e2733; --b2:#2a3543; --b3:#3a4757;
        --accent:#00d9a3; --accent-d:#00a37a; --accent-glow:rgba(0,217,163,.12);
        --coral:#ff6b6b; --coral-d:#cc4f4f;
        --amber:#ffa940; --amber-d:#cc8120;
        --teal:#4ecdc4; --teal-d:#3a9a93;
        --gold:#ffd93d; --gold-d:#c9a830;
        --silver:#c8cdd6; --bronze:#cd9b6e;
        --green:#00d9a3; --red:#ff4757; --orange:#ff8c42;
        --t1:#dfe6f0; --t2:#6b7a8f; --t3:#3d4a5c; --t4:#202a37;
    }

    /* === BACKGROUND === */
    .stApp {
        background-color:var(--bg) !important;
        background-image:
            radial-gradient(circle at 20% 10%, rgba(0,217,163,.04) 0%, transparent 40%),
            radial-gradient(circle at 80% 90%, rgba(255,107,107,.03) 0%, transparent 40%),
            radial-gradient(circle at 50% 50%, rgba(78,205,196,.02) 0%, transparent 60%);
        font-family:'Space Grotesk',sans-serif;
    }

    /* === HEADER === */
    .hdr {
        text-align:center; padding:44px 20px 16px; position:relative;
    }
    .hdr::after {
        content:""; position:absolute; bottom:0; left:50%; transform:translateX(-50%);
        width:50%; height:1px;
        background:linear-gradient(90deg, transparent, var(--accent), transparent);
        opacity:.4;
    }
    .badge {
        display:inline-block; position:relative;
        background:var(--card); border:1px solid var(--b2); border-radius:20px;
        padding:6px 28px; font-family:'JetBrains Mono',monospace;
        font-size:10px; font-weight:600; color:var(--accent);
        letter-spacing:6px; text-transform:uppercase; margin-bottom:18px;
    }
    .badge::before, .badge::after {
        content:""; position:absolute; top:50%; transform:translateY(-50%);
        width:40px; height:1px; background:linear-gradient(90deg, transparent, var(--b2));
    }
    .badge::before { left:-45px; }
    .badge::after { right:-45px; background:linear-gradient(90deg, var(--b2), transparent); }
    .title {
        font-family:'Audiowide',sans-serif; font-size:54px; font-weight:400;
        color:var(--t1); letter-spacing:4px; line-height:1.1; margin-bottom:10px;
    }
    .title span {
        color:var(--accent);
        text-shadow:0 0 30px rgba(0,217,163,.3);
    }
    .sub {
        font-family:'JetBrains Mono',monospace; font-size:11px; color:var(--t2);
        letter-spacing:4px; text-transform:uppercase; margin-bottom:32px;
    }

    /* === OPERATOR BAR === */
    .opbar {
        display:flex; justify-content:center; align-items:center; gap:0;
        margin-bottom:32px; font-family:'JetBrains Mono',monospace;
        font-size:11px; flex-wrap:wrap;
    }
    .op-item {
        display:flex; align-items:center; gap:8px;
        padding:10px 22px; color:var(--t2);
        background:var(--card); border:1px solid var(--b1);
        transition:all .2s ease;
    }
    .op-item:first-child { border-radius:8px 0 0 8px; }
    .op-item:last-child { border-radius:0 8px 8px 0; }
    .op-item + .op-item { border-left:none; }
    .op-item span { color:var(--accent); font-weight:600; }

    /* === PULSE DOT === */
    .pulse-dot {
        display:inline-block; width:7px; height:7px; border-radius:50%;
        background:var(--green); box-shadow:0 0 6px var(--green);
        animation:pulse 1.8s ease-in-out infinite; margin-right:8px;
    }
    @keyframes pulse {
        0%,100%{opacity:1;transform:scale(1)}
        50%{opacity:.4;transform:scale(.6)}
    }

    /* === SECTION LABEL === */
    .sl {
        font-family:'Space Grotesk',sans-serif; font-size:13px; font-weight:600;
        color:var(--t1); letter-spacing:2px; text-transform:uppercase;
        margin-top:36px; margin-bottom:16px; padding:10px 0;
        display:flex; align-items:center; gap:10px;
        border-bottom:1px solid var(--b1);
    }
    .sl::before {
        content:""; width:3px; height:16px; border-radius:2px;
        background:var(--accent);
    }

    /* === STAT CARDS === */
    .stat-grid {
        display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:28px;
    }
    .stat-card {
        background:var(--card); border:1px solid var(--b1); border-radius:12px;
        padding:20px; text-align:center; position:relative; overflow:hidden;
        transition:all .25s ease;
    }
    .stat-card:hover { border-color:var(--b2); background:var(--card2); }
    .stat-card::before {
        content:""; position:absolute; top:0; left:0; right:0; height:2px;
        background:var(--accent); opacity:.3;
    }
    .stat-val {
        font-family:'Audiowide',monospace; font-size:30px; font-weight:400;
        color:var(--accent); line-height:1.2;
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
        background:var(--card); border:1px solid var(--b1); border-radius:14px;
        padding:26px 24px; position:relative; overflow:hidden;
        transition:all .25s ease;
    }
    .lb-card:hover { transform:translateY(-2px); border-color:var(--accent); }
    .lb-card::before {
        content:""; position:absolute; top:0; left:0; right:0; height:3px;
        background:var(--rank-color); border-radius:14px 14px 0 0;
    }
    .lb-1 { --rank-color:var(--gold); }
    .lb-2 { --rank-color:var(--silver); }
    .lb-3 { --rank-color:var(--bronze); }
    .lb-rank {
        position:absolute; right:20px; top:50%; transform:translateY(-50%);
        font-family:'Audiowide',sans-serif; font-size:60px; font-weight:400;
        color:var(--rank-color); opacity:.05;
    }
    .lb-label {
        font-family:'JetBrains Mono',monospace; font-size:10px; font-weight:600;
        letter-spacing:2px; text-transform:uppercase; margin-bottom:14px;
        color:var(--rank-color);
    }
    .lb-name {
        font-family:'Space Grotesk',sans-serif; font-size:26px; font-weight:600;
        color:var(--t1); text-transform:uppercase; overflow:hidden;
        text-overflow:ellipsis; white-space:nowrap; margin-bottom:8px;
    }
    .lb-count {
        font-family:'JetBrains Mono',monospace; font-size:13px; font-weight:500;
        color:var(--accent);
    }

    /* === INPUTS === */
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        background:var(--card) !important; color:var(--t1) !important;
        border:1px solid var(--b1) !important; border-radius:8px !important;
        font-family:'JetBrains Mono',monospace !important; font-size:13px !important;
        transition:all .2s ease !important;
    }
    .stTextInput>div>div>input:focus, .stNumberInput>div>div>input:focus {
        border-color:var(--accent-d) !important;
        box-shadow:0 0 0 3px rgba(0,217,163,.08) !important;
    }
    label {
        color:var(--t2) !important; font-family:'JetBrains Mono',monospace !important;
        font-size:11px !important; letter-spacing:1px !important;
    }

    /* === TABS === */
    .stTabs [data-baseweb="tab-list"] {
        background:var(--card) !important; border:1px solid var(--b1) !important;
        border-radius:10px !important; gap:2px !important; padding:4px !important;
    }
    .stTabs [data-baseweb="tab"] {
        background:transparent !important; color:var(--t2) !important;
        font-family:'Space Grotesk',sans-serif !important; font-size:12px !important;
        font-weight:500 !important; letter-spacing:2px !important;
        text-transform:uppercase !important; border-radius:8px !important;
        padding:10px 22px !important; border:1px solid transparent !important;
        transition:all .2s ease !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color:var(--t1) !important; background:rgba(0,217,163,.04) !important;
    }
    .stTabs [aria-selected="true"] {
        color:var(--accent) !important;
        background:rgba(0,217,163,.06) !important;
        border:1px solid var(--accent-d) !important;
    }
    .stTabs [data-baseweb="tab-panel"] { background:transparent !important; padding-top:20px !important; }

    /* === BUTTONS === */
    .stButton>button {
        background:var(--accent-d) !important; color:var(--bg) !important;
        border:none !important; border-radius:8px !important;
        font-family:'Space Grotesk',sans-serif !important; font-size:13px !important;
        font-weight:600 !important; letter-spacing:1px !important;
        padding:10px 32px !important; text-transform:uppercase !important;
        transition:all .2s ease !important;
    }
    .stButton>button:hover {
        background:var(--accent) !important; box-shadow:0 4px 15px rgba(0,217,163,.2) !important;
    }

    /* === SCROLLBAR === */
    ::-webkit-scrollbar { width:5px; height:5px; }
    ::-webkit-scrollbar-track { background:var(--bg); }
    ::-webkit-scrollbar-thumb { background:var(--b2); border-radius:3px; }
    ::-webkit-scrollbar-thumb:hover { background:var(--b3); }

    /* === LOGIN CARD === */
    .login-card {
        background:var(--card); border:1px solid var(--b1); border-radius:20px;
        padding:56px 48px; position:relative; overflow:hidden;
        box-shadow:0 25px 70px rgba(0,0,0,.4);
    }
    .login-card::before {
        content:""; position:absolute; top:0; left:0; right:0; height:3px;
        background:linear-gradient(90deg, var(--accent), var(--teal), var(--accent));
    }
    .login-icon {
        font-size:52px; text-align:center; margin-bottom:18px;
        animation:float 3s ease-in-out infinite;
    }
    @keyframes float {
        0%,100%{transform:translateY(0)}
        50%{transform:translateY(-6px)}
    }
    .login-title {
        font-family:'Audiowide',sans-serif; font-size:26px; font-weight:400;
        color:var(--t1); text-align:center; margin-bottom:8px; letter-spacing:3px;
    }
    .login-sub {
        font-family:'JetBrains Mono',monospace; font-size:10px; color:var(--t3);
        letter-spacing:4px; text-transform:uppercase; text-align:center; margin-bottom:36px;
    }
    .login-error {
        background:rgba(255,71,87,.06); border:1px solid rgba(255,71,87,.2);
        border-radius:8px; padding:12px 18px; font-family:'JetBrains Mono',monospace;
        font-size:11px; color:var(--red); margin-top:14px;
    }
    .login-footer {
        margin-top:28px; font-family:'JetBrains Mono',monospace; font-size:9px;
        color:var(--t3); text-align:center; line-height:2.2;
    }

    /* === ADMIN CARDS === */
    .admin-card {
        background:var(--card); border:1px solid var(--b1); border-radius:12px;
        padding:28px; margin-bottom:24px; position:relative; overflow:hidden;
    }
    .admin-card::before {
        content:""; position:absolute; top:0; left:0; right:0; height:2px;
        background:linear-gradient(90deg, var(--accent), var(--teal));
    }
    .admin-title {
        font-family:'Space Grotesk',sans-serif; font-size:13px; font-weight:600;
        color:var(--accent); letter-spacing:2px; text-transform:uppercase;
        margin-bottom:20px; padding-bottom:10px; border-bottom:1px solid var(--b1);
        display:flex; align-items:center; gap:10px;
    }
    .admin-title::before {
        content:""; width:6px; height:6px; border-radius:50%;
        background:var(--accent); box-shadow:0 0 6px var(--accent);
    }

    /* === DATAFRAME === */
    .stDataFrame { border:1px solid var(--b1); border-radius:10px; overflow:hidden; }

    /* === REFRESH INDICATOR === */
    .refresh-indicator {
        text-align:center; font-family:'JetBrains Mono',monospace; font-size:10px;
        color:var(--t3); margin-top:24px; padding:14px;
        border-top:1px solid var(--b1);
    }
    .refresh-indicator span { color:var(--accent); }

    /* === UTILITY MESSAGES === */
    .info-msg {
        text-align:center; padding:48px; font-family:'JetBrains Mono',monospace;
        font-size:13px; color:var(--t2);
    }
    .info-msg span { color:var(--accent); font-size:32px; display:block; margin-bottom:14px; }
    .error-msg {
        text-align:center; padding:36px; font-family:'JetBrains Mono',monospace;
        font-size:13px; color:var(--red);
    }
    .error-msg span { font-size:36px; display:block; margin-bottom:14px; }
    .warn-msg {
        text-align:center; padding:36px; font-family:'JetBrains Mono',monospace;
        font-size:13px; color:var(--orange);
    }
    .warn-msg span { font-size:36px; display:block; margin-bottom:14px; }

    /* === HIDE STREAMLIT BRANDING === */
    #MainMenu { visibility:hidden; }
    footer { visibility:hidden; }
    header[data-testid="stHeader"] { background:transparent !important; }
    .stDeployButton { display:none; }

    /* === SPINNER === */
    .stSpinner>div { border-color:var(--accent) !important; }
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
        <div class="title">UTS <span>HUNTERS</span></div>
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
            Each code is device-locked. Contact admin for access.
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
        return ['background-color:rgba(0,217,163,.06);color:#00d9a3;font-weight:bold;border-right:3px solid #00d9a3'] * len(row)
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
    <div class="title">UTS <span>HUNTERS</span></div>
    <div class="sub">> Database Integrated Control Panel</div>
</div>
<div class="opbar">
    <div class="op-item"><span class="pulse-dot"></span><span>LIVE</span></div>
    <div class="op-item">OPERATOR: <span>{operator_name.upper()}</span></div>
    <div class="op-item">SESSION: <span>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></div>
    <div class="op-item">STATUS: <span style="color:#00d9a3">\u2713 AUTHORIZED</span></div>
    {"<div class='op-item'><span style='color:#ffd93d'>\U0001f451 ADMIN MODE</span></div>" if is_admin else ""}
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
                    if v == "ACTIVE":      return "color:#00d9a3;font-weight:bold"
                    if v == "DEACTIVATED": return "color:#ff4757;font-weight:bold"
                    return "color:#ffd93d"
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
                     color:var(--t2);margin-bottom:14px;padding:8px 18px;
                     background:var(--card);border:1px solid var(--b1);
                     border-radius:8px;display:inline-block">
                    <span style="color:var(--accent);font-weight:600;font-size:14px">{len(sdf)}</span>
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
# AUTO-REFRESH
# ============================================================
REFRESH_SECONDS = 15
st.markdown(
    f'<div class="refresh-indicator">\u21bb Auto-refresh in <span>{REFRESH_SECONDS}s</span> \u2014 System Online</div>',
    unsafe_allow_html=True
)
time.sleep(REFRESH_SECONDS)
st.rerun()
