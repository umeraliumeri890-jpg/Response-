import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import phonenumbers
from phonenumbers import geocoder

# --- CONFIG ---
URL = "http://51.77.216.195/crapi/lamix/viewstats"
TOKEN = "SVdVRTRSQmiGX4FWYJJzgF-Hi4mHX41TglBhWVtieEOEUHhleGFy"
TEAM_FILE = "Numbers_Export.csv"

st.set_page_config(page_title="HUNTING RADAR - TEAM PRO", layout="wide")

# Stylish UI & Highlight Logic
st.markdown("""
<style>
    .stApp { background-color: #050505; color: #00ff00; }
    .report-box { 
        background-color: #111; border: 1px solid #00ff00; 
        padding: 20px; border-radius: 15px; margin-bottom: 20px;
    }
    .team-highlight {
        background-color: #1d3557 !important;
        color: #ffb703 !important;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Helper Functions
def get_country(num):
    try:
        full_num = "+" + str(num).strip()
        parsed = phonenumbers.parse(full_num)
        return geocoder.description_for_number(parsed, "en")
    except: return "Unknown"

@st.cache_data
def load_team_numbers():
    try:
        df = pd.read_csv(TEAM_FILE)
        return df['Phone Number'].astype(str).tolist()
    except: return []

# UI LAYOUT
st.title("📡 PRO HUNTING & TEAM MONITOR")

col_a, col_b = st.columns([2, 1])
with col_a:
    target_app = st.text_input("🔍 Search App Stats (e.g. whatsapp):", "whatsapp").strip().lower()
with col_b:
    msg_limit = st.number_input("📥 Live Messages Limit:", min_value=5, max_value=200, value=25)

team_numbers = load_team_numbers()
placeholder = st.empty()

while True:
    try:
        # 1-day analysis ke liye humein max records chahiye honge
        r = requests.get(URL, params={"token": TOKEN, "records": 2000})
        if r.status_code == 200:
            data = r.json().get("data", [])
            df = pd.DataFrame(data)
            
            if not df.empty:
                df['dt'] = pd.to_datetime(df['dt'])
                latest_time = df['dt'].max()
                
                # --- 1: TARGETED REPORT (5m, 10m, 30m, 1 Day) ---
                df_target = df[df['cli'].str.contains(target_app, case=False, na=False)].copy()
                
                c5 = len(df_target[df_target['dt'] >= (latest_time - timedelta(minutes=5))])
                c10 = len(df_target[df_target['dt'] >= (latest_time - timedelta(minutes=10))])
                c30 = len(df_target[df_target['dt'] >= (latest_time - timedelta(minutes=30))])
                c1d = len(df_target[df_target['dt'] >= (latest_time - timedelta(days=1))])
                
                # Country mapping for Target App
                if not df_target.empty:
                    df_target['Country'] = df_target['num'].head(30).apply(get_country)
                    top_countries = df_target['Country'].value_counts().head(3).index.tolist()
                    countries_str = ", ".join(top_countries)
                else:
                    countries_str = "No Data"

                # --- 2: LIVE FEED WITH HIGHLIGHTS ---
                df_live = df.head(msg_limit).copy()
                df_live['Country'] = df_live['num'].apply(get_country)
                
                # Highlight Logic
                def highlight_team(row):
                    if str(row['num']) in team_numbers:
                        return ['background-color: #1d3557; color: #ffb703; font-weight: bold'] * len(row)
                    return [''] * len(row)

                with placeholder.container():
                    # TOP REPORT
                    st.markdown(f"""
                    <div class="report-box">
                        <h3 style="color:#00ff00; margin-top:0;">📊 {target_app.upper()} INTELLIGENCE</h3>
                        <p><b>5 Mins:</b> {c5} | <b>10 Mins:</b> {c10} | <b>30 Mins:</b> {c30} | <b>1 Day:</b> {c1d}</p>
                        <p><b>🌍 Active Regions:</b> {countries_str}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    # LIVE TABLE
                    st.subheader(f"🚀 Latest {msg_limit} Global Messages")
                    styled_df = df_live[['dt', 'cli', 'num', 'Country', 'message']].style.apply(highlight_team, axis=1)
                    st.table(styled_df)

            else:
                st.info("Market scanning...")

        time.sleep(15)
        st.rerun()
    except Exception as e:
        time.sleep(5)
                
