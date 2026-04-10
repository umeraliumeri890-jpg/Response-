import streamlit as st
import pandas as pd
import requests
import time
import plotly.express as px

# --- CONFIG ---
URL = "http://51.77.216.195/crapi/lamix/viewstats"
TOKEN = "SVdVRTRSQmiGX4FWYJJzgF-Hi4mHX41TglBhWVtieEOEUHhleGFy"

st.set_page_config(page_title="HUNTING RADAR - UMER ALI", layout="wide")

# Custom CSS for a "Hacker/Professional" Look
st.markdown("""
<style>
    .stApp { background-color: #050505; color: #00ff00; }
    .reportview-container .main .block-container { padding-top: 2rem; }
    .metric-card { 
        background-color: #111; 
        border: 1px solid #00ff00; 
        padding: 15px; 
        border-radius: 10px; 
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>🎯 HUNTING RADAR AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 20px;'>Market Intelligence by <b>Umer Ali</b></p>", unsafe_allow_html=True)
st.divider()

placeholder = st.empty()

while True:
    try:
        # Global Data Fetch (Zyada records mangwaein ge market trend ke liye)
        r = requests.get(URL, params={"token": TOKEN, "records": 200})
        if r.status_code == 200:
            data = r.json().get("data", [])
            df = pd.DataFrame(data)
            
            if not df.empty:
                # 1. App Analysis
                app_counts = df['cli'].value_counts().reset_index()
                app_counts.columns = ['App', 'Count']
                top_app = app_counts.iloc[0]['App']
                
                # 2. Country/Prefix Analysis
                df['Prefix'] = df['num'].astype(str).str[:2]
                prefix_counts = df['Prefix'].value_counts().head(5)

                with placeholder.container():
                    # Top Stats Row
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"<div class='metric-card'><h3>🔥 HOT APP</h3><h2 style='color:white;'>{top_app}</h2></div>", unsafe_allow_html=True)
                    with col2:
                        st.markdown(f"<div class='metric-card'><h3>⚡ SYSTEM SPEED</h3><h2 style='color:white;'>{len(df)} OTPs / min</h2></div>", unsafe_allow_html=True)
                    with col3:
                        st.markdown(f"<div class='metric-card'><h3>🌍 TOP PREFIX</h3><h2 style='color:white;'>+{prefix_counts.index[0]}</h2></div>", unsafe_allow_html=True)

                    st.markdown("### 📊 Market Trends (Live)")
                    
                    graph_col1, graph_col2 = st.columns(2)
                    with graph_col1:
                        # Pie Chart for Apps
                        fig = px.pie(app_counts.head(8), values='Count', names='App', title="Apps Success Share",
                                     color_discrete_sequence=px.colors.sequential.Greens_r, hole=0.3)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with graph_col2:
                        # Bar Chart for Countries
                        st.write("**Top Active Country Routes**")
                        st.bar_chart(prefix_counts)

                    st.divider()
                    st.success(f"💡 **STRATEGY:** Is waqt **{top_app}** aur prefix **+{prefix_counts.index[0]}** sabse fast hain. Team ko idhar lagao!")

            else:
                st.info("Market data scanning... Please wait.")

        time.sleep(15)
        st.rerun()
    except Exception as e:
        time.sleep(5)
                      
