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
import streamlit.components.v1 as components

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
st.markdown("Interactive tool to calculate and visualise mortgage payments.")
st.markdown('</div>', unsafe_allow_html=True)

# Display Bitmoji image
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("assets/mortgage-calculator_DALL_E.png", width=250)
    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Load defaults from file
defaults, default_overpayments = load_defaults()

# Check if we have at least 2 interest rates for counterfactual analysis
interest_rates = defaults.get('interest_rates', [])
show_counterfactual = len(interest_rates) >= 2

# Create tabs for standard calculator, overpayment calculator, and potentially counterfactual
if show_counterfactual:
    standard_tab, overpayment_tab, counterfactual_tab, about_tab = st.tabs(["Standard Calculator", "Overpayment Calculator", "Rate Change Analysis", "About"])
else:
    standard_tab, overpayment_tab, about_tab = st.tabs(["Standard Calculator", "Overpayment Calculator", "About"])

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

# Function to display Buy Me A Coffee widget
def buy_me_coffee_widget():
    components.html(
        """
        <script data-name="BMC-Widget" data-cfasync="false" src="https://cdnjs.buymeacoffee.com/1.0.0/widget.prod.min.js" data-id="zurdo" data-description="Support me on Buy me a coffee!" data-message="Buy me a slice of pizza! 🍕" data-color="#40DCA5" data-position="Right" data-x_margin="18" data-y_margin="18"></script>
        """,
        scrolling=False,
        height=600
    )

with about_tab:
    st.markdown("""
    <br>
    <p> ❤️ this app? See below how you can support me! </p>
            
    ---

    <h2>About the App</h2>
    <p>This mortgage calculator is a Streamlit app that allows you to calculate and visualize mortgage payments. 
    You can compare different scenarios, including overpayments and changes in interest rates over time.</p>
    
    <h3>Features</h3>
    <ul>
        <li>Calculate mortgage payments with different interest rates and overpayments</li>
        <li>Visualise the payment schedule, including principal, interest, and remaining balance</li>
        <li>Compare scenarios with different interest rates over time</li>
    </ul>
    
    <h3>How to Use</h3>
    <p>Use the sidebar to adjust the mortgage parameters, such as loan amount, interest rate, and overpayments. 
    You can also switch between different tabs to explore the standard calculator, overpayment calculator, and counterfactual analysis.</p>
    
    <h3>Source Code</h3>
    <p>The source code for this app is available on <a href=https://github.com/elzurdo/mortgage-calculator>GitHub</a>. </p
                
    --- 
                """, unsafe_allow_html=True)

    # Display Bitmoji image
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("assets/kazin_bitmoji_computer.png", width=250)
        st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("""
    <h2>About the Creator</h2>
    <p>Hi 👋 I'm Eyal. My superpower is simplifying the complex and turning data to ta-da! 🪄 I'm a DS/ML researcher and communicator as well as an ex-cosmologist with ❤️ for applied stats.</p>
    <p>I made this app for my own purposes but I'm glad to share with anybody who finds it useful.</p>
                For feedback please contact me via <a href="https://www.linkedin.com/in/eyal-kazin/">LinkedIn</a>.
                <br>
    <h3>Support</h3>
    <p>If you find this app helpful, consider supporting me by:
                
    <ul>
    <li>Buying me a <a href="https://buymeacoffee.com/zurdo">slice of pizza! 🍕</a> (Or scroll below for my `buymecoffee` widget.) </li>
    <li>Reading any of my <a href="https://eyal-kazin.medium.com/">Medium</a> articles. I mostly write about applied stats in data science and machine learning, but not limited to!</li>

    </ul> </p>
                
                """, unsafe_allow_html=True)
    

    buy_me_coffee_widget()

# Footer
st.markdown("""
<div style="margin-top: 3rem; text-align: center; color: #666;">
    <p>This calculator is for educational purposes only. Actual mortgage terms and conditions may vary.</p>
</div>
""", unsafe_allow_html=True)