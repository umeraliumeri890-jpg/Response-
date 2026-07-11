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
st.set_page_config(page_title="UTS HUNTERS", page_icon="⚡", layout="wide")

# ============================================================
# CSS
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700;800&family=Inter:wght@300;400;600;700;900&display=swap');
    :root {
        --bg:#040b1a; --bg2:#071228; --card:#0a1a35;
        --b1:#112244; --b2:#1a3a70;
        --e:#00aaff; --ed:#0066bb;
        --gold:#f0b429; --silver:#a8b4c8; --bronze:#cd7f32;
        --green:#00e676; --red:#ff3d71;
        --t1:#c8deff; --t2:#5a7aa0; --t3:#304560;
    }
    .stApp {
        background-color:var(--bg) !important;
        background-image:radial-gradient(ellipse at 20% 0%,rgba(0,90,200,.08) 0%,transparent 60%),
                         radial-gradient(ellipse at 80% 100%,rgba(0,60,150,.06) 0%,transparent 60%);
        font-family:'Inter',sans-serif;
    }
    .hdr{text-align:center;padding:32px 20px 8px}
    .badge{display:inline-block;background:linear-gradient(135deg,#071228,#0a1a35);
        border:1px solid var(--ed);border-radius:2px;padding:4px 18px;
        font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:600;
        color:var(--e);letter-spacing:6px;text-transform:uppercase;margin-bottom:12px}
    .title{font-size:52px;font-weight:900;color:#fff;letter-spacing:-1px;line-height:1;margin-bottom:6px}
    .title span{color:var(--e);text-shadow:0 0 30px rgba(0,170,255,.6)}
    .sub{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--t2);
        letter-spacing:4px;text-transform:uppercase;margin-bottom:28px}
    .divider{height:1px;background:linear-gradient(90deg,transparent,var(--ed),transparent);
        margin:0 auto 28px;max-width:600px}
    .opbar{display:flex;justify-content:center;align-items:center;gap:24px;
        padding:10px 20px;background:var(--bg2);border:1px solid var(--b1);
        border-radius:4px;margin-bottom:24px;font-family:'JetBrains Mono',monospace;font-size:11px}
    .oi{color:var(--t2)}.oi span{color:var(--e);font-weight:700}.od{color:var(--b2)}
    .sl{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;color:var(--t2);
        letter-spacing:3px;text-transform:uppercase;margin-top:32px;margin-bottom:14px;
        padding-bottom:10px;border-bottom:1px solid var(--b1);display:flex;align-items:center;gap:10px}
    .sl::before{content:"";display:inline-block;width:3px;height:14px;
        background:var(--e);border-radius:1px;box-shadow:0 0 8px var(--e)}
    .lg{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:28px}
    .rc{background:var(--card);border:1px solid var(--b1);border-radius:4px;
        padding:22px 20px;position:relative;overflow:hidden}
    .rc::before{content:"";position:absolute;top:0;left:0;right:0;height:1px;
        background:linear-gradient(90deg,transparent,var(--ac),transparent)}
    .r1{--ac:var(--gold);border-left:3px solid var(--gold)}
    .r2{--ac:var(--silver);border-left:3px solid var(--silver)}
    .r3{--ac:var(--bronze);border-left:3px solid var(--bronze)}
    .rb{font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;
        letter-spacing:2px;text-transform:uppercase;margin-bottom:10px;color:var(--ac)}
    .rn{color:#fff;font-size:26px;font-weight:800;text-transform:uppercase;
        overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-bottom:6px}
    .rc_{font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--e);font-weight:600}
    .rwm{position:absolute;right:16px;top:50%;transform:translateY(-50%);
        font-size:52px;opacity:.04;font-weight:900;color:var(--ac)}
    .sr{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:28px}
    .sb{background:var(--bg2);border:1px solid var(--b1);border-radius:3px;
        padding:14px 18px;text-align:center}
    .sv{font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:800;
        color:var(--e);line-height:1.1}
    .sl2{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--t2);
        letter-spacing:2px;text-transform:uppercase;margin-top:4px}
    .stTextInput>div>div>input,.stNumberInput>div>div>input{
        background-color:var(--bg2) !important;color:var(--t1) !important;
        border:1px solid var(--b2) !important;border-radius:3px !important;
        font-family:'JetBrains Mono',monospace !important;font-size:13px !important}
    label{color:var(--t2) !important;font-family:'JetBrains Mono',monospace !important;
        font-size:11px !important;letter-spacing:1px !important}
    .stTabs [data-baseweb="tab-list"]{background-color:var(--bg2) !important;
        border-bottom:1px solid var(--b1) !important;gap:4px !important;padding:0 6px !important}
    .stTabs [data-baseweb="tab"]{background:transparent !important;color:var(--t2) !important;
        font-family:'JetBrains Mono',monospace !important;font-size:11px !important;
        font-weight:600 !important;letter-spacing:2px !important;text-transform:uppercase !important;
        border-radius:0 !important;padding:12px 20px !important;border-bottom:2px solid transparent !important}
    .stTabs [aria-selected="true"]{color:var(--e) !important;border-bottom-color:var(--e) !important;
        background:transparent !important}
    .stTabs [data-baseweb="tab-panel"]{background:transparent !important;padding-top:16px !important}
    ::-webkit-scrollbar{width:4px;height:4px}
    ::-webkit-scrollbar-track{background:var(--bg)}
    ::-webkit-scrollbar-thumb{background:var(--ed);border-radius:2px}
    .stButton>button{background:var(--ed) !important;color:#fff !important;
        border:1px solid var(--e) !important;border-radius:3px !important;
        font-family:'JetBrains Mono',monospace !important;font-size:12px !important;
        font-weight:700 !important;letter-spacing:2px !important;padding:10px 28px !important;
        text-transform:uppercase !important}
    .stButton>button:hover{background:var(--e) !important;box-shadow:0 0 20px rgba(0,170,255,.3) !important}
    .pd{display:inline-block;width:8px;height:8px;background:var(--green);border-radius:50%;
        box-shadow:0 0 6px var(--green);animation:p 2s infinite;margin-right:6px}
    @keyframes p{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.85)}}
    .lc{background:var(--card);border:1px solid var(--b2);border-radius:6px;
        padding:48px 40px;box-shadow:0 20px 60px rgba(0,0,0,.5)}
    .le{background:rgba(255,61,113,.08);border:1px solid rgba(255,61,113,.3);
        border-radius:3px;padding:10px 16px;font-family:'JetBrains Mono',monospace;
        font-size:11px;color:var(--red);margin-top:12px}
    .ac{background:var(--card);border:1px solid var(--b1);border-radius:4px;
        padding:24px;margin-bottom:20px}
    .at{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;
        color:var(--e);letter-spacing:3px;text-transform:uppercase;
        margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid var(--b1)}
