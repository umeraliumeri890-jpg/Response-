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
TEAM_FILE = "Numbers_Export.csv"  # Sirf sniffer dashboard par operators match karne ke liye use hogi

# Page Config
st.set_page_config(page_title="HUNTING SYSTEM - UMER ALI", layout="wide")

# Static Panel Credentials Locked
ADMIN_USER = "UTS"
ADMIN_PASS = "@Umer123456"

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

# --- PANEL DATA SCRAPER & AUTOMATION ENGINE ---
def get_selenium_options():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.binary_location = "/usr/bin/chromium"
    return options

def get_webdriver():
    options = get_selenium_options()
    try:
        return webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=options)
    except:
        return webdriver.Chrome(service=Service("/usr/lib/chromium-browser/chromedriver"), options=options)

@st.cache_data(ttl=300)  # 5 minutes cache taaki baar baar login na karna pare
def fetch_live_panel_options(admin_user, admin_pass):
    """Matrix Panel par login karke real dropdown choices scrape karta ha"""
    driver = get_webdriver()
    wait = WebDriverWait(driver, 20)
    ranges_list = []
    clients_list = []
    
    try:
        # Step 1: Login
        driver.get("https://matrix-panel.tech/auth/login")
        email_field = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='text' or @name='username' or @name='email']")))
        password_field = driver.find_element(By.XPATH, "//input[@type='password' or @name='password']")
        login_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
        
        email_field.send_keys(admin_user)
        password_field.send_keys(admin_pass)
        login_btn.click()
        time.sleep(4)
        
        # Step 2: Go to allocation page
        driver.get("https://matrix-panel.tech/agent/allocate")
        time.sleep(3)
        
        # Ranges Options Scrape (Select hidden option elements tags directly)
        range_elements = driver.find_elements(By.XPATH, "//select[contains(@id, 'range_name') or contains(@name, 'range_name')]/option")
        for el in range_elements:
            text = el.text.strip()
            if text and "--" not in text:
                ranges_list.append(text)
                
        # Target Clients Options Scrape
        client_elements = driver.find_elements(By.XPATH, "//select[contains(@id, 'allocate_target') or contains(@name, 'allocate_target')]/option")
        for el in client_elements:
            text = el.text.strip()
            if text and "--" not in text:
                clients_list.append(text)
                
        driver.quit()
        return sorted(list(set(ranges_list))), sorted(list(set(clients_list)))
    except Exception as e:
        driver.quit()
        return [], []

