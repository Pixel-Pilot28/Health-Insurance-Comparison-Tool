#!/usr/bin/env python3
"""
Direct test script to debug the recommendation generation function
"""
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_recommendation_generation():
    """Test the recommendation generation directly"""
    try:
        print("🔍 Starting direct recommendation test...")
        
        # Import the required modules
        from routers.recommendation import RecommendationRequest, generate_recommendations
        import asyncio
        
        print("✅ Successfully imported recommendation modules")
        
        # Create sample request data that matches what frontend sends
        sample_data = {
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
        
        print("✅ Created sample request data")
        
        # Create the request object
        request = RecommendationRequest(**sample_data)
        print("✅ Successfully created RecommendationRequest object")
        
        # Run the async function
        async def run_test():
            try:
                result = await generate_recommendations(request)
                return result
            except Exception as e:
                print(f"❌ Error in generate_recommendations: {e}")
                import traceback
                traceback.print_exc()
                return None
        
        # Execute the async function
        result = asyncio.run(run_test())
        
        if result:
            print(f"🎉 SUCCESS! Generated recommendations: {len(result.get('recommendations', []))} plans")
            return True
        else:
            print("❌ Failed to generate recommendations")
            return False
            
    except Exception as e:
        print(f"❌ Error in test setup: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_recommendation_generation()
    if success:
        print("\n🎯 CONCLUSION: Recommendation generation works!")
    else:
        print("\n💥 CONCLUSION: There are issues with recommendation generation.")