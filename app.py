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

# Create tabs for standard calculator and overpayment calculator
standard_tab, overpayment_tab = st.tabs(["Standard Calculator", "Overpayment Calculator"])

# Load defaults from file
defaults, default_overpayments = load_defaults()

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
    
    interest_rate = st.slider(
        "Annual Interest Rate (%)",
        min_value=0.1,
        max_value=15.0,
        value=defaults['interest_rate'],
        step=0.1
    )
    
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

# Calculate total months
total_months = years * 12 + months

# Calculate monthly payment
monthly_interest_rate = interest_rate / 100 / 12
monthly_payment = loan_amount * (monthly_interest_rate * (1 + monthly_interest_rate) ** total_months) / ((1 + monthly_interest_rate) ** total_months - 1)

# Standard Calculator Tab
with standard_tab:
    # Check if we have multiple interest rates defined
    interest_rates = defaults.get('interest_rates', [])
    multiple_rates = len(interest_rates) > 1
    
    if multiple_rates:
        st.info(f"This mortgage has {len(interest_rates)} different interest rate periods defined.")
        
        # Display the interest rate periods
        rate_data = []
        for i, rate_info in enumerate(interest_rates):
            end_date = interest_rates[i+1]['start_date'] - datetime.timedelta(days=1) if i < len(interest_rates) - 1 else "End of term"
            rate_data.append({
                "Period": i + 1,
                "Rate": f"{rate_info['rate']}%",
                "Start Date": rate_info['start_date'].strftime("%Y-%m-%d"),
                "End Date": end_date if isinstance(end_date, str) else end_date.strftime("%Y-%m-%d")
            })
        
        st.table(pd.DataFrame(rate_data))
        
        # Use the multiple interest rates for calculation
        amortization_df = calculate_amortization(
            loan_amount, 
            interest_rate, 
            total_months, 
            start_date, 
            extra_payment, 
            interest_rates=interest_rates
        )
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
            st.metric(
                label=f"Monthly Payment ({currency})",
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
        
        fig.add_trace(go.Scatter(
            x=baseline_df['Date_Str'],
            y=baseline_df['Balance'],
            name='Without Overpayments',
            line=dict(color='#FF9900', width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=overpayment_df['Date_Str'],
            y=overpayment_df['Balance'],
            name='With Overpayments',
            line=dict(color='#4CAF50', width=2)
        ))
        
        # Add markers for overpayment points
        for month, amount in overpayments_dict.items():
            # Find the corresponding balance after overpayment
            if month <= len(overpayment_df):
                row = overpayment_df.loc[overpayment_df['Month'] == month]
                if not row.empty:
                    balance = row['Balance'].values[0]
                    date_str = row['Date_Str'].values[0]
                    
                    fig.add_trace(go.Scatter(
                        x=[date_str],
                        y=[balance],
                        mode='markers',
                        marker=dict(size=10, color='red'),
                        name=f'Overpayment: {currency}{amount:,.2f}' if month == list(overpayments_dict.keys())[0] else None,
                        showlegend=(month == list(overpayments_dict.keys())[0]),
                        hoverinfo='text',
                        hovertext=f'Date: {date_str}<br>Overpayment: {currency}{amount:,.2f}<br>New Balance: {currency}{balance:,.2f}'
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
            single_op_df = calculate_amortization(loan_amount, interest_rate, total_months, start_date, extra_payment, single_overpayment)
            
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

# Footer
st.markdown("""
<div style="margin-top: 3rem; text-align: center; color: #666;">
    <p>This calculator is for educational purposes only. Actual mortgage terms and conditions may vary.</p>
</div>
""", unsafe_allow_html=True)