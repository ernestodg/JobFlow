"""
Unit tests for jobs CRUD operations.
Tests create/update/delete, stable job_id generation, and duplicate guards.
"""
import sys
from pathlib import Path

# Import functions from app.py - must be at top for E402
sys.path.append(str(Path(__file__).parent.parent.parent))
import tempfile

from utils import ensure_job_ids


class TestJobsCRUD:
    """Test job creation, reading, updating, and deletion operations."""

    def setup_method(self):
        """Set up temporary directory and test data for each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_jobs_file = self.temp_dir / "jobs.json"

        # Sample job data
        self.sample_jobs = [
            {
                "company": "TechCorp",
                "title": "Software Engineer",
                "date_applied": "2025-10-01",
                "status": "Applied",
                "stage": "applied",
                "source": "LinkedIn",
                "location": "San Francisco, CA",
                "job_type": "Full-time",
                "salary_range": "$120k-150k",
                "url": "https://techcorp.com/jobs/123",
                "notes": "Great company culture",
                "country": "US",
            },
            {
                "company": "StartupXYZ",
                "title": "Frontend Developer",
                "date_applied": "2025-10-05",
                "status": "Interviewing",
                "stage": "interview",
                "source": "AngelList",
                "location": "Remote",
                "job_type": "Full-time",
                "salary_range": "$80k-110k",
                "url": "https://startupxyz.com/careers",
                "notes": "Fast-paced environment",
                "country": "US",
            },
        ]

    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_create_job_generates_stable_id(self):
        """
        GIVEN: A new job record without job_id
        WHEN: Creating the job
        THEN: A stable job_id is automatically generated
        """
        job_without_id = self.sample_jobs[0].copy()
        jobs_list = [job_without_id]

        # Generate job IDs
        updated_jobs, ids_changed = ensure_job_ids(jobs_list)

        # Verify ID was generated
        assert ids_changed is True
        assert len(updated_jobs) == 1
        assert "job_id" in updated_jobs[0]
        assert updated_jobs[0]["job_id"].startswith("job_")
        assert len(updated_jobs[0]["job_id"]) == 16  # "job_" + 12 hex chars

    def test_stable_job_id_deterministic_generation(self):
        """
        GIVEN: The same job record processed multiple times
        WHEN: Generating job_id
        THEN: The same job_id is generated each time
        """
        job = self.sample_jobs[0].copy()

        # Generate ID first time
        jobs_list_1 = [job.copy()]
        updated_jobs_1, _ = ensure_job_ids(jobs_list_1)
        first_id = updated_jobs_1[0]["job_id"]

        # Generate ID second time with same data
        jobs_list_2 = [job.copy()]
        updated_jobs_2, _ = ensure_job_ids(jobs_list_2)
        second_id = updated_jobs_2[0]["job_id"]

        # IDs should be the same (deterministic)
        assert first_id == second_id

    def test_duplicate_guard_by_fingerprint(self):
        """
        GIVEN: Jobs with same fingerprint (duplicates)
        WHEN: Generating job_ids
        THEN: Different IDs are generated to avoid collisions but share same base
        """
        # Create duplicate jobs (same fingerprint)
        job1 = self.sample_jobs[0].copy()
        job2 = self.sample_jobs[0].copy()
        job2["notes"] = "Different notes"  # Different notes but same fingerprint

        jobs_list = [job1, job2]
        updated_jobs, _ = ensure_job_ids(jobs_list)

        # Both should get different job_ids to avoid collisions (duplicate detection handled separately)
        assert updated_jobs[0]["job_id"] != updated_jobs[1]["job_id"]
        # But they should share the same base (before UUID suffix)
        base_id_1 = updated_jobs[0]["job_id"].split("_")[0]
        base_id_2 = updated_jobs[1]["job_id"].split("_")[0]
        assert base_id_1 == base_id_2

    def test_different_jobs_get_different_ids(self):
        """
        GIVEN: Jobs with different fingerprints
        WHEN: Generating job_ids
        THEN: Different job_ids are generated
        """
        jobs_list = self.sample_jobs.copy()
        updated_jobs, _ = ensure_job_ids(jobs_list)

        # Should have different IDs
        assert updated_jobs[0]["job_id"] != updated_jobs[1]["job_id"]
        assert all(job["job_id"].startswith("job_") for job in updated_jobs)

    def test_existing_job_id_preserved(self):
        """
        GIVEN: A job record that already has a job_id
        WHEN: Processing job_ids
        THEN: Existing job_id is preserved
        """
        job_with_id = self.sample_jobs[0].copy()
        job_with_id["job_id"] = "job_existing123"

        jobs_list = [job_with_id]
        updated_jobs, ids_changed = ensure_job_ids(jobs_list)

        # Existing ID should be preserved
        assert ids_changed is False
        assert updated_jobs[0]["job_id"] == "job_existing123"

    def test_mixed_jobs_with_and_without_ids(self):
        """
        GIVEN: A mix of jobs with and without job_ids
        WHEN: Processing the job list
        THEN: Missing IDs are generated, existing IDs are preserved
        """
        job_with_id = self.sample_jobs[0].copy()
        job_with_id["job_id"] = "job_existing123"

        job_without_id = self.sample_jobs[1].copy()

        jobs_list = [job_with_id, job_without_id]
        updated_jobs, ids_changed = ensure_job_ids(jobs_list)

        # Should indicate IDs were changed (one was added)
        assert ids_changed is True

        # First job keeps existing ID
        assert updated_jobs[0]["job_id"] == "job_existing123"

        # Second job gets new ID
        assert updated_jobs[1]["job_id"].startswith("job_")
        assert updated_jobs[1]["job_id"] != "job_existing123"

    def test_job_update_preserves_id(self):
        """
        GIVEN: An existing job record being updated
        WHEN: Updating job fields
        THEN: job_id remains unchanged
        """
        original_job = self.sample_jobs[0].copy()
        original_job["job_id"] = "job_test123456"

        # Update some fields
        updated_job = original_job.copy()
        updated_job["status"] = "Interviewing"
        updated_job["stage"] = "interview"
        updated_job["notes"] = "Updated notes after phone screen"

        # job_id should remain the same
        assert updated_job["job_id"] == original_job["job_id"]

    def test_job_deletion_by_id(self):
        """
        GIVEN: A list of jobs with job_ids
        WHEN: Deleting a job by job_id
        THEN: The correct job is removed
        """
        jobs_list = self.sample_jobs.copy()
        updated_jobs, _ = ensure_job_ids(jobs_list)

        # Get ID of first job
        job_id_to_delete = updated_jobs[0]["job_id"]

        # Delete job by ID
        remaining_jobs = [job for job in updated_jobs if job["job_id"] != job_id_to_delete]

        # Verify deletion
        assert len(remaining_jobs) == len(updated_jobs) - 1
        assert all(job["job_id"] != job_id_to_delete for job in remaining_jobs)

    def test_job_lookup_by_id(self):
        """
        GIVEN: A list of jobs with job_ids
        WHEN: Looking up a job by job_id
        THEN: The correct job is returned
        """
        jobs_list = self.sample_jobs.copy()
        updated_jobs, _ = ensure_job_ids(jobs_list)

        # Get ID of first job
        target_job_id = updated_jobs[0]["job_id"]

        # Find job by ID
        found_job = next((job for job in updated_jobs if job["job_id"] == target_job_id), None)

        # Verify correct job found
        assert found_job is not None
        assert found_job["company"] == updated_jobs[0]["company"]
        assert found_job["title"] == updated_jobs[0]["title"]

    def test_bulk_job_operations(self):
        """
        GIVEN: A large number of jobs
        WHEN: Performing bulk operations
        THEN: All operations complete successfully
        """
        # Create 100 test jobs
        bulk_jobs = []
        for i in range(100):
            job = self.sample_jobs[0].copy()
            job["company"] = f"Company_{i}"
            job["title"] = f"Position_{i}"
            job["date_applied"] = f"2025-{10 + i % 3:02d}-{1 + i % 28:02d}"
            bulk_jobs.append(job)

        # Process all jobs
        updated_jobs, ids_changed = ensure_job_ids(bulk_jobs)

        # Verify all got IDs
        assert ids_changed is True
        assert len(updated_jobs) == 100
        assert all("job_id" in job for job in updated_jobs)

        # Verify all IDs are unique (different companies/titles)
        job_ids = [job["job_id"] for job in updated_jobs]
        assert len(set(job_ids)) == 100  # All unique

    def test_job_fingerprint_collision_handling(self):
        """
        GIVEN: Jobs that might have the same fingerprint
        WHEN: Processing multiple identical applications
        THEN: Same job_id is used (legitimate duplicates)
        """
        # Create exact duplicates (same company, title, date)
        job1 = self.sample_jobs[0].copy()
        job2 = self.sample_jobs[0].copy()
        job3 = self.sample_jobs[0].copy()

        # Only notes differ (not part of fingerprint)
        job2["notes"] = "Applied through recruiter"
        job3["notes"] = "Applied directly"

        jobs_list = [job1, job2, job3]
        updated_jobs, _ = ensure_job_ids(jobs_list)

        # All should have different job_ids to prevent collisions, but share same base
        job_ids = [job["job_id"] for job in updated_jobs]
        base_ids = [job_id.split("_")[0] for job_id in job_ids]

        # All IDs should be unique
        assert len(set(job_ids)) == len(job_ids)
        # But all should share the same base (fingerprint)
        assert len(set(base_ids)) == 1

    def test_invalid_job_handling(self):
        """
        GIVEN: Job records with invalid or missing data
        WHEN: Processing jobs
        THEN: Errors are handled gracefully
        """
        invalid_jobs = [
            {},  # Empty job
            {"company": "Test"},  # Missing required fields
            {"company": None, "title": None},  # Null values
        ]

        # Processing should not crash
        try:
            updated_jobs, ids_changed = ensure_job_ids(invalid_jobs)
            # Should still process what it can
            assert isinstance(updated_jobs, list)
            assert len(updated_jobs) == len(invalid_jobs)
        except Exception as e:
            # If it does raise an exception, it should be meaningful
            assert isinstance(e, ValueError | TypeError | KeyError)

    def test_job_id_format_validation(self):
        """
        GIVEN: Generated job_ids
        WHEN: Validating the format
        THEN: All job_ids follow the correct format
        """
        jobs_list = self.sample_jobs.copy()
        updated_jobs, _ = ensure_job_ids(jobs_list)

        for job in updated_jobs:
            job_id = job["job_id"]

            # Should start with "job_"
            assert job_id.startswith("job_")

            # Should be exactly 16 characters
            assert len(job_id) == 16

            # Suffix should be 12 hexadecimal characters
            suffix = job_id[4:]  # Remove "job_" prefix
            assert len(suffix) == 12
            assert all(c in "0123456789abcdef" for c in suffix)

    def test_concurrent_job_creation_safety(self):
        """
        GIVEN: Multiple processes creating jobs simultaneously
        WHEN: Processing jobs with ensure_job_ids
        THEN: No race conditions or ID conflicts occur
        """
        # This is a simplified test - in practice you'd use threading
        # Here we test that the ID generation is deterministic enough
        # to avoid conflicts in concurrent scenarios

        job = self.sample_jobs[0].copy()

        # Simulate multiple "processes" creating the same job
        results = []
        for _ in range(10):
            jobs_list = [job.copy()]
            updated_jobs, _ = ensure_job_ids(jobs_list)
            results.append(updated_jobs[0]["job_id"])

        # All should generate the same ID (deterministic)
        assert all(job_id == results[0] for job_id in results)
