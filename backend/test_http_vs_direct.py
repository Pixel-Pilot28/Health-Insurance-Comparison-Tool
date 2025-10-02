#!/usr/bin/env python3
"""
HTTP server test to isolate the exact issue between direct calls and HTTP calls
"""
import sys
import os
import asyncio
import requests
import json

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_http_vs_direct():
    """Compare HTTP request vs direct function call"""
    
    # The exact same data that worked in direct test
    test_data = {
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
        "preferences": {
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
    }
    
    print("🧪 Testing identical data via HTTP vs Direct call...")
    print(f"📊 Test data: {json.dumps(test_data, indent=2)}")
    
    # Test 1: Direct function call (we know this works)
    print("\n🔄 Testing DIRECT function call...")
    try:
        from routers.recommendation import RecommendationRequest, generate_recommendations
        
        request = RecommendationRequest(**test_data)
        
        async def test_direct():
            result = await generate_recommendations(request)
            return result
            
        direct_result = asyncio.run(test_direct())
        print("✅ DIRECT call: SUCCESS!")
        print(f"   - Generated {len(direct_result.get('recommendations', []))} recommendations")
        
    except Exception as e:
        print(f"❌ DIRECT call failed: {e}")
        return False
    
    # Test 2: HTTP call with exact same data
    print("\n🌐 Testing HTTP request...")
    try:
        response = requests.post(
            'http://localhost:8000/api/recommendations/generate', 
            json=test_data,
            timeout=30
        )
        print(f"📡 HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ HTTP call: SUCCESS!")
            print(f"   - Generated {len(result.get('recommendations', []))} recommendations")
            return True
        else:
            print(f"❌ HTTP call failed: {response.status_code}")
            print(f"   - Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ HTTP call failed: Server not running")
        return False
    except Exception as e:
        print(f"❌ HTTP call failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting HTTP vs Direct comparison test...")
    success = test_http_vs_direct()
    
    if success:
        print("\n🎉 BOTH DIRECT AND HTTP WORK! Issue resolved!")
    else:
        print("\n💥 HTTP still failing while direct works. Need to investigate server setup.")