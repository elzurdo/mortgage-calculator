import os
import json
import datetime
import streamlit as st

def load_defaults():
    """Function to load default parameters from JSON file"""
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
    defaults_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'mortgage_defaults.json')
    
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
    overpayments_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'mortgage_overpayments.json')
    
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
