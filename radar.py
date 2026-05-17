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

# --- UI DESIGN ---
st.markdown("""
<style>
    /* Main Background */
    .stApp { 
        background-color: #0073eb;
        color: #ffffff; 
    }
    
    /* Main Title */
    .main-title { 
        text-align: center; 
        color: #ffffff; 
        font-size: 35px; 
        font-weight: 800;
        padding-top: 10px;
        margin-bottom: 20px;
    }

    /* SECTION HEADINGS */
    .section-label { 
        color: #ffffff; 
        font-size: 22px; 
        font-weight: 900; 
        margin-top: 35px;
        margin-bottom: 15px; 
        border-left: 6px solid #ffffff; 
        padding-left: 15px;
        text-transform: uppercase;
    }

    /* TABLE HEADER FIX */
    .stDataFrame thead tr th {
        background-color: #f0f2f6 !important;
        color: #31333f !important;
        font-weight: 800 !important;
        border: 1px solid #dee2e6 !important;
    }

    /* Analytics Box */
    .report-box { 
        background-color: #ffffff; 
        border-radius: 8px; 
        margin-bottom: 25px;
        border: 1px solid #ddd;
    }
    .analytics-header-row { background-color: #f8f9fa; display: flex; border-bottom: 1px solid #dee2e6; }
    .header-item { flex: 1; padding: 10px; color: #6c757d; font-size: 14px; font-weight: 800; border-right: 1px solid #dee2e6; padding-left: 15px; }
    .analytics-data-row { display: flex; background-color: white; }
    .data-item { flex: 1; padding: 15px; color: #000; font-size: 24px; font-weight: 700; border-right: 1px solid #eee; padding-left: 15px; }

    /* Inputs */
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        background-color: white !important;
        color: #0073eb !important;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
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
    except Exception: return {}

def get_team_info(num, team_data):
    """Returns MemberName and Range, but ignores specific users."""
    n_str = str(num).split('.')[0].strip()
    if n_str in team_data:
        name = team_data[n_str]['MemberName']
        # EXCLUSION LOGIC: In names ka data normal show hoga
        if name in ["UTS_Umer1", "UTS_Khadija"]:
            return "", ""
        return name, team_data[n_str]['Range']
    return "", ""

def highlight_team(row):
    """Highlights rows ONLY if a team member name exists (after exclusion)."""
    if row['Team Member'] != "":
        return ['background-color: #ffd700; color: #000; font-weight: bold'] * len(row)
    return [''] * len(row)

# --- HEADER ---
st.markdown('<div class="main-title">🎯 DOUBLE FACER HUNTER</div>', unsafe_allow_html=True)

# Inputs
col_in1, col_in2 = st.columns([2, 1])
with col_in1:
    target_cli = st.text_input("Search App (CLI):", "MYOB").strip()
with col_in2:
    msg_limit = st.number_input("Global Feed Limit:", min_value=1, max_value=2000, value=1000)

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
                # FILTER EXCLUSION: ADAHI name ki CLI wale records shuru me hi filter out kar diye
                df = df[~df['cli'].str.contains('ADAHI', case=False, na=False)].copy()
                
            if not df.empty:
                df['dt'] = pd.to_datetime(df['dt'])
                now = datetime.now()
                
                # Shift calculation (starting 5 AM)
                if now.hour < 5: 
                    start_day = (now - timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)
                else: 
                    start_day = now.replace(hour=5, minute=0, second=0, microsecond=0)

                # Filter Target CLI
                df_target_all = df[df['cli'].str.contains(target_cli, case=False, na=False)].copy()
                
                # Analytics
                c5 = len(df_target_all[df_target_all['dt'] >= (now - timedelta(minutes=5))])
                c10 = len(df_target_all[df_target_all['dt'] >= (now - timedelta(minutes=10))])
                c30 = len(df_target_all[df_target_all['dt'] >= (now - timedelta(minutes=30))])
                c_today = len(df_target_all[df_target_all['dt'] >= start_day])

                with placeholder.container():
                    # Analytics Table
                    st.markdown(f"""
                    <div class="report-box">
                        <div class="analytics-header-row">
                            <div class="header-item">5m</div><div class="header-item">10m</div>
                            <div class="header-item">30m</div><div class="header-item" style="border-right:none;">Today</div>
                        </div>
                        <div class="analytics-data-row">
                            <div class="data-item">{c5}</div><div class="data-item">{c10}</div>
                            <div class="data-item">{c30}</div><div class="data-item" style="border-right:none; color:#28a745;">{c_today}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # 1. Target Monitoring Table
                    st.markdown(f'<div class="section-label">🎯 {target_cli.upper()} MONITORING</div>', unsafe_allow_html=True)
                    if not df_target_all.empty:
                        mid_df = df_target_all.head(25).copy()
                        # Apply team info logic with exclusion
                        mid_df[['Team Member', 'Range']] = mid_df['num'].apply(lambda x: pd.Series(get_team_info(x, team_data)))
                        mid_df['Country'] = mid_df['num'].apply(get_country)
                        
                        disp_mid = mid_df[['dt', 'cli', 'num', 'Country', 'message', 'Team Member', 'Range']]
                        disp_mid.columns = ['Time', 'App', 'Number', 'Country', 'Message', 'Team Member', 'Range']
                        
                        st.dataframe(disp_mid.style.apply(highlight_team, axis=1), 
                                     use_container_width=True, height=350, hide_index=True, column_config=col_cfg)

                    # 2. Global Feed Table
                    st.markdown('<div class="section-label">🌐 GLOBAL NETWORK FEED</div>', unsafe_allow_html=True)
                    global_df = df.head(msg_limit).copy()
                    global_df[['Team Member', 'Range']] = global_df['num'].apply(lambda x: pd.Series(get_team_info(x, team_data)))
                    global_df['Country'] = global_df['num'].apply(get_country)
                    
                    disp_global = global_df[['dt', 'cli', 'num', 'Country', 'message', 'Team Member', 'Range']]
                    disp_global.columns = ['Time', 'App', 'Number', 'Country', 'Message', 'Team Member', 'Range']
                    
                    st.dataframe(disp_global.style.apply(highlight_team, axis=1), 
                                 use_container_width=True, height=800, hide_index=True, column_config=col_cfg)

        time.sleep(15)
        st.rerun()
    except Exception as e:
        time.sleep(5)
