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
def load_team_dict():
    try:
        df = pd.read_csv(TEAM_FILE)
        return pd.Series(df.Name.values, index=df['Phone Number'].astype(str)).to_dict()
    except: return {}

# Header
st.markdown('<div class="main-title">🎯 HUNTING RADAR</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Powered by Umer Ali</div>', unsafe_allow_html=True)

# Controls
col_in1, col_in2 = st.columns([2, 1])
with col_in1:
    target_cli = st.text_input("🔍 Search App (CLI):", "MYOB").strip()
with col_in2:
    msg_limit = st.number_input("📥 Global Feed Limit:", min_value=1, max_value=500, value=25)

team_dict = load_team_dict()
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

                # 5 AM Logic
                if now.hour < 5:
                    start_day = (now - timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)
                else:
                    start_day = now.replace(hour=5, minute=0, second=0, microsecond=0)

                # --- 1: TARGETED CLI DATA ---
                df_target_all = df[df['cli'].str.contains(target_cli, case=False, na=False)].copy()
                
                # Calculations
                c5 = len(df_target_all[df_target_all['dt'] >= (now - timedelta(minutes=5))])
                c10 = len(df_target_all[df_target_all['dt'] >= (now - timedelta(minutes=10))])
                c30 = len(df_target_all[df_target_all['dt'] >= (now - timedelta(minutes=30))])
                c_today = len(df_target_all[df_target_all['dt'] >= start_day])
                
                # --- 2: LIVE FEED PREP ---
                df_live = df.head(msg_limit).copy()
                
                def attach_info(num):
                    n_str = str(num)
                    country = get_country(num)
                    if n_str in team_dict:
                        return f"👤 {team_dict[n_str]}", country
                    return n_str, country

                with placeholder.container():
                    # --- SECTION A: DEDICATED CLI REPORT BOX ---
                    st.markdown(f'<div class="report-box"><div class="cli-header">📊 {target_cli.upper()} LIVE REPORT</div>', unsafe_allow_html=True)
                    
                    # Metrics for CLI
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Last 5m", f"{c5} OTP")
                    m2.metric("Last 10m", f"{c10} OTP")
                    m3.metric("Last 30m", f"{c30} OTP")
                    m4.metric("Today (Since 5AM)", f"{c_today} OTP")

                    # Target App ki apni choti monitoring table (Last 10 messages of this app)
                    st.write(f"**Latest {target_cli.upper()} Hits:**")
                    if not df_target_all.empty:
                        target_mini = df_target_all.head(10)[['dt', 'num', 'message']].copy()
                        target_mini.columns = ['Time', 'Number', 'OTP Message']
                        st.dataframe(target_mini, use_container_width=True, hide_index=True)
                    else:
                        st.info(f"No active hits for {target_cli} right now.")
                    
                    st.markdown('</div>', unsafe_allow_html=True)

                    # --- SECTION B: GLOBAL MONITORING ---
                    st.subheader(f"🚀 Global Market Feed (Last {msg_limit} Mixed Records)")
                    
                    df_live['User/Number'] = df_live['num'].apply(lambda x: attach_info(x)[0])
                    df_live['Country'] = df_live['num'].apply(lambda x: attach_info(x)[1])
                    
                    display_df = df_live[['dt', 'cli', 'User/Number', 'Country', 'message']].copy()
                    display_df.columns = ['Time', 'App', 'User/Number', 'Country', 'Message']
                    
                    def highlight_team(row):
                        is_team = "👤" in str(row['User/Number'])
                        return ['background-color: #1d3557; color: #ffb703; font-weight: bold' if is_team else '' for _ in row]

                    st.dataframe(display_df.style.apply(highlight_team, axis=1), use_container_width=True, height=450)

            else:
                st.info("Searching market...")

        time.sleep(15)
        st.rerun()
    except Exception as e:
        time.sleep(5)
                    
