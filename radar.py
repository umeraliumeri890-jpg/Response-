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
URL             = "http://51.77.216.195/crapi/lamix/viewstats"
TOKEN           = "X46ZeF6ViotShZl5WYRse1t3lYiKZ3CAdo6ZdINSh0o="
TEAM_FILE       = "Numbers_Export.csv"
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyTHahQPjxjbuZGcIWiN2AgY8lHJEDm7Pyi2QnpSJVV436Q65DOlOtmA2Ilux8UkVgl/exec"
REGISTRY_URL    = "https://script.google.com/macros/s/AKfycbzo_Z_7CEVEeKA9fL-M3WXtznKrd19MyiXTksRlbSd1E8bNXh8nZF5HsLdedOjG2iVF/exec"
ADMIN_KEY       = "UTS_ADMIN_2024"

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(page_title="UTS HUNTERS", page_icon="⚡", layout="wide")

# ============================================================
# CSS
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700;800&family=Inter:wght@300;400;600;700;900&display=swap');
    :root {
        --bg-primary:#040b1a; --bg-secondary:#071228; --bg-card:#0a1a35;
        --border-color:#112244; --border-accent:#1a3a70;
        --electric:#00aaff; --electric-dim:#0066bb;
        --gold:#f0b429; --silver:#a8b4c8; --bronze:#cd7f32;
        --green:#00e676; --red:#ff3d71;
        --text-primary:#c8deff; --text-secondary:#5a7aa0; --text-muted:#304560;
    }
    .stApp {
        background-color:var(--bg-primary) !important;
        background-image:
            radial-gradient(ellipse at 20% 0%,rgba(0,90,200,.08) 0%,transparent 60%),
            radial-gradient(ellipse at 80% 100%,rgba(0,60,150,.06) 0%,transparent 60%);
        font-family:'Inter',sans-serif;
    }
    .uts-header{text-align:center;padding:32px 20px 8px}
    .uts-badge{display:inline-block;background:linear-gradient(135deg,#071228,#0a1a35);
        border:1px solid var(--electric-dim);border-radius:2px;padding:4px 18px;
        font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:600;
        color:var(--electric);letter-spacing:6px;text-transform:uppercase;margin-bottom:12px}
    .uts-title{font-family:'Inter',sans-serif;font-size:52px;font-weight:900;
        color:#fff;letter-spacing:-1px;line-height:1;margin-bottom:6px}
    .uts-title span{color:var(--electric);text-shadow:0 0 30px rgba(0,170,255,.6)}
    .uts-subtitle{font-family:'JetBrains Mono',monospace;font-size:11px;
        color:var(--text-secondary);letter-spacing:4px;text-transform:uppercase;margin-bottom:28px}
    .uts-divider{height:1px;background:linear-gradient(90deg,transparent,var(--electric-dim),transparent);
        margin:0 auto 28px;max-width:600px}
    .operator-bar{display:flex;justify-content:center;align-items:center;gap:24px;
        padding:10px 20px;background:var(--bg-secondary);border:1px solid var(--border-color);
        border-radius:4px;margin-bottom:24px;font-family:'JetBrains Mono',monospace;font-size:11px}
    .op-item{color:var(--text-secondary)}.op-item span{color:var(--electric);font-weight:700}
    .op-dot{color:var(--border-accent)}
    .section-label{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;
        color:var(--text-secondary);letter-spacing:3px;text-transform:uppercase;
        margin-top:32px;margin-bottom:14px;padding-bottom:10px;
        border-bottom:1px solid var(--border-color);display:flex;align-items:center;gap:10px}
    .section-label::before{content:"";display:inline-block;width:3px;height:14px;
        background:var(--electric);border-radius:1px;box-shadow:0 0 8px var(--electric)}
    .leaderboard-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:28px}
    .rank-card{background:var(--bg-card);border:1px solid var(--border-color);
        border-radius:4px;padding:22px 20px;position:relative;overflow:hidden}
    .rank-card::before{content:"";position:absolute;top:0;left:0;right:0;height:1px;
        background:linear-gradient(90deg,transparent,var(--accent-color),transparent)}
    .rank-1{--accent-color:var(--gold);border-left:3px solid var(--gold)}
    .rank-2{--accent-color:var(--silver);border-left:3px solid var(--silver)}
    .rank-3{--accent-color:var(--bronze);border-left:3px solid var(--bronze)}
    .rank-badge{font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;
        letter-spacing:2px;text-transform:uppercase;margin-bottom:10px;color:var(--accent-color)}
    .rank-cli{color:#fff;font-size:26px;font-weight:800;text-transform:uppercase;
        overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-bottom:6px}
    .rank-count{font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--electric);font-weight:600}
    .rank-watermark{position:absolute;right:16px;top:50%;transform:translateY(-50%);
        font-size:52px;opacity:.04;font-weight:900;color:var(--accent-color)}
    .stats-row{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:28px}
    .stat-box{background:var(--bg-secondary);border:1px solid var(--border-color);
        border-radius:3px;padding:14px 18px;text-align:center}
    .stat-val{font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:800;
        color:var(--electric);line-height:1.1}
    .stat-lbl{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--text-secondary);
        letter-spacing:2px;text-transform:uppercase;margin-top:4px}
    .stTextInput>div>div>input,.stNumberInput>div>div>input{
        background-color:var(--bg-secondary) !important;color:var(--text-primary) !important;
        border:1px solid var(--border-accent) !important;border-radius:3px !important;
        font-family:'JetBrains Mono',monospace !important;font-size:13px !important}
    label{color:var(--text-secondary) !important;font-family:'JetBrains Mono',monospace !important;
        font-size:11px !important;letter-spacing:1px !important}
    .stTabs [data-baseweb="tab-list"]{background-color:var(--bg-secondary) !important;
        border-bottom:1px solid var(--border-color) !important;gap:4px !important;padding:0 6px !important}
    .stTabs [data-baseweb="tab"]{background-color:transparent !important;
        color:var(--text-secondary) !important;font-family:'JetBrains Mono',monospace !important;
        font-size:11px !important;font-weight:600 !important;letter-spacing:2px !important;
        text-transform:uppercase !important;border-radius:0 !important;padding:12px 20px !important;
        border-bottom:2px solid transparent !important}
    .stTabs [aria-selected="true"]{color:var(--electric) !important;
        border-bottom-color:var(--electric) !important;background-color:transparent !important}
    .stTabs [data-baseweb="tab-panel"]{background-color:transparent !important;padding-top:16px !important}
    ::-webkit-scrollbar{width:4px;height:4px}
    ::-webkit-scrollbar-track{background:var(--bg-primary)}
    ::-webkit-scrollbar-thumb{background:var(--electric-dim);border-radius:2px}
    .stButton>button{background:var(--electric-dim) !important;color:#fff !important;
        border:1px solid var(--electric) !important;border-radius:3px !important;
        font-family:'JetBrains Mono',monospace !important;font-size:12px !important;
        font-weight:700 !important;letter-spacing:2px !important;padding:10px 28px !important;
        text-transform:uppercase !important}
    .stButton>button:hover{background:var(--electric) !important;
        box-shadow:0 0 20px rgba(0,170,255,.3) !important}
    .pulse-dot{display:inline-block;width:8px;height:8px;background:var(--green);
        border-radius:50%;box-shadow:0 0 6px var(--green);animation:pulse 2s infinite;margin-right:6px}
    @keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.85)}}
    /* hide fp input completely */
    [data-testid="stTextInput"][aria-label="__fp_carrier__"] {display:none !important}
    .login-card{background:var(--bg-card);border:1px solid var(--border-accent);
        border-radius:6px;padding:48px 52px;
        box-shadow:0 20px 60px rgba(0,0,0,.5)}
    .login-error{background:rgba(255,61,113,.08);border:1px solid rgba(255,61,113,.3);
        border-radius:3px;padding:10px 16px;font-family:'JetBrains Mono',monospace;
        font-size:11px;color:var(--red);margin-top:12px}
    .admin-card{background:var(--bg-card);border:1px solid var(--border-color);
        border-radius:4px;padding:24px;margin-bottom:20px}
    .admin-card-title{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;
        color:var(--electric);letter-spacing:3px;text-transform:uppercase;
        margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid var(--border-color)}
