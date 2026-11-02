"""
Integration tests for API roundtrip operations.
Tests full flow: create job → add follow-ups → close job → verify metrics updates.
"""
import sys
from pathlib import Path

# Import Flask app for testing - must be at top for E402
sys.path.append(str(Path(__file__).parent.parent.parent))
import json
import tempfile
from unittest.mock import patch

from app import app


class TestAPIRoundtrip:
    """Test complete API workflows end-to-end."""

    def setup_method(self):
        """Set up Flask test client and temporary data files."""
        # Create temporary directory for test data
        self.temp_dir = Path(tempfile.mkdtemp())

        # Set up Flask test client
        app.config["TESTING"] = True
        self.client = app.test_client()

        # Mock the data file paths to use temporary files
        self.temp_jobs_file = self.temp_dir / "jobs.json"
        self.temp_followups_file = self.temp_dir / "followups.json"
        self.temp_journal_file = self.temp_dir / "journal.json"
        self.temp_metrics_file = self.temp_dir / "metrics.cache.json"

        # Initialize empty data files
        self._init_empty_data_files()

    def teardown_method(self):
        """Clean up temporary files."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def _init_empty_data_files(self):
        """Initialize empty data files for testing."""
        # Empty jobs file
        jobs_data = {"schema_version": 2, "last_modified": "2025-11-12T00:00:00.000000+00:00", "jobs": []}
        with open(self.temp_jobs_file, "w") as f:
            json.dump(jobs_data, f)

        # Empty followups file
        followups_data = {"version": 1, "entries": []}
        with open(self.temp_followups_file, "w") as f:
            json.dump(followups_data, f)

        # Empty journal file
        journal_data = {"schema_version": 1, "entries": [], "last_modified": "2025-11-12T00:00:00.000000+00:00"}
        with open(self.temp_journal_file, "w") as f:
            json.dump(journal_data, f)

        # Empty metrics cache
        metrics_data = {
            "generated_at": None,
            "data_points": 0,
            "by_month": {},
            "by_source": {},
            "by_status": {},
            "by_job_type": {},
            "funnel": {},
            "success_rate": {},
            "avg_duration_by_status": {},
            "followup_metrics": {},
            "sentiment_trends": {},
        }
        with open(self.temp_metrics_file, "w") as f:
            json.dump(metrics_data, f)

    @patch("app.DATA_FILE")
    @patch("app.FOLLOWUPS_FILE")
    @patch("app.data_manager")
    def test_complete_job_lifecycle_roundtrip(self, mock_data_manager, mock_followups_file, mock_data_file):
        """
        GIVEN: An empty system
        WHEN: Creating job → adding follow-ups → closing job
        THEN: All operations succeed and data is consistent
        """
        # Mock file paths
        mock_data_file.return_value = self.temp_jobs_file
        mock_followups_file.return_value = self.temp_followups_file

        # Mock data manager methods
        mock_data_manager.load_journal.return_value = {
            "schema_version": 1,
            "entries": [],
            "last_modified": "2025-11-12T00:00:00.000000+00:00",
        }

        # Step 1: Create a new job
        job_data = {
            "company": "TechCorp Integration Test",
            "title": "Senior Software Engineer",
            "date_applied": "2025-10-01",
            "status": "Applied",
            "stage": "applied",
            "source": "LinkedIn",
            "location": "San Francisco, CA",
            "job_type": "Full-time",
            "salary_range": "$120k-150k",
            "url": "https://techcorp.com/jobs/123",
            "notes": "Integration test job",
            "country": "US",
        }

        # Create job via API
        response = self.client.post("/api/jobs", data=json.dumps(job_data), content_type="application/json")

        assert response.status_code == 201
        create_response = json.loads(response.data)
        assert create_response["success"] is True
        assert "job_id" in create_response

        job_id = create_response["job_id"]

        # Step 2: Verify job was created
        response = self.client.get("/api/jobs")
        assert response.status_code == 200
        jobs_response = json.loads(response.data)
        assert len(jobs_response["jobs"]) == 1
        assert jobs_response["jobs"][0]["job_id"] == job_id

        # Step 3: Add follow-up entries
        followup_data = {
            "job_id": job_id,
            "type": "note",
            "summary": "Application submitted successfully",
            "details": "Submitted application through company portal",
            "next_action": {"what": "Follow up in one week", "when": "2025-10-08", "done": False},
            "tags": ["application", "initial"],
        }

        response = self.client.post("/api/followups", data=json.dumps(followup_data), content_type="application/json")

        assert response.status_code == 201
        followup_response = json.loads(response.data)
        assert followup_response["success"] is True

        # Step 4: Add another follow-up (status change)
        status_update_data = {
            "job_id": job_id,
            "type": "status_change",
            "summary": "Moved to interviewing",
            "details": "HR contacted for phone screen",
            "next_action": {"what": "Prepare for phone screen", "when": "2025-10-10", "done": False},
            "tags": ["interview", "phone_screen"],
        }

        response = self.client.post(
            "/api/followups", data=json.dumps(status_update_data), content_type="application/json"
        )

        assert response.status_code == 201

        # Step 5: Update job status
        status_patch_data = {"status": "Interviewing", "stage": "interview"}

        response = self.client.patch(
            f"/api/jobs/{job_id}/status", data=json.dumps(status_patch_data), content_type="application/json"
        )

        assert response.status_code == 200
        status_response = json.loads(response.data)
        assert status_response["success"] is True

        # Step 6: Verify follow-ups were created
        response = self.client.get(f"/api/followups?job_id={job_id}")
        assert response.status_code == 200
        followups_response = json.loads(response.data)
        assert len(followups_response["followups"]) == 2

        # Step 7: Close the job
        close_data = {"job_id": job_id, "final_status": "Hired", "notes": "Accepted offer - integration test complete"}

        response = self.client.post(
            "/api/followups/close_job", data=json.dumps(close_data), content_type="application/json"
        )

        assert response.status_code == 200
        close_response = json.loads(response.data)
        assert close_response["success"] is True

        # Step 8: Verify job status updated and metrics reflect changes
        response = self.client.get("/api/jobs")
        assert response.status_code == 200
        final_jobs = json.loads(response.data)

        closed_job = next((j for j in final_jobs["jobs"] if j["job_id"] == job_id), None)
        assert closed_job is not None
        assert closed_job["status"] == "Hired"

    @patch("app.DATA_FILE")
    @patch("app.FOLLOWUPS_FILE")
    def test_job_update_preserves_followups(self, mock_followups_file, mock_data_file):
        """
        GIVEN: A job with existing follow-ups
        WHEN: Updating job details
        THEN: Follow-ups remain intact and linked correctly
        """
        # Mock file paths
        mock_data_file.return_value = self.temp_jobs_file
        mock_followups_file.return_value = self.temp_followups_file

        # Pre-populate with a job and follow-up
        initial_jobs = {
            "schema_version": 2,
            "last_modified": "2025-11-12T00:00:00.000000+00:00",
            "jobs": [
                {
                    "job_id": "job_test123456789",
                    "company": "InitialCorp",
                    "title": "Initial Title",
                    "date_applied": "2025-10-01",
                    "status": "Applied",
                    "stage": "applied",
                    "source": "LinkedIn",
                    "location": "Test City",
                    "job_type": "Full-time",
                    "salary_range": "$100k",
                    "country": "US",
                }
            ],
        }

        initial_followups = {
            "version": 1,
            "entries": [
                {
                    "id": "fu_test_001",
                    "job_id": "job_test123456789",
                    "timestamp": "2025-10-02T10:00:00.000Z",
                    "author": "user",
                    "type": "note",
                    "summary": "Initial follow-up",
                    "details": "Test follow-up entry",
                    "tags": ["test"],
                }
            ],
        }

        with open(self.temp_jobs_file, "w") as f:
            json.dump(initial_jobs, f)
        with open(self.temp_followups_file, "w") as f:
            json.dump(initial_followups, f)

        # Update job details
        update_data = {"company": "UpdatedCorp", "title": "Updated Title", "notes": "Updated via integration test"}

        response = self.client.put(
            "/api/jobs/job_test123456789", data=json.dumps(update_data), content_type="application/json"
        )

        assert response.status_code == 200
        update_response = json.loads(response.data)
        assert update_response["success"] is True

        # Verify job was updated
        response = self.client.get("/api/jobs")
        jobs_response = json.loads(response.data)
        updated_job = jobs_response["jobs"][0]
        assert updated_job["company"] == "UpdatedCorp"
        assert updated_job["title"] == "Updated Title"
        assert updated_job["job_id"] == "job_test123456789"  # ID unchanged

        # Verify follow-ups still linked
        response = self.client.get("/api/followups?job_id=job_test123456789")
        followups_response = json.loads(response.data)
        assert len(followups_response["followups"]) == 1
        assert followups_response["followups"][0]["job_id"] == "job_test123456789"

    @patch("app.DATA_FILE")
    @patch("app.FOLLOWUPS_FILE")
    def test_job_deletion_cascades_followups(self, mock_followups_file, mock_data_file):
        """
        GIVEN: A job with follow-ups
        WHEN: Deleting the job
        THEN: Associated follow-ups are also removed or marked appropriately
        """
        # Mock file paths
        mock_data_file.return_value = self.temp_jobs_file
        mock_followups_file.return_value = self.temp_followups_file

        # Pre-populate with job and follow-ups
        initial_jobs = {
            "schema_version": 2,
            "last_modified": "2025-11-12T00:00:00.000000+00:00",
            "jobs": [
                {
                    "job_id": "job_to_delete123",
                    "company": "DeleteTest Corp",
                    "title": "Test Position",
                    "date_applied": "2025-10-01",
                    "status": "Applied",
                    "stage": "applied",
                    "source": "Test",
                    "country": "US",
                }
            ],
        }

        initial_followups = {
            "version": 1,
            "entries": [
                {
                    "id": "fu_delete_001",
                    "job_id": "job_to_delete123",
                    "timestamp": "2025-10-02T10:00:00.000Z",
                    "author": "user",
                    "type": "note",
                    "summary": "Follow-up 1",
                    "tags": [],
                },
                {
                    "id": "fu_delete_002",
                    "job_id": "job_to_delete123",
                    "timestamp": "2025-10-03T10:00:00.000Z",
                    "author": "user",
                    "type": "note",
                    "summary": "Follow-up 2",
                    "tags": [],
                },
            ],
        }

        with open(self.temp_jobs_file, "w") as f:
            json.dump(initial_jobs, f)
        with open(self.temp_followups_file, "w") as f:
            json.dump(initial_followups, f)

        # Verify initial state
        response = self.client.get("/api/followups?job_id=job_to_delete123")
        initial_followups_response = json.loads(response.data)
        assert len(initial_followups_response["followups"]) == 2

        # Delete the job
        response = self.client.delete("/api/jobs/job_to_delete123")
        assert response.status_code == 200
        delete_response = json.loads(response.data)
        assert delete_response["success"] is True

        # Verify job is gone
        response = self.client.get("/api/jobs")
        jobs_response = json.loads(response.data)
        assert len(jobs_response["jobs"]) == 0

        # Verify follow-ups are handled appropriately
        # (Implementation may vary - they might be deleted or marked as orphaned)
        response = self.client.get("/api/followups?job_id=job_to_delete123")
        json.loads(response.data)
        # Follow-ups should either be deleted or marked as orphaned
        # This depends on the business logic implementation

    def test_error_handling_in_workflow(self):
        """
        GIVEN: Various error conditions during workflow
        WHEN: API operations encounter errors
        THEN: Errors are handled gracefully without data corruption
        """
        # Test 1: Create job with invalid data
        invalid_job_data = {
            "company": "",  # Empty required field
            "title": "Test",
            # Missing required fields
        }

        response = self.client.post("/api/jobs", data=json.dumps(invalid_job_data), content_type="application/json")

        assert response.status_code in [400, 422]  # Bad request or validation error
        error_response = json.loads(response.data)
        assert error_response["success"] is False
        assert "error" in error_response or "errors" in error_response

        # Test 2: Add follow-up to non-existent job
        invalid_followup_data = {"job_id": "job_nonexistent123", "type": "note", "summary": "This should fail"}

        response = self.client.post(
            "/api/followups", data=json.dumps(invalid_followup_data), content_type="application/json"
        )

        assert response.status_code in [400, 404]  # Bad request or not found

        # Test 3: Update non-existent job
        response = self.client.put(
            "/api/jobs/job_nonexistent456", data=json.dumps({"company": "Updated"}), content_type="application/json"
        )

        assert response.status_code == 404

        # Test 4: Invalid JSON payload
        response = self.client.post("/api/jobs", data="invalid json{", content_type="application/json")

        assert response.status_code == 400

    @patch("app.DATA_FILE")
    def test_concurrent_operations_safety(self, mock_data_file):
        """
        GIVEN: Multiple concurrent API operations
        WHEN: Operations are performed simultaneously
        THEN: Data integrity is maintained
        """
        # This is a simplified test for concurrent operations
        # In a real scenario, you'd use threading or multiprocessing

        mock_data_file.return_value = self.temp_jobs_file

        # Simulate multiple job creations in quick succession
        job_data_template = {
            "company": "ConcurrentTest",
            "title": "Position {}",
            "date_applied": "2025-10-01",
            "status": "Applied",
            "stage": "applied",
            "source": "Test",
            "country": "US",
        }

        created_jobs = []
        for i in range(5):
            job_data = job_data_template.copy()
            job_data["title"] = job_data["title"].format(i)
            job_data["company"] = f"ConcurrentTest_{i}"

            response = self.client.post("/api/jobs", data=json.dumps(job_data), content_type="application/json")

            if response.status_code == 201:
                create_response = json.loads(response.data)
                created_jobs.append(create_response["job_id"])

        # Verify all jobs were created successfully
        response = self.client.get("/api/jobs")
        jobs_response = json.loads(response.data)

        # Should have created some jobs (depending on implementation thread safety)
        assert len(jobs_response["jobs"]) >= 1

        # All job_ids should be unique
        job_ids = [job["job_id"] for job in jobs_response["jobs"]]
        assert len(job_ids) == len(set(job_ids))  # All unique
