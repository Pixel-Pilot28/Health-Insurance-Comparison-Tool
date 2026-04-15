"""
Test suite for cost_calculator.py service cost computation

Tests the new compute_cost_for_service function that uses parsed fields.
"""
import pytest
from services.cost_calculator import compute_cost_for_service, map_service_to_column_base


class TestMapServiceToColumnBase:
    """Test service name to column base mapping"""
    
    def test_primary_care_mapping(self):
        assert map_service_to_column_base('PrimaryCareVisit') == 'Primary_Care_Office_Visit'
    
    def test_specialist_mapping(self):
        assert map_service_to_column_base('SpecialistVisit') == 'Specialist_Office_Visit'
    
    def test_unmapped_service(self):
        # Should return the input if not in mapping
        assert map_service_to_column_base('UnknownService') == 'UnknownService'


class TestComputeCostForService:
    """Test the compute_cost_for_service function with different scenarios"""
    
    def test_money_field_priority(self):
        """Money field should take priority over percent and raw"""
        plan_row = {
            'PCP_Office_Visit_money': 25.0,
            'PCP_Office_Visit_percent': 20.0,
            'PCP_Office_Visit_raw': '$25 copay'
        }
        cost, metadata = compute_cost_for_service(plan_row, 'PCP_Office_Visit', 150.0)
        
        assert cost == 25.0
        assert metadata['cost_type'] == 'copay'
    
    def test_percent_field_when_no_money(self):
        """Percent field should be used when money is None"""
        plan_row = {
            'PCP_Office_Visit_money': None,
            'PCP_Office_Visit_percent': 20.0,
            'PCP_Office_Visit_raw': '20% coinsurance'
        }
        allowed_charge = 150.0
        cost, metadata = compute_cost_for_service(plan_row, 'PCP_Office_Visit', allowed_charge)
        
        assert cost == 30.0  # 20% of 150
        assert metadata['cost_type'] == 'coinsurance'
    
    def test_covered_interpretation(self):
        """Raw 'Covered' should return cost of 0"""
        plan_row = {
            'PCP_Office_Visit_money': None,
            'PCP_Office_Visit_percent': None,
            'PCP_Office_Visit_raw': 'Covered'
        }
        cost, metadata = compute_cost_for_service(plan_row, 'PCP_Office_Visit', 150.0)
        
        assert cost == 0.0
        assert metadata['cost_type'] == 'covered'
    
    def test_not_covered_interpretation(self):
        """Raw 'Not Covered' should charge the full allowed amount"""
        plan_row = {
            'PCP_Office_Visit_money': None,
            'PCP_Office_Visit_percent': None,
            'PCP_Office_Visit_raw': 'Not Covered'
        }
        cost, metadata = compute_cost_for_service(plan_row, 'PCP_Office_Visit', 150.0)

        assert cost == 150.0
        assert metadata['cost_type'] == 'not_covered_full_liability'
    
    def test_after_deductible_flag(self):
        """'After deductible' text should return None for special handling"""
        plan_row = {
            'PCP_Office_Visit_money': None,
            'PCP_Office_Visit_percent': None,
            'PCP_Office_Visit_raw': 'Covered after deductible',
            'PCP_Office_Visit_applies_after_deductible': True
        }
        cost, metadata = compute_cost_for_service(plan_row, 'PCP_Office_Visit', 150.0)
        
        assert cost is None
        assert metadata['cost_type'] == 'needs_review'
        assert metadata['applies_after_deductible'] is True
    
    def test_special_flags_captured(self):
        """Special condition flags should be captured in metadata"""
        plan_row = {
            'PCP_Office_Visit_money': 25.0,
            'PCP_Office_Visit_percent': None,
            'PCP_Office_Visit_raw': '$25 copay, prior authorization required',
            'PCP_Office_Visit_applies_after_deductible': False,
            'PCP_Office_Visit_first_visit_only': False,
            'PCP_Office_Visit_network_only': True,
            'PCP_Office_Visit_prior_authorization': True
        }
        cost, metadata = compute_cost_for_service(plan_row, 'PCP_Office_Visit', 150.0)
        
        assert cost == 25.0
        assert metadata['network_only'] is True
        assert metadata['prior_authorization'] is True
        assert metadata['first_visit_only'] is False
    
    def test_in_network_covered(self):
        """'In-network' should be interpreted as covered"""
        plan_row = {
            'PCP_Office_Visit_money': None,
            'PCP_Office_Visit_percent': None,
            'PCP_Office_Visit_raw': 'In-network'
        }
        cost, metadata = compute_cost_for_service(plan_row, 'PCP_Office_Visit', 150.0)
        
        assert cost == 0.0
        assert metadata['cost_type'] == 'covered'
    
    def test_no_data_needs_review(self):
        """No data should return None and needs_review"""
        plan_row = {
            'PCP_Office_Visit_money': None,
            'PCP_Office_Visit_percent': None,
            'PCP_Office_Visit_raw': None
        }
        cost, metadata = compute_cost_for_service(plan_row, 'PCP_Office_Visit', 150.0)
        
        assert cost is None
        assert metadata['cost_type'] == 'needs_review'
    
    def test_hundred_percent_covered(self):
        """'100%' in raw text should be interpreted as covered"""
        plan_row = {
            'PCP_Office_Visit_money': None,
            'PCP_Office_Visit_percent': None,
            'PCP_Office_Visit_raw': '100% covered'
        }
        cost, metadata = compute_cost_for_service(plan_row, 'PCP_Office_Visit', 150.0)
        
        assert cost == 0.0
        assert metadata['cost_type'] == 'covered'
    
    def test_excluded_service(self):
        """'Excluded' should be treated as not covered"""
        plan_row = {
            'PCP_Office_Visit_money': None,
            'PCP_Office_Visit_percent': None,
            'PCP_Office_Visit_raw': 'Excluded'
        }
        cost, metadata = compute_cost_for_service(plan_row, 'PCP_Office_Visit', 150.0)

        assert cost == 150.0
        assert metadata['cost_type'] == 'not_covered_full_liability'
    
    def test_coinsurance_calculation(self):
        """Verify coinsurance is correctly calculated"""
        plan_row = {
            'ER_Visit_money': None,
            'ER_Visit_percent': 15.0,
            'ER_Visit_raw': '15% after deductible'
        }
        cost, metadata = compute_cost_for_service(plan_row, 'ER_Visit', 1000.0)
        
        assert cost == 150.0  # 15% of 1000
        assert metadata['cost_type'] == 'coinsurance'
    
    def test_fractional_percent(self):
        """Test with fractional percentage"""
        plan_row = {
            'Service_money': None,
            'Service_percent': 12.5,
            'Service_raw': '12.5%'
        }
        cost, metadata = compute_cost_for_service(plan_row, 'Service', 200.0)
        
        assert cost == 25.0  # 12.5% of 200
        assert metadata['cost_type'] == 'coinsurance'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
