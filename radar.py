import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import phonenumbers
from phonenumbers import geocoder
import threading
import json

# --- CONFIG (NEW URL UPDATED HERE) ---
URL = "http://51.77.216.195/crapi/lamix/viewstats"
TOKEN = "e1KDh36NdVxcaFNmc4uBYGSXiXmFiItnZI2QQ4d0YVY="
TEAM_FILE = "Numbers_Export.csv"
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyTHahQPjxjbuZGcIWiN2AgY8lHJEDm7Pyi2QnpSJVV436Q65DOlOtmA2Ilux8UkVgl/exec"

st.set_page_config(page_title="HUNTING SYSTEM - UMER ALI", layout="wide")

# --- UI DESIGN ---
st.markdown("""
<style>
    .stApp { background-color: #0a0a0c; color: #00ff66; font-family: 'Courier New', Courier, monospace; }
    .main-title { text-align: center; color: #00ff66; font-size: 42px; font-weight: 900; padding-top: 15px; margin-bottom: 5px; text-shadow: 0 0 15px #00ff66; }
    .main-subtitle { text-align: center; color: #888888; font-size: 12px; margin-bottom: 35px; letter-spacing: 4px; text-transform: uppercase; }
    .section-label { color: #ffffff; font-size: 18px; font-weight: bold; margin-top: 40px; margin-bottom: 15px; border-bottom: 2px solid #333333; padding-bottom: 8px; }
    .section-label::before { content: "■ "; color: #00ff66; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input { background-color: #121214 !important; color: #00ff66 !important; border: 1px solid #00ff66 !important; border-radius: 4px !important; }
    label { color: #ffffff !important; }
</style>
""", unsafe_allow_html=True)

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
    except: return {}

def get_team_info(num, team_data):
    n_str = str(num).split('.')[0].strip()
    if n_str in team_data:
        name = team_data[n_str]['MemberName']
        if name in ["UTS_Umer1", "UTS_Khadija"]: return "", ""
        return name, team_data[n_str]['Range']
    return "", ""

def highlight_team(row):
    if row['Team Member'] != "":
        return ['background-color: rgba(255, 0, 85, 0.12); color: #ff3366; font-weight: bold; border-right: 4px solid #ff0055;'] * len(row)
    return [''] * len(row)