</style>
""", unsafe_allow_html=True)


# ============================================================
# DEVICE FINGERPRINT — via hidden st.text_input + JS DOM trick
# This is the ONLY method that works reliably on Streamlit Cloud.
# JS writes into a hidden Streamlit text_input and triggers onChange.
# Python reads it as a normal widget value.
# ============================================================

def get_device_fingerprint() -> str:
    """
    Returns device fingerprint string.
    First call: returns empty (JS not run yet) → show spinner, rerun.
    Second call onwards: returns FP from widget value.
    """
    # Hidden carrier input — JS will fill this
    fp_val = st.text_input("__fp_carrier__", value="", key="__fp_input__", label_visibility="collapsed")

    # Inject JS to compute FP and fill the hidden input
    # JS targets the input by its aria-label attribute
    st.components.v1.html("""
    <script>
    (function() {
        function buildFP() {
            var c = [
                navigator.userAgent,
                navigator.platform,
                screen.width + 'x' + screen.height + 'x' + screen.colorDepth,
                Intl.DateTimeFormat().resolvedOptions().timeZone,
                navigator.language,
                String(navigator.hardwareConcurrency || 0),
                String(navigator.maxTouchPoints || 0),
                String(new Date().getTimezoneOffset()),
                navigator.vendor || '',
                String(window.devicePixelRatio || 1)
            ];
            var raw = c.join('||');
            var h = 5381;
            for (var i = 0; i < raw.length; i++) { h = ((h<<5)+h)+raw.charCodeAt(i); h=h&h; }
            return 'FP' + Math.abs(h).toString(16).toUpperCase().padStart(8,'0')
                 + 'W' + screen.width + 'H' + screen.height
                 + 'C' + (navigator.hardwareConcurrency||0)
                 + 'D' + screen.colorDepth;
        }

        function setInput(fp) {
            // Streamlit renders inputs in the parent frame — use window.parent
            var doc = window.parent.document;
            // Find by data-testid + placeholder or by iterating all inputs
            var inputs = doc.querySelectorAll('input[type="text"]');
            for (var i = 0; i < inputs.length; i++) {
                var inp = inputs[i];
                // The hidden input has empty value and its container has aria-label __fp_carrier__
                var container = inp.closest('[data-testid="stTextInput"]');
                if (container) {
                    var label = container.querySelector('label');
                    if (label && label.textContent.trim() === '__fp_carrier__') {
                        if (inp.value !== fp) {
                            // Set value via React's native input value setter
                            var nativeSetter = Object.getOwnPropertyDescriptor(
                                window.HTMLInputElement.prototype, 'value'
                            ).set;
                            nativeSetter.call(inp, fp);
                            inp.dispatchEvent(new Event('input', {bubbles:true}));
                        }
                        return true;
                    }
                }
            }
            return false;
        }

        var fp = buildFP();
        var attempts = 0;
        function trySet() {
            if (!setInput(fp) && attempts < 20) {
                attempts++;
                setTimeout(trySet, 150);
            }
        }
        trySet();
    })();
    </script>
    """, height=0)

    return fp_val  # empty on first render, filled on rerun


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
        payload = {"action": "generate_codes", "count": count, "prefix": prefix, "admin_key": ADMIN_KEY}
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
# MAIN AUTH FLOW
# ============================================================

# Always get FP first (hidden input trick)
device_fp = get_device_fingerprint()

# If not authenticated yet
if not st.session_state.get("authenticated"):

    # If we have saved code in session but fp just loaded — re-verify
    if st.session_state.get("pending_code") and device_fp and device_fp.startswith("FP"):
        saved_code = st.session_state["pending_code"]
        result = check_code_api(saved_code, device_fp)
        if result.get("success"):
            st.session_state["authenticated"] = True
            st.session_state["operator_name"] = result.get("operator", "OPERATOR")
            st.session_state["auth_code"] = saved_code
            st.session_state.pop("pending_code", None)
            st.rerun()

    # ---- LOGIN SCREEN ----
    st.markdown("""
    <div class="uts-header">
        <div class="uts-badge">UTS SYSTEMS</div>
        <div class="uts-title">⚡ UTS <span>HUNTERS</span> ⚡</div>
        <div class="uts-subtitle">> Authorized Access Only</div>
        <div class="uts-divider"></div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center">
            <div style="font-size:44px;margin-bottom:12px">⚡</div>
            <div style="font-family:Inter,sans-serif;font-size:24px;font-weight:900;color:#fff;margin-bottom:4px">UTS HUNTERS</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#304560;
                 letter-spacing:3px;text-transform:uppercase;margin-bottom:28px">Enter Activation Code</div>
        </div>
        """, unsafe_allow_html=True)

        entered_code = st.text_input("🔑 ACTIVATION CODE:", placeholder="UTS-XXXXXXXXXXXX", key="login_code_input")

        if st.button("▶  ACTIVATE SESSION", key="login_btn"):
            if entered_code.strip():
                if not device_fp or not device_fp.startswith("FP"):
                    # FP not ready yet — save code, rerun will catch it
                    st.session_state["pending_code"] = entered_code.strip().upper()
                    st.info("⚙ Verifying device... please wait 2 seconds and try again.")
                else:
                    with st.spinner("Verifying..."):
                        result = check_code_api(entered_code.strip(), device_fp)
                    if result.get("success"):
                        st.session_state["authenticated"] = True
                        st.session_state["operator_name"] = result.get("operator", "OPERATOR")
                        st.session_state["auth_code"] = entered_code.strip().upper()
                        st.rerun()
                    else:
                        msg = result.get("msg", "UNKNOWN ERROR")
                        st.markdown(f'<div class="login-error">⛔ ACCESS DENIED — {msg}</div>',
                                    unsafe_allow_html=True)
            else:
                st.markdown('<div class="login-error">⚠ Enter your activation code.</div>',
                            unsafe_allow_html=True)

        # Show FP status (small, for debugging — remove later)
        if device_fp and device_fp.startswith("FP"):
            st.markdown(f'<div style="font-family:JetBrains Mono,monospace;font-size:9px;'
                        f'color:#112244;text-align:center;margin-top:12px">'
                        f'🔒 Device: {device_fp[:24]}...</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:9px;'
                        'color:#f0b429;text-align:center;margin-top:12px">'
                        '⚙ Scanning device...</div>', unsafe_allow_html=True)

        st.markdown("""
        <div style="margin-top:20px;font-family:'JetBrains Mono',monospace;
             font-size:10px;color:#304560;text-align:center;line-height:1.8">
            Each code is device-locked.<br>Contact admin for access.
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.stop()


