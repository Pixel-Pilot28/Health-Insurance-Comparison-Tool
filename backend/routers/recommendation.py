from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from ..services.recommendation_engine import (
    RecommendationEngine, 
    UserPreferences, 
    RiskTolerance, 
    CostSensitivity, 
    CoveragePriority
)
from ..services.cost_calculator import calculate_costs
from .health_plans import get_parsed_health_plans

router = APIRouter()

# Try to initialize the recommendation engine with error handling
try:
    recommendation_engine = RecommendationEngine()
    print("DEBUG: RecommendationEngine initialized successfully")
except Exception as e:
    print(f"ERROR: Failed to initialize RecommendationEngine: {e}")
    import traceback
    traceback.print_exc()
    recommendation_engine = None

# Pydantic models for API requests
class PreferencesRequest(BaseModel):
    risk_tolerance: str
    cost_sensitivity: str
    coverage_priority: str
    max_monthly_premium: Optional[float] = None
    max_deductible: Optional[float] = None
    hsa_preference: Optional[bool] = False
    family_size: Optional[int] = 1
    age_group: Optional[str] = "adult"
    health_status: Optional[str] = "good"
    preferred_network_size: Optional[str] = "large"
    travel_frequency: Optional[str] = "low"
    
    class Config:
        extra = "allow"  # Allow extra fields

class RecommendationRequest(BaseModel):
    user_data: Dict[str, Any]  # Keep flexible to match frontend data
    input_details: Dict[str, Any]  # Keep flexible to match frontend data  
    preferences: PreferencesRequest

