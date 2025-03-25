import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.calculation_utils import calculate_amortization
from utils.date_utils import get_payment_date, format_date, payment_date_to_month

def render_standard_tab(params, interest_rates):
    """Render the standard calculator tab"""
    # Extract needed parameters
    currency = params['currency']
    start_date = params['start_date']
    loan_amount = params['loan_amount']
    total_months = params['total_months']
    interest_rate = params['interest_rate']
    extra_payment = params['extra_payment']
    years = params['years']
    months = params['months']
    multiple_rates = params['multiple_rates']
    
    # Check if we have multiple interest rates defined
    if multiple_rates:
        st.info(f"This mortgage has {len(interest_rates)} different interest rate periods defined.")
        
        # Calculate monthly payment for each interest rate period
        rate_data = []
        total_duration_months = 0
        weighted_monthly_payment = 0
        loan_amount_balance = float(loan_amount)
        
        for i, rate_info in enumerate(interest_rates):
            # Calculate end date for this period
            if i < len(interest_rates) - 1:
                end_date = interest_rates[i+1]['start_date'] - datetime.timedelta(days=1)
                # Calculate months in this period
                period_months = payment_date_to_month(interest_rates[i+1]['start_date'], rate_info['start_date']) - 1
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
            interest_rates=interest_rates
        )
        
        # For multiple rates, use weighted average instead of initial payment
        monthly_payment = weighted_monthly_payment
    else:
        # Calculate monthly payment for single rate
        monthly_interest_rate = interest_rate / 100 / 12
        monthly_payment = loan_amount * (monthly_interest_rate * (1 + monthly_interest_rate) ** total_months) / ((1 + monthly_interest_rate) ** total_months - 1)
        
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
            
            # Check for overpayments
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
