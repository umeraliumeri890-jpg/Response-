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

# Updated Page Title for Browser Tab
st.set_page_config(page_title="DOUBLE FACER HUNTER - UMER ALI", layout="wide")

# --- PROFESSIONAL COLOR GRADING & UI ---
st.markdown("""
<style>
    /* Main Background with a deep radial gradient */
    .stApp { 
        background: radial-gradient(circle, #0a0a0a 0%, #050505 100%);
        color: #e0e0e0; 
    }
    
    /* Neon Glow Title with Sharp Typography */
    .main-title { 
        text-align: center; 
        color: #00ff00; 
        font-size: 42px; 
        font-weight: 800;
        text-shadow: 0px 0px 20px rgba(0, 255, 0, 0.5);
        letter-spacing: 2px;
        padding-top: 20px;
        font-family: 'Courier New', Courier, monospace;
    }

    /* Glassmorphism Analysis Box */
    .report-box { 
        background: rgba(20, 20, 20, 0.85);
        border: 1px solid rgba(0, 255, 0, 0.3);
        padding: 20px; 
        border-radius: 12px; 
        margin-bottom: 25px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.9);
        backdrop-filter: blur(8px);
    }

    /* Professional Header for Live Stats */
    .cli-header { 
        color: #ffb703; 
        font-size: 26px; 
        font-weight: bold; 
        margin-bottom: 15px; 
        text-align: center;
        text-transform: uppercase;
        border-bottom: 1px solid #333;
        padding-bottom: 10px;
    }

    /* Neon Accent Section Labels */
    .section-label { 
        color: #00ff00; 
        font-size: 22px; 
        font-weight: 700; 
        margin-top: 25px;
        margin-bottom: 15px; 
        border-left: 5px solid #00ff00; 
        padding-left: 15px;
        background: linear-gradient(90deg, rgba(0,255,0,0.15) 0%, rgba(0,0,0,0) 100%);
    }

    /* Input Field Styling - Cyber Look */
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        background-color: #111 !important;
        color: #00ff00 !important;
        border: 1px solid #00ff0033 !important;
        border-radius: 5px;
    }

    /* Scrollbar Styling */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: #050505; }
    ::-webkit-scrollbar-thumb { background: #333; border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: #00ff00; }
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
st.markdown('<div class="main-title">🎯 DOUBLE FACER HUNTER</div>', unsafe_allow_html=True)
st.markdown('<div style="text-align:center; color:#888; margin-bottom:25px; font-size: 14px;">🛠️ System Secure | Powered by <b>Umer Ali</b></div>', unsafe_allow_html=True)

# Input Controls
col_in1, col_in2 = st.columns([2, 1])
with col_in1:
    target_cli = st.text_input("🔍 Search App (CLI):", "MYOB").strip()
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
        # Fetching data with high records count
        r = requests.get(URL, params={"token": TOKEN, "records": 5000})
        if r.status_code == 200:
            data = r.json().get("data", [])
            df = pd.DataFrame(data)
            
            if not df.empty:
                df['dt'] = pd.to_datetime(df['dt'])
                now = datetime.now()

                # Daily Reset logic (5 AM)
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
                        # Professional highlight for team members
                        return ['background-color: #1d3557; color: #ffb703; font-weight: bold'] * len(row)
                    return [''] * len(row)

                with placeholder.container():
                    # LIVE ANALYSIS BOX
                    st.markdown(f"""
                    <div class="report-box">
                        <div class="cli-header">📊 {target_cli.upper()} LIVE ANALYSIS</div>
                        <table style="width:100%; color:white; font-size:22px; text-align:center; border-collapse: collapse;">
                            <tr>
                                <td style="padding:10px;"><b>5m:</b> <span style="color:#00ff00;">{c5}</span></td>
                                <td style="padding:10px;"><b>10m:</b> <span style="color:#00ff00;">{c10}</span></td>
                                <td style="padding:10px;"><b>30m:</b> <span style="color:#00ff00;">{c30}</span></td>
                                <td style="color:#00ff00; border-left: 2px solid #333; padding:10px;"><b>Today: {c_today}</b></td>
                            </tr>
                        </table>
                    </div>
                    """, unsafe_allow_html=True)

                    # TARGET MONITORING TABLE
                    st.markdown(f'<div class="section-label">🎯 {target_cli.upper()} MONITORING</div>', unsafe_allow_html=True)
                    if not df_target_all.empty:
                        mid_df = df_target_all.head(20).copy()
                        mid_df[['Name', 'Range']] = mid_df['num'].apply(lambda x: pd.Series(get_team_info(x)))
                        mid_df['Country'] = mid_df['num'].apply(get_country)
                        
                        disp_mid = mid_df[['dt', 'cli', 'num', 'Country', 'message', 'Name', 'Range']]
                        disp_mid.columns = ['Time', 'App', 'Number', 'Country', 'Message', 'Team Member', 'Range']
                        
                        st.dataframe(disp_mid.style.apply(highlight_team, axis=1), 
                                     use_container_width=True, height=300, hide_index=True, column_config=col_cfg)

                    # GLOBAL FEED TABLE
                    st.markdown('<div class="section-label">🚀 GLOBAL MARKET FEED</div>', unsafe_allow_html=True)
                    global_df = df.head(msg_limit).copy()
                    global_df[['Name', 'Range']] = global_df['num'].apply(lambda x: pd.Series(get_team_info(x)))
                    global_df['Country'] = global_df['num'].apply(get_country)
                    
                    disp_global = global_df[['dt', 'cli', 'num', 'Country', 'message', 'Name', 'Range']]
                    disp_global.columns = ['Time', 'App', 'Number', 'Country', 'Message', 'Team Member', 'Range']

                    st.dataframe(disp_global.style.apply(highlight_team, axis=1), 
                                     use_container_width=True, height=800, hide_index=True, column_config=col_cfg)

            else:
                st.info("Searching for data in the shadows...")

        time.sleep(15)
        st.rerun()
    except Exception as e:
        st.error(f"System Glitch: {e}")
        time.sleep(5)
