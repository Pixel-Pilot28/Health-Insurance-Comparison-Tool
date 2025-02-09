from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List
import json

try:
    from models import InputDetails
    from services.cost_calculator import calculate_costs
    from routers.health_plans import get_parsed_health_plans
except ImportError:
    from backend.models import InputDetails
    from backend.services.cost_calculator import calculate_costs
    from backend.routers.health_plans import get_parsed_health_plans

router = APIRouter()


# Define payload models
class InputDetails(BaseModel):
    service: List[str] = []
    count: int
    dates: List[str]

class UserData(BaseModel):
    planType: str
    income: float
    taxRate: float
    assumedRateOfReturn: float
    hsa: Dict[str, float]
    fsa: Dict[str, float]
    medicare: Dict[str, float]

class Payload(BaseModel):
    userData: UserData
    inputDetails: Dict[str, InputDetails]

@router.post("/user-data")
def save_user_data(payload: dict):
    """
    Save the user payload from the Data Input tab to a file.
    """
    try:
        with open("data/user_payload.json", "w") as f:
            json.dump(payload, f)
        return {"calculate.py": "User data saved successfully"}
    except Exception as e:
        print(f"Error saving user data: {e}")
        raise HTTPException(status_code=500, detail="Failed to save user data")


@router.get("/user-data")
def get_user_data():
    """
    Retrieve the most recent user payload for the Compare tab.
    """
    try:
        with open("data/user_payload.json", "r") as f:
            payload = json.load(f)
        return payload
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No user data found")
    except Exception as e:
        print(f"Error retrieving user data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user data")


@router.post("")
def calculate_cost(payload: Payload):
    """
    Calculate monthly and annual costs for each health plan.
    """
    try:
        # Extract user inputs
        user_data = payload.userData.dict()
        input_details = payload.inputDetails
        # print("Received Payload:", payload.dict())

        # Extract enrollment type
        enrollment_type = user_data.get("planType", "Self")
        # print("Extracted enrollment type from user data:", enrollment_type)

        # Convert InputDetails to a dictionary
        input_details_dict = {key: value.dict() for key, value in input_details.items()}
        # print("Converted Input Details:", input_details_dict)

        # Convert tax rate to decimal
        tax_rate = user_data["taxRate"] / 100
        # print("Processed tax rate:", tax_rate)

        # Load health plan data
        health_plans = get_parsed_health_plans()
        # print("Parsed plan:", health_plans)

        # Perform cost calculationsS
        try:
            results = calculate_costs(
            user_input=input_details_dict,
            tax_rate=tax_rate,
            plan_type=enrollment_type
        )

        except Exception as e:
            print(f"Error during cost calculations: {e}")
            raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")
        # print("Results", results)

        # Format response with monthly and annual breakdowns
        formatted_results = {
            plan_id: {
                "plan_name": plan_data["plan_name"],
                "monthly_breakdown": plan_data["monthly_breakdown"],  # Directly use the pre-formatted dictionary
                "annual_cost": plan_data["total_cost"],
                "tax_savings": plan_data["tax_savings"],
                "cumulative_cost": plan_data["cumulative_cost"],
                "unused_hsa": plan_data["unused_hsa"],
                "unused_fsa": plan_data["unused_fsa"]
            }
            for plan_id, plan_data in results.items()
        }
        return {"message": "Cost calculation successful", "plans": formatted_results}
    except Exception as e:
        print(f"Unhandled error in calculate endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Error during calculation: {str(e)}")




 