import streamlit as st
import os
from rag_engine import initialize_vector_store, get_calculation_explanation

st.set_page_config(page_title="Siebel Calculation Explainer", layout="wide")

st.title("Siebel Process & Calculation Explainer")
st.markdown("Upload your formula documents and input the core values to generate an explanation of the underlying calculations.")

# --- SIDEBAR: Document Management ---
with st.sidebar:
    st.header("1. Knowledge Base")
    uploaded_files = st.file_uploader("Upload Formula/Policy Documents", accept_multiple_files=True, type=["pdf", "txt"])
    if st.button("Process Documents"):
        if uploaded_files:
            # Save files temporarily to the data folder
            if not os.path.exists("data"):
                os.makedirs("data")
            for file in uploaded_files:
                with open(os.path.join("data", file.name), "wb") as f:
                    f.write(file.getbuffer())
            
            with st.spinner("Building Vector Store..."):
                st.session_state.vector_store = initialize_vector_store()
            st.success("Knowledge Base Ready!")
        else:
            st.warning("Please upload documents first.")

if 'vector_store' not in st.session_state:
    st.session_state.vector_store = None

# --- MAIN LAYOUT: Columns ---
col1, col2 = st.columns([1, 1.2])

# LEFT COLUMN: Simplified Input UI
with col1:
    st.subheader("Calculation Inputs")
    st.markdown("Enter the required variables for the formula.")
    
    with st.container(border=True):
        daily_liability = st.number_input("Daily Liability (£)", value=18.71, format="%.2f")
        no_of_periods = st.number_input("Number of Periods", value=1, step=1)
        no_of_days_income = st.number_input("Number of Days Income", value=7, step=1)

# RIGHT COLUMN: AI Output
with col2:
    st.subheader("System Explanation")
    
    if st.button("Explain Calculations", type="primary"):
        if st.session_state.vector_store is None:
            st.error("Please upload and process formula documents in the sidebar first.")
        else:
            # Format the streamlined inputs to send to the LLM
            siebel_data_string = f"""
            - Daily Liability: £{daily_liability}
            - Number of Periods: {no_of_periods}
            - Number of Days Income: {no_of_days_income}
            """
            
            with st.spinner("Retrieving formulas and calculating..."):
                try:
                    explanation = get_calculation_explanation(
                        st.session_state.vector_store, 
                        siebel_data_string
                    )
                    st.markdown("### Step-by-Step Breakdown")
                    st.write(explanation)
                except Exception as e:
                    st.error(f"An error occurred: {e}")