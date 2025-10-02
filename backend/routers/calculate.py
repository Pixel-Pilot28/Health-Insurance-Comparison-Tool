from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from ..services.cost_calculator import calculate_costs
from ..models import CalculationPayload
from .health_plans import get_parsed_health_plans
import json

router = APIRouter()


# Define payload models
class InputDetails(BaseModel):
    service: List[str] = []
    count: int
    dates: List[str]

class UserData(BaseModel):
    planType: str
    income: str  # Allow string input and convert in processing
    taxRate: str  # Allow string input and convert in processing
    assumedRateOfReturn: str  # Allow string input and convert in processing
    hsa: Dict[str, str]  # Allow string input
    fsa: Dict[str, str]  # Allow string input
    medicare: Dict[str, str]  # Allow string input

class Payload(BaseModel):
    userData: UserData
    inputDetails: Dict[str, InputDetails]

@router.post("/user-data")
async def save_user_data(data: dict):
    """
    Save user data (e.g., from a form) to a JSON file.
    """
    try:
        with open("backend/data/user_payload.json", "w") as f:
            json.dump(data, f, indent=4)
        print(f"Received user data: {data}")
        return {"status": "success", "message": "User data saved successfully", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving user data: {str(e)}")


@router.get("/user-data")
async def get_user_data():
    """
    Retrieve the user payload from the file.
    """
    try:
        with open("backend/data/user_payload.json", "r") as f:
            data = json.load(f)
        return {"status": "success", "data": data}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="User data not found")
    except Exception as e:
        print(f"Error reading user data: {e}")
        raise HTTPException(status_code=500, detail="Failed to read user data")


@router.post("/calculate")
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

        # Convert string values to numbers and tax rate to decimal
        tax_rate = float(user_data["taxRate"]) / 100
        user_data["income"] = float(user_data["income"]) if user_data["income"] else 0
        user_data["assumedRateOfReturn"] = float(user_data["assumedRateOfReturn"]) if user_data["assumedRateOfReturn"] else 0
        
        # Convert HSA, FSA, Medicare values to floats
        for key, value in user_data["hsa"].items():
            user_data["hsa"][key] = float(value) if value else 0
        for key, value in user_data["fsa"].items():
            user_data["fsa"][key] = float(value) if value else 0
        for key, value in user_data["medicare"].items():
            user_data["medicare"][key] = float(value) if value else 0
        # print("Processed tax rate:", tax_rate)

        # Load health plan data
        health_plans = get_parsed_health_plans()
        # print("Parsed plan:", health_plans)

        # Perform cost calculations
        try:
            results = calculate_costs(
            user_input=input_details_dict,
            user_data=user_data,
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




