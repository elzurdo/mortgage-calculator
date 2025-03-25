import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta
from utils.date_utils import get_payment_date, format_date

def get_applicable_interest_rate(date, interest_rates):
    """Helper function to find the applicable interest rate for a given date"""
    # Sort rates by start date (newest to oldest)
    sorted_rates = sorted(interest_rates, key=lambda x: x['start_date'], reverse=True)
    
    # Find the most recent rate that applies (with start_date <= current date)
    for rate_info in sorted_rates:
        if rate_info['start_date'] <= date:
            return rate_info['rate']
    
    # If no applicable rate found, return the earliest one
    return sorted_rates[-1]['rate']

def calculate_amortization(loan_amount, interest_rate, total_months, start_date, extra_payment=0, overpayments=None, interest_rates=None):
    """Calculate amortization schedule with support for one-time overpayments and variable interest rates"""
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
