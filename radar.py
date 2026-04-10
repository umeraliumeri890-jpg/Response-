import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta

# --- CONFIG ---
URL = "http://51.77.216.195/crapi/lamix/viewstats"
TOKEN = "SVdVRTRSQmiGX4FWYJJzgF-Hi4mHX41TglBhWVtieEOEUHhleGFy"

st.set_page_config(page_title="HUNTING RADAR - LIVE FEED", layout="wide")

st.markdown("<h1 style='text-align: center; color: #00ff00;'>🎯 TARGET SCANNER & LIVE FEED</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Powered by <b>Umer Ali</b></p>", unsafe_allow_html=True)

# User Input
target_app = st.text_input("Enter App Name to Track (e.g. whatsapp, telegram, google):", "whatsapp").strip().lower()

placeholder = st.empty()

while True:
    try:
        # 500 records fetch kar rahe hain taake history mil sake
        r = requests.get(URL, params={"token": TOKEN, "records": 500})
        if r.status_code == 200:
            data = r.json().get("data", [])
            df = pd.DataFrame(data)
            
            if not df.empty:
                df['dt'] = pd.to_datetime(df['dt'])
                now = datetime.now()

                # Targeted App Filter
                df_app = df[df['cli'].str.contains(target_app, case=False, na=False)].copy()

                # Stats Calculation
                m5_df = df_app[df_app['dt'] >= (now - timedelta(minutes=5))]
                count_5m = len(m5_df)
                count_10m = len(df_app[df_app['dt'] >= (now - timedelta(minutes=10))])
                count_30m = len(df_app[df_app['dt'] >= (now - timedelta(minutes=30))])

                with placeholder.container():
                    # --- SECTION 1: METRICS ---
                    st.subheader(f"📊 {target_app.upper()} Performance Stats")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Last 5 Mins", f"{count_5m} OTPs")
                    c2.metric("Last 10 Mins", f"{count_10m} OTPs")
                    c3.metric("Last 30 Mins", f"{count_30m} OTPs")
                    
                    st.divider()

                    # --- SECTION 2: LIVE 5-MINUTE MESSAGES ---
                    st.subheader(f"📨 Live Messages (Last 5 Minutes)")
                    
                    if not m5_df.empty:
                        # Sirf zaroori columns dikhana
                        display_df = m5_df[['dt', 'num', 'message']].sort_values(by='dt', ascending=False)
                        
                        # Table ko thora stylish dikhane ke liye
                        st.table(display_df) 
                    else:
                        st.info(f"Pichle 5 minute mein {target_app} ka koi naya message nahi aaya.")

                    # --- SECTION 3: SYSTEM ALERT ---
                    if count_5m > 15:
                        st.success(f"🚀 **FAST TRACK:** {target_app.upper()} is hitting hard! Get active.")
                    elif count_5m > 0:
                        st.warning(f"⚡ **STABLE:** {target_app.upper()} route is working.")
                    else:
                        st.error(f"😴 **DEAD ROUTE:** No recent activity on {target_app.upper()}.")

            else:
                st.info("Market data scanning...")

        time.sleep(15) # 15 seconds refresh rate perfect hai
        st.rerun()
    except Exception as e:
        time.sleep(5)
    
