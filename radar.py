import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

# CONFIG
URL = "http://51.77.216.195/crapi/lamix/viewstats"
TOKEN = "aXZ0gVZXgoCAc2loX4iFSl9mVWB8hVdgdFVhW3SVZXM="
TEAM_FILE = "Numbers_Export.csv"

st.set_page_config(page_title="UTS HUNTERS", page_icon="⚡", layout="wide")

# Custom Clean CSS Injection
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;700;900&display=swap');
    :root {
        --bg: #040b1a; --bg2: #071228; --card: #0a1a35;
        --b1: #112244; --b2: #1a3a70; --e: #00aaff;
        --green: #00e676; --t2: #5a7aa0;
    }
    .stApp { background-color: var(--bg) !important; font-family: 'Inter', sans-serif; }
    .hdr { text-align: center; padding: 15px; }
    .title { font-size: 38px; font-weight: 900; color: #fff; letter-spacing: -1px; }
    .title span { color: var(--e); text-shadow: 0 0 20px rgba(0,170,255,.5); }
    .opbar { display: flex; justify-content: center; gap: 20px; padding: 10px; background: var(--bg2); border: 1px solid var(--b1); border-radius: 4px; margin-bottom: 15px; font-family: 'JetBrains Mono', monospace; font-size: 11px; }
    .oi { color: var(--t2); } .oi span { color: var(--e); font-weight: 700; }
    .pd { display: inline-block; width: 8px; height: 8px; background: var(--green); border-radius: 50%; margin-right: 6px; }
    .sr { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 15px; }
    .sb { background: var(--bg2); border: 1px solid var(--b1); border-radius: 3px; padding: 10px; text-align: center; }
    .sv { font-family: 'JetBrains Mono', monospace; font-size: 24px; font-weight: 800; color: var(--e); }
    .sl2 { font-family: 'JetBrains Mono', monospace; font-size: 9px; color: var(--t2); text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# Layout setup (Inputs at the top)
c1, c2 = st.columns([2, 1])
with c1:
    target_cli = st.text_input("⚙ TARGET AGENT (CLI):", value="MYOB").strip()
with c2:
    msg_limit = st.number_input("📡 STREAM BUFFER:", min_value=10, max_value=1000, value=200)

# Main structure placeholders
hdr_placeholder = st.empty()
stats_placeholder = st.empty()
table_placeholder = st.empty()

def get_country(num):
    s = str(num).strip().lstrip('+')
    prefixes = {'1': 'USA/Canada', '44': 'United Kingdom', '61': 'Australia', '92': 'Pakistan', '91': 'India'}
    for l in [3, 2, 1]:
        if len(s) >= l and s[:l] in prefixes: return prefixes[s[:l]]
    return "Global"

# Production Pure Engine Loop
while True:
    # Update Header Info
    hdr_placeholder.markdown(f"""
    <div class="hdr"><div class="title">⚡ UTS <span>HUNTERS</span> ⚡</div></div>
    <div class="opbar">
        <div class="oi"><span class="pd"></span><span>LIVE STREAM</span></div>
        <div class="oi">|</div>
        <div class="oi">OPERATOR: <span>UMER ALI</span></div>
        <div class="oi">|</div>
        <div class="oi">SYNC TIME: <span>{datetime.now().strftime('%H:%M:%S')}</span></div>
    </div>
    """, unsafe_allow_html=True)

    try:
        # Fetch directly from live backend
        r = requests.get(URL, params={"token": TOKEN, "records": int(msg_limit)}, timeout=4)
        if r.status_code == 200:
            raw = r.json().get("data", [])
            df = pd.DataFrame(raw)
            
            if not df.empty:
                df['Country'] = df['num'].apply(get_country)
                
                # Render Metrics Dashboard
                stats_placeholder.markdown(f"""
                <div class="sr">
                    <div class="sb"><div class="sv">{len(df)}</div><div class="sl2">Total Packets</div></div>
                    <div class="sb"><div class="sv">{df['cli'].nunique()}</div><div class="sl2">Active CLIs</div></div>
                    <div class="sb"><div class="sv">{df['num'].nunique()}</div><div class="sl2">Unique Targets</div></div>
                    <div class="sb"><div class="sv" style="color:#00e676">CONNECTED</div><div class="sl2">Status</div></div>
                </div>
                """, unsafe_allow_html=True)
                
                # Process Table Grid
                display_df = df[['dt', 'cli', 'num', 'Country', 'message']].copy()
                display_df.columns = ['Time', 'Agent', 'Number', 'Country', 'Message']
                
                if target_cli:
                    display_df = display_df[display_df['Agent'].str.contains(target_cli, case=False, na=False)]
                
                table_placeholder.dataframe(display_df, width=1600, height=500, hide_index=True)
            else:
                table_placeholder.info("Stream queue is currently clear.")
        else:
            table_placeholder.error(f"Backend Server returned status: {r.status_code}")
    except Exception as e:
        table_placeholder.warning(f"Connection unstable. Re-syncing connection parameters...")
    
    # Simple hard structural sleep to prevent server high CPU throttling
    time.sleep(2)
