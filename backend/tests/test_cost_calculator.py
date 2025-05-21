import pytest
from unittest.mock import patch
from backend.services.cost_calculator import calculate_costs

# Mock data for get_parsed_health_plans
MOCK_HEALTH_PLANS = {
    'hsa_with_pass_through': {
        'plan_id': 'hsa_with_pass_through',
        'plan_name': 'HSA Plan with Pass-Through',
        'enrollment_type': 'Self',
        'premium': 100,
        'deductible': 1500,
        'oop_max': 3000,
        'hsa_hra_type': 'HSA',
        'hsa_pass_through': 500,
        'services': {},
    },
    'hsa_no_pass_through': {
        'plan_id': 'hsa_no_pass_through',
        'plan_name': 'HSA Plan without Pass-Through',
        'enrollment_type': 'Self',
        'premium': 120,
        'deductible': 1000,
        'oop_max': 2500,
        'hsa_hra_type': 'HSA',
        'hsa_pass_through': 0,
        'services': {},
    },
    'ppo_plan': {
        'plan_id': 'ppo_plan',
        'plan_name': 'PPO Plan',
        'enrollment_type': 'Self',
        'premium': 200,
        'deductible': 500,
        'oop_max': 4000,
        'hsa_hra_type': 'N/A',
        'services': {},
    }
}

# Mock data for load_service_costs
MOCK_SERVICE_COSTS = {
    'some_service': 100
}

# Helper function to create user_input
def create_user_input(hsacontribution=0, fsa_contribution=0):
    return {
        'hsacontribution': hsacontribution,
        'fsa': {'contribution': fsa_contribution},
        'income': 50000,
        'assumedRateOfReturn': 0.05,
        'hsaPercentSpent': 1.0,
        'planType': 'Self', # Added as it might be accessed by the function
    }

@patch('backend.services.cost_calculator.get_parsed_health_plans', return_value=MOCK_HEALTH_PLANS)
@patch('backend.services.cost_calculator.load_service_costs', return_value=MOCK_SERVICE_COSTS)
def test_hsa_with_user_and_employer_contribution(mock_load_costs, mock_get_plans):
    user_input = create_user_input(hsacontribution=2000)
    tax_rate = 0.25
    plan_type = 'Self'
    
    results = calculate_costs(user_input, tax_rate, plan_type)
    
    assert 'hsa_with_pass_through' in results
    assert results['hsa_with_pass_through']['tax_savings'] == 500.0 # 2000 * 0.25

@patch('backend.services.cost_calculator.get_parsed_health_plans', return_value=MOCK_HEALTH_PLANS)
@patch('backend.services.cost_calculator.load_service_costs', return_value=MOCK_SERVICE_COSTS)
def test_hsa_with_user_contribution_no_employer(mock_load_costs, mock_get_plans):
    user_input = create_user_input(hsacontribution=1500)
    tax_rate = 0.20
    plan_type = 'Self'
    
    results = calculate_costs(user_input, tax_rate, plan_type)
    
    assert 'hsa_no_pass_through' in results
    assert results['hsa_no_pass_through']['tax_savings'] == 300.0 # 1500 * 0.20

@patch('backend.services.cost_calculator.get_parsed_health_plans', return_value=MOCK_HEALTH_PLANS)
@patch('backend.services.cost_calculator.load_service_costs', return_value=MOCK_SERVICE_COSTS)
def test_hsa_no_user_contribution_with_employer(mock_load_costs, mock_get_plans):
    user_input = create_user_input(hsacontribution=0)
    tax_rate = 0.25
    plan_type = 'Self'
    
    results = calculate_costs(user_input, tax_rate, plan_type)
    
    assert 'hsa_with_pass_through' in results
    assert results['hsa_with_pass_through']['tax_savings'] == 0.0 # 0 * 0.25

@patch('backend.services.cost_calculator.get_parsed_health_plans', return_value=MOCK_HEALTH_PLANS)
@patch('backend.services.cost_calculator.load_service_costs', return_value=MOCK_SERVICE_COSTS)
def test_fsa_contribution(mock_load_costs, mock_get_plans):
    user_input = create_user_input(fsa_contribution=1000)
    tax_rate = 0.25
    plan_type = 'Self'
    
    results = calculate_costs(user_input, tax_rate, plan_type)
    
    assert 'ppo_plan' in results
    assert results['ppo_plan']['tax_savings'] == 250.0 # 1000 * 0.25
