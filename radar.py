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

# Normal Layout (Zoom 100%)
st.set_page_config(page_title="HUNTING RADAR - UMER ALI", layout="wide")

# Stylish UI Design
st.markdown("""
<style>
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
def load_team_data():
    try:
        # CSV read karke Phone Number ko index banana
        df = pd.read_csv(TEAM_FILE)
        df['Phone Number'] = df['Phone Number'].astype(str).str.strip()
        # Status column se name nikalna (e.g., 'Allocated: UTS_Shan' -> 'UTS_Shan')
        df['MemberName'] = df['Status'].str.replace('Allocated: ', '', case=False)
        # Dictionary format: { '213556105442': {'Range': '...', 'Name': '...'}, ... }
        return df.set_index('Phone Number')[['Range', 'MemberName']].to_dict('index')
    except: return {}

# Header
st.markdown('<div class="main-title">🎯 HUNTING RADAR</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">✨ Powered by <b>Umer Ali</b> ✨</div>', unsafe_allow_html=True)

# Controls
col_in1, col_in2 = st.columns([2, 1])
with col_in1:
    target_cli = st.text_input("🔍 Search App (CLI):", "MYOB").strip()
with col_in2:
    msg_limit = st.number_input("📥 Global Feed Limit:", min_value=1, max_value=500, value=25)

team_data = load_team_data()
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

                # Function to map Team Info (Sirf list walon ke liye)
                def get_team_info(num):
                    n_str = str(num).strip()
                    if n_str in team_data:
                        info = team_data[n_str]
                        return info['MemberName'], info['Range']
                    return "", ""

                # Highlight Row Logic
                def highlight_team(row):
                    num_check = str(row['Number']).strip()
                    if num_check in team_data:
                        return ['background-color: #1d3557; color: #ffb703; font-weight: bold'] * len(row)
                    return [''] * len(row)

                with placeholder.container():
                    # TOP STATS
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

                    # --- MID BOX: TARGETED CLI ---
                    st.markdown(f'<div class="section-label">🎯 {target_cli.upper()} MONITORING</div>', unsafe_allow_html=True)
                    if not df_target_all.empty:
                        mid_df = df_target_all.head(20).copy()
                        mid_df[['Name', 'Range']] = mid_df['num'].apply(lambda x: pd.Series(get_team_info(x)))
                        mid_df['Country'] = mid_df['num'].apply(get_country)
                        
                        disp_mid = mid_df[['dt', 'Name', 'Range', 'num', 'Country', 'message']]
                        disp_mid.columns = ['Time', 'Team Member', 'Range', 'Number', 'Country', 'Message']
                        st.dataframe(disp_mid.style.apply(highlight_team, axis=1), use_container_width=True, height=250, hide_index=True)

                    # --- BOTTOM BOX: GLOBAL FEED ---
                    st.markdown('<div class="section-label">🚀 GLOBAL MARKET FEED</div>', unsafe_allow_html=True)
                    global_df = df.head(msg_limit).copy()
                    global_df[['Name', 'Range']] = global_df['num'].apply(lambda x: pd.Series(get_team_info(x)))
                    global_df['Country'] = global_df['num'].apply(get_country)
                    
                    disp_global = global_df[['dt', 'Name', 'Range', 'num', 'Country', 'message']]
                    disp_global.columns = ['Time', 'Team Member', 'Range', 'Number', 'Country', 'Message']
                    st.dataframe(disp_global.style.apply(highlight_team, axis=1), use_container_width=True, height=400, hide_index=True)

            else:
                st.info("Scanning market data...")

        time.sleep(15)
        st.rerun()
    except Exception:
        time.sleep(5)
                    
