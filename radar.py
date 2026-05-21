import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import phonenumbers
from phonenumbers import geocoder
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIG ---
URL = "http://51.77.216.195/crapi/lamix/viewstats"
TOKEN = "SVdVRTRSQkd-ZVZEYWVgfmiViFmCg3ZYX5FuZUJoUGZlgJWFhoyS"
TEAM_FILE = "Numbers_Export.csv"

# Page Config (Must be at the top)
st.set_page_config(page_title="HUNTING SYSTEM - UMER ALI", layout="wide")

# --- UI DESIGN (CYBERPUNK & PURPLE HYBRID THEME) ---
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
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div {
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

    /* Sidebar Button styling for multi-page switching */
    .stSidebar .stButton>button {
        background-color: #161b22;
        color: #a855f7;
        border: 1px solid #a855f7;
        font-weight: bold;
        border-radius: 4px;
    }
    .stSidebar .stButton>button:hover {
        background-color: #a855f7;
        color: #000000;
        box-shadow: 0 0 10px #a855f7;
    }

    /* Allocation Submit Form Box */
    div[data-testid="stForm"] {
        border: 2px solid #a855f7;
        border-radius: 8px;
        padding: 25px;
        background-color: #111827;
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

# --- HELPER FUNCTIONS FOR SNIFFER ---
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
    except Exception: 
        return pd.DataFrame()

def get_team_info_dict(team_df):
    if not team_df.empty:
        return team_df.set_index('Phone Number')[['Range', 'MemberName']].to_dict('index')
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
        return ['background-color: rgba(255, 0, 85, 0.12); color: #ff3366; font-weight: bold; border-right: 4px solid #ff0055;'] * len(row)
    return [''] * len(row)


# --- SELENIUM BACKEND INTEGRATION ENGINE ---
def run_matrix_allocation(admin_user, admin_pass, selected_range, quantity, target_client):
    from webdriver_manager.chrome import ChromeDriverManager
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 25)
    
    try:
        # Login
        driver.get("https://matrix-panel.tech/auth/login")
        email_field = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='text' or @name='username' or @name='email']")))
        password_field = driver.find_element(By.XPATH, "//input[@type='password' or @name='password']")
        login_btn = driver.find_element(By.XPATH, "//button[@type='submit' or contains(text(), 'Login')]")
        
        email_field.send_keys(admin_user)
        password_field.send_keys(admin_pass)
        login_btn.click()
        time.sleep(4)
        
        # Navigate to Allocation
        driver.get("https://matrix-panel.tech/agent/allocate")
        time.sleep(3)
        
        # Dynamic inputs execution (Typing values straight from system parameters)
        range_input = wait.until(EC.presence_of_element_located((By.XPATH, "//select[contains(@class, 'form-control')] | //input[contains(@placeholder, 'Select Ranges')]")))
        range_input.send_keys(selected_range)
        time.sleep(1)
        
        qty_field = driver.find_element(By.XPATH, "//input[@placeholder='e.g. 500' or @type='number']")
        qty_field.clear()
        qty_field.send_keys(str(quantity))
        
        client_input = driver.find_element(By.XPATH, "//select[contains(., 'Target')] | //input[contains(@placeholder, 'Target Clients')]")
        client_input.send_keys(target_client)
        time.sleep(1)
        
        final_allocate_btn = driver.find_element(By.XPATH, "//button[contains(., 'Allocate Numbers')]")
        final_allocate_btn.click()
        time.sleep(4)
        
        driver.quit()
        return True, f"Successfully Linked {quantity} numbers from range '{selected_range}' to '{target_client}'!"
    except Exception as e:
        driver.quit()
        return False, f"Automation Interface Issue: {str(e)}"


# --- NAVIGATION SESSION HANDLING ---
if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"

# Sidebar Design
st.sidebar.title("🔮 UTS MATRIX CONTROL")
st.sidebar.markdown("---")
if st.sidebar.button("📊 Main Dashboard (Sniffer)", use_container_width=True):
    st.session_state.current_page = "Dashboard"
if st.sidebar.button("🔗 Link Numbers Panel", use_container_width=True):
    st.session_state.current_page = "LinkNumbers"
st.sidebar.markdown("---")
st.sidebar.caption("DEVELOPED BY: UTS TEAM")

# Load Team CSV Data Globally
raw_team_df = load_team_data()
team_dict = get_team_info_dict(raw_team_df)


