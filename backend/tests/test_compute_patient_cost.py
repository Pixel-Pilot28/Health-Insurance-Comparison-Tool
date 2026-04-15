"""
Unit tests for enhanced cost computation with copay-then-coinsurance rules

Tests the compute_patient_cost function in cost_calculator.py
"""

import pytest
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.cost_calculator import compute_patient_cost


class TestSimpleCopay:
    """Tests for simple copay rules"""
    
    def test_fixed_copay_no_deductible(self):
        """$25 copay with no deductible"""
        plan_row = {
            "Primary_Care_Office_Visit_money": 25.0
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Primary_Care_Office_Visit", 150.0, 0.0
        )
        assert cost == 25.0
        assert deductible == 0.0
        assert metadata['cost_type'] == 'copay_primary'
    
    def test_copay_with_deductible_not_applied(self):
        """$25 copay, deductible does not apply"""
        plan_row = {
            "Primary_Care_Office_Visit_money": 25.0,
            "Primary_Care_Office_Visit_applies_after_deductible": False
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Primary_Care_Office_Visit", 150.0, 500.0
        )
        assert cost == 25.0
        assert deductible == 500.0  # Unchanged
        assert metadata['cost_type'] == 'copay_primary'
    
    def test_copay_applies_after_deductible(self):
        """$25 copay applies after deductible"""
        plan_row = {
            "Primary_Care_Office_Visit_money": 25.0,
            "Primary_Care_Office_Visit_applies_after_deductible": True
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Primary_Care_Office_Visit", 150.0, 500.0
        )
        # Should pay deductible first: $150, then copay: $25
        assert cost == 175.0
        assert deductible == 350.0  # 500 - 150
        assert 'deductible_applied' in metadata


class TestSimpleCoinsurance:
    """Tests for simple coinsurance rules"""
    
    def test_coinsurance_no_deductible(self):
        """20% coinsurance with no deductible"""
        plan_row = {
            "Specialist_Office_Visit_percent": 20.0
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Specialist_Office_Visit", 200.0, 0.0
        )
        assert cost == 40.0  # 20% of 200
        assert deductible == 0.0
        assert metadata['cost_type'] == 'coinsurance_primary'
    
    def test_coinsurance_with_deductible(self):
        """20% coinsurance applies after deductible"""
        plan_row = {
            "Specialist_Office_Visit_percent": 20.0,
            "Specialist_Office_Visit_applies_after_deductible": True
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Specialist_Office_Visit", 200.0, 100.0
        )
        # Pay $100 to deductible, then 20% of remaining $100 = $20
        assert cost == 120.0
        assert deductible == 0.0
        assert 'deductible_applied' in metadata


class TestCopayThenCoinsurance:
    """Tests for copay-then-coinsurance rules (multi-step)"""
    
    def test_copay_then_coinsurance_basic(self):
        """$25 then 20% up to $500"""
        plan_row = {
            "Emergency_Care_money": 25.0,
            "Emergency_Care_secondary_coinsurance": 20.0,
            "Emergency_Care_cap": 500.0
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Emergency_Care", 1000.0, 0.0
        )
        # $25 copay + 20% of the allowed charge ($1000) = $225
        assert cost == 225.0
        assert metadata['cost_type'] == 'copay_then_coinsurance'
        assert metadata['has_secondary_rule']
    
    def test_copay_then_coinsurance_with_cap(self):
        """$25 then 20% up to $150"""
        plan_row = {
            "Emergency_Care_money": 25.0,
            "Emergency_Care_secondary_coinsurance": 20.0,
            "Emergency_Care_cap": 150.0
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Emergency_Care", 1000.0, 0.0
        )
        # $25 + 20% of $975 = $220, but capped at $150
        assert cost == 150.0
        assert metadata['cap_applied']
    
    def test_copay_then_coinsurance_with_deductible(self):
        """$25 then 20%, deductible applies"""
        plan_row = {
            "Emergency_Care_money": 25.0,
            "Emergency_Care_secondary_coinsurance": 20.0,
            "Emergency_Care_applies_after_deductible": True
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Emergency_Care", 500.0, 300.0
        )
        # Pay $300 to deductible, $200 remaining
        # Then $25 copay + 20% of the post-deductible charge ($200)
        # Total: $300 + $25 + $40 = $365
        assert cost == 365.0
        assert deductible == 0.0


