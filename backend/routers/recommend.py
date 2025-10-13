from fastapi import APIRouter, HTTPException
from typing import Dict, Any
try:
    from ..models import InputDetails
except ImportError:
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


@router.post("/")
def recommend_plan_endpoint(input_details: InputDetails):
    return recommend_plan(input_details)
