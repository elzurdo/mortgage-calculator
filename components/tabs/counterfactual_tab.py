import streamlit as st
import pandas as pd
import datetime
import plotly.graph_objects as go
from utils.calculation_utils import calculate_amortization
from utils.date_utils import get_payment_date, format_date, payment_date_to_month

def render_counterfactual_tab(params, interest_rates):
    """Render the counterfactual analysis tab"""
    st.subheader("Interest Rate Change Impact Analysis")
    st.write("This analysis shows what would happen if the last interest rate change never occurred.")
    
    # Extract needed parameters
    currency = params['currency']
    start_date = params['start_date']
    loan_amount = params['loan_amount']
    total_months = params['total_months']
    interest_rate = params['interest_rate']
    extra_payment = params['extra_payment']
    
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
            monthly_payment = loan_amount * (interest_rate / 100 / 12 * (1 + interest_rate / 100 / 12) ** total_months) / ((1 + interest_rate / 100 / 12) ** total_months - 1)
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
    
    # Create dataframe comparing monthly payments
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
