import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import phonenumbers
from phonenumbers import geocoder

# --- CONFIG ---
URL = "http://51.77.216.195/crapi/lamix/viewstats"
TOKEN = "SVdVRTRSQkd-ZVZEYWVgfmiViFmCg3ZYX5FuZUJoUGZlgJWFhoyS"
TEAM_FILE = "Numbers_Export.csv"

# Page Config
st.set_page_config(page_title="DOUBLE FACER HUNTER - UMER ALI", layout="wide")

# --- DREAMHOST STYLE UI DESIGN ---
st.markdown("""
<style>
    /* Main Background - Clean White/Light Grey */
    .stApp { 
        background-color: #ffffff;
        color: #333333; 
    }
    
    /* Top Header Banner Style */
    .main-title { 
        text-align: center; 
        color: #0073eb; 
        font-size: 38px; 
        font-weight: 800;
        padding-top: 20px;
        font-family: 'Inter', sans-serif;
    }

    /* Professional Content Box (DreamHost Style) */
    .report-box { 
        background: #f8f9fa;
        border: 1px solid #e1e4e8;
        padding: 25px; 
        border-radius: 8px; 
        margin-bottom: 25px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }

    /* Analysis Header */
    .cli-header { 
        color: #111111; 
        font-size: 24px; 
        font-weight: 700; 
        margin-bottom: 15px; 
        text-align: center;
        border-bottom: 2px solid #0073eb;
        padding-bottom: 10px;
        display: inline-block;
        width: 100%;
    }

    /* Section Labels with Blue Accent */
    .section-label { 
        color: #0073eb; 
        font-size: 20px; 
        font-weight: 700; 
        margin-top: 25px;
        margin-bottom: 15px; 
        border-left: 5px solid #0073eb; 
        padding-left: 15px;
    }

    /* Input Controls Customization */
    .stTextInput>div>div>input {
        border: 1px solid #ced4da !important;
        border-radius: 4px !important;
        padding: 10px !important;
    }

    /* Blue Button Style for Numbers */
    .stNumberInput>div>div>input {
        border: 1px solid #0073eb !important;
        color: #0073eb !important;
        font-weight: bold;
    }

    /* Footer Text */
    .footer-sub {
        text-align: center;
        color: #666;
        font-size: 14px;
        margin-bottom: 30px;
    }

    /* DataFrame Styling */
    [data-testid="stTable"] {
        border-radius: 8px;
        overflow: hidden;
    }
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
        df = pd.read_csv(TEAM_FILE)
        df['Phone Number'] = df['Phone Number'].astype(str).str.split('.').str[0].str.strip()
        df['Status'] = df['Status'].fillna('') 
        df['MemberName'] = df['Status'].str.replace('Allocated: ', '', case=False, regex=False).str.strip()
        return df.set_index('Phone Number')[['Range', 'MemberName']].to_dict('index')
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return {}

# --- HEADER ---
st.markdown('<div class="main-title">DOUBLE FACER HUNTER</div>', unsafe_allow_html=True)
st.markdown('<div class="footer-sub">Verified System | Managed by <b>Umer Ali</b></div>', unsafe_allow_html=True)

# Inputs
col_in1, col_in2 = st.columns([2, 1])
with col_in1:
    target_cli = st.text_input("🔍 Search Application (CLI):", "MYOB").strip()
with col_in2:
    msg_limit = st.number_input("📥 Feed Limit:", min_value=1, max_value=2000, value=1000)

team_data = load_team_data()
placeholder = st.empty()

col_cfg = {
    "Range": st.column_config.TextColumn("Range", width="large"),
    "Message": st.column_config.TextColumn("Message", width="max"),
    "Time": st.column_config.TextColumn("Time", width="medium"),
}

# --- MAIN LOOP ---
while True:
    try:
        r = requests.get(URL, params={"token": TOKEN, "records": 5000})
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

                df_target_all = df[df['cli'].str.contains(target_cli, case=False, na=False)].copy()
                c5 = len(df_target_all[df_target_all['dt'] >= (now - timedelta(minutes=5))])
                c10 = len(df_target_all[df_target_all['dt'] >= (now - timedelta(minutes=10))])
                c30 = len(df_target_all[df_target_all['dt'] >= (now - timedelta(minutes=30))])
                c_today = len(df_target_all[df_target_all['dt'] >= start_day])

                def get_team_info(num):
                    n_str = str(num).split('.')[0].strip()
                    if n_str in team_data:
                        return team_data[n_str]['MemberName'], team_data[n_str]['Range']
                    return "", ""

                def highlight_team(row):
                    num_check = str(row['Number']).split('.')[0].strip()
                    if num_check in team_data:
                        # Professional Blue/White highlight
                        return ['background-color: #e7f3ff; color: #0073eb; font-weight: bold'] * len(row)
                    return [''] * len(row)

                with placeholder.container():
                    # STATS BOX
                    st.markdown(f"""
                    <div class="report-box">
                        <div class="cli-header">📊 {target_cli.upper()} LIVE ANALYTICS</div>
                        <table style="width:100%; color:#333; font-size:20px; text-align:center;">
                            <tr>
                                <td><small>5 Min</small><br><b style="color:#0073eb;">{c5}</b></td>
                                <td><small>10 Min</small><br><b style="color:#0073eb;">{c10}</b></td>
                                <td><small>30 Min</small><br><b style="color:#0073eb;">{c30}</b></td>
                                <td style="border-left: 1px solid #ddd;"><small>Total Today</small><br><b style="color:#28a745;">{c_today}</b></td>
                            </tr>
                        </table>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown(f'<div class="section-label">🎯 {target_cli.upper()} LIVE MONITOR</div>', unsafe_allow_html=True)
                    if not df_target_all.empty:
                        mid_df = df_target_all.head(20).copy()
                        mid_df[['Name', 'Range']] = mid_df['num'].apply(lambda x: pd.Series(get_team_info(x)))
                        mid_df['Country'] = mid_df['num'].apply(get_country)
                        
                        disp_mid = mid_df[['dt', 'cli', 'num', 'Country', 'message', 'Name', 'Range']]
                        disp_mid.columns = ['Time', 'App', 'Number', 'Country', 'Message', 'Team Member', 'Range']
                        
                        st.dataframe(disp_mid.style.apply(highlight_team, axis=1), 
                                     use_container_width=True, height=250, hide_index=True, column_config=col_cfg)

                    st.markdown('<div class="section-label">🌐 GLOBAL NETWORK FEED</div>', unsafe_allow_html=True)
                    global_df = df.head(msg_limit).copy()
                    global_df[['Name', 'Range']] = global_df['num'].apply(lambda x: pd.Series(get_team_info(x)))
                    global_df['Country'] = global_df['num'].apply(get_country)
                    
                    disp_global = global_df[['dt', 'cli', 'num', 'Country', 'message', 'Name', 'Range']]
                    disp_global.columns = ['Time', 'App', 'Number', 'Country', 'Message', 'Team Member', 'Range']

                    st.dataframe(disp_global.style.apply(highlight_team, axis=1), 
                                     use_container_width=True, height=800, hide_index=True, column_config=col_cfg)

            else:
                st.info("Awaiting incoming data stream...")

        time.sleep(15)
        st.rerun()
    except Exception as e:
        st.error(f"Connection Alert: {e}")
        time.sleep(5)
