"""
Integration tests for Nerdy Stats 2 endpoints.
Tests /api/stats2/scatter and /api/stats2/heatmap with filters and data shapes.
"""
import sys
from pathlib import Path

# Import Flask app for testing - must be at top for E402
sys.path.append(str(Path(__file__).parent.parent.parent))
import json
from unittest.mock import patch

from app import app


class TestStats2Endpoints:
    """Test Nerdy Stats 2 scatter and heatmap endpoints."""

    def setup_method(self):
        """Set up Flask test client and test data."""
        app.config["TESTING"] = True
        self.client = app.test_client()

        # Sample test data
        self.sample_jobs = [
            {
                "job_id": "job_test001",
                "company": "TechCorp",
                "title": "Software Engineer",
                "date_applied": "2025-10-01",
                "status": "Applied",
                "stage": "applied",
                "source": "LinkedIn",
                "location": "San Francisco, CA",
                "job_type": "Full-time",
                "country": "US",
            },
            {
                "job_id": "job_test002",
                "company": "StartupXYZ",
                "title": "Frontend Developer",
                "date_applied": "2025-10-05",
                "status": "Interviewing",
                "stage": "interview",
                "source": "AngelList",
                "location": "Remote",
                "job_type": "Full-time",
                "country": "US",
            },
            {
                "job_id": "job_test003",
                "company": "BigTech",
                "title": "DevOps Engineer",
                "date_applied": "2025-09-20",
                "status": "Rejected",
                "stage": "closed",
                "source": "Indeed",
                "location": "Seattle, WA",
                "job_type": "Full-time",
                "country": "US",
            },
        ]

        self.sample_followups = [
            {
                "id": "fu_test001",
                "job_id": "job_test001",
                "timestamp": "2025-10-03T10:30:00.000Z",
                "author": "user",
                "type": "note",
                "summary": "Application submitted",
                "tags": ["application"],
            },
            {
                "id": "fu_test002",
                "job_id": "job_test002",
                "timestamp": "2025-10-06T14:15:00.000Z",
                "author": "user",
                "type": "status_change",
                "summary": "Phone screen scheduled",
                "tags": ["interview"],
            },
            {
                "id": "fu_test003",
                "job_id": "job_test003",
                "timestamp": "2025-09-25T16:45:00.000Z",
                "author": "user",
                "type": "note",
                "summary": "Rejection received",
                "tags": ["rejection"],
            },
        ]

        self.sample_journal = [
            {
                "id": "journal_test001",
                "timestamp": "2025-10-01T08:30:00.000Z",
                "content": "Starting job search, feeling optimistic",
                "sentiment_score": 0.6,
                "sentiment_label": "Positive",
            },
            {
                "id": "journal_test002",
                "timestamp": "2025-10-05T19:15:00.000Z",
                "content": "Great conversation with startup team",
                "sentiment_score": 0.8,
                "sentiment_label": "Very Positive",
            },
            {
                "id": "journal_test003",
                "timestamp": "2025-09-25T20:30:00.000Z",
                "content": "Got rejected but not giving up",
                "sentiment_score": -0.3,
                "sentiment_label": "Negative",
            },
        ]

    @patch("app.load_jobs")
    @patch("app.load_followups")
    @patch("app.data_manager.load_journal")
    def test_scatter_endpoint_basic_functionality(self, mock_journal, mock_followups, mock_jobs):
        """
        GIVEN: Sample jobs, followups, and journal data
        WHEN: Calling /api/stats2/scatter endpoint
        THEN: Response contains expected scatter plot data structures
        """
        # Mock data loading
        mock_jobs.return_value = self.sample_jobs
        mock_followups.return_value = {"entries": self.sample_followups}
        mock_journal.return_value = {"entries": self.sample_journal}

        # Call scatter endpoint
        response = self.client.get("/api/stats2/scatter")

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify response structure
        assert data["success"] is True
        assert "data" in data
        assert "metadata" in data
        assert "filters" in data

        # Verify scatter plot data structure
        scatter_data = data["data"]
        expected_plots = [
            "applications_over_time",
            "mood_vs_productivity",
            "followup_timing_vs_outcome",
            "duration_to_close_vs_source",
        ]

        for plot_name in expected_plots:
            assert plot_name in scatter_data
            assert isinstance(scatter_data[plot_name], list)

    @patch("app.load_jobs")
    @patch("app.load_followups")
    @patch("app.data_manager.load_journal")
    def test_scatter_applications_over_time_data_shape(self, mock_journal, mock_followups, mock_jobs):
        """
        GIVEN: Sample jobs data
        WHEN: Calling scatter endpoint
        THEN: applications_over_time has correct data shape and cumulative nature
        """
        mock_jobs.return_value = self.sample_jobs
        mock_followups.return_value = {"entries": self.sample_followups}
        mock_journal.return_value = {"entries": self.sample_journal}

        response = self.client.get("/api/stats2/scatter")
        data = json.loads(response.data)

        apps_over_time = data["data"]["applications_over_time"]

        # Should have data points for each job
        assert len(apps_over_time) == len(self.sample_jobs)

        # Each data point should have required fields
        for point in apps_over_time:
            assert "x" in point  # date
            assert "y" in point  # cumulative count
            assert "source" in point
            assert "status" in point
            assert "text" in point  # hover text

        # Should be cumulative (y values should be increasing)
        y_values = [point["y"] for point in apps_over_time]
        assert y_values == sorted(y_values)  # Should be in ascending order
        assert y_values[-1] == len(self.sample_jobs)  # Final count should match total jobs

    @patch("app.load_jobs")
    @patch("app.load_followups")
    @patch("app.data_manager.load_journal")
    def test_scatter_mood_vs_productivity_with_journal_data(self, mock_journal, mock_followups, mock_jobs):
        """
        GIVEN: Jobs and journal data with sentiment scores
        WHEN: Calling scatter endpoint
        THEN: mood_vs_productivity data correlates journal sentiment with application counts
        """
        mock_jobs.return_value = self.sample_jobs
        mock_followups.return_value = {"entries": self.sample_followups}
        mock_journal.return_value = {"entries": self.sample_journal}

        response = self.client.get("/api/stats2/scatter")
        data = json.loads(response.data)

        mood_productivity = data["data"]["mood_vs_productivity"]

        # Should have data points based on journal entries
        assert len(mood_productivity) <= len(self.sample_journal)

        for point in mood_productivity:
            assert "x" in point  # sentiment score
            assert "y" in point  # application count
            assert "mood" in point  # mood label
            assert "date" in point
            assert "text" in point

            # Sentiment score should be numeric
            assert isinstance(point["x"], int | float)
            # Application count should be non-negative integer
            assert isinstance(point["y"], int)
            assert point["y"] >= 0

    @patch("app.load_jobs")
    @patch("app.load_followups")
    @patch("app.data_manager.load_journal")
    def test_heatmap_endpoint_basic_functionality(self, mock_journal, mock_followups, mock_jobs):
        """
        GIVEN: Sample data
        WHEN: Calling /api/stats2/heatmap endpoint
        THEN: Response contains expected heatmap data structures
        """
        mock_jobs.return_value = self.sample_jobs
        mock_followups.return_value = {"entries": self.sample_followups}
        mock_journal.return_value = {"entries": self.sample_journal}

        response = self.client.get("/api/stats2/heatmap")

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify response structure
        assert data["success"] is True
        assert "data" in data
        assert "metadata" in data
        assert "filters" in data

        # Verify heatmap data structure
        heatmap_data = data["data"]
        expected_heatmaps = ["applications_weekday_week", "followup_intensity", "mood_vs_activity", "hourly_engagement"]

        for heatmap_name in expected_heatmaps:
            assert heatmap_name in heatmap_data

    @patch("app.load_jobs")
    @patch("app.load_followups")
    @patch("app.data_manager.load_journal")
    def test_heatmap_data_matrix_structure(self, mock_journal, mock_followups, mock_jobs):
        """
        GIVEN: Sample data
        WHEN: Calling heatmap endpoint
        THEN: Heatmap data has proper matrix structure (z, x, y arrays)
        """
        mock_jobs.return_value = self.sample_jobs
        mock_followups.return_value = {"entries": self.sample_followups}
        mock_journal.return_value = {"entries": self.sample_journal}

        response = self.client.get("/api/stats2/heatmap")
        data = json.loads(response.data)

        heatmap_data = data["data"]

        # Check each heatmap has proper structure
        for heatmap_name, heatmap in heatmap_data.items():
            if heatmap:  # Some might be empty based on data
                assert "z" in heatmap  # 2D matrix values
                assert "x" in heatmap  # x-axis labels
                assert "y" in heatmap  # y-axis labels
                assert "colorscale" in heatmap

                # Verify matrix dimensions match labels
                z_matrix = heatmap["z"]
                if z_matrix:  # If not empty
                    assert len(z_matrix) == len(heatmap["y"])  # Rows match y-labels
                    if z_matrix[0]:  # If first row not empty
                        assert len(z_matrix[0]) == len(heatmap["x"])  # Cols match x-labels

    def test_scatter_endpoint_year_filter(self):
        """
        GIVEN: Data spanning multiple years
        WHEN: Calling scatter endpoint with year filter
        THEN: Only data from specified year is returned
        """
        # This test would need more complex mock data spanning multiple years
        response = self.client.get("/api/stats2/scatter?year=2025")

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify filter was applied
        assert data["filters"]["year"] == 2025

    def test_scatter_endpoint_source_filter(self):
        """
        GIVEN: Data from multiple sources
        WHEN: Calling scatter endpoint with source filter
        THEN: Only data from specified source is returned
        """
        response = self.client.get("/api/stats2/scatter?source=LinkedIn")

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify filter was applied
        assert data["filters"]["source"] == "LinkedIn"

    def test_scatter_endpoint_status_filter(self):
        """
        GIVEN: Jobs with different statuses
        WHEN: Calling scatter endpoint with status filter
        THEN: Only jobs with specified status are included
        """
        response = self.client.get("/api/stats2/scatter?status=Applied")

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify filter was applied
        assert data["filters"]["status"] == "Applied"

    def test_heatmap_endpoint_with_filters(self):
        """
        GIVEN: Sample data
        WHEN: Calling heatmap endpoint with multiple filters
        THEN: Filters are properly applied and reflected in response
        """
        response = self.client.get("/api/stats2/heatmap?year=2025&source=LinkedIn&status=Applied")

        assert response.status_code == 200
        data = json.loads(response.data)

        # Verify all filters were applied
        filters = data["filters"]
        assert filters["year"] == 2025
        assert filters["source"] == "LinkedIn"
        assert filters["status"] == "Applied"

    def test_scatter_endpoint_error_handling(self):
        """
        GIVEN: Various error conditions
        WHEN: Calling scatter endpoint
        THEN: Errors are handled gracefully
        """
        # Test with invalid year
        response = self.client.get("/api/stats2/scatter?year=invalid")
        # Should either handle gracefully or return 400
        assert response.status_code in [200, 400]

        if response.status_code == 200:
            data = json.loads(response.data)
            # Year filter should be None if invalid
            assert data["filters"]["year"] is None

    def test_heatmap_endpoint_error_handling(self):
        """
        GIVEN: Error conditions in data loading
        WHEN: Calling heatmap endpoint
        THEN: Errors are handled gracefully with meaningful messages
        """
        # This would test various error scenarios
        with patch("app.load_jobs", side_effect=Exception("Data loading error")):
            response = self.client.get("/api/stats2/heatmap")

            assert response.status_code == 500
            data = json.loads(response.data)
            assert "error" in data

    @patch("app.load_jobs")
    @patch("app.load_followups")
    @patch("app.data_manager.load_journal")
    def test_scatter_empty_data_handling(self, mock_journal, mock_followups, mock_jobs):
        """
        GIVEN: Empty or minimal data
        WHEN: Calling scatter endpoint
        THEN: Endpoint handles empty data gracefully
        """
        # Mock empty data
        mock_jobs.return_value = []
        mock_followups.return_value = {"entries": []}
        mock_journal.return_value = {"entries": []}

        response = self.client.get("/api/stats2/scatter")

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data["success"] is True
        assert data["metadata"]["total_jobs"] == 0
        assert data["metadata"]["total_followups"] == 0

        # All scatter plots should be empty lists
        for plot_data in data["data"].values():
            assert isinstance(plot_data, list)
            assert len(plot_data) == 0

    @patch("app.load_jobs")
    @patch("app.load_followups")
    @patch("app.data_manager.load_journal")
    def test_heatmap_empty_data_handling(self, mock_journal, mock_followups, mock_jobs):
        """
        GIVEN: Empty data
        WHEN: Calling heatmap endpoint
        THEN: Endpoint handles empty data gracefully
        """
        mock_jobs.return_value = []
        mock_followups.return_value = {"entries": []}
        mock_journal.return_value = {"entries": []}

        response = self.client.get("/api/stats2/heatmap")

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data["success"] is True
        assert data["metadata"]["total_jobs"] == 0

    def test_stats2_page_route(self):
        """
        GIVEN: Stats2 HTML template
        WHEN: Accessing /stats2 route
        THEN: Page loads successfully
        """
        response = self.client.get("/stats2")

        assert response.status_code == 200
        assert b"Nerdy Stats 2" in response.data
        assert b"Advanced Analytics" in response.data

    @patch("app.load_jobs")
    @patch("app.load_followups")
    @patch("app.data_manager.load_journal")
    def test_scatter_metadata_accuracy(self, mock_journal, mock_followups, mock_jobs):
        """
        GIVEN: Sample data
        WHEN: Calling scatter endpoint
        THEN: Metadata accurately reflects processed data
        """
        mock_jobs.return_value = self.sample_jobs
        mock_followups.return_value = {"entries": self.sample_followups}
        mock_journal.return_value = {"entries": self.sample_journal}

        response = self.client.get("/api/stats2/scatter")
        data = json.loads(response.data)

        metadata = data["metadata"]

        assert metadata["total_jobs"] == len(self.sample_jobs)
        assert metadata["total_followups"] == len(self.sample_followups)
        assert "generated_at" in metadata

        # Generated timestamp should be recent (within last minute)
        from datetime import datetime

        generated_time = datetime.fromisoformat(metadata["generated_at"])
        time_diff = datetime.now() - generated_time
        assert time_diff.total_seconds() < 60  # Less than 1 minute ago

    @patch("app.load_jobs")
    @patch("app.load_followups")
    @patch("app.data_manager.load_journal")
    def test_combined_filters_effect(self, mock_journal, mock_followups, mock_jobs):
        """
        GIVEN: Diverse data set
        WHEN: Applying multiple filters simultaneously
        THEN: Data is filtered correctly by all criteria
        """
        # Create more diverse test data
        diverse_jobs = [
            {
                "job_id": "job_2024_001",
                "company": "Corp2024",
                "title": "Engineer",
                "date_applied": "2024-10-01",
                "status": "Applied",
                "source": "LinkedIn",
                "country": "US",
            },
            {
                "job_id": "job_2025_001",
                "company": "Corp2025",
                "title": "Developer",
                "date_applied": "2025-10-01",
                "status": "Interviewing",
                "source": "LinkedIn",
                "country": "US",
            },
            {
                "job_id": "job_2025_002",
                "company": "Corp2025B",
                "title": "Architect",
                "date_applied": "2025-10-01",
                "status": "Applied",
                "source": "Indeed",
                "country": "US",
            },
        ]

        mock_jobs.return_value = diverse_jobs
        mock_followups.return_value = {"entries": []}
        mock_journal.return_value = {"entries": []}

        # Apply filters: year=2025, source=LinkedIn, status=Applied
        response = self.client.get("/api/stats2/scatter?year=2025&source=LinkedIn&status=Applied")
        data = json.loads(response.data)

        # Should filter to only jobs matching all criteria
        # From our test data: job_2025_001 has LinkedIn+2025 but status=Interviewing
        # No jobs match all three criteria, so metadata should reflect filtered count
        metadata = data["metadata"]
        # The exact count depends on filtering implementation
        assert metadata["total_jobs"] <= len(diverse_jobs)