class TestCoinsuranceThenCopay:
    """Tests for coinsurance-then-copay rules (rare but possible)"""
    
    def test_coinsurance_then_copay(self):
        """20% then $50 copay"""
        plan_row = {
            "Urgent_Care_percent": 20.0,
            "Urgent_Care_secondary_copay": 50.0
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Urgent_Care", 200.0, 0.0
        )
        # 20% of $200 = $40, then $50 copay = $90
        assert cost == 90.0
        assert metadata['cost_type'] == 'coinsurance_then_copay'


class TestRanges:
    """Tests for min/max range rules"""
    
    def test_range_within_bounds(self):
        """$25-$50 range, cost falls within"""
        plan_row = {
            "Service_min_value": 25.0,
            "Service_max_value": 50.0,
            "Service_money": 30.0
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Service", 100.0, 0.0
        )
        # Cost is $30, within range [25, 50]
        assert 25.0 <= cost <= 50.0
        assert metadata['cost_type'] == 'range'
    
    def test_range_exceeds_max(self):
        """Range caps at maximum"""
        plan_row = {
            "Service_min_value": 25.0,
            "Service_max_value": 50.0,
            "Service_money": 100.0  # Would exceed max
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Service", 200.0, 0.0
        )
        # Cost capped at max
        assert cost == 50.0


class TestCaps:
    """Tests for cap (maximum member responsibility)"""
    
    def test_cap_applied(self):
        """50% coinsurance capped at $500"""
        plan_row = {
            "Inpatient_percent": 50.0,
            "Inpatient_cap": 500.0
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Inpatient", 2000.0, 0.0
        )
        # 50% of $2000 = $1000, but capped at $500
        assert cost == 500.0
        assert metadata['cap_applied']
    
    def test_cap_not_reached(self):
        """Cap higher than calculated cost"""
        plan_row = {
            "Inpatient_percent": 10.0,
            "Inpatient_cap": 500.0
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Inpatient", 1000.0, 0.0
        )
        # 10% of $1000 = $100, under $500 cap
        assert cost == 100.0
        assert not metadata.get('cap_applied', False)


class TestCoverageStatus:
    """Tests for coverage status flags"""
    
    def test_fully_covered(self):
        """Service covered in full"""
        plan_row = {
            "Preventive_Care_is_covered": True
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Preventive_Care", 150.0, 0.0
        )
        assert cost == 0.0
        assert metadata['cost_type'] == 'covered'
    
    def test_not_covered(self):
        """Service not covered"""
        plan_row = {
            "Cosmetic_is_covered": False
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Cosmetic", 1000.0, 0.0
        )
        assert cost == 1000.0
        assert metadata['cost_type'] == 'not_covered_full_liability'


class TestFlags:
    """Tests for special condition flags"""
    
    def test_prior_authorization_flag(self):
        """Prior authorization required"""
        plan_row = {
            "Specialist_money": 50.0,
            "Specialist_prior_authorization": True
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Specialist", 200.0, 0.0
        )
        assert cost == 50.0
        assert metadata['prior_authorization']
    
    def test_network_only_flag(self):
        """Network only restriction"""
        plan_row = {
            "Specialist_money": 50.0,
            "Specialist_network_only": True
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Specialist", 200.0, 0.0
        )
        assert cost == 50.0
        assert metadata['network_only']
    
    def test_first_visit_only_flag(self):
        """Benefit applies to first visit only"""
        plan_row = {
            "Physical_Therapy_money": 25.0,
            "Physical_Therapy_first_visit_only": True
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Physical_Therapy", 150.0, 0.0
        )
        assert cost == 25.0
        assert metadata['first_visit_only']
    
    def test_visits_limit(self):
        """Service has visit limit"""
        plan_row = {
            "Chiropractic_money": 30.0,
            "Chiropractic_visits_limit": 20
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Chiropractic", 100.0, 0.0
        )
        assert cost == 30.0
        assert metadata['visits_limit'] == 20


