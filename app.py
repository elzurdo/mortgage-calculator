import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
from dateutil.relativedelta import relativedelta
import json
import os

# Set page configuration
st.set_page_config(
    page_title="Mortgage Calculator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to improve appearance
st.markdown("""
<style>
    .main {
        padding: 2rem;
        max-width: 1200px;
        margin: 0 auto;
    }
    .stRadio > div {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
    }
    .stNumberInput label, .stRadio label, .stSelectbox label {
        font-weight: 600;
    }
    .header-container {
        padding: 1rem 0;
        margin-bottom: 2rem;
        border-bottom: 1px solid #f0f0f0;
    }
    h1 {
        color: #1E3A8A;
    }
    .block-container {
        padding-top: 1rem;
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

# Function to load default parameters from JSON file
def load_defaults():
    # Default parameters if file doesn't exist or contain values
    defaults = {
        'loan_amount': 300000,
        'interest_rate': 4.0,  # Legacy single interest rate (for backward compatibility)
        'interest_rates': [
            {'rate': 4.0, 'start_date': datetime.date.today().replace(day=1).strftime('%Y-%m-%d')}
        ],
        'years': 25,
        'months': 0,
        'extra_payment': 0,
        'currency': '£',
        'start_date': datetime.date.today().replace(day=1).strftime('%Y-%m-%d')  # Format as string
    }
    
    # Path to the defaults file
    defaults_file = os.path.join(os.path.dirname(__file__), 'mortgage_defaults.json')
    
    # Try to load values from file
    try:
        if os.path.exists(defaults_file):
            with open(defaults_file, 'r') as f:
                user_defaults = json.load(f)
                
            # Update defaults with user values
            for key, value in user_defaults.items():
                if key in defaults:
                    defaults[key] = value
            
            # Handle backward compatibility for interest rates
            if 'interest_rate' in user_defaults and 'interest_rates' not in user_defaults:
                # Create interest_rates array with just the single rate starting at start_date
                defaults['interest_rates'] = [
                    {'rate': user_defaults['interest_rate'], 'start_date': defaults['start_date']}
                ]
    except Exception as e:
        st.error(f"Error loading defaults file: {e}")
    
    # Convert start_date back to datetime.date
    if isinstance(defaults['start_date'], str):
        try:
            defaults['start_date'] = datetime.datetime.strptime(defaults['start_date'], '%Y-%m-%d').date()
        except:
            defaults['start_date'] = datetime.date.today().replace(day=1)
    
    # Convert interest rates start dates to datetime.date
    processed_rates = []
    for rate_info in defaults.get('interest_rates', []):
        try:
            # Convert string dates to datetime
            if isinstance(rate_info['start_date'], str):
                start_date = datetime.datetime.strptime(rate_info['start_date'], '%Y-%m-%d').date()
            else:
                start_date = rate_info['start_date']
                
            processed_rates.append({
                'rate': float(rate_info['rate']),
                'start_date': start_date
            })
        except Exception as e:
            # Skip invalid entries
            st.warning(f"Skipping invalid interest rate entry: {e}")
    
    # Sort interest rates by start date
    if processed_rates:
        processed_rates.sort(key=lambda x: x['start_date'])
        defaults['interest_rates'] = processed_rates
    else:
        # If no valid rates, set a default based on the single interest_rate
        defaults['interest_rates'] = [{
            'rate': defaults['interest_rate'],
            'start_date': defaults['start_date']
        }]
    
    # For backward compatibility and UI default, set interest_rate to the first rate
    if defaults['interest_rates']:
        defaults['interest_rate'] = defaults['interest_rates'][0]['rate']
    
    # Load overpayments from separate file if it exists
    overpayments = []
    overpayments_file = os.path.join(os.path.dirname(__file__), 'mortgage_overpayments.json')
    
    try:
        if os.path.exists(overpayments_file):
            with open(overpayments_file, 'r') as f:
                overpayment_data = json.load(f)
                
            if isinstance(overpayment_data, list):
                for op in overpayment_data:
                    if 'date' in op and 'amount' in op:
                        # Convert date string to date object
                        try:
                            op_date = datetime.datetime.strptime(op['date'], '%Y-%m-%d').date()
                            overpayments.append({
                                'date': op_date,
                                'amount': float(op['amount'])
                            })
                        except:
                            # Skip invalid entries
                            pass
    except Exception as e:
        st.warning(f"Error loading overpayments file: {e}")
    
    return defaults, overpayments

# Helper function to get the date for a given month number
def get_payment_date(start_date, month_number):
    return start_date + relativedelta(months=month_number - 1)

# Helper function to format date as YYYY-MM
def format_date(date):
    return date.strftime("%Y-%m")

# Convert payment date to month number based on start date
def payment_date_to_month(payment_date, start_date):
    # Calculate months between dates
    delta = relativedelta(payment_date, start_date)
    return delta.years * 12 + delta.months + 1  # +1 because month 1 is the start month

# Helper function to find the applicable interest rate for a given date
def get_applicable_interest_rate(date, interest_rates):
    # Sort rates by start date (newest to oldest)
    sorted_rates = sorted(interest_rates, key=lambda x: x['start_date'], reverse=True)
    
    # Find the most recent rate that applies (with start_date <= current date)
    for rate_info in sorted_rates:
        if rate_info['start_date'] <= date:
            return rate_info['rate']
    
    # If no applicable rate found, return the earliest one
    return sorted_rates[-1]['rate']

# Calculate amortization schedule with support for one-time overpayments and variable interest rates
def calculate_amortization(loan_amount, interest_rate, total_months, start_date, extra_payment=0, overpayments=None, interest_rates=None):
    # Use interest_rates if provided, otherwise create a single entry from interest_rate
    if interest_rates is None:
        interest_rates = [{'rate': interest_rate, 'start_date': start_date}]
    
    schedule = []
    remaining_balance = loan_amount
    total_interest = 0
    month_counter = 0
    prev_monthly_payment = None
    
    # Initialize overpayments if None
    if overpayments is None:
        overpayments = {}
    
    while remaining_balance > 0 and month_counter < 1000:  # Safety limit
        month_counter += 1
        payment_date = get_payment_date(start_date, month_counter)
        payment_date_str = format_date(payment_date)
        
        # Get the applicable interest rate for this payment date
        applicable_rate = get_applicable_interest_rate(payment_date, interest_rates)
        monthly_interest_rate = applicable_rate / 100 / 12
        
        # Recalculate monthly payment only if the interest rate has changed
        if prev_monthly_payment is None or applicable_rate != schedule[-1].get('Rate', None):
            # Calculate remaining term
            remaining_term = total_months - month_counter + 1
            
            # Calculate new monthly payment based on current balance and remaining term
            if remaining_term > 0:
                monthly_payment = remaining_balance * (monthly_interest_rate * (1 + monthly_interest_rate) ** remaining_term) / ((1 + monthly_interest_rate) ** remaining_term - 1)
            else:
                # Last payment - just pay off the balance plus interest
                monthly_payment = remaining_balance * (1 + monthly_interest_rate)
        else:
            monthly_payment = prev_monthly_payment
        
        # Store for comparison in next iteration
        prev_monthly_payment = monthly_payment
                
        interest_payment = remaining_balance * monthly_interest_rate
        principal_payment = min(monthly_payment - interest_payment + extra_payment, remaining_balance)
        
        # Add any one-time overpayment for this month
        overpayment_amount = overpayments.get(month_counter, 0)
        principal_payment += overpayment_amount
        
        total_payment = interest_payment + principal_payment
        
        total_interest += interest_payment
        remaining_balance -= principal_payment
        
        schedule.append({
            'Month': month_counter,
            'Date': payment_date,
            'Date_Str': payment_date_str,
            'Rate': applicable_rate,
            'Payment': total_payment,
            'Principal': principal_payment,
            'Interest': interest_payment,
            'Total Interest': total_interest,
            'Balance': remaining_balance,
            'Overpayment': overpayment_amount
        })
        
        if remaining_balance <= 0:
            break
    
    return pd.DataFrame(schedule)

# Header
st.markdown('<div class="header-container">', unsafe_allow_html=True)
st.title("Mortgage Calculator")
st.markdown("Interactive tool to calculate and visualise mortgage payments")
st.markdown('</div>', unsafe_allow_html=True)

# Load defaults from file
defaults, default_overpayments = load_defaults()

# Check if we have at least 3 interest rates for counterfactual analysis
interest_rates = defaults.get('interest_rates', [])
show_counterfactual = len(interest_rates) >= 2

# Create tabs for standard calculator, overpayment calculator, and potentially counterfactual
if show_counterfactual:
    standard_tab, overpayment_tab, counterfactual_tab = st.tabs(["Standard Calculator", "Overpayment Calculator", "Rate Change Analysis"])
else:
    standard_tab, overpayment_tab = st.tabs(["Standard Calculator", "Overpayment Calculator"])



# Inputs
with st.sidebar:
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
    
    # Years and months inputs (moved up)
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
    
    # Calculate total months here before using it
    total_months = years * 12 + months
    
    # Check if interest rates are defined in the JSON file
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
    
    # Functions for managing interest rates
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
    
    # Show either the single rate slider or multiple rates UI
    if json_has_multiple_rates:
        # If rates are defined in JSON, just show a message
        st.info("Interest rates are defined in the mortgage_defaults.json file and cannot be changed via the UI.")
        
        # Display the interest rates from the JSON
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
                st.experimental_rerun()
            
            # Use the first rate for standard calculations
            interest_rate = st.session_state.interest_rates[0]['rate']
            
            # Flag that we're using multiple rates
            multiple_rates = True
    
    # Optional extra payment (moved down)
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

# Calculate monthly payment
monthly_interest_rate = interest_rate / 100 / 12
monthly_payment = loan_amount * (monthly_interest_rate * (1 + monthly_interest_rate) ** total_months) / ((1 + monthly_interest_rate) ** total_months - 1)

# Standard Calculator Tab
with standard_tab:
    # Check if we have multiple interest rates defined
    if 'multiple_rates' not in locals():
        # If not set in sidebar, determine here
        multiple_rates = len(interest_rates) > 1
    
    # Use the interest rates from either the JSON file or session state
    if json_has_multiple_rates:
        # Use rates from JSON
        active_interest_rates = interest_rates
    elif 'interest_rates' in st.session_state and len(st.session_state.interest_rates) > 1:
        # Use rates from session state
        active_interest_rates = st.session_state.interest_rates
    else:
        # Single rate
        active_interest_rates = [{'rate': interest_rate, 'start_date': start_date}]
    
    loan_amount_balance =float(loan_amount)
    
    if multiple_rates:
        st.info(f"This mortgage has {len(active_interest_rates)} different interest rate periods defined.")
        
        # Calculate monthly payment for each interest rate period
        rate_data = []
        total_duration_months = 0
        weighted_monthly_payment = 0
        
        for i, rate_info in enumerate(active_interest_rates):
            # Calculate end date for this period
            if i < len(active_interest_rates) - 1:
                end_date = active_interest_rates[i+1]['start_date'] - datetime.timedelta(days=1)
                # Calculate months in this period
                period_months = payment_date_to_month(active_interest_rates[i+1]['start_date'], rate_info['start_date']) - 1
            else:
                end_date = "End of term"
                # For last period, remaining months to complete the term
                period_months = total_months - total_duration_months
            
            # Calculate monthly payment for this period
            period_rate = rate_info['rate'] / 100 / 12
            remaining_term = total_months - total_duration_months
            if remaining_term > 0:
                period_payment = loan_amount_balance * (period_rate * (1 + period_rate) ** remaining_term) / ((1 + period_rate) ** remaining_term - 1)
            else:
                period_payment = 0  # Should not happen, but avoid division by zero

            # subtracting fro the balance what has been payed.
            # TODO: this needs to account for overpayments
            # TODO: add the interst accumulated to the period
            #loan_amount_balance -= period_months * period_payment
                
            # Add to total for weighted average
            weighted_monthly_payment += period_payment * min(period_months, remaining_term)
            total_duration_months += period_months
            
            # Add to table data
            rate_data.append({
                "Period": i + 1,
                "Rate": f"{rate_info['rate']}%",
                "Start Date": rate_info['start_date'].strftime("%Y-%m-%d"),
                "End Date": end_date if isinstance(end_date, str) else end_date.strftime("%Y-%m-%d"),
                "Monthly Payment": f"{currency}{period_payment:.2f}",
                "Estimated Duration": f"{period_months} months"
            })

            
            # Properly simulate amortization for this period by calculating monthly changes
            remaining_balance = float(loan_amount_balance)
            for _ in range(min(period_months, remaining_term)):
                # Calculate interest for this month
                interest_payment = remaining_balance * period_rate
                # Calculate principal for this month (payment minus interest)
                principal_payment = period_payment - interest_payment
                # Update remaining balance
                remaining_balance -= principal_payment
            
            # Update loan balance for next period
            loan_amount_balance = remaining_balance
        
        # Calculate weighted average monthly payment
        if total_duration_months > 0:
            weighted_monthly_payment = weighted_monthly_payment / min(total_duration_months, total_months)
        else:
            weighted_monthly_payment = monthly_payment  # Fallback to simple calculation
        
        # Display enhanced table with payment and duration information
        st.table(pd.DataFrame(rate_data).set_index("Period"))
        
        # Use the multiple interest rates for calculation
        amortization_df = calculate_amortization(
            loan_amount, 
            interest_rate, 
            total_months, 
            start_date, 
            extra_payment, 
            interest_rates=active_interest_rates
        )
        
        # For multiple rates, use weighted average instead of initial payment
        monthly_payment = weighted_monthly_payment
    else:
        # Use the single interest rate calculation
        amortization_df = calculate_amortization(loan_amount, interest_rate, total_months, start_date, extra_payment)
    
    # Calculate summary statistics
    total_payments = amortization_df['Payment'].sum()
    total_interest = amortization_df['Interest'].sum()
    actual_months = len(amortization_df)
    
    # Create dashboard layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Monthly Payment Breakdown")
        
        col_metric1, col_metric2, col_metric3 = st.columns(3)
        
        with col_metric1:
            # Display monthly payment (either weighted average or single rate)
            payment_label = f"{'Average ' if multiple_rates else ''}Monthly Payment ({currency})"
            st.metric(
                label=payment_label,
                value=f"{monthly_payment+extra_payment:.2f}"
            )
        
        with col_metric2:
            # Calculate end date
            end_date = get_payment_date(start_date, actual_months)
            end_date_str = format_date(end_date)
            expected_end_date = get_payment_date(start_date, total_months)
            expected_end_date_str = format_date(expected_end_date)
            
            # Fix: Don't use len() on overpayment_tab (DeltaGenerator object)
            has_overpayments = hasattr(st.session_state, 'overpayments') and len(st.session_state.overpayments) > 0
            
            st.metric(
                label="Loan Duration",
                value=f"{actual_months} months ({end_date_str})",
                delta=f"-{total_months-actual_months} months" if extra_payment > 0 or has_overpayments else None,
                delta_color="normal" if extra_payment > 0 or has_overpayments else "off"
            )
        
        with col_metric3:
            st.metric(
                label=f"Total Interest ({currency})",
                value=f"{total_interest:,.2f}"
            )
        
        # Monthly payment breakdown pie chart
        fig = go.Figure(data=[
            go.Pie(
                labels=['Principal', 'Interest'],
                values=[loan_amount, total_interest],
                hole=0.4,
                marker=dict(colors=['#3366CC', '#FF9900']),
                textinfo='label+percent',
                textposition='inside'
            )
        ])
        
        fig.update_layout(
            title=f"Total Payment Breakdown ({currency}{total_payments:,.2f})",
            height=350,
            margin=dict(t=50, b=0, l=0, r=0)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Amortization Visualization")
        
        # Plotting the amortization data using dates instead of month numbers
        fig = make_subplots(rows=2, cols=1, 
                             subplot_titles=("Principal vs Interest Payments", "Balance Over Time"),
                             vertical_spacing=0.13,
                             row_heights=[0.5, 0.5])
        
        # First subplot: Principal and Interest over time
        fig.add_trace(
            go.Bar(
                x=amortization_df['Date_Str'], 
                y=amortization_df['Principal'],
                name='Principal',
                marker_color='#3366CC'
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=amortization_df['Date_Str'], 
                y=amortization_df['Interest'],
                name='Interest',
                marker_color='#FF9900'
            ),
            row=1, col=1
        )
        
        # Second subplot: Remaining balance
        fig.add_trace(
            go.Scatter(
                x=amortization_df['Date_Str'], 
                y=amortization_df['Balance'],
                name='Remaining Balance',
                fill='tozeroy',
                mode='lines',
                line=dict(color='#4CAF50', width=2)
            ),
            row=2, col=1
        )
        
        fig.update_layout(
            barmode='stack', 
            hovermode='x unified',
            height=500,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            margin=dict(t=60, b=0, l=0, r=0)
        )
        
        fig.update_yaxes(title_text=f"Amount ({currency})", row=1, col=1)
        fig.update_yaxes(title_text=f"Remaining Balance ({currency})", row=2, col=1)
        fig.update_xaxes(title_text="Date", row=2, col=1)
        
        # Update x-axis to show dates
        fig.update_xaxes(
            tickmode='array',
            tickvals=amortization_df['Date_Str'][::12].tolist(),  # Show every 12 months
            ticktext=amortization_df['Date_Str'][::12].tolist(),
            row=1, col=1
        )
        
        fig.update_xaxes(
            tickmode='array',
            tickvals=amortization_df['Date_Str'][::12].tolist(),  # Show every 12 months
            ticktext=amortization_df['Date_Str'][::12].tolist(),
            row=2, col=1
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Display amortization schedule
    st.subheader("Amortization Schedule")
    
    # End date for display
    end_date_str = format_date(get_payment_date(start_date, actual_months))
    
    # Summary statistics
    st.markdown(f"""
    <div style="display: flex; gap: 2rem; margin-bottom: 1rem;">
        <div>
            <strong>Loan Amount:</strong> {currency}{loan_amount:,}
        </div>
        <div>
            <strong>Interest Rate:</strong> {interest_rate}%
        </div>
        <div>
            <strong>Term:</strong> {years} years, {months} months
        </div>
        <div>
            <strong>Start Date:</strong> {format_date(start_date)}
        </div>
        <div>
            <strong>End Date:</strong> {end_date_str}
        </div>
        <div>
            <strong>Total Interest:</strong> {currency}{total_interest:,.2f}
        </div>
        <div>
            <strong>Total Paid:</strong> {currency}{total_payments:,.2f}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Add a download button for the amortization schedule
    csv = amortization_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Amortization Schedule",
        data=csv,
        file_name="mortgage_amortization.csv",
        mime="text/csv",
    )
    
    # Display the first few rows of the schedule with formatting
    display_df = amortization_df.copy()
    display_df = display_df[['Month', 'Date_Str', 'Payment', 'Principal', 'Interest', 'Total Interest', 'Balance']]  # Reorder columns
    display_df.rename(columns={'Date_Str': 'Date'}, inplace=True)  # Rename column
    
    display_df['Payment'] = display_df['Payment'].map(lambda x: f"{currency}{x:.2f}")
    display_df['Principal'] = display_df['Principal'].map(lambda x: f"{currency}{x:.2f}")
    display_df['Interest'] = display_df['Interest'].map(lambda x: f"{currency}{x:.2f}")
    display_df['Total Interest'] = display_df['Total Interest'].map(lambda x: f"{currency}{x:.2f}")
    display_df['Balance'] = display_df['Balance'].map(lambda x: f"{currency}{x:.2f}")
    
    st.dataframe(
        display_df.head(10),
        use_container_width=True,
        hide_index=True
    )
    
    if len(display_df) > 10:
        st.caption(f"Showing 10 of {len(display_df)} months. Download the full schedule using the button above.")

# Overpayment Calculator Tab
with overpayment_tab:
    st.subheader("Overpayments Analysis")
    st.write("Add one-time overpayments to see their impact on your mortgage.")
    
    # Initialize overpayments in session state if not already there
    if 'overpayments' not in st.session_state:
        st.session_state.overpayments = default_overpayments.copy() if default_overpayments else []
    
    # Function to add overpayment
    def add_overpayment():
        # Add a default overpayment at the first payment date
        default_date = start_date + relativedelta(months=0)
        st.session_state.overpayments.append({
            'date': default_date,
            'amount': 1000
        })
    
    # Function to remove overpayment
    def remove_overpayment(index):
        st.session_state.overpayments.pop(index)
    
    # Overpayment input UI
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.write("Enter your one-time overpayments:")
    
    with col2:
        st.button("Add Overpayment", on_click=add_overpayment, key="add_overpayment_btn")
        
    with col3:
        if st.button("Reset to Defaults", key="reset_overpayment_defaults"):
            st.session_state.overpayments = default_overpayments.copy() if default_overpayments else []

    # Add info about defaults file
    with st.expander("Custom Overpayments File"):
        st.write("""
        To set your own default overpayments, create a file named `mortgage_overpayments.json` in the same directory as this app with the following format:
        ```json
        [
            {
                "date": "2023-10-01",
                "amount": 5000
            },
            {
                "date": "2024-01-15",
                "amount": 10000
            }
        ]
        ```
        Each overpayment should have a date (YYYY-MM-DD) and an amount. The app will automatically load these when it starts.
        """)
    
    # Display and edit overpayments
    overpayments_dict = {}
    
    if not st.session_state.overpayments:
        st.info("No overpayments added. Click 'Add Overpayment' to begin.")
    
    for i, op in enumerate(st.session_state.overpayments):
        with st.container():
            st.markdown(f"<div class='overpayment-card'>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                # Use date picker instead of month number
                payment_date = st.date_input(
                    "Payment Date",
                    value=op.get('date', start_date),
                    min_value=start_date,
                    max_value=start_date + relativedelta(months=total_months),
                    key=f"date_{i}"
                )
                st.session_state.overpayments[i]['date'] = payment_date
                
                # Convert date to month number for calculation
                month_num = payment_date_to_month(payment_date, start_date)
                st.session_state.overpayments[i]['month'] = month_num
                
            with col2:
                st.session_state.overpayments[i]['amount'] = st.number_input(
                    f"Amount ({currency})",
                    min_value=100.0,
                    max_value=float(loan_amount),
                    value=float(st.session_state.overpayments[i]['amount']),
                    step=100.0,
                    key=f"amount_{i}"
                )
                
            with col3:
                st.write("")
                st.write("")
                remove_btn = st.button("Remove", key=f"remove_{i}", on_click=remove_overpayment, args=(i,))
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Add to overpayments dictionary using month number
            month = st.session_state.overpayments[i]['month']
            amount = st.session_state.overpayments[i]['amount']
            
            # Handle multiple overpayments in the same month
            if month in overpayments_dict:
                overpayments_dict[month] += amount
            else:
                overpayments_dict[month] = amount
    
    # Calculate amortization with overpayments
    if overpayments_dict:
        # Check if we have multiple interest rates defined
        interest_rates = defaults.get('interest_rates', [])
        multiple_rates = len(interest_rates) > 1
        
        if multiple_rates:
            # Calculate without overpayments for comparison
            baseline_df = calculate_amortization(
                loan_amount, 
                interest_rate, 
                total_months, 
                start_date, 
                extra_payment, 
                interest_rates=interest_rates
            )
            
            # Calculate with overpayments
            overpayment_df = calculate_amortization(
                loan_amount, 
                interest_rate, 
                total_months, 
                start_date, 
                extra_payment, 
                overpayments_dict, 
                interest_rates=interest_rates
            )
        else:
            # Use the single interest rate calculation
            baseline_df = calculate_amortization(loan_amount, interest_rate, total_months, start_date, extra_payment)
            overpayment_df = calculate_amortization(loan_amount, interest_rate, total_months, start_date, extra_payment, overpayments_dict)
            
        baseline_months = len(baseline_df)
        baseline_interest = baseline_df['Interest'].sum()
        overpayment_months = len(overpayment_df)
        overpayment_interest = overpayment_df['Interest'].sum()
        
        # Display impact analysis
        st.subheader("Overpayments Impact Analysis")
        
        # Metrics comparison
        col1, col2, col3 = st.columns(3)
        
        with col1:
            months_saved = baseline_months - overpayment_months
            
            # Calculate new end date
            new_end_date = get_payment_date(start_date, overpayment_months)
            original_end_date = get_payment_date(start_date, baseline_months)
            
            st.metric(
                label="Months Saved",
                value=f"{months_saved}",
                delta=f"{format_date(new_end_date)} vs {format_date(original_end_date)}"
            )
            
        with col2:
            interest_saved = baseline_interest - overpayment_interest
            st.metric(
                label=f"Interest Saved ({currency})",
                value=f"{interest_saved:,.2f}",
                delta=f"-{interest_saved:,.2f}"
            )
            
        with col3:
            total_overpaid = sum(overpayments_dict.values())
            st.metric(
                label=f"Total Overpayments ({currency})",
                value=f"{total_overpaid:,.2f}"
            )
        
        # Comparison visualization
        st.subheader("Balance Comparison")
        
        fig = go.Figure()
        
        # Add baseline trace (without overpayments)
        fig.add_trace(go.Scatter(
            x=baseline_df['Date_Str'],
            y=baseline_df['Balance'],
            name='Without Overpayments',
            line=dict(color='#FF9900', width=2),
            hovertemplate='%{x}<br>Balance: ' + currency + '%{y:,.2f}<br>Rate: %{customdata}%',
            customdata=baseline_df['Rate']
        ))
        
        # Add overpayment trace
        fig.add_trace(go.Scatter(
            x=overpayment_df['Date_Str'],
            y=overpayment_df['Balance'],
            name='With Overpayments',
            line=dict(color='#4CAF50', width=2),
            hovertemplate='%{x}<br>Balance: ' + currency + '%{y:,.2f}<br>Rate: %{customdata}%',
            customdata=overpayment_df['Rate']
        ))
        
        # Add markers for interest rate change points
        if multiple_rates:
            for rate_info in interest_rates[1:]:  # Skip the first one (starting rate)
                rate_date = rate_info['start_date']
                rate_date_str = format_date(rate_date)
                
                # Only add if this date is in our dataset
                if rate_date_str in baseline_df['Date_Str'].values:
                    # Find the balances at this rate change date
                    baseline_balance = baseline_df.loc[baseline_df['Date_Str'] == rate_date_str, 'Balance'].values[0]
                    
                    # Add vertical line at rate change date
                    fig.add_shape(
                        type="line",
                        x0=rate_date_str,
                        y0=0,
                        x1=rate_date_str,
                        y1=baseline_balance,
                        line=dict(color="red", width=1, dash="dash"),
                    )
                    
                    # Add annotation for the rate change
                    fig.add_annotation(
                        x=rate_date_str,
                        y=baseline_balance,
                        text=f"Rate: {rate_info['rate']}%",
                        showarrow=True,
                        arrowhead=1,
                        ax=40,
                        ay=-40
                    )
        
        # Add markers for overpayment points
        for month, amount in overpayments_dict.items():
            # Find the corresponding balance after overpayment
            if month <= len(overpayment_df):
                row = overpayment_df.loc[overpayment_df['Month'] == month]
                if not row.empty:
                    balance = row['Balance'].values[0]
                    date_str = row['Date_Str'].values[0]
                    rate = row['Rate'].values[0]
                    
                    fig.add_trace(go.Scatter(
                        x=[date_str],
                        y=[balance],
                        mode='markers',
                        marker=dict(size=10, color='red'),
                        name=f'Overpayment: {currency}{amount:,.2f}' if month == list(overpayments_dict.keys())[0] else None,
                        showlegend=(month == list(overpayments_dict.keys())[0]),
                        hoverinfo='text',
                        hovertext=f'Date: {date_str}<br>Overpayment: {currency}{amount:,.2f}<br>New Balance: {currency}{balance:,.2f}<br>Rate: {rate}%'
                    ))
        
        # Update x-axis to show select dates
        date_ticks = []
        date_labels = []
        
        # Add yearly ticks
        for i in range(0, len(baseline_df), 12):
            if i < len(baseline_df):
                date_ticks.append(baseline_df['Date_Str'].iloc[i])
                date_labels.append(baseline_df['Date_Str'].iloc[i])
        
        fig.update_layout(
            title="Loan Balance Over Time",
            xaxis_title="Date",
            yaxis_title=f"Balance ({currency})",
            height=400,
            hovermode="closest",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5
            ),
            xaxis=dict(
                tickmode='array',
                tickvals=date_ticks,
                ticktext=date_labels
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Individual overpayment impact
        st.subheader("Individual Overpayment Impact")
        
        for i, (month, amount) in enumerate(overpayments_dict.items()):
            # Calculate scenario with just this overpayment
            single_overpayment = {month: amount}
            
            # Pass the interest_rates to the calculation if multiple rates exist
            if multiple_rates:
                single_op_df = calculate_amortization(
                    loan_amount, 
                    interest_rate, 
                    total_months, 
                    start_date, 
                    extra_payment, 
                    single_overpayment,
                    interest_rates=interest_rates
                )
            else:
                single_op_df = calculate_amortization(
                    loan_amount, 
                    interest_rate, 
                    total_months, 
                    start_date, 
                    extra_payment, 
                    single_overpayment
                )
            
            # Find the payment date for this month
            payment_date = get_payment_date(start_date, month)
            payment_date_str = format_date(payment_date)
            
            single_months_saved = baseline_months - len(single_op_df)
            single_interest_saved = baseline_interest - single_op_df['Interest'].sum()
            
            with st.expander(f"Overpayment {i+1}: {currency}{amount:,.2f} on {payment_date_str}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Months Saved", f"{single_months_saved}")
                    
                with col2:
                    st.metric(f"Interest Saved ({currency})", f"{single_interest_saved:,.2f}")
                
                st.write(f"Return on Investment: {(single_interest_saved/amount)*100:.2f}% (Interest saved as percentage of overpayment)")
        
        # Amortization schedule with overpayments
        st.subheader("Amortization Schedule with Overpayments")
        
        # Add a download button for the overpayment amortization schedule
        csv_overpayment = overpayment_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Overpayment Schedule",
            data=csv_overpayment,
            file_name="mortgage_overpayment_schedule.csv",
            mime="text/csv",
        )
        
        # Display the schedule with formatting
        display_op_df = overpayment_df.copy()
        display_op_df = display_op_df[['Month', 'Date_Str', 'Payment', 'Principal', 'Interest', 'Overpayment', 'Total Interest', 'Balance']]  # Reorder columns
        display_op_df.rename(columns={'Date_Str': 'Date'}, inplace=True)  # Rename column
        
        display_op_df['Payment'] = display_op_df['Payment'].map(lambda x: f"{currency}{x:.2f}")
        display_op_df['Principal'] = display_op_df['Principal'].map(lambda x: f"{currency}{x:.2f}")
        display_op_df['Interest'] = display_op_df['Interest'].map(lambda x: f"{currency}{x:.2f}")
        display_op_df['Total Interest'] = display_op_df['Total Interest'].map(lambda x: f"{currency}{x:.2f}")
        display_op_df['Balance'] = display_op_df['Balance'].map(lambda x: f"{currency}{x:.2f}")
        display_op_df['Overpayment'] = display_op_df['Overpayment'].map(lambda x: f"{currency}{x:.2f}" if x > 0 else "-")
        
        st.dataframe(
            display_op_df.head(10),
            use_container_width=True,
            hide_index=True
        )
        
        if len(display_op_df) > 10:
            st.caption(f"Showing 10 of {len(display_op_df)} months. Download the full schedule using the button above.")

# Counterfactual Analysis Tab
if show_counterfactual:
    with counterfactual_tab:
        st.subheader("Interest Rate Change Impact Analysis")
        st.write("This analysis shows what would happen if the last interest rate change never occurred.")
        
        # Create counterfactual interest rates (without the last rate change)
        counterfactual_rates = interest_rates[:-1].copy()
        
        # Display rate comparison
        st.info(f"Comparing the scenario with all {len(interest_rates)} rates vs. keeping the {len(interest_rates)-1}th rate ({counterfactual_rates[-1]['rate']}%) " 
                f"instead of changing to {interest_rates[-1]['rate']}% on {interest_rates[-1]['start_date'].strftime('%Y-%m-%d')}")
        
        # Create comparison table of interest rates
        rate_comparison = []
        for i, rate_info in enumerate(interest_rates):
            is_counterfactual = i == len(interest_rates) - 1
            end_date = interest_rates[i+1]['start_date'] - datetime.timedelta(days=1) if i < len(interest_rates) - 1 else "End of term"
            
            if is_counterfactual:
                rate_comparison.append({
                    "Period": i + 1,
                    "Actual Rate": f"{rate_info['rate']}%",
                    "Counterfactual Rate": f"{counterfactual_rates[-1]['rate']}%",
                    "Start Date": rate_info['start_date'].strftime("%Y-%m-%d"),
                    "End Date": end_date if isinstance(end_date, str) else end_date.strftime("%Y-%m-%d")
                })
            else:
                rate_comparison.append({
                    "Period": i + 1,
                    "Actual Rate": f"{rate_info['rate']}%",
                    "Counterfactual Rate": f"{rate_info['rate']}%",
                    "Start Date": rate_info['start_date'].strftime("%Y-%m-%d"),
                    "End Date": end_date if isinstance(end_date, str) else end_date.strftime("%Y-%m-%d")
                })
                
        st.table(pd.DataFrame(rate_comparison).set_index("Period"))
        
        # Calculate amortization schedules
        actual_df = calculate_amortization(
            loan_amount, 
            interest_rate, 
            total_months, 
            start_date, 
            extra_payment, 
            interest_rates=interest_rates
        )
        
        counterfactual_df = calculate_amortization(
            loan_amount, 
            interest_rate, 
            total_months, 
            start_date, 
            extra_payment, 
            interest_rates=counterfactual_rates
        )
        
        # Calculate key metrics for comparison
        actual_total_interest = actual_df['Interest'].sum()
        counterfactual_total_interest = counterfactual_df['Interest'].sum()
        interest_difference = actual_total_interest - counterfactual_total_interest
        
        # Display metrics comparison
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label=f"Total Interest ({currency})",
                value=f"{actual_total_interest:,.2f}",
                delta=f"{interest_difference:,.2f}",
                delta_color="inverse"  # Red if more interest, green if less
            )
        
        with col2:
            # Get the monthly payment at the last rate change date
            last_rate_date = interest_rates[-1]['start_date']
            last_rate_month = payment_date_to_month(last_rate_date, start_date)
            
            if last_rate_month <= len(actual_df) and last_rate_month <= len(counterfactual_df):
                actual_monthly = actual_df.loc[actual_df['Month'] >= last_rate_month, 'Payment'].iloc[0]
                counterfactual_monthly = counterfactual_df.loc[counterfactual_df['Month'] >= last_rate_month, 'Payment'].iloc[0]
                payment_diff = actual_monthly - counterfactual_monthly
                
                st.metric(
                    label=f"Monthly Payment After Change ({currency})",
                    value=f"{actual_monthly:.2f}",
                    delta=f"{payment_diff:.2f}",
                    delta_color="inverse"  # Red if payment increased, green if decreased
                )
            else:
                st.metric(
                    label=f"Monthly Payment ({currency})",
                    value=f"{monthly_payment:.2f}"
                )
        
        with col3:
            actual_months = len(actual_df)
            counterfactual_months = len(counterfactual_df)
            months_diff = actual_months - counterfactual_months
            
            st.metric(
                label="Loan Duration (Months)",
                value=f"{actual_months}",
                delta=f"{months_diff}",
                delta_color="inverse"  # Red if longer, green if shorter
            )
        
        # Show balance comparison
        st.subheader("Balance Comparison")
        
        # Create a balance comparison chart
        fig = go.Figure()
        
        # Add traces for both scenarios
        fig.add_trace(go.Scatter(
            x=actual_df['Date_Str'],
            y=actual_df['Balance'],
            name='Actual (With Last Rate Change)',
            line=dict(color='#FF9900', width=2),
            hovertemplate='%{x}<br>Balance: ' + currency + '%{y:,.2f}<br>Rate: %{customdata}%',
            customdata=actual_df['Rate']
        ))
        
        fig.add_trace(go.Scatter(
            x=counterfactual_df['Date_Str'],
            y=counterfactual_df['Balance'],
            name='Counterfactual (Without Last Rate Change)',
            line=dict(color='#4CAF50', width=2, dash='dash'),
            hovertemplate='%{x}<br>Balance: ' + currency + '%{y:,.2f}<br>Rate: %{customdata}%',
            customdata=counterfactual_df['Rate']
        ))
        
        # Mark where the rates change
        for rate_info in interest_rates[1:]:
            rate_date = rate_info['start_date']
            rate_date_str = format_date(rate_date)
            
            if rate_date_str in actual_df['Date_Str'].values:
                # Get balances at the rate change point
                actual_balance = actual_df.loc[actual_df['Date_Str'] == rate_date_str, 'Balance'].values[0]
                counterfactual_balance = counterfactual_df.loc[counterfactual_df['Date_Str'] == rate_date_str, 'Balance'].values[0] if rate_date_str in counterfactual_df['Date_Str'].values else None
                
                # Add shape and annotation
                fig.add_shape(
                    type="line",
                    x0=rate_date_str,
                    y0=0,
                    x1=rate_date_str,
                    y1=max(actual_balance, counterfactual_balance) if counterfactual_balance else actual_balance,
                    line=dict(color="red", width=1, dash="dash"),
                )
                
                # Add annotation for rate change
                fig.add_annotation(
                    x=rate_date_str,
                    y=actual_balance,
                    text=f"Rate Change: {rate_info['rate']}%",
                    showarrow=True,
                    arrowhead=1,
                    ax=40,
                    ay=-40
                )
        
        # Format x-axis to show dates at regular intervals
        date_ticks = []
        date_labels = []
        
        # Add yearly ticks
        for i in range(0, len(actual_df), 12):
            if i < len(actual_df):
                date_ticks.append(actual_df['Date_Str'].iloc[i])
                date_labels.append(actual_df['Date_Str'].iloc[i])
        
        fig.update_layout(
            title="Impact of Last Interest Rate Change on Loan Balance",
            xaxis_title="Date",
            yaxis_title=f"Balance ({currency})",
            height=500,
            hovermode="closest",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5
            ),
            xaxis=dict(
                tickmode='array',
                tickvals=date_ticks,
                ticktext=date_labels
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display payment comparison
        st.subheader("Monthly Payment Analysis")
        
        # Create dataframe comparing monthly payments - Fix column naming issue
        payment_comparison = pd.merge(
            actual_df[['Month', 'Date_Str', 'Payment', 'Principal', 'Interest', 'Rate']].rename(columns={'Date_Str': 'Date_Str_actual'}),
            counterfactual_df[['Month', 'Date_Str', 'Payment', 'Principal', 'Interest', 'Rate']].rename(columns={'Date_Str': 'Date_Str_counterfactual'}),
            on='Month', 
            suffixes=('_actual', '_counterfactual')
        )
        
        # Calculate payment differences
        payment_comparison['Payment_Diff'] = payment_comparison['Payment_actual'] - payment_comparison['Payment_counterfactual']
        payment_comparison['Principal_Diff'] = payment_comparison['Principal_actual'] - payment_comparison['Principal_counterfactual']
        payment_comparison['Interest_Diff'] = payment_comparison['Interest_actual'] - payment_comparison['Interest_counterfactual']
        
        # Plot the payment difference over time
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=payment_comparison['Date_Str_actual'],
            y=payment_comparison['Payment_Diff'],
            name='Payment Difference',
            line=dict(color='purple', width=2),
            hovertemplate='%{x}<br>Payment Difference: ' + currency + '%{y:,.2f}'
        ))
        
        # Fill above/below zero line with different colors
        fig.add_trace(go.Scatter(
            x=payment_comparison['Date_Str_actual'],
            y=payment_comparison['Payment_Diff'].apply(lambda x: max(x, 0)),
            fill='tozeroy',
            line=dict(color='rgba(255, 0, 0, 0.3)', width=0),
            name='Higher Payment with Last Rate Change',
            hoverinfo='skip'
        ))
        
        fig.add_trace(go.Scatter(
            x=payment_comparison['Date_Str_actual'],
            y=payment_comparison['Payment_Diff'].apply(lambda x: min(x, 0)),
            fill='tozeroy',
            line=dict(color='rgba(0, 255, 0, 0.3)', width=0),
            name='Lower Payment with Last Rate Change',
            hoverinfo='skip'
        ))
        
        # Add zero line
        fig.add_shape(
            type="line",
            x0=payment_comparison['Date_Str_actual'].iloc[0],
            y0=0,
            x1=payment_comparison['Date_Str_actual'].iloc[-1],
            y1=0,
            line=dict(color="black", width=1),
        )
        
        fig.update_layout(
            title="Difference in Monthly Payments (Actual - Counterfactual)",
            xaxis_title="Date",
            yaxis_title=f"Payment Difference ({currency})",
            height=350,
            hovermode="closest",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5
            ),
            xaxis=dict(
                tickmode='array',
                tickvals=date_ticks,
                ticktext=date_labels
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display total cost comparison
        st.subheader("Total Cost Comparison")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Total cost with actual rates
            total_actual_cost = loan_amount + actual_total_interest
            
            # Create pie chart for actual scenario
            fig = go.Figure(data=[
                go.Pie(
                    labels=['Principal', 'Interest'],
                    values=[loan_amount, actual_total_interest],
                    hole=0.4,
                    marker=dict(colors=['#3366CC', '#FF9900']),
                    textinfo='label+percent',
                    textposition='inside'
                )
            ])
            
            fig.update_layout(
                title=f"With Last Rate Change: Total Cost {currency}{total_actual_cost:,.2f}",
                height=300,
                margin=dict(t=50, b=0, l=0, r=0)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        with col2:
            # Total cost with counterfactual rates
            total_counterfactual_cost = loan_amount + counterfactual_total_interest
            
            # Create pie chart for counterfactual scenario
            fig = go.Figure(data=[
                go.Pie(
                    labels=['Principal', 'Interest'],
                    values=[loan_amount, counterfactual_total_interest],
                    hole=0.4,
                    marker=dict(colors=['#3366CC', '#4CAF50']),
                    textinfo='label+percent',
                    textposition='inside'
                )
            ])
            
            fig.update_layout(
                title=f"Without Last Rate Change: Total Cost {currency}{total_counterfactual_cost:,.2f}",
                height=300,
                margin=dict(t=50, b=0, l=0, r=0)
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Show summary of the difference
        total_diff = total_actual_cost - total_counterfactual_cost
        st.info(f"The last interest rate change from {counterfactual_rates[-1]['rate']}% to {interest_rates[-1]['rate']}% " 
                f"results in a difference of {currency}{abs(total_diff):,.2f} " 
                f"{'more' if total_diff > 0 else 'less'} over the life of the loan.")

# Footer
st.markdown("""
<div style="margin-top: 3rem; text-align: center; color: #666;">
    <p>This calculator is for educational purposes only. Actual mortgage terms and conditions may vary.</p>
</div>
""", unsafe_allow_html=True)