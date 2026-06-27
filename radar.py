import streamlit as st
from auth import check_access
logged_in_user = check_access()

import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import phonenumbers
from phonenumbers import geocoder
import threading
import json

# --- CONFIG ---
URL = "http://51.77.216.195/crapi/lamix/viewstats"
TOKEN = "X46ZeF6ViotShZl5WYRse1t3lYiKZ3CAdo6ZdINSh0o="
TEAM_FILE = "Numbers_Export.csv"
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyTHahQPjxjbuZGcIWiN2AgY8lHJEDm7Pyi2QnpSJVV436Q65DOlOtmA2Ilux8UkVgl/exec"

st.set_page_config(
    page_title="DOUBLE FACER HUNTER — UMER ALI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&family=Inter:wght@300;400;500;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
  .stApp {
    background: #020408;
    background-image:
      radial-gradient(ellipse 80% 50% at 50% -10%, rgba(0,212,255,0.08) 0%, transparent 60%),
      radial-gradient(ellipse 60% 40% at 80% 80%, rgba(139,0,255,0.06) 0%, transparent 60%),
      linear-gradient(180deg, #020408 0%, #030810 100%);
    min-height: 100vh;
    color: #e2e8f0;
  }
  .stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: repeating-linear-gradient(
      0deg, transparent, transparent 2px,
      rgba(0,212,255,0.015) 2px, rgba(0,212,255,0.015) 4px
    );
    pointer-events: none;
    z-index: 0;
  }
  .main-header { text-align: center; padding: 40px 20px 30px; }
  .main-title {
    font-family: 'Orbitron', monospace;
    font-size: clamp(28px, 5vw, 52px);
    font-weight: 900;
    letter-spacing: 6px;
    background: linear-gradient(135deg, #00d4ff 0%, #7b2fff 50%, #ff006e 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    text-transform: uppercase;
    margin-bottom: 8px;
    filter: drop-shadow(0 0 30px rgba(0,212,255,0.4));
  }
  .main-subtitle {
    font-family: 'Share Tech Mono', monospace;
    color: #4a9eff;
    font-size: 13px;
    letter-spacing: 4px;
    text-transform: uppercase;
    opacity: 0.8;
  }
  .operator-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(0,212,255,0.08);
    border: 1px solid rgba(0,212,255,0.25);
    border-radius: 20px;
    padding: 5px 18px;
    font-family: 'Orbitron', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 3px;
    color: #00d4ff;
    text-transform: uppercase;
    margin-top: 12px;
  }
  .operator-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #00d4ff;
    box-shadow: 0 0 8px #00d4ff;
    animation: pulse-dot 2s ease-in-out infinite;
  }
  .header-line {
    width: 100%;
    height: 1px;
    background: linear-gradient(90deg, transparent, #00d4ff, #7b2fff, #ff006e, transparent);
    margin: 20px 0 0;
    box-shadow: 0 0 15px rgba(0,212,255,0.4);
  }
  .stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.03) !important;
    border-radius: 12px !important;
    padding: 6px !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    gap: 4px !important;
  }
  .stTabs [data-baseweb="tab"] {
    font-family: 'Orbitron', monospace !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    letter-spacing: 2px !important;
    color: #4a5568 !important;
    border-radius: 8px !important;
    padding: 10px 24px !important;
    transition: all 0.3s ease !important;
    border: none !important;
    background: transparent !important;
  }
  .stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(0,212,255,0.2), rgba(123,47,255,0.2)) !important;
    color: #00d4ff !important;
    border: 1px solid rgba(0,212,255,0.3) !important;
    box-shadow: 0 0 20px rgba(0,212,255,0.15) !important;
  }
  .stTabs [data-baseweb="tab-highlight"] { display: none !important; }
  .stTabs [data-baseweb="tab-border"] { display: none !important; }
  .lb-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 24px 0; }
  .lb-card {
    position: relative;
    background: rgba(255,255,255,0.03);
    border-radius: 16px;
    padding: 24px 20px;
    border: 1px solid rgba(255,255,255,0.06);
    overflow: hidden;
  }
  .lb-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; }
  .lb-card-1::before { background: linear-gradient(90deg, #ffd700, #ffaa00); box-shadow: 0 0 20px rgba(255,215,0,0.5); }
  .lb-card-2::before { background: linear-gradient(90deg, #c0c0c0, #a0a0a0); }
  .lb-card-3::before { background: linear-gradient(90deg, #cd7f32, #a0522d); }
  .lb-badge { font-family: 'Orbitron', monospace; font-size: 9px; font-weight: 700; letter-spacing: 3px; text-transform: uppercase; margin-bottom: 12px; display: flex; align-items: center; gap: 6px; }
  .lb-card-1 .lb-badge { color: #ffd700; }
  .lb-card-2 .lb-badge { color: #c0c0c0; }
  .lb-card-3 .lb-badge { color: #cd7f32; }
  .lb-dot { width: 6px; height: 6px; border-radius: 50%; animation: pulse-dot 1.5s ease-in-out infinite; }
  .lb-card-1 .lb-dot { background: #ffd700; box-shadow: 0 0 8px #ffd700; }
  .lb-card-2 .lb-dot { background: #c0c0c0; }
  .lb-card-3 .lb-dot { background: #cd7f32; }
  @keyframes pulse-dot { 0%,100%{transform:scale(1);opacity:1} 50%{transform:scale(1.5);opacity:0.7} }
  .lb-name { font-family: 'Orbitron', monospace; font-size: clamp(16px,2.5vw,26px); font-weight: 900; color: #f8fafc; text-transform: uppercase; letter-spacing: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-bottom: 8px; }
  .lb-count { font-family: 'Share Tech Mono', monospace; font-size: 14px; display: flex; align-items: center; gap: 8px; }
  .lb-card-1 .lb-count { color: #ffd700; }
  .lb-card-2 .lb-count { color: #c0c0c0; }
  .lb-card-3 .lb-count { color: #cd7f32; }
  .section-label {
    font-family: 'Orbitron', monospace;
    font-size: 11px; font-weight: 700; letter-spacing: 4px; text-transform: uppercase;
    color: #00d4ff; margin: 32px 0 16px; display: flex; align-items: center; gap: 12px;
  }
  .section-label::before { content: ''; display: block; width: 4px; height: 18px; background: linear-gradient(180deg, #00d4ff, #7b2fff); border-radius: 2px; box-shadow: 0 0 10px rgba(0,212,255,0.6); }
  .section-label::after { content: ''; flex: 1; height: 1px; background: linear-gradient(90deg, rgba(0,212,255,0.3), transparent); }
  .stTextInput > div > div > input, .stNumberInput > div > div > input {
    background: rgba(0,212,255,0.04) !important; border: 1px solid rgba(0,212,255,0.2) !important;
    border-radius: 10px !important; color: #e2e8f0 !important;
    font-family: 'Share Tech Mono', monospace !important; font-size: 14px !important; padding: 10px 16px !important;
  }
  .stTextInput > div > div > input:focus, .stNumberInput > div > div > input:focus {
    border-color: rgba(0,212,255,0.6) !important;
    box-shadow: 0 0 0 3px rgba(0,212,255,0.1) !important;
  }
  label { font-family: 'Orbitron', monospace !important; font-size: 10px !important; letter-spacing: 2px !important; color: #4a9eff !important; text-transform: uppercase !important; font-weight: 700 !important; }
  .stDataFrame { border-radius: 12px !important; overflow: hidden !important; border: 1px solid rgba(0,212,255,0.1) !important; }
  .status-box { background: rgba(255,255,255,0.02); border: 1px dashed rgba(0,212,255,0.15); border-radius: 16px; padding: 50px 30px; text-align: center; margin-top: 20px; }
  .status-box .icon { font-size: 40px; margin-bottom: 15px; opacity: 0.6; }
  .status-box .title { font-family: 'Orbitron', monospace; font-size: 13px; color: #4a9eff; letter-spacing: 4px; margin-bottom: 10px; }
  .status-box .desc { color: #2d3748; font-size: 13px; line-height: 1.8; font-family: 'Share Tech Mono', monospace; }
  .live-pill { display: inline-flex; align-items: center; gap: 6px; background: rgba(255,0,110,0.12); border: 1px solid rgba(255,0,110,0.3); border-radius: 20px; padding: 4px 14px; font-family: 'Orbitron', monospace; font-size: 9px; font-weight: 700; letter-spacing: 3px; color: #ff006e; text-transform: uppercase; margin-bottom: 16px; }
  .live-dot { width: 6px; height: 6px; border-radius: 50%; background: #ff006e; box-shadow: 0 0 8px #ff006e; animation: pulse-dot 1s ease-in-out infinite; }
  ::-webkit-scrollbar { width: 4px; height: 4px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: rgba(0,212,255,0.3); border-radius: 4px; }
  .block-container { padding: 0 2rem 2rem !important; max-width: 1400px !important; }
  @media (max-width: 768px) { .lb-grid { grid-template-columns: 1fr; } .main-title { font-size: 24px; } }
</style>
""", unsafe_allow_html=True)

# ============================================================
#  FUNCTIONS
# ============================================================
def get_country(num):
    try:
        parsed = phonenumbers.parse("+" + str(num).strip())
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
    except:
        return {}

def get_team_info(num, team_data):
    n_str = str(num).split('.')[0].strip()
    if n_str in team_data:
        name = team_data[n_str]['MemberName']
        if name in ["UTS_Umer1", "UTS_Khadija"]:
            return "", ""
        return name, team_data[n_str]['Range']
    return "", ""

def highlight_team(row):
    if row['Team Member'] != "":
        return ['background-color: rgba(255,0,110,0.1); color: #ff006e; font-weight: bold;'] * len(row)
    return [''] * len(row)

def stream_to_google_sheet(raw_data):
    try:
        bg_df = pd.DataFrame(raw_data)
        if bg_df.empty:
            return
        bg_df['dt'] = pd.to_datetime(bg_df['dt']).dt.strftime('%Y-%m-%d %H:%M:%S')
        for _, row in bg_df.head(20).iterrows():
            payload = {"Time": row['dt'], "App": row['cli'], "Number": str(row['num']),
                       "Country": get_country(row['num']), "Message": str(row['message'])}
            requests.post(GOOGLE_SCRIPT_URL, data=json.dumps(payload),
                          headers={'Content-Type': 'application/json'}, timeout=5)
    except:
        pass

# ============================================================
#  HEADER
# ============================================================
st.markdown(f"""
<div class="main-header">
  <div class="live-pill"><div class="live-dot"></div> LIVE SYSTEM</div>
  <div class="main-title">⚡ DOUBLE FACER HUNTER ⚡</div>
  <div class="main-subtitle">> DATABASE INTEGRATED CONTROL PANEL // UMER ALI</div>
  <div style="margin-top:12px;">
    <span class="operator-badge">
      <div class="operator-dot"></div>
      OPERATOR: {logged_in_user.upper()}
    </span>
  </div>
  <div class="header-line"></div>
</div>
""", unsafe_allow_html=True)

# ============================================================
#  SESSION STATE
# ============================================================
if 'last_fetch' not in st.session_state:
    st.session_state['last_fetch'] = None
if 'data_cache' not in st.session_state:
    st.session_state['data_cache'] = []

# ============================================================
#  TABS
# ============================================================
tab1, tab2 = st.tabs(["📡  LIVE MONITORING FEED", "📊  GOOGLE SHEET DATABASE FILTERS"])

with tab1:
    col_in1, col_in2 = st.columns([2, 1])
    with col_in1:
        target_cli = st.text_input("⚙️ ENTER TARGET AGENT (CLI):", "MYOB").strip()
    with col_in2:
        msg_limit = st.number_input("📡 STREAM BUFFER LIMIT:", min_value=1, max_value=2000, value=1000)
    placeholder = st.empty()

with tab2:
    st.markdown('<div class="section-label">INTELLIGENT DATABASE SEARCH</div>', unsafe_allow_html=True)
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filter_cli = st.text_input("🔍 Search by App/CLI:", "", key="f_cli").strip()
    with col_f2:
        filter_num = st.text_input("📞 Search by Phone Number:", "", key="f_num").strip()
    with col_f3:
        filter_msg = st.text_input("💬 Search by Message Content:", "", key="f_msg").strip()
    history_placeholder = st.empty()

team_data = load_team_data()

col_cfg = {
    "Time":        st.column_config.TextColumn("TIMESTAMP",     width="medium"),
    "App":         st.column_config.TextColumn("IDENT/CLI",     width="small"),
    "Number":      st.column_config.TextColumn("DATA_STREAM",   width="medium"),
    "Country":     st.column_config.TextColumn("LOCATION",      width="small"),
    "Message":     st.column_config.TextColumn("DECRYPTED_MSG", width="max"),
    "Team Member": st.column_config.TextColumn("OPERATOR",      width="medium"),
    "Range":       st.column_config.TextColumn("NETWORK_RANGE", width="large"),
}

# ============================================================
#  DATA FETCH — session cache se, 15 sec interval
# ============================================================
now = datetime.now()
fetch_needed = (
    st.session_state['last_fetch'] is None or
    (now - st.session_state['last_fetch']).total_seconds() >= 15
)

if fetch_needed:
    try:
        r = requests.get(URL, params={"token": TOKEN, "records": 100}, timeout=10)
        if r.status_code == 200:
            raw_json = r.json().get("data", [])
            st.session_state['data_cache'] = raw_json
            st.session_state['last_fetch'] = now
            if raw_json:
                threading.Thread(
                    target=stream_to_google_sheet,
                    args=(raw_json,), daemon=True
                ).start()
    except:
        pass

raw_json = st.session_state['data_cache']
df = pd.DataFrame(raw_json) if raw_json else pd.DataFrame()

# ============================================================
#  TAB 1 — LIVE FEED
# ============================================================
with placeholder.container():
    if not df.empty:
        df['dt'] = pd.to_datetime(df['dt'])
        five_mins_ago = now - timedelta(minutes=5)
        df_5m = df[df['dt'] >= five_mins_ago]

        top1_name, top1_count = "NO_DATA", 0
        top2_name, top2_count = "NO_DATA", 0
        top3_name, top3_count = "NO_DATA", 0

        if not df_5m.empty and 'cli' in df_5m.columns:
            top_clis = df_5m['cli'].value_counts().head(3)
            if len(top_clis) >= 1: top1_name, top1_count = top_clis.index[0], int(top_clis.iloc[0])
            if len(top_clis) >= 2: top2_name, top2_count = top_clis.index[1], int(top_clis.iloc[1])
            if len(top_clis) >= 3: top3_name, top3_count = top_clis.index[2], int(top_clis.iloc[2])

        st.markdown(f"""
        <div class="lb-grid">
          <div class="lb-card lb-card-1">
            <div class="lb-badge"><div class="lb-dot"></div> 🏆 TOP 1 · LAST 5MIN</div>
            <div class="lb-name">{top1_name}</div>
            <div class="lb-count">🔥 {top1_count:,} OTPs</div>
          </div>
          <div class="lb-card lb-card-2">
            <div class="lb-badge"><div class="lb-dot"></div> 🥈 TOP 2 · LAST 5MIN</div>
            <div class="lb-name">{top2_name}</div>
            <div class="lb-count">⚡ {top2_count:,} OTPs</div>
          </div>
          <div class="lb-card lb-card-3">
            <div class="lb-badge"><div class="lb-dot"></div> 🥉 TOP 3 · LAST 5MIN</div>
            <div class="lb-name">{top3_name}</div>
            <div class="lb-count">📡 {top3_count:,} OTPs</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Target Tracker
        st.markdown(f'<div class="section-label">LIVE TARGET TRACKER // {target_cli.upper()}</div>', unsafe_allow_html=True)
        df_target = df[df['cli'].str.contains(target_cli, case=False, na=False)].copy()
        if not df_target.empty:
            mid_df = df_target.head(25).copy()
            mid_df[['Team Member', 'Range']] = mid_df['num'].apply(lambda x: pd.Series(get_team_info(x, team_data)))
            mid_df['Country'] = mid_df['num'].apply(get_country)
            disp_mid = mid_df[['dt','cli','num','Country','message','Team Member','Range']].copy()
            disp_mid.columns = ['Time','App','Number','Country','Message','Team Member','Range']
            disp_mid = disp_mid.sort_values('Time', ascending=False)
            disp_mid['Time'] = disp_mid['Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
            st.dataframe(disp_mid.style.apply(highlight_team, axis=1),
                         use_container_width=True, height=300, hide_index=True, column_config=col_cfg)
        else:
            st.markdown('<div class="status-box"><div class="icon">📡</div><div class="title">NO PACKETS DETECTED</div><div class="desc">No data stream found for current agent identifier.</div></div>', unsafe_allow_html=True)

        # Global Stream
        st.markdown('<div class="section-label">GLOBAL LIVE NETWORK STREAM</div>', unsafe_allow_html=True)
        global_df = df.head(msg_limit).copy()
        global_df[['Team Member', 'Range']] = global_df['num'].apply(lambda x: pd.Series(get_team_info(x, team_data)))
        global_df['Country'] = global_df['num'].apply(get_country)
        disp_global = global_df[['dt','cli','num','Country','message','Team Member','Range']].copy()
        disp_global.columns = ['Time','App','Number','Country','Message','Team Member','Range']
        disp_global = disp_global.sort_values('Time', ascending=False)
        disp_global['Time'] = disp_global['Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
        st.dataframe(disp_global.style.apply(highlight_team, axis=1),
                     use_container_width=True, height=500, hide_index=True, column_config=col_cfg)
    else:
        st.markdown('<div class="status-box"><div class="icon">🛰️</div><div class="title">CONNECTING TO NETWORK</div><div class="desc">Data stream initializing... please wait.</div></div>', unsafe_allow_html=True)

# ============================================================
#  TAB 2 — DATABASE FILTERS
# ============================================================
with history_placeholder.container():
    if filter_cli or filter_num or filter_msg:
        try:
            sheet_r = requests.get(GOOGLE_SCRIPT_URL, timeout=10)
            if sheet_r.status_code == 200:
                sheet_data = sheet_r.json()
                if sheet_data:
                    saved_df = pd.DataFrame(sheet_data)
                    if filter_cli: saved_df = saved_df[saved_df['App'].astype(str).str.contains(filter_cli, case=False, na=False)]
                    if filter_num: saved_df = saved_df[saved_df['Number'].astype(str).str.contains(filter_num, na=False)]
                    if filter_msg: saved_df = saved_df[saved_df['Message'].astype(str).str.contains(filter_msg, case=False, na=False)]
                    st.markdown(f'<div class="section-label">QUERY RESULTS — {len(saved_df):,} RECORDS FOUND</div>', unsafe_allow_html=True)
                    if not saved_df.empty:
                        try:
                            saved_df['Time'] = pd.to_datetime(saved_df['Time'])
                            saved_df = saved_df.sort_values('Time', ascending=False)
                            saved_df['Time'] = saved_df['Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
                        except: pass
                        saved_df[['Team Member','Range']] = saved_df['Number'].apply(lambda x: pd.Series(get_team_info(x, team_data)))
                        st.dataframe(saved_df.style.apply(highlight_team, axis=1),
                                     use_container_width=True, height=600, hide_index=True, column_config=col_cfg)
                    else:
                        st.markdown('<div class="status-box"><div class="icon">❌</div><div class="title">NO RECORDS FOUND</div><div class="desc">No entries matched your search criteria.</div></div>', unsafe_allow_html=True)
        except:
            st.warning("Database connection error. Retry karo.")
    else:
        st.markdown("""
        <div class="status-box">
          <div class="icon">🛰️</div>
          <div class="title">COLD STORAGE MONITOR — SYSTEM READY</div>
          <div class="desc">Database preload disabled to maximize performance.<br>Enter a search term above to query records instantly.</div>
        </div>
        """, unsafe_allow_html=True)

# ============================================================
#  AUTO REFRESH — 15 seconds — WHILE LOOP NAHI!
# ============================================================
time.sleep(15)
st.rerun()
