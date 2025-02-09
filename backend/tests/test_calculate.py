from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_calculate():
    """Test the calculate endpoint."""
    data = {
        "user_data": {
            "plan_type": "Self",
            "income": 50000,
            "tax_rate": 25.0,
            "assumed_rate_of_return": 5.0,
            "hsa": {
                "contribution": 3000,
                "limit": 3500,
                "percent_spent": 50.0
            },
            "fsa": {
                "contribution": 2000,
                "limit": 2500
            },
            "medicare": {
                "part_b_premium": 170.0,
                "covered_people": 1
            }
        },
        "medical_needs": {
            "Primary Care": {
                "count": 4,
                "dates": ["2024-01-01", "2024-04-01", "2024-07-01", "2024-10-01"]
            },
            "Specialist": {
                "count": 2,
                "dates": ["2024-02-01", "2024-08-01"]
            }
        }
    }

    response = client.post("/api/calculate", json=data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
