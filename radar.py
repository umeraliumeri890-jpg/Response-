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

# --- CUSTOM BLUE & WHITE ANALYTICS UI ---
st.markdown("""
<style>
    /* Main Background - Royal Blue */
    .stApp { 
        background-color: #0073eb;
        color: #ffffff; 
    }
    
    /* Main Title */
    .main-title { 
        text-align: center; 
        color: #ffffff; 
        font-size: 40px; 
        font-weight: 800;
        padding-top: 20px;
    }

    /* FULL WHITE ANALYTICS BOX */
    .report-box { 
        background-color: #ffffff; /* Pure White Background */
        border: none;
        padding: 25px; 
        border-radius: 12px; 
        margin-bottom: 25px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
    }

    /* Inside Analytics Box Text - Blue */
    .cli-header { 
        color: #0073eb; 
        font-size: 24px; 
        font-weight: 700; 
        margin-bottom: 15px; 
        text-align: center;
        border-bottom: 1px solid #eee;
        padding-bottom: 10px;
    }

    .stats-text {
        color: #0073eb !important; /* Blue text for stats */
        font-weight: bold;
    }

    /* Section Labels */
    .section-label { 
        color: #ffffff; 
        font-size: 20px; 
        font-weight: 700; 
        margin-top: 25px;
        margin-bottom: 15px; 
        border-left: 5px solid #ffffff; 
        padding-left: 15px;
    }

    /* Input Field Styling */
    .stTextInput>div>div>input {
        background-color: white !important;
        color: #0073eb !important;
        border-radius: 6px !important;
    }

    .stNumberInput>div>div>input {
        background-color: white !important;
        color: #0073eb !important;
    }

    /* Table Styling */
    .stDataFrame {
        background-color: white;
        border-radius: 8px;
        padding: 5px;
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
st.markdown('<div class="main-title">🎯 DOUBLE FACER HUNTER</div>', unsafe_allow_html=True)
st.markdown('<div style="text-align:center; color:white; opacity:0.8; margin-bottom:20px;">System Secure | Managed by <b>Umer Ali</b></div>', unsafe_allow_html=True)

# Inputs
col_in1, col_in2 = st.columns([2, 1])
with col_in1:
    target_cli = st.text_input("🔍 Search CLI:", "MYOB").strip()
with col_in2:
    msg_limit = st.number_input("📥 Limit:", min_value=1, max_value=2000, value=1000)

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
                        # Gold highlight for team members in the white table
                        return ['background-color: #ffd700; color: #000; font-weight: bold'] * len(row)
                    return [''] * len(row)

                with placeholder.container():
                    # WHITE ANALYTICS BOX
                    st.markdown(f"""
                    <div class="report-box">
                        <div class="cli-header">📊 {target_cli.upper()} LIVE ANALYTICS</div>
                        <table style="width:100%; text-align:center; border-collapse: collapse;">
                            <tr class="stats-text" style="font-size:22px;">
                                <td style="padding:10px;">5m: {c5}</td>
                                <td style="padding:10px;">10m: {c10}</td>
                                <td style="padding:10px;">30m: {c30}</td>
                                <td style="border-left: 2px solid #ddd; padding:10px; color: #28a745;">Today: {c_today}</td>
                            </tr>
                        </table>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown(f'<div class="section-label">🎯 {target_cli.upper()} MONITORING</div>', unsafe_allow_html=True)
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
                st.info("Searching for incoming signals...")

        time.sleep(15)
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")
        time.sleep(5)
