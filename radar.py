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

# --- MODERN WHITE & BLUE UI DESIGN ---
st.markdown("""
<style>
    /* Main Background - Soft Light Grey for a clean look */
    .stApp { 
        background-color: #f4f7f9;
        color: #2d3436; 
    }
    
    /* Top Header Section with Blue Gradient */
    .header-container {
        background: linear-gradient(90deg, #0073eb 0%, #0056b3 100%);
        padding: 30px;
        border-radius: 0px 0px 20px 20px;
        margin: -60px -20px 30px -20px;
        text-align: center;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.1);
    }

    .main-title { 
        color: #ffffff; 
        font-size: 40px; 
        font-weight: 800;
        margin-bottom: 5px;
        letter-spacing: 1px;
    }

    .footer-sub {
        color: rgba(255, 255, 255, 0.9);
        font-size: 15px;
    }

    /* Professional Content Card */
    .report-box { 
        background: #ffffff;
        border: 1px solid #e1e8ed;
        padding: 25px; 
        border-radius: 15px; 
        margin-bottom: 25px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
    }

    /* Analysis Header inside card */
    .cli-header { 
        color: #0073eb; 
        font-size: 24px; 
        font-weight: 700; 
        margin-bottom: 20px; 
        text-align: center;
        text-transform: uppercase;
    }

    /* Section Labels with Blue Accent */
    .section-label { 
        color: #0073eb; 
        font-size: 20px; 
        font-weight: 700; 
        margin-top: 25px;
        margin-bottom: 15px; 
        border-left: 6px solid #0073eb; 
        padding-left: 15px;
    }

    /* Input Field Styling */
    .stTextInput>div>div>input {
        border: 2px solid #e1e8ed !important;
        border-radius: 10px !important;
        padding: 12px !important;
        transition: 0.3s;
    }
    
    .stTextInput>div>div>input:focus {
        border-color: #0073eb !important;
        box-shadow: 0 0 8px rgba(0,115,235,0.2);
    }

    /* Table styling to make it pop */
    .stDataFrame {
        background: white;
        padding: 10px;
        border-radius: 15px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.02);
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

# --- HEADER SECTION ---
st.markdown("""
<div class="header-container">
    <div class="main-title">🎯 DOUBLE FACER HUNTER</div>
    <div class="footer-sub">Live Monitoring System | Developed by <b>Umer Ali</b></div>
</div>
""", unsafe_allow_html=True)

# Inputs
col_in1, col_in2 = st.columns([2, 1])
with col_in1:
    target_cli = st.text_input("🔍 Search App Name (CLI):", "MYOB").strip()
with col_in2:
    msg_limit = st.number_input("📥 Global Feed Limit:", min_value=1, max_value=2000, value=1000)

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
                        # Professional Blue highlight for team members
                        return ['background-color: #e7f3ff; color: #0073eb; font-weight: bold; border: 1px solid #0073eb'] * len(row)
                    return [''] * len(row)

                with placeholder.container():
                    # STATS BOX
                    st.markdown(f"""
                    <div class="report-box">
                        <div class="cli-header">📊 {target_cli.upper()} REAL-TIME STATS</div>
                        <div style="display: flex; justify-content: space-around; text-align: center;">
                            <div><p style="color:#636e72; margin-bottom:0;">5 Min</p><h2 style="color:#0073eb; margin-top:0;">{c5}</h2></div>
                            <div><p style="color:#636e72; margin-bottom:0;">10 Min</p><h2 style="color:#0073eb; margin-top:0;">{c10}</h2></div>
                            <div><p style="color:#636e72; margin-bottom:0;">30 Min</p><h2 style="color:#0073eb; margin-top:0;">{c30}</h2></div>
                            <div style="border-left: 2px solid #eee; padding-left: 40px;">
                                <p style="color:#636e72; margin-bottom:0;">Today's Total</p><h2 style="color:#2ecc71; margin-top:0;">{c_today}</h2>
                            </div>
                        </div>
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
                st.info("Scanning network for incoming data...")

        time.sleep(15)
        st.rerun()
    except Exception as e:
        st.error(f"Alert: {e}")
        time.sleep(5)
