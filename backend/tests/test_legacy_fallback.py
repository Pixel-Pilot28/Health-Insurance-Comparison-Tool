import pytest
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

if 'fastapi' not in sys.modules:
    class _RouterStub:
        def get(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

        def post(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

    fastapi_stub = types.SimpleNamespace(
        APIRouter=_RouterStub,
        HTTPException=Exception
    )
    sys.modules['fastapi'] = fastapi_stub

from backend.services import cost_calculator as cc


def test_interpret_legacy_copay_value():
    cost, metadata = cc.interpret_legacy_service_value(25.0, 150.0)
    assert cost == 25.0
    assert metadata["cost_type"] == "legacy_copay"
    assert metadata["interpreted_copay"] == 25.0


def test_interpret_legacy_coinsurance_value():
    cost, metadata = cc.interpret_legacy_service_value(0.2, 200.0)
    assert cost == pytest.approx(40.0)
    assert metadata["cost_type"] == "legacy_coinsurance"
    assert metadata["interpreted_percent"] == pytest.approx(0.2)


def test_interpret_legacy_string_percent():
    cost, metadata = cc.interpret_legacy_service_value("20%", 100.0)
    assert cost == pytest.approx(20.0)
    assert metadata["cost_type"] == "legacy_coinsurance"


def test_interpret_legacy_string_dollar():
    cost, metadata = cc.interpret_legacy_service_value("$45", 200.0)
    assert cost == pytest.approx(45.0)
    assert metadata["cost_type"] == "legacy_copay"


def test_calculate_costs_legacy_copay(monkeypatch):
    plans = {
        "TEST PLAN": {
            "plan_name": "Test Plan",
            "enrollment_type": "Self",
            "premium": 100.0,
            "deductible": 0.0,
            "oop_max": 1000.0,
            "hsa_hra_type": "N/A",
            "services": {
                "Specialist": 30.0
            }
        }
    }

    service_costs = {"Specialist": 200.0}

    monkeypatch.setattr(cc, "get_parsed_health_plans", lambda: plans)
    monkeypatch.setattr(cc, "load_service_costs", lambda: service_costs)

    user_input = {
        "Specialist": {
            "count": 2,
            "dates": ["2026-01-15", "2026-02-15"]
        }
    }

    user_data = {
        "income": 0,
        "assumedRateOfReturn": 0,
        "hsa": {"contribution": 0, "percentSpent": 0},
        "fsa": {"contribution": 0},
        "medicare": {"partBPremium": 0, "coveredPeople": 0},
    }

    results = cc.calculate_costs(user_input, user_data, tax_rate=0.0, plan_type="Self")
    plan_result = results["TEST PLAN"]
    jan = plan_result["monthly_breakdown"]["Jan"]
    feb = plan_result["monthly_breakdown"]["Feb"]
    mar = plan_result["monthly_breakdown"]["Mar"]

    assert jan == pytest.approx(130.0)
    assert feb == pytest.approx(130.0)
    assert mar == pytest.approx(100.0)
    assert plan_result["cumulative_cost"] == pytest.approx(60.0)


def test_calculate_costs_legacy_coinsurance_with_deductible(monkeypatch):
    plans = {
        "COINSURANCE PLAN": {
            "plan_name": "Coinsurance Plan",
            "enrollment_type": "Self",
            "premium": 50.0,
            "deductible": 200.0,
            "oop_max": 1000.0,
            "hsa_hra_type": "HSA",
            "services": {
                "Specialist": 0.2
            }
        }
    }

    service_costs = {"Specialist": 300.0}

    monkeypatch.setattr(cc, "get_parsed_health_plans", lambda: plans)
    monkeypatch.setattr(cc, "load_service_costs", lambda: service_costs)

    user_input = {
        "Specialist": {
            "count": 2,
            "dates": ["2026-01-10", "2026-02-10"]
        }
    }

    user_data = {
        "income": 0,
        "assumedRateOfReturn": 0,
        "hsa": {"contribution": 0, "percentSpent": 0},
        "fsa": {"contribution": 0},
        "medicare": {"partBPremium": 0, "coveredPeople": 0},
    }

    results = cc.calculate_costs(user_input, user_data, tax_rate=0.0, plan_type="Self")
    plan_result = results["COINSURANCE PLAN"]
    jan = plan_result["monthly_breakdown"]["Jan"]
    feb = plan_result["monthly_breakdown"]["Feb"]
    mar = plan_result["monthly_breakdown"]["Mar"]

    # First visit: $200 to deductible + 20% of remaining $100 = $220, plus $50 premium
    assert jan == pytest.approx(270.0)
    # Second visit: deductible met, 20% coinsurance on $300 = $60, plus $50 premium
    assert feb == pytest.approx(110.0)
    # No visits afterwards, premium only
    assert mar == pytest.approx(50.0)
    # Medical costs should reflect $220 + $60 = $280
    assert plan_result["cumulative_cost"] == pytest.approx(280.0)