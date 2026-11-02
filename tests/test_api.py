"""
Test Suite for JobFlow API Endpoints
Tests all Flask routes with various scenarios.
"""

import sys
from pathlib import Path

# Add parent directory to path to import app - must be at top for E402
sys.path.insert(0, str(Path(__file__).parent.parent))

import json

import pytest

from app import app, extract_year, normalize_status


@pytest.fixture
def client():
    """Create Flask test client."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def sample_jobs():
    """Sample jobs data for testing."""
    return [
        {
            "company": "TestCorp",
            "title": "Engineer",
            "date_applied": "2025-01-15",
            "status": "applied",
            "stage": "applied",
            "source": "LinkedIn",
        },
        {
            "company": "DevCo",
            "title": "Developer",
            "date_applied": "2024-12-20",
            "status": "interviewing",
            "stage": "technical",
            "source": "Indeed",
        },
    ]


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test /api/health returns 200 OK."""
        response = client.get("/api/health")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["status"] == "ok"
        assert "timestamp" in data


class TestYearsEndpoint:
    """Test /api/years endpoint."""

    def test_get_years_returns_array(self, client):
        """Test that /api/years returns a JSON array."""
        response = client.get("/api/years")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_years_sorted_descending(self, client):
        """Test that years are sorted newest first."""
        response = client.get("/api/years")
        data = json.loads(response.data)

        if len(data) > 1:
            assert data == sorted(data, reverse=True)

    # TODO: Add test with mocked data file


class TestSankeyEndpoint:
    """Test /api/sankey endpoint."""

    def test_sankey_without_year_filter(self, client):
        """Test /api/sankey without year parameter."""
        response = client.get("/api/sankey")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "nodes" in data
        assert "links" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["links"], dict)

    def test_sankey_with_year_filter(self, client):
        """Test /api/sankey with year parameter."""
        response = client.get("/api/sankey?year=2025")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "nodes" in data
        assert "links" in data

    def test_sankey_links_structure(self, client):
        """Test that links have required fields."""
        response = client.get("/api/sankey")
        data = json.loads(response.data)

        links = data["links"]
        assert "source" in links
        assert "target" in links
        assert "value" in links
        assert isinstance(links["source"], list)
        assert isinstance(links["target"], list)
        assert isinstance(links["value"], list)

    # TODO: Test with invalid year parameter
    # TODO: Test with year that has no data


class TestStatusCountsEndpoint:
    """Test /api/status_counts endpoint."""

    def test_status_counts_without_filter(self, client):
        """Test /api/status_counts without year parameter."""
        response = client.get("/api/status_counts")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "labels" in data
        assert "counts" in data
        assert isinstance(data["labels"], list)
        assert isinstance(data["counts"], list)

    def test_status_counts_with_year(self, client):
        """Test /api/status_counts with year parameter."""
        response = client.get("/api/status_counts?year=2025")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "labels" in data
        assert "counts" in data

    def test_status_counts_arrays_same_length(self, client):
        """Test that labels and counts arrays have same length."""
        response = client.get("/api/status_counts")
        data = json.loads(response.data)

        assert len(data["labels"]) == len(data["counts"])

    # TODO: Test counts are positive integers
    # TODO: Test sorted by count descending


class TestUtilityFunctions:
    """Test utility functions."""

    def test_extract_year_valid_date(self):
        """Test extracting year from valid date."""
        assert extract_year("2025-01-15") == 2025
        assert extract_year("2024-12-31") == 2024

    def test_extract_year_invalid_date(self):
        """Test extracting year from invalid date."""
        assert extract_year("invalid") is None
        assert extract_year(None) is None
        assert extract_year("2025-13-01") is None

    def test_normalize_status(self):
        """Test status normalization."""
        assert normalize_status("applied") == "Applied"
        assert normalize_status("APPLIED") == "Applied"
        assert normalize_status("interviewing") == "Interviewing"
        assert normalize_status("rejected") == "Rejected"

    def test_normalize_status_unknown(self):
        """Test normalizing unknown status."""
        result = normalize_status("custom_status")
        assert isinstance(result, str)
        # Should still return something (title case of input)


class TestIndexRoute:
    """Test main dashboard route."""

    def test_index_returns_html(self, client):
        """Test that / returns HTML page."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"<!DOCTYPE html>" in response.data or b"<html" in response.data

    def test_index_contains_title(self, client):
        """Test that index contains JobFlow title."""
        response = client.get("/")
        assert b"JobFlow" in response.data


# TODO: Add integration tests
# TODO: Add test for data file not found scenario
# TODO: Add test for malformed JSON in data file
# TODO: Mock data file for consistent testing

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