# ==========================================
# PAGE 1: DUAL SNIFFER DASHBOARD LOGIC
# ==========================================
if st.session_state.current_page == "Dashboard":
    st.markdown('<div class="main-title">⚡ DOUBLE FACER HUNTER ⚡</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-subtitle">> SYSTEM CONTROL PANEL // NETWORK SNIFFER</div>', unsafe_allow_html=True)

    # Sniffer Config Inputs
    col_in1, col_in2 = st.columns([2, 1])
    with col_in1:
        target_cli = st.text_input("⚙️ ENTER TARGET AGENT (CLI):", "MYOB").strip()
    with col_in2:
        msg_limit = st.number_input("📡 STREAM BUFFER LIMIT:", min_value=1, max_value=2000, value=1000)

    placeholder = st.empty()

    col_cfg = {
        "Time": st.column_config.TextColumn("TIMESTAMP", width="medium"),
        "App": st.column_config.TextColumn("IDENT/CLI", width="small"),
        "Number": st.column_config.TextColumn("DATA_STREAM", width="medium"),
        "Country": st.column_config.TextColumn("LOCATION", width="small"),
        "Message": st.column_config.TextColumn("DECRYPTED_MSG", width="max"),
        "Team Member": st.column_config.TextColumn("OPERATOR", width="medium"),
        "Range": st.column_config.TextColumn("NETWORK_RANGE", width="large"),
    }

    # Running continuous sniffer loop
    while st.session_state.current_page == "Dashboard":
        try:
            r = requests.get(URL, params={"token": TOKEN, "records": 5000})
            if r.status_code == 200:
                data = r.json().get("data", [])
                df = pd.DataFrame(data)
                
                if not df.empty:
                    df['dt'] = pd.to_datetime(df['dt'])
                    now = datetime.now()
                    
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

                    with placeholder.container():
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

                        st.markdown(f'<div class="section-label">LIVE TARGET TRACKER // ACCESSED: {target_cli.upper()}</div>', unsafe_allow_html=True)
                        if not df_target_all.empty:
                            mid_df = df_target_all.head(25).copy()
                            mid_df[['Team Member', 'Range']] = mid_df['num'].apply(lambda x: pd.Series(get_team_info(x, team_dict)))
                            mid_df['Country'] = mid_df['num'].apply(get_country)
                            
                            disp_mid = mid_df[['dt', 'cli', 'num', 'Country', 'message', 'Team Member', 'Range']]
                            disp_mid.columns = ['Time', 'App', 'Number', 'Country', 'Message', 'Team Member', 'Range']
                            
                            st.dataframe(disp_mid.style.apply(highlight_team, axis=1), 
                                         use_container_width=True, height=350, hide_index=True, column_config=col_cfg)
                        else:
                            st.caption("NO PACKETS DETECTED FOR CURRENT AGENT.")

                        st.markdown('<div class="section-label">GLOBAL NETWORK LOG STREAM</div>', unsafe_allow_html=True)
                        global_df = df.head(msg_limit).copy()
                        global_df[['Team Member', 'Range']] = global_df['num'].apply(lambda x: pd.Series(get_team_info(x, team_dict)))
                        global_df['Country'] = global_df['num'].apply(get_country)
                        
                        disp_global = global_df[['dt', 'cli', 'num', 'Country', 'message', 'Team Member', 'Range']]
                        disp_global.columns = ['Time', 'App', 'Number', 'Country', 'Message', 'Team Member', 'Range']
                        
                        st.dataframe(disp_global.style.apply(highlight_team, axis=1), 
                                     use_container_width=True, height=750, hide_index=True, column_config=col_cfg)

            time.sleep(15)
            st.rerun()
        except Exception as e:
            time.sleep(5)


# ==========================================
# PAGE 2: SECURE LINK NUMBERS ALLOCATION
# ==========================================
elif st.session_state.current_page == "LinkNumbers":
    st.markdown('<div class="main-title">⚡ SECURE LINK NUMBERS BRIDGE ⚡</div>', unsafe_allow_html=True)
    st.write("Fill parameters to execute bulk allocation action on the Matrix panel.")
    
    # Extract dynamic select options from Numbers_Export.csv if data exists
    if not raw_team_df.empty:
        dynamic_ranges = ["-- Select Ranges --"] + sorted(raw_team_df['Range'].dropna().unique().tolist())
        dynamic_clients = ["-- Select Target Clients --"] + sorted(raw_team_df['MemberName'].dropna().unique().tolist())
    else:
        # Fallbacks strings if file mapping error occurs
        dynamic_ranges = ["-- Select Ranges --", "Range A", "Range B"]
        dynamic_clients = ["-- Select Target Clients --", "new han"]

    with st.form("secure_allocation_form"):
        st.subheader("Allocation Parameters Config")
        
        # 1. Dynamic Dropdown Range
        selected_range = st.selectbox("Range(s) (From Your Quota)", options=dynamic_ranges)
        
        # 2. Strict Capped Quantity Input
        quantity = st.number_input("Quantity (Maximum allowed: 50)", min_value=1, max_value=50, value=10, step=1)
        
        # 3. Dynamic Dropdown Client
        target_client = st.selectbox("Target Client(s)", options=dynamic_clients)
        
        st.markdown("---")
        submit_action = st.form_submit_button("⚡ Execute Safe Allocation")
        
        if submit_action:
            if "Select" in selected_range or "Select" in target_client:
                st.error("Meharbani karke valid Range aur Target Client select karein!")
            elif quantity > 50:
                st.error("Operation Denied: Batch quantity processing ceiling is capped at 50.")
            else:
                with st.spinner("Connecting Matrix Tunnel Core... Executing Allocation."):
                    # Injected Login details securely
                    ADMIN_USER = "UTS"
                    ADMIN_PASS = "@Umer123456"
                    
                    success, msg = run_matrix_allocation(ADMIN_USER, ADMIN_PASS, selected_range, quantity, target_client)
                    
                    if success:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.error(msg)
