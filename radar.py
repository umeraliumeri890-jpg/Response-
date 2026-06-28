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
import secrets

# ============================================================
# --- CONFIG ---
# ============================================================
URL = "http://51.77.216.195/crapi/lamix/viewstats"
TOKEN = "X46ZeF6ViotShZl5WYRse1t3lYiKZ3CAdo6ZdINSh0o="
TEAM_FILE = "Numbers_Export.csv"

# Your existing Google Sheet (for OTP data)
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyTHahQPjxjbuZGcIWiN2AgY8lHJEDm7Pyi2QnpSJVV436Q65DOlOtmA2Ilux8UkVgl/exec"

# New Registry Google Sheet (for codes + device lock)
REGISTRY_URL = "https://script.google.com/macros/s/AKfycbzo_Z_7CEVEeKA9fL-M3WXtznKrd19MyiXTksRlbSd1E8bNXh8nZF5HsLdedOjG2iVF/exec"

# Admin Key — sirf tumhare paas
ADMIN_KEY = "UTS_ADMIN_2024"

# ============================================================
# --- PAGE CONFIG ---
# ============================================================
st.set_page_config(page_title="UTS HUNTERS", page_icon="⚡", layout="wide")

# ============================================================
# --- CSS: ELITE DARK BLUE THEME ---
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700;800&family=Inter:wght@300;400;600;700;900&display=swap');

    :root {
        --bg-primary: #040b1a;
        --bg-secondary: #071228;
        --bg-card: #0a1a35;
        --border-color: #112244;
        --border-accent: #1a3a70;
        --electric: #00aaff;
        --electric-dim: #0066bb;
        --electric-glow: rgba(0,170,255,0.15);
        --gold: #f0b429;
        --silver: #a8b4c8;
        --bronze: #cd7f32;
        --green: #00e676;
        --red: #ff3d71;
        --text-primary: #c8deff;
        --text-secondary: #5a7aa0;
        --text-muted: #304560;
    }

    .stApp {
        background-color: var(--bg-primary) !important;
        background-image:
            radial-gradient(ellipse at 20% 0%, rgba(0,90,200,0.08) 0%, transparent 60%),
            radial-gradient(ellipse at 80% 100%, rgba(0,60,150,0.06) 0%, transparent 60%);
        font-family: 'Inter', sans-serif;
    }

    /* HEADER */
    .uts-header { text-align: center; padding: 32px 20px 8px 20px; }
    .uts-badge {
        display: inline-block;
        background: linear-gradient(135deg, #071228, #0a1a35);
        border: 1px solid var(--electric-dim);
        border-radius: 2px;
        padding: 4px 18px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px; font-weight: 600;
        color: var(--electric);
        letter-spacing: 6px; text-transform: uppercase;
        margin-bottom: 12px;
    }
    .uts-title {
        font-family: 'Inter', sans-serif;
        font-size: 52px; font-weight: 900;
        color: #ffffff; letter-spacing: -1px;
        line-height: 1; margin-bottom: 6px;
    }
    .uts-title span { color: var(--electric); text-shadow: 0 0 30px rgba(0,170,255,0.6); }
    .uts-subtitle {
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px; color: var(--text-secondary);
        letter-spacing: 4px; text-transform: uppercase; margin-bottom: 28px;
    }
    .uts-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--electric-dim), transparent);
        margin: 0 auto 28px auto; max-width: 600px;
    }

    /* OPERATOR BAR */
    .operator-bar {
        display: flex; justify-content: center; align-items: center;
        gap: 24px; padding: 10px 20px;
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: 4px; margin-bottom: 24px;
        font-family: 'JetBrains Mono', monospace; font-size: 11px;
    }
    .op-item { color: var(--text-secondary); }
    .op-item span { color: var(--electric); font-weight: 700; }
    .op-dot { color: var(--border-accent); }

    /* SECTION LABELS */
    .section-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px; font-weight: 700;
        color: var(--text-secondary);
        letter-spacing: 3px; text-transform: uppercase;
        margin-top: 32px; margin-bottom: 14px;
        padding-bottom: 10px;
        border-bottom: 1px solid var(--border-color);
        display: flex; align-items: center; gap: 10px;
    }
    .section-label::before {
        content: "";
        display: inline-block; width: 3px; height: 14px;
        background: var(--electric); border-radius: 1px;
        box-shadow: 0 0 8px var(--electric);
    }

    /* RANK CARDS */
    .leaderboard-grid {
        display: grid; grid-template-columns: repeat(3, 1fr);
        gap: 16px; margin-bottom: 28px;
    }
    .rank-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 4px; padding: 22px 20px;
        position: relative; overflow: hidden;
    }
    .rank-card::before {
        content: ""; position: absolute;
        top: 0; left: 0; right: 0; height: 1px;
        background: linear-gradient(90deg, transparent, var(--accent-color), transparent);
    }
    .rank-1 { --accent-color: var(--gold); border-left: 3px solid var(--gold); }
    .rank-2 { --accent-color: var(--silver); border-left: 3px solid var(--silver); }
    .rank-3 { --accent-color: var(--bronze); border-left: 3px solid var(--bronze); }
    .rank-badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px; font-weight: 700;
        letter-spacing: 2px; text-transform: uppercase;
        margin-bottom: 10px; color: var(--accent-color);
    }
    .rank-cli {
        color: #ffffff; font-family: 'Inter', sans-serif;
        font-size: 26px; font-weight: 800;
        text-transform: uppercase;
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        margin-bottom: 6px;
    }
    .rank-count {
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px; color: var(--electric); font-weight: 600;
    }
    .rank-watermark {
        position: absolute; right: 16px; top: 50%;
        transform: translateY(-50%);
        font-size: 52px; opacity: 0.04;
        font-weight: 900; color: var(--accent-color);
    }

    /* STATS ROW */
    .stats-row {
        display: grid; grid-template-columns: repeat(4, 1fr);
        gap: 12px; margin-bottom: 28px;
    }
    .stat-box {
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: 3px; padding: 14px 18px; text-align: center;
    }
    .stat-val {
        font-family: 'JetBrains Mono', monospace;
        font-size: 28px; font-weight: 800;
        color: var(--electric); line-height: 1.1;
    }
    .stat-lbl {
        font-family: 'JetBrains Mono', monospace;
        font-size: 9px; color: var(--text-secondary);
        letter-spacing: 2px; text-transform: uppercase; margin-top: 4px;
    }

    /* INPUTS */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        background-color: var(--bg-secondary) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-accent) !important;
        border-radius: 3px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px !important;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--electric) !important;
        box-shadow: 0 0 0 1px var(--electric-dim) !important;
    }
    label {
        color: var(--text-secondary) !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 11px !important; letter-spacing: 1px !important;
    }

    /* TABS */
    .stTabs [data-baseweb="tab-list"] {
        background-color: var(--bg-secondary) !important;
        border-bottom: 1px solid var(--border-color) !important;
        gap: 4px !important; padding: 0 6px !important;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent !important;
        color: var(--text-secondary) !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 11px !important; font-weight: 600 !important;
        letter-spacing: 2px !important; text-transform: uppercase !important;
        border-radius: 0 !important; padding: 12px 20px !important;
        border-bottom: 2px solid transparent !important;
    }
    .stTabs [aria-selected="true"] {
        color: var(--electric) !important;
        border-bottom-color: var(--electric) !important;
        background-color: transparent !important;
    }
    .stTabs [data-baseweb="tab-panel"] {
        background-color: transparent !important;
        padding-top: 16px !important;
    }

    /* SCROLLBAR */
    ::-webkit-scrollbar { width: 4px; height: 4px; }
    ::-webkit-scrollbar-track { background: var(--bg-primary); }
    ::-webkit-scrollbar-thumb { background: var(--electric-dim); border-radius: 2px; }

    /* BUTTONS */
    .stButton > button {
        background: var(--electric-dim) !important;
        color: #ffffff !important;
        border: 1px solid var(--electric) !important;
        border-radius: 3px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 12px !important; font-weight: 700 !important;
        letter-spacing: 2px !important; padding: 10px 28px !important;
        text-transform: uppercase !important;
    }
    .stButton > button:hover {
        background: var(--electric) !important;
        box-shadow: 0 0 20px rgba(0,170,255,0.3) !important;
    }

    /* PULSE */
    .pulse-dot {
        display: inline-block; width: 8px; height: 8px;
        background: var(--green); border-radius: 50%;
        box-shadow: 0 0 6px var(--green);
        animation: pulse 2s infinite; margin-right: 6px;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.4; transform: scale(0.85); }
    }

    /* LOGIN */
    .login-wrap {
        display: flex; flex-direction: column;
        align-items: center; justify-content: center;
        min-height: 70vh; text-align: center;
    }
    .login-card {
        background: var(--bg-card);
        border: 1px solid var(--border-accent);
        border-radius: 6px; padding: 48px 52px; width: 420px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.5);
    }
    .login-logo { font-size: 44px; margin-bottom: 16px; }
    .login-title {
        font-family: 'Inter', sans-serif;
        font-size: 26px; font-weight: 900;
        color: #ffffff; margin-bottom: 4px;
    }
    .login-sub {
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px; color: var(--text-muted);
        letter-spacing: 3px; text-transform: uppercase; margin-bottom: 32px;
    }
    .login-error {
        background: rgba(255,61,113,0.08);
        border: 1px solid rgba(255,61,113,0.3);
        border-radius: 3px; padding: 10px 16px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px; color: var(--red);
        margin-top: 12px; text-align: left;
    }
    .login-success {
        background: rgba(0,230,118,0.08);
        border: 1px solid rgba(0,230,118,0.3);
        border-radius: 3px; padding: 10px 16px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px; color: var(--green);
        margin-top: 12px; text-align: left;
    }

    /* ADMIN PANEL */
    .admin-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 4px; padding: 24px;
        margin-bottom: 20px;
    }
    .admin-card-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px; font-weight: 700;
        color: var(--electric); letter-spacing: 3px;
        text-transform: uppercase; margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 1px solid var(--border-color);
    }
    .code-pill {
        display: inline-block;
        background: rgba(0,170,255,0.08);
        border: 1px solid rgba(0,170,255,0.2);
        border-radius: 3px; padding: 6px 12px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px; color: var(--electric);
        margin: 4px; cursor: pointer;
    }
    .status-active { color: var(--green); }
    .status-deactivated { color: var(--red); }
    .status-pending { color: var(--gold); }

    div[data-testid="stCaption"] {
        color: var(--text-muted) !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 10px !important;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# --- JAVASCRIPT: DEVICE FINGERPRINT ---
# ============================================================
def inject_fingerprint_js():
    """
    Strong device fingerprint using 9 browser signals.
    Also fetches public IP via a free API and stores both in URL params.
    unknown-device fingerprint = REJECTED at login.
    """
    st.components.v1.html("""
    <script>
    (function() {
        // --- Build device fingerprint ---
        var components = [
            navigator.userAgent || '',
            navigator.platform || '',
            screen.width + 'x' + screen.height + 'x' + screen.colorDepth,
            Intl.DateTimeFormat().resolvedOptions().timeZone || '',
            navigator.language || '',
            String(navigator.hardwareConcurrency || 0),
            String(navigator.maxTouchPoints || 0),
            String(new Date().getTimezoneOffset()),
            navigator.vendor || '',
            String(window.devicePixelRatio || 1),
            navigator.oscpu || navigator.platform || ''
        ];
        var raw = components.join('||');

        // djb2 hash — strong enough for fingerprinting
        var hash = 5381;
        for (var i = 0; i < raw.length; i++) {
            hash = ((hash << 5) + hash) + raw.charCodeAt(i);
            hash = hash & hash;
        }
        var fp = 'FP'
               + Math.abs(hash).toString(16).toUpperCase().padStart(8,'0')
               + '_W' + screen.width
               + '_C' + (navigator.hardwareConcurrency || 0)
               + '_D' + screen.colorDepth
               + '_P' + String(window.devicePixelRatio || 1).replace('.','');

        function setFpParam(fp, ip) {
            var params = new URLSearchParams(window.location.search);
            var changed = false;
            if (params.get('_fp') !== fp) { params.set('_fp', fp); changed = true; }
            if (ip && params.get('_ip') !== ip) { params.set('_ip', ip); changed = true; }
            if (changed) {
                window.history.replaceState({}, '', window.location.pathname + '?' + params.toString());
            }
        }

        // --- Fetch public IP (ipify — free, no auth) ---
        var existingIp = new URLSearchParams(window.location.search).get('_ip');
        if (existingIp) {
            setFpParam(fp, existingIp);
        } else {
            fetch('https://api.ipify.org?format=json')
                .then(function(r){ return r.json(); })
                .then(function(d){ setFpParam(fp, d.ip || ''); })
                .catch(function(){ setFpParam(fp, 'noip'); });
        }
    })();
    </script>
    """, height=0)

def persist_auth_in_url(code):
    st.components.v1.html(f"""
    <script>
    (function() {{
        var params = new URLSearchParams(window.location.search);
        params.set('_ac', '{code}');
        window.history.replaceState({{}}, '', window.location.pathname + '?' + params.toString());
    }})();
    </script>
    """, height=0)


# ============================================================
# --- REGISTRY API CALLS ---
# ============================================================
def check_code_api(code, fp, ip=""):
    """Verify code + device fingerprint + IP subnet with Google Sheet registry."""
    if not fp or fp == "unknown-device" or not fp.startswith("FP"):
        return {"success": False, "msg": "DEVICE FINGERPRINT MISSING — Please reload the page and wait 3 seconds before logging in"}
    try:
        payload = {
            "action": "check_code",
            "code": code.strip().upper(),
            "fp": fp,
            "ip": ip
        }
        r = requests.post(REGISTRY_URL, data=json.dumps(payload),
                          headers={"Content-Type": "application/json"}, timeout=15)
        return r.json()
    except Exception as e:
        return {"success": False, "msg": f"Connection error: {str(e)}"}

def generate_codes_api(count, prefix="UTS"):
    """Generate new codes via Admin API."""
    try:
        payload = {"action": "generate_codes", "count": count,
                   "prefix": prefix, "admin_key": ADMIN_KEY}
        r = requests.post(REGISTRY_URL, data=json.dumps(payload),
                          headers={"Content-Type": "application/json"}, timeout=20)
        return r.json()
    except Exception as e:
        return {"success": False, "msg": str(e)}

def deactivate_code_api(code):
    """Deactivate a code (removes device lock too)."""
    try:
        payload = {"action": "deactivate_code", "code": code, "admin_key": ADMIN_KEY}
        r = requests.post(REGISTRY_URL, data=json.dumps(payload),
                          headers={"Content-Type": "application/json"}, timeout=15)
        return r.json()
    except Exception as e:
        return {"success": False, "msg": str(e)}

def list_codes_api():
    """Get all codes list."""
    try:
        payload = {"action": "list_codes", "admin_key": ADMIN_KEY}
        r = requests.post(REGISTRY_URL, data=json.dumps(payload),
                          headers={"Content-Type": "application/json"}, timeout=15)
        return r.json()
    except Exception as e:
        return {"success": False, "msg": str(e)}


# ============================================================
# --- LOGIN GATE ---
# ============================================================
def show_login_gate(raw_fp, raw_ip):
    st.markdown("""
    <div class="uts-header">
        <div class="uts-badge">UTS SYSTEMS</div>
        <div class="uts-title">⚡ UTS <span>HUNTERS</span> ⚡</div>
        <div class="uts-subtitle">> Authorized Access Only</div>
        <div class="uts-divider"></div>
    </div>
    """, unsafe_allow_html=True)

    # FP not ready yet — auto reload after JS sets the param
    if not raw_fp or raw_fp == "unknown-device" or not raw_fp.startswith("FP"):
        st.components.v1.html("""
        <script>
        (function() {
            // Build fingerprint immediately
            var components = [
                navigator.userAgent || '',
                navigator.platform || '',
                screen.width + 'x' + screen.height + 'x' + screen.colorDepth,
                Intl.DateTimeFormat().resolvedOptions().timeZone || '',
                navigator.language || '',
                String(navigator.hardwareConcurrency || 0),
                String(navigator.maxTouchPoints || 0),
                String(new Date().getTimezoneOffset()),
                navigator.vendor || '',
                String(window.devicePixelRatio || 1),
                navigator.oscpu || navigator.platform || ''
            ];
            var raw = components.join('||');
            var hash = 5381;
            for (var i = 0; i < raw.length; i++) {
                hash = ((hash << 5) + hash) + raw.charCodeAt(i);
                hash = hash & hash;
            }
            var fp = 'FP'
                   + Math.abs(hash).toString(16).toUpperCase().padStart(8,'0')
                   + '_W' + screen.width
                   + '_C' + (navigator.hardwareConcurrency || 0)
                   + '_D' + screen.colorDepth
                   + '_P' + String(window.devicePixelRatio || 1).replace('.','');

            function doReload(ip) {
                var params = new URLSearchParams(window.location.search);
                params.set('_fp', fp);
                if (ip) params.set('_ip', ip);
                // Hard reload with new params — Streamlit will re-run
                window.location.href = window.location.pathname + '?' + params.toString();
            }

            // Try to get IP first, then reload
            fetch('https://api.ipify.org?format=json')
                .then(function(r){ return r.json(); })
                .then(function(d){ doReload(d.ip || 'noip'); })
                .catch(function(){ doReload('noip'); });
        })();
        </script>
        <div style="font-family:'JetBrains Mono',monospace; color:#5a7aa0;
                    text-align:center; padding:40px; font-size:12px;">
            ⚙ Verifying device... please wait.
        </div>
        """, height=80)
        st.stop()

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown('<div class="login-logo">⚡</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-title">UTS HUNTERS</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Enter Activation Code</div>', unsafe_allow_html=True)

        entered_code = st.text_input("🔑 ACTIVATION CODE:", placeholder="UTS-XXXXXXXXXXXX", key="login_input")

        if st.button("▶  ACTIVATE SESSION", key="login_btn"):
            if entered_code.strip():
                with st.spinner("Verifying device..."):
                    result = check_code_api(entered_code.strip(), raw_fp, raw_ip)
                if result.get("success"):
                    st.session_state["authenticated"] = True
                    st.session_state["operator_name"] = result.get("operator", "OPERATOR")
                    st.session_state["auth_code"] = entered_code.strip().upper()
                    st.rerun()
                else:
                    msg = result.get("msg", "UNKNOWN ERROR")
                    st.markdown(f'<div class="login-error">⛔ ACCESS DENIED — {msg}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="login-error">⚠ Please enter your activation code.</div>', unsafe_allow_html=True)

        st.markdown("""
        <div style="margin-top:24px; font-family:'JetBrains Mono',monospace;
             font-size:10px; color:#304560; text-align:center; line-height:1.8;">
            Each code is device-locked.<br>Contact admin for access.
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


# ============================================================
# --- MAIN AUTH FLOW ---
# ============================================================
inject_fingerprint_js()

qp     = st.query_params
raw_fp = qp.get("_fp", "unknown-device")
raw_ip = qp.get("_ip", "")

if "authenticated" not in st.session_state or not st.session_state.get("authenticated"):
    saved_code = qp.get("_ac", "")
    if saved_code and raw_fp and raw_fp.startswith("FP"):
        result = check_code_api(saved_code, raw_fp, raw_ip)
        if result.get("success"):
            st.session_state["authenticated"] = True
            st.session_state["operator_name"] = result.get("operator", "OPERATOR")
            st.session_state["auth_code"] = saved_code
        else:
            show_login_gate(raw_fp, raw_ip)
    else:
        show_login_gate(raw_fp, raw_ip)

operator_name = st.session_state.get("operator_name", "OPERATOR")
auth_code = st.session_state.get("auth_code", "")
is_admin = (operator_name == "Umer Ali")

if auth_code:
    persist_auth_in_url(auth_code)


# ============================================================
# --- HELPER FUNCTIONS ---
# ============================================================
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
        df['Status'] = df['Status'].fillna('')
        df['MemberName'] = df['Status'].str.replace('Allocated: ', '', case=False, regex=False).str.strip()
        return df.set_index('Phone Number')[['Range', 'MemberName']].to_dict('index')
    except:
        return {}

def get_team_info(num, team_data):
    n_str = str(num).split('.')[0].strip()
    if n_str in team_data:
        name = team_data[n_str]['MemberName']
        if name in ["UTS_Umer1", "UTS_Khadija"]: return "", ""
        return name, team_data[n_str]['Range']
    return "", ""

def highlight_team(row):
    if row.get('Team Member', '') != "":
        return ['background-color: rgba(0,170,255,0.08); color: #00aaff; font-weight: bold; border-right: 3px solid #00aaff;'] * len(row)
    return [''] * len(row)

def stream_to_google_sheet(raw_data):
    try:
        bg_df = pd.DataFrame(raw_data)
        if bg_df.empty: return
        bg_df['dt'] = pd.to_datetime(bg_df['dt']).dt.strftime('%Y-%m-%d %H:%M:%S')
        for _, row in bg_df.head(20).iterrows():
            payload = {"Time": row['dt'], "App": row['cli'],
                       "Number": str(row['num']), "Country": get_country(row['num']),
                       "Message": str(row['message'])}
            requests.post(GOOGLE_SCRIPT_URL, data=json.dumps(payload),
                          headers={'Content-Type': 'application/json'}, timeout=5)
    except:
        pass


# ============================================================
# --- HEADER ---
# ============================================================
st.markdown(f"""
<div class="uts-header">
    <div class="uts-badge">UTS SYSTEMS</div>
    <div class="uts-title">⚡ UTS <span>HUNTERS</span> ⚡</div>
    <div class="uts-subtitle">> Database Integrated Control Panel</div>
    <div class="uts-divider"></div>
</div>
<div class="operator-bar">
    <div class="op-item"><span class="pulse-dot"></span><span>LIVE</span></div>
    <div class="op-dot">|</div>
    <div class="op-item">OPERATOR: <span>{operator_name.upper()}</span></div>
    <div class="op-dot">|</div>
    <div class="op-item">SESSION: <span>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></div>
    <div class="op-dot">|</div>
    <div class="op-item">STATUS: <span style="color:#00e676;">✓ AUTHORIZED</span></div>
    {"<div class='op-dot'>|</div><div class='op-item'><span style='color:#f0b429;'>👑 ADMIN MODE</span></div>" if is_admin else ""}
</div>
""", unsafe_allow_html=True)


# ============================================================
# --- TABS ---
# ============================================================
tabs = ["📡  LIVE MONITORING", "📊  SHEET DATABASE"]
if is_admin:
    tabs.append("🔐  ADMIN PANEL")

tab_objects = st.tabs(tabs)
tab1 = tab_objects[0]
tab2 = tab_objects[1]
tab3 = tab_objects[2] if is_admin else None

# ---- TAB 1 SETUP ----
with tab1:
    col_in1, col_in2 = st.columns([2, 1])
    with col_in1: target_cli = st.text_input("⚙ TARGET AGENT (CLI):", "MYOB").strip()
    with col_in2: msg_limit = st.number_input("📡 STREAM BUFFER:", min_value=1, max_value=2000, value=1000)
    placeholder = st.empty()

# ---- TAB 2 SETUP ----
with tab2:
    st.markdown('<div class="section-label">REAL-TIME FILTERS — GOOGLE SHEET DATABASE</div>', unsafe_allow_html=True)
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1: filter_cli = st.text_input("🔍 App/CLI:", "").strip()
    with col_f2: filter_num = st.text_input("📞 Phone Number:", "").strip()
    with col_f3: filter_msg = st.text_input("💬 Message:", "").strip()
    history_placeholder = st.empty()

# ---- TAB 3: ADMIN PANEL ----
if is_admin and tab3:
    with tab3:
        st.markdown('<div class="section-label">CODE GENERATION</div>', unsafe_allow_html=True)

        st.markdown('<div class="admin-card">', unsafe_allow_html=True)
        st.markdown('<div class="admin-card-title">⚡ Generate New Activation Codes</div>', unsafe_allow_html=True)

        col_g1, col_g2, col_g3 = st.columns([1, 1, 2])
        with col_g1:
            gen_count = st.number_input("How many codes?", min_value=1, max_value=50, value=5)
        with col_g2:
            gen_prefix = st.text_input("Prefix:", value="UTS")
        with col_g3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("⚡ GENERATE CODES", key="gen_btn"):
                with st.spinner("Generating..."):
                    result = generate_codes_api(int(gen_count), gen_prefix)
                if result.get("success"):
                    new_codes = result.get("codes", [])
                    st.success(f"✅ {len(new_codes)} codes generated!")
                    codes_text = "\n".join(new_codes)
                    st.code(codes_text, language=None)
                    st.caption("Copy these codes and give to operators. Each code = 1 person, 1 device.")
                else:
                    st.error(f"❌ {result.get('msg')}")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-label">ALL CODES — MANAGE</div>', unsafe_allow_html=True)

        col_reload, _ = st.columns([1, 4])
        with col_reload:
            if st.button("🔄 REFRESH LIST", key="refresh_codes"):
                st.session_state["codes_list"] = None

        if st.button("📋 LOAD ALL CODES", key="load_codes") or st.session_state.get("codes_list"):
            if not st.session_state.get("codes_list"):
                with st.spinner("Loading..."):
                    result = list_codes_api()
                if result.get("success"):
                    st.session_state["codes_list"] = result.get("codes", [])
                else:
                    st.error(f"Error: {result.get('msg')}")

            codes_list = st.session_state.get("codes_list", [])
            if codes_list:
                codes_df = pd.DataFrame(codes_list)

                def color_status(val):
                    if val == "ACTIVE": return "color: #00e676; font-weight: bold;"
                    elif val == "DEACTIVATED": return "color: #ff3d71; font-weight: bold;"
                    return "color: #f0b429;"

                st.dataframe(
                    codes_df.style.applymap(color_status, subset=["status"]),
                    use_container_width=True, hide_index=True,
                    column_config={
                        "code": st.column_config.TextColumn("ACTIVATION CODE", width="large"),
                        "operator": st.column_config.TextColumn("OPERATOR NAME", width="medium"),
                        "status": st.column_config.TextColumn("STATUS", width="small"),
                        "created": st.column_config.TextColumn("CREATED AT", width="medium"),
                        "activated_at": st.column_config.TextColumn("DEVICE LOCKED AT", width="medium"),
                    }
                )

                st.markdown('<div class="section-label">DEACTIVATE / RESET A CODE</div>', unsafe_allow_html=True)
                st.markdown('<div class="admin-card">', unsafe_allow_html=True)
                st.markdown('<div class="admin-card-title">🔒 Deactivate Code (Also Removes Device Lock)</div>', unsafe_allow_html=True)

                col_d1, col_d2 = st.columns([2, 1])
                with col_d1:
                    deact_code = st.text_input("Enter code to deactivate:", placeholder="UTS-XXXXXXXXXXXX", key="deact_input")
                with col_d2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🚫 DEACTIVATE", key="deact_btn"):
                        if deact_code.strip():
                            with st.spinner("Processing..."):
                                res = deactivate_code_api(deact_code.strip().upper())
                            if res.get("success"):
                                st.success("✅ Code deactivated! Device lock removed. You can now give a new code to this person.")
                                st.session_state["codes_list"] = None
                                st.rerun()
                            else:
                                st.error(f"❌ {res.get('msg')}")
                        else:
                            st.warning("Enter a code first.")

                st.markdown("""
                <div style="font-family:'JetBrains Mono',monospace; font-size:10px; color:#304560; margin-top:12px;">
                ℹ️ Deactivating a code also removes the device lock — you can give a fresh new code to that person.
                </div>
                """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# --- COLUMN CONFIG ---
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
# --- MAIN LOOP ---
# ============================================================
while True:
    try:
        r = requests.get(URL, params={"token": TOKEN, "records": 100}, timeout=10)
        if r.status_code == 200:
            raw_json = r.json().get("data", [])
            df = pd.DataFrame(raw_json)

            if not df.empty:
                threading.Thread(target=stream_to_google_sheet, args=(raw_json,), daemon=True).start()

                df['dt'] = pd.to_datetime(df['dt'])
                now = datetime.now()
                df_5m = df[df['dt'] >= now - timedelta(minutes=5)]

                top1_name, top1_count = "NO DATA", 0
                top2_name, top2_count = "NO DATA", 0
                top3_name, top3_count = "NO DATA", 0

                if not df_5m.empty and 'cli' in df_5m.columns:
                    top_clis = df_5m['cli'].value_counts().head(3)
                    if len(top_clis) >= 1: top1_name, top1_count = top_clis.index[0], int(top_clis.iloc[0])
                    if len(top_clis) >= 2: top2_name, top2_count = top_clis.index[1], int(top_clis.iloc[1])
                    if len(top_clis) >= 3: top3_name, top3_count = top_clis.index[2], int(top_clis.iloc[2])

                total_records = len(df)
                unique_clis = df['cli'].nunique() if 'cli' in df.columns else 0
                unique_nums = df['num'].nunique() if 'num' in df.columns else 0
                df_target = df[df['cli'].str.contains(target_cli, case=False, na=False)].copy()

                with placeholder.container():
                    # STATS
                    st.markdown(f"""
                    <div class="stats-row">
                        <div class="stat-box"><div class="stat-val">{total_records}</div><div class="stat-lbl">Total Records</div></div>
                        <div class="stat-box"><div class="stat-val">{top1_count}</div><div class="stat-lbl">Top CLI (5min)</div></div>
                        <div class="stat-box"><div class="stat-val">{unique_clis}</div><div class="stat-lbl">Unique CLIs</div></div>
                        <div class="stat-box"><div class="stat-val">{unique_nums}</div><div class="stat-lbl">Unique Numbers</div></div>
                    </div>
                    """, unsafe_allow_html=True)

                    # LEADERBOARD
                    st.markdown(f"""
                    <div class="leaderboard-grid">
                        <div class="rank-card rank-1">
                            <div class="rank-watermark">1</div>
                            <div class="rank-badge">🏆 Top 1 — Last 5 Min</div>
                            <div class="rank-cli">{top1_name}</div>
                            <div class="rank-count">⚡ {top1_count} OTPs Intercepted</div>
                        </div>
                        <div class="rank-card rank-2">
                            <div class="rank-watermark">2</div>
                            <div class="rank-badge">🥈 Top 2 — Last 5 Min</div>
                            <div class="rank-cli">{top2_name}</div>
                            <div class="rank-count">⚡ {top2_count} OTPs Intercepted</div>
                        </div>
                        <div class="rank-card rank-3">
                            <div class="rank-watermark">3</div>
                            <div class="rank-badge">🥉 Top 3 — Last 5 Min</div>
                            <div class="rank-cli">{top3_name}</div>
                            <div class="rank-count">⚡ {top3_count} OTPs Intercepted</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # TARGET TRACKER
                    st.markdown(f'<div class="section-label">LIVE TARGET TRACKER — AGENT: {target_cli.upper()}</div>', unsafe_allow_html=True)
                    if not df_target.empty:
                        mid = df_target.head(25).copy()
                        mid[['Team Member', 'Range']] = mid['num'].apply(lambda x: pd.Series(get_team_info(x, team_data)))
                        mid['Country'] = mid['num'].apply(get_country)
                        mid = mid[['dt','cli','num','Country','message','Team Member','Range']].copy()
                        mid.columns = ['Time','App','Number','Country','Message','Team Member','Range']
                        mid['Time'] = pd.to_datetime(mid['Time'])
                        mid = mid.sort_values('Time', ascending=False)
                        mid['Time'] = mid['Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
                        st.dataframe(mid.style.apply(highlight_team, axis=1),
                                     use_container_width=True, height=300, hide_index=True, column_config=col_cfg)
                    else:
                        st.caption("▸ NO PACKETS FOR CURRENT TARGET AGENT.")

                    # GLOBAL STREAM
                    st.markdown('<div class="section-label">GLOBAL LIVE NETWORK STREAM</div>', unsafe_allow_html=True)
                    gdf = df.head(msg_limit).copy()
                    gdf[['Team Member', 'Range']] = gdf['num'].apply(lambda x: pd.Series(get_team_info(x, team_data)))
                    gdf['Country'] = gdf['num'].apply(get_country)
                    gdf = gdf[['dt','cli','num','Country','message','Team Member','Range']].copy()
                    gdf.columns = ['Time','App','Number','Country','Message','Team Member','Range']
                    gdf['Time'] = pd.to_datetime(gdf['Time'])
                    gdf = gdf.sort_values('Time', ascending=False)
                    gdf['Time'] = gdf['Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
                    st.dataframe(gdf.style.apply(highlight_team, axis=1),
                                 use_container_width=True, height=500, hide_index=True, column_config=col_cfg)

        # TAB 2: SHEET DATA
        sheet_r = requests.get(GOOGLE_SCRIPT_URL, timeout=10)
        if sheet_r.status_code == 200:
            sheet_data = sheet_r.json()
            if sheet_data:
                sdf = pd.DataFrame(sheet_data)
                if filter_cli: sdf = sdf[sdf['App'].astype(str).str.contains(filter_cli, case=False, na=False)]
                if filter_num: sdf = sdf[sdf['Number'].astype(str).str.contains(filter_num, na=False)]
                if filter_msg: sdf = sdf[sdf['Message'].astype(str).str.contains(filter_msg, case=False, na=False)]

                with history_placeholder.container():
                    st.markdown(f"""
                    <div style="font-family:'JetBrains Mono',monospace; font-size:11px; color:#5a7aa0; margin-bottom:12px;">
                        <span style="color:#00aaff; font-weight:700;">{len(sdf)}</span> permanent records in database
                    </div>
                    """, unsafe_allow_html=True)
                    if not sdf.empty:
                        try:
                            sdf['Time'] = pd.to_datetime(sdf['Time'])
                            sdf = sdf.sort_values('Time', ascending=False)
                            sdf['Time'] = sdf['Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
                        except: pass
                        sdf[['Team Member','Range']] = sdf['Number'].apply(lambda x: pd.Series(get_team_info(x, team_data)))
                        st.dataframe(sdf.style.apply(highlight_team, axis=1),
                                     use_container_width=True, height=600, hide_index=True, column_config=col_cfg)

        time.sleep(15)
        st.rerun()

    except Exception as e:
        time.sleep(5)
