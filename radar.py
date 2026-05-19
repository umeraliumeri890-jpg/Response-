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
st.set_page_config(page_title="HUNTING SYSTEM - UMER ALI", layout="wide")

# --- UI DESIGN (CYBERPUNK TERMINAL THEME) ---
st.markdown("""
<style>
    /* Main Background & Font */
    .stApp { 
        background-color: #0a0a0c;
        color: #00ff66; 
        font-family: 'Courier New', Courier, monospace;
    }
    
    /* Cyber Title */
    .main-title { 
        text-align: center; 
        color: #00ff66; 
        font-size: 42px; 
        font-weight: 900;
        padding-top: 15px;
        margin-bottom: 5px;
        letter-spacing: 3px;
        text-shadow: 0 0 15px #00ff66;
    }
    .main-subtitle {
        text-align: center;
        color: #888888;
        font-size: 12px;
        margin-bottom: 35px;
        letter-spacing: 4px;
        text-transform: uppercase;
    }

    /* Neo Sections */
    .section-label { 
        color: #ffffff; 
        font-size: 18px; 
        font-weight: bold; 
        margin-top: 40px;
        margin-bottom: 15px; 
        border-bottom: 2px solid #333333;
        padding-bottom: 8px;
        letter-spacing: 2px;
    }
    .section-label::before {
        content: "■ ";
        color: #00ff66;
    }

    /* Inputs Styling */
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        background-color: #121214 !important;
        color: #00ff66 !important;
        border: 1px solid #00ff66 !important;
        border-radius: 4px !important;
        font-family: 'Courier New', Courier, monospace;
        box-shadow: inset 0 0 5px rgba(0,255,102,0.1);
    }
    label {
        color: #ffffff !important;
        letter-spacing: 1px;
    }

    /* Terminal Analytics Cards */
    .terminal-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 15px;
        margin-bottom: 30px;
    }
    .t-card {
        background: linear-gradient(135deg, #121214, #1a1a1e);
        border: 1px solid #222222;
        border-left: 4px solid #333333;
        border-radius: 4px;
        padding: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.5);
    }
    .t-card.active-shift {
        border-left: 4px solid #00ff66;
        box-shadow: 0 0 10px rgba(0,255,102,0.05);
    }
    .t-label {
        color: #888888;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 8px;
    }
    .t-value {
        color: #ffffff;
        font-size: 32px;
        font-weight: bold;
    }
    .t-value.neon {
        color: #00ff66;
        text-shadow: 0 0 10px rgba(0,255,102,0.3);
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
        # EXCLUSION LOGIC
        if name in ["UTS_Umer1", "UTS_Khadija"]:
            return "", ""
        return name, team_data[n_str]['Range']
    return "", ""

def highlight_team(row):
    """Highlights rows with a Toxic Cyber Red/Neon Pink theme for alerts."""
    if row['Team Member'] != "":
        # Matrix Red Highlight for Target Detection
        return ['background-color: rgba(255, 0, 85, 0.12); color: #ff3366; font-weight: bold; border-right: 4px solid #ff0055;'] * len(row)
    return [''] * len(row)

# --- HEADER ---
st.markdown('<div class="main-title">⚡ DOUBLE FACER HUNTER ⚡</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">> SYSTEM CONTROL PANEL // NETWORK SNIFFER</div>', unsafe_allow_html=True)

# Inputs Panel
col_in1, col_in2 = st.columns([2, 1])
with col_in1:
    target_cli = st.text_input("⚙️ ENTER TARGET AGENT (CLI):", "MYOB").strip()
with col_in2:
    msg_limit = st.number_input("📡 STREAM BUFFER LIMIT:", min_value=1, max_value=2000, value=1000)

team_data = load_team_data()
placeholder = st.empty()

# Cyber Columns Settings
col_cfg = {
    "Time": st.column_config.TextColumn("TIMESTAMP", width="medium"),
    "App": st.column_config.TextColumn("IDENT/CLI", width="small"),
    "Number": st.column_config.TextColumn("DATA_STREAM", width="medium"),
    "Country": st.column_config.TextColumn("LOCATION", width="small"),
    "Message": st.column_config.TextColumn("DECRYPTED_MSG", width="max"),
    "Team Member": st.column_config.TextColumn("OPERATOR", width="medium"),
    "Range": st.column_config.TextColumn("NETWORK_RANGE", width="large"),
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
                
                # Shift calculation
                if now.hour < 5: 
                    start_day = (now - timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)
                else: 
                    start_day = now.replace(hour=5, minute=0, second=0, microsecond=0)

                # Filter Target CLI
                df_target_all = df[df['cli'].str.contains(target_cli, case=False, na=False)].copy()
                
                # Analytics Metrics
                c5 = len(df_target_all[df_target_all['dt'] >= (now - timedelta(minutes=5))])
                c10 = len(df_target_all[df_target_all['dt'] >= (now - timedelta(minutes=10))])
                c30 = len(df_target_all[df_target_all['dt'] >= (now - timedelta(minutes=30))])
                c_today = len(df_target_all[df_target_all['dt'] >= start_day])

                with placeholder.container():
                    # Terminal Style Cards Grid
                    st.markdown(f"""
                    <div class="terminal-grid">
                        <div class="t-card">
                            <div class="t-label">PING_5M</div>
                            <div class="t-value">{c5}</div>
                        </div>
                        <div class="t-card">
                            <div class="t-label">PING_10M</div>
                            <div class="t-value">{c10}</div>
                        </div>
                        <div class="t-card">
                            <div class="t-label">PING_30M</div>
                            <div class="t-value">{c30}</div>
                        </div>
                        <div class="t-card active-shift">
                            <div class="t-label">SHIFT_TOTAL</div>
                            <div class="t-value neon">{c_today}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # 1. Target Monitoring Table
                    st.markdown(f'<div class="section-label">LIVE TARGET TRACKER // ACCESSED: {target_cli.upper()}</div>', unsafe_allow_html=True)
                    if not df_target_all.empty:
                        mid_df = df_target_all.head(25).copy()
                        mid_df[['Team Member', 'Range']] = mid_df['num'].apply(lambda x: pd.Series(get_team_info(x, team_data)))
                        mid_df['Country'] = mid_df['num'].apply(get_country)
                        
                        disp_mid = mid_df[['dt', 'cli', 'num', 'Country', 'message', 'Team Member', 'Range']]
                        disp_mid.columns = ['Time', 'App', 'Number', 'Country', 'Message', 'Team Member', 'Range']
                        
                        st.dataframe(disp_mid.style.apply(highlight_team, axis=1), 
                                     use_container_width=True, height=350, hide_index=True, column_config=col_cfg)
                    else:
                        st.caption("NO PACKETS DETECTED FOR CURRENT AGENT.")

                    # 2. Global Feed Table
                    st.markdown('<div class="section-label">GLOBAL NETWORK LOG STREAM</div>', unsafe_allow_html=True)
                    global_df = df.head(msg_limit).copy()
                    global_df[['Team Member', 'Range']] = global_df['num'].apply(lambda x: pd.Series(get_team_info(x, team_data)))
                    global_df['Country'] = global_df['num'].apply(get_country)
                    
                    disp_global = global_df[['dt', 'cli', 'num', 'Country', 'message', 'Team Member', 'Range']]
                    disp_global.columns = ['Time', 'App', 'Number', 'Country', 'Message', 'Team Member', 'Range']
                    
                    st.dataframe(disp_global.style.apply(highlight_team, axis=1), 
                                 use_container_width=True, height=750, hide_index=True, column_config=col_cfg)

        time.sleep(15)
        st.rerun()
    except Exception as e:
        time.sleep(5)
