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

# Stylish UI Design
st.markdown("""
<style>
    .stApp { background-color: #050505; color: #00ff00; }
    .main-title { text-align: center; color: #00ff00; font-size: 35px; font-weight: bold; }
    .sub-title { text-align: center; color: #ffffff; font-size: 16px; margin-bottom: 20px; }
    .report-box { 
        background-color: #111; border: 2px solid #00ff00; 
        padding: 15px; border-radius: 10px; margin-bottom: 20px;
        box-shadow: 0px 0px 10px #00ff00;
    }
    .cli-header { color: #ffb703; font-size: 24px; font-weight: bold; margin-bottom: 10px; }
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

                # --- BACKGROUND 5 AM LOGIC ---
                if now.hour < 5:
                    start_day = (now - timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)
                else:
                    start_day = now.replace(hour=5, minute=0, second=0, microsecond=0)

                # --- 1: TARGETED CLI DATA ---
                df_target_all = df[df['cli'].str.contains(target_cli, case=False, na=False)].copy()
                
                c5 = len(df_target_all[df_target_all['dt'] >= (now - timedelta(minutes=5))])
                c10 = len(df_target_all[df_target_all['dt'] >= (now - timedelta(minutes=10))])
                c30 = len(df_target_all[df_target_all['dt'] >= (now - timedelta(minutes=30))])
                c_today = len(df_target_all[df_target_all['dt'] >= start_day])
                
                # --- 2: LIVE FEED PREVIEW ---
                df_live = df.head(msg_limit).copy()
                df_live['Country'] = df_live['num'].apply(get_country)

                with placeholder.container():
                    # SECTION A: DEDICATED CLI REPORT BOX
                    st.markdown(f"""
                    <div class="report-box">
                        <div class="cli-header">📊 {target_cli.upper()} LIVE ANALYSIS</div>
                        <table style="width:100%; color:white; font-size:20px;">
                            <tr>
                                <td><b>Last 5m:</b> {c5}</td>
                                <td><b>Last 10m:</b> {c10}</td>
                                <td><b>Last 30m:</b> {c30}</td>
                                <td style="color:#00ff00;"><b>Total Today:</b> {c_today}</td>
                            </tr>
                        </table>
                    </div>
                    """, unsafe_allow_html=True)

                    # SECTION B: GLOBAL MONITORING
                    st.subheader(f"🚀 Global Market Feed (Last {msg_limit} Records)")
                    
                    display_df = df_live[['dt', 'cli', 'num', 'Country', 'message']].copy()
                    display_df.columns = ['Time', 'App', 'Number', 'Country', 'Message']
                    
                    # --- HIGHLIGHT CODE INTEGRATED ---
                    def highlight_team(row):
                        is_team = str(row['Number']) in team_numbers
                        return ['background-color: #1d3557; color: #ffb703; font-weight: bold' if is_team else '' for _ in row]

                    st.dataframe(
                        display_df.style.apply(highlight_team, axis=1),
                        use_container_width=True,
                        height=500,
                        hide_index=True
                    )

            else:
                st.info("Searching market data...")

        time.sleep(15)
        st.rerun()
    except Exception as e:
        time.sleep(5)
