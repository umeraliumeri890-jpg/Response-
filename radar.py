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

st.set_page_config(page_title="HUNTING RADAR PRO", layout="wide")

# Stylish UI & Highlight CSS
st.markdown("""
<style>
    .stApp { background-color: #050505; color: #00ff00; }
    .report-box { 
        background-color: #111; border: 1px solid #00ff00; 
        padding: 20px; border-radius: 15px; margin-bottom: 20px;
        box-shadow: 0px 0px 15px #00ff00;
    }
</style>
""", unsafe_allow_html=True)

# Helper: Get Country Name
def get_country(num):
    try:
        full_num = "+" + str(num).strip()
        parsed = phonenumbers.parse(full_num)
        return geocoder.description_for_number(parsed, "en")
    except: return "Global"

# Helper: Load Team Numbers
@st.cache_data
def load_team_numbers():
    try:
        df = pd.read_csv(TEAM_FILE)
        return df['Phone Number'].astype(str).tolist()
    except: return []

st.title("🎯 UMER ALI - ADVANCED HUNTING RADAR")

# --- INPUT SECTION ---
col_in1, col_in2 = st.columns([2, 1])
with col_in1:
    target_cli = st.text_input("🔍 Search exact CLI (App Name):", "whatsapp").strip().lower()
with col_in2:
    msg_limit = st.number_input("📥 Live Messages to show:", min_value=1, max_value=500, value=20)

team_numbers = load_team_numbers()
placeholder = st.empty()

while True:
    try:
        # 1-day analysis ke liye zyada records fetch karna
        r = requests.get(URL, params={"token": TOKEN, "records": 2000})
        if r.status_code == 200:
            data = r.json().get("data", [])
            df = pd.DataFrame(data)
            
            if not df.empty:
                df['dt'] = pd.to_datetime(df['dt'])
                latest_time = df['dt'].max()
                
                # --- 1: TARGETED CLI REPORT ---
                # API ke 'cli' column se filter
                df_target = df[df['cli'].str.contains(target_cli, case=False, na=False)].copy()
                
                c5 = len(df_target[df_target['dt'] >= (latest_time - timedelta(minutes=5))])
                c10 = len(df_target[df_target['dt'] >= (latest_time - timedelta(minutes=10))])
                c30 = len(df_target[df_target['dt'] >= (latest_time - timedelta(minutes=30))])
                c1d = len(df_target[df_target['dt'] >= (latest_time - timedelta(days=1))])
                
                # Top Countries for this CLI
                if not df_target.empty:
                    df_target['Country'] = df_target['num'].head(50).apply(get_country)
                    top_countries = df_target['Country'].value_counts().head(3).index.tolist()
                    countries_str = ", ".join(top_countries)
                else:
                    countries_str = "None"

                # --- 2: LIVE FEED PREPARATION ---
                df_live = df.head(msg_limit).copy()
                df_live['Country'] = df_live['num'].apply(get_country)

                with placeholder.container():
                    # THE STATS BOX
                    st.markdown(f"""
                    <div class="report-box">
                        <h2 style="color:#00ff00; margin-top:0;">📊 CLI Report for: {target_cli.upper()}</h2>
                        <table style="width:100%; color:white; font-size:18px;">
                            <tr>
                                <td><b>Last 5m:</b> {c5}</td>
                                <td><b>Last 10m:</b> {c10}</td>
                                <td><b>Last 30m:</b> {c30}</td>
                                <td><b>Last 24h:</b> {c1d}</td>
                            </tr>
                        </table>
                        <p style="margin-top:10px;">🌍 <b>Top Countries (from CLI):</b> <span style="color:#00ff00;">{countries_str}</span></p>
                    </div>
                    """, unsafe_allow_html=True)

                    # LIVE FEED TABLE
                    st.subheader(f"🚀 Last {msg_limit} Global Live Messages")
                    
                    # Highlighting Function
                    def style_team_rows(row):
                        is_team = str(row['Number']) in team_numbers
                        if is_team:
                            return ['background-color: #1d3557; color: #ffb703; font-weight: bold'] * len(row)
                        return [''] * len(row)

                    display_df = df_live[['dt', 'cli', 'num', 'Country', 'message']]
                    display_df.columns = ['Time', 'App (CLI)', 'Number', 'Country', 'Message']
                    
                    # Render Table
                    st.table(display_df.style.apply(style_team_rows, axis=1))

            else:
                st.info("API is online, but no data found.")

        time.sleep(15)
        st.rerun()
    except Exception as e:
        time.sleep(5)
                    
