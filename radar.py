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

st.set_page_config(page_title="HUNTING RADAR - 5AM FIX", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #050505; color: #00ff00; }
    .report-box { 
        background-color: #111; border: 1px solid #00ff00; 
        padding: 20px; border-radius: 15px; margin-bottom: 20px;
        box-shadow: 0px 0px 10px #00ff00;
    }
</style>
""", unsafe_allow_html=True)

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

st.title("📡 PRO RADAR (5 AM RESET MODE)")

col_in1, col_in2 = st.columns([2, 1])
with col_in1:
    target_cli = st.text_input("🔍 Search exact CLI (e.g. MYOB, whatsapp):", "MYOB").strip()
with col_in2:
    msg_limit = st.number_input("📥 Live Messages limit:", min_value=1, max_value=500, value=25)

team_numbers = load_team_numbers()
placeholder = st.empty()

while True:
    try:
        # 1-day analysis ke liye 2000+ records
        r = requests.get(URL, params={"token": TOKEN, "records": 2500})
        if r.status_code == 200:
            data = r.json().get("data", [])
            df = pd.DataFrame(data)
            
            if not df.empty:
                df['dt'] = pd.to_datetime(df['dt'])
                now = datetime.now()

                # --- CUSTOM 5 AM RESET LOGIC ---
                # Agar abhi subah ke 5 nahi baje, to start_time kal subah ka 5 AM hoga
                if now.hour < 5:
                    start_of_day = (now - timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)
                else:
                    start_of_day = now.replace(hour=5, minute=0, second=0, microsecond=0)

                # --- TARGETED CLI REPORT ---
                # Search exact CLI (Case-insensitive matching)
                df_target = df[df['cli'].str.contains(target_cli, case=False, na=False)].copy()
                
                # Filter accurate time intervals
                c5 = len(df_target[df_target['dt'] >= (now - timedelta(minutes=5))])
                c10 = len(df_target[df_target['dt'] >= (now - timedelta(minutes=10))])
                c30 = len(df_target[df_target['dt'] >= (now - timedelta(minutes=30))])
                # Shift Wise Count (Since 5:00 AM)
                c_shift = len(df_target[df_target['dt'] >= start_of_day])
                
                # Countries
                if not df_target.empty:
                    df_target['Country'] = df_target['num'].head(50).apply(get_country)
                    top_regions = df_target['Country'].value_counts().head(3).index.tolist()
                    regions_str = ", ".join(top_regions)
                else:
                    regions_str = "No Data"

                # --- LIVE FEED ---
                df_live = df.head(msg_limit).copy()
                df_live['Country'] = df_live['num'].apply(get_country)

                with placeholder.container():
                    st.markdown(f"""
                    <div class="report-box">
                        <h2 style="color:#00ff00; margin-top:0;">📊 CLI Report: {target_cli.upper()}</h2>
                        <table style="width:100%; color:white; font-size:20px;">
                            <tr>
                                <td><b>5m:</b> {c5}</td>
                                <td><b>10m:</b> {c10}</td>
                                <td><b>30m:</b> {c30}</td>
                                <td style="color:#00ff00;"><b>Today (Since 5AM):</b> {c_shift}</td>
                            </tr>
                        </table>
                        <p style="margin-top:10px;">🌍 <b>Main Regions:</b> {regions_str}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    st.subheader(f"🚀 Live Feed (Last {msg_limit} Records)")
                    
                    def style_rows(row):
                        if str(row['Number']) in team_numbers:
                            return ['background-color: #1d3557; color: #ffb703; font-weight: bold'] * len(row)
                        return [''] * len(row)

                    display_df = df_live[['dt', 'cli', 'num', 'Country', 'message']]
                    display_df.columns = ['Time', 'App (CLI)', 'Number', 'Country', 'Message']
                    st.table(display_df.style.apply(style_rows, axis=1))

            else:
                st.info("Searching data...")

        time.sleep(15)
        st.rerun()
    except Exception as e:
        time.sleep(5)
                
