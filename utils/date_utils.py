import datetime
from dateutil.relativedelta import relativedelta

def get_payment_date(start_date, month_number):
    """Helper function to get the date for a given month number"""
    return start_date + relativedelta(months=month_number - 1)

def format_date(date):
    """Helper function to format date as YYYY-MM"""
    return date.strftime("%Y-%m")

def payment_date_to_month(payment_date, start_date):
    """Convert payment date to month number based on start date"""
    # Calculate months between dates
    delta = relativedelta(payment_date, start_date)
    return delta.years * 12 + delta.months + 1  # +1 because month 1 is the start month
