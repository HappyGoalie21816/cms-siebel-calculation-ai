import streamlit as st
import os
from rag_engine import initialize_vector_store, get_calculation_explanation

FORMULAS = {
    "OGM": {"name": "Operational Growth Metric", "vars": ["Daily Liability", "Number of Days", "Number of Periods"]},
    "ENPAM": {"name": "Extended Non-Resident Parent Arrears Matrix", "vars": ["Base Daily Arrears", "Total Days Delinquent", "Assessment Cycles"]},
    "SMCA": {"name": "Standard Maintenance Clawback Assessment", "vars": ["Daily Overpayment Threshold", "Non-Compliance Windows", "Operational Alignment Blocks"]},
    "EECP": {"name": "Escalated Enforcement Collection Premium", "vars": ["Daily Field Levy", "Active Tracking Window", "Enforcement Tier Index"]},
    "BLLR": {"name": "Backdated Legal Liability Reconciliation", "vars": ["Daily Valuation Variance", "Historical Term Count", "Statutory Settlement Windows"]},
    "PPSS": {"name": "Pro-Rata Public Sector Service Surcharge", "vars": ["Daily Processing Cost", "Tracking Run Duration", "Active Interface Batches"]},
    "PPDP": {"name": "Managed Promise-to-Pay Default Penalty", "vars": ["Daily Breach Fine", "Days Since Expiry", "Scheduled Installment Count"]},
    "DIVA": {"name": "Dynamic Income Variation Assessment Fee", "vars": ["Daily Tracking Surcharge", "Audit Window Days", "Reporting Assessment Blocks"]},
    "IAAI": {"name": "Inter-Agency Asset Intercept Fine", "vars": ["Daily Intercept Cost", "Asset Isolation Period", "Enforcement Run Quantums"]},
    "CPCA": {"name": "Mitigated Care Provider Credit Allocation", "vars": ["Daily Care Credit Rate", "Eligible Co-Parenting Days", "Allocation Schedule Intervals"]},
    "SCHAM": {"name": "Special Circumstance Hardship Abatement Metric", "vars": ["Daily Relief Factor", "Certified Injury Days", "Active Payment Schedules"]},
    "FEARC": {"name": "Foreign Exchange Asset Remittance Charge", "vars": ["Daily Conversion Overhead", "Clearing Window Count", "Cross-Border Remittance Terms"]},
    "ACRL": {"name": "Automated Case Re-Registration Levy", "vars": ["Daily Processing Overhead", "Readjustment Window", "Validation Check Blocks"]},
    "DDCI": {"name": "Delayed Disclosure Compounding Interest", "vars": ["Daily Punitive Penalty", "Non-Disclosure Days", "Formal Reporting Intervals"]},
    "EDAS": {"name": "Employer Deduction Order Admin Surcharge", "vars": ["Daily Payroll Handling Surcharge", "Execution Span Days", "Active Pay Cycles"]},
    "CRLA": {"name": "Closed-Case Residual Liability Assessment", "vars": ["Daily Archive Maintenance Unit", "Retention Tracking Span", "Statutory Review Cycles"]},
    "MCCM": {"name": "Multi-Case Consolidation Credit Matrix", "vars": ["Daily Consolidation Credit", "Overlapping Case Days", "Active Client Accounts"]},
    "CCYA": {"name": "Complex Capital Asset Yield Adjustment", "vars": ["Daily Imputed Asset Revenue", "Financial Year Run", "Capital Assessment Waves"]},
    "PVRT": {"name": "Retroactive Paternity Verification Recovery Token", "vars": ["Daily Restitution Rate", "Erroneous Payment Window", "Reconciliation Eras"]},
    "HELS": {"name": "Higher-Tier Education Expense Liability Surcharge", "vars": ["Daily Academic Support Factor", "Semester Tracking Term", "Institutional Billing Blocks"]},
    "SBRA": {"name": "System-Wide Batch Reconciliation Adjustment", "vars": ["Daily Rounding Residual", "Database Processing Interval", "Macro Batch Run Units"]},
}

st.set_page_config(page_title="Siebel Calculation Explainer", layout="wide", initial_sidebar_state="collapsed")