def run_matrix_allocation(admin_user, admin_pass, selected_range, quantity, target_client):
    """Select2 targets ko robust tareeqay se handle karne wali main pipeline"""
    driver = get_webdriver()
    wait = WebDriverWait(driver, 25)
    
    try:
        # Step 1: Login
        driver.get("https://matrix-panel.tech/auth/login")
        email_field = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='text' or @name='username' or @name='email']")))
        password_field = driver.find_element(By.XPATH, "//input[@type='password' or @name='password']")
        login_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
        
        email_field.send_keys(admin_user)
        password_field.send_keys(admin_pass)
        login_btn.click()
        time.sleep(4)
        
        # Step 2: Allocation Dashboard Page Link
        driver.get("https://matrix-panel.tech/agent/allocate")
        time.sleep(4)
        
        # Step 3: Select2 Handling for 'Ranges' Dropdown Field
        # Span container ya parent box par strong click target lagaya ha
        range_container = wait.until(EC.element_to_be_clickable((By.XPATH, "//select[@id='range_name']/following-sibling::span[contains(@class, 'select2')]|//textarea[contains(@aria-describedby, 'select2-range_name')]/..")))
        driver.execute_script("arguments[0].click();", range_container)
        time.sleep(1.5)
        
        # Select2 dropdown body open hone par text write engine trigger
        range_search = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@class='select2-search__field']|//textarea[contains(@class, 'select2-search__field')]")))
        range_search.send_keys(selected_range)
        time.sleep(1.5)
        range_search.send_keys("\n")  # Hit Enter key
        time.sleep(1)
        
        # Step 4: Quantity Field Setup
        qty_field = driver.find_element(By.XPATH, "//input[contains(@name, 'qty') or @type='number' or @placeholder='e.g. 500']")
        qty_field.clear()
        qty_field.send_keys(str(quantity))
        time.sleep(1)
        
        # Step 5: Select2 Handling for 'Target Clients' Dropdown
        client_container = driver.find_element(By.XPATH, "//select[@id='allocate_target']/following-sibling::span[contains(@class, 'select2')]|//textarea[contains(@aria-describedby, 'select2-allocate_target')]/..")
        driver.execute_script("arguments[0].click();", client_container)
        time.sleep(1.5)
        
        client_search = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@class='select2-search__field']|//textarea[contains(@class, 'select2-search__field')]")))
        client_search.send_keys(target_client)
        time.sleep(1.5)
        client_search.search.send_keys("\n")  # Hit Enter key
        time.sleep(1.5)
        
        # Step 6: Final Submission Allocation Button Click
        final_allocate_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Allocate Numbers')]|//button[@id='allocate_btn']")))
        driver.execute_script("arguments[0].click();", final_allocate_btn)
        time.sleep(5)   # Success confirmation delay
        
        driver.quit()
        return True, f"Successfully Allocated {quantity} numbers from '{selected_range}' to '{target_client}'!"
    except Exception as e:
        driver.quit()
        return False, f"Select2 Link Automation Error: {str(e)}"

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

    while st.session_state.current_page == "Dashboard":
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
                        else: st.caption("NO PACKETS DETECTED FOR CURRENT AGENT.")

                        st.markdown('<div class="section-label">GLOBAL NETWORK LOG STREAM</div>', unsafe_allow_html=True)
                        global_df = df.head(msg_limit).copy()
                        global_df[['Team Member', 'Range']] = global_df['num'].apply(lambda x: pd.Series(get_team_info(x, team_df)))
                        global_df['Country'] = global_df['num'].apply(get_country)
                        disp_global = global_df[['dt', 'cli', 'num', 'Country', 'message', 'Team Member', 'Range']]
                        disp_global.columns = ['Time', 'App', 'Number', 'Country', 'Message', 'Team Member', 'Range']
                        st.dataframe(disp_global.style.apply(highlight_team, axis=1), use_container_width=True, height=600, hide_index=True, column_config=col_cfg)

            time.sleep(15)
            st.rerun()
        except:
            time.sleep(5)

# ==========================================
# PAGE 2: LINK NUMBERS ALLOCATION (PANEL SYNCED)
# ==========================================
elif st.session_state.current_page == "LinkNumbers":
    st.markdown('<div class="main-title">⚡ SECURE LINK NUMBERS BRIDGE ⚡</div>', unsafe_allow_html=True)
    
    # Live account options loader setup
    with st.spinner("🔄 Synchronizing live data options from Matrix Panel account..."):
        live_ranges, live_clients = fetch_live_panel_options(ADMIN_USER, ADMIN_PASS)
    
    if not live_ranges or not live_clients:
        st.warning("⚠️ Warning: Could not connect or retrieve choices dynamically. Retrying container tunnel...")
        # Fallbacks in case dashboard scraping experiences network delays
        live_ranges = ["-- No Live Ranges Detected --"] if not live_ranges else live_ranges
        live_clients = ["-- No Live Clients Detected --"] if not live_clients else live_clients

    with st.form("secure_allocation_form"):
        st.subheader("Allocation Parameters Config (Live Synced)")
        
        selected_range = st.selectbox("Range(s) (Fetched Live From Your Quota)", options=["-- Select Ranges --"] + live_ranges)
        quantity = st.number_input("Quantity (Maximum batch limit: 50)", min_value=1, max_value=50, value=10, step=1)
        target_client = st.selectbox("Target Client(s) (Fetched Live from Panel)", options=["-- Select Target Clients --"] + live_clients)
        
        st.markdown("---")
        submit_action = st.form_submit_button("⚡ Execute Safe Allocation")
        
        if submit_action:
            if "Select" in selected_range or "Select" in target_client or "--" in selected_range:
                st.error("Meharbani karke live values mein se valid Range aur Target Client select karein!")
            else:
                with st.spinner("Executing dynamic injection on Matrix Panel Core..."):
                    success, msg = run_matrix_allocation(ADMIN_USER, ADMIN_PASS, selected_range, quantity, target_client)
                    if success:
                        st.success(msg)
                        st.balloons()
                    else:
