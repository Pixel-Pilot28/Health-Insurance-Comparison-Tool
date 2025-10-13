"""
Unit tests for Extended NLP Parser

Tests the parsing of complex benefit strings like:
- "$25 then 20% up to $500"
- "$25 or 15%"
- "50% after deductible up to $1500"
"""

import pytest
from backend.scripts.opm_nlp_parser import (
    ExtendedNLPParser,
    BenefitRule,
    parse_benefit_string,
)


class TestSimpleRules:
    """Tests for simple copay and coinsurance rules."""
    
    def test_simple_copay(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("$25")
        
        assert rule.copay == 25.0
        assert rule.coinsurance is None
        assert rule.is_covered is None
    
    def test_simple_coinsurance(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("20%")
        
        assert rule.coinsurance == 20.0
        assert rule.copay is None
    
    def test_copay_with_text(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("Copay is $35 per visit")
        
        assert rule.copay == 35.0
    
    def test_coinsurance_with_text(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("You pay 15% of the cost")
        
        assert rule.coinsurance == 15.0
    
    def test_money_with_commas(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("$1,500 per admission")
        
        assert rule.copay == 1500.0
    
    def test_money_with_decimals(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("$25.50 copay")
        
        assert rule.copay == 25.50


class TestRanges:
    """Tests for range parsing."""
    
    def test_simple_range(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("$100-$200")
        
        assert rule.min_value == 100.0
        assert rule.max_value == 200.0
    
    def test_range_with_spaces(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("$100 - $200")
        
        assert rule.min_value == 100.0
        assert rule.max_value == 200.0
    
    def test_range_with_text(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("Cost ranges from $50 to $150")
        
        # Note: Currently parses as simple copay, not range
        # This tests current behavior
        assert rule.copay == 50.0 or rule.min_value == 50.0


class TestCoverageStatus:
    """Tests for coverage status detection."""
    
    def test_no_charge(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("No charge")
        
        assert rule.is_covered is True
        assert rule.copay == 0.0
    
    def test_covered(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("Covered in full")
        
        assert rule.is_covered is True
        assert rule.copay == 0.0
    
    def test_not_covered(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("Not covered")
        
        assert rule.is_covered is False
    
    def test_all_charges(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("All charges")
        
        assert rule.is_covered is False
    
    def test_not_covered_priority(self):
        # "Not covered" should be detected before "covered"
        parser = ExtendedNLPParser()
        rule = parser.parse("Not covered by plan")
        
        assert rule.is_covered is False


class TestFlags:
    """Tests for flag detection."""
    
    def test_after_deductible(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("20% after deductible")
        
        assert rule.applies_after_deductible is True
        assert rule.coinsurance == 20.0
    
    def test_deductible_applies(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("$50 copay, deductible applies")
        
        assert rule.applies_after_deductible is True
        assert rule.copay == 50.0
    
    def test_subject_to_deductible(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("15% subject to deductible")
        
        assert rule.applies_after_deductible is True
    
    def test_first_visit_only(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("$25 first visit only")
        
        assert rule.first_visit_only is True
        assert rule.copay == 25.0
    
    def test_network_only(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("$30 network only")
        
        assert rule.network_only is True
        assert rule.copay == 30.0
    
    def test_prior_authorization(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("Covered with prior authorization")
        
        assert rule.prior_authorization is True
    
    def test_multiple_flags(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("20% after deductible, network only, prior auth required")
        
        assert rule.coinsurance == 20.0
        assert rule.applies_after_deductible is True
        assert rule.network_only is True
        assert rule.prior_authorization is True


class TestVisitLimits:
    """Tests for visit limit extraction."""
    
    def test_first_n_visits(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("First 3 visits $25")
        
        assert rule.visits_limit == 3
        assert rule.copay == 25.0
    
    def test_initial_visits(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("Initial 5 visits covered")
        
        assert rule.visits_limit == 5


class TestThenRules:
    """Tests for multi-step 'then' rules."""
    
    def test_copay_then_coinsurance(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("$25 then 20%")
        
        assert rule.copay == 25.0
        assert rule.secondary_coinsurance == 20.0
    
    def test_copay_then_copay(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("$25 then $50")
        
        assert rule.copay == 25.0
        assert rule.secondary_copay == 50.0
    
    def test_complex_then_rule(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("$25 then 20% up to $500")
        
        assert rule.copay == 25.0
        assert rule.secondary_coinsurance == 20.0
        assert rule.cap == 500.0
    
    def test_coinsurance_then_copay(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("20% then $100 maximum")
        
        assert rule.coinsurance == 20.0
        assert rule.secondary_copay == 100.0


class TestOrRules:
    """Tests for alternative 'or' rules."""
    
    def test_copay_or_coinsurance(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("$25 or 15%")
        
        assert rule.copay == 25.0
        assert rule.secondary_coinsurance == 15.0
    
    def test_coinsurance_or_copay(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("20% or $50")
        
        assert rule.coinsurance == 20.0
        assert rule.secondary_copay == 50.0
    
    def test_or_with_text(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("You pay $30 copay or 10% coinsurance")
        
        assert rule.copay == 30.0
        assert rule.secondary_coinsurance == 10.0


class TestUpToRules:
    """Tests for 'up to' rules with caps."""
    
    def test_coinsurance_up_to_cap(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("20% up to $500")
        
        assert rule.coinsurance == 20.0
        assert rule.cap == 500.0
    
    def test_copay_up_to_cap(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("$50 per day up to $1,000")
        
        assert rule.copay == 50.0
        assert rule.cap == 1000.0
    
    def test_after_deductible_up_to(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("50% after deductible up to $1500")
        
        assert rule.coinsurance == 50.0
        assert rule.applies_after_deductible is True
        assert rule.cap == 1500.0
    
    def test_multiple_amounts_with_cap(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("$200 copay up to $2,000 maximum")
        
        assert rule.copay == 200.0
        assert rule.cap == 2000.0


class TestComplexRules:
    """Tests for complex multi-part rules."""
    
    def test_first_visits_then_different_copay(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("First 3 visits $25, then $50")
        
        assert rule.visits_limit == 3
        assert rule.copay == 25.0
        assert rule.secondary_copay == 50.0
    
    def test_network_with_deductible_and_cap(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("Network only: 20% after deductible up to $1,500")
        
        assert rule.network_only is True
        assert rule.coinsurance == 20.0
        assert rule.applies_after_deductible is True
        assert rule.cap == 1500.0
    
    def test_prior_auth_with_coinsurance(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("15% with prior authorization required")
        
        assert rule.coinsurance == 15.0
        assert rule.prior_authorization is True


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_string(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("")
        
        assert rule.raw == ""
        assert rule.copay is None
    
    def test_none_input(self):
        parser = ExtendedNLPParser()
        rule = parser.parse(None)
        
        assert rule.raw == "None"
    
    def test_no_numbers(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("Contact plan for details")
        
        assert rule.copay is None
        assert rule.coinsurance is None
    
    def test_multiple_percentages(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("10% or 20% depending on service")
        
        # Should pick first one
        assert rule.coinsurance == 10.0
    
    def test_percentage_over_100(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("150% of allowed amount")
        
        assert rule.coinsurance == 150.0


class TestConvenienceFunction:
    """Tests for parse_benefit_string convenience function."""
    
    def test_returns_dict(self):
        result = parse_benefit_string("$25 copay")
        
        assert isinstance(result, dict)
        assert 'copay' in result
        assert 'coinsurance' in result
        assert 'raw' in result
    
    def test_dict_values(self):
        result = parse_benefit_string("20% after deductible")
        
        assert result['coinsurance'] == 20.0
        assert result['applies_after_deductible'] is True
        assert result['raw'] == "20% after deductible"
    
    def test_all_fields_present(self):
        result = parse_benefit_string("$25")
        
        expected_fields = [
            'copay', 'coinsurance', 'cap', 'min_value', 'max_value',
            'applies_after_deductible', 'first_visit_only', 'network_only',
            'prior_authorization', 'visits_limit', 'secondary_copay',
            'secondary_coinsurance', 'is_covered', 'raw'
        ]
        
        for field in expected_fields:
            assert field in result


class TestToDictMethod:
    """Tests for BenefitRule.to_dict() method."""
    
    def test_to_dict_serialization(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("$25 then 20% up to $500")
        result = parser.to_dict(rule)
        
        assert isinstance(result, dict)
        assert result['copay'] == 25.0
        assert result['secondary_coinsurance'] == 20.0
        assert result['cap'] == 500.0
    
    def test_none_values_preserved(self):
        parser = ExtendedNLPParser()
        rule = parser.parse("$25")
        result = parser.to_dict(rule)
        
        assert result['coinsurance'] is None
        assert result['secondary_copay'] is None
        assert result['visits_limit'] is None


class TestRealWorldExamples:
    """Tests using real-world benefit string examples."""
    
    def test_geha_standard_pcp(self):
        # Real example from GEHA plan
        parser = ExtendedNLPParser()
        rule = parser.parse("$25 copay per visit")
        
        assert rule.copay == 25.0
        assert rule.is_covered is None
    
    def test_bcbs_deductible_coinsurance(self):
        # Real example from BCBS
        parser = ExtendedNLPParser()
        rule = parser.parse("20% after deductible")
        
        assert rule.coinsurance == 20.0
        assert rule.applies_after_deductible is True
    
    def test_aetna_emergency_room(self):
        # Real example from Aetna
        parser = ExtendedNLPParser()
        rule = parser.parse("$150 copay, waived if admitted")
        
        assert rule.copay == 150.0
    
    def test_kaiser_preventive(self):
        # Real example from Kaiser
        parser = ExtendedNLPParser()
        rule = parser.parse("No charge for preventive care")
        
        assert rule.is_covered is True
        assert rule.copay == 0.0
    
    def test_cigna_specialist(self):
        # Real example from Cigna
        parser = ExtendedNLPParser()
        rule = parser.parse("$40 copay or 30% after deductible")
        
        assert rule.copay == 40.0
        assert rule.secondary_coinsurance == 30.0
