import streamlit as st
import requests
import pandas as pd
import time
import plotly.express as px
import phonenumbers
from phonenumbers import geocoder

# --- CONFIG ---
URL = "http://51.77.216.195/crapi/lamix/viewstats"
TOKEN = "SVdVRTRSQmiGX4FWYJJzgF-Hi4mHX41TglBhWVtieEOEUHhleGFy"

st.set_page_config(page_title="GLOBAL HUNTING RADAR", layout="wide")

# Stylish Hacker UI
st.markdown("""
<style>
    .stApp { background-color: #050505; color: #00ff00; }
    .metric-card { 
        background-color: #111; 
        border: 1px solid #444; 
        padding: 15px; 
        border-radius: 10px; 
        text-align: center;
        box-shadow: 0px 0px 10px #00ff00;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>🎯 GLOBAL HUNTING RADAR AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Intelligence Engine by <b>Umer Ali</b></p>", unsafe_allow_html=True)

# Function to get Country Name from ANY Number
def get_country_name(phone_num):
    try:
        # Number ke shuru mein + add karna zaroori hai identification ke liye
        full_num = "+" + str(phone_num).strip()
        parsed_num = phonenumbers.parse(full_num)
        country = geocoder.description_for_number(parsed_num, "en")
        return country if country else "Unknown Region"
    except:
        return "Unknown Route"

placeholder = st.empty()

while True:
    try:
        r = requests.get(URL, params={"token": TOKEN, "records": 300}) # 300 records for deep analysis
        if r.status_code == 200:
            data = r.json().get("data", [])
            df = pd.DataFrame(data)
            
            if not df.empty:
                # 1. World-Wide Country Identification
                df['Country'] = df['num'].apply(get_country_name)
                
                # 2. Analytics
                app_counts = df['cli'].value_counts().reset_index()
                country_counts = df['Country'].value_counts().reset_index()
                country_counts.columns = ['Country', 'Count']
                
                top_app = app_counts.iloc[0]['cli']
                top_country = country_counts.iloc[0]['Country']

                with placeholder.container():
                    # Top Dashboard Metrics
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown(f"<div class='metric-card'><h3>🔥 DOMINANT APP</h3><h1 style='color:white;'>{top_app}</h1></div>", unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"<div class='metric-card'><h3>🌍 TOP COUNTRY</h3><h1 style='color:white;'>{top_country}</h1></div>", unsafe_allow_html=True)
                    with c3:
                        st.markdown(f"<div class='metric-card'><h3>📊 DATA SCAN</h3><h1 style='color:white;'>{len(df)} OTPs</h1></div>", unsafe_allow_html=True)

                    st.divider()

                    # Charts
                    g1, g2 = st.columns(2)
                    with g1:
                        st.subheader("📱 Global App Share")
                        fig_app = px.pie(app_counts.head(10), values='count', names='cli', hole=0.5,
                                        color_discrete_sequence=px.colors.sequential.Greens_r)
                        st.plotly_chart(fig_app, use_container_width=True)
                    
                    with g2:
                        st.subheader("🏁 Top 15 Active Countries")
                        fig_country = px.bar(country_counts.head(15), x='Count', y='Country', orientation='h',
                                           color='Count', color_continuous_scale='Greens')
                        st.plotly_chart(fig_country, use_container_width=True)

                    # Hunting Recommendation
                    st.success(f"🚀 **HUNTING SIGNAL:** Is waqt market mein **{top_country}** ke numbers par **{top_app}** sabse zyada hit ho raha hai. Targets set karo!")

        time.sleep(15)
        st.rerun()
    except Exception as e:
        time.sleep(5)
        
