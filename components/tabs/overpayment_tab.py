import streamlit as st
import pandas as pd
import datetime
import plotly.graph_objects as go
from dateutil.relativedelta import relativedelta
from utils.calculation_utils import calculate_amortization
from utils.date_utils import get_payment_date, format_date, payment_date_to_month

def render_overpayment_tab(params, interest_rates, default_overpayments):
    """Render the overpayment calculator tab"""
    st.subheader("Overpayments Analysis")
    st.write("Add one-time overpayments to see their impact on your mortgage.")
    
    # Extract needed parameters
    currency = params['currency']
    start_date = params['start_date']
    loan_amount = params['loan_amount']
    total_months = params['total_months']
    interest_rate = params['interest_rate']
    extra_payment = params['extra_payment']
    multiple_rates = params['multiple_rates']
    
    # Initialize overpayments in session state if not already there
    if 'overpayments' not in st.session_state:
        st.session_state.overpayments = default_overpayments.copy() if default_overpayments else []
    
    # Functions for managing overpayments
    def add_overpayment():
        # Add a default overpayment at the first payment date
        default_date = start_date + relativedelta(months=0)
        st.session_state.overpayments.append({
            'date': default_date,
            'amount': 1000
        })
    
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
