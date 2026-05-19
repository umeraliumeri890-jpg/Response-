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

# --- UI DESIGN (PROFESSIONAL DARK & NEON INTERFACE) ---
st.markdown("""
<style>
    /* Global Background and Typography */
    .stApp { 
        background: radial-gradient(circle at top left, #0d1117, #161b22);
        color: #c9d1d9; 
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Main Dashboard Header */
    .main-title { 
        text-align: center; 
        color: #ffffff; 
        font-size: 38px; 
        font-weight: 800;
        padding: 20px 0px 5px 0px;
        letter-spacing: 1.5px;
        text-shadow: 0 0 20px rgba(0, 115, 235, 0.4);
    }
    .main-subtitle {
        text-align: center;
        color: #8b949e;
        font-size: 14px;
        margin-bottom: 30px;
        text-transform: uppercase;
        letter-spacing: 2px;
    }

    /* Section Headings */
    .section-label { 
        color: #ffffff; 
        font-size: 20px; 
        font-weight: 700; 
        margin-top: 35px;
        margin-bottom: 15px; 
        border-left: 4px solid #58a6ff; 
        padding-left: 12px;
        letter-spacing: 0.5px;
    }

    /* Streamlit Components Overrides (Inputs) */
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        background-color: #21262d !important;
        color: #ffffff !important;
        border: 1px solid #30363d !important;
        border-radius: 6px !important;
        font-weight: 600;
    }
    .stTextInput>div>div>input:focus, .stNumberInput>div>div>input:focus {
        border-color: #58a6ff !important;
        box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.2) !important;
    }
    label {
        color: #8b949e !important;
        font-weight: 600 !important;
    }

    /* Professional Analytics Container */
    .analytics-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 20px;
        margin-bottom: 25px;
    }
    .card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 15px 20px;
        text-align: left;
        transition: transform 0.2s, border-color 0.2s;
    }
    .card:hover {
        border-color: #484f58;
    }
    .card-label {
        color: #8b949e;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 5px;
    }
    .card-value {
        color: #ffffff;
        font-size: 28px;
        font-weight: 700;
    }
    .card-value.highlight {
        color: #2ea043; /* Green highlight for 'Today' count */
        text-shadow: 0 0 10px rgba(46, 160, 67, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def get_country(num):
    try:
        full_num = "+" + str(num).strip()
        parsed = phonenumbers.parse(full_num)
        return geocoder.description_for_number(parsed, "en")
    except: 
        return "Global"

@st.cache_data
def load_team_data():
    try:
        df = pd.read_csv(TEAM_FILE)
        df['Phone Number'] = df['Phone Number'].astype(str).str.split('.').str[0].str.strip()
        df['Status'] = df['Status'].fillna('') 
        df['MemberName'] = df['Status'].str.replace('Allocated: ', '', case=False, regex=False).str.strip()
        return df.set_index('Phone Number')[['Range', 'MemberName']].to_dict('index')
    except Exception: 
        return {}

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
    """Highlights rows with an elegant amber accent color if a team member matches."""
    if row['Team Member'] != "":
        # Professional Dark Amber Overlay
        return ['background-color: rgba(210, 153, 34, 0.15); color: #ffcb47; font-weight: bold; border-left: 3px solid #d29922;'] * len(row)
    return [''] * len(row)

# --- HEADER ---
st.markdown('<div class="main-title">🎯 DOUBLE FACER HUNTER</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">Real-time Advanced Telecom Monitoring Control Center</div>', unsafe_allow_html=True)

# Control Panel Inputs
with st.container():
    col_in1, col_in2 = st.columns([2, 1])
    with col_in1:
        target_cli = st.text_input("📊 Search Target App (CLI):", "MYOB").strip()
    with col_in2:
        msg_limit = st.number_input("🌐 Global Feed Limit:", min_value=1, max_value=2000, value=1000)

team_data = load_team_data()
placeholder = st.empty()

# Table Configuration Matrix
col_cfg = {
    "Time": st.column_config.TextColumn("⏰ Time", width="medium"),
    "App": st.column_config.TextColumn("📱 App/CLI", width="small"),
    "Number": st.column_config.TextColumn("📞 Phone Number", width="medium"),
    "Country": st.column_config.TextColumn("🌍 Country", width="small"),
    "Message": st.column_config.TextColumn("💬 Message Log", width="max"),
    "Team Member": st.column_config.TextColumn("👤 Team Member", width="medium"),
    "Range": st.column_config.TextColumn("📡 Range Area", width="large"),
}

# --- MAIN REAL-TIME LOOP ---
while True:
    try:
        r = requests.get(URL, params={"token": TOKEN, "records": 5000})
        if r.status_code == 200:
            data = r.json().get("data", [])
            df = pd.DataFrame(data)
            
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
                
                # Analytics Parsing
                c5 = len(df_target_all[df_target_all['dt'] >= (now - timedelta(minutes=5))])
                c10 = len(df_target_all[df_target_all['dt'] >= (now - timedelta(minutes=10))])
                c30 = len(df_target_all[df_target_all['dt'] >= (now - timedelta(minutes=30))])
                c_today = len(df_target_all[df_target_all['dt'] >= start_day])

                with placeholder.container():
                    # HTML Grid-based Metric Cards (Modern look instead of old style tables)
                    st.markdown(f"""
                    <div class="analytics-container">
                        <div class="card">
                            <div class="card-label">Traffic (Last 5 Mins)</div>
                            <div class="card-value">{c5}</div>
                        </div>
                        <div class="card">
                            <div class="card-label">Traffic (Last 10 Mins)</div>
                            <div class="card-value">{c10}</div>
                        </div>
                        <div class="card">
                            <div class="card-label">Traffic (Last 30 Mins)</div>
                            <div class="card-value">{c30}</div>
                        </div>
                        <div class="card">
                            <div class="card-label">Total Today Shift</div>
                            <div class="card-value highlight">{c_today}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # 1. Target Monitoring Table
                    st.markdown(f'<div class="section-label">🎯 TARGET DETECTOR: {target_cli.upper()}</div>', unsafe_allow_html=True)
                    if not df_target_all.empty:
                        mid_df = df_target_all.head(25).copy()
                        
                        # Data processing
                        mid_df[['Team Member', 'Range']] = mid_df['num'].apply(lambda x: pd.Series(get_team_info(x, team_data)))
                        mid_df['Country'] = mid_df['num'].apply(get_country)
                        
                        disp_mid = mid_df[['dt', 'cli', 'num', 'Country', 'message', 'Team Member', 'Range']]
                        disp_mid.columns = ['Time', 'App', 'Number', 'Country', 'Message', 'Team Member', 'Range']
                        
                        # Rendering DataFrame
                        st.dataframe(
                            disp_mid.style.apply(highlight_team, axis=1), 
                            use_container_width=True, 
                            height=350, 
                            hide_index=True, 
                            column_config=col_cfg
                        )
                    else:
                        st.info("No active logs matching target CLI found right now.")

                    # 2. Global Feed Table
                    st.markdown('<div class="section-label">🌐 GLOBAL NETWORK INTERCEPT FEED</div>', unsafe_allow_html=True)
                    global_df = df.head(msg_limit).copy()
                    
                    # Data processing
                    global_df[['Team Member', 'Range']] = global_df['num'].apply(lambda x: pd.Series(get_team_info(x, team_data)))
                    global_df['Country'] = global_df['num'].apply(get_country)
                    
                    disp_global = global_df[['dt', 'cli', 'num', 'Country', 'message', 'Team Member', 'Range']]
                    disp_global.columns = ['Time', 'App', 'Number', 'Country', 'Message', 'Team Member', 'Range']
                    
                    # Rendering DataFrame
                    st.dataframe(
                        disp_global.style.apply(highlight_team, axis=1), 
                        use_container_width=True, 
                        height=700, 
                        hide_index=True, 
                        column_config=col_cfg
                    )

        time.sleep(15)
        st.rerun()
    except Exception as e:
        time.sleep(5)
