"""Check what fields are available in the parsed plans"""

from routers.health_plans import get_parsed_health_plans

plans = get_parsed_health_plans()
sample_plan = list(plans.values())[0]

print(f"Sample plan: {sample_plan['plan_name']}")
print(f"\nPlan keys: {list(sample_plan.keys())}")

# Check if there are specialist-related fields
specialist_fields = [k for k in sample_plan.keys() if 'Specialist' in k or 'specialist' in k.lower()]
print(f"\nSpecialist-related fields ({len(specialist_fields)}):")
for field in specialist_fields[:10]:
    print(f"  {field}: {sample_plan.get(field)}")

# Check for office visit fields  
office_fields = [k for k in sample_plan.keys() if 'Office_Visit' in k or 'office' in k.lower()]
print(f"\nOffice visit fields ({len(office_fields)}):")
for field in office_fields[:10]:
    print(f"  {field}: {sample_plan.get(field)}")

# Check what's in the services dict
print(f"\nServices dict:")
services = sample_plan.get('services', {})
print(f"  Type: {type(services)}")
print(f"  Keys: {list(services.keys()) if isinstance(services, dict) else 'Not a dict'}")
if isinstance(services, dict) and len(services) > 0:
    print(f"\nSample service entries:")
    for key, value in list(services.items())[:5]:
        print(f"  {key}: {value}")
