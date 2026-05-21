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

# --- BACKEND EXECUTOR ENGINE ---
def run_direct_matrix_allocation(selected_range, quantity, target_client):
    """Direct transmission layer that mimics secure browser post headers"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Origin": BASE_PANEL_URL,
        "Referer": f"{BASE_PANEL_URL}/auth/login"
    })
    
    try:
        # Step 1: Initialize Session Cookie Context
        login_init = session.get(f"{BASE_PANEL_URL}/auth/login", timeout=10)
        
        # Step 2: Fire Secure Core Authentication Payload
        login_payload = {
            "username": ADMIN_USER,
            "email": ADMIN_USER,
            "password": ADMIN_PASS
        }
        auth_res = session.post(f"{BASE_PANEL_URL}/auth/login", data=login_payload, timeout=10, allow_redirects=True)
        
        # Step 3: Dispatch Payload Endpoint Parameters
        post_payload = {
            "range_name": str(selected_range).strip(),
            "qty": int(quantity),
            "allocate_target": str(target_client).strip(),
            "payout_pattern": "Daily",
            "client_payout": "0.013"
        }
        
        session.headers.update({"Referer": f"{BASE_PANEL_URL}/agent/allocate"})
        action_res = session.post(f"{BASE_PANEL_URL}/agent/allocate", data=post_payload, timeout=12, allow_redirects=True)
        
        if action_res.status_code in [200, 302]:
            return True, f"Successfully Processed allocation of {quantity} units to '{target_client}'!"
        return False, f"Server returned unexpected state response code: {action_res.status_code}"
        
    except Exception as e:
        return False, f"Interface Communication Exception: {str(e)}"

# --- SNIFFER AUXILIARY LOGIC ---
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
        return df
    except: return pd.DataFrame()

def get_team_info(num, team_df):
    if team_df.empty: return "", ""
    n_str = str(num).split('.')[0].strip()
    match = team_df[team_df['Phone Number'] == n_str]
    if not match.empty:
        name = match.iloc[0]['MemberName']
        if name in ["UTS_Umer1", "UTS_Khadija"]: return "", ""
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
    with col_in1: target_cli = st.text_input("⚙️ ENTER TARGET AGENT (CLI):", "MYOB").strip()
    with col_in2: msg_limit = st.number_input("📡 STREAM BUFFER LIMIT:", min_value=1, max_value=2000, value=1000)

    placeholder = st.empty()
    team_df = load_team_data()

    col_cfg = {
        "Time": st.column_config.TextColumn("TIMESTAMP", width="medium"),
        "App": st.column_config.TextColumn("IDENT/CLI", width="small"),
        "Number": st.column_config.TextColumn("DATA_STREAM", width="medium"),
        "Country": st.column_config.TextColumn("LOCATION", width="small"),
        "Message": st.column_config.TextColumn("DECRYPTED_MSG", width="max"),
        "Team Member": st.column_config.TextColumn("OPERATOR", width="medium"),
        "Range": st.column_config.TextColumn("NETWORK_RANGE", width="large"),
    }

    try:
        r = requests.get(URL, params={"token": TOKEN, "records": 5000})
        if r.status_code == 200:
            data = r.json().get("data", [])
            df = pd.DataFrame(data)
            
            if not df.empty:
                df['dt'] = pd.to_datetime(df['dt'])
                df_5m = df[df['dt'] >= (datetime.now() - timedelta(minutes=5))]
                
                top1, top2, top3 = ("NO_DATA", 0), ("NO_DATA", 0), ("NO_DATA", 0)
                if not df_5m.empty and 'cli' in df_5m.columns:
                    top = df_5m['cli'].value_counts().head(3)
                    if len(top) >= 1: top1 = (top.index[0], top.iloc[0])
                    if len(top) >= 2: top2 = (top.index[1], top.iloc[1])
                    if len(top) >= 3: top3 = (top.index[2], top.iloc[2])

                df_target_all = df[df['cli'].str.contains(target_cli, case=False, na=False)].copy()

                with placeholder.container():
                    st.markdown(f"""
                    <div class="leaderboard-grid">
                        <div class="rank-card rank-1"><div class="rank-badge">🏆 TOP 1 (LAST 5M)</div><div class="rank-cli">{top1[0]}</div><div class="rank-count">🔥 {top1[1]} OTPs</div></div>
                        <div class="rank-card rank-2"><div class="rank-badge">🥈 TOP 2 (LAST 5M)</div><div class="rank-cli">{top2[0]}</div><div class="rank-count">⚡ {top2[1]} OTPs</div></div>
                        <div class="rank-card rank-3"><div class="rank-badge">🥉 TOP 3 (LAST 5M)</div><div class="rank-cli">{top3[0]}</div><div class="rank-count">📡 {top3[1]} OTPs</div></div>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown(f'<div class="section-label">LIVE TARGET TRACKER // ACCESSED: {target_cli.upper()}</div>', unsafe_allow_html=True)
                    if not df_target_all.empty:
                        mid_df = df_target_all.head(25).copy()
                        mid_df[['Team Member', 'Range']] = mid_df['num'].apply(lambda x: pd.Series(get_team_info(x, team_df)))
                        mid_df['Country'] = mid_df['num'].apply(get_country)
                        disp_mid = mid_df[['dt', 'cli', 'num', 'Country', 'message', 'Team Member', 'Range']]
                        disp_mid.columns = ['Time', 'App', 'Number', 'Country', 'Message', 'Team Member', 'Range']
                        st.dataframe(disp_mid.style.apply(highlight_team, axis=1), use_container_width=True, height=300, hide_index=True, column_config=col_cfg)
                    else:
                        st.caption("NO PACKETS DETECTED FOR CURRENT AGENT.")

                    st.markdown('<div class="section-label">GLOBAL NETWORK LOG STREAM</div>', unsafe_allow_html=True)
                    global_df = df.head(msg_limit).copy()
                    global_df[['Team Member', 'Range']] = global_df['num'].apply(lambda x: pd.Series(get_team_info(x, team_df)))
                    global_df['Country'] = global_df['num'].apply(get_country)
                    disp_global = global_df[['dt', 'cli', 'num', 'Country', 'message', 'Team Member', 'Range']]
                    disp_global.columns = ['Time', 'App', 'Number', 'Country', 'Message', 'Team Member', 'Range']
                    st.dataframe(disp_global.style.apply(highlight_team, axis=1), use_container_width=True, height=600, hide_index=True, column_config=col_cfg)

        time.sleep(12)
        st.rerun()
    except Exception as e:
        time.sleep(4)
        st.rerun()

