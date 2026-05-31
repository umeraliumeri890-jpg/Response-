import streamlit as st
from anthropic import Anthropic

# 1. Page Configuration & Premium Dark Interface
st.set_page_config(page_title="AI Chat Assistant", page_icon="🤖", layout="centered")

st.markdown("""
    <style>
    /* Chat layout styling */
    .stChatInputContainer { padding-bottom: 20px; }
    .stChatMessage { border-radius: 15px; padding: 15px; margin-bottom: 12px; }
    </style>
""", unsafe_allow_html=True)

st.title("🤖 My Live AI Assistant")
st.caption("Powered by Claude Opus via Orbit Provider")
st.write("---")

# 2. Integration of Your Exact Config Environment
BASE_URL = "https://api.orbit-provider.com/api/provider/agy"
API_KEY = "sk-orbit-4b14b4b695719576c852d12de2c3b2ab"  
MODEL_NAME = "claude-opus-4-7"                       

# Initialize Anthropic client
client = Anthropic(
    base_url=BASE_URL,
    api_key=API_KEY
)

# 3. Session State Maintenance (Chat History)
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar Actions
if st.sidebar.button("🗑️ Clear Chat History"):
    st.session_state.messages = []
    st.rerun()

# System Prompt for Claude Opus Behavior
SYSTEM_PROMPT = "You are a helpful, brilliant, and adaptive AI assistant. Respond with clear formatting."

# Display existing chat history logs on screen
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 4. User Chat Input & Claude Opus Real-Time Streaming
if user_input := st.chat_input("Ask me anything..."):
    
    # Show user message instantly
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # AI Response Window
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # Calling the new model with dynamic streaming
            with client.messages.stream(
                model=MODEL_NAME,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
            ) as stream:
                for text in stream.text_stream:
                    full_response += text
                    # Real-time update with cursor block
                    message_placeholder.markdown(full_response + "▌")
            
            # Static clean text layout once done
            message_placeholder.markdown(full_response)
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
            full_response = "Sorry, system response generate nahi kar saka. Please backend keys check karein."
            message_placeholder.markdown(full_response)

    # SECURE LINE: Save final response to browser state memory correctly
    st.session_state.messages.append({"role": "assistant", "content": full_response})
          