# --- BACKEND SHEET STREAMER ---
def stream_to_google_sheet(raw_data):
    try:
        bg_df = pd.DataFrame(raw_data)
        if bg_df.empty: return
        bg_df['dt'] = pd.to_datetime(bg_df['dt']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Live records ko row-by-row Google Sheet me post karega
        for _, row in bg_df.head(20).iterrows(): 
            payload = {
                "Time": row['dt'],
                "App": row['cli'],
                "Number": str(row['num']),
                "Country": get_country(row['num']),
                "Message": str(row['message'])
            }
            requests.post(GOOGLE_SCRIPT_URL, data=json.dumps(payload), headers={'Content-Type': 'application/json'}, timeout=5)
    except:
        pass

# --- UI CONTROLS ---
st.markdown('<div class="main-title">⚡ DOUBLE FACER HUNTER ⚡</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">> DATABASE INTEGRATED CONTROL PANEL</div>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📡 LIVE MONITORING FEED", "📊 GOOGLE SHEET DATABASE FILTERS"])

with tab1:
    col_in1, col_in2 = st.columns([2, 1])
    with col_in1: target_cli = st.text_input("⚙️ ENTER TARGET AGENT (CLI):", "MYOB").strip()
    with col_in2: msg_limit = st.number_input("📡 STREAM BUFFER LIMIT:", min_value=1, max_value=2000, value=1000)
    placeholder = st.empty()

with tab2:
    st.markdown('<div class="section-label">REAL-TIME FILTERS (FETCHED DIRECT FROM GOOGLE SHEET)</div>', unsafe_allow_html=True)
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1: filter_cli = st.text_input("🔍 Search by App/CLI:", "").strip()
    with col_f2: filter_num = st.text_input("📞 Search by Phone Number:", "").strip()
    with col_f3: filter_msg = st.text_input("💬 Search by Message Content:", "").strip()
    history_placeholder = st.empty()

team_data = load_team_data()
col_cfg = {
    "Time": st.column_config.TextColumn("TIMESTAMP", width="medium"),
    "App": st.column_config.TextColumn("IDENT/CLI", width="small"),
    "Number": st.column_config.TextColumn("DATA_STREAM", width="medium"),
    "Country": st.column_config.TextColumn("LOCATION", width="small"),
    "Message": st.column_config.TextColumn("DECRYPTED_MSG", width="max"),
    "Team Member": st.column_config.TextColumn("OPERATOR", width="medium"),
    "Range": st.column_config.TextColumn("NETWORK_RANGE", width="large"),
}

# --- MAIN RUNNING LOOP ---
while True:
    try:
        r = requests.get(URL, params={"token": TOKEN, "records": 100}, timeout=10)
        if r.status_code == 200:
            raw_json = r.json().get("data", [])
            df = pd.DataFrame(raw_json)
            
            if not df.empty:
                threading.Thread(target=stream_to_google_sheet, args=(raw_json,), daemon=True).start()
                
                df['dt'] = pd.to_datetime(df['dt'])
                df_target_all = df[df['cli'].str.contains(target_cli, case=False, na=False)].copy()

                with placeholder.container():
                    st.markdown('<div class="section-label">LIVE TARGET TRACKER</div>', unsafe_allow_html=True)
                    if not df_target_all.empty:
                        mid_df = df_target_all.head(25).copy()
                        mid_df[['Team Member', 'Range']] = mid_df['num'].apply(lambda x: pd.Series(get_team_info(x, team_data)))
                        mid_df['Country'] = mid_df['num'].apply(get_country)
                        disp_mid = mid_df[['dt', 'cli', 'num', 'Country', 'message', 'Team Member', 'Range']]
                        disp_mid.columns = ['Time', 'App', 'Number', 'Country', 'Message', 'Team Member', 'Range']
                        st.dataframe(disp_mid.style.apply(highlight_team, axis=1), use_container_width=True, height=300, hide_index=True, column_config=col_cfg)

                    st.markdown('<div class="section-label">GLOBAL LIVE NETWORK STREAM</div>', unsafe_allow_html=True)
                    global_df = df.head(msg_limit).copy()
                    global_df[['Team Member', 'Range']] = global_df['num'].apply(lambda x: pd.Series(get_team_info(x, team_data)))
                    global_df['Country'] = global_df['num'].apply(get_country)
                    disp_global = global_df[['dt', 'cli', 'num', 'Country', 'message', 'Team Member', 'Range']]
                    disp_global.columns = ['Time', 'App', 'Number', 'Country', 'Message', 'Team Member', 'Range']
                    st.dataframe(disp_global.style.apply(highlight_team, axis=1), use_container_width=True, height=500, hide_index=True, column_config=col_cfg)

        # --- TAB 2 DIRECT GOOGLE SHEET LIVE FETCH ---
        sheet_r = requests.get(GOOGLE_SCRIPT_URL, timeout=10)
        if sheet_r.status_code == 200:
            sheet_data = sheet_r.json()
            if sheet_data:
                saved_df = pd.DataFrame(sheet_data)
                
                if filter_cli: saved_df = saved_df[saved_df['App'].astype(str).str.contains(filter_cli, case=False, na=False)]
                if filter_num: saved_df = saved_df[saved_df['Number'].astype(str).str.contains(filter_num, na=False)]
                if filter_msg: saved_df = saved_df[saved_df['Message'].astype(str).str.contains(filter_msg, case=False, na=False)]
                
                with history_placeholder.container():
                    st.markdown(f"Total Permanent Records in Google Sheet: `{len(saved_df)}`")
                    if not saved_df.empty:
                        saved_df[['Team Member', 'Range']] = saved_df['Number'].apply(lambda x: pd.Series(get_team_info(x, team_data)))
                        st.dataframe(saved_df.style.apply(highlight_team, axis=1), use_container_width=True, height=600, hide_index=True, column_config=col_cfg)

        time.sleep(15)
        st.rerun()
    except Exception as e:
        time.sleep(5)
