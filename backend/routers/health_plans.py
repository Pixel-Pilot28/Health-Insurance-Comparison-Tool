from fastapi import APIRouter
import csv
import math
import os
from typing import Dict, Any, Optional, Tuple

# Dynamically resolve the path to the data files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEGACY_HEALTH_PLAN_FILE = os.path.join(BASE_DIR, "../data/health_plan_info.csv")
PARSED_HEALTH_PLAN_FILE = os.path.join(BASE_DIR, "../data/health_plan_info_parsed.csv")

router = APIRouter()

# Column handling rules for parsed data
FLOAT_SUFFIXES = (
    "_money",
    "_percent",
    "_cap",
    "_min_value",
    "_max_value",
    "_ded_money",
    "_ded_money_max",
    "_ded_per_person",
    "_ded_family",
    "_secondary_copay",
    "_secondary_coinsurance",
    "_visits_limit",
)

FLOAT_PREFIXES = ("Biweekly_", "Monthly_", "Annual_")
FLOAT_KEYS = {"Govt_pct", "Emp_pct"}

BOOL_SUFFIXES = (
    "_applies_after_deductible",
    "_first_visit_only",
    "_network_only",
    "_prior_authorization",
    "_is_covered",
)

TRUE_VALUES = {"true", "t", "1", "yes", "y"}
FALSE_VALUES = {"false", "f", "0", "no", "n", "", "nan", "none"}

ENROLLMENT_TO_DED_SUFFIX = {
    "Self": "Self",
    "Self + One": "Self_Plus_One",
    "Self + Family": "Self_And_Family",
}

ENROLLMENT_TO_CONTRIB_SUFFIX = {
    "Self": "Self",
    "Self + One": "Self_Plus_One",
    "Self + Family": "Self_&_Family",
}

SERVICE_COLUMN_MAPPING = {
    "Primary Care": "Primary_Care_Office_Visit",
    "Specialist": "Specialist_Office_Visit",
    "Emergency Care": "Emergency_Care",
    "Urgent Care": "Urgent_Care",
    "Accidental Injury": "Accidental_Injury",
    "Inpatient Admission": "Hospital_Inpatient_Cost_Per_Admission",
    "Room and Board": "Hospital_Room_Costs",
    "Outpatient Surgery": "Other_Outpatient_Surgery_Costs",
    "Outpatient Tests": "Diagnostic_Tests_Or_Procedures_Blood_Tests_X_Rays_Urinalysis_Ultrasounds",
    "Simple Labs": "Diagnostic_Tests_Or_Procedures_Blood_Tests_X_Rays_Urinalysis_Ultrasounds",
    "Complex Labs": "Diagnostic_Tests_Or_Procedures_CT_Scans_MRIs_PET_Scans",
    "Medications Tier 0": "Tier_0",
    "Medications Tier 1": "Tier_1",
    "Medications Tier 2": "Tier_2",
    "Medications Tier 3": "Tier_3",
    "Medications Tier 4": "Tier_4",
    "Medications Tier 5": "Tier_5",
    "ABA": "Applied_Behavioral_Analysis_(ABA)",
    "Chiropractic": "Chiropractic",
    "OT": "Occupational_Therapy",
    "Speech Therapy": "Speech_Therapy",
    "Physical Therapy": "Physical_Therapy",
    "Infertility Services": "Diagnosis_and_Treatment_(Infertility_Services)",
    "Hearing Services": "Hearing_Services",
    "Maternity Care": "Prenatal_Care,_Screening_for_Gestational_Diabetes,_Delivery,_and_Postpartum_Care_(Maternity_Care)",
}


def parse_cost(value: str) -> float:
    """Legacy numeric conversion used for the pre-parsed CSV."""
    if value is None:
        return 0.0

    cleaned = value.strip()

    if not cleaned or cleaned.lower() in {"n/a", "na", "not applicable"}:
        return 0.0

    if cleaned.endswith("%"):
        return float(cleaned.strip("%")) / 100.0

    try:
        return float(cleaned.replace(",", ""))
    except ValueError as exc:
        raise ValueError(f"Invalid cost format: {value}") from exc


def parse_optional_float(value: Any) -> Optional[float]:
    """Best-effort conversion that preserves None for missing values."""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)

    cleaned = str(value).strip()

    if not cleaned:
        return None

    lowered = cleaned.lower()
    if lowered in {"n/a", "na", "not applicable", "varies", "see brochure", "see plan brochure"}:
        return None

    if cleaned.endswith("%"):
        cleaned = cleaned[:-1]

    cleaned = cleaned.replace("$", "").replace(",", "")

    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_optional_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    cleaned = str(value).strip().lower()

    if cleaned in TRUE_VALUES:
        return True
    if cleaned in FALSE_VALUES:
        return False

    return False