# ==========================================
# PAGE 2: LINK NUMBERS ALLOCATION (HYBRID AUTOMATION)
# ==========================================
elif st.session_state.current_page == "LinkNumbers":
    st.markdown('<div class="main-title">⚡ SECURE LINK NUMBERS BRIDGE ⚡</div>', unsafe_allow_html=True)
    
    # Smart Data Loader from Local Exporter Storage
    team_df = load_team_data()
    detected_ranges = ["Afghanistan (K) Cellular 9374404xxxx"] # Default fail-safe fallback
    detected_clients = ["UTS_Amjad"]
    
    if not team_df.empty:
        if 'Range' in team_df.columns:
            extracted_ranges = sorted(list(set(team_df['Range'].dropna().astype(str).tolist())))
            if extracted_ranges: detected_ranges = extracted_ranges
        if 'MemberName' in team_df.columns:
            extracted_clients = sorted(list(set(team_df['MemberName'].dropna().astype(str).tolist())))
            extracted_clients = [c for c in extracted_clients if c.strip() and c not in ["UTS_Umer1", "UTS_Khadija"]]
            if extracted_clients: detected_clients = extracted_clients

    with st.form("secure_allocation_form"):
        st.subheader("Allocation Parameters Dynamic Manual Setup")
        
        # Dropdowns mapping from active configurations natively
        selected_range = st.selectbox("Select Target Range:", options=detected_ranges)
        quantity = st.number_input("Quantity (Batch limit ceiling: 50):", min_value=1, max_value=50, value=10, step=1)
        target_client = st.selectbox("Select Target Client:", options=detected_clients)
        
        st.markdown("---")
        submit_action = st.form_submit_button("⚡ Execute Safe Allocation")
        
        if submit_action:
            with st.spinner("Injecting allocation vectors directly into safe channel tunnel..."):
                success, msg = run_direct_matrix_allocation(selected_range, quantity, target_client)
                if success:
                    st.success(msg)
                    st.balloons()
                else:
                    st.error(msg)
