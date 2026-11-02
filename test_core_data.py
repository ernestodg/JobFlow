"""
Test suite for core data management functionality.
Tests schema validation, atomic writes, backups, and data integrity.
"""
import json
import tempfile
from pathlib import Path

import pytest

from core_data import DataManager


@pytest.fixture
def temp_data_manager():
    """Create a DataManager with a temporary data directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create a test DataManager
        dm = DataManager()
        dm.data_dir = temp_path / "data"
        dm.backup_dir = dm.data_dir / "backups"
        dm.data_dir.mkdir(exist_ok=True)
        dm.backup_dir.mkdir(exist_ok=True)

        # Create test settings
        settings = {
            "controlled_vocabularies": {
                "status": ["Applied", "Rejected", "Hired"],
                "stage": ["applied", "interview", "closed"],
                "source": ["LinkedIn", "Company"],
                "followup_type": ["note", "email", "call"],
            }
        }
        dm.settings = settings

        yield dm


class TestValidation:
    """Test data validation functions."""

    def test_validate_iso_date_valid(self, temp_data_manager):
        """Test valid ISO date validation."""
        dm = temp_data_manager
        assert dm.validate_iso_date("2025-11-10T12:00:00Z") is True
        assert dm.validate_iso_date("2025-11-10T12:00:00") is True
        assert dm.validate_iso_date("2025-11-10") is True

    def test_validate_iso_date_invalid(self, temp_data_manager):
        """Test invalid ISO date validation."""
        dm = temp_data_manager
        assert dm.validate_iso_date("invalid-date") is False
        assert dm.validate_iso_date("2025-13-40") is False
        assert dm.validate_iso_date("") is False
        assert dm.validate_iso_date(None) is False

    def test_validate_enum_valid(self, temp_data_manager):
        """Test valid enum validation."""
        dm = temp_data_manager
        assert dm.validate_enum("Applied", "status") is True
        assert dm.validate_enum("LinkedIn", "source") is True

    def test_validate_enum_invalid(self, temp_data_manager):
        """Test invalid enum validation."""
        dm = temp_data_manager
        assert dm.validate_enum("InvalidStatus", "status") is False
        assert dm.validate_enum("Applied", "nonexistent_enum") is False

    def test_validate_job_valid(self, temp_data_manager):
        """Test validation of valid job."""
        dm = temp_data_manager
        job = {
            "job_id": "job_test_123",
            "company": "Test Company",
            "title": "Test Role",
            "date_applied": "2025-11-10T12:00:00Z",
            "status": "Applied",
            "stage": "applied",
            "source": "LinkedIn",
        }
        errors = dm.validate_job(job)
        assert len(errors) == 0

    def test_validate_job_missing_fields(self, temp_data_manager):
        """Test validation of job with missing required fields."""
        dm = temp_data_manager
        job = {
            "company": "Test Company"
            # Missing job_id, title, date_applied
        }
        errors = dm.validate_job(job)
        assert len(errors) == 3  # job_id, title, date_applied
        error_fields = [e.field for e in errors]
        assert "job_id" in error_fields
        assert "title" in error_fields
        assert "date_applied" in error_fields

    def test_validate_job_bad_enums(self, temp_data_manager):
        """Test validation of job with bad enum values."""
        dm = temp_data_manager
        job = {
            "job_id": "job_test_123",
            "company": "Test Company",
            "title": "Test Role",
            "date_applied": "2025-11-10T12:00:00Z",
            "status": "InvalidStatus",
            "stage": "invalid_stage",
            "source": "InvalidSource",
        }
        errors = dm.validate_job(job)
        assert len(errors) == 3  # status, stage, source
        error_fields = [e.field for e in errors]
        assert "status" in error_fields
        assert "stage" in error_fields
        assert "source" in error_fields


class TestJobIdGeneration:
    """Test job ID generation and duplicate detection."""

    def test_generate_job_id_deterministic(self, temp_data_manager):
        """Test that job ID generation is deterministic."""
        dm = temp_data_manager
        company = "Test Company"
        title = "Software Engineer"
        date = "2025-11-10"

        id1 = dm.generate_job_id(company, title, date)
        id2 = dm.generate_job_id(company, title, date)

        assert id1 == id2
        assert id1.startswith("job_")

    def test_ensure_job_ids_adds_missing(self, temp_data_manager):
        """Test that ensure_job_ids adds missing IDs."""
        dm = temp_data_manager
        jobs = [{"company": "Test Company", "title": "Engineer", "date_applied": "2025-11-10"}]

        updated_jobs = dm.ensure_job_ids(jobs)

        assert len(updated_jobs) == 1
        assert "job_id" in updated_jobs[0]
        assert updated_jobs[0]["job_id"].startswith("job_")

    def test_ensure_job_ids_handles_duplicates(self, temp_data_manager):
        """Test that ensure_job_ids handles duplicate IDs."""
        dm = temp_data_manager
        jobs = [
            {"job_id": "duplicate_id", "company": "Test Company 1", "title": "Engineer", "date_applied": "2025-11-10"},
            {"job_id": "duplicate_id", "company": "Test Company 2", "title": "Engineer", "date_applied": "2025-11-10"},
        ]

        updated_jobs = dm.ensure_job_ids(jobs)

        assert len(updated_jobs) == 2
        assert updated_jobs[0]["job_id"] != updated_jobs[1]["job_id"]
        # First one keeps original ID, second gets modified
        assert updated_jobs[0]["job_id"] == "duplicate_id"
        assert updated_jobs[1]["job_id"].startswith("duplicate_id_")


class TestBackupRotation:
    """Test backup creation and rotation."""

    def test_rotate_backup_creates_backup(self, temp_data_manager):
        """Test that rotate_backup creates a backup file."""
        dm = temp_data_manager

        # Create a test file
        test_file = dm.data_dir / "test.json"
        test_data = {"test": "data"}
        with open(test_file, "w") as f:
            json.dump(test_data, f)

        # Create backup
        dm.rotate_backup(test_file)

        # Check backup was created
        backups = list(dm.backup_dir.glob("test_*.json"))
        assert len(backups) == 1

        # Verify backup content
        with open(backups[0]) as f:
            backup_data = json.load(f)
        assert backup_data == test_data

    def test_rotate_backup_keeps_max_backups(self, temp_data_manager):
        """Test that backup rotation keeps only MAX_BACKUPS files."""
        dm = temp_data_manager

        # Create a test file
        test_file = dm.data_dir / "test.json"
        test_data = {"test": "data"}
        with open(test_file, "w") as f:
            json.dump(test_data, f)

        # Create more backups than MAX_BACKUPS
        for i in range(7):  # More than MAX_BACKUPS (5)
            dm.rotate_backup(test_file)
            # Modify file content to simulate changes
            test_data["version"] = i
            with open(test_file, "w") as f:
                json.dump(test_data, f)

        # Check that only MAX_BACKUPS are kept
        backups = list(dm.backup_dir.glob("test_*.json"))
        assert len(backups) <= dm.MAX_BACKUPS


class TestAtomicSave:
    """Test atomic save operations."""

    def test_atomic_save_success(self, temp_data_manager):
        """Test successful atomic save."""
        dm = temp_data_manager

        test_file = dm.data_dir / "test.json"
        test_data = {"test": "data", "timestamp": "2025-11-10T12:00:00Z"}

        result = dm.atomic_save(test_file, test_data)

        assert result is True
        assert test_file.exists()

        # Verify content
        with open(test_file) as f:
            saved_data = json.load(f)
        assert saved_data == test_data

    def test_atomic_save_creates_backup(self, temp_data_manager):
        """Test that atomic save creates backup of existing file."""
        dm = temp_data_manager

        test_file = dm.data_dir / "test.json"

        # Create initial file
        original_data = {"version": 1}
        with open(test_file, "w") as f:
            json.dump(original_data, f)

        # Update with atomic save
        new_data = {"version": 2}
        dm.atomic_save(test_file, new_data)

        # Check backup was created
        backups = list(dm.backup_dir.glob("test_*.json"))
        assert len(backups) == 1

        # Verify backup contains original data
        with open(backups[0]) as f:
            backup_data = json.load(f)
        assert backup_data == original_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
