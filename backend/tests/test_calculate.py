from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_calculate():
    """Test the calculate endpoint."""
    data = {
        "userData": {
            "planType": "Self",
            "income": "50000",
            "taxRate": "25",
            "assumedRateOfReturn": "5",
            "hsa": {
                "contribution": "3000",
                "limit": "3500",
                "percentSpent": "50"
            },
            "fsa": {
                "contribution": "2000",
                "limit": "2500"
            },
            "medicare": {
                "part_b_premium": "170",
                "covered_people": "1"
            }
        },
        "inputDetails": {
            "Primary Care": {
                "service": [],
                "count": 4,
                "dates": ["2024-01-01", "2024-04-01", "2024-07-01", "2024-10-01"]
            },
            "Specialist": {
                "service": [],
                "count": 2,
                "dates": ["2024-02-01", "2024-08-01"]
            }
        }
    }

    response = client.post("/api/calculate", json=data)
    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "Cost calculation successful"
    assert "plans" in payload and isinstance(payload["plans"], dict)
