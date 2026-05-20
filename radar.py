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

    /* Dynamic Leaderboard Cards */
    .leaderboard-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 20px;
        margin-bottom: 30px;
    }
    .rank-card {
        background: linear-gradient(135deg, #121214, #1a1a1e);
        border: 1px solid #222222;
        border-radius: 4px;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.6);
        position: relative;
        overflow: hidden;
    }
    /* Distinct left glow colors for ranks */
    .rank-1 { border-left: 5px solid #ffcc00; box-shadow: 0 0 10px rgba(255,204,0,0.1); }
    .rank-2 { border-left: 5px solid #cccccc; }
    .rank-3 { border-left: 5px solid #cd7f32; }
    
    .rank-badge {
        font-size: 11px;
        font-weight: bold;
        letter-spacing: 2px;
        margin-bottom: 8px;
    }
    .rank-1 .rank-badge { color: #ffcc00; }
    .rank-2 .rank-badge { color: #cccccc; }
    .rank-3 .rank-badge { color: #cd7f32; }

    .rank-cli {
        color: #ffffff;
        font-size: 28px;
        font-weight: 900;
        letter-spacing: 1px;
        margin-bottom: 5px;
        text-transform: uppercase;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .rank-count {
        color: #00ff66;
        font-size: 14px;
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
        if name in ["UTS_Umer1", "UTS_Khadija"]:
            return "", ""
        return name, team_data[n_str]['Range']
    return "", ""

def highlight_team(row):
    """Highlights rows with a Toxic Cyber Red/Neon Pink theme for alerts."""
    if row['Team Member'] != "":
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
                
                # --- FILTER: EXCLUDE SPECIFIC CLI (15412293970) ---
                # Is line se "15412293970" naam ki CLI ka poora data gayab ho jayega
                df = df[~df['cli'].astype(str).str.contains("15412293970", case=False, na=False)].copy()
                
                now = datetime.now()
                
                # --- TOP 3 APP/CLI CALCULATION (LAST 5 MINS) ---
                five_mins_ago = now - timedelta(minutes=5)
                df_5m = df[df['dt'] >= five_mins_ago]
                
                # Default empty placeholders
                top1_name, top1_count = "NO_DATA", 0
                top2_name, top2_count = "NO_DATA", 0
                top3_name, top3_count = "NO_DATA", 0
                
                if not df_5m.empty and 'cli' in df_5m.columns:
                    top_clis = df_5m['cli'].value_counts().head(3)
                    
                    if len(top_clis) >= 1:
                        top1_name, top1_count = top_clis.index[0], top_clis.iloc[0]
                    if len(top_clis) >= 2:
                        top2_name, top2_count = top_clis.index[1], top_clis.iloc[1]
                    if len(top_clis) >= 3:
                        top3_name, top3_count = top_clis.index[2], top_clis.iloc[2]

                # Filter Target CLI for tables
                df_target_all = df[df['cli'].str.contains(target_cli, case=False, na=False)].copy()

                with placeholder.container():
                    # --- NEW TOP 3 LEADERBOARD GRID UI ---
                    st.markdown(f"""
                    <div class="leaderboard-grid">
                        <div class="rank-card rank-1">
                            <div class="rank-badge">🏆 TOP 1 (LAST 5M)</div>
                            <div class="rank-cli">{top1_name}</div>
                            <div class="rank-count">🔥 {top1_count} OTPs</div>
                        </div>
                        <div class="rank-card rank-2">
                            <div class="rank-badge">🥈 TOP 2 (LAST 5M)</div>
                            <div class="rank-cli">{top2_name}</div>
                            <div class="rank-count">⚡ {top2_count} OTPs</div>
                        </div>
                        <div class="rank-card rank-3">
                            <div class="rank-badge">🥉 TOP 3 (LAST 5M)</div>
                            <div class="rank-cli">{top3_name}</div>
                            <div class="rank-count">📡 {top3_count} OTPs</div>
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
