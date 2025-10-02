from typing import Dict, List, Any, Optional, Tuple
import math
import json
from enum import Enum

class RiskTolerance(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"

class CostSensitivity(str, Enum):
    VERY_HIGH = "very_high"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"

class CoveragePriority(str, Enum):
    COMPREHENSIVE = "comprehensive"
    PREVENTIVE = "preventive"
    EMERGENCY = "emergency"
    BALANCED = "balanced"

class UserPreferences:
    def __init__(self, 
                 risk_tolerance: RiskTolerance,
                 cost_sensitivity: CostSensitivity,
                 coverage_priority: CoveragePriority,
                 max_monthly_premium: Optional[float] = None,
                 max_deductible: Optional[float] = None,
                 hsa_preference: bool = False,
                 family_size: int = 1,
                 age_group: str = "adult",
                 health_status: str = "good",
                 preferred_network_size: str = "large",
                 travel_frequency: str = "low"):
        self.risk_tolerance = risk_tolerance
        self.cost_sensitivity = cost_sensitivity
        self.coverage_priority = coverage_priority
        self.max_monthly_premium = max_monthly_premium
        self.max_deductible = max_deductible
        self.hsa_preference = hsa_preference
        self.family_size = family_size
        self.age_group = age_group
        self.health_status = health_status
        self.preferred_network_size = preferred_network_size
        self.travel_frequency = travel_frequency

class PlanRecommendation:
    def __init__(self, plan_id: str, plan_name: str, score: float, 
                 cost_score: float, coverage_score: float, risk_score: float,
                 reasons: List[str], warnings: List[str] = None):
        self.plan_id = plan_id
        self.plan_name = plan_name
        self.score = score
        self.cost_score = cost_score
        self.coverage_score = coverage_score
        self.risk_score = risk_score
        self.reasons = reasons
        self.warnings = warnings or []

class RecommendationEngine:
    """
    Advanced recommendation engine that analyzes health plans based on user preferences,
    risk tolerance, cost sensitivity, and coverage needs.
    """
    
    def __init__(self):
        # Weight factors for different scoring components
        self.weights = {
            'cost': 0.4,      # 40% weight on cost considerations
            'coverage': 0.35,  # 35% weight on coverage matching
            'risk': 0.25      # 25% weight on risk alignment
        }
    
    def calculate_cost_score(self, plan_data: Dict[str, Any], 
                           user_preferences: UserPreferences) -> Tuple[float, List[str]]:
        """
        Calculate how well a plan aligns with user's cost preferences.
        Higher score = better cost alignment.
        """
        reasons = []
        score = 0.0
        
        annual_cost = float(plan_data.get('annual_cost', 0))
        monthly_premium = float(plan_data.get('premium', 0))
        deductible = float(plan_data.get('deductible', 0))
        tax_savings = float(plan_data.get('tax_savings', 0))
        
        # Cost sensitivity scoring
        if user_preferences.cost_sensitivity == CostSensitivity.VERY_HIGH:
            # Heavily prioritize lowest total cost
            score += 30 if annual_cost < 2000 else (20 if annual_cost < 3000 else 10)
            if annual_cost < 2000:
                reasons.append("Very low annual cost aligns with high cost sensitivity")
        
        elif user_preferences.cost_sensitivity == CostSensitivity.HIGH:
            # Balance total cost with value
            score += 25 if annual_cost < 2500 else (15 if annual_cost < 3500 else 8)
            if tax_savings > 500:
                score += 10
                reasons.append("Significant tax savings provide good value")
        
        elif user_preferences.cost_sensitivity == CostSensitivity.MODERATE:
            # Focus on reasonable costs with good benefits
            score += 20 if 2000 <= annual_cost <= 4000 else 10
            if 1500 <= deductible <= 3000:
                score += 8
                reasons.append("Moderate deductible balances premium and out-of-pocket costs")
        
        else:  # LOW cost sensitivity
            # Less focus on cost, more on comprehensive coverage
            score += 15 if annual_cost < 5000 else 10
            if tax_savings > 800:
                score += 12
                reasons.append("Excellent tax savings despite higher premium")
        
        # Premium constraints
        if user_preferences.max_monthly_premium and monthly_premium > user_preferences.max_monthly_premium:
            score -= 15
            reasons.append(f"Monthly premium exceeds your ${user_preferences.max_monthly_premium} limit")
        
        # Deductible constraints
        if user_preferences.max_deductible and deductible > user_preferences.max_deductible:
            score -= 10
            reasons.append(f"Deductible exceeds your ${user_preferences.max_deductible} limit")
        
        # HSA preference bonus
        if user_preferences.hsa_preference and plan_data.get('hsa_hra_type') == 'HSA':
            score += 15
            reasons.append("HSA-eligible plan matches your tax savings preference")
        
        return min(max(score, 0), 50), reasons  # Normalize to 0-50 range
    
    def calculate_coverage_score(self, plan_data: Dict[str, Any], 
                               user_preferences: UserPreferences) -> Tuple[float, List[str]]:
        """
        Calculate how well a plan's coverage aligns with user priorities.
        """
        reasons = []
        score = 0.0
        
        services = plan_data.get('services', {})
        oop_max = float(plan_data.get('oop_max', float('inf')))
        
        # Coverage priority scoring
        if user_preferences.coverage_priority == CoveragePriority.COMPREHENSIVE:
            # Prioritize low out-of-pocket costs and comprehensive coverage
            score += 20 if oop_max < 5000 else (15 if oop_max < 8000 else 8)
            
            # Check for good coverage across service types
            preventive_coverage = self._evaluate_service_coverage(services, ['Primary Care', 'Simple Labs'])
            specialty_coverage = self._evaluate_service_coverage(services, ['Specialist', 'Complex Labs'])
            
            score += preventive_coverage * 5
            score += specialty_coverage * 8
            
            if preventive_coverage > 0.8 and specialty_coverage > 0.8:
                reasons.append("Excellent comprehensive coverage across all service types")
            
        elif user_preferences.coverage_priority == CoveragePriority.PREVENTIVE:
            # Focus on preventive care coverage
            preventive_coverage = self._evaluate_service_coverage(
                services, ['Primary Care', 'Simple Labs', 'Outpatient Tests']
            )
            score += preventive_coverage * 25
            
            if preventive_coverage > 0.9:
                reasons.append("Outstanding preventive care coverage")
            
        elif user_preferences.coverage_priority == CoveragePriority.EMERGENCY:
            # Focus on emergency and major medical coverage
            emergency_coverage = self._evaluate_service_coverage(
                services, ['Emergency Care', 'Inpatient Admission', 'Complex Labs']
            )
            score += emergency_coverage * 20
            
            # Lower out-of-pocket max is crucial for emergency situations
            score += 15 if oop_max < 6000 else (10 if oop_max < 10000 else 5)
            
            if emergency_coverage > 0.8:
                reasons.append("Strong emergency and major medical coverage")
        
        else:  # BALANCED
            # Even weighting across all service types
            all_services = ['Primary Care', 'Specialist', 'Emergency Care', 'Simple Labs', 'Complex Labs']
            overall_coverage = self._evaluate_service_coverage(services, all_services)
            score += overall_coverage * 20
            
            if overall_coverage > 0.7:
                reasons.append("Well-balanced coverage across all healthcare needs")
        
        # Age-based adjustments
        if user_preferences.age_group in ["senior", "mature"]:
            # Older adults may need more coverage
            score += 5 if oop_max < 6000 else -5
            
        # Health status adjustments
        if user_preferences.health_status == "poor":
            score += 10 if oop_max < 5000 else -10
            reasons.append("Lower out-of-pocket maximum important for ongoing health needs")
        
        return min(max(score, 0), 35), reasons  # Normalize to 0-35 range
    
    def calculate_risk_score(self, plan_data: Dict[str, Any], 
                           user_preferences: UserPreferences) -> Tuple[float, List[str]]:
        """
        Calculate how well a plan aligns with user's risk tolerance.
        """
        reasons = []
        score = 0.0
        
        deductible = float(plan_data.get('deductible', 0))
        oop_max = float(plan_data.get('oop_max', float('inf')))
        monthly_premium = float(plan_data.get('premium', 0))
        
        if user_preferences.risk_tolerance == RiskTolerance.CONSERVATIVE:
            # Prefer predictable costs, lower deductibles
            score += 15 if deductible < 2000 else (10 if deductible < 3000 else 3)
            score += 10 if monthly_premium > 150 else 5  # Willing to pay more for predictability
            
            if deductible < 1500:
                reasons.append("Low deductible provides cost predictability")
            
        elif user_preferences.risk_tolerance == RiskTolerance.MODERATE:
            # Balance between cost and risk
            score += 12 if 1500 <= deductible <= 4000 else 6
            score += 8 if 100 <= monthly_premium <= 250 else 4
            
            if 2000 <= deductible <= 3500:
                reasons.append("Moderate deductible balances premium costs with risk exposure")
            
        else:  # AGGRESSIVE
            # Willing to take on more risk for lower premiums
            score += 15 if deductible > 3000 else (10 if deductible > 2000 else 5)
            score += 10 if monthly_premium < 150 else 5
            
            if deductible > 3500 and monthly_premium < 120:
                reasons.append("High deductible plan offers low premiums for risk-tolerant users")
        
        # Family size considerations
        if user_preferences.family_size > 2:
            # Larger families may want more predictable costs
            score += 5 if deductible < 3000 else -3
            score += 3 if oop_max < 10000 else -5
        
        return min(max(score, 0), 25), reasons  # Normalize to 0-25 range
    
    def _evaluate_service_coverage(self, services: Dict[str, Any], 
                                 service_types: List[str]) -> float:
        """
        Evaluate coverage quality for specific service types.
        Returns a score from 0.0 to 1.0 based on copay amounts.
        """
        if not services or not service_types:
            return 0.0
        
        total_score = 0.0
        evaluated_services = 0
        
        for service_type in service_types:
            if service_type in services:
                copay = float(services[service_type])
                # Lower copays = better coverage
                if copay == 0:
                    service_score = 1.0
                elif copay <= 25:
                    service_score = 0.8
                elif copay <= 50:
                    service_score = 0.6
                elif copay <= 100:
                    service_score = 0.4
                else:
                    service_score = 0.2
                
                total_score += service_score
                evaluated_services += 1
        
        return total_score / max(evaluated_services, 1)
    
    def generate_recommendations(self, health_plans: Dict[str, Any], 
                               user_preferences: UserPreferences,
                               user_cost_data: Dict[str, Any]) -> List[PlanRecommendation]:
        """
        Generate ranked recommendations based on user preferences.
        """
        recommendations = []
        
        for plan_id, plan_data in health_plans.items():
            # Skip plans that don't match enrollment type
            enrollment_type = user_cost_data.get('planType', 'Self')
            if plan_data.get('enrollment_type') != enrollment_type:
                continue
            
            # Calculate component scores
            cost_score, cost_reasons = self.calculate_cost_score(plan_data, user_preferences)
            coverage_score, coverage_reasons = self.calculate_coverage_score(plan_data, user_preferences)
            risk_score, risk_reasons = self.calculate_risk_score(plan_data, user_preferences)
            
            # Calculate weighted total score
            total_score = (
                cost_score * self.weights['cost'] +
                coverage_score * self.weights['coverage'] +
                risk_score * self.weights['risk']
            )
            
            # Combine all reasons
            all_reasons = cost_reasons + coverage_reasons + risk_reasons
            
            # Generate warnings for potential issues
            warnings = self._generate_warnings(plan_data, user_preferences)
            
            recommendation = PlanRecommendation(
                plan_id=plan_id,
                plan_name=plan_data.get('plan_name', plan_id),
                score=round(total_score, 2),
                cost_score=round(cost_score, 2),
                coverage_score=round(coverage_score, 2),
                risk_score=round(risk_score, 2),
                reasons=all_reasons[:5],  # Limit to top 5 reasons
                warnings=warnings
            )
            
            recommendations.append(recommendation)
        
        # Sort by total score (highest first)
        recommendations.sort(key=lambda x: x.score, reverse=True)
        
        return recommendations
    
    def _generate_warnings(self, plan_data: Dict[str, Any], 
                         user_preferences: UserPreferences) -> List[str]:
        """
        Generate warnings about potential plan limitations or mismatches.
        """
        warnings = []
        
        annual_cost = float(plan_data.get('annual_cost', 0))
        deductible = float(plan_data.get('deductible', 0))
        oop_max = float(plan_data.get('oop_max', 0))
        
        # High cost warnings
        if annual_cost > 4000 and user_preferences.cost_sensitivity in [CostSensitivity.HIGH, CostSensitivity.VERY_HIGH]:
            warnings.append("High annual cost may strain budget")
        
        # High deductible warnings for conservative users
        if deductible > 3000 and user_preferences.risk_tolerance == RiskTolerance.CONSERVATIVE:
            warnings.append("High deductible increases financial risk")
        
        # Family coverage warnings
        if user_preferences.family_size > 2 and oop_max > 12000:
            warnings.append("High out-of-pocket maximum for family coverage")
        
        # Health status warnings
        if user_preferences.health_status == "poor" and deductible > 2000:
            warnings.append("High deductible may be costly with frequent medical needs")
        
        return warnings