</style>
""", unsafe_allow_html=True)


# ============================================================
# SERVER-SIDE DEVICE FINGERPRINT
# No JS needed. Uses Streamlit's context headers.
# Works 100% on Streamlit Cloud.
# ============================================================
def get_server_side_fp() -> str:
    """
    Build a stable device fingerprint from HTTP headers available in Streamlit.
    User-Agent + Accept-Language + Accept-Encoding combined → SHA256 hash.
    This is consistent per browser/device and does NOT change on refresh.
    """
    try:
        # Streamlit 1.31+ exposes request headers via st.context
        headers = st.context.headers
        ua      = headers.get("User-Agent", "unknown")
        lang    = headers.get("Accept-Language", "")
        enc     = headers.get("Accept-Encoding", "")
        # Combine signals
        raw = f"{ua}|{lang}|{enc}"
        fp  = "FP" + hashlib.sha256(raw.encode()).hexdigest()[:20].upper()
        return fp
    except Exception:
        # Fallback for older Streamlit versions
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
# GET FINGERPRINT — always available, no JS needed
# ============================================================
device_fp = get_server_side_fp()


# ============================================================
# AUTH FLOW
# ============================================================
if not st.session_state.get("authenticated"):

    # Header
    st.markdown("""
    <div class="hdr">
        <div class="badge">UTS SYSTEMS</div>
        <div class="title">⚡ UTS <span>HUNTERS</span> ⚡</div>
        <div class="sub">> Authorized Access Only</div>
        <div class="divider"></div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        st.markdown('<div class="lc">', unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;margin-bottom:24px">
            <div style="font-size:44px;margin-bottom:10px">⚡</div>
            <div style="font-family:Inter,sans-serif;font-size:24px;font-weight:900;color:#fff;margin-bottom:4px">UTS HUNTERS</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#304560;letter-spacing:3px;text-transform:uppercase">Enter Activation Code</div>
        </div>
        """, unsafe_allow_html=True)

        entered_code = st.text_input("🔑 ACTIVATION CODE:", placeholder="UTS-XXXXXXXXXXXX", key="login_code")

        if st.button("▶  ACTIVATE SESSION", key="login_btn"):
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
                    st.markdown(f'<div class="le">⛔ ACCESS DENIED — {msg}</div>',
                                unsafe_allow_html=True)
            else:
                st.markdown('<div class="le">⚠ Enter your activation code.</div>',
                            unsafe_allow_html=True)

        st.markdown(f"""
        <div style="margin-top:20px;font-family:'JetBrains Mono',monospace;
             font-size:9px;color:#1a3a70;text-align:center;line-height:2">
            🔒 Device ID: {device_fp[:20]}...<br>
            <span style="color:#304560">Each code is device-locked. Contact admin for access.</span>
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
        return ['background-color:rgba(0,170,255,.08);color:#00aaff;font-weight:bold;border-right:3px solid #00aaff'] * len(row)
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


# HEADER
st.markdown(f"""
<div class="hdr">
    <div class="badge">UTS SYSTEMS</div>
    <div class="title">⚡ UTS <span>HUNTERS</span> ⚡</div>
    <div class="sub">> Database Integrated Control Panel</div>
    <div class="divider"></div>
</div>
<div class="opbar">
    <div class="oi"><span class="pd"></span><span>LIVE</span></div>
    <div class="od">|</div>
    <div class="oi">OPERATOR: <span>{operator_name.upper()}</span></div>
    <div class="od">|</div>
    <div class="oi">SESSION: <span>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></div>
    <div class="od">|</div>
    <div class="oi">STATUS: <span style="color:#00e676">✓ AUTHORIZED</span></div>
    {"<div class='od'>|</div><div class='oi'><span style='color:#f0b429'>👑 ADMIN</span></div>" if is_admin else ""}
</div>
""", unsafe_allow_html=True)


# TABS
tab_labels = ["📡  LIVE MONITORING", "📊  SHEET DATABASE"]
if is_admin: tab_labels.append("🔐  ADMIN PANEL")
tab_objs = st.tabs(tab_labels)
tab1, tab2 = tab_objs[0], tab_objs[1]
tab3 = tab_objs[2] if is_admin else None

with tab1:
    c1, c2 = st.columns([2, 1])
    with c1: target_cli = st.text_input("⚙ TARGET AGENT (CLI):", "MYOB").strip()
    with c2: msg_limit  = st.number_input("📡 STREAM BUFFER:", min_value=1, max_value=2000, value=500)
    placeholder = st.empty()

with tab2:
    st.markdown('<div class="sl">REAL-TIME FILTERS — GOOGLE SHEET DATABASE</div>', unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    with f1: filter_cli = st.text_input("🔍 App/CLI:", "").strip()
    with f2: filter_num = st.text_input("📞 Number:", "").strip()
    with f3: filter_msg = st.text_input("💬 Message:", "").strip()
    history_placeholder = st.empty()

if is_admin and tab3:
    with tab3:
        st.markdown('<div class="sl">CODE GENERATION</div>', unsafe_allow_html=True)
        st.markdown('<div class="ac"><div class="at">⚡ Generate New Codes</div>', unsafe_allow_html=True)
        g1, g2, g3 = st.columns([1, 1, 2])
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
                    st.caption("Give each code to ONE person only.")
                else:
                    st.error(f"❌ {res.get('msg')}")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="sl">ALL CODES</div>', unsafe_allow_html=True)
        col_r, _ = st.columns([1, 4])
        with col_r:
            if st.button("🔄 REFRESH", key="ref_btn"):
                st.session_state["codes_list"] = None

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
                    if v == "ACTIVE":      return "color:#00e676;font-weight:bold"
                    if v == "DEACTIVATED": return "color:#ff3d71;font-weight:bold"
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

                st.markdown('<div class="ac"><div class="at">🔒 Deactivate / Reset Code</div>', unsafe_allow_html=True)
                d1, d2 = st.columns([2, 1])
                with d1:
                    deact_code = st.text_input("Code to deactivate:", placeholder="UTS-XXXXXXXXXXXX", key="deact_in")
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
    "Time":        st.column_config.TextColumn("TIMESTAMP",     width="medium"),
    "App":         st.column_config.TextColumn("IDENT/CLI",     width="small"),
    "Number":      st.column_config.TextColumn("DATA STREAM",   width="medium"),
    "Country":     st.column_config.TextColumn("LOCATION",      width="small"),
    "Message":     st.column_config.TextColumn("MESSAGE",       width="large"),
    "Team Member": st.column_config.TextColumn("OPERATOR",      width="medium"),
    "Range":       st.column_config.TextColumn("NETWORK RANGE", width="large"),
}


# ============================================================
# MAIN LOOP
# ============================================================
while True:
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
                    <div class="sr">
                        <div class="sb"><div class="sv">{tr}</div><div class="sl2">Total Records</div></div>
                        <div class="sb"><div class="sv">{t1c}</div><div class="sl2">Top CLI (5min)</div></div>
                        <div class="sb"><div class="sv">{uc}</div><div class="sl2">Unique CLIs</div></div>
                        <div class="sb"><div class="sv">{un}</div><div class="sl2">Unique Numbers</div></div>
                    </div>
                    <div class="lg">
                        <div class="rc r1"><div class="rwm">1</div>
                            <div class="rb">🏆 Top 1 — Last 5 Min</div>
                            <div class="rn">{t1n}</div><div class="rc_">⚡ {t1c} OTPs</div></div>
                        <div class="rc r2"><div class="rwm">2</div>
                            <div class="rb">🥈 Top 2 — Last 5 Min</div>
                            <div class="rn">{t2n}</div><div class="rc_">⚡ {t2c} OTPs</div></div>
                        <div class="rc r3"><div class="rwm">3</div>
                            <div class="rb">🥉 Top 3 — Last 5 Min</div>
                            <div class="rn">{t3n}</div><div class="rc_">⚡ {t3c} OTPs</div></div>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown(f'<div class="sl">LIVE TARGET TRACKER — AGENT: {target_cli.upper()}</div>', unsafe_allow_html=True)
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
                        st.caption("▸ No packets for current target agent.")

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

        sr = requests.get(GOOGLE_SCRIPT_URL, timeout=10)
        if sr.status_code == 200:
            sd = sr.json()
            if sd:
                sdf = pd.DataFrame(sd)
                if filter_cli: sdf = sdf[sdf['App'].astype(str).str.contains(filter_cli, case=False, na=False)]
                if filter_num: sdf = sdf[sdf['Number'].astype(str).str.contains(filter_num, na=False)]
                if filter_msg: sdf = sdf[sdf['Message'].astype(str).str.contains(filter_msg, case=False, na=False)]
                with history_placeholder.container():
                    st.markdown(f'<div style="font-family:JetBrains Mono,monospace;font-size:11px;'
                                f'color:#5a7aa0;margin-bottom:12px"><span style="color:#00aaff;font-weight:700">'
                                f'{len(sdf)}</span> permanent records</div>', unsafe_allow_html=True)
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

        time.sleep(15)
        st.rerun()
    except Exception:
        time.sleep(5)