class TestComplexScenarios:
    """Tests for complex real-world scenarios"""
    
    def test_geha_emergency_room(self):
        """GEHA: $150 then 20% after deductible up to $500"""
        plan_row = {
            "Emergency_Care_money": 150.0,
            "Emergency_Care_secondary_coinsurance": 20.0,
            "Emergency_Care_applies_after_deductible": True,
            "Emergency_Care_cap": 500.0
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Emergency_Care", 3000.0, 1000.0
        )
        # Pay $1000 to deductible, $2000 remaining
        # $150 copay + 20% of ($2000 - $150) = $150 + $370 = $520
        # Capped at $500 total member cost (not including deductible)
        # Actually: deductible + capped amount = $1000 + $500
        assert cost == 1500.0
        assert deductible == 0.0
        assert metadata['cap_applied']
    
    def test_bcbs_specialist_after_deductible(self):
        """BCBS: $50 specialist copay applies after deductible"""
        plan_row = {
            "Specialist_Office_Visit_money": 50.0,
            "Specialist_Office_Visit_applies_after_deductible": True
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Specialist_Office_Visit", 200.0, 800.0
        )
        # Pay $200 to deductible, then $50 copay
        assert cost == 250.0
        assert deductible == 600.0
    
    def test_kaiser_no_deductible_copay(self):
        """Kaiser: $25 copay, no deductible"""
        plan_row = {
            "Primary_Care_Office_Visit_money": 25.0,
            "Primary_Care_Office_Visit_applies_after_deductible": False
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Primary_Care_Office_Visit", 150.0, 0.0
        )
        assert cost == 25.0
        assert deductible == 0.0
    
    def test_aetna_high_deductible_coinsurance(self):
        """Aetna HDHP: 20% after deductible"""
        plan_row = {
            "Specialist_Office_Visit_percent": 20.0,
            "Specialist_Office_Visit_applies_after_deductible": True
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Specialist_Office_Visit", 300.0, 2000.0
        )
        # Pay $300 to deductible, nothing left for coinsurance
        assert cost == 300.0
        assert deductible == 1700.0


class TestEdgeCases:
    """Tests for edge cases and error handling"""
    
    def test_zero_allowed_charge(self):
        """Service with $0 allowed charge"""
        plan_row = {
            "Service_money": 25.0
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Service", 0.0, 0.0
        )
        assert cost == 25.0  # Copay still applies
    
    def test_no_cost_sharing_rules(self):
        """No parsed fields - needs review"""
        plan_row = {
            "Service_raw": "See plan details"
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Service", 100.0, 0.0
        )
        assert cost is None
        assert metadata['cost_type'] == 'needs_review'
    
    def test_deductible_exactly_met(self):
        """Service cost exactly equals deductible"""
        plan_row = {
            "Service_percent": 20.0,
            "Service_applies_after_deductible": True
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Service", 500.0, 500.0
        )
        # All $500 goes to deductible, no coinsurance
        assert cost == 500.0
        assert deductible == 0.0
    
    def test_multiple_flags(self):
        """Service with multiple flags set"""
        plan_row = {
            "Service_money": 50.0,
            "Service_prior_authorization": True,
            "Service_network_only": True,
            "Service_first_visit_only": True,
            "Service_visits_limit": 10
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Service", 200.0, 0.0
        )
        assert cost == 50.0
        assert metadata['prior_authorization']
        assert metadata['network_only']
        assert metadata['first_visit_only']
        assert metadata['visits_limit'] == 10


class TestRawFieldFallback:
    """Tests for raw field interpretation when parsed fields missing"""
    
    def test_raw_not_covered(self):
        """Raw field says 'not covered'"""
        plan_row = {
            "Service_raw": "Not covered under this plan"
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Service", 100.0, 0.0
        )
        assert cost == 100.0
        assert metadata['cost_type'] == 'not_covered_full_liability'
    
    def test_raw_covered_in_full(self):
        """Raw field says 'covered in full'"""
        plan_row = {
            "Service_raw": "Covered in full, no member cost"
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Service", 100.0, 0.0
        )
        assert cost == 0.0
        assert metadata['cost_type'] == 'covered'
    
    def test_raw_100_percent(self):
        """Raw field says '100%'"""
        plan_row = {
            "Service_raw": "100% covered by plan"
        }
        cost, deductible, metadata = compute_patient_cost(
            plan_row, "Service", 100.0, 0.0
        )
        assert cost == 0.0
        assert metadata['cost_type'] == 'covered'


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
