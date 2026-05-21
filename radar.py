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

# Page Config (Must be the very first Streamlit command)
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


# --- STREAMLIT CLOUD SELECT2 OPTIMIZED DRIVER ENGINE ---
def run_matrix_allocation(admin_user, admin_pass, selected_range, quantity, target_client):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  # Streamlit New Headless Standard
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # Chromium Cloud paths setup securely
    options.binary_location = "/usr/bin/chromium"
    
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
    except Exception:
        try:
            service = Service("/usr/lib/chromium-browser/chromedriver")
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            return False, f"Cloud Browser System Mapping Error: {str(e)}"
            
    wait = WebDriverWait(driver, 25)
    
    try:
        # Step 1: Login
        driver.get("https://matrix-panel.tech/auth/login")
        email_field = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='text' or @name='username' or @name='email']")))
        password_field = driver.find_element(By.XPATH, "//input[@type='password' or @name='password']")
        login_btn = driver.find_element(By.XPATH, "//button[@type='submit' or contains(text(), 'Login')]")
        
        email_field.send_keys(admin_user)
        password_field.send_keys(admin_pass)
        login_btn.click()
        time.sleep(4)
        
        # Step 2: Navigate to Allocation Page
        driver.get("https://matrix-panel.tech/agent/allocate")
        time.sleep(3)
        
        # Step 3: Select2 Handling for 'Ranges' Dropdown
        # Pehle Select2 element ke