# ============================================================
# AUTHENTICATED — MAIN APP
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
        df['Status'] = df['Status'].fillna('')
        df['MemberName'] = df['Status'].str.replace('Allocated: ', '', case=False, regex=False).str.strip()
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
        return ['background-color:rgba(0,170,255,.08);color:#00aaff;font-weight:bold;border-right:3px solid #00aaff'] * len(row)
    return [''] * len(row)

def stream_to_google_sheet(raw_data):
    try:
        bg = pd.DataFrame(raw_data)
        if bg.empty: return
        bg['dt'] = pd.to_datetime(bg['dt']).dt.strftime('%Y-%m-%d %H:%M:%S')
        for _, row in bg.head(20).iterrows():
            requests.post(GOOGLE_SCRIPT_URL,
                data=json.dumps({"Time":row['dt'],"App":row['cli'],
                    "Number":str(row['num']),"Country":get_country(row['num']),
                    "Message":str(row['message'])}),
                headers={'Content-Type':'application/json'}, timeout=5)
    except: pass


# HEADER
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
    <div class="op-item">STATUS: <span style="color:#00e676">✓ AUTHORIZED</span></div>
    {"<div class='op-dot'>|</div><div class='op-item'><span style='color:#f0b429'>👑 ADMIN</span></div>" if is_admin else ""}
</div>
""", unsafe_allow_html=True)


# TABS
tab_labels = ["📡  LIVE MONITORING", "📊  SHEET DATABASE"]
if is_admin: tab_labels.append("🔐  ADMIN PANEL")
tab_objs = st.tabs(tab_labels)
tab1, tab2 = tab_objs[0], tab_objs[1]
tab3 = tab_objs[2] if is_admin else None

with tab1:
    c1, c2 = st.columns([2,1])
    with c1: target_cli = st.text_input("⚙ TARGET AGENT (CLI):", "MYOB").strip()
    with c2: msg_limit  = st.number_input("📡 STREAM BUFFER:", min_value=1, max_value=2000, value=1000)
    placeholder = st.empty()

with tab2:
    st.markdown('<div class="section-label">REAL-TIME FILTERS — GOOGLE SHEET DATABASE</div>', unsafe_allow_html=True)
    f1,f2,f3 = st.columns(3)
    with f1: filter_cli = st.text_input("🔍 App/CLI:", "").strip()
    with f2: filter_num = st.text_input("📞 Number:", "").strip()
    with f3: filter_msg = st.text_input("💬 Message:", "").strip()
    history_placeholder = st.empty()

if is_admin and tab3:
    with tab3:
        st.markdown('<div class="section-label">CODE GENERATION</div>', unsafe_allow_html=True)
        st.markdown('<div class="admin-card"><div class="admin-card-title">⚡ Generate New Activation Codes</div>', unsafe_allow_html=True)
        g1,g2,g3 = st.columns([1,1,2])
        with g1: gen_count  = st.number_input("How many?", min_value=1, max_value=50, value=5)
        with g2: gen_prefix = st.text_input("Prefix:", value="UTS")
        with g3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("⚡ GENERATE", key="gen_btn"):
                with st.spinner("Generating..."):
                    res = generate_codes_api(int(gen_count), gen_prefix)
                if res.get("success"):
                    st.success(f"✅ {len(res['codes'])} codes generated!")
                    st.code("\n".join(res['codes']), language=None)
                    st.caption("Give each code to ONE person only. Each code = 1 device lock.")
                else:
                    st.error(f"❌ {res.get('msg')}")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-label">MANAGE ALL CODES</div>', unsafe_allow_html=True)
        if st.button("📋 LOAD ALL CODES", key="load_codes") or st.session_state.get("codes_list"):
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
                    if v=="ACTIVE": return "color:#00e676;font-weight:bold"
                    if v=="DEACTIVATED": return "color:#ff3d71;font-weight:bold"
                    return "color:#f0b429"
                st.dataframe(cdf.style.applymap(cs, subset=["status"]),
                    use_container_width=True, hide_index=True,
                    column_config={
                        "code":         st.column_config.TextColumn("ACTIVATION CODE", width="large"),
                        "operator":     st.column_config.TextColumn("OPERATOR",        width="medium"),
                        "status":       st.column_config.TextColumn("STATUS",          width="small"),
                        "created":      st.column_config.TextColumn("CREATED",         width="medium"),
                        "activated_at": st.column_config.TextColumn("LOCKED AT",       width="medium"),
                        "last_seen":    st.column_config.TextColumn("LAST SEEN",       width="medium"),
                    })

                st.markdown('<div class="admin-card"><div class="admin-card-title">🔒 Deactivate / Reset Code</div>', unsafe_allow_html=True)
                d1,d2 = st.columns([2,1])
                with d1: deact_code = st.text_input("Code to deactivate:", placeholder="UTS-XXXXXXXXXXXX", key="deact_in")
                with d2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🚫 DEACTIVATE", key="deact_btn"):
                        if deact_code.strip():
                            with st.spinner("Processing..."):
                                r2 = deactivate_code_api(deact_code.strip().upper())
                            if r2.get("success"):
                                st.success("✅ Deactivated! Device lock removed.")
                                st.session_state["codes_list"] = None
                                st.rerun()
                            else:
                                st.error(f"❌ {r2.get('msg')}")
                st.markdown("</div>", unsafe_allow_html=True)

team_data = load_team_data()
col_cfg = {
    "Time":        st.column_config.TextColumn("TIMESTAMP",    width="medium"),
    "App":         st.column_config.TextColumn("IDENT/CLI",    width="small"),
    "Number":      st.column_config.TextColumn("DATA STREAM",  width="medium"),
    "Country":     st.column_config.TextColumn("LOCATION",     width="small"),
    "Message":     st.column_config.TextColumn("MESSAGE",      width="large"),
    "Team Member": st.column_config.TextColumn("OPERATOR",     width="medium"),
    "Range":       st.column_config.TextColumn("NETWORK RANGE",width="large"),
}


# ============================================================
# MAIN LOOP
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
                now      = datetime.now()
                df_5m    = df[df['dt'] >= now - timedelta(minutes=5)]

                t1n,t1c = "NO DATA",0
                t2n,t2c = "NO DATA",0
                t3n,t3c = "NO DATA",0
                if not df_5m.empty and 'cli' in df_5m.columns:
                    tc = df_5m['cli'].value_counts().head(3)
                    if len(tc)>=1: t1n,t1c = tc.index[0],int(tc.iloc[0])
                    if len(tc)>=2: t2n,t2c = tc.index[1],int(tc.iloc[1])
                    if len(tc)>=3: t3n,t3c = tc.index[2],int(tc.iloc[2])

                tr = len(df)
                uc = df['cli'].nunique() if 'cli' in df.columns else 0
                un = df['num'].nunique() if 'num' in df.columns else 0
                df_tgt = df[df['cli'].str.contains(target_cli, case=False, na=False)].copy()

                with placeholder.container():
                    st.markdown(f"""
                    <div class="stats-row">
                        <div class="stat-box"><div class="stat-val">{tr}</div><div class="stat-lbl">Total Records</div></div>
                        <div class="stat-box"><div class="stat-val">{t1c}</div><div class="stat-lbl">Top CLI (5min)</div></div>
                        <div class="stat-box"><div class="stat-val">{uc}</div><div class="stat-lbl">Unique CLIs</div></div>
                        <div class="stat-box"><div class="stat-val">{un}</div><div class="stat-lbl">Unique Numbers</div></div>
                    </div>
                    <div class="leaderboard-grid">
                        <div class="rank-card rank-1"><div class="rank-watermark">1</div>
                            <div class="rank-badge">🏆 Top 1 — Last 5 Min</div>
                            <div class="rank-cli">{t1n}</div><div class="rank-count">⚡ {t1c} OTPs</div></div>
                        <div class="rank-card rank-2"><div class="rank-watermark">2</div>
                            <div class="rank-badge">🥈 Top 2 — Last 5 Min</div>
                            <div class="rank-cli">{t2n}</div><div class="rank-count">⚡ {t2c} OTPs</div></div>
                        <div class="rank-card rank-3"><div class="rank-watermark">3</div>
                            <div class="rank-badge">🥉 Top 3 — Last 5 Min</div>
                            <div class="rank-cli">{t3n}</div><div class="rank-count">⚡ {t3c} OTPs</div></div>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown(f'<div class="section-label">LIVE TARGET TRACKER — AGENT: {target_cli.upper()}</div>', unsafe_allow_html=True)
                    if not df_tgt.empty:
                        md = df_tgt.head(25).copy()
                        md[['Team Member','Range']] = md['num'].apply(lambda x: pd.Series(get_team_info(x,team_data)))
                        md['Country'] = md['num'].apply(get_country)
                        md = md[['dt','cli','num','Country','message','Team Member','Range']].copy()
                        md.columns = ['Time','App','Number','Country','Message','Team Member','Range']
                        md['Time'] = pd.to_datetime(md['Time'])
                        md = md.sort_values('Time', ascending=False)
                        md['Time'] = md['Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
                        st.dataframe(md.style.apply(highlight_team,axis=1), use_container_width=True,
                                     height=300, hide_index=True, column_config=col_cfg)
                    else:
                        st.caption("▸ No packets for current target agent.")

                    st.markdown('<div class="section-label">GLOBAL LIVE NETWORK STREAM</div>', unsafe_allow_html=True)
                    gd = df.head(msg_limit).copy()
                    gd[['Team Member','Range']] = gd['num'].apply(lambda x: pd.Series(get_team_info(x,team_data)))
                    gd['Country'] = gd['num'].apply(get_country)
                    gd = gd[['dt','cli','num','Country','message','Team Member','Range']].copy()
                    gd.columns = ['Time','App','Number','Country','Message','Team Member','Range']
                    gd['Time'] = pd.to_datetime(gd['Time'])
                    gd = gd.sort_values('Time', ascending=False)
                    gd['Time'] = gd['Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
                    st.dataframe(gd.style.apply(highlight_team,axis=1), use_container_width=True,
                                 height=500, hide_index=True, column_config=col_cfg)

        sr = requests.get(GOOGLE_SCRIPT_URL, timeout=10)
        if sr.status_code == 200:
            sd = sr.json()
            if sd:
                sdf = pd.DataFrame(sd)
                if filter_cli: sdf = sdf[sdf['App'].astype(str).str.contains(filter_cli, case=False, na=False)]
                if filter_num: sdf = sdf[sdf['Number'].astype(str).str.contains(filter_num, na=False)]
                if filter_msg: sdf = sdf[sdf['Message'].astype(str).str.contains(filter_msg, case=False, na=False)]
                with history_placeholder.container():
                    st.markdown(f'<div style="font-family:JetBrains Mono,monospace;font-size:11px;color:#5a7aa0;margin-bottom:12px">'
                                f'<span style="color:#00aaff;font-weight:700">{len(sdf)}</span> permanent records</div>',
                                unsafe_allow_html=True)
                    if not sdf.empty:
                        try:
                            sdf['Time'] = pd.to_datetime(sdf['Time'])
                            sdf = sdf.sort_values('Time', ascending=False)
                            sdf['Time'] = sdf['Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
                        except: pass
                        sdf[['Team Member','Range']] = sdf['Number'].apply(lambda x: pd.Series(get_team_info(x,team_data)))
                        st.dataframe(sdf.style.apply(highlight_team,axis=1), use_container_width=True,
                                     height=600, hide_index=True, column_config=col_cfg)

        time.sleep(15)
        st.rerun()
    except Exception:
        time.sleep(5)
