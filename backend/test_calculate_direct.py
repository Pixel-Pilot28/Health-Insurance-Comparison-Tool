"""Direct test of calculate endpoint to debug service cost calculations"""

import json
import sys
sys.path.insert(0, '.')
from routers.calculate import calculate_cost, Payload, UserData, InputDetails

# Load the saved user data
with open('data/user_payload.json', 'r') as f:
    saved_data = json.load(f)

# Create the payload
user_data = UserData(**saved_data['userData'])
input_details = {
    key: InputDetails(**value) 
    for key, value in saved_data['inputDetails'].items()
}

payload = Payload(userData=user_data, inputDetails=input_details)

# Call the endpoint
print("Calling calculate_cost endpoint...")
result = calculate_cost(payload)

# Check the results
print(f"\nNumber of plans: {len(result['plans'])}")
sample_plan = list(result['plans'].values())[0]
print(f"\nSample plan: {sample_plan['plan_name']}")
print(f"Monthly costs: {list(sample_plan['monthly_breakdown'].values())}")
print(f"All same? {len(set(sample_plan['monthly_breakdown'].values())) == 1}")
print(f"Cumulative cost: {sample_plan['cumulative_cost']}")
