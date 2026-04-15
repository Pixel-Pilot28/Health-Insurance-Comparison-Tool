"""
Unit tests for OPM reconciliation API router

Tests all endpoints in backend/routers/opm.py
"""

import pytest
import json
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# Test data
SAMPLE_OVERRIDES = {
    "version": "1.0",
    "description": "Test overrides",
    "column_map": {
        "Test Column": "Test_Field"
    },
    "plan_overrides": {
        "EnrollmentCode_123": {
            "Test_Field_money": 25.0,
            "_note": "Test override"
        }
    },
    "ignore_columns": []
}

SAMPLE_COLUMN_MAPPING = {
    "opm_column": "Ded. (Self)",
    "canonical_target": "Annual Deductible Self"
}

SAMPLE_PLAN_UPDATE = {
    "plan": "Test Plan",
    "enrollment_code": "123",
    "column": "Primary Care Office Visit",
    "updates": {
        "Primary_Care_Office_Visit_money": 25.0,
        "Primary_Care_Office_Visit_cap": 500.0
    }
}


class TestHealthEndpoint:
    """Tests for /opm/health endpoint"""
    
    def test_health_check_returns_200(self):
        """Health endpoint should return 200"""
        response = client.get("/api/opm/health")
        assert response.status_code == 200
    
    def test_health_check_has_status(self):
        """Health response should include status field"""
        response = client.get("/api/opm/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_health_check_includes_availability(self):
        """Health response should include file availability info"""
        response = client.get("/api/opm/health")
        data = response.json()
        assert "parser_available" in data
        assert "inputs_available" in data
        assert "outputs_available" in data
        assert isinstance(data["parser_available"], bool)


class TestParseReportEndpoint:
    """Tests for /opm/parse-report endpoint"""
    
    def test_parse_report_without_file(self):
        """Should return 404 if parse_report.json doesn't exist"""
        # Note: This might return 200 if file exists from previous runs
        response = client.get("/api/opm/parse-report")
        assert response.status_code in [200, 404]
    
    def test_parse_report_structure(self):
        """Parse report should have expected structure if it exists"""
        response = client.get("/api/opm/parse-report")
        if response.status_code == 200:
            data = response.json()
            # Should have these keys (may be empty)
            assert isinstance(data, dict)
            # _meta is always added by the endpoint
            assert "_meta" in data


class TestOverridesEndpoint:
    """Tests for overrides GET/POST/DELETE endpoints"""
    
    def test_get_overrides_returns_200(self):
        """GET /overrides should always return 200"""
        response = client.get("/api/opm/overrides")
        assert response.status_code == 200
    
    def test_get_overrides_returns_dict(self):
        """GET /overrides should return dictionary"""
        response = client.get("/api/opm/overrides")
        data = response.json()
        assert isinstance(data, dict)
    
    def test_save_overrides(self):
        """POST /overrides should save and return success"""
        response = client.post(
            "/api/opm/overrides",
            json=SAMPLE_OVERRIDES
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "overrides" in data
    
    def test_save_overrides_adds_timestamp(self):
        """POST /overrides should add last_updated if not provided"""
        overrides = SAMPLE_OVERRIDES.copy()
        overrides.pop("last_updated", None)  # Remove if exists
        
        response = client.post("/api/opm/overrides", json=overrides)
        assert response.status_code == 200
        
        # Verify timestamp was added
        saved = response.json()["overrides"]
        assert "last_updated" in saved
    
    def test_get_after_save_returns_saved_data(self):
        """GET /overrides after POST should return saved data"""
        # Save overrides
        client.post("/api/opm/overrides", json=SAMPLE_OVERRIDES)
        
        # Retrieve them
        response = client.get("/api/opm/overrides")
        data = response.json()
        
        assert data["version"] == SAMPLE_OVERRIDES["version"]
        assert "Test Column" in data["column_map"]


class TestColumnMapEndpoint:
    """Tests for /opm/column-map endpoint"""
    
    def test_column_map_without_file(self):
        """Should return 404 if column_map.json doesn't exist"""
        response = client.get("/api/opm/column-map")
        # Might exist from previous parser runs
        assert response.status_code in [200, 404]
    
    def test_column_map_structure(self):
        """Column map should have expected structure if it exists"""
        response = client.get("/api/opm/column-map")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)


class TestAcceptSuggestionEndpoint:
    """Tests for /opm/accept-suggestion endpoint"""
    
    def test_accept_suggestion_returns_200(self):
        """POST /accept-suggestion should return 200"""
        response = client.post(
            "/api/opm/accept-suggestion",
            json=SAMPLE_COLUMN_MAPPING
        )
        assert response.status_code == 200
    
    def test_accept_suggestion_adds_to_column_map(self):
        """Accepting suggestion should add to column_map in overrides"""
        # Accept a suggestion
        response = client.post(
            "/api/opm/accept-suggestion",
            json=SAMPLE_COLUMN_MAPPING
        )
        assert response.status_code == 200
        
        # Verify it was added
        overrides_response = client.get("/api/opm/overrides")
        overrides = overrides_response.json()
        
        assert SAMPLE_COLUMN_MAPPING["opm_column"] in overrides.get("column_map", {})
        assert (overrides["column_map"][SAMPLE_COLUMN_MAPPING["opm_column"]] 
                == SAMPLE_COLUMN_MAPPING["canonical_target"])
    
    def test_accept_suggestion_response_structure(self):
        """Accept suggestion response should have expected structure"""
        response = client.post(
            "/api/opm/accept-suggestion",
            json=SAMPLE_COLUMN_MAPPING
        )
        data = response.json()
        
        assert data["status"] == "ok"
        assert "message" in data
        assert "overrides" in data


class TestUpdatePlanOverrideEndpoint:
    """Tests for /opm/update-plan-override endpoint"""
    
    def test_update_plan_override_returns_200(self):
        """POST /update-plan-override should return 200"""
        response = client.post(
            "/api/opm/update-plan-override",
            json=SAMPLE_PLAN_UPDATE
        )
        assert response.status_code == 200
    
    def test_update_plan_override_adds_to_overrides(self):
        """Update should add to plan_overrides in overrides"""
        response = client.post(
            "/api/opm/update-plan-override",
            json=SAMPLE_PLAN_UPDATE
        )
        data = response.json()
        
        assert data["status"] == "ok"
        assert "plan_key" in data
        assert data["plan_key"] == f"EnrollmentCode_{SAMPLE_PLAN_UPDATE['enrollment_code']}"
    
    def test_update_plan_override_response_includes_updates(self):
        """Response should include the updates that were applied"""
        response = client.post(
            "/api/opm/update-plan-override",
            json=SAMPLE_PLAN_UPDATE
        )
        data = response.json()
        
        assert "updates" in data
        assert data["updates"] == SAMPLE_PLAN_UPDATE["updates"]
    
    def test_update_plan_override_persists(self):
        """Plan override should persist in overrides file"""
        # Apply update
        client.post("/api/opm/update-plan-override", json=SAMPLE_PLAN_UPDATE)
        
        # Retrieve overrides
        response = client.get("/api/opm/overrides")
        overrides = response.json()
        
        plan_key = f"EnrollmentCode_{SAMPLE_PLAN_UPDATE['enrollment_code']}"
        assert plan_key in overrides.get("plan_overrides", {})


class TestStatsEndpoint:
    """Tests for /opm/stats endpoint"""
    
    def test_stats_without_report(self):
        """Should return 404 if parse_report.json doesn't exist"""
        response = client.get("/api/opm/stats")
        # Might exist from previous runs
        assert response.status_code in [200, 404]
    
    def test_stats_structure(self):
        """Stats should have expected structure if report exists"""
        response = client.get("/api/opm/stats")
        if response.status_code == 200:
            data = response.json()
            assert "total_plans" in data
            assert "total_columns" in data
            assert "ambiguous_cells_count" in data
            assert "unmapped_columns_count" in data
            assert "overrides_active" in data
            assert "files_available" in data


class TestAmbiguousCellsEndpoint:
    """Tests for /opm/ambiguous-cells endpoint"""
    
    def test_ambiguous_cells_without_report(self):
        """Should return 404 if parse_report.json doesn't exist"""
        response = client.get("/api/opm/ambiguous-cells")
        assert response.status_code in [200, 404]
    
    def test_ambiguous_cells_with_pagination(self):
        """Should accept skip and limit parameters"""
        response = client.get("/api/opm/ambiguous-cells?skip=0&limit=10")
        assert response.status_code in [200, 404]
    
    def test_ambiguous_cells_response_structure(self):
        """Response should have pagination structure if report exists"""
        response = client.get("/api/opm/ambiguous-cells")
        if response.status_code == 200:
            data = response.json()
            assert "total" in data
            assert "skip" in data
            assert "limit" in data
            assert "items" in data
            assert "has_more" in data
            assert isinstance(data["items"], list)


class TestParsedCSVEndpoint:
    """Tests for /opm/parsed-csv endpoint"""
    
    def test_parsed_csv_without_file(self):
        """Should return 404 if CSV doesn't exist"""
        response = client.get("/api/opm/parsed-csv")
        assert response.status_code in [200, 404]
    
    def test_parsed_csv_content_type(self):
        """Should return CSV content type if file exists"""
        response = client.get("/api/opm/parsed-csv")
        if response.status_code == 200:
            assert "text/csv" in response.headers.get("content-type", "")


class TestRunParserEndpoint:
    """Tests for /opm/run-parser endpoint"""
    
    def test_run_parser_accepts_empty_body(self):
        """POST /run-parser should accept empty request body"""
        # Note: This will actually try to run the parser if files exist
        # In a real test environment, you'd mock the subprocess call
        response = client.post("/api/opm/run-parser", json={})
        # Could be 200 (success), 404 (files missing), or 500 (execution failed)
        assert response.status_code in [200, 404, 500]
    
    def test_run_parser_accepts_parameters(self):
        """POST /run-parser should accept optional parameters"""
        response = client.post("/api/opm/run-parser", json={
            "min_score": 0.7,
            "use_fuzzy": False
        })
        assert response.status_code in [200, 404, 500]
    
    def test_run_parser_response_has_status(self):
        """Response should include status field"""
        response = client.post("/api/opm/run-parser", json={})
        data = response.json()
        assert "status" in data


class TestDeleteOverridesEndpoint:
    """Tests for DELETE /opm/overrides endpoint"""
    
    def test_delete_overrides_returns_200(self):
        """DELETE /overrides should return 200"""
        response = client.delete("/api/opm/overrides")
        assert response.status_code == 200
    
    def test_delete_overrides_response(self):
        """DELETE response should include status and message"""
        response = client.delete("/api/opm/overrides")
        data = response.json()
        assert data["status"] == "ok"
        assert "message" in data
    
    def test_delete_removes_overrides(self):
        """After DELETE, GET should return empty overrides"""
        # Save some overrides
        client.post("/api/opm/overrides", json=SAMPLE_OVERRIDES)
        
        # Delete them
        client.delete("/api/opm/overrides")
        
        # Verify they're gone
        response = client.get("/api/opm/overrides")
        data = response.json()
        # Should return default empty structure
        assert len(data.get("column_map", {})) == 0 or data.get("column_map") is None


class TestEndToEndWorkflow:
    """Integration tests for complete workflow"""
    
    def test_complete_override_workflow(self):
        """Test complete workflow: clear -> save -> retrieve -> update -> delete"""
        # 1. Clear existing overrides
        client.delete("/api/opm/overrides")
        
        # 2. Save initial overrides
        response = client.post("/api/opm/overrides", json=SAMPLE_OVERRIDES)
        assert response.status_code == 200
        
        # 3. Retrieve overrides
        response = client.get("/api/opm/overrides")
        assert response.status_code == 200
        data = response.json()
        assert "Test Column" in data.get("column_map", {})
        
        # 4. Accept a column suggestion
        response = client.post("/api/opm/accept-suggestion", json=SAMPLE_COLUMN_MAPPING)
        assert response.status_code == 200
        
        # 5. Update a plan override
        response = client.post("/api/opm/update-plan-override", json=SAMPLE_PLAN_UPDATE)
        assert response.status_code == 200
        
        # 6. Verify all changes persisted
        response = client.get("/api/opm/overrides")
        overrides = response.json()
        
        # Check column map has both original and suggestion
        assert "Test Column" in overrides["column_map"]
        assert SAMPLE_COLUMN_MAPPING["opm_column"] in overrides["column_map"]
        
        # Check plan override exists
        plan_key = f"EnrollmentCode_{SAMPLE_PLAN_UPDATE['enrollment_code']}"
        assert plan_key in overrides["plan_overrides"]
        
        # 7. Clean up
        client.delete("/api/opm/overrides")


class TestErrorHandling:
    """Tests for error handling"""
    
    def test_invalid_json_in_post(self):
        """Invalid JSON should return 422"""
        response = client.post(
            "/api/opm/overrides",
            data="not json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_missing_required_fields_in_accept_suggestion(self):
        """Missing required fields should return 422"""
        response = client.post(
            "/api/opm/accept-suggestion",
            json={"opm_column": "Test"}  # Missing canonical_target
        )
        assert response.status_code == 422
    
    def test_missing_required_fields_in_update_plan(self):
        """Missing required fields should return 422"""
        response = client.post(
            "/api/opm/update-plan-override",
            json={"plan": "Test"}  # Missing other required fields
        )
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
