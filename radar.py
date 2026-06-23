import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import phonenumbers
from phonenumbers import geocoder
import os

# --- CONFIG ---
URL = "http://51.77.216.195/crapi/lamix/viewstats"
TOKEN = "e1KDh36NdVxcaFNmc4uBYGSXiXmFiItnZI2QQ4d0YVY="
TEAM_FILE = "Numbers_Export.csv"
SAVED_DATA_FILE = "all_captured_data.csv"

# Aapka Google Script URL
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwxNEVq19lF-qGzMwiuBlyKHJSLQg1JDbnu5IIwAdPZFsa-LAiNlVoDd5IOxNC2XLUa/exec"

# Page Config
st.set_page_config(page_title="HUNTING SYSTEM - UMER ALI", layout="wide")

# --- UI DESIGN ---
st.markdown("""
<style>
    .stApp { background-color: #0a0a0c; color: #00ff66; font-family: 'Courier New', Courier, monospace; }
    .main-title { text-align: center; color: #00ff66; font-size: 42px; font-weight: 900; padding-top: 15px; margin-bottom: 5px; text-shadow: 0 0 15px #00ff66; }
    .main-subtitle { text-align: center; color: #888888; font-size: 12px; margin-bottom: 35px; letter-spacing: 4px; text-transform: uppercase; }
    .section-label { color: #ffffff; font-size: 18px; font-weight: bold; margin-top: 40px; margin-bottom: 15px; border-bottom: 2px solid #333333; padding-bottom: 8px; }
    .section-label::before { content: "■ "; color: #00ff66; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input { background-color: #121214 !important; color: #00ff66 !important; border: 1px solid #00ff66 !important; }
    label { color: #ffffff !important; }
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

# --- HEADER ---
st.markdown('<div class="main-title">⚡ DOUBLE FACER HUNTER ⚡</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">> SYSTEM CONTROL PANEL // NETWORK SNIFFER</div>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📡 LIVE MONITORING FEED", "📊 SAVED LOGS ANALYTICS & FILTERS"])

with tab1:
    col_in1, col_in2 = st.columns([2, 1])
    with col_in1: target_cli = st.text_input("⚙️ ENTER TARGET AGENT (CLI):", "MYOB").strip()
    with col_in2: msg_limit = st.number_input("📡 STREAM BUFFER LIMIT:", min_value=1, max_value=2000, value=1000)
    placeholder = st.empty()

with tab2:
    st.markdown('<div class="section-label">SEARCH AND FILTER ENTIRE SAVED HISTORY</div>', unsafe_allow_html=True)
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1: filter_cli = st.text_input("🔍 Search by App/CLI (Saved Data):", "")
    with col_f2: filter_num = st.text_input("📞 Search by Phone Number (Saved Data):", "")
    with col_f3: filter_msg = st.text_input("💬 Search by Message Content:", "")
    
    download_btn_placeholder = st.empty()
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

# --- MAIN LOOP ---
while True:
    try:
        r = requests.get(URL, params={"token": TOKEN, "records": 5000}, timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", [])
            df = pd.DataFrame(data)
            
            if not df.empty:
                # Local app database backup logic
                if not os.path.isfile(SAVED_DATA_FILE):
                    df.to_csv(SAVED_DATA_FILE, index=False)
                    new_entries = df.copy()
                else:
                    existing_df = pd.read_csv(SAVED_DATA_FILE)
                    merged = df.merge(existing_df, on=['dt', 'num', 'message'], how='left', indicator=True)
                    new_entries = df[merged['_merge'] == 'left_only'].copy()
                    
                    combined_df = pd.concat([existing_df, df], ignore_index=True)
                    combined_df.drop_duplicates(subset=['dt', 'num', 'message'], keep='first', inplace=True)
                    combined_df.to_csv(SAVED_DATA_FILE, index=False)
                
                # CRITICAL FIX: Google Sheet request ko bilkul azad kar diya (Timeout 3 sec)
                # Agar Google API bura maan jaye ya slow ho, to dashboard crash ya lag nahi hoga
                if not new_entries.empty:
                    try:
                        new_entries['country'] = new_entries['num'].apply(get_country)
                        payload = new_entries[['dt', 'cli', 'num', 'country', 'message']].to_dict(orient='records')
                        requests.post(GOOGLE_SCRIPT_URL, json=payload, timeout=3)
                    except Exception as sheet_err:
                        pass # Google Sheet fail bhi ho to live data chalta rahega
                
                # --- LIVE RENDERING ---
                df['dt'] = pd.to_datetime(df['dt'])
                df_target_all = df[df['cli'].str.contains(target_cli, case=False, na=False)].copy()

                with placeholder.container():
                    st.markdown(f'<div class="section-label">LIVE TARGET TRACKER // ACCESSED: {target_cli.upper()}</div>', unsafe_allow_html=True)
                    if not df_target_all.empty:
                        mid_df = df_target_all.head(25).copy()
                        mid_df[['Team Member', 'Range']] = mid_df['num'].apply(lambda x: pd.Series(get_team_info(x, team_data)))
                        mid_df['Country'] = mid_df['num'].apply(get_country)
                        disp_mid = mid_df[['dt', 'cli', 'num', 'Country', 'message', 'Team Member', 'Range']]
                        disp_mid.columns = ['Time', 'App', 'Number', 'Country', 'Message', 'Team Member', 'Range']
                        styled_mid = disp_mid.style.apply(highlight_team, axis=1)
                        st.dataframe(styled_mid, use_container_width=True, height=350, hide_index=True, column_config=col_cfg)
                    else:
                        st.caption("NO PACKETS DETECTED FOR CURRENT AGENT.")

                    st.markdown('<div class="section-label">GLOBAL NETWORK LOG STREAM</div>', unsafe_allow_html=True)
                    global_df = df.head(msg_limit).copy()
                    global_df[['Team Member', 'Range']] = global_df['num'].apply(lambda x: pd.Series(get_team_info(x, team_data)))
                    global_df['Country'] = global_df['num'].apply(get_country)
                    disp_global = global_df[['dt', 'cli', 'num', 'Country', 'message', 'Team Member', 'Range']]
                    disp_global.columns = ['Time', 'App', 'Number', 'Country', 'Message', 'Team Member', 'Range']
                    styled_global = disp_global.style.apply(highlight_team, axis=1)
                    st.dataframe(styled_global, use_container_width=True, height=750, hide_index=True, column_config=col_cfg)

        # --- TAB 2 PROCESSING ---
        if os.path.exists(SAVED_DATA_FILE):
            saved_df = pd.read_csv(SAVED_DATA_FILE)
            
            with download_btn_placeholder.container():
                csv_data = saved_df.to_csv(index=False).encode('utf-8')
                st.download_button(label="📥 DOWNLOAD LOCAL CSV BACKUP", data=csv_data, file_name="hunting_backup.csv", mime="text/csv")
            
            if filter_cli: saved_df = saved_df[saved_df['cli'].str.contains(filter_cli, case=False, na=False)]
            if filter_num: saved_df = saved_df[saved_df['num'].astype(str).str.contains(filter_num, na=False)]
            if filter_msg: saved_df = saved_df[saved_df['message'].str.contains(filter_msg, case=False, na=False)]
            
            with history_placeholder.container():
                st.markdown(f"Total Unique Saved Records (In App Storage): `{len(saved_df)}`")
                if not saved_df.empty:
                    saved_df = saved_df.sort_values(by='dt', ascending=False)
                    history_disp = saved_df.head(200).copy()
                    history_disp[['Team Member', 'Range']] = history_disp['num'].apply(lambda x: pd.Series(get_team_info(x, team_data)))
                    history_disp['Country'] = history_disp['num'].apply(get_country)
                    final_history = history_disp[['dt', 'cli', 'num', 'Country', 'message', 'Team Member', 'Range']]
                    final_history.columns = ['Time', 'App', 'Number', 'Country', 'Message', 'Team Member', 'Range']
                    styled_history = final_history.style.apply(highlight_team, axis=1)
                    st.dataframe(styled_history, use_container_width=True, height=600, hide_index=True, column_config=col_cfg)
                else:
                    st.warning("No matched data found.")

        time.sleep(15)
        st.rerun()
    except Exception as e:
        time.sleep(5)