def normalise_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


RAW_NATIONAL_PLAN_NAMES = {
    "APWU Health Plan",
    "Aetna HealthFund CDHP and Aetna Value Plan",
    "Aetna Open Access  (National H/B Option)",
    "Aetna Open Access (National High Option Only)",
    "Aetna: HDHP/Aetna Direct/Aetna ADV",
    "Blue Cross and Blue Shield",
    "Compass Rose Health Plan",
    "Foreign Service Benefit Plan",
    "GEHA",
    "GEHA Indemnity Benefit Plan",
    "MHBP",
    "Panama Canal Area Benefit Plan",
    "SAMBA",
    "UnitedHealthcare Insurance Company, Inc. (A HDHP with a Health Savings Account (HSA))",
    "UnitedHealthcare Insurance Company, Inc. (Choice Open Access)",
    "UnitedHealthcare Insurance Company, Inc. Choice Plus Primary East",
    "UnitedHealthcare Insurance Company, Inc. Choice Plus Primary West",
    "UnitedHealthcare Insurance Company, Inc. Choice Primary West",
}

NATIONAL_PLAN_NAME_SET = {normalise_string(name).lower() for name in RAW_NATIONAL_PLAN_NAMES}
NATIONAL_PLAN_PREFIXES = tuple(
    normalise_string(prefix).lower()
    for prefix in (
        "UnitedHealthcare Insurance Company, Inc.",
    )
)


def is_national_plan(plan_name: Any) -> bool:
    """Return True if the supplied plan name corresponds to a nationwide plan."""

    if plan_name is None:
        return False

    normalised_name = normalise_string(plan_name).lower()

    if not normalised_name:
        return False

    if normalised_name in NATIONAL_PLAN_NAME_SET:
        return True

    return any(normalised_name.startswith(prefix) for prefix in NATIONAL_PLAN_PREFIXES)


def convert_parsed_row(row: Dict[str, Any]) -> Dict[str, Any]:
    converted: Dict[str, Any] = {}

    for key, value in row.items():
        if value is None:
            converted[key] = None
            continue

        if key in FLOAT_KEYS or any(key.startswith(prefix) for prefix in FLOAT_PREFIXES) or any(
            key.endswith(suffix) for suffix in FLOAT_SUFFIXES
        ):
            converted[key] = parse_optional_float(value)
        elif any(key.endswith(suffix) for suffix in BOOL_SUFFIXES):
            converted[key] = parse_optional_bool(value)
        else:
            converted[key] = value

    return converted


def build_plan_name(row: Dict[str, Any], plan_id: str) -> str:
    plan_name = normalise_string(row.get("Plan_Name"))
    option_name = normalise_string(row.get("Plan_Option_Name"))
    code = normalise_string(row.get("Plan_Code"))

    parts = [p for p in (plan_name, option_name) if p]

    if parts:
        display = " - ".join(dict.fromkeys(parts))  # remove duplicates while preserving order
    else:
        display = plan_id

    if code and code not in display:
        display = f"{display} ({code})"

    return display


def extract_services(row: Dict[str, Any], converted_row: Dict[str, Any]) -> Dict[str, Any]:
    services: Dict[str, Any] = {}

    for service_name, column_base in SERVICE_COLUMN_MAPPING.items():
        money_key = f"{column_base}_money"
        percent_key = f"{column_base}_percent"
        raw_key = f"{column_base}_raw"

        money_value = converted_row.get(money_key)
        if money_value is not None:
            services[service_name] = money_value
            continue

        percent_value_raw = row.get(percent_key)
        if percent_value_raw:
            percent_str = str(percent_value_raw).strip()
            if percent_str and percent_str.lower() not in {"nan", "none"}:
                services[service_name] = f"{percent_str.rstrip('%')}%"
                continue

        raw_value = normalise_string(row.get(raw_key))
        if raw_value:
            services[service_name] = raw_value

    return services


def derive_oop_max(enrollment_type: str, row: Dict[str, Any]) -> float:
    suffix = ENROLLMENT_TO_DED_SUFFIX.get(enrollment_type, "Self")
    column = f"Annual_Out_Of_Pocket_Maximum_{suffix}_money"
    parsed_value = parse_optional_float(row.get(column))
    return parsed_value if parsed_value is not None else float("inf")


