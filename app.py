import streamlit as st
import pandas as pd
import sqlite3
import subprocess
import os
import time
import asyncio
from python_scripts.database_manager import get_connection, initialize_db, clear_logs
from python_scripts.ai_utils import generate_with_retry, generate_image_dalle
from python_scripts.vector_engine import vector_engine

# 1. Page Configuration
st.set_page_config(
    page_title="Digital FTE Orchestrator",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SESSION STATE GUARD: INITIALIZATION ---
if 'initialized' not in st.session_state:
    initialize_db()
    clear_logs()
    st.session_state.initialized = True
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Hassan Bhai, setup ready hai. Aaj konsi e-commerce post queue karni hai?"}]
    if "show_chat" not in st.session_state:
        st.session_state.show_chat = False
    # Conversation state for step-by-step product info collection
    if "conv_state" not in st.session_state:
        st.session_state.conv_state = {
            "collecting_info": False,
            "step": 0,  # 0=none, 1=asking_name, 2=asking_features, 3=asking_price
            "product_name": "",
            "features": "",
            "price": "",
            "generated_caption": ""
        }

# --- STYLED CSS ---
st.markdown("""
    <style>
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    
    /* Floating Chat Trigger */
    .chat-trigger {
        position: fixed;
        bottom: 30px;
        right: 30px;
        width: 60px;
        height: 60px;
        background-color: #3b82f6;
        color: white;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 28px;
        cursor: pointer;
        z-index: 1001;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
        border: none;
        transition: transform 0.2s;
    }
    .chat-trigger:hover {
        transform: scale(1.1);
    }

    /* Premium Glassmorphism Panel */
    .chat-panel {
        backdrop-filter: blur(15px);
        background: rgba(255, 255, 255, 0.05);
        border-left: 1px solid rgba(255, 255, 255, 0.1);
        padding: 25px;
        height: 100vh;
        display: flex;
        flex-direction: column;
        color: #f8fafc;
    }
    
    .chat-header {
        font-size: 1.5rem;
        font-weight: 800;
        color: #18181b; /* Zinc-900 effect */
        background: #f4f4f5;
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 20px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    .main-dashboard {
        max-height: 95vh;
        overflow-y: auto;
        padding: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE CACHING ---
# ... (rest of caching code remains same)

@st.cache_data(ttl=10)
def get_cached_metrics():
    try:
        conn = get_connection()
        l_count = pd.read_sql_query("SELECT COUNT(*) FROM leads", conn).iloc[0,0]
        c_count = pd.read_sql_query("SELECT COUNT(*) FROM campaigns WHERE status='ready_to_post'", conn).iloc[0,0]
        r_count = pd.read_sql_query("SELECT COUNT(*) FROM leads WHERE status='ready_to_whatsapp'", conn).iloc[0,0]
        conn.close()
        return l_count, c_count, r_count
    except:
        return 0, 0, 0

@st.cache_data(ttl=5)
def get_cached_leads():
    try:
        conn = get_connection()
        df = pd.read_sql_query("SELECT platform, handle, message, status, timestamp FROM leads ORDER BY timestamp DESC LIMIT 50", conn)
        conn.close()
        return df
    except:
        return pd.DataFrame()

# 2. Sidebar: Health & Systems
with st.sidebar:
    st.title("🛡️ Digital FTE")
    st.markdown("---")
    
    # System Controls
    if st.button("🚀 LAUNCH ALL SYSTEMS", use_container_width=True, type="primary"):
        subprocess.Popen(["python", "python_scripts/instagram_watcher.py"])
        subprocess.Popen(["python", "python_scripts/facebook_watcher.py"])
        subprocess.Popen(["python", "python_scripts/master_orchestrator.py"])
        subprocess.Popen(["python", "python_scripts/whatsapp_poster.py"])
        st.toast("System sequence initiated.")
    
    st.markdown("---")
    st.subheader("🌐 Platform Health")
    platforms = {"Instagram": "instagram_session/state.json", "Facebook": "facebook_session/state.json", "WhatsApp": "whatsapp_session/browser_data"}
    for name, path in platforms.items():
        if os.path.exists(path): st.success(f"{name}: Connected")
        else: st.error(f"{name}: Disconnected")

    st.markdown("---")
    # CHATBOT TOGGLE IN SIDEBAR
    st.subheader("🤖 FTE Assistant")
    if st.button("Toggle Assistant", use_container_width=True, type="primary"):
        st.session_state.show_chat = not st.session_state.show_chat
        st.rerun()

# --- FLOATING TRIGGER ---
st.markdown('<div class="chat-trigger">', unsafe_allow_html=True)
if st.button("🤖", key="floating_chat_toggle"):
    st.session_state.show_chat = not st.session_state.show_chat
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# --- MAIN LAYOUT LOOP ---
if st.session_state.get("show_chat", False):
    col_main, col_chat = st.columns([0.7, 0.3], gap="medium")
else:
    col_main = st.container()
    col_chat = None

# --- COLUMN 1: DASHBOARD ---
with col_main:
    st.markdown('<div class="main-dashboard">', unsafe_allow_html=True)
    st.title("🚀 Digital FTE: Command Center")

    # Metrics
    l_count, c_count, r_count = get_cached_metrics()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Leads", l_count)
    m2.metric("Active Campaigns", c_count)
    m3.metric("WhatsApp Queue", r_count)
    m4.metric("System Status", "Online")

    st.markdown("---")

    # Functional Tabs
    tab_leads, tab_studio, tab_inventory, tab_logs = st.tabs(["📊 Leads Engine", "🎨 Creative Studio", "📦 Inventory", "📝 Diagnostics"])

    with tab_leads:
        st.subheader("📋 Active Lead Management")
        df_leads = get_cached_leads()
        if not df_leads.empty:
            st.dataframe(df_leads, use_container_width=True, hide_index=True)
        else:
            st.info("No leads detected yet.")

    with tab_studio:
        st.subheader("✨ AI Campaign Engine")
        with st.form("campaign_form"):
            p_name = st.text_input("Product Title")
            p_price = st.number_input("Listing Price", min_value=0.0)
            p_feat = st.text_area("Key Features")
            if st.form_submit_button("Generate Campaign"):
                st.info("Generating content...")

    with tab_inventory:
        st.subheader("📦 Inventory Hub")
        st.write("Inventory tracking active.")

    with tab_logs:
        st.subheader("📝 Live Diagnostics")
        st.write("System healthy.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- COLUMN 2: SLIDE-IN PANEL (Premium UI) ---
if col_chat:
    with col_chat:
        st.markdown('<div class="chat-panel">', unsafe_allow_html=True)
        st.markdown('<div class="chat-header">🤖 Digital FTE Assistant</div>', unsafe_allow_html=True)
        
        chat_container = st.container(height=650)
        with chat_container:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            
            # Draft Preview inside the Glassmorphism Panel
            if st.session_state.conv_state["generated_caption"]:
                st.markdown("---")
                st.caption("📝 **Draft Preview**")
                final_caption = st.text_area("Edit Caption", value=st.session_state.conv_state["generated_caption"], height=150)
                st.session_state.conv_state["generated_caption"] = final_caption
                c1, c2, c3 = st.columns(3)
                if c1.button("IG", use_container_width=True): st.toast("IG Queued")
                if c2.button("FB", use_container_width=True): st.toast("FB Queued")
                if c3.button("LI", use_container_width=True): st.toast("LI Queued")

        if prompt := st.chat_input("Baat karein...", key="panel_chat_input"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            user_input = prompt.lower().strip()
            
            # 1. Premium Greeting Logic
            if user_input in ["hi", "hello", "hey", "salam"]:
                st.session_state.conv_state.update({"collecting_info": False, "step": 0, "generated_caption": ""})
                response = "Assalam-o-Alaikum Hassan Bhai! Ready to scale? What are we launching today?"
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.rerun()

            # 2. Handle Step-by-Step Info Gathering
            if st.session_state.conv_state["collecting_info"]:
                step = st.session_state.conv_state["step"]
                if step == 1: # Asking Price
                    st.session_state.conv_state.update({"product_name": prompt, "step": 2})
                    response = "Price kya rakhni hai?"
                elif step == 2: # Asking Features
                    st.session_state.conv_state.update({"price": prompt, "step": 3})
                    response = "3 bullet features bata dein?"
                elif step == 3: # Finalizing
                    st.session_state.conv_state.update({"features": prompt, "collecting_info": False, "step": 0})
                    async def generate_caption():
                        cap_prompt = f"Create a viral Hinglish caption for {st.session_state.conv_state['product_name']}. Price: {st.session_state.conv_state['price']}. Features: {st.session_state.conv_state['features']}."
                        return await generate_with_retry(cap_prompt)
                    st.session_state.conv_state["generated_caption"] = asyncio.run(generate_caption())
                    response = "Perfect! Draft ready hai. Preview check karein."
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.rerun()

            # 3. Intent Check for Product Mentions
            async def detect_intent(p, history):
                intent_prompt = f"History: {history}\nUser: '{p}'. Is user mentioning a product? Answer 'PRODUCT' or 'CHAT'."
                res = await generate_with_retry(intent_prompt)
                return "PRODUCT" in res.upper()

            history_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-3:]])
            is_product = asyncio.run(detect_intent(prompt, history_text)) or (len(user_input.split()) <= 3 and user_input not in ["ok", "yes", "no"])
            
            if is_product:
                st.session_state.conv_state["collecting_info"] = True
                if len(user_input.split()) <= 3: # Likely product name
                    st.session_state.conv_state.update({"product_name": prompt, "step": 2})
                    response = "Price kya rakhni hai?"
                else: # Sent a longer sentence
                    st.session_state.conv_state["step"] = 1
                    response = "Sahi hai! Product ka naam kya hai?"
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.rerun()

            # 4. RAG Chat
            async def get_response(p):
                context = vector_engine.query(p)
                rag_prompt = f"Context: {context}\nUser: {p}\nAnswer in Hinglish."
                return await generate_with_retry(rag_prompt)
            
            response = asyncio.run(get_response(prompt))
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)
