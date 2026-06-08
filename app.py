import streamlit as st
import os
from rag_engine import initialize_vector_store, get_calculation_explanation

st.set_page_config(page_title="Siebel Calculation Explainer", layout="wide", initial_sidebar_state="collapsed")

# Injecting Custom CSS for Siebel UI Look
siebel_css = """
<style>
    /* Main Background and general font */
    .stApp {
        background-color: #d1e0ec; /* Siebel light blue/grey */
    }
    
    html, body, [class*="st-"] {
        font-family: Tahoma, Arial, sans-serif !important;
        color: #000000 !important;
        font-size: 11px !important;
    }
    
    /* Headers */
    h1 {
        font-size: 14px !important;
        font-weight: bold !important;
        color: #003366 !important;
        border-bottom: 2px solid #a3c2e0;
        margin-bottom: 10px !important;
        padding-bottom: 5px !important;
    }
    
    h3 {
        font-size: 12px !important;
        font-weight: bold !important;
        color: #000000 !important;
        background: linear-gradient(to bottom, #dbe8f4, #b5cbe0);
        padding: 4px 8px !important;
        border-top: 1px solid #ffffff;
        border-left: 1px solid #ffffff;
        border-right: 1px solid #7a9cbe;
        border-bottom: 1px solid #7a9cbe;
        margin-top: 0px !important;
        margin-bottom: 10px !important;
    }
    
    /* Input fields */
    .stNumberInput > div > div > input, .stTextInput > div > div > input, .stSelectbox > div > div > div {
        background-color: #eaf1f8 !important;
        border: 1px solid #a5b6c7 !important;
        color: #000000 !important;
        font-size: 11px !important;
        padding: 2px 4px !important;
        min-height: 20px !important;
        height: 22px !important;
        box-shadow: inset 1px 1px 2px rgba(0,0,0,0.1);
        border-radius: 0 !important;
    }
    
    /* Input Labels */
    .stNumberInput label p, .stTextInput label p, .stSelectbox label p {
        font-size: 11px !important;
        color: #000000 !important;
        font-weight: normal !important;
        margin-bottom: 2px !important;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(to bottom, #f0f5fa, #d1e0ec) !important;
        border: 1px solid #7a9cbe !important;
        color: #003366 !important;
        font-size: 11px !important;
        padding: 2px 10px !important;
        min-height: 22px !important;
        height: 24px !important;
        font-weight: bold;
        border-radius: 0 !important; /* Siebel has square buttons */
    }
    .stButton > button:hover {
        background: linear-gradient(to bottom, #d1e0ec, #b5cbe0) !important;
    }
    
    /* Hide Streamlit top padding and menus */
    .block-container {
        padding-top: 20px !important;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Container styling to look like Siebel applets */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
        background-color: transparent;
        padding: 0px;
    }
    
    /* Expander/Explanation area */
    .stMarkdown p, .stMarkdown li {
        font-size: 11px !important;
    }
</style>
"""
st.markdown(siebel_css, unsafe_allow_html=True)

st.markdown("<h1>Siebel Process & Calculation Explainer</h1>", unsafe_allow_html=True)

def get_data_mtime():
    data_path = "data/"
    if not os.path.exists(data_path): return 0
    mtimes = [os.path.getmtime(os.path.join(data_path, f)) for f in os.listdir(data_path) if os.path.isfile(os.path.join(data_path, f))]
    return max(mtimes) if mtimes else 0

current_mtime = get_data_mtime()

# Initialize or rebuild vector store if missing or if data files changed
if 'vector_store' not in st.session_state or st.session_state.get('data_mtime') != current_mtime:
    with st.spinner("Initializing Knowledge Base..."):
        st.session_state.vector_store = initialize_vector_store()
        st.session_state.data_mtime = current_mtime

# --- MAIN LAYOUT: Columns ---
col1, col2, col3 = st.columns([1, 1, 1.5])

# LEFT COLUMN: Simplified Input UI (mimicking Siebel form applet)
with col1:
    st.markdown("<h3>Account Details</h3>", unsafe_allow_html=True)
    st.text_input("From Account:", value="3000534644", disabled=True)
    st.selectbox("Frequency:", ["05-Calendar Monthly", "Weekly", "Bi-Weekly"], disabled=True)
    st.text_input("Response Code:", value="0", disabled=True)
    st.text_input("Response Message:", value="O.K.", disabled=True)

with col2:
    st.markdown("<h3>Liability Schedule Details</h3>", unsafe_allow_html=True)
    st.text_input("Version:", value="3", disabled=True)
    st.text_input("Start Date:", value="14/04/2026", disabled=True)
    daily_liability = st.number_input("Daily Liability Amount:", value=18.71, format="%.2f")
    no_of_periods = st.number_input("No Of Periods:", value=12, step=1)
    no_of_days_income = st.number_input("No Of Days:", value=365, step=1)

# RIGHT COLUMN: AI Output (mimicking a separate applet)
with col3:
    st.markdown("<h3>System Explanation</h3>", unsafe_allow_html=True)
    
    if st.button("Calculate OGM"):
        if st.session_state.vector_store is None:
            st.error("Vector store not initialized.")
        else:
            # Format the streamlined inputs to send to the LLM
            siebel_data_string = f"""
            - Daily Liability: £{daily_liability}
            - Number of Periods: {no_of_periods}
            - Number of Days Income: {no_of_days_income}
            """
            
            with st.spinner("Processing..."):
                try:
                    explanation = get_calculation_explanation(
                        st.session_state.vector_store, 
                        siebel_data_string
                    )
                    st.markdown("**Step-by-Step Breakdown:**")
                    st.write(explanation)
                except Exception as e:
                    st.error(f"An error occurred: {e}")