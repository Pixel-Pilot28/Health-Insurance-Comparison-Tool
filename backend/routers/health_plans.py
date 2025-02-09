from fastapi import APIRouter, HTTPException
import csv
import os
from typing import Dict, Any

# Dynamically resolve the path to the data file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HEALTH_PLAN_FILE = os.path.join(BASE_DIR, "../data/health_plan_info.csv")

router = APIRouter()

def parse_cost(value: str) -> float:
    """
    Convert cost value to a float. Handles decimals, percentages, and whole numbers.
    """
    value = value.strip()
    if value.endswith("%"):  # Percentage case
        return float(value.strip("%")) / 100
    try:
        return float(value)  # Handle decimals and whole numbers
    except ValueError:
        raise ValueError(f"Invalid cost format: {value}")

def get_parsed_health_plans() -> Dict[str, Dict[str, Any]]:
    """
    Parse the health_plan_info.csv file into a structured dictionary.

    :return: Dictionary with plan IDs as keys and plan details as values.
    """
    
    try:
        with open(HEALTH_PLAN_FILE, mode="r") as csvfile:
            reader = csv.DictReader(csvfile)
            plans = {}

            for row in reader:
                # Extract unique plan name as ID
                plan_id = row["Short Name"]
                enrollment_type = row["Enrollment Type"]
                # plan_type = plan_id[-1]  # S, SF, or SO for enrollment type
                # plan_name = plan_id[:-2].strip()  # Remove enrollment type for display

                # Determine enrollment-specific fields
                premium = parse_cost(row["2025 Monthly - Empl. Pays"])
                deductible = parse_cost(row["Calendar Year Deductible"])
                oop_max = float("inf")  # Default to infinity if not provided
                premium = parse_cost(row["2025 Monthly - Empl. Pays"])
                deductible = parse_cost(row["Calendar Year Deductible"])
                premium = parse_cost(row["2025 Monthly - Empl. Pays"])
                deductible = parse_cost(row["Calendar Year Deductible"])
                hsa_pass_through = parse_cost(row["Premium Pass Through HSA/HRA Contribution"])

                # Extract HSA/HRA information
                hsa_hra_type = row["Services & Benefits - Type of Account"]
                hsa_contribution = parse_cost(row["Premium Pass Through HSA/HRA Contribution"])

                # Extract service costs
                services = {
                    "Primary Care": parse_cost(row["Primary/Specialty Care - Primary Care Office Visit"]),
                    "Specialist": parse_cost(row["Primary/Specialty Care - Specialist Office Visit"]),
                    "Emergency Care": parse_cost(row["Emergency & Urgent Care - Emergency Care"]),
                    "Urgent Care": parse_cost(row["Emergency & Urgent Care - Urgent Care"]),
                    "Accidental Injury": parse_cost(row["Emergency & Urgent Care - Accidental Injuries"]),
                    "Inpatient Admission": parse_cost(row["Surgery & Hospital Charges - Hospital Inpatient Cost"]),
                    "Room and Board": parse_cost(row["Surgery & Hospital Charges - Room & Board Charges"]),
                    "Outpatient Surgery": parse_cost(row["Surgery & Hospital Charges - Doctor Costs Outpatient Surgery"]),
                    "Outpatient Tests": parse_cost(row["Surgery & Hospital Charges - Outpatient Tests"]),
                    "Simple Labs": parse_cost(row["Lab, X-Ray & Other Diagnostic Tests - Simple Diagnostic Tests/Procedures"]),
                    "Complex Labs": parse_cost(row["Lab, X-Ray & Other Diagnostic Tests - Complex Diagnostic Tests/Procedures"]),
                    "Medications Tier 0": parse_cost(row["Prescription Drugs - Tier 0 Prescriptions"]),
                    "Medications Tier 1": parse_cost(row["Prescription Drugs - Tier 1 Prescriptions"]),
                    "Medications Tier 2": parse_cost(row["Prescription Drugs - Tier 2 Prescriptions"]),
                    "Medications Tier 3": parse_cost(row["Prescription Drugs - Tier 3 Prescriptions"]),
                    "Medications Tier 4": parse_cost(row["Prescription Drugs - Tier 4 Prescriptions"]),
                    "Medications Tier 5": parse_cost(row["Prescription Drugs - Tier 5 Prescriptions"]),
                    "ABA": parse_cost(row["Treatment, Devices, and Services - Applied Behavioral Analysis (ABA)"]),
                    "Chiropractic": parse_cost(row["Treatment, Devices, and Services - Chiropractic"]),
                    "OT": parse_cost(row["Treatment, Devices, and Services - Occupational Therapy"]),
                    "Speech Therapy": parse_cost(row["Treatment, Devices, and Services - Speech Therapy"]),
                    "Physical Therapy": parse_cost(row["Treatment, Devices, and Services - Physical Therapy"]),
                    "Infertility Services": parse_cost(row["Treatment, Devices, and Services - Infertility Services"]),
                    "Hearing Services": parse_cost(row["Treatment, Devices, and Services - Hearing Services"]),
                    "Maternity Care": parse_cost(row["Treatment, Devices, and Services - Maternity Care - Hospital Stay"]),
                }

                # Store plan data
                plans[plan_id] = {
                    "plan_name": plan_id,
                    "enrollment_type": enrollment_type,
                    "premium": premium,
                    "deductible": deductible,
                    "oop_max": oop_max,
                    "hsa_hra_type": hsa_hra_type,
                    "hsa_contribution": hsa_contribution,
                    "services": services,
                    "hsa_pass_through" : hsa_pass_through,
                }
    except FileNotFoundError:
        raise RuntimeError(f"Health plan file not found: {HEALTH_PLAN_FILE}")
    except Exception as e:
        raise RuntimeError(f"Error parsing health plans: {e}")

    return plans

@router.get("/health-plans", response_model=dict)
async def get_health_plans():
    """
    Endpoint to retrieve parsed health plan data.
    """
    return get_parsed_health_plans()

# Example usage
if __name__ == "__main__":
    parsed_data = get_parsed_health_plans()
    # print(parsed_data)


