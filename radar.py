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

st.set_page_config(page_title="HUNTING RADAR - GLOBAL LIVE", layout="wide")

# Stylish UI
st.markdown("""
<style>
    .stApp { background-color: #050505; color: #00ff00; }
    .report-box { 
        background-color: #111; border: 1px solid #00ff00; 
        padding: 20px; border-radius: 15px; margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Country Identifier Function
def get_country(num):
    try:
        full_num = "+" + str(num).strip()
        parsed = phonenumbers.parse(full_num)
        name = geocoder.description_for_number(parsed, "en")
        return name if name else "Unknown"
    except: return "Unknown"

st.markdown("<h1 style='text-align: center;'>📡 LIVE GLOBAL MONITOR & ANALYZER</h1>", unsafe_allow_html=True)

# SEARCH BOX (Sirf Report ke liye)
target_app = st.text_input("🔍 Check Specific App Performance (e.g. telegram, google):", "whatsapp").strip().lower()

placeholder = st.empty()

while True:
    try:
        r = requests.get(URL, params={"token": TOKEN, "records": 1000})
        if r.status_code == 200:
            data = r.json().get("data", [])
            df = pd.DataFrame(data)
            
            if not df.empty:
                df['dt'] = pd.to_datetime(df['dt'])
                latest_time = df['dt'].max()
                
                # --- LOGIC 1: TARGETED APP REPORT ---
                df_target = df[df['cli'].str.contains(target_app, case=False, na=False)].copy()
                
                # Calculate Counts
                c5 = len(df_target[df_target['dt'] >= (latest_time - timedelta(minutes=5))])
                c10 = len(df_target[df_target['dt'] >= (latest_time - timedelta(minutes=10))])
                c30 = len(df_target[df_target['dt'] >= (latest_time - timedelta(minutes=30))])
                
                # Identify Countries for Target App (Top 3)
                if not df_target.empty:
                    df_target['Country'] = df_target['num'].head(20).apply(get_country) # Performance ke liye top 20 scan
                    top_countries = df_target['Country'].value_counts().head(3).index.tolist()
                    countries_str = ", ".join(top_countries)
                else:
                    countries_str = "No Data"

                # --- LOGIC 2: LIVE FEED (ALL APPS) ---
                # Hum niche saari apps ki live monitoring dikhayenge
                df_live = df.head(40).copy() # Latest 40 messages of ALL apps
                df_live['Country'] = df_live['num'].apply(get_country)

                with placeholder.container():
                    # TOP SECTION: TARGETED REPORT
                    st.markdown(f"""
                    <div class="report-box">
                        <h3 style="color:#00ff00; margin-top:0;">📊 {target_app.upper()} INTELLIGENCE</h3>
                        <p><b>Last 5 Mins:</b> {c5} OTPs | <b>Last 10 Mins:</b> {c10} | <b>Last 30 Mins:</b> {c30}</p>
                        <p><b>🌍 Top Countries for {target_app}:</b> <span style="color:white;">{countries_str}</span></p>
                    </div>
                    """, unsafe_allow_html=True)

                    # BOTTOM SECTION: LIVE FEED (ALL APPS)
                    st.subheader("🚀 LIVE GLOBAL FEED (All Apps)")
                    display_df = df_live[['dt', 'cli', 'num', 'Country', 'message']]
                    display_df.columns = ['Time', 'App/Site', 'Number', 'Country', 'Message']
                    st.table(display_df)

            else:
                st.info("Scanning Market...")

        time.sleep(15)
        st.rerun()
    except Exception as e:
        time.sleep(5)
