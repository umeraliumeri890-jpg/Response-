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

st.set_page_config(page_title="HUNTING RADAR - CLI ACCURATE", layout="wide")

# UI Styling
st.markdown("""
<style>
    .stApp { background-color: #050505; color: #00ff00; }
    .report-box { 
        background-color: #111; border: 1px solid #00ff00; 
        padding: 20px; border-radius: 15px; margin-bottom: 20px;
    }
    .team-row { background-color: #1d3557 !important; color: #ffb703 !important; }
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

# Main UI
st.title("📡 REAL-TIME CLI ANALYZER")

# Inputs
col_input1, col_input2 = st.columns([2, 1])
with col_input1:
    target_app = st.text_input("🔍 Search exact CLI Name (e.g. whatsapp, google, imo):", "whatsapp").strip().lower()
with col_input2:
    msg_limit = st.number_input("📥 Live Feed Limit:", min_value=5, max_value=500, value=30)

team_numbers = load_team_numbers()
placeholder = st.empty()

while True:
    try:
        # 1-day analysis ke liye 2000 records mangwa rahe hain
        r = requests.get(URL, params={"token": TOKEN, "records": 2000})
        if r.status_code == 200:
            data = r.json().get("data", [])
            df = pd.DataFrame(data)
            
            if not df.empty:
                df['dt'] = pd.to_datetime(df['dt'])
                latest_time = df['dt'].max()
                
                # --- 1: TARGETED CLI REPORT (Pure API Data) ---
                # Ye line sirf CLI column se match karegi
                df_target = df[df['cli'].str.contains(target_app, case=False, na=False)].copy()
                
                c5 = len(df_target[df_target['dt'] >= (latest_time - timedelta(minutes=5))])
                c10 = len(df_target[df_target['dt'] >= (latest_time - timedelta(minutes=10))])
                c30 = len(df_target[df_target['dt'] >= (latest_time - timedelta(minutes=30))])
                c1d = len(df_target[df_target['dt'] >= (latest_time - timedelta(days=1))])
                
                # Active Regions for this CLI
                if not df_target.empty:
                    df_target['Country'] = df_target['num'].head(50).apply(get_country)
                    top_regions = df_target['Country'].value_counts().head(3).index.tolist()
                    regions_str = ", ".join(top_regions)
                else:
                    regions_str = "Waiting for data..."

                # --- 2: LIVE FEED PREVIEW ---
                df_live = df.head(msg_limit).copy()
                df_live['Country'] = df_live['num'].apply(get_country)

                with placeholder.container():
                    # THE REPORT BOX
                    st.markdown(f"""
                    <div class="report-box">
                        <h3 style="color:#00ff00; margin-top:0;">📊 CLI REPORT: {target_app.upper()}</h3>
                        <p style="font-size:18px;">
                            <b>5m:</b> {c5} | <b>10m:</b> {c10} | <b>30m:</b> {c30} | <b>24h:</b> {c1d}
                        </p>
                        <p>🌍 <b>Active Countries (from CLI):</b> <span style="color:white;">{regions_str}</span></p>
                    </div>
                    """, unsafe_allow_html=True)

                    # LIVE FEED TABLE
                    st.subheader(f"🚀 Last {msg_limit} API Records")
                    
                    # Highlight Team Numbers
                    def make_styled(row):
                        is_team = str(row['num']) in team_numbers
                        color = 'background-color: #1d3557; color: #ffb703;' if is_team else ''
                        return [color] * len(row)

                    display_df = df_live[['dt', 'cli', 'num', 'Country', 'message']]
                    display_df.columns = ['Time', 'CLI (App)', 'Number', 'Country', 'Message']
                    
                    st.table(display_df.style.apply(make_styled, axis=1))

            else:
                st.info("Market is silent... scanning API.")

        time.sleep(15)
        st.rerun()
    except Exception as e:
        time.sleep(5)
        
