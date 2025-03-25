import streamlit as st
import os

def load_css():
    """Load custom CSS styles"""
    css_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'styles', 'main.css')
    try:
        with open(css_file, 'r') as f:
            css = f.read()
            
        st.markdown(f"""
        <style>
        {css}
        </style>
        """, unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Error loading CSS file: {e}")
        
        # Fallback to basic CSS
        st.markdown("""
        <style>
        .header-container {
            padding: 1rem 0;
            margin-bottom: 2rem;
            border-bottom: 1px solid #f0f0f0;
        }
        h1 {
            color: #1E3A8A;
        }
        .overpayment-card {
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 1rem;
            margin-bottom: 1rem;
            border-left: 3px solid #4CAF50;
        }
        </style>
        """, unsafe_allow_html=True)
