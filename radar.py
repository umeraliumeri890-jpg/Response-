import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import phonenumbers
from phonenumbers import geocoder

# --- CONFIG ---
URL = "http://51.77.216.195/crapi/lamix/viewstats"
TOKEN = "SVdVRTRSQmiGX4FWYJJzgF-Hi4mHX41TglBhWVtieEOEUHhleGFy"
TEAM_FILE = "Numbers_Export.csv"

st.set_page_config(page_title="HUNTING RADAR - UMER ALI", layout="wide")

# Stylish UI Design with ZOOM-OUT Fix
st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"] {
        zoom: 0.9; /* Yeh poori site ko 90% zoom-out kar dega */
        -moz-transform: scale(0.9);
        -moz-transform-origin: 0 0;
    }
    .stApp { background-color: #050505; color: #00ff00; }
    .main-title { text-align: center; color: #00ff00; font-size: 35px; font-weight: bold; }
    .sub-title { text-align: center; color: #ffffff; font-size: 16px; margin-bottom: 20px; }
    .report-box { 
        background-color: #111; border: 2px solid #00ff00; 
        padding: 15px; border-radius: 15px; margin-bottom: 20px;
        box-shadow: 0px 0px 15px #00ff00;
    }
    .cli-header { color: #ffb703; font-size: 24px; font-weight: bold; margin-bottom: 10px; text-align: center; }
    .section-label { color: #00ff00; font-size: 18px; font-weight: bold; margin-bottom: 10px; border-left: 5px solid #00ff00; padding-left: 10px; }
</style>
""", unsafe_allow_html=True)

# Helper Functions
def get_country(num):
    try:
        full_num = "+" + str(num).strip()
        parsed = phonenumbers.parse(full_num)
        return geocoder.description_for_number(parsed, "en")
    except: return "Global"

@st.cache_data
def load_team_numbers():
    try:
        df = pd.read_csv(TEAM_FILE)
        return df['Phone Number'].astype(str).tolist()
    except: return []

# Header Section
st.markdown('<div class="main-title">🎯 HUNTING RADAR</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">✨ Powered by <b>Umer Ali</b> ✨</div>', unsafe_allow_html=True)

# Input Controls
col_in1, col_in2 = st.columns([2, 1])
with col_in1:
    target_cli = st.text_input("🔍 Search App (CLI):", "MYOB").strip()
with col_in2:
    msg_limit = st.number_input("📥 Global Feed Limit:", min_value=1, max_value=500, value=25)

team_numbers = load_team_numbers()
placeholder = st.empty()

while True:
    try:
        r = requests.get(URL, params={"token": TOKEN, "records": 3500})
        if r.status_code == 200:
            data = r.json().get("data", [])
            df = pd.DataFrame(data)
            
            if not df.empty:
                df['dt'] = pd.to_datetime(df['dt'])
                now = datetime.now()

                # --- 5 AM RESET LOGIC ---
                if now.hour < 5:
                    start_day = (now - timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)
                else:
                    start_day = now.replace(hour=5, minute=0, second=0, microsecond=0)

                # --- TARGETED CLI DATA ---
                df_target_all = df[df['cli'].str.contains(target_cli, case=False, na=False)].copy()
                
                c5 = len(df_target_all[df_target_all['dt'] >= (now - timedelta(minutes=5))])
                c10 = len(df_target_all[df_target_all['dt'] >= (now - timedelta(minutes=10))])
                c30 = len(df_target_all[df_target_all['dt'] >= (now - timedelta(minutes=30))])
                c_today = len(df_target_all[df_target_all['dt'] >= start_day])

                # Highlighter Logic
                def highlight_team(row):
                    is_team = str(row['Number']) in team_numbers
                    return ['background-color: #1d3557; color: #ffb703; font-weight: bold' if is_team else '' for _ in row]

                with placeholder.container():
                    # --- SECTION 1: TOP STATS BOX ---
                    st.markdown(f"""
                    <div class="report-box">
                        <div class="cli-header">📊 {target_cli.upper()} ANALYSIS</div>
                        <table style="width:100%; color:white; font-size:20px; text-align:center;">
                            <tr>
                                <td><b>5m:</b> {c5}</td>
                                <td><b>10m:</b> {c10}</td>
                                <td><b>30m:</b> {c30}</td>
                                <td style="color:#00ff00; border-left: 1px solid #333;"><b>Today: {c_today}</b></td>
                            </tr>
                        </table>
                    </div>
                    """, unsafe_allow_html=True)

                    # --- SECTION 2: MID BOX (TARGETED CLI FEED) ---
                    st.markdown(f'<div class="section-label">🎯 {target_cli.upper()} MONITORING</div>', unsafe_allow_html=True)
                    if not df_target_all.empty:
                        df_target_view = df_target_all.head(15).copy()
                        df_target_view['Country'] = df_target_view['num'].apply(get_country)
                        display_target = df_target_view[['dt', 'cli', 'num', 'Country', 'message']]
                        display_target.columns = ['Time', 'App', 'Number', 'Country', 'Message']
                        
                        st.dataframe(
                            display_target.style.apply(highlight_team, axis=1),
                            use_container_width=True, height=250, hide_index=True
                        )
                    else:
                        st.warning(f"No live data found for {target_cli}")

                    # --- SECTION 3: BOTTOM BOX (GLOBAL FEED) ---
                    st.markdown('<div class="section-label">🚀 GLOBAL MARKET FEED</div>', unsafe_allow_html=True)
                    df_live = df.head(msg_limit).copy()
                    df_live['Country'] = df_live['num'].apply(get_country)
                    display_global = df_live[['dt', 'cli', 'num', 'Country', 'message']]
                    display_global.columns = ['Time', 'App', 'Number', 'Country', 'Message']

                    st.dataframe(
                        display_global.style.apply(highlight_team, axis=1),
                        use_container_width=True, height=350, hide_index=True
                    )

            else:
                st.info("Scanning market data...")

        time.sleep(15)
        st.rerun()
    except Exception:
        time.sleep(5)
                
