import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import phonenumbers
from phonenumbers import geocoder
from bs4 import BeautifulSoup

# --- CONFIG ---
URL = "http://51.77.216.195/crapi/lamix/viewstats"
TOKEN = "SVdVRTRSQkd-ZVZEYWVgfmiViFmCg3ZYX5FuZUJoUGZlgJWFhoyS"
TEAM_FILE = "Numbers_Export.csv"

# Page Config
st.set_page_config(page_title="HUNTING SYSTEM - UMER ALI", layout="wide")

# Static Panel Credentials Locked
ADMIN_USER = "UTS"
ADMIN_PASS = "@Umer123456"
BASE_PANEL_URL = "https://matrix-panel.tech"

# --- UI DESIGN (CYBERPUNK THEME) ---
st.markdown("""
<style>
    .stApp { background-color: #0a0a0c; color: #00ff66; font-family: 'Courier New', Courier, monospace; }
    .main-title { text-align: center; color: #00ff66; font-size: 42px; font-weight: 900; padding-top: 15px; margin-bottom: 5px; text-shadow: 0 0 15px #00ff66; }
    .main-subtitle { text-align: center; color: #888888; font-size: 12px; margin-bottom: 35px; letter-spacing: 4px; }
    .section-label { color: #ffffff; font-size: 18px; font-weight: bold; margin-top: 40px; margin-bottom: 15px; border-bottom: 2px solid #333333; padding-bottom: 8px; }
    .section-label::before { content: "■ "; color: #00ff66; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div {
        background-color: #121214 !important; color: #00ff66 !important; border: 1px solid #00ff66 !important; border-radius: 4px !important;
    }
    label { color: #ffffff !important; }
    .stSidebar .stButton>button { background-color: #161b22; color: #a855f7; border: 1px solid #a855f7; font-weight: bold; }
    .stSidebar .stButton>button:hover { background-color: #a855f7; color: #000000; box-shadow: 0 0 10px #a855f7; }
    div[data-testid="stForm"] { border: 2px solid #a855f7; border-radius: 8px; padding: 25px; background-color: #111827; }
    .leaderboard-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px; }
    .rank-card { background: linear-gradient(135deg, #121214, #1a1a1e); border: 1px solid #222222; border-radius: 4px; padding: 20px; }
    .rank-1 { border-left: 5px solid #ffcc00; } .rank-2 { border-left: 5px solid #cccccc; } .rank-3 { border-left: 5px solid #cd7f32; }
    .rank-badge { font-size: 11px; font-weight: bold; }
    .rank-1 .rank-badge { color: #ffcc00; } .rank-2 .rank-badge { color: #cccccc; } .rank-3 .rank-badge { color: #cd7f32; }
    .rank-cli { color: #ffffff; font-size: 28px; font-weight: 900; }
    .rank-count { color: #00ff66; font-size: 14px; }
</style>
""", unsafe_allow_html=True)

# --- BACKEND INTERFACE TRANSMISSION ENGINE ---
def run_matrix_allocation_api(username, password, selected_range, quantity, target_client):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    })
    try:
        # Step 1: Initialize CSRF & Session Context
        login_page = session.get(f"{BASE_PANEL_URL}/auth/login", timeout=10)
        soup = BeautifulSoup(login_page.text, "html.parser")
        csrf_token = ""
        csrf_input = soup.find("input", {"name": "_token"})
        if csrf_input:
            csrf_token = csrf_input.get("value", "")

        # Step 2: Authenticate User Node
        payload = {
            "username": username,
            "email": username,
            "password": password
        }
        if csrf_token:
            payload["_token"] = csrf_token

        session.post(f"{BASE_PANEL_URL}/auth/login", data=payload, timeout=10, allow_redirects=True)
        
        # Step 3: Fetch allocation page to get active form unique tokens
        alloc_page = session.get(f"{BASE_PANEL_URL}/agent/allocate", timeout=10)
        alloc_soup = BeautifulSoup(alloc_page.text, "html.parser")
        
        alloc_csrf = ""
        alloc_csrf_input = alloc_soup.find("input", {"name": "_token"})
        if alloc_csrf_input:
            alloc_csrf = alloc_csrf_input.get("value", "")

        # Step 4: Dispatch targeting structural Select2 Array Parameters
        post_payload = {
            "range_name[]": str(selected_range).strip(),
            "qty": int(quantity),
            "allocate_target": str(target_client).strip(),
            "payout_pattern": "Daily",
            "client_payout": "0.013"
        }
        if alloc_csrf:
            post_payload["_token"] = alloc_csrf
            
        session.headers.update({"Referer": f"{BASE_PANEL_URL}/agent/allocate"})
        action_res = session.post(f"{BASE_PANEL_URL}/agent/allocate", data=post_payload, timeout=12)
        
        if action_res.status_code in [200, 302]:
            return True, f"Successfully Allocated {quantity} Items from '{selected_range}' to '{target_client}'!"
        return False, f"Server denied request execution. Status Code: {action_res.status_code}"
    except Exception as e:
        return False, f"Tunnel bridge connectivity error: {str(e)}"

# --- SNIFFER AUXILIARY LOGIC ---
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
        return df
    except:
        return pd.DataFrame()

def get_team_info(num, team_df):
    if team_df.empty:
        return "", ""
    n_str = str(num).split('.')[0].strip()
    match = team_df[team_df['Phone Number'] == n_str]
    if not match.empty:
        name = match.iloc[0]['MemberName']
        if name in ["UTS_Umer1", "UTS_Khadija"]:
            return "", ""
        return name, match.iloc[0]['Range']
    return "", ""

def highlight_team(row):
    if row['Team Member'] != "":
        return ['background-color: rgba(255, 0, 85, 0.12); color: #ff3366; font-weight: bold; border-right: 4px solid #ff0055;'] * len(row)
    return [''] * len(row)

# --- NAVIGATION SETUP ---
if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"

st.sidebar.title("🔮 UTS MATRIX CONTROL")
st.sidebar.markdown("---")
if st.sidebar.button("📊 Main Dashboard (Sniffer)", use_container_width=True):
    st.session_state.current_page = "Dashboard"
if st.sidebar.button("🔗 Link Numbers Panel", use_container_width=True):
    st.session_state.current_page = "LinkNumbers"
st.sidebar.markdown("---")
st.sidebar.caption("DEVELOPED BY: UTS TEAM")

# ==========================================
# PAGE 1: LIVE SNIFFER DASHBOARD
# ==========================================
if st.session_state.current_page == "Dashboard":
    st.markdown('<div class="main-title">⚡ DOUBLE FACER HUNTER ⚡</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-subtitle">> SYSTEM CONTROL PANEL // NETWORK SNIFFER</div>', unsafe_allow_html=True)

    col_in1, col_in2 = st.columns([2, 1])
    with col_in1:
        target_cli = st.text_input("⚙️ ENTER TARGET AGENT (CLI):", "MYOB").strip()
    with col_in2:
        msg_limit = st.number_input("📡 STREAM BUFFER LIMIT:", min_
