import json
from typing import List, Dict, Any, Tuple
import os

try:
    # For production use with uvicorn or FastAPI
    from ..routers.health_plans import get_parsed_health_plans
except ImportError:
    try:
        # Fallback for different import contexts
        from routers.health_plans import get_parsed_health_plans
    except ImportError:
        # For running script directly with `python -m`
        from backend.routers.health_plans import get_parsed_health_plans

# Dynamically resolve the path to the average service costs file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_COSTS_FILE = os.path.join(BASE_DIR, "../data/service_costs.json")

def load_service_costs() -> Dict[str, float]:
    """
    Load average service costs from the JSON file.
    """
    try:
        with open(SERVICE_COSTS_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        raise RuntimeError(f"Service costs file not found: {SERVICE_COSTS_FILE}")
    except Exception as e:
        raise RuntimeError(f"Error loading service costs: {e}")

def calculate_tax_savings(contribution: float, tax_rate: float) -> float:
    """
    Calculate tax savings from HSA or FSA contributions.
    """
    return contribution * tax_rate

def calculate_hsa_growth(hsa_contribution: float, hsa_pass_through: float,
                         hsa_percent_spent: float, assumed_rate_of_return: float) -> float:
    """
    Calculate potential HSA growth on a monthly basis, including investment gains.
    """
    monthly_hsa_contribution = hsa_contribution / 12
    monthly_pass_through = hsa_pass_through / 12
    hsa_balance = 0.0
    total_growth = 0.0

    for month in range(1, 13):
        hsa_balance += monthly_hsa_contribution + monthly_pass_through
        # Spend a percentage of the balance (spread over the year)
        amount_spent = hsa_balance * (hsa_percent_spent / 12)
        hsa_balance -= amount_spent
        monthly_return_rate = (1 + assumed_rate_of_return) ** (1/12) - 1
        investment_gain = hsa_balance * monthly_return_rate
        hsa_balance += investment_gain
        total_growth += investment_gain

    return round(total_growth, 2)
    

def map_service_to_column_base(service_name: str) -> str:
    """
    Map a service name from user input to the corresponding column base name in parsed data.
    
    Args:
        service_name: Service name from user input (e.g., "PrimaryCareVisit")
    
    Returns:
        Column base name (e.g., "Primary_Care_Office_Visit")
    
    Note: These mappings match the exact column names from OPM's 2026-fehb-plan-benefits_100525.xlsx
    after parsing. The column base excludes suffixes like _money, _percent, _raw, _applies_after_deductible, etc.
    Service names correspond to keys in service_costs.json.
    """
    # Map service names to actual OPM parsed column bases
    service_mapping = {
        # Office Visits
        'Primary Care': 'Primary_Care_Office_Visit',
        'Specialist': 'Specialist_Office_Visit',
        
        # Emergency & Urgent Care
        'Emergency Care': 'Emergency_Care',
        'Urgent Care': 'Urgent_Care',
        
        # Inpatient Services
        'Inpatient Admission': 'Hospital_Inpatient_Cost_Per_Admission',
        'Room and Board': 'Hospital_Room_Costs',
        
        # Outpatient Services
        'Outpatient Surgery': 'Other_Outpatient_Surgery_Costs',  # or Doctor_Costs_for_Outpatient_Surgery
        
        # Diagnostic Tests
        'Outpatient Tests': 'Diagnostic_Tests_or_Procedures_(e.g.,_Blood_Tests,_X_rays,_Urinalysis,_Ultrasounds)',
        'Simple Labs': 'Diagnostic_Tests_or_Procedures_(e.g.,_Blood_Tests,_X_rays,_Urinalysis,_Ultrasounds)',
        'Complex Labs': 'Diagnostic_Tests_or_Procedures_(e.g.,_CT_scans,_MRIs,_PET_Scans)',
        
        # Prescriptions (Tiers)
        'Medications Tier 0': 'Tier_0',
        'Medications Tier 1': 'Tier_1',
        'Medications Tier 2': 'Tier_2',
        'Medications Tier 3': 'Tier_3',
        'Medications Tier 4': 'Tier_4',
        'Medications Tier 5': 'Tier_5',
        
        # Therapy Services
        'ABA': 'Applied_Behavioral_Analysis_(ABA)',
        'Chiropractic': 'Chiropractic',
        'OT': 'Occupational_Therapy',
        'Speech Therapy': 'Speech_Therapy',
        'Physical Therapy': 'Physical_Therapy',
        
        # Specialized Services
        'Infertility Services': 'Diagnosis_and_Treatment_(Infertility_Services)',
        'Hearing Services': 'Hearing_Services',
        'Maternity Care': 'Prenatal_Care,_Screening_for_Gestational_Diabetes,_Delivery,_and_Postpartum_Care_(Maternity_Care)',
        
        # Mental Health
        'Mental Health Visit': 'Professional_Services_(Mental_Health_and_Substance_Use_Disorder)',
    }
    
    return service_mapping.get(service_name, service_name)


def compute_cost_for_service(plan_row: Dict[str, Any], service_col_base: str, 
                            allowed_charge: float) -> Tuple[float, Dict[str, Any]]:
    """
    Compute the cost for a specific service using parsed fields with deterministic priority.
    
    Priority order:
    1. money field (direct copay)
    2. percent field (coinsurance)
    3. raw field interpretation (covered, not covered, etc.)
    
    Args:
        plan_row: Dictionary containing plan data with parsed fields
        service_col_base: Base column name (e.g., "Primary_Care_Office_Visit")
        allowed_charge: The allowed/average charge for the service
    
    Returns:
        Tuple of (cost, metadata_dict)
        - cost: Member cost for the service (None if special handling needed)
        - metadata: Dict with flags and parsing info
    """
    money = plan_row.get(f"{service_col_base}_money")
    pct = plan_row.get(f"{service_col_base}_percent")
    raw = plan_row.get(f"{service_col_base}_raw")
    
    # Get special condition flags
    applies_after_deductible = plan_row.get(f"{service_col_base}_applies_after_deductible", False)
    first_visit_only = plan_row.get(f"{service_col_base}_first_visit_only", False)
    network_only = plan_row.get(f"{service_col_base}_network_only", False)
    prior_auth = plan_row.get(f"{service_col_base}_prior_authorization", False)
    
    metadata = {
        'applies_after_deductible': applies_after_deductible,
        'first_visit_only': first_visit_only,
        'network_only': network_only,
        'prior_authorization': prior_auth,
        'raw': raw,
        'cost_type': None  # Will be set to 'copay', 'coinsurance', 'covered', 'not_covered', or 'needs_review'
    }
    
    # Priority 1: Money field (direct copay)
    if money is not None:
        metadata['cost_type'] = 'copay'
        return float(money), metadata
    
    # Priority 2: Percent field (coinsurance)
    if pct is not None:
        metadata['cost_type'] = 'coinsurance'
        return (float(pct) / 100.0) * allowed_charge, metadata
    
    # Priority 3: Raw field interpretation
    if raw:
        lr = raw.lower().strip()
        
        # Check for "not covered" first (before "covered")
        if any(phrase in lr for phrase in ['not covered', 'excluded', 'not applicable']):
            metadata['cost_type'] = 'not_covered'
            return float('inf'), metadata
        
        # After deductible - needs special handling (before "covered" check)
        if 'after deductible' in lr and not money and not pct:
            metadata['cost_type'] = 'needs_review'
            return None, metadata
        
        # Fully covered
        if any(phrase in lr for phrase in ['covered', 'in-network', 'in network', '100%']):
            metadata['cost_type'] = 'covered'
            return 0.0, metadata
        
        # N/A
        if 'n/a' in lr or 'na' == lr:
            metadata['cost_type'] = 'not_covered'
            return float('inf'), metadata
    
    # Default: Unknown/needs manual review
    metadata['cost_type'] = 'needs_review'
    return None, metadata


def calculate_service_cost(service_cost: float, frequency: int, coverage: Dict[str, Any],
                           deductible_remaining: float, oop_remaining: float) -> Tuple[float, float, float, Dict[str, float]]:
    """
    Calculate the cost to the user for a specific service.
    Applies deductible, then copay (if defined), otherwise coinsurance.
    Finally, caps the cost by the out-of-pocket remaining.
    
    Returns:
      - user_pays: cost incurred for the service,
      - updated deductible_remaining,
      - updated oop_remaining,
      - breakdown of costs (deductible, copay, coinsurance).
    """
    user_pays = 0.0
    cost_breakdown = {'deductible': 0.0, 'copay': 0.0, 'coinsurance': 0.0}
    total_service_cost = service_cost * frequency

    # Apply deductible if applicable
    if coverage.get('deductible_applies', True):
        deductible_applied = min(total_service_cost, deductible_remaining)
        user_pays += deductible_applied
        deductible_remaining -= deductible_applied
        remaining_service_cost = total_service_cost - deductible_applied
        cost_breakdown['deductible'] = deductible_applied
    else:
        remaining_service_cost = total_service_cost

    # Apply copay if defined (and assume that if a copay exists, coinsurance is not applied)
    if coverage.get('copay', 0.0) > 0:
        copay_total = coverage['copay'] * frequency
        user_pays += copay_total
        cost_breakdown['copay'] = copay_total
    elif coverage.get('coinsurance', 0.0) > 0:
        coinsurance_cost = remaining_service_cost * coverage['coinsurance']
        user_pays += coinsurance_cost
        cost_breakdown['coinsurance'] = coinsurance_cost

    # Cap at out-of-pocket maximum
    if user_pays > oop_remaining:
        user_pays = oop_remaining
        oop_remaining = 0.0
    else:
        oop_remaining -= user_pays

    return round(user_pays, 2), round(deductible_remaining, 2), round(oop_remaining, 2), {k: round(v, 2) for k, v in cost_breakdown.items()}

def calculate_costs(user_input: Dict[str, Any], user_data: Dict[str, Any], tax_rate: float, plan_type: str) -> Dict[str, Any]:
    """
    Calculate monthly and annual costs for each health plan based on user inputs.
    Returns a dictionary of results keyed by plan ID.
    """
    try:
        print(f"DEBUG: calculate_costs called with plan_type={plan_type}")
        print(f"DEBUG: user_input keys: {list(user_input.keys()) if user_input else 'None'}")
        import sys
        sys.stdout.flush()
        
        plans = get_parsed_health_plans()
        print(f"DEBUG: Loaded {len(plans)} health plans")
        sys.stdout.flush()
        
        service_costs = load_service_costs()
        print(f"DEBUG: Loaded {len(service_costs)} service costs")
        sys.stdout.flush()
        
        results = {}

        for plan_id, plan_details in plans.items():
            print(f"DEBUG: Processing plan {plan_id} with enrollment type {plan_details.get('enrollment_type', 'Unknown')}")
            sys.stdout.flush()
            
            # Filter by enrollment type
            if plan_details['enrollment_type'] != plan_type:
                print(f"DEBUG: Skipping plan {plan_id} - enrollment type mismatch")
                sys.stdout.flush()
                continue

            try:
                # Determine if plan is HSA eligible
                has_hsa = (plan_details.get('hsa_hra_type', 'N/A') == 'HSA')
                deductible_remaining = float(plan_details.get('deductible', 0.0))
                oop_max = float(plan_details.get('oop_max', float('inf')))
                oop_remaining = oop_max
                premium = float(plan_details.get('premium', 0.0))
                assumed_rate_of_return = float(user_data.get('assumedRateOfReturn', 0.0)) / 100
                hsa_percent_spent = float(user_data.get('hsa', {}).get('percentSpent', 1.0)) / 100
                
                # Fix HSA contribution extraction from user_data
                hsa_contribution = 0.0
                if has_hsa and 'hsa' in user_data:
                    hsa_contribution = float(user_data['hsa'].get('contribution', 0.0))
                
                fsa_contribution = 0.0
                if not has_hsa and 'fsa' in user_data:
                    fsa_contribution = float(user_data['fsa'].get('contribution', 0.0))
                
                hsa_pass_through = float(plan_details.get('hsa_pass_through', 0.0)) if has_hsa else 0.0
                income = float(user_data.get('income', 0.0))


                # Calculate tax savings and HSA growth
                # Tax savings should only apply to USER contributions, not employer pass-through
                # Employer HSA pass-through is already a tax-free benefit
                if has_hsa:
                    tax_savings = calculate_tax_savings(hsa_contribution, tax_rate)
                else:
                    tax_savings = calculate_tax_savings(fsa_contribution, tax_rate)
                hsa_growth = calculate_hsa_growth(hsa_contribution, hsa_pass_through, hsa_percent_spent, assumed_rate_of_return) if has_hsa else 0.0
                total_premiums = premium * 12

                # if has_hsa:
                #     hsa_growth = calculate_hsa_growth(
                #         hsa_contribution,
                #         hsa_pass_through,
                #         hsa_percent_spent,
                #         assumed_rate_of_return
                #     )
                # print(plan_id,": HSA growth: ", hsa_growth,"HSA contribution: ", hsa_contribution, "HSA pass through: ", hsa_pass_through, "HSA percent spent: ", hsa_percent_spent)

                # Initialize monthly breakdown: each month starts with the premium
                monthly_breakdown = {month: premium for month in range(1, 13)}
                
                # Group services by month for processing
                monthly_services = {month: [] for month in range(1, 13)}
                
                # Process each service from user input (input_details)
                for service, details in user_input.items():
                    # user_input now only contains service details, no need to skip other fields
                    if not isinstance(details, dict) or 'dates' not in details:
                        continue

                    # Get average service cost
                    service_cost_value = float(service_costs.get(service, 0.0))
                    
                    # Map service name to parsed column base
                    service_col_base = map_service_to_column_base(service)
                    
                    # Try to use parsed fields first, fallback to legacy 'services' dict
                    member_cost, metadata = compute_cost_for_service(
                        plan_details, 
                        service_col_base, 
                        service_cost_value
                    )
                    
                    # Fallback to legacy services dict if parsing returns None
                    if member_cost is None:
                        raw_services = plan_details.get('services', {})
                        if not isinstance(raw_services, dict):
                            raw_services = {}
                        member_cost_from_plan = raw_services.get(service, 0.0)
                        # Use legacy logic
                        if isinstance(member_cost_from_plan, (int, float)):
                            member_cost = float(member_cost_from_plan)
                        else:
                            member_cost = 0.0
                        metadata = {
                            'cost_type': 'legacy',
                            'applies_after_deductible': False,
                            'raw': str(member_cost_from_plan)
                        }

                    # Group services by month
                    for date in details.get('dates', []):
                        try:
                            month = int(date.split('-')[1])  # Extract month (assuming 'YYYY-MM-DD')
                            monthly_services[month].append({
                                'service': service,
                                'date': date,
                                'avg_cost': service_cost_value,
                                'member_cost': member_cost,
                                'metadata': metadata
                            })
                        except Exception as e:
                            print(f"Error parsing date '{date}' for service {service}: {e}")
                            continue

                # Process each month in order, using parsed fields with priority logic
                cumulative_medical_cost = 0.0
                for month in range(1, 13):
                    monthly_service_cost = 0.0
                    
                    # Process all services for this month
                    for service_info in monthly_services[month]:
                        member_cost = service_info['member_cost']
                        avg_service_cost = service_info['avg_cost']
                        metadata = service_info.get('metadata', {})
                        cost_type = metadata.get('cost_type', 'unknown')
                        
                        # Handle service not covered
                        if member_cost == float('inf'):
                            # Service not covered - skip or handle specially
                            print(f"Service {service_info['service']} not covered in plan {plan_id}")
                            continue
                        
                        # Check special condition flags
                        deductible_applies = metadata.get('applies_after_deductible', False)
                        prior_auth_required = metadata.get('prior_authorization', False)
                        network_only = metadata.get('network_only', False)
                        first_visit_only = metadata.get('first_visit_only', False)
                        
                        # Handle prior authorization flag
                        if prior_auth_required:
                            # Log for UI warning - for now, proceed with normal calculation
                            # In future, this could set a flag in results for UI to display
                            print(f"Note: Service {service_info['service']} requires prior authorization for plan {plan_id}")
                        
                        # Handle network-only services
                        # Assumption: if network_only is True, we assume user is in-network
                        # In future, could add user input for in/out of network
                        
                        # Calculate member pays based on cost type and deductible logic
                        if cost_type == 'copay':
                            # Fixed copay
                            if deductible_applies and deductible_remaining > 0:
                                # Special case: "applies after deductible" means:
                                # 1. Member pays full service cost until deductible is met
                                # 2. Then the copay applies
                                deductible_applied = min(avg_service_cost, deductible_remaining)
                                deductible_remaining -= deductible_applied
                                
                                if deductible_applied >= avg_service_cost:
                                    # Entire service cost goes to deductible
                                    member_pays = deductible_applied
                                else:
                                    # Deductible met during this service, apply copay
                                    member_pays = deductible_applied + member_cost
                            else:
                                # Deductible already met or doesn't apply - just copay
                                member_pays = member_cost
                                
                        elif cost_type == 'coinsurance':
                            # Coinsurance - always applies deductible first if not met
                            if deductible_remaining > 0:
                                # Member pays to satisfy deductible first
                                deductible_applied = min(avg_service_cost, deductible_remaining)
                                deductible_remaining -= deductible_applied
                                
                                # Then apply coinsurance to any remaining allowed charge
                                remaining_charge = avg_service_cost - deductible_applied
                                coinsurance_amount = (member_cost / avg_service_cost) * remaining_charge
                                member_pays = deductible_applied + coinsurance_amount
                            else:
                                # Deductible already met - just coinsurance
                                member_pays = member_cost
                                
                        elif cost_type == 'covered':
                            # Fully covered - member pays nothing
                            member_pays = 0.0
                            
                        elif cost_type == 'legacy':
                            # Legacy calculation (backward compatibility)
                            member_cost_float = float(member_cost)
                            
                            # Determine if this is a percentage (coinsurance) or fixed copay
                            if 0 < member_cost_float <= 1.0:
                                # This is coinsurance (e.g., 0.15 = 15%)
                                member_pays = avg_service_cost * member_cost_float
                                
                                # Apply deductible logic for coinsurance
                                if deductible_remaining > 0:
                                    deductible_applied = min(avg_service_cost, deductible_remaining)
                                    member_pays = deductible_applied + (avg_service_cost - deductible_applied) * member_cost_float
                                    deductible_remaining -= deductible_applied
                            else:
                                # Fixed copay
                                member_pays = member_cost_float
                        else:
                            # Unknown or needs review - use 0 for now
                            member_pays = 0.0
                            print(f"Warning: Cost type '{cost_type}' needs manual review for service {service_info['service']}")
                        
                        # Apply out-of-pocket maximum
                        if oop_remaining > 0:
                            if member_pays > oop_remaining:
                                member_pays = oop_remaining
                                oop_remaining = 0.0
                            else:
                                oop_remaining -= member_pays
                        else:
                            member_pays = 0.0  # OOP max reached
                        
                        monthly_service_cost += member_pays
                        cumulative_medical_cost += member_pays
                    
                    # Update the monthly breakdown
                    monthly_breakdown[month] = round(monthly_breakdown[month] + monthly_service_cost, 2)
                
                # Use the cumulative medical cost instead of the complex deductible calculation
                cumulative_cost = cumulative_medical_cost

                # Ensure we don't exceed OOP max
                if cumulative_cost > oop_max:
                    cumulative_cost = oop_max

                # Calculate base cost (premiums + medical costs)
                base_cost = total_premiums + cumulative_cost
                
                # Apply tax savings and HSA growth as reductions
                # Tax savings reduce your effective cost by the tax you don't pay
                # HSA growth is additional value you get from investment returns
                total_cost = base_cost - tax_savings - hsa_growth
                
                # Ensure total cost doesn't go below zero (though it could theoretically)
                # This accounts for cases where HSA benefits exceed actual costs
                if total_cost < 0:
                    total_cost = 0

                # Calculate unused HSA or FSA funds
                if has_hsa:
                    total_hsa_available = hsa_contribution + hsa_pass_through
                    total_hsa_spent = total_hsa_available * hsa_percent_spent
                    unused_hsa = total_hsa_available - total_hsa_spent
                    unused_fsa = 0.0
                else:
                    total_fsa_available = fsa_contribution
                    total_fsa_spent = total_fsa_available  # Assume entire FSA is spent
                    unused_fsa = total_fsa_available - total_fsa_spent
                    unused_hsa = 0.0

                # Debug logging for specific plans
                if "GEHA HDHP" in plan_details['plan_name'] or "APWU" in plan_details['plan_name']:
                    print(f"DEBUG: {plan_details['plan_name']} - Premium: ${premium}, Medical Costs: ${cumulative_medical_cost}, Total: ${total_cost}", flush=True)
                    print(f"  Monthly breakdown varies: {len(set(monthly_breakdown.values())) > 1}", flush=True)

                results[plan_id] = {
                    'plan_name': plan_details['plan_name'],
                    'monthly_breakdown': {
                        month_name: round(monthly_breakdown[month], 2)
                        for month_name, month in zip(
                            ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                            range(1, 13)
                        )
                    },
                    'total_cost': round(total_cost, 2),
                    'tax_savings': round(tax_savings, 2),
                    'cumulative_cost': round(cumulative_cost, 2),
                    'unused_hsa': round(unused_hsa, 2),
                    'unused_fsa': round(unused_fsa, 2),
                    'hsa_growth': round(hsa_growth, 2)
                }

            except Exception as e:
                print(f"Error processing plan {plan_id}: {e}")
                continue

        return results

    except Exception as e:
        print(f"Error in calculate_costs function: {e}")
        raise





# import json
# from typing import List, Dict, Any
# import os

# try:
#     # For production use with uvicorn or FastAPI
#     from routers.health_plans import get_parsed_health_plans
# except ImportError:
#     # For running script directly with `python -m`
#     from backend.routers.health_plans import get_parsed_health_plans

# # Dynamically resolve the path to the average service costs file
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# SERVICE_COSTS_FILE = os.path.join(BASE_DIR, "../data/service_costs.json")

# def load_service_costs() -> Dict[str, float]:
#     """
#     Load average service costs from the JSON file.
#     """
#     try:
#         with open(SERVICE_COSTS_FILE, 'r') as file:
#             return json.load(file)
#     except FileNotFoundError:
#         raise RuntimeError(f"Service costs file not found: {SERVICE_COSTS_FILE}")
#     except Exception as e:
#         raise RuntimeError(f"Error loading service costs: {e}")

# def calculate_costs(user_input: Dict[str, Any], tax_rate: float, plan_type: str) -> Dict[str, Any]:
#     try:
#         # Load parsed health plans and service costs
#         plans = get_parsed_health_plans()
#         service_costs = load_service_costs()

#         results = {}

#         for plan_id, plan_details in plans.items():
#             if plan_details['enrollment_type'] != plan_type:
#                 continue  # Skip plans that don't match the enrollment type

#             try:
#                 # Initialize variables
#                 cumulative_cost = 0
#                 deductible_remaining = plan_details.get('deductible', 0)
#                 oop_max = plan_details.get('oop_max', float('inf'))
#                 premium = plan_details.get('premium', 0)
#                 monthly_breakdown = {month: premium for month in range(1, 13)}

#                 # Process services for each month
#                 for month in range(1, 13):
#                     monthly_service_cost = 0

#                     # Iterate over all services in the user input
#                     for service, details in user_input.items():
#                         if service in ['planType', 'hsa', 'fsa']:
#                             continue  # Skip non-service entries

#                         service_count = details.get('count', 0)
#                         service_dates = details.get('dates', [])
#                         service_cost = plan_details['services'].get(service, service_costs.get(service, 0))

#                         # Check if the service occurs in the current month
#                         if any(int(date.split('-')[1]) == month for date in service_dates):
#                             total_service_cost = service_cost * service_count

#                             # Apply deductible
#                             if deductible_remaining > 0:
#                                 deductible_applied = min(total_service_cost, deductible_remaining)
#                                 total_service_cost -= deductible_applied
#                                 deductible_remaining -= deductible_applied

#                             # Apply OOP maximum
#                             if cumulative_cost + total_service_cost > oop_max:
#                                 total_service_cost = max(0, oop_max - cumulative_cost)

#                             # Update monthly service cost and cumulative cost
#                             monthly_service_cost += total_service_cost
#                             cumulative_cost += total_service_cost

#                     # Add the calculated monthly service cost to the breakdown
#                     monthly_breakdown[month] += monthly_service_cost

#                 # Calculate total annual cost
#                 total_cost = sum(monthly_breakdown.values())

#                 # Apply tax savings
#                 tax_savings = plan_details.get('hsa_contribution', 0) * tax_rate
#                 total_cost -= tax_savings

#                 # Calculate unused HSA and FSA funds
#                 user_hsa_contribution = user_input.get('hsa', {}).get('contribution', 0)
#                 fsa_contribution = user_input.get('fsa', {}).get('contribution', 0)
#                 unused_hsa = max(0, user_hsa_contribution - cumulative_cost)
#                 unused_fsa = max(0, fsa_contribution - cumulative_cost)

#                 # Add results for this plan
#                 results[plan_id] = {
#                     'plan_name': plan_details['plan_name'],
#                     'monthly_breakdown': {
#                         month_name: monthly_breakdown[month]
#                         for month_name, month in zip(
#                             ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
#                             range(1, 13)
#                         )
#                     },
#                     'total_cost': total_cost,
#                     'tax_savings': tax_savings,
#                     'cumulative_cost': cumulative_cost,
#                     'unused_hsa': unused_hsa,
#                     'unused_fsa': unused_fsa,
#                 }

#             except Exception as e:
#                 print(f"Error processing plan {plan_id}: {e}")
#                 continue
#         # print(results)
#         return results

#     except Exception as e:
#         print(f"Error in calculate_costs function: {e}")
#         raise