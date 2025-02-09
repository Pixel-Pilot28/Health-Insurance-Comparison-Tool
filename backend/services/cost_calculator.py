import json
from typing import List, Dict, Any, Tuple
import os

try:
    # For production use with uvicorn or FastAPI
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
    print("HSA contribution:", hsa_contribution, "HSA pass through:", hsa_pass_through, "HSA percent spent:", hsa_percent_spent)
    print("Total growth:", total_growth)
    return round(total_growth, 2)
    

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

def calculate_costs(user_input: Dict[str, Any], tax_rate: float, plan_type: str) -> Dict[str, Any]:
    """
    Calculate monthly and annual costs for each health plan based on user inputs.
    Returns a dictionary of results keyed by plan ID.
    """
    try:
        plans = get_parsed_health_plans()
        service_costs = load_service_costs()
        results = {}

        for plan_id, plan_details in plans.items():
            # Filter by enrollment type
            if plan_details['enrollment_type'] != plan_type:
                continue

            try:
                # Determine if plan is HSA eligible
                # has_hsa = plan_details.get('hsaEligible', False)
                has_hsa = (plan_details.get('hsa_hra_type', 'N/A') == 'HSA')
                deductible_remaining = float(plan_details.get('deductible', 0.0))
                oop_max = float(plan_details.get('oop_max', float('inf')))
                oop_remaining = oop_max
                premium = float(plan_details.get('premium', 0.0))
                assumed_rate_of_return = float(user_input.get('assumedRateOfReturn', 0.0))
                hsa_percent_spent = float(user_input.get('hsaPercentSpent', 1.0))
                hsa_contribution = float(user_input.get('hsacontribution', 0.0)) if has_hsa else 0.0
                fsa_contribution = float(user_input.get('fsa', {}).get('contribution', 0.0)) if not has_hsa else 0.0
                hsa_pass_through = float(plan_details.get('hsa_pass_through', 0.0)) if has_hsa else 0.0
                income = float(user_input.get('income', 0.0))


                # Calculate tax savings and HSA growth
                contribution = hsa_contribution + hsa_pass_through if has_hsa else fsa_contribution
                tax_savings = calculate_tax_savings(contribution, tax_rate)
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
                cumulative_cost = 0.0

                # Process each service from user input
                for service, details in user_input.items():
                    if service in ['planType', 'hsa', 'fsa', 'income', 'assumedRateOfReturn', 'hsaPercentSpent']:
                        continue

                    # Get average service cost
                    service_cost_value = float(service_costs.get(service, 0.0))
                    
                    # Retrieve coverage information from plan_details['services']
                    raw_coverage = plan_details.get('services', {})
                    if not isinstance(raw_coverage, dict):
                        raw_coverage = {}
                    coverage = raw_coverage.get(service, {})
                    if not isinstance(coverage, dict):
                        coverage = {}

                    # Process each date for this service
                    for date in details.get('dates', []):
                        try:
                            month = int(date.split('-')[1])  # Extract month (assuming 'YYYY-MM-DD')
                        except Exception as e:
                            print(f"Error parsing date '{date}' for service {service}: {e}")
                            continue

                        user_pays, deductible_remaining, oop_remaining, cost_breakdown_detail = calculate_service_cost(
                            service_cost_value, 1, coverage, deductible_remaining, oop_remaining
                        )
                        cumulative_cost += user_pays
                        monthly_breakdown[month] += user_pays

                if cumulative_cost > oop_max:
                    cumulative_cost = oop_max

                total_cost = total_premiums + cumulative_cost - tax_savings - hsa_growth

                # Calculate unused HSA or FSA funds
                if has_hsa:
                    total_hsa_available = hsa_contribution + hsa_pass_through
                    print("total HSA available:", total_hsa_available)
                    total_hsa_spent = total_hsa_available * hsa_percent_spent
                    unused_hsa = total_hsa_available - total_hsa_spent
                    unused_fsa = 0.0
                else:
                    total_fsa_available = fsa_contribution
                    total_fsa_spent = total_fsa_available  # Assume entire FSA is spent
                    unused_fsa = total_fsa_available - total_fsa_spent
                    unused_hsa = 0.0

                results[plan_id] = {
                    'plan_name': plan_details['plan_name'],
                    'monthly_breakdown': {
                        month_name: monthly_breakdown[month]
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