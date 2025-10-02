#!/usr/bin/env python3

import requests
import json

# Test data that mimics what the frontend sends
test_data = {
    "user_data": {
        "taxRate": 25,
        "planType": "Self"
    },
    "input_details": {
        "medicalNeeds": {
            "office_visits": 3,
            "specialist_visits": 1,
            "prescriptions": {
                "generic": 2,
                "brand": 0,
                "specialty": 0
            },
            "procedures": {
                "lab_tests": 2,
                "imaging": 1,
                "minor_surgery": 0
            }
        }
    },
    "preferences": {
        "risk_tolerance": "moderate",
        "cost_sensitivity": "high",
        "coverage_priority": "preventive",
        "max_monthly_premium": 500,
        "max_deductible": 2000,
        "hsa_preference": False,
        "family_size": 1,
        "age_group": "adult",
        "health_status": "good",
        "preferred_network_size": "large",
        "travel_frequency": "low"
    }
}

try:
    response = requests.post(
        "http://localhost:8000/api/recommendations/generate",
        json=test_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {response.headers}")
    print(f"Response Text: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success! Generated {len(data.get('recommendations', []))} recommendations")
    else:
        print(f"Error: {response.status_code}")
        
except Exception as e:
    print(f"Exception: {e}")