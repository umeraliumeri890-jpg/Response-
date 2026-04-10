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

st.set_page_config(page_title="HUNTING RADAR - UMER ALI", layout="wide")

# Stylish UI Design
st.markdown("""
<style>
    .stApp { background-color: #050505; color: #00ff00; }
    .main-title { text-align: center; color: #00ff00; font-size: 40px; font-weight: bold; margin-bottom: 0px; }
    .sub-title { text-align: center; color: #ffffff; font-size: 18px; margin-top: -10px; margin-bottom: 20px; }
    .report-box { 
        background-color: #111; border: 1px solid #00ff00; 
        padding: 20px; border-radius: 15px; margin-bottom: 20px;
        box-shadow: 0px 0px 10px #00ff00;
    }
</style>
""", unsafe_allow_html=True)

# Helper Functions
def get_country(num):
    try:
        full_num = "+" + str(num).strip()
        parsed = phonenumbers.parse(full_num)
        return geocoder.description_for_number(parsed, "en")
    except: return "Global"

@st.cache_data
def load_team_numbers():
    try:
        df = pd.read_csv(TEAM_FILE)
        return df['Phone Number'].astype(str).tolist()
    except: return []

# Header Section
st.markdown('<div class="main-title">🎯 HUNTING RADAR</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">✨ Powered by <b>Umer Ali</b> ✨</div>', unsafe_allow_html=True)

# Input Controls
col_in1, col_in2 = st.columns([2, 1])
with col_in1:
    target_cli = st.text_input("🔍 Search App (CLI):", "MYOB").strip()
with col_in2:
    msg_limit = st.number_input("📥 Live Feed Limit:", min_value=1, max_value=500, value=25)

team_numbers = load_team_numbers()
placeholder = st.empty()

while True:
    try:
        r = requests.get(URL, params={"token": TOKEN, "records": 3000})
        if r.status_code == 200:
            data = r.json().get("data", [])
            df = pd.DataFrame(data)
            
            if not df.empty:
                df['dt'] = pd.to_datetime(df['dt'])
                now = datetime.now()

                # --- BACKGROUND 5 AM LOGIC ---
                if now.hour < 5:
                    start_of_day = (now - timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)
                else:
                    start_of_day = now.replace(hour=5, minute=0, second=0, microsecond=0)

                # --- TARGETED CLI REPORT ---
                df_target = df[df['cli'].str.contains(target_cli, case=False, na=False)].copy()
                
                c5 = len(df_target[df_target['dt'] >= (now - timedelta(minutes=5))])
                c10 = len(df_target[df_target['dt'] >= (now - timedelta(minutes=10))])
                c30 = len(df_target[df_target['dt'] >= (now - timedelta(minutes=30))])
                c_today = len(df_target[df_target['dt'] >= start_of_day])
                
                if not df_target.empty:
                    df_target['Country'] = df_target['num'].head(50).apply(get_country)
                    top_regions = df_target['Country'].value_counts().head(3).index.tolist()
                    regions_str = ", ".join(top_regions)
                else:
                    regions_str = "No Data Found"

                # --- LIVE FEED PREVIEW ---
                df_live = df.head(msg_limit).copy()
                df_live['Country'] = df_live['num'].apply(get_country)

                with placeholder.container():
                    # THE CLEAN REPORT BOX
                    st.markdown(f"""
                    <div class="report-box">
                        <h2 style="color:#00ff00; margin-top:0;">📊 {target_cli.upper()} ANALYSIS</h2>
                        <table style="width:100%; color:white; font-size:20px;">
                            <tr>
                                <td><b>Last 5m:</b> {c5}</td>
                                <td><b>Last 10m:</b> {c10}</td>
                                <td><b>Last 30m:</b> {c30}</td>
                                <td style="color:#00ff00;"><b>Total Today:</b> {c_today}</td>
                            </tr>
                        </table>
                        <p style="margin-top:10px;">🌍 <b>Primary Regions:</b> {regions_str}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    # LIVE FEED TABLE (FIXED)
                    st.subheader(f"🚀 Latest {msg_limit} Global Records")
                    
                    # Formatting Display Data
                    display_df = df_live[['dt', 'cli', 'num', 'Country', 'message']].copy()
                    display_df.columns = ['Time', 'App', 'Number', 'Country', 'Message']
                    
                    # Highlighter function with correct column reference
                    def highlight_team(row):
                        is_team = str(row['Number']) in team_numbers
                        return ['background-color: #1d3557; color: #ffb703; font-weight: bold' if is_team else '' for _ in row]

                    # Displaying using st.dataframe for better reliability
                    st.dataframe(
                        display_df.style.apply(highlight_team, axis=1),
                        use_container_width=True,
                        height=500
                    )

            else:
                st.info("Searching market data...")

        time.sleep(15)
        st.rerun()
    except Exception as e:
        time.sleep(5)
        
