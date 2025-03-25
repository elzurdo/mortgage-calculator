import streamlit as st
import pandas as pd
import datetime

# Import utility functions
from utils.file_utils import load_defaults
from utils.style_loader import load_css
from utils.date_utils import format_date

# Import components
from components.sidebar import render_sidebar
from components.tabs.standard_tab import render_standard_tab
from components.tabs.overpayment_tab import render_overpayment_tab
from components.tabs.counterfactual_tab import render_counterfactual_tab

# Set page configuration
st.set_page_config(
    page_title="Mortgage Calculator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
load_css()

# Header
st.markdown('<div class="header-container">', unsafe_allow_html=True)
st.title("Mortgage Calculator")
st.markdown("Interactive tool to calculate and visualise mortgage payments")
st.markdown('</div>', unsafe_allow_html=True)


# Load defaults from file
defaults, default_overpayments = load_defaults()

# Check if we have at least 2 interest rates for counterfactual analysis
interest_rates = defaults.get('interest_rates', [])
show_counterfactual = len(interest_rates) >= 2

# Create tabs for standard calculator, overpayment calculator, and potentially counterfactual
if show_counterfactual:
    standard_tab, overpayment_tab, counterfactual_tab = st.tabs(["Standard Calculator", "Overpayment Calculator", "Rate Change Analysis"])
else:
    standard_tab, overpayment_tab = st.tabs(["Standard Calculator", "Overpayment Calculator"])

# Sidebar with inputs
with st.sidebar:
    params = render_sidebar(defaults)

# Get the active interest rates to use for calculations
if params['multiple_rates']:
    active_interest_rates = st.session_state.interest_rates
else:
    active_interest_rates = [{'rate': params['interest_rate'], 'start_date': params['start_date']}]

# Standard Calculator Tab
with standard_tab:
    render_standard_tab(params, active_interest_rates)

# Overpayment Calculator Tab
with overpayment_tab:
    render_overpayment_tab(params, active_interest_rates, default_overpayments)

# Counterfactual Analysis Tab (if we have multiple rates)
if show_counterfactual:
    with counterfactual_tab:
        render_counterfactual_tab(params, active_interest_rates)

# Footer
st.markdown("""
<div style="margin-top: 3rem; text-align: center; color: #666;">
    <p>This calculator is for educational purposes only. Actual mortgage terms and conditions may vary.</p>
</div>
""", unsafe_allow_html=True)