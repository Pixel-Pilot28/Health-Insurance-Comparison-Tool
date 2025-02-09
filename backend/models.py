from pydantic import BaseModel
from typing import List, Optional, Dict


class HSAData(BaseModel):
    contribution: float
    limit: float
    percent_spent: float

class FSAData(BaseModel):
    contribution: float
    limit: float

class MedicareData(BaseModel):
    part_b_premium: float
    covered_people: int

class UserData(BaseModel):
    plan_type: str
    income: float
    tax_rate: float
    assumed_rate_of_return: float
    hsa: HSAData
    fsa: FSAData
    medicare: MedicareData

class MedicalNeed(BaseModel):
    count: int
    dates: List[str]

class InputDetails(BaseModel):
    user_data: UserData
    medical_needs: Dict[str, MedicalNeed]

# class HealthPlan(BaseModel):
#     id: int
#     name: str
#     option: str
#     network_type: str
#     attributes: Dict

# class UserInput(BaseModel):
#     primary_care_visits: int
#     primary_care_dates: List[str]

#     specialist_visits: int
#     specialist_dates: List[str]
    
#     emergency_visits: int
#     emergency_dates: List[str]

#     urgent_care_visits: int
#     urgent_care_dates: List[str]

#     Accidental_injury_visits: int
#     Accidental_injury_dates: List[str]

#     inpatient_admission_visits: int
#     inpatient_admission_dates: List[str]

#     room_and_board_visits: int
#     room_and_board_dates: List[str]

#     outpatient_surgery_visits: int
#     outpatient_surgery_dates: List[str]

#     outpatient_tests_visits: int
#     outpatient_tests_dates: List[str]

#     simple_labs_visits: int
#     simple_labs_dates: List[str]

#     complex_labs_visits: int
#     complex_labs_dates: List[str]

#     aba_visits: int
#     aba_dates: List[str]

#     chiropractic_visits: int
#     chiropractic_dates: List[str]

#     ot_visits: int
#     ot_dates: List[str]

#     speech_therapy_visits: int
#     speech_therapy_dates: List[str]
    
#     medications_tier_0_visits: int
#     medications_tier_0_dates: List[str]

#     medications_tier_1_visits: int
#     medications_tier_1_dates: List[str]

#     medications_tier_2_visits: int
#     medications_tier_2_dates: List[str]

#     medications_tier_3_visits: int
#     medications_tier_3_dates: List[str]

#     medications_tier_4_visits: int
#     medications_tier_4_dates: List[str]

#     medications_tier_5_visits: int
#     medications_tier_5_dates: List[str]

#     # surgeries: int  
#     # medication_usage: Dict[str, int]  # e.g., {"Tier 1": 5, "Tier 2": 3}