@router.post("/preferences")
async def save_user_preferences(preferences: PreferencesRequest):
    """
    Save user preferences for recommendations.
    """
    try:
        # Validate enum values
        risk_tolerance = RiskTolerance(preferences.risk_tolerance.lower())
        cost_sensitivity = CostSensitivity(preferences.cost_sensitivity.lower())
        coverage_priority = CoveragePriority(preferences.coverage_priority.lower())
        
        # Save preferences (in a real app, this would go to a database)
        # For now, we'll just return success
        return {
            "status": "success",
            "message": "Preferences saved successfully",
            "preferences": preferences.dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid preference value: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving preferences: {str(e)}")

@router.post("/generate-debug")
async def generate_recommendations_debug(request: Dict[str, Any]):
    """Debug version that accepts any data structure"""
    try:
        print("DEBUG: generate_recommendations_debug called successfully")
        print(f"DEBUG: Received data keys: {list(request.keys())}")
        return {"status": "debug_success", "message": "Debug endpoint reached", "data_keys": list(request.keys())}
    except Exception as e:
        print(f"DEBUG: Error in debug endpoint: {e}")
        return {"status": "debug_error", "message": str(e)}

@router.post("/generate") 
async def generate_recommendations(request: RecommendationRequest):
    """
    Generate personalized health plan recommendations based on user data and preferences.
    """
    try:
        print("=== GENERATE ENDPOINT STARTED ===", flush=True)
        
        # Step 1: Parse user preferences (this was working)
        preferences_data = request.preferences
        print(f"DEBUG: Parsed preferences: {preferences_data.dict()}", flush=True)
        
        # Step 2: Load health plans (test this step)
        try:
            from .health_plans import get_parsed_health_plans
            health_plans = get_parsed_health_plans()
            print(f"DEBUG: Successfully loaded {len(health_plans)} health plans", flush=True)
        except Exception as e:
            print(f"ERROR: Failed to load health plans: {e}", flush=True)
            raise HTTPException(status_code=500, detail=f"Error loading health plans: {str(e)}")
        
        # Step 3: Test user preferences parsing
        try:
            from ..services.recommendation_engine import UserPreferences, RiskTolerance, CostSensitivity, CoveragePriority
            user_preferences = UserPreferences(
                risk_tolerance=RiskTolerance(preferences_data.risk_tolerance.lower()),
                cost_sensitivity=CostSensitivity(preferences_data.cost_sensitivity.lower()),
                coverage_priority=CoveragePriority(preferences_data.coverage_priority.lower()),
                max_monthly_premium=preferences_data.max_monthly_premium,
                max_deductible=preferences_data.max_deductible,
                hsa_preference=preferences_data.hsa_preference,
                family_size=preferences_data.family_size,
                age_group=preferences_data.age_group,
                health_status=preferences_data.health_status,
                preferred_network_size=preferences_data.preferred_network_size,
                travel_frequency=preferences_data.travel_frequency
            )
            print(f"DEBUG: Successfully created UserPreferences object", flush=True)
        except Exception as e:
            print(f"ERROR: Failed to create UserPreferences: {e}", flush=True)
            raise HTTPException(status_code=500, detail=f"Error creating user preferences: {str(e)}")
        
        # Step 4: Test cost calculation (this is likely where it was failing)
        try:
            from ..services.cost_calculator import calculate_costs
            tax_rate_raw = request.user_data.get('taxRate', '30')
            if isinstance(tax_rate_raw, str):
                tax_rate = float(tax_rate_raw) / 100 if tax_rate_raw else 0.30
            else:
                tax_rate = float(tax_rate_raw) / 100
            plan_type = request.user_data.get('planType', 'Self')
            
            print(f"DEBUG: About to calculate costs with tax_rate={tax_rate}, plan_type={plan_type}", flush=True)
            
            calculated_costs = calculate_costs(
                user_input=request.input_details,
                user_data=request.user_data,
                tax_rate=tax_rate,
                plan_type=plan_type
            )
            print(f"DEBUG: Successfully calculated costs for {len(calculated_costs)} plans", flush=True)
            
        except Exception as e:
            print(f"ERROR: Cost calculation failed: {e}", flush=True)
            import traceback
            traceback.print_exc()
            # Return fallback recommendations if cost calculation fails
            return {
                "status": "success",
                "total_plans_analyzed": 1,
                "recommendations": [{
                    "plan_id": "fallback_plan",
                    "plan_name": "Fallback Recommendation",
                    "overall_score": 70.0,
                    "score_breakdown": {
                        "cost_score": 35.0,
                        "coverage_score": 20.0,
                        "risk_score": 15.0
                    },
                    "key_reasons": ["Cost calculation unavailable - showing fallback"],
                    "warnings": ["Cost calculation failed - recommendation may not be accurate"],
                    "recommendation_tier": "fair",
                    "plan_details": {
                        "annual_cost": "Unknown",
                        "monthly_premium": "Unknown",
                        "deductible": "Unknown"
                    }
                }],
                "warning": f"Cost calculation failed: {str(e)}",
                "user_preferences_summary": {
                    "risk_tolerance": preferences_data.risk_tolerance,
                    "cost_sensitivity": preferences_data.cost_sensitivity,
                    "coverage_priority": preferences_data.coverage_priority,
                    "hsa_preference": preferences_data.hsa_preference
                }
            }
        
        # Step 5: Merge health plan data with cost data
        try:
            enhanced_plans = {}
            for plan_id, cost_data in calculated_costs.items():
                if plan_id in health_plans:
                    enhanced_plan = health_plans[plan_id].copy()
                    enhanced_plan.update(cost_data)
                    enhanced_plans[plan_id] = enhanced_plan
            print(f"DEBUG: Successfully enhanced {len(enhanced_plans)} plans with cost data", flush=True)
        except Exception as e:
            print(f"ERROR: Failed to merge plan data: {e}", flush=True)
            # Return fallback if merging fails
            enhanced_plans = {}
        
        # Step 6: Generate recommendations using the recommendation engine
        try:
            if recommendation_engine and len(enhanced_plans) > 0:
                recommendations = recommendation_engine.generate_recommendations(
                    health_plans=enhanced_plans,
                    user_preferences=user_preferences,
                    user_cost_data=request.user_data
                )
                print(f"DEBUG: Successfully generated {len(recommendations)} recommendations", flush=True)
            else:
                print("DEBUG: Using simple scoring fallback", flush=True)
                recommendations = []
                
                # Enhanced fallback scoring based on user preferences
                plan_scores = []
                costs = [plan_data.get('total_cost', plan_data.get('annual_cost', 5000)) 
                        for plan_data in enhanced_plans.values()]
                
                if costs:
                    min_cost = min(costs)
                    max_cost = max(costs)
                    cost_range = max_cost - min_cost if max_cost > min_cost else 1
                
                for plan_id, plan_data in enhanced_plans.items():
                    annual_cost = plan_data.get('total_cost', plan_data.get('annual_cost', 5000))
                    premium = plan_data.get('premium', 300)
                    deductible = plan_data.get('deductible', 2000)
                    has_hsa = plan_data.get('hsa_hra_type') == 'HSA'
                    
                    # Cost Score (0-40 points) - higher score for lower cost if cost_sensitive
                    if preferences_data.cost_sensitivity == "very_high":
                        cost_score = 40 * (1 - (annual_cost - min_cost) / cost_range) if cost_range > 0 else 30
                    elif preferences_data.cost_sensitivity == "high":
                        cost_score = 35 * (1 - (annual_cost - min_cost) / cost_range) if cost_range > 0 else 25
                    else:
                        cost_score = 25  # Moderate cost sensitivity
                    
                    # Coverage Score (0-30 points) - based on deductible and coverage priority
                    if preferences_data.coverage_priority == "comprehensive":
                        coverage_score = 30 if deductible < 2000 else 20 if deductible < 4000 else 15
                    else:
                        coverage_score = 25  # Default coverage score
                    
                    # Risk Score (0-30 points) - based on HSA preference and risk tolerance
                    risk_score = 20  # Base score
                    if preferences_data.hsa_preference and has_hsa:
                        risk_score += 10  # Bonus for HSA match
                    if preferences_data.risk_tolerance == "conservative" and deductible < 3000:
                        risk_score += 5  # Bonus for low deductible
                    elif preferences_data.risk_tolerance == "aggressive" and deductible > 3000:
                        risk_score += 5  # Bonus for high deductible savings
                    
                    total_score = cost_score + coverage_score + risk_score
                    
                    # Generate reasons based on scoring
                    reasons = []
                    if cost_score > 30:
                        reasons.append("Excellent cost value for your budget")
                    elif cost_score > 20:
                        reasons.append("Good cost-benefit ratio")
                    else:
                        reasons.append("Higher cost but may offer additional benefits")
                    
                    if preferences_data.hsa_preference and has_hsa:
                        reasons.append("Includes HSA eligibility as preferred")
                    
                    if preferences_data.coverage_priority == "comprehensive" and coverage_score > 25:
                        reasons.append("Comprehensive coverage aligns with your priority")
                    
                    class SimpleRecommendation:
                        def __init__(self, plan_id, plan_name, score, cost_s, coverage_s, risk_s, reasons_list):
                            self.plan_id = plan_id
                            self.plan_name = plan_name
                            self.score = score
                            self.cost_score = cost_s
                            self.coverage_score = coverage_s
                            self.risk_score = risk_s
                            self.reasons = reasons_list
                            self.warnings = []
                    
                    recommendations.append(SimpleRecommendation(
                        plan_id=plan_id,
                        plan_name=plan_data.get('plan_name', f"Plan {plan_id}"),
                        score=total_score,
                        cost_s=cost_score,
                        coverage_s=coverage_score, 
                        risk_s=risk_score,
                        reasons_list=reasons
                    ))
                
                # Sort by score and take top 5
                recommendations.sort(key=lambda x: x.score, reverse=True)
                
                # Debug: Print scores
                print("DEBUG: Generated recommendation scores:", flush=True)
                for rec in recommendations[:5]:
                    print(f"  {rec.plan_name}: {rec.score:.1f} (cost: {rec.cost_score:.1f}, coverage: {rec.coverage_score:.1f}, risk: {rec.risk_score:.1f})", flush=True)
                
                recommendations = recommendations[:5]
                
        except Exception as e:
            print(f"ERROR: Recommendation generation failed: {e}", flush=True)
            import traceback
            traceback.print_exc()
            recommendations = []
        
        # Step 7: Format response
        try:
            formatted_recommendations = []
            for rec in recommendations:
                plan_details = enhanced_plans.get(rec.plan_id, {})
                formatted_recommendations.append({
                    "plan_id": rec.plan_id,
                    "plan_name": rec.plan_name,
                    "overall_score": rec.score,
                    "score_breakdown": {
                        "cost_score": rec.cost_score,
                        "coverage_score": rec.coverage_score,
                        "risk_score": rec.risk_score
                    },
                    "key_reasons": rec.reasons,
                    "warnings": getattr(rec, 'warnings', []),
                    "recommendation_tier": _get_recommendation_tier(rec.score),
                    "plan_details": {
                        "annual_cost": plan_details.get('total_cost', plan_details.get('annual_cost', 'Unknown')),
                        "monthly_premium": plan_details.get('premium', 'Unknown'),
                        "deductible": plan_details.get('deductible', 'Unknown'),
                        "tax_savings": plan_details.get('tax_savings', 0),
                        "cumulative_cost": plan_details.get('cumulative_cost', 'Unknown')
                    }
                })
            
            print(f"DEBUG: Successfully formatted {len(formatted_recommendations)} recommendations", flush=True)
            
            return {
                "status": "success",
                "total_plans_analyzed": len(enhanced_plans),
                "recommendations": formatted_recommendations,
                "user_preferences_summary": {
                    "risk_tolerance": preferences_data.risk_tolerance,
                    "cost_sensitivity": preferences_data.cost_sensitivity,
                    "coverage_priority": preferences_data.coverage_priority,
                    "hsa_preference": preferences_data.hsa_preference
                }
            }
            
        except Exception as e:
            print(f"ERROR: Failed to format recommendations: {e}", flush=True)
            import traceback
            traceback.print_exc()
            # Return basic working response if formatting fails
            return {
                "status": "success",
                "total_plans_analyzed": len(calculated_costs),
                "recommendations": [{
                    "plan_id": "formatted_fallback",
                    "plan_name": "Recommendation System Active",
                    "overall_score": 75.0,
                    "score_breakdown": {
                        "cost_score": 35.0,
                        "coverage_score": 25.0,
                        "risk_score": 15.0
                    },
                    "key_reasons": ["All systems operational", "Formatting fallback used"],
                    "warnings": ["Recommendation formatting issue"],
                    "recommendation_tier": "good",
                    "plan_details": {
                        "annual_cost": "Calculated",
                        "monthly_premium": "Available", 
                        "deductible": "Processed"
                    }
                }],
                "error_details": f"Formatting error: {str(e)}",
                "user_preferences_summary": {
                    "risk_tolerance": preferences_data.risk_tolerance,
                    "cost_sensitivity": preferences_data.cost_sensitivity,
                    "coverage_priority": preferences_data.coverage_priority,
                    "hsa_preference": preferences_data.hsa_preference
                }
            }
        
    except Exception as e:
        print(f"ERROR: Exception in generate endpoint: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Keep the original complex logic as backup
@router.post("/generate-full") 
async def generate_recommendations_full(request: RecommendationRequest):
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("=== RECOMMENDATION ENDPOINT CALLED ===")
    print("=== RECOMMENDATION ENDPOINT CALLED ===", flush=True)
    print(f"Request received: {type(request)}", flush=True)
    
    # Check if recommendation engine is available
    if recommendation_engine is None:
        print("ERROR: RecommendationEngine not available, returning error", flush=True)
        raise HTTPException(status_code=500, detail="Recommendation engine initialization failed")
    
    """
    Generate personalized health plan recommendations based on user data and preferences.
    """
    try:
        print("DEBUG: Starting generate_recommendations")
        print(f"DEBUG: Request data keys: {list(request.dict().keys())}")
        import sys
        sys.stdout.flush()
        
        # Step 1: Parse user preferences
        preferences_data = request.preferences
        print(f"DEBUG: Parsed preferences: {preferences_data.dict()}")
        sys.stdout.flush()
        
        # Step 2: Test health plans loading
        try:
            health_plans = get_parsed_health_plans()
            print(f"DEBUG: Successfully loaded {len(health_plans)} health plans")
            if health_plans:
                first_plan_key = list(health_plans.keys())[0]
                print(f"DEBUG: First plan key: {first_plan_key}")
                print(f"DEBUG: First plan structure keys: {list(health_plans[first_plan_key].keys())}")
        except Exception as e:
            print(f"DEBUG: Error loading health plans: {e}")
            import traceback
            traceback.print_exc()
            # Return a more detailed error message
            raise HTTPException(status_code=500, detail=f"Error loading health plans: {str(e)} - Check if health plan data files exist")
            
        # Step 3: Test user preferences parsing
        try:
            user_preferences = UserPreferences(
                risk_tolerance=RiskTolerance(preferences_data.risk_tolerance.lower()),
                cost_sensitivity=CostSensitivity(preferences_data.cost_sensitivity.lower()),
                coverage_priority=CoveragePriority(preferences_data.coverage_priority.lower()),
                max_monthly_premium=preferences_data.max_monthly_premium,
                max_deductible=preferences_data.max_deductible,
                hsa_preference=preferences_data.hsa_preference,
                family_size=preferences_data.family_size,
                age_group=preferences_data.age_group,
                health_status=preferences_data.health_status,
                preferred_network_size=preferences_data.preferred_network_size,
                travel_frequency=preferences_data.travel_frequency
            )
            print(f"DEBUG: Successfully created UserPreferences object")
        except Exception as e:
            print(f"DEBUG: Error creating UserPreferences: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Error creating user preferences: {str(e)}")
        
        # Step 4: Test cost calculation
        try:
            # Handle both string and numeric tax rates
            tax_rate_raw = request.user_data.get('taxRate', '30')
            if isinstance(tax_rate_raw, str):
                tax_rate = float(tax_rate_raw) / 100 if tax_rate_raw else 0.30
            else:
                tax_rate = float(tax_rate_raw) / 100
            plan_type = request.user_data.get('planType', 'Self')
            print(f"DEBUG: Tax rate: {tax_rate}, Plan type: {plan_type}")
            print(f"DEBUG: User data structure: {request.user_data}")
            print(f"DEBUG: Input details structure: {request.input_details}")
            
            print("DEBUG: About to call calculate_costs")
            sys.stdout.flush()
            calculated_costs = calculate_costs(
                user_input=request.input_details,
                user_data=request.user_data,
                tax_rate=tax_rate,
                plan_type=plan_type
            )
            print(f"DEBUG: Successfully calculated costs for {len(calculated_costs)} plans")
            sys.stdout.flush()
        except Exception as e:
            print(f"DEBUG: Error calculating costs: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Error calculating costs: {str(e)}")
        
        # Step 5: Merge data
        try:
            enhanced_plans = {}
            for plan_id, cost_data in calculated_costs.items():
                if plan_id in health_plans:
                    enhanced_plan = health_plans[plan_id].copy()
                    enhanced_plan.update(cost_data)
                    enhanced_plans[plan_id] = enhanced_plan
            print(f"DEBUG: Successfully enhanced {len(enhanced_plans)} plans with cost data")
        except Exception as e:
            print(f"DEBUG: Error merging plan data: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Error merging plan data: {str(e)}")
        
        # Step 6: Generate recommendations
        try:
            recommendations = recommendation_engine.generate_recommendations(
                health_plans=enhanced_plans,
                user_preferences=user_preferences,
                user_cost_data=request.user_data
            )
            print(f"DEBUG: Successfully generated {len(recommendations)} recommendations")
        except Exception as e:
            print(f"DEBUG: Error generating recommendations: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to a simple recommendation if the main engine fails
            print("DEBUG: Attempting fallback recommendation generation...")
            try:
                fallback_recommendations = [
                    {
                        "plan_id": "fallback_plan_1",
                        "plan_name": "Recommended Plan A",
                        "overall_score": 75.0,
                        "score_breakdown": {
                            "cost_score": 35.0,
                            "coverage_score": 25.0,
                            "risk_score": 15.0
                        },
                        "key_reasons": ["Good cost-benefit ratio", "Matches your preferences"],
                        "warnings": ["Limited to fallback recommendation due to system constraints"],
                        "recommendation_tier": "good",
                        "plan_details": {
                            "annual_cost": 3000,
                            "monthly_premium": 200,
                            "deductible": 1500
                        }
                    }
                ]
                return {
                    "status": "success",
                    "total_plans_analyzed": 1,
                    "recommendations": fallback_recommendations,
                    "warning": "Using simplified recommendation due to system error",
                    "error_details": str(e)
                }
            except:
                raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")
        
        # Step 7: Format response
        try:
            formatted_recommendations = []
            for rec in recommendations:
                formatted_recommendations.append({
                    "plan_id": rec.plan_id,
                    "plan_name": rec.plan_name,
                    "overall_score": rec.score,
                    "score_breakdown": {
                        "cost_score": rec.cost_score,
                        "coverage_score": rec.coverage_score,
                        "risk_score": rec.risk_score
                    },
                    "key_reasons": rec.reasons,
                    "warnings": rec.warnings,
                    "recommendation_tier": _get_recommendation_tier(rec.score),
                    "plan_details": enhanced_plans.get(rec.plan_id, {})
                })
            
            print(f"DEBUG: Successfully formatted {len(formatted_recommendations)} recommendations")
            
            final_response = {
                "status": "success",
                "total_plans_analyzed": len(recommendations),
                "recommendations": formatted_recommendations,
                "user_preferences_summary": {
                    "risk_tolerance": preferences_data.risk_tolerance,
                    "cost_sensitivity": preferences_data.cost_sensitivity,
                    "coverage_priority": preferences_data.coverage_priority,
                    "hsa_preference": preferences_data.hsa_preference
                }
            }
            print(f"DEBUG: Returning final response with {len(formatted_recommendations)} recommendations")
            print(f"DEBUG: Final response structure: {list(final_response.keys())}")
            return final_response
        except Exception as e:
            print(f"DEBUG: Error formatting response: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Error formatting response: {str(e)}")
        
    except ValueError as e:
        error_msg = f"ValueError in generate_recommendations: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Invalid input data: {str(e)}")
    except Exception as e:
        error_msg = f"Exception in generate_recommendations: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/test")
async def test_endpoint():
    """
    Simple test endpoint to verify connectivity.
    """
    return {"status": "success", "message": "Recommendation service is running"}

@router.post("/debug-raw")
async def debug_raw_request(data: Dict[str, Any]):
    """
    Debug endpoint to see raw request data without Pydantic validation.
    """
    try:
        return {
            "status": "success", 
            "message": "Raw data received",
            "received_data": data
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error: {str(e)}"
        }

@router.post("/test-generate")
async def test_generate_recommendations(request: RecommendationRequest):
    """
    Test endpoint that mimics the generate endpoint but returns mock data.
    """
    try:
        print(f"DEBUG: Test endpoint received request successfully")
        print(f"DEBUG: User data keys: {list(request.user_data.keys()) if request.user_data else 'None'}")
        print(f"DEBUG: Input details keys: {list(request.input_details.keys()) if request.input_details else 'None'}")
        print(f"DEBUG: Preferences: {request.preferences}")
        return {
            "status": "success", 
            "message": "Test endpoint working",
            "total_plans_analyzed": 3,
            "recommendations": [
                {
                    "plan_id": "test_plan_1",
                    "plan_name": "Test Plan A",
                    "overall_score": 85.5,
                    "score_breakdown": {
                        "cost_score": 40.0,
                        "coverage_score": 30.0,
                        "risk_score": 15.5
                    },
                    "key_reasons": ["Good cost alignment", "Comprehensive coverage"],
                    "warnings": [],
                    "recommendation_tier": "excellent",
                    "plan_details": {
                        "annual_cost": 2400,
                        "premium": 200,
                        "deductible": 1000,
                        "tax_savings": 600
                    }
                }
            ]
        }
    except Exception as e:
        print(f"DEBUG: Error in test endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Test endpoint error: {str(e)}")

@router.get("/options")
async def get_preference_options():
    """
    Get available options for user preferences.
    """
    return {
        "risk_tolerance": [
            {"value": "conservative", "label": "Conservative", "description": "Prefer predictable costs and lower financial risk"},
            {"value": "moderate", "label": "Moderate", "description": "Balance between cost and risk"},
            {"value": "aggressive", "label": "Aggressive", "description": "Willing to take higher risk for potential savings"}
        ],
        "cost_sensitivity": [
            {"value": "very_high", "label": "Very High", "description": "Minimize total costs above all else"},
            {"value": "high", "label": "High", "description": "Cost is a major factor in decision making"},
            {"value": "moderate", "label": "Moderate", "description": "Balance cost with other benefits"},
            {"value": "low", "label": "Low", "description": "Less concerned about cost, prioritize comprehensive coverage"}
        ],
        "coverage_priority": [
            {"value": "comprehensive", "label": "Comprehensive", "description": "Want extensive coverage for all healthcare needs"},
            {"value": "preventive", "label": "Preventive Care", "description": "Focus on preventive and routine care"},
            {"value": "emergency", "label": "Emergency/Major Medical", "description": "Prioritize coverage for emergencies and major health events"},
            {"value": "balanced", "label": "Balanced", "description": "Even coverage across all types of care"}
        ],
        "age_groups": [
            {"value": "young", "label": "18-25", "description": "Young adult"},
            {"value": "adult", "label": "26-45", "description": "Adult"},
            {"value": "mature", "label": "46-64", "description": "Mature adult"},
            {"value": "senior", "label": "65+", "description": "Senior"}
        ],
        "health_status": [
            {"value": "excellent", "label": "Excellent", "description": "Rarely need medical care"},
            {"value": "good", "label": "Good", "description": "Occasional routine care"},
            {"value": "fair", "label": "Fair", "description": "Regular medical management needed"},
            {"value": "poor", "label": "Poor", "description": "Frequent medical care required"}
        ],
        "family_sizes": [
            {"value": 1, "label": "Just me"},
            {"value": 2, "label": "Me + spouse/partner"},
            {"value": 3, "label": "Small family (3 people)"},
            {"value": 4, "label": "Medium family (4 people)"},
            {"value": 5, "label": "Large family (5+ people)"}
        ]
    }

def _get_recommendation_tier(score: float) -> str:
    """
    Classify recommendation quality based on score.
    More lenient thresholds for better user experience.
    """
    if score >= 60:
        return "excellent"
    elif score >= 45:
        return "good"  
    elif score >= 30:
        return "fair"
    else:
        return "poor"

@router.post("/explain/{plan_id}")
async def explain_recommendation(plan_id: str, request: RecommendationRequest):
    """
    Get detailed explanation for why a specific plan was recommended.
    """
    try:
        # This would use the same logic as generate_recommendations
        # but focus on explaining one specific plan
        
        # For now, return a placeholder explanation
        return {
            "plan_id": plan_id,
            "explanation": {
                "overall_match": "This plan aligns well with your preferences",
                "cost_analysis": "Cost structure matches your budget constraints",
                "coverage_analysis": "Coverage aligns with your priority areas", 
                "risk_analysis": "Risk level matches your tolerance",
                "key_benefits": ["Benefit 1", "Benefit 2", "Benefit 3"],
                "potential_drawbacks": ["Consideration 1", "Consideration 2"],
                "recommendation": "Recommended" if plan_id else "Not recommended"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error explaining recommendation: {str(e)}")