# Injecting Custom CSS for Siebel UI Look
siebel_css = """
<style>
    /* Main Background and general font */
    .stApp {
        background-color: #f0f8ff; /* Alice Blue for a brighter, airy feel */
    }
    
    html, body, [class*="st-"] {
        font-family: 'Segoe UI', Tahoma, Arial, sans-serif !important;
        color: #1a202c !important;
        font-size: 14px !important;
    }
    
    /* Headers */
    h1 {
        font-size: 24px !important;
        font-weight: 800 !important;
        color: #2b6cb0 !important; /* Brighter blue */
        border-bottom: 3px solid #63b3ed;
        margin-bottom: 20px !important;
        padding-bottom: 10px !important;
    }
    
    h3 {
        font-size: 16px !important;
        font-weight: 700 !important;
        color: #2c5282 !important;
        background: linear-gradient(135deg, #ebf8ff, #bee3f8);
        padding: 10px 15px !important;
        border-radius: 6px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #90cdf4;
        margin-top: 15px !important;
        margin-bottom: 15px !important;
    }
    
    /* Input fields */
    .stNumberInput > div > div > input, .stTextInput > div > div > input, .stSelectbox > div > div > div {
        background-color: #ffffff !important;
        border: 2px solid #cbd5e0 !important;
        color: #1a202c !important;
        font-size: 14px !important;
        padding: 8px 12px !important;
        min-height: 36px !important;
        height: 40px !important;
        border-radius: 6px !important;
        transition: border-color 0.2s ease;
    }
    .stNumberInput > div > div > input:focus, .stTextInput > div > div > input:focus, .stSelectbox > div > div > div:focus {
        border-color: #3182ce !important;
        box-shadow: 0 0 0 1px #3182ce;
    }
    
    /* Input Labels */
    .stNumberInput label p, .stTextInput label p, .stSelectbox label p {
        font-size: 13px !important;
        color: #4a5568 !important;
        font-weight: 600 !important;
        margin-bottom: 6px !important;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(to right, #3182ce, #2b6cb0) !important;
        border: none !important;
        color: #ffffff !important;
        font-size: 14px !important;
        padding: 8px 16px !important;
        min-height: 36px !important;
        height: 40px !important;
        font-weight: 700;
        border-radius: 6px !important;
        cursor: pointer;
        box-shadow: 0 4px 6px rgba(49, 130, 206, 0.2);
        transition: transform 0.1s ease, box-shadow 0.1s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(to right, #4299e1, #3182ce) !important;
        transform: translateY(-1px);
        box-shadow: 0 6px 8px rgba(49, 130, 206, 0.3);
    }
    
    /* Hide Streamlit top padding and menus */
    .block-container {
        padding-top: 2rem !important;
        max-width: 1200px !important;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Container styling */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
        background-color: transparent;
        padding: 0px;
    }
</style>
"""
st.markdown(siebel_css, unsafe_allow_html=True)

col_logo, col_title = st.columns([1, 4])
with col_logo:
    try:
        st.image("logo.png", use_container_width=True)
    except FileNotFoundError:
        st.warning("Please save 'logo.png' in the root directory.", icon="⚠️")
with col_title:
    st.markdown("<h1>Child Maintenance Service<br/><span style='font-size:18px; color:#4a5568;'>Calculation Engine & Explainer</span></h1>", unsafe_allow_html=True)

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
col1, col2 = st.columns([2.5, 1.2])

with col1:
    st.markdown("<h3>Calculation Module Selection</h3>", unsafe_allow_html=True)
    selected_acronym = st.selectbox("Select Rule Matrix Component:", options=list(FORMULAS.keys()), format_func=lambda x: f"{x} - {FORMULAS[x]['name']}")
    
    st.markdown("<h3>Input Parameters</h3>", unsafe_allow_html=True)
    formula_data = FORMULAS[selected_acronym]
    v1_name = formula_data['vars'][0]
    v2_name = formula_data['vars'][1]
    v3_name = formula_data['vars'][2]
    
    subcol1, subcol2, subcol3 = st.columns(3)
    with subcol1:
        val1 = st.number_input(f"{v1_name}:", value=0.00, format="%.2f")
    with subcol2:
        val2 = st.number_input(f"{v2_name}:", value=0.00, format="%.2f")
    with subcol3:
        val3 = st.number_input(f"{v3_name}:", value=1.00, format="%.2f")
        
    st.markdown("<h3>Local Calculation Result</h3>", unsafe_allow_html=True)
    
    #st.info("Formulas are natively evaluated as: `(Variable 1 × Variable 2) / Variable 3`", icon="ℹ️")
    
    if val3 == 0:
        st.error(f"Validation Error: '{v3_name}' cannot be zero (Null Pointer/Divide-by-zero prevention).")
        computed_result = None
    else:
        computed_result = (val1 * val2) / val3
        st.success(f"**{selected_acronym} Computed Value:** {computed_result:,.2f}")

with col2:
    # Custom styling for the AI Copilot widget
    st.markdown("""
        <div style='background: linear-gradient(to bottom, #1e293b, #0f172a); padding: 15px; border-radius: 8px; color: white; border: 1px solid #334155; box-shadow: 0px 4px 12px rgba(0,0,0,0.3); height: 100%; margin-top: 10px;'>
            <h3 style='color: #38bdf8 !important; background: transparent !important; border: none !important; margin-bottom: 5px !important; padding: 0px !important;'>🤖 AI Copilot Explainer</h3>
            <p style='font-size: 11px; color: #94a3b8; margin-bottom: 15px;'>Select a component to learn how it is calculated according to the Siebel Rule Matrix context.</p>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("Explain Current Formula ✨", use_container_width=True):
        if st.session_state.vector_store is None:
            st.error("Vector store not initialized.")
        else:
            prompt_input = f"""
            Target Component: {formula_data['name']} ({selected_acronym})
            Provided Variables:
            - {v1_name}: {val1}
            - {v2_name}: {val2}
            - {v3_name}: {val3}
            Calculated Result: {computed_result}
            """
            with st.spinner("AI is analyzing the rule matrix..."):
                try:
                    explanation = get_calculation_explanation(
                        st.session_state.vector_store, 
                        prompt_input
                    )
                    st.markdown("""
                        <div style='background-color: #f8fafc; padding: 15px; border-left: 4px solid #38bdf8; border-radius: 4px; color: #334155; margin-top: 15px; font-size: 13px; box-shadow: 0px 2px 5px rgba(0,0,0,0.05);'>
                    """, unsafe_allow_html=True)
                    st.write(explanation)
                    st.markdown("</div>", unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"An error occurred: {e}")