"""
Contract/snapshot tests for backward compatibility.
Tests that API outputs match expected snapshots to prevent breaking changes.
"""
import sys
from pathlib import Path

# Import Flask app for testing - must be at top for E402
sys.path.append(str(Path(__file__).parent.parent.parent))
import json
import os
from unittest.mock import patch

import pytest

from app import app


class TestContractMetricsCache:
    """Test metrics cache API contract against golden snapshots."""

    def setup_method(self):
        """Set up test client and snapshot paths."""
        app.config["TESTING"] = True
        self.client = app.test_client()

        self.snapshot_dir = Path(__file__).parent / "__snapshots__"
        self.snapshot_dir.mkdir(exist_ok=True)

        # Load test fixtures
        fixtures_dir = Path(__file__).parent.parent / "fixtures"

        with open(fixtures_dir / "jobs_seed_v2.json") as f:
            self.test_jobs_data = json.load(f)

        with open(fixtures_dir / "followups_seed_v1.json") as f:
            self.test_followups_data = json.load(f)

        with open(fixtures_dir / "journal_seed_v1.json") as f:
            self.test_journal_data = json.load(f)

        with open(fixtures_dir / "metrics_cache_expected.json") as f:
            self.expected_metrics = json.load(f)

    def _load_snapshot(self, name: str):
        """Load a snapshot file."""
        snapshot_file = self.snapshot_dir / f"{name}.json"
        if snapshot_file.exists():
            with open(snapshot_file) as f:
                return json.load(f)
        return None

    def _save_snapshot(self, name: str, data: dict):
        """Save data as a snapshot file."""
        snapshot_file = self.snapshot_dir / f"{name}.json"
        with open(snapshot_file, "w") as f:
            json.dump(data, f, indent=2, sort_keys=True)

    def _should_update_snapshots(self) -> bool:
        """Check if snapshots should be updated based on environment variable."""
        return os.environ.get("UPDATE_SNAPSHOTS", "0") == "1"

    @patch("app.data_manager.compute_metrics")
    def test_metrics_cache_contract(self, mock_compute_metrics):
        """
        GIVEN: Test fixture data
        WHEN: Calling /api/metrics/cache
        THEN: Response matches expected snapshot exactly
        """
        # Mock the metrics computation to return expected data
        mock_compute_metrics.return_value = self.expected_metrics

        response = self.client.get("/api/metrics/cache")

        assert response.status_code == 200
        actual_data = json.loads(response.data)

        snapshot_name = "metrics_cache_response"
        expected_snapshot = self._load_snapshot(snapshot_name)

        if self._should_update_snapshots() or expected_snapshot is None:
            # Update or create snapshot
            self._save_snapshot(snapshot_name, actual_data)
            expected_snapshot = actual_data

        # Compare actual response with snapshot
        assert actual_data == expected_snapshot, (
            "Metrics cache response doesn't match snapshot. " "If this is intentional, run with UPDATE_SNAPSHOTS=1"
        )

    @patch("app.load_jobs")
    @patch("app.load_followups")
    def test_followup_list_contract(self, mock_followups, mock_jobs):
        """
        GIVEN: Test fixture data
        WHEN: Calling /api/followup/list
        THEN: Response structure matches expected snapshot
        """
        mock_jobs.return_value = self.test_jobs_data["jobs"]
        mock_followups.return_value = self.test_followups_data

        response = self.client.get("/api/followup/list")

        assert response.status_code == 200
        actual_data = json.loads(response.data)

        snapshot_name = "followup_list_response"
        expected_snapshot = self._load_snapshot(snapshot_name)

        if self._should_update_snapshots() or expected_snapshot is None:
            self._save_snapshot(snapshot_name, actual_data)
            expected_snapshot = actual_data

        # Compare structure and key fields
        assert actual_data.keys() == expected_snapshot.keys()

        if "active_followups" in actual_data:
            # Verify structure of active followups
            for actual_item, expected_item in zip(
                actual_data["active_followups"][:1],  # Just check first item
                expected_snapshot["active_followups"][:1],
            ):
                assert actual_item.keys() == expected_item.keys()

    @patch("app.load_jobs")
    def test_calendar_month_contract(self, mock_jobs):
        """
        GIVEN: Test fixture data
        WHEN: Calling calendar API for a specific month
        THEN: Response format matches expected snapshot
        """
        mock_jobs.return_value = self.test_jobs_data["jobs"]

        # Test October 2025 (has data in fixtures)
        response = self.client.get("/api/timeline?month=2025-10")

        assert response.status_code == 200
        actual_data = json.loads(response.data)

        snapshot_name = "calendar_month_oct_2025"
        expected_snapshot = self._load_snapshot(snapshot_name)

        if self._should_update_snapshots() or expected_snapshot is None:
            self._save_snapshot(snapshot_name, actual_data)
            expected_snapshot = actual_data

        # Verify response structure
        assert actual_data.keys() == expected_snapshot.keys()

        # Verify data types and structure
        if "events" in actual_data:
            assert isinstance(actual_data["events"], list)
            if actual_data["events"]:
                # Check first event structure
                event = actual_data["events"][0]
                expected_event = expected_snapshot["events"][0]
                assert event.keys() == expected_event.keys()

    @patch("app.load_jobs")
    def test_sankey_data_contract(self, mock_jobs):
        """
        GIVEN: Test fixture data
        WHEN: Calling /api/sankey
        THEN: Sankey diagram data structure matches snapshot
        """
        mock_jobs.return_value = self.test_jobs_data["jobs"]

        response = self.client.get("/api/sankey")

        assert response.status_code == 200
        actual_data = json.loads(response.data)

        snapshot_name = "sankey_data_response"
        expected_snapshot = self._load_snapshot(snapshot_name)

        if self._should_update_snapshots() or expected_snapshot is None:
            self._save_snapshot(snapshot_name, actual_data)
            expected_snapshot = actual_data

        # Verify Sankey structure
        assert "nodes" in actual_data
        assert "links" in actual_data
        assert isinstance(actual_data["nodes"], list)
        assert isinstance(actual_data["links"], list)

        # Compare with snapshot
        assert actual_data == expected_snapshot

    @patch("app.load_jobs")
    def test_status_counts_contract(self, mock_jobs):
        """
        GIVEN: Test fixture data
        WHEN: Calling /api/status_counts
        THEN: Status count structure matches snapshot
        """
        mock_jobs.return_value = self.test_jobs_data["jobs"]

        response = self.client.get("/api/status_counts")

        assert response.status_code == 200
        actual_data = json.loads(response.data)

        snapshot_name = "status_counts_response"
        expected_snapshot = self._load_snapshot(snapshot_name)

        if self._should_update_snapshots() or expected_snapshot is None:
            self._save_snapshot(snapshot_name, actual_data)
            expected_snapshot = actual_data

        # Verify counts structure
        assert isinstance(actual_data, dict)
        for status, count in actual_data.items():
            assert isinstance(status, str)
            assert isinstance(count, int)
            assert count >= 0

        # Compare with snapshot
        assert actual_data == expected_snapshot

    @patch("app.load_jobs")
    @patch("app.load_followups")
    @patch("app.data_manager.load_journal")
    def test_stats2_scatter_contract(self, mock_journal, mock_followups, mock_jobs):
        """
        GIVEN: Test fixture data
        WHEN: Calling /api/stats2/scatter
        THEN: New Nerdy Stats 2 scatter response matches snapshot
        """
        mock_jobs.return_value = self.test_jobs_data["jobs"]
        mock_followups.return_value = self.test_followups_data
        mock_journal.return_value = self.test_journal_data

        response = self.client.get("/api/stats2/scatter?year=2025")

        assert response.status_code == 200
        actual_data = json.loads(response.data)

        snapshot_name = "stats2_scatter_response"
        expected_snapshot = self._load_snapshot(snapshot_name)

        if self._should_update_snapshots() or expected_snapshot is None:
            self._save_snapshot(snapshot_name, actual_data)
            expected_snapshot = actual_data

        # Verify structure
        assert actual_data["success"] is True
        assert "data" in actual_data
        assert "metadata" in actual_data
        assert "filters" in actual_data

        # Verify scatter plot data keys
        expected_plots = [
            "applications_over_time",
            "mood_vs_productivity",
            "followup_timing_vs_outcome",
            "duration_to_close_vs_source",
        ]

        for plot_name in expected_plots:
            assert plot_name in actual_data["data"]

        # Compare with snapshot (excluding timestamp fields)
        actual_copy = json.loads(json.dumps(actual_data))
        if "metadata" in actual_copy and "generated_at" in actual_copy["metadata"]:
            actual_copy["metadata"]["generated_at"] = "TIMESTAMP_PLACEHOLDER"

        expected_copy = json.loads(json.dumps(expected_snapshot))
        if "metadata" in expected_copy and "generated_at" in expected_copy["metadata"]:
            expected_copy["metadata"]["generated_at"] = "TIMESTAMP_PLACEHOLDER"

        assert actual_copy == expected_copy

    @patch("app.load_jobs")
    @patch("app.load_followups")
    @patch("app.data_manager.load_journal")
    def test_stats2_heatmap_contract(self, mock_journal, mock_followups, mock_jobs):
        """
        GIVEN: Test fixture data
        WHEN: Calling /api/stats2/heatmap
        THEN: Nerdy Stats 2 heatmap response matches snapshot
        """
        mock_jobs.return_value = self.test_jobs_data["jobs"]
        mock_followups.return_value = self.test_followups_data
        mock_journal.return_value = self.test_journal_data

        response = self.client.get("/api/stats2/heatmap?year=2025")

        assert response.status_code == 200
        actual_data = json.loads(response.data)

        snapshot_name = "stats2_heatmap_response"
        expected_snapshot = self._load_snapshot(snapshot_name)

        if self._should_update_snapshots() or expected_snapshot is None:
            self._save_snapshot(snapshot_name, actual_data)
            expected_snapshot = actual_data

        # Verify structure
        assert actual_data["success"] is True
        assert "data" in actual_data

        # Verify heatmap data keys
        expected_heatmaps = ["applications_weekday_week", "followup_intensity", "mood_vs_activity", "hourly_engagement"]

        for heatmap_name in expected_heatmaps:
            assert heatmap_name in actual_data["data"]

        # Compare with snapshot (excluding timestamps)
        actual_copy = json.loads(json.dumps(actual_data))
        if "metadata" in actual_copy and "generated_at" in actual_copy["metadata"]:
            actual_copy["metadata"]["generated_at"] = "TIMESTAMP_PLACEHOLDER"

        expected_copy = json.loads(json.dumps(expected_snapshot))
        if "metadata" in expected_copy and "generated_at" in expected_copy["metadata"]:
            expected_copy["metadata"]["generated_at"] = "TIMESTAMP_PLACEHOLDER"

        assert actual_copy == expected_copy

    def test_api_years_contract(self):
        """
        GIVEN: Jobs data spanning multiple years
        WHEN: Calling /api/years
        THEN: Years list format matches snapshot
        """
        with patch("app.load_jobs") as mock_jobs:
            # Mock jobs from different years
            mock_jobs.return_value = [
                {"date_applied": "2024-10-01", "company": "Corp1"},
                {"date_applied": "2025-01-15", "company": "Corp2"},
                {"date_applied": "2025-10-01", "company": "Corp3"},
            ]

            response = self.client.get("/api/years")

            assert response.status_code == 200
            actual_data = json.loads(response.data)

            snapshot_name = "api_years_response"
            expected_snapshot = self._load_snapshot(snapshot_name)

            if self._should_update_snapshots() or expected_snapshot is None:
                self._save_snapshot(snapshot_name, actual_data)
                expected_snapshot = actual_data

            # Verify structure
            assert "years" in actual_data
            assert isinstance(actual_data["years"], list)

            # Years should be integers, sorted descending
            years = actual_data["years"]
            assert all(isinstance(year, int) for year in years)
            assert years == sorted(years, reverse=True)

            # Compare with snapshot
            assert actual_data == expected_snapshot

    def test_job_schema_backward_compatibility(self):
        """
        GIVEN: Current job data structure
        WHEN: Comparing with v2 schema
        THEN: All required fields are present and types match
        """
        with patch("app.load_jobs") as mock_jobs:
            mock_jobs.return_value = self.test_jobs_data["jobs"]

            response = self.client.get("/api/jobs")

            assert response.status_code == 200
            actual_data = json.loads(response.data)

            # Verify jobs structure hasn't changed
            assert "jobs" in actual_data

            if actual_data["jobs"]:
                job = actual_data["jobs"][0]

                # Required fields from v2 schema
                required_fields = ["job_id", "company", "title", "date_applied", "status", "stage", "source"]

                for field in required_fields:
                    assert field in job, f"Required field '{field}' missing from job schema"

                # Verify job_id format
                assert job["job_id"].startswith("job_")
                assert len(job["job_id"]) == 16

    def test_followup_schema_backward_compatibility(self):
        """
        GIVEN: Current followup data structure
        WHEN: Comparing with v1 schema
        THEN: All required fields are present and types match
        """
        with patch("app.load_followups") as mock_followups:
            mock_followups.return_value = self.test_followups_data

            response = self.client.get("/api/followups")

            assert response.status_code == 200
            actual_data = json.loads(response.data)

            if "followups" in actual_data and actual_data["followups"]:
                followup = actual_data["followups"][0]

                # Required fields from v1 schema
                required_fields = ["id", "job_id", "timestamp", "author", "type", "summary"]

                for field in required_fields:
                    assert field in followup, f"Required field '{field}' missing from followup schema"

                # Verify ID format
                assert followup["id"].startswith("fu_")
                assert followup["job_id"].startswith("job_")

    def test_breaking_change_detection(self):
        """
        GIVEN: All current API endpoints
        WHEN: Making requests to each endpoint
        THEN: No breaking changes in response structure
        """
        # Test multiple endpoints to ensure no breaking changes
        endpoints_to_test = ["/api/health", "/api/jobs/statistics", "/api/timeline"]

        for endpoint in endpoints_to_test:
            response = self.client.get(endpoint)

            # Should not return 404 or 500 (breaking changes)
            assert response.status_code not in [404, 500], f"Breaking change detected in {endpoint}"

            # Should return valid JSON
            try:
                json.loads(response.data)
            except json.JSONDecodeError:
                pytest.fail(f"Invalid JSON response from {endpoint}")


def create_snapshot_update_helper():
    """Helper function to create snapshot update utility."""

    def update_snapshots():
        """Update all snapshots by setting environment variable and running tests."""
        os.environ["UPDATE_SNAPSHOTS"] = "1"

        try:
            # Run the contract tests to update snapshots
            pytest.main([__file__, "-v"])
        finally:
            # Clean up environment variable
            if "UPDATE_SNAPSHOTS" in os.environ:
                del os.environ["UPDATE_SNAPSHOTS"]

    return update_snapshots


# Export the helper for external use
update_all_snapshots = create_snapshot_update_helper()
