import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import hashlib

# CONFIG
URL               = "http://51.77.216.195/crapi/lamix/viewstats"
TOKEN             = "aXZ0gVZXgoCAc2loX4iFSl9mVWB8hVdgdFVhW3SVZXM="
TEAM_FILE         = "Numbers_Export.csv"
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyTHahQPjxjbuZGcIWiN2AgY8lHJEDm7Pyi2QnpSJVV436Q65DOlOtmA2Ilux8UkVgl/exec"
REGISTRY_URL      = "https://script.google.com/macros/s/AKfycbzo_Z_7CEVEeKA9fL-M3WXtznKrd19MyiXTksRlbSd1E8bNXh8nZF5HsLdedOjG2iVF/exec"
ADMIN_KEY         = "UTS_ADMIN_2024"

st.set_page_config(page_title="UTS HUNTERS", page_icon="⚡", layout="wide")

# Modern Dark UI Styling
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
    .stApp { background-color:var(--bg) !important; font-family:'Inter',sans-serif; }
    .hdr{text-align:center;padding:20px 20px 5px}
    .badge{display:inline-block;background:linear-gradient(135deg,#071228,#0a1a35); border:1px solid var(--ed);border-radius:2px;padding:4px 18px; font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:600; color:var(--e);letter-spacing:6px;text-transform:uppercase;margin-bottom:12px}
    .title{font-size:42px;font-weight:900;color:#fff;letter-spacing:-1px;margin-bottom:6px}
    .title span{color:var(--e);text-shadow:0 0 30px rgba(0,170,255,.6)}
    .sub{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--t2);letter-spacing:4px;margin-bottom:15px}
    .divider{height:1px;background:linear-gradient(90deg,transparent,var(--ed),transparent);margin:0 auto 15px;max-width:600px}
    .opbar{display:flex;justify-content:center;align-items:center;gap:24px;padding:10px 20px;background:var(--bg2);border:1px solid var(--b1);border-radius:4px;margin-bottom:20px;font-family:'JetBrains Mono',monospace;font-size:11px}
    .oi{color:var(--t2)}.oi span{color:var(--e);font-weight:700}.od{color:var(--b2)}
    .sl{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;color:var(--t2);letter-spacing:3px;text-transform:uppercase;margin-top:20px;margin-bottom:10px;padding-bottom:5px;border-bottom:1px solid var(--b1);display:flex;align-items:center;gap:10px}
    .sl::before{content:"";display:inline-block;width:3px;height:14px;background:var(--e);}
    .sr{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}
    .sb{background:var(--bg2);border:1px solid var(--b1);border-radius:3px;padding:14px 18px;text-align:center}
    .sv{font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:800;color:var(--e);line-height:1.1}
    .sl2{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--t2);letter-spacing:2px;text-transform:uppercase;margin-top:4px}
    .pd{display:inline-block;width:8px;height:8px;background:var(--green);border-radius:50%;box-shadow:0 0 6px var(--green);margin-right:6px}
    .lc{background:var(--card);border:1px solid var(--b2);border-radius:6px;padding:40px;box-shadow:0 20px 60px rgba(0,0,0,.5)}
</style>
""", unsafe_allow_html=True)

# Session Auth
if not st.session_state.get("authenticated"):
    st.markdown('<div class="hdr"><div class="badge">UTS SYSTEMS</div><div class="title">⚡ UTS <span>HUNTERS</span> ⚡</div></div>', unsafe_allow_html=True)
    c1, col2, c3 = st.columns([1, 1.3, 1])
    with col2:
        st.markdown('<div class="lc">', unsafe_allow_html=True)
        entered_code = st.text_input("🔑 ACTIVATION CODE:", placeholder="UTS-XXXXXXXXXXXX")
        if st.button("▶  ACTIVATE"):
            st.session_state["authenticated"] = True
            st.session_state["operator_name"] = "UMER ALI"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

operator_name = st.session_state.get("operator_name", "OPERATOR")

# Static Python-based fast mapping (Zero C-Extensions)
def get_country(num):
    s = str(num).strip().lstrip('+')
    prefixes = {'1': 'USA/Canada', '44': 'United Kingdom', '61': 'Australia', '92': 'Pakistan', '91': 'India', '971': 'UAE', '966': 'Saudi Arabia'}
    for l in [3, 2, 1]:
        if len(s) >= l and s[:l] in prefixes: return prefixes[s[:l]]
    return "Global"

@st.cache_data(ttl=300)
def load_team_data():
    try:
        df = pd.read_csv(TEAM_FILE, dtype=str)
        df['Phone Number'] = df['Phone Number'].astype(str).str.split('.').str[0].str.strip()
        df['MemberName'] = df['Status'].fillna('').str.replace('Allocated: ', '', case=False, regex=False).str.strip()
        return df.set_index('Phone Number')[['Range', 'MemberName']].to_dict('index')
    except: 
        return {}

team_data = load_team_data()

# Native Render Friendly Auto Refresh (No loops)
st.fragment(run_every=2.0)
def render_realtime_interface():
    st.markdown(f'<div class="hdr"><div class="title">⚡ UTS <span>HUNTERS</span> ⚡</div></div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="opbar">
        <div class="oi"><span class="pd"></span><span>LIVE STREAM</span></div>
        <div class="od">|</div>
        <div class="oi">OPERATOR: <span>{operator_name}</span></div>
        <div class="od">|</div>
        <div class="oi">SYNC TIME: <span>{datetime.now().strftime('%H:%M:%S')}</span></div>
    </div>
    """, unsafe_allow_html=True)

    try:
        r = requests.get(URL, params={"token": TOKEN, "records": 100}, timeout=4)
        if r.status_code == 200:
            raw = r.json().get("data", [])
            df = pd.DataFrame(raw)
            if not df.empty:
                df['Country'] = df['num'].apply(get_country)
                
                st.markdown(f"""
                <div class="sr">
                    <div class="sb"><div class="sv">{len(df)}</div><div class="sl2">Current Packets</div></div>
                    <div class="sb"><div class="sv">{df['cli'].nunique()}</div><div class="sl2">Active Agents</div></div>
                    <div class="sb"><div class="sv">{df['num'].nunique()}</div><div class="sl2">Unique Targets</div></div>
                    <div class="sb"><div class="sv" style="color:#00e676">● 2.0s</div><div class="sl2">Refresh Rate</div></div>
                </div>
                """, unsafe_allow_html=True)
                
                display_df = df[['dt', 'cli', 'num', 'Country', 'message']].copy()
                display_df.columns = ['Time', 'Agent', 'Number', 'Country', 'Message']
                st.dataframe(display_df, width='stretch', height=550, hide_index=True)
            else:
                st.warning("Buffer stream empty.")
    except Exception as e:
        st.error("Data fetch timeout. Retrying next tick...")

render_realtime_interface()
