import pytest
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta
from utils.calculation_utils import get_applicable_interest_rate, calculate_amortization


class TestGetApplicableInterestRate:
    def test_single_interest_rate(self):
        """Test with a single interest rate"""
        date = datetime.date(2023, 1, 15)
        rates = [{'rate': 5.0, 'start_date': datetime.date(2022, 1, 1)}]
        
        assert get_applicable_interest_rate(date, rates) == 5.0

    def test_multiple_rates(self):
        """Test with multiple interest rates"""
        date = datetime.date(2023, 6, 15)
        rates = [
            {'rate': 3.0, 'start_date': datetime.date(2022, 1, 1)},
            {'rate': 4.0, 'start_date': datetime.date(2023, 1, 1)},
            {'rate': 5.0, 'start_date': datetime.date(2023, 7, 1)}
        ]
        
        assert get_applicable_interest_rate(date, rates) == 4.0

    def test_date_before_earliest_rate(self):
        """Test with date before earliest rate should return earliest rate"""
        date = datetime.date(2021, 1, 1)
        rates = [
            {'rate': 3.0, 'start_date': datetime.date(2022, 1, 1)},
            {'rate': 4.0, 'start_date': datetime.date(2023, 1, 1)}
        ]
        
        assert get_applicable_interest_rate(date, rates) == 3.0

    def test_date_matches_start_date(self):
        """Test when date exactly matches a start date"""
        date = datetime.date(2023, 1, 1)
        rates = [
            {'rate': 3.0, 'start_date': datetime.date(2022, 1, 1)},
            {'rate': 4.0, 'start_date': datetime.date(2023, 1, 1)},
            {'rate': 5.0, 'start_date': datetime.date(2024, 1, 1)}
        ]
        
        assert get_applicable_interest_rate(date, rates) == 4.0


class TestCalculateAmortization:
    def test_basic_amortization(self):
        """Test basic amortization with fixed rate"""
        loan_amount = 100000
        interest_rate = 5.0
        total_months = 12
        start_date = datetime.date(2023, 1, 1)
        
        result = calculate_amortization(loan_amount, interest_rate, total_months, start_date)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 12  # Should have 12 payments
        assert abs(result['Balance'].iloc[-1]) < 0.01  # Final balance should be approximately zero
        assert result['Rate'].unique()[0] == 5.0  # Should use the provided interest rate

    def test_with_extra_payment(self):
        """Test amortization with regular extra payments"""
        loan_amount = 100000
        interest_rate = 5.0
        total_months = 12
        start_date = datetime.date(2023, 1, 1)
        extra_payment = 500
        
        result = calculate_amortization(loan_amount, interest_rate, total_months, start_date, extra_payment)
        
        # With extra payments, the loan should be paid off earlier
        assert len(result) < 12
        assert abs(result['Balance'].iloc[-1]) < 0.01

    def test_with_overpayments(self):
        """Test amortization with one-time overpayments"""
        loan_amount = 100000
        interest_rate = 5.0
        total_months = 12
        start_date = datetime.date(2023, 1, 1)
        overpayments = {3: 10000, 6: 5000}  # Overpayments in month 3 and 6
        
        result = calculate_amortization(loan_amount, interest_rate, total_months, start_date, 
                                        overpayments=overpayments)
        
        # Check overpayments were applied in the correct months
        assert result[result['Month'] == 3]['Overpayment'].iloc[0] == 10000
        assert result[result['Month'] == 6]['Overpayment'].iloc[0] == 5000

    def test_variable_interest_rates(self):
        """Test amortization with variable interest rates"""
        loan_amount = 100000
        interest_rate = 5.0  # Default rate, should be overridden
        total_months = 24
        start_date = datetime.date(2023, 1, 1)
        
        interest_rates = [
            {'rate': 5.0, 'start_date': datetime.date(2023, 1, 1)},
            {'rate': 6.0, 'start_date': datetime.date(2023, 7, 1)},
            {'rate': 4.5, 'start_date': datetime.date(2024, 1, 1)}
        ]
        
        result = calculate_amortization(
            loan_amount, interest_rate, total_months, start_date,
            interest_rates=interest_rates
        )
        
        # Check that different rates were applied at different times
        rates_in_first_six_months = result[result['Month'] <= 6]['Rate'].unique()
        rates_in_second_six_months = result[(result['Month'] > 6) & (result['Month'] <= 12)]['Rate'].unique()
        rates_in_remaining_months = result[result['Month'] > 12]['Rate'].unique()
        
        assert 5.0 in rates_in_first_six_months
        assert 6.0 in rates_in_second_six_months
        assert 4.5 in rates_in_remaining_months

    def test_full_early_repayment(self):
        """Test case where the loan is fully paid off by an overpayment"""
        loan_amount = 100000
        interest_rate = 5.0
        total_months = 120  # 10 years
        start_date = datetime.date(2023, 1, 1)
        overpayments = {3: 100000}  # Pay off most/all in month 3
        
        result = calculate_amortization(loan_amount, interest_rate, total_months, start_date, 
                                        overpayments=overpayments)
        
        # The loan should be paid off shortly after the overpayment
        assert len(result) <= 4  # Should be at most 4 payments (including the final one)
        assert abs(result['Balance'].iloc[-1]) < 0.01

    def test_edge_case_short_term_loan(self):
        """Test very short-term loan"""
        loan_amount = 10000
        interest_rate = 5.0
        total_months = 3
        start_date = datetime.date(2023, 1, 1)
        
        result = calculate_amortization(loan_amount, interest_rate, total_months, start_date)
        
        assert len(result) == 3
        assert abs(result['Balance'].iloc[-1]) < 0.01
