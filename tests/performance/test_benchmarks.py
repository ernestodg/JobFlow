"""Performance benchmarks for JobFlow Tracker components."""

import os
import sys

# Add project root to path - must be at top for E402
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import tempfile
from unittest.mock import patch

import pytest

from core_data import load_followups, load_jobs, save_jobs
from utils import calculate_days_between, format_date


class TestDataLoadingPerformance:
    """Benchmark data loading operations."""

    def test_load_jobs_performance(self, benchmark):
        """Benchmark jobs loading with various data sizes."""
        result = benchmark(load_jobs)
        assert isinstance(result, list)

    def test_load_followups_performance(self, benchmark):
        """Benchmark followups loading."""
        result = benchmark(load_followups)
        assert isinstance(result, list)

    @pytest.mark.parametrize("job_count", [100, 500, 1000])
    def test_save_jobs_performance(self, benchmark, job_count):
        """Benchmark saving jobs with different data volumes."""
        # Generate test data
        jobs = []
        for i in range(job_count):
            jobs.append(
                {
                    "id": f"job_{i}",
                    "company": f"Company {i}",
                    "position": f"Position {i}",
                    "status": "applied",
                    "applied_date": "2024-01-01",
                    "source": "website",
                    "notes": f"Test job {i}" * 10,  # Make notes longer
                }
            )

        # Use temporary file for benchmarking
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_file = f.name

        try:
            with patch("core_data.JOBS_FILE", temp_file):
                result = benchmark(save_jobs, jobs)
            assert result is True
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)


class TestUtilsPerformance:
    """Benchmark utility functions."""

    def test_calculate_days_between_performance(self, benchmark):
        """Benchmark date calculation with various inputs."""
        result = benchmark(calculate_days_between, "2024-01-01", "2024-12-31")
        assert isinstance(result, int)

    def test_format_date_performance(self, benchmark):
        """Benchmark date formatting."""
        result = benchmark(format_date, "2024-01-01")
        assert isinstance(result, str)

    @pytest.mark.parametrize("date_count", [100, 500, 1000])
    def test_bulk_date_operations(self, benchmark, date_count):
        """Benchmark bulk date operations."""
        dates = [f"2024-{i%12+1:02d}-{i%28+1:02d}" for i in range(date_count)]

        def bulk_format_dates():
            return [format_date(date) for date in dates]

        result = benchmark(bulk_format_dates)
        assert len(result) == date_count


class TestAPIPerformance:
    """Benchmark API endpoints."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        import os
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

        from app import app

        app.config["TESTING"] = True
        return app

    def test_stats_endpoint_performance(self, benchmark, app):
        """Benchmark /api/stats endpoint."""
        with app.test_client() as client:

            def get_stats():
                return client.get("/api/stats")

            response = benchmark(get_stats)
            assert response.status_code == 200

    def test_jobs_endpoint_performance(self, benchmark, app):
        """Benchmark /api/jobs endpoint."""
        with app.test_client() as client:

            def get_jobs():
                return client.get("/api/jobs")

            response = benchmark(get_jobs)
            assert response.status_code == 200

    def test_stats2_scatter_performance(self, benchmark, app):
        """Benchmark /api/stats2/scatter endpoint."""
        with app.test_client() as client:

            def get_scatter():
                return client.get("/api/stats2/scatter")

            response = benchmark(get_scatter)
            assert response.status_code == 200

    def test_stats2_heatmap_performance(self, benchmark, app):
        """Benchmark /api/stats2/heatmap endpoint."""
        with app.test_client() as client:

            def get_heatmap():
                return client.get("/api/stats2/heatmap")

            response = benchmark(get_heatmap)
            assert response.status_code == 200


class TestMemoryUsage:
    """Memory usage tests for key operations."""

    @pytest.mark.skip(reason="Memory profiling requires memory_profiler")
    def test_data_loading_memory(self):
        """Test memory usage during data loading."""
        from memory_profiler import profile

        @profile
        def load_all_data():
            jobs = load_jobs()
            followups = load_followups()
            return jobs, followups

        result = load_all_data()
        assert result is not None
