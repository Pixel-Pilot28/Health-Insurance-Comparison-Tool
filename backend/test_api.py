#!/usr/bin/env python3
"""
Test script to verify the recommendation API without server issues
"""
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Test the imports
    from routers.recommendation import RecommendationRequest, PreferencesRequest
    print("✓ Successfully imported recommendation models")
    
    # Test creating a PreferencesRequest with sample data
    sample_prefs = {
        "risk_tolerance": "moderate",
        "cost_sensitivity": "high", 
        "coverage_priority": "preventive",
        "hsa_preference": False,
        "family_size": 1,
        "age_group": "adult",
        "health_status": "good", 
        "preferred_network_size": "large",
        "travel_frequency": "low"
    }
    
    prefs = PreferencesRequest(**sample_prefs)
    print("✓ Successfully created PreferencesRequest")
    
    # Test creating a RecommendationRequest
    sample_request = {
        "user_data": {
            "planType": "Self",
            "income": "75000",
            "taxRate": "25"
        },
        "input_details": {
            "medical_needs": {
                "office_visits": {"count": 3, "dates": ["2024-01-15"]}
            }
        },
        "preferences": sample_prefs
    }
    
    req = RecommendationRequest(**sample_request)
    print("✓ Successfully created RecommendationRequest")
    print("✓ All validations passed!")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()