def derive_deductible(enrollment_type: str, row: Dict[str, Any]) -> float:
    suffix = ENROLLMENT_TO_DED_SUFFIX.get(enrollment_type, "Self")
    column = f"Annual_Deductible_{suffix}_money"
    parsed_value = parse_optional_float(row.get(column))
    return parsed_value if parsed_value is not None else 0.0


def derive_hsa_pass_through(enrollment_type: str, row: Dict[str, Any]) -> float:
    suffix = ENROLLMENT_TO_CONTRIB_SUFFIX.get(enrollment_type, "Self")
    column = f"Medical_account_contribution_({suffix})_money"
    parsed_value = parse_optional_float(row.get(column))
    return parsed_value if parsed_value is not None else 0.0


def derive_hsa_type(row: Dict[str, Any]) -> str:
    raw_type = normalise_string(row.get("Type_of_account_raw"))
    if not raw_type or raw_type.lower() in {"not applicable"}:
        return "N/A"
    if "savings" in raw_type.lower():
        return "HSA"
    if "reimbursement" in raw_type.lower():
        return "HRA"
    return raw_type


def build_plan_from_parsed_row(row: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    plan_id = normalise_string(row.get("Enrollment_Code"))
    if not plan_id:
        raise ValueError("Missing Enrollment_Code for parsed plan row")

    enrollment_type = normalise_string(row.get("Enrollment_Type")) or "Self"
    converted_row = convert_parsed_row(row)

    plan_details: Dict[str, Any] = dict(converted_row)

    plan_details.update(
        {
            "plan_name": build_plan_name(row, plan_id),
            "enrollment_type": enrollment_type,
            "premium": parse_optional_float(row.get("Monthly_Emp")) or 0.0,
            "deductible": derive_deductible(enrollment_type, row),
            "oop_max": derive_oop_max(enrollment_type, row),
            "hsa_hra_type": derive_hsa_type(row),
            "hsa_contribution": derive_hsa_pass_through(enrollment_type, row),
            "hsa_pass_through": derive_hsa_pass_through(enrollment_type, row),
            "services": extract_services(row, converted_row),
        }
    )

    return plan_id, plan_details


def build_plan_from_legacy_row(row: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    plan_id = row["Short Name"]
    enrollment_type = row["Enrollment Type"]

    premium = parse_cost(row["2025 Monthly - Empl. Pays"])
    deductible = parse_cost(row["Calendar Year Deductible"])

    catastrophic_limit_raw = row.get("Catastrophic Limit", "")
    oop_max = parse_cost(catastrophic_limit_raw)
    if oop_max == 0.0:
        oop_max = float("inf")

    hsa_pass_through = parse_cost(row["Premium Pass Through HSA/HRA Contribution"])

    hsa_hra_type = row["Services & Benefits - Type of Account"]
    hsa_contribution = parse_cost(row["Premium Pass Through HSA/HRA Contribution"])

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

    plan_details = {
        "plan_name": plan_id,
        "enrollment_type": enrollment_type,
        "premium": premium,
        "deductible": deductible,
        "oop_max": oop_max,
        "hsa_hra_type": hsa_hra_type,
        "hsa_contribution": hsa_contribution,
        "services": services,
        "hsa_pass_through": hsa_pass_through,
    }

    return plan_id, plan_details


def get_parsed_health_plans() -> Dict[str, Dict[str, Any]]:
    """
    Load health plan data into a structured dictionary keyed by plan ID.
    Prefers the enriched parsed CSV and falls back to the legacy file if needed.
    """

    data_file = PARSED_HEALTH_PLAN_FILE if os.path.exists(PARSED_HEALTH_PLAN_FILE) else LEGACY_HEALTH_PLAN_FILE

    if not os.path.exists(data_file):
        raise RuntimeError(f"Health plan file not found: {data_file}")

    plans: Dict[str, Dict[str, Any]] = {}

    try:
        with open(data_file, mode="r", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                plan_name_value = row.get("Plan_Name") or row.get("Short Name")

                if not is_national_plan(plan_name_value):
                    continue

                if data_file == PARSED_HEALTH_PLAN_FILE:
                    plan_id, plan_details = build_plan_from_parsed_row(row)
                else:
                    plan_id, plan_details = build_plan_from_legacy_row(row)

                plans[plan_id] = plan_details

    except Exception as exc:
        raise RuntimeError(f"Error parsing health plans: {exc}") from exc

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


