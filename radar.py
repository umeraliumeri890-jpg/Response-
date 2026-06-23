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

# Aapka Google Apps Script Web App URL
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwxNEVq19lF-qGzMwiuBlyKHJSLQg1JDbnu5IIwAdPZFsa-LAiNlVoDd5IOxNC2XLUa/exec"

# Page Config
st.set_page_config(page_title="HUNTING SYSTEM - UMER ALI", layout="wide")

# --- UI DESIGN (CYBERPUNK TERMINAL THEME) ---
st.markdown("""
<style>
    .stApp { 
        background-color: #0a0a0c;
        color: #00ff66; 
        font-family: 'Courier New', Courier, monospace;
    }
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
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        background-color: #121214 !important;
        color: #00ff66 !important;
        border: 1px solid #00ff66 !important;
        border-radius: 4px !important;
    }
    label { color: #ffffff !important; }
    .leaderboard-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px; }
    .rank-card { background: linear-gradient(135deg, #121214, #1a1a1e); border: 1px solid #222222; border-radius: 4px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.6); }
    .rank-1 { border-left: 5px solid #ffcc00; }
    .rank-2 { border-left: 5px solid #cccccc; }
    .rank-3 { border-left: 5px solid #cd7f32; }
    .rank-badge { font-size: 11px; font-weight: bold; margin-bottom: 8px; }
    .rank-1 .rank-badge { color: #ffcc00; }
    .rank-2 .rank-badge { color: #cccccc; }
    .rank-3 .rank-badge { color: #cd7f32; }
    .rank-cli { color: #ffffff; font-size: 28px; font-weight: 900; text-transform: uppercase; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .rank-count { color: #00ff66; font-size: 14px; font-weight: bold; }
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
                # CRITICAL FIX: Convert datetime instantly before saving or merging!
                df['dt'] = pd.to_datetime(df['dt'])
                now = datetime.now()
                
                # --- AUTO-SAVE AND DUPLICATE CHECK LOGIC ---
                if not os.path.isfile(SAVED_DATA_FILE):
                    df.to_csv(SAVED_DATA_FILE, index=False)
                    new_entries = df.copy()
                else:
                    existing_df = pd.read_csv(SAVED_DATA_FILE)
                    existing_df['dt'] = pd.to_datetime(existing_df['dt'])
                    
                    merged = df.merge(existing_df, on=['dt', 'num', 'message'], how='left', indicator=True)
                    new_entries = df[merged['_merge'] == 'left_only'].copy()
                    
                    combined_df = pd.concat([existing_df, df], ignore_index=True)
                    combined_df.drop_duplicates(subset=['dt', 'num', 'message'], keep='first', inplace=True)
                    combined_df.to_csv(SAVED_DATA_FILE, index=False)

                # --- GOOGLE SHEET EXPORT ---
                if not new_entries.empty:
                    try:
                        new_entries['country'] = new_entries['num'].apply(get_country)
                        export_df = new_entries.copy()
                        export_df['dt'] = export_df['dt'].dt.strftime('%Y-%m-%d %H:%M:%S')
                        payload = export_df[['dt', 'cli', 'num', 'country', 'message']].to_dict(orient='records')
                        requests.post(GOOGLE_SCRIPT_URL, json=payload, timeout=3)
                    except:
                        pass
                
                # --- TOP 3 APP/CLI CALCULATION ---
                five_mins_ago = now - timedelta(minutes=5)
                df_5m = df[df['dt'] >= five_mins_ago]
                
                top1_name, top1_count = "NO_DATA", 0
                top2_name, top2_count = "NO_DATA", 0
                top3_name, top3_count = "NO_DATA", 0
                
                if not df_5m.empty and 'cli' in df_5m.columns:
                    top_clis = df_5m['cli'].value_counts().head(3)
                    if len(top_clis) >= 1: top1_name, top1_count = top_clis.index[0], top_clis.iloc[0]
                    if len(top_clis) >= 2: top2_name, top2_count = top_clis.index[1], top_clis.iloc[1]
                    if len(top_clis) >= 3: top3_name, top3_count = top_clis.index[2], top_clis.iloc[2]

                df_target_all = df[df['cli'].str.contains(target_cli, case=False, na=False)].copy()

                # --- TAB 1 RENDERING ---
                with placeholder.container():
                    st.markdown(f"""
                    <div class="leaderboard-grid">
                        <div class="rank-card rank-1"><div class="rank-badge">🏆 TOP 1 (LAST 5M)</div><div class="rank-cli">{top1_name}</div><div class="rank-count">🔥 {top1_count} OTPs</div></div>
                        <div class="rank-card rank-2"><div class="rank-badge">🥈 TOP 2 (LAST 5M)</div><div class="rank-cli">{top2_name}</div><div class="rank-count">⚡ {top2_count} OTPs</div></div>
                        <div class="rank-card rank-3"><div class="rank-badge">🥉 TOP 3 (LAST 5M)</div><div class="rank-cli">{top3_name}</div><div class="rank-count">📡 {top3_count} OTPs</div></div>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown(f'<div class="section-label">LIVE TARGET TRACKER // ACCESSED: {target_cli.upper()}</div>', unsafe_allow_html=True)
                    if not df_target_all.empty:
                        mid_df = df_target_all.head(25).copy()
                        mid_df[['Team Member', 'Range']] = mid_df['num'].apply(lambda x: pd.Series(get_team_info(x, team_data)))
                        mid_df['Country'] = mid_df['num'].apply(get_country)
                        disp_mid = mid_df[['dt', 'cli', 'num', 'Country', 'message', 'Team Member', 'Range']]
                        disp_mid.columns = ['Time', 'App', 'Number', 'Country', 'Message', 'Team Member', 'Range']
                        st.dataframe(disp_mid.style.apply(highlight_team, axis=1), use_container_width=True, height=350, hide_index=True, column_config=col_cfg)
                    else:
                        st.caption("NO PACKETS DETECTED FOR CURRENT AGENT.")

                    st.markdown('<div class="section-label">GLOBAL NETWORK LOG STREAM</div>', unsafe_allow_html=True)
                    global_df = df.head(msg_limit).copy()
                    global_df[['Team Member', 'Range']] = global_df['num'].apply(lambda x: pd.Series(get_team_info(x, team_data)))
                    global_df['Country'] = global_df['num'].apply(get_country)
                    disp_global = global_df[['dt', 'cli', 'num', 'Country', 'message', 'Team Member', 'Range']]
                    disp_global.columns = ['Time', 'App', 'Number', 'Country', 'Message', 'Team Member', 'Range']
                    st.dataframe(disp_global.style.apply(highlight_team, axis=1), use_container_width=True, height=750, hide_index=True, column_config=col_cfg)

        # --- TAB 2 RENDERING ---
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
                    st.dataframe(final_history.style.apply(highlight_team, axis=1), use_container_width=True, height=600, hide_index=True, column_config=col_cfg)
                else:
                    st.warning("No historical matched data found.")

        time.sleep(15)
        st.rerun()
    except Exception as e:
        time.sleep(5)
