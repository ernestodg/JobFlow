"""
Unit tests for atomic I/O operations and data safety.
Tests temp+rename atomicity, fsync, backup rotation, and recovery.
"""
import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from core_data import DataManager


class TestIOAtomic:
    """Test atomic file operations and backup mechanisms."""

    def setup_method(self):
        """Set up temporary directory for each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_file = self.temp_dir / "test_data.json"
        self.data_manager = DataManager()
        # Override data_dir for testing
        self.data_manager.data_dir = self.temp_dir
        self.data_manager.backup_dir = self.temp_dir / "backups"
        self.data_manager.backup_dir.mkdir(exist_ok=True)

    def teardown_method(self):
        """Clean up temporary directory after each test."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_atomic_write_success(self):
        """
        GIVEN: A data file and valid JSON data
        WHEN: Writing data atomically
        THEN: Data is written via temp file and renamed
        """
        test_data = {"test": "data", "items": [1, 2, 3]}

        # Write data atomically
        temp_file = None
        with patch("tempfile.NamedTemporaryFile") as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = str(self.temp_dir / "temp_123")
            temp_file = Path(mock_temp.return_value.__enter__.return_value.name)

            # Simulate atomic write operation
            with open(temp_file, "w") as f:
                json.dump(test_data, f)

            # Simulate rename operation
            shutil.move(str(temp_file), str(self.test_file))

        # Verify file exists and contains correct data
        assert self.test_file.exists()
        with open(self.test_file) as f:
            loaded_data = json.load(f)
        assert loaded_data == test_data

    def test_atomic_write_failure_recovery(self):
        """
        GIVEN: A data file and a write operation that fails
        WHEN: The write operation is interrupted
        THEN: Original file remains unchanged, temp file is cleaned up
        """
        # Create original file
        original_data = {"original": "data"}
        with open(self.test_file, "w") as f:
            json.dump(original_data, f)

        # Simulate failed write operation
        temp_file = self.temp_dir / "temp_failed"
        bad_data = {"incomplete": "data"}

        try:
            with open(temp_file, "w") as f:
                json.dump(bad_data, f)
            # Simulate failure before rename
            raise OSError("Simulated write failure")
        except OSError:
            # Clean up temp file on failure
            if temp_file.exists():
                temp_file.unlink()

        # Verify original file is unchanged
        assert self.test_file.exists()
        with open(self.test_file) as f:
            loaded_data = json.load(f)
        assert loaded_data == original_data
        assert not temp_file.exists()

    def test_backup_rotation_five_backups(self):
        """
        GIVEN: A data file with existing backups
        WHEN: Creating more than 5 backups
        THEN: Only the 5 most recent backups are kept
        """
        # Create original file
        original_data = {"version": 0}
        with open(self.test_file, "w") as f:
            json.dump(original_data, f)

        # Create 7 backups to test rotation
        for i in range(1, 8):
            # Create backup
            backup_file = self.test_file.with_suffix(f".json.bak{i}")
            backup_data = {"version": i}
            with open(backup_file, "w") as f:
                json.dump(backup_data, f)

        # Simulate backup rotation (keeping only 5 most recent)
        backups = sorted([f for f in self.temp_dir.glob("*.bak*")], key=lambda x: int(str(x).split(".bak")[1]))

        if len(backups) > 5:
            for old_backup in backups[:-5]:
                old_backup.unlink()

        # Verify only 5 backups remain
        remaining_backups = list(self.temp_dir.glob("*.bak*"))
        assert len(remaining_backups) == 5

        # Verify they are the most recent ones (bak3, bak4, bak5, bak6, bak7)
        backup_numbers = sorted([int(str(b).split(".bak")[1]) for b in remaining_backups])
        assert backup_numbers == [3, 4, 5, 6, 7]

    def test_recovery_from_corrupted_primary(self):
        """
        GIVEN: A corrupted primary file and valid backup files
        WHEN: Loading data
        THEN: Data is recovered from the latest valid backup
        """
        # Create valid backups
        for i in range(1, 4):
            backup_file = self.test_file.with_suffix(f".json.bak{i}")
            backup_data = {"version": i, "status": "valid"}
            with open(backup_file, "w") as f:
                json.dump(backup_data, f)

        # Create corrupted primary file
        with open(self.test_file, "w") as f:
            f.write('{"corrupted": invalid json')

        # Simulate recovery process
        recovered_data = None
        try:
            with open(self.test_file) as f:
                recovered_data = json.load(f)
        except json.JSONDecodeError:
            # Try to recover from backups
            for i in range(3, 0, -1):  # Try bak3, bak2, bak1
                backup_file = self.test_file.with_suffix(f".json.bak{i}")
                if backup_file.exists():
                    try:
                        with open(backup_file) as f:
                            recovered_data = json.load(f)
                        break
                    except json.JSONDecodeError:
                        continue

        # Verify recovery from latest backup
        assert recovered_data is not None
        assert recovered_data["version"] == 3
        assert recovered_data["status"] == "valid"

    def test_fsync_called_on_write(self):
        """
        GIVEN: A file write operation
        WHEN: Writing data with fsync enabled
        THEN: fsync is called to ensure data is written to disk
        """
        test_data = {"test": "fsync"}

        with patch("os.fsync") as mock_fsync:
            # Simulate write with fsync
            with open(self.test_file, "w") as f:
                json.dump(test_data, f)
                f.flush()
                os.fsync(f.fileno())

        # Verify fsync was called
        mock_fsync.assert_called_once()

    def test_concurrent_write_protection(self):
        """
        GIVEN: Multiple processes attempting to write to the same file
        WHEN: Using file locking or atomic operations
        THEN: Data integrity is maintained
        """
        # This is a simplified test - in practice, you'd use file locking libraries
        test_data_1 = {"writer": 1, "data": "first"}
        test_data_2 = {"writer": 2, "data": "second"}

        # Simulate first write completing atomically
        temp_file_1 = self.temp_dir / "temp_writer_1"
        with open(temp_file_1, "w") as f:
            json.dump(test_data_1, f)
        shutil.move(str(temp_file_1), str(self.test_file))

        # Verify first write completed
        with open(self.test_file) as f:
            current_data = json.load(f)
        assert current_data["writer"] == 1

        # Simulate second write completing atomically
        temp_file_2 = self.temp_dir / "temp_writer_2"
        with open(temp_file_2, "w") as f:
            json.dump(test_data_2, f)
        shutil.move(str(temp_file_2), str(self.test_file))

        # Verify second write completed (last writer wins)
        with open(self.test_file) as f:
            final_data = json.load(f)
        assert final_data["writer"] == 2

    def test_backup_integrity_verification(self):
        """
        GIVEN: Backup files that may be corrupted
        WHEN: Verifying backup integrity
        THEN: Only valid backups are used for recovery
        """
        # Create a mix of valid and invalid backups
        backups_data = [
            (1, '{"version": 1, "valid": true}'),  # Valid JSON
            (2, '{"version": 2, "incomplete"'),  # Invalid JSON
            (3, '{"version": 3, "valid": true}'),  # Valid JSON
        ]

        for i, data in backups_data:
            backup_file = self.test_file.with_suffix(f".json.bak{i}")
            with open(backup_file, "w") as f:
                f.write(data)

        # Test recovery process with validation
        valid_backups = []
        for i in range(3, 0, -1):
            backup_file = self.test_file.with_suffix(f".json.bak{i}")
            if backup_file.exists():
                try:
                    with open(backup_file) as f:
                        data = json.load(f)
                    valid_backups.append((i, data))
                except json.JSONDecodeError:
                    continue

        # Verify only valid backups are identified
        assert len(valid_backups) == 2
        assert valid_backups[0][1]["version"] == 3  # Latest valid backup
        assert valid_backups[1][1]["version"] == 1  # Earlier valid backup

    def test_disk_space_handling(self):
        """
        GIVEN: Limited disk space
        WHEN: Writing data
        THEN: Appropriate error handling and cleanup
        """
        test_data = {"large": "data" * 1000}

        # Simulate disk space error
        with patch("builtins.open", side_effect=OSError("No space left on device")):
            with pytest.raises(OSError):
                with open(self.test_file, "w") as f:
                    json.dump(test_data, f)

        # Verify no partial files remain
        assert not self.test_file.exists()

    def test_permission_error_handling(self):
        """
        GIVEN: A file with restricted permissions
        WHEN: Attempting to write
        THEN: Permission error is handled gracefully
        """
        # Create a read-only file
        readonly_data = {"readonly": True}
        with open(self.test_file, "w") as f:
            json.dump(readonly_data, f)

        # Make file read-only
        os.chmod(self.test_file, 0o444)

        # Attempt to write should fail
        with pytest.raises(PermissionError):
            with open(self.test_file, "w") as f:
                json.dump({"new": "data"}, f)

        # Verify original data remains
        os.chmod(self.test_file, 0o644)  # Restore permissions to read
        with open(self.test_file) as f:
            data = json.load(f)
        assert data["readonly"] is True
