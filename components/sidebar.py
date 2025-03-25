import streamlit as st
from dateutil.relativedelta import relativedelta
import datetime

def render_sidebar(defaults):
    """Render the sidebar with all input parameters"""
    st.header("Mortgage Parameters")
    
    # Move currency selection to sidebar
    currency = st.radio("Select Currency", ["£", "$"], index=0 if defaults['currency'] == '£' else 1)
    
    # Add start date picker
    start_date = st.date_input(
        "Mortgage Start Date",
        value=defaults['start_date'],
        help="The date when your mortgage begins"
    )
    
    loan_amount = st.number_input(
        f"Loan Amount ({currency})",
        min_value=1000,
        max_value=10000000,
        value=defaults['loan_amount'],
        step=10000,
        format="%d"
    )
    
    # Years and months inputs
    years = st.number_input(
        "Loan Term (Years)",
        min_value=1,
        max_value=40,
        value=defaults['years'],
        step=1
    )
    
    months = st.number_input(
        "Additional Months",
        min_value=0,
        max_value=11,
        value=defaults['months'],
        step=1
    )
    
    # Calculate total months
    total_months = years * 12 + months
    
    # Interest rate management
    interest_rates = defaults.get('interest_rates', [])
    json_has_multiple_rates = len(interest_rates) > 1
    
    # Initialize interest rates in session state if not already there
    if 'interest_rates' not in st.session_state:
        # If JSON file has multiple rates, use those
        if json_has_multiple_rates:
            st.session_state.interest_rates = interest_rates.copy()
        # Otherwise, initialize with single rate
        else:
            st.session_state.interest_rates = [{
                'rate': defaults['interest_rate'],
                'start_date': defaults['start_date']
            }]
    
    # Use either the multi-rate UI or the single rate slider
    interest_rate, multiple_rates = _handle_interest_rates(json_has_multiple_rates, start_date, total_months, defaults, interest_rates)
    
    # Optional extra payment
    extra_payment = st.number_input(
        f"Additional Monthly Payment ({currency})",
        min_value=0,
        max_value=10000,
        value=defaults['extra_payment'],
        step=100
    )
    
    # Reset button
    if st.button("Reset to Defaults", key="reset_core_defaults"):
        loan_amount = defaults['loan_amount']
        interest_rate = defaults['interest_rate']
        years = defaults['years']
        months = defaults['months']
        extra_payment = defaults['extra_payment']
        start_date = defaults['start_date']

    # Add info about defaults file
    with st.expander("Custom Defaults"):
        st.write("""
        To set your own default values, create a file named `mortgage_defaults.json` in the same directory as this app with the following format:
        ```json
        {
            "loan_amount": 300000,
            "interest_rate": 4.0,
            "years": 25,
            "months": 0,
            "extra_payment": 0,
            "currency": "£",
            "start_date": "2023-01-01"
        }
        ```
        The app will automatically load your custom defaults when it starts.
        """)
    
    return {
        'currency': currency,
        'start_date': start_date,
        'loan_amount': loan_amount,
        'years': years,
        'months': months,
        'total_months': total_months,
        'interest_rate': interest_rate,
        'extra_payment': extra_payment,
        'multiple_rates': multiple_rates
    }

def _handle_interest_rates(json_has_multiple_rates, start_date, total_months, defaults, interest_rates):
    """Handle interest rate UI (single or multiple rates)"""
    
    def add_interest_rate():
        # Add a new rate that starts 1 year after the start date
        new_date = st.session_state.interest_rates[-1]['start_date'] + relativedelta(years=1)
        st.session_state.interest_rates.append({
            'rate': st.session_state.interest_rates[-1]['rate'],
            'start_date': new_date
        })
    
    def remove_interest_rate(index):
        if index > 0:  # Don't remove the first rate
            st.session_state.interest_rates.pop(index)
    
    multiple_rates = False
    # Show either the single rate slider or multiple rates UI
    if json_has_multiple_rates:
        # If rates are defined in JSON, just show a message
        st.info("Interest rates are defined in the mortgage_defaults.json file and cannot be changed via the UI.")
        
        # Display the interest rates from the JSON
        import pandas as pd
        rates_df = pd.DataFrame([
            {"Period": i+1, "Rate": f"{rate['rate']}%", "Start Date": rate['start_date'].strftime('%Y-%m-%d')}
            for i, rate in enumerate(interest_rates)
        ]).set_index("Period")
        
        st.dataframe(rates_df)
        
        # Use the JSON rates for calculations
        interest_rate = defaults['interest_rate']  # Keep initial rate for compatibility
        multiple_rates = True
        
    else:
        # Check if we're in multi-rate mode
        using_multiple_rates = len(st.session_state.interest_rates) > 1
        
        if not using_multiple_rates:
            # Show the standard single rate slider
            interest_rate = st.slider(
                "Annual Interest Rate (%)",
                min_value=0.1,
                max_value=15.0,
                value=defaults['interest_rate'],
                step=0.1
            )
            
            # Update the session state with the slider value
            st.session_state.interest_rates[0]['rate'] = interest_rate
            
            # Button to add more rates
            if st.button("Add more interest rates"):
                # Add a second rate a year after the first
                add_interest_rate()
                st.rerun()
                
        else:
            # We're in multi-rate mode - show UI for managing rates
            st.subheader("Interest Rates")
            
            for i, rate_info in enumerate(st.session_state.interest_rates):
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    # First rate's date is always the mortgage start date
                    if i == 0:
                        st.info(f"Start Date: {rate_info['start_date'].strftime('%Y-%m-%d')}")
                    else:
                        # For subsequent rates, allow date selection
                        min_date = st.session_state.interest_rates[i-1]['start_date'] + relativedelta(months=1)
                        max_date = start_date + relativedelta(months=total_months)
                        
                        new_date = st.date_input(
                            f"Start Date for Rate {i+1}",
                            value=rate_info['start_date'],
                            min_value=min_date,
                            max_value=start_date + relativedelta(months=total_months),
                            key=f"rate_date_{i}"
                        )
                        st.session_state.interest_rates[i]['start_date'] = new_date
                
                with col2:
                    new_rate = st.number_input(
                        f"Rate {i+1} (%)",
                        min_value=0.1,
                        max_value=15.0,
                        value=float(rate_info['rate']),
                        step=0.05,
                        key=f"rate_value_{i}"
                    )
                    st.session_state.interest_rates[i]['rate'] = new_rate
                
                with col3:
                    # Allow removing all rates except the first one
                    if i > 0:
                        st.write("")  # For vertical alignment
                        st.button("Remove", key=f"remove_rate_{i}", on_click=remove_interest_rate, args=(i,))
            
            # Button to add another rate
            if st.button("Add Another Rate", key="add_rate_btn"):
                add_interest_rate()
                
            # Button to revert to single rate
            if st.button("Use Single Rate"):
                st.session_state.interest_rates = [{
                    'rate': st.session_state.interest_rates[0]['rate'],
                    'start_date': st.session_state.interest_rates[0]['start_date']
                }]
                st.rerun()
            
            # Use the first rate for standard calculations
            interest_rate = st.session_state.interest_rates[0]['rate']
            
            # Flag that we're using multiple rates
            multiple_rates = True
    
    return interest_rate, multiple_rates
