"""
Test suite for parse_helpers.py

Tests the parsing helper functions that extract money, percentages, and flags
from OPM health plan data cells.
"""
import pytest
import pandas as pd
from scripts.parse_helpers import (
    parse_money_percent,
    detect_flags,
    parse_deductible,
    parse_coinsurance,
    parse_specialist_split,
    safe_float,
    normalize_column_name,
    is_ambiguous_cell
)


class TestParseMoneyPercent:
    """Test the parse_money_percent function"""
    
    def test_simple_money(self):
        result = parse_money_percent("$25 copay")
        assert result['money'] == 25.0
        assert result['percent'] is None
        assert result['raw'] == "$25 copay"
    
    def test_simple_percent(self):
        result = parse_money_percent("20% after deductible")
        assert result['money'] is None
        assert result['percent'] == 20.0
        assert result['raw'] == "20% after deductible"
    
    def test_money_with_comma(self):
        result = parse_money_percent("$1,500 per year")
        assert result['money'] == 1500.0
        assert result['percent'] is None
    
    def test_covered_keyword(self):
        result = parse_money_percent("Covered")
        assert result['money'] == 0.0
        assert result['percent'] == 0.0
        assert result['raw'] == "Covered"
    
    def test_not_covered_keyword(self):
        result = parse_money_percent("Not Covered")
        assert result['money'] is None
        assert result['percent'] is None
        assert result['raw'] == "Not Covered"
    
    def test_nan_value(self):
        result = parse_money_percent(pd.NA)
        assert result['money'] is None
        assert result['percent'] is None
        assert result['raw'] is None
    
    def test_copay_without_dollar_sign(self):
        result = parse_money_percent("25 copay")
        assert result['money'] == 25.0
    
    def test_multiple_money_values(self):
        # Should extract the first dollar amount
        result = parse_money_percent("$20 copay or $50 after hours")
        assert result['money'] == 20.0


class TestDetectFlags:
    """Test the detect_flags function"""
    
    def test_after_deductible_flag(self):
        flags = detect_flags("$500 after deductible")
        assert flags['applies_after_deductible'] is True
        assert flags['first_visit_only'] is False
    
    def test_first_visit_flag(self):
        flags = detect_flags("Free for first visit")
        assert flags['first_visit_only'] is True
        assert flags['applies_after_deductible'] is False
    
    def test_network_only_flag(self):
        flags = detect_flags("In-network only")
        assert flags['network_only'] is True
    
    def test_prior_auth_flag(self):
        flags = detect_flags("Requires prior authorization")
        assert flags['prior_authorization'] is True
    
    def test_multiple_flags(self):
        flags = detect_flags("$100 after deductible, prior authorization required")
        assert flags['applies_after_deductible'] is True
        assert flags['prior_authorization'] is True
    
    def test_no_flags(self):
        flags = detect_flags("$25 copay")
        assert flags['applies_after_deductible'] is False
        assert flags['first_visit_only'] is False
        assert flags['network_only'] is False
        assert flags['prior_authorization'] is False
    
    def test_none_value(self):
        flags = detect_flags(None)
        assert flags == {}


class TestParseDeductible:
    """Test the parse_deductible function"""
    
    def test_single_deductible(self):
        result = parse_deductible("$500 per person")
        assert result['ded_money'] == 500.0
        assert result['ded_money_max'] is None
        assert result['ded_per_person'] is True
    
    def test_individual_and_family_deductible(self):
        result = parse_deductible("$500 per person / $1,000 family maximum")
        assert result['ded_money'] == 500.0
        assert result['ded_money_max'] == 1000.0
        assert result['ded_per_person'] is True
        assert result['ded_family'] is True
    
    def test_no_deductible(self):
        result = parse_deductible("No deductible")
        assert result['ded_money'] is None
        assert result['ded_raw'] == "No deductible"
    
    def test_none_value(self):
        result = parse_deductible(None)
        assert result == {}


class TestParseCoinsurance:
    """Test the parse_coinsurance function"""
    
    def test_simple_coinsurance(self):
        result = parse_coinsurance("20% coinsurance")
        assert result['coinsurance_pct'] == 20.0
        assert result['coinsurance_raw'] == "20% coinsurance"
    
    def test_coinsurance_with_context(self):
        result = parse_coinsurance("20% after deductible")
        assert result['coinsurance_pct'] == 20.0
    
    def test_no_coinsurance(self):
        result = parse_coinsurance("Covered")
        assert result['coinsurance_pct'] == 0.0


class TestParseSpecialistSplit:
    """Test the parse_specialist_split function"""
    
    def test_pcp_and_specialist_copays(self):
        result = parse_specialist_split("$20 PCP / $35 Specialist")
        assert result['pcp_copay'] == 20.0
        assert result['specialist_copay'] == 35.0
    
    def test_specialist_percent(self):
        result = parse_specialist_split("Specialist: 20% coinsurance")
        assert result['specialist_coinsurance_pct'] == 20.0
        assert result['specialist_copay'] is None
    
    def test_no_split(self):
        result = parse_specialist_split("$25 copay")
        assert result == {}
    
    def test_none_value(self):
        result = parse_specialist_split(None)
        assert result == {}


class TestSafeFloat:
    """Test the safe_float function"""
    
    def test_string_with_currency(self):
        assert safe_float("$1,234.56") == 1234.56
    
    def test_plain_number(self):
        assert safe_float("123.45") == 123.45
    
    def test_integer(self):
        assert safe_float(100) == 100.0
    
    def test_float(self):
        assert safe_float(123.45) == 123.45
    
    def test_nan_value(self):
        assert safe_float(pd.NA) is None
    
    def test_invalid_string(self):
        assert safe_float("not a number") is None


class TestNormalizeColumnName:
    """Test the normalize_column_name function"""
    
    def test_spaces_to_underscores(self):
        assert normalize_column_name("PCP Copay") == "PCP_Copay"
    
    def test_slashes_to_underscores(self):
        assert normalize_column_name("PCP/Specialist") == "PCP_Specialist"
    
    def test_hyphens_to_underscores(self):
        assert normalize_column_name("Out-of-Pocket") == "Out_of_Pocket"
    
    def test_colons_removed(self):
        assert normalize_column_name("Deductible:") == "Deductible"
    
    def test_complex_column_name(self):
        assert normalize_column_name("PCP/Specialist Copay: In-Network") == "PCP_Specialist_Copay_In_Network"


class TestIsAmbiguousCell:
    """Test the is_ambiguous_cell function"""
    
    def test_ambiguous_with_may(self):
        parsed = {'money': None, 'percent': None, 'raw': 'May be covered'}
        assert is_ambiguous_cell(parsed, 'May be covered') is True
    
    def test_ambiguous_with_subject_to(self):
        parsed = {'money': None, 'percent': None, 'raw': 'Subject to approval'}
        assert is_ambiguous_cell(parsed, 'Subject to approval') is True
    
    def test_not_ambiguous_with_value(self):
        parsed = {'money': 25.0, 'percent': None, 'raw': '$25 copay after deductible'}
        assert is_ambiguous_cell(parsed, '$25 copay after deductible') is False
    
    def test_not_ambiguous_clear_text(self):
        parsed = {'money': None, 'percent': None, 'raw': 'Covered'}
        assert is_ambiguous_cell(parsed, 'Covered') is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
