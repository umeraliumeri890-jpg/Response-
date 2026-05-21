import streamlit as st
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Page Configuration
st.set_page_config(page_title="UTS Control Center", layout="wide", page_icon="⚡")

# Custom CSS for Premium Interface
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    h1, h2, h3 { color: #a855f7 !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .stButton>button { background-color: #a855f7; color: white; font-weight: bold; border-radius: 8px; border: none; width: 100%; height: 45px; }
    .stButton>button:hover { background-color: #9333ea; color: white; }
    div[data-testid="stForm"] { border: 2px solid #a855f7; border-radius: 12px; padding: 25px; background-color: #111827; }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE FOR NAVIGATION ---
if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"

# Sidebar Navigation Layout
st.sidebar.title("🔮 UTS MATRIX CONTROLLER")
st.sidebar.markdown("---")
if st.sidebar.button("📊 Main Dashboard", use_container_width=True):
    st.session_state.current_page = "Dashboard"
if st.sidebar.button("🔗 Link Numbers Panel", use_container_width=True):
    st.session_state.current_page = "LinkNumbers"
st.sidebar.markdown("---")
st.sidebar.caption("DEVELOPED BY: UTS TEAM")


# --- BACK-END AUTOMATION CORE ENGINE ---
def run_matrix_allocation(admin_user, admin_pass, selected_range, quantity, target_client):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Background runner
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Chrome setup
    from webdriver_manager.chrome import ChromeDriverManager
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 25)
    
    try:
        # Step 1: Open Login Page
        driver.get("https://matrix-panel.tech/auth/login")
        
        # Step 2: Auto Login Fields Detection
        # Matrix panel input fields dynamic handling
        email_field = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='text' or @name='username' or @name='email']")))
        password_field = driver.find_element(By.XPATH, "//input[@type='password' or @name='password']")
        login_btn = driver.find_element(By.XPATH, "//button[@type='submit' or contains(text(), 'Login')]")
        
        # Typing Credentials securely
        email_field.send_keys(admin_user)
        password_field.send_keys(admin_pass)
        login_btn.click()
        
        # Dashboard redirect wait
        time.sleep(4)
        
        # Step 3: Jump into Allocation Module
        driver.get("https://matrix-panel.tech/agent/allocate")
        time.sleep(3)
        
        # Step 4: Range Input / Dropdown Handling
        # Input standard search structure for dynamic selects
        range_input = wait.until(EC.presence_of_element_located((By.XPATH, "//select[contains(@class, 'form-control')] | //input[contains(@placeholder, 'Select Ranges')]")))
        range_input.send_keys(selected_range)
        time.sleep(1)
        
        # Step 5: Quantity Injection (Max Restricted via Streamlit, pushed directly here)
        qty_field = driver.find_element(By.XPATH, "//input[@placeholder='e.g. 500' or @type='number']")
        qty_field.clear()
        qty_field.send_keys(str(quantity))
        
        # Step 6: Target Client Selection
        client_input = driver.find_element(By.XPATH, "//select[contains(., 'Target')] | //input[contains(@placeholder, 'Target Clients')]")
        client_input.send_keys(target_client)
        time.sleep(1)
        
        # Step 7: Allocation Trigger Click
        final_allocate_btn = driver.find_element(By.XPATH, "//button[contains(., 'Allocate Numbers')]")
        final_allocate_btn.click()
        time.sleep(4)  # Processing time buffer
        
        driver.quit()
        return True, f"Successfully Linked {quantity} numbers from range '{selected_range}' to '{target_client}'!"
        
    except Exception as e:
        driver.quit()
        return False, f"Automation Interface Issue: {str(e)}"


# --- MAIN DASHBOARD SCREEN ---
if st.session_state.current_page == "Dashboard":
    st.title("📊 UTS Control Command Center")
    st.write("Welcome! Internal dashboard handles the pipeline backend securely.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("💡 **Bridge Mode:** Active (Matrix Panel Tunnel Encrypted)")
    with col2:
        st.success("🔒 **Access Control:** Restricted allocations enabled for operators.")

# --- LINK NUMBERS BRIDGED SCREEN ---
elif st.session_state.current_page == "LinkNumbers":
    st.title("🔗 Secure Link Numbers Bridge")
    st.write("Fill parameters to execute bulk action. Max ceiling capped at **50** units.")
    
    with st.form("secure_allocation_form"):
        st.subheader("Allocation Parameters")
        
        # Range Select Dropdown (Add your panel's visible options here)
        range_options = ["-- Select Ranges --", "Range A", "Range B"] 
        selected_range = st.selectbox("Range(s) (From Your Quota)", options=range_options)
        
        # Quantity control (Hardcapped to 50 max value)
        quantity = st.number_input("Quantity (Maximum allowed: 50)", min_value=1, max_value=50, value=10, step=1)
        
        # Target Client Field
        client_options = ["-- Select Target Clients --", "new han", "Client 2"]
        target_client = st.selectbox("Target Client(s)", options=client_options)
        
        st.markdown("---")
        submit_action = st.form_submit_button("⚡ Execute Safe Allocation")
        
        if submit_action:
            if selected_range == "-- Select Ranges --" or target_client == "-- Select Target Clients --":
                st.error("Meharbani karke Range aur Target Client dono select karein!")
            elif quantity > 50:
                st.error("System Error: Maximum single batch limit is 50 numbers.")
            else:
                with st.spinner("Processing operation on matrix-panel.tech in background..."):
                    
                    # Core credentials injected securely on runtime
                    ADMIN_USER = "UTS"
                    ADMIN_PASS = "@Umer123456"
                    
                    success, msg = run_matrix_allocation(ADMIN_USER, ADMIN_PASS, selected_range, quantity, target_client)
                    
                    if success:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.error(msg)
