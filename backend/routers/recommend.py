from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from services.recommendation_engine import score_plans
from models import InputDetails

router = APIRouter()
def recommend_plan(input_details: InputDetails):
    """
    Recommend the best health plan based on user input.
    """
    user_data = input_details.user_data
    medical_needs = input_details.medical_needs

    # Mock implementation of recommendations
    recommendation = "Plan A is the best based on your inputs."

    # Example response with received data echoed back
    return {
        "status": "success",
        "recommendation": recommendation,
        "data": {
            "user_data": user_data,
            "medical_needs": medical_needs
        }
    }


# @router.post("/")
# def recommend_plan(user_input: UserInput):
#     try:
#         # Extract plan costs and user preferences
#         plan_costs = user_input.get("plan_costs")
#         user_preferences = user_input.get("preferences", {})

#         if not plan_costs:
#             raise ValueError("Plan costs are required in the input.")

#         # Generate ranked recommendations
#         ranked_plans = score_plans(plan_costs, user_preferences)
#         return {"status": "success", "data": ranked_plans}
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail="An error occurred during recommendation.")
