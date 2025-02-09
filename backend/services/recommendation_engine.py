from fastapi import APIRouter
from models import InputDetails
from typing import List, Dict, Any

router = APIRouter()

@router.post("/")
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

def score_plans(
    plan_costs: Dict[str, Any],
    user_preferences: Dict[str, float]
) -> List[Dict[str, Any]]:
    """
    Rank health plans based on user-defined preferences and calculated costs.

    :param plan_costs: Dictionary of plans with calculated costs and details.
    :param user_preferences: Weights for preferences (cost, flexibility, risk, tax savings).
    :return: List of plans ranked by their overall scores.
    """
    # Default weights if user preferences are neutral
    default_weights = {
        "cost": 0.25,
        "flexibility": 0.25,
        "risk": 0.25,
        "tax_savings": 0.25
    }

    # Merge default weights with user-defined preferences
    weights = {**default_weights, **user_preferences}

    scored_plans = []

    for plan_id, plan_data in plan_costs.items():
        # Extract necessary details
        total_cost = plan_data["total_cost"]
        tax_savings = plan_data["tax_savings"]
        flexibility_score = plan_data.get("flexibility_score", 1.0)  # Placeholder
        risk_score = plan_data.get("risk_score", 1.0)  # Placeholder

        # Normalize cost and tax savings (lower cost and higher tax savings are better)
        cost_score = 1 / (1 + total_cost)
        tax_savings_score = tax_savings

        # Calculate overall score
        overall_score = (
            weights["cost"] * cost_score +
            weights["flexibility"] * flexibility_score +
            weights["risk"] * risk_score +
            weights["tax_savings"] * tax_savings_score
        )

        scored_plans.append({
            "plan_id": plan_id,
            "plan_name": plan_data["plan_name"],
            "total_cost": total_cost,
            "flexibility_score": flexibility_score,
            "risk_score": risk_score,
            "tax_savings": tax_savings,
            "overall_score": overall_score
        })

    # Sort plans by overall score in descending order
    scored_plans.sort(key=lambda x: x["overall_score"], reverse=True)

    return scored_plans

# Example Usage
if __name__ == "__main__":
    example_plan_costs = {
        "plan_1": {
            "plan_name": "Plan A",
            "total_cost": 5000,
            "tax_savings": 1200,
            "flexibility_score": 0.8,
            "risk_score": 0.9
        },
        "plan_2": {
            "plan_name": "Plan B",
            "total_cost": 4500,
            "tax_savings": 1000,
            "flexibility_score": 0.9,
            "risk_score": 0.85
        }
    }

    user_preferences = {
        "cost": 0.4,
        "flexibility": 0.2,
        "risk": 0.2,
        "tax_savings": 0.2
    }

    ranked_plans = score_plans(example_plan_costs, user_preferences)
    for plan in ranked_plans:
        print(plan)
