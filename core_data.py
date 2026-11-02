"""
Core data management module for JobFlow.
Handles schema validation, atomic writes, backups, and data integrity.
"""
import json
import logging
import os
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Set up data directories - respect JOBFLOW_DATA_DIR for desktop app
if "JOBFLOW_DATA_DIR" in os.environ:
    DATA_DIR = Path(os.environ["JOBFLOW_DATA_DIR"])
else:
    DATA_DIR = Path(__file__).parent / "data"
BACKUP_DIR = DATA_DIR / "backups"
MAX_BACKUPS = 5


@dataclass
class ValidationError:
    field: str
    value: Any
    message: str
    severity: str = "error"  # error, warning


class DataManager:
    """Handles all data operations with atomic writes and validation."""

    def __init__(self):
        self.data_dir = DATA_DIR
        self.backup_dir = BACKUP_DIR
        self.settings = self.load_settings()

        # Ensure directories exist
        self.data_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)

    def load_settings(self) -> dict[str, Any]:
        """Load application settings."""
        settings_path = self.data_dir / "settings.json"
        try:
            if settings_path.exists():
                with open(settings_path, encoding="utf-8-sig") as f:
                    return json.load(f)
            else:
                # Return default settings if file doesn't exist
                return {
                    "sla_thresholds": {"no_followup_days": 14, "interview_no_update_days": 7},
                    "controlled_vocabularies": {
                        "status": ["Applied", "Viewed", "Under Consideration", "Interview", "Offer", "Hired", "Rejected", "Ghosted", "Withdrawn", "Declined"],
                        "stage": ["applied", "Applied", "screening", "interview", "offer", "employed", "Employed", "closed"],
                        "source": ["Email", "LazyApply", "LinkedIn", "Company", "CV", "Inspira.org", "UNOPS Careers", "WIPO Careers", "WIPO", "UNOPS", "Referral", "Other"],
                        "lead_status": ["Active", "Replied", "No Response", "Converted", "Closed"],
                        "contact_method": ["email", "linkedin", "phone", "in-person", "other"],
                        "lead_source": ["Networking", "LinkedIn", "Referral", "Company Website", "Job Board", "Event", "Other"],
                    },
                }
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            return {}

    def save_settings(self, settings: dict[str, Any]) -> bool:
        """Persist application settings and refresh in-memory cache."""
        settings_path = self.data_dir / "settings.json"

        if not isinstance(settings, dict):
            logger.error("Settings payload must be an object")
            return False

        settings_copy = dict(settings)
        settings_copy["last_modified"] = datetime.now(UTC).isoformat()

        saved = self.atomic_save(settings_path, settings_copy)
        if saved:
            self.settings = settings_copy
        return saved

    def validate_iso_date(self, date_str: str) -> bool:
        """Validate ISO date format."""
        if not date_str:
            return False
        try:
            datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return True
        except ValueError:
            return False

    def validate_enum(self, value: str, enum_name: str) -> bool:
        """Validate value against controlled vocabulary (case-insensitive)."""
        vocabularies = self.settings.get("controlled_vocabularies", {})
        allowed_values = vocabularies.get(enum_name, [])
        # Case-insensitive comparison
        return any(value.lower() == allowed.lower() for allowed in allowed_values)

    def normalize_enum(self, value: str, enum_name: str) -> str:
        """Normalize value to match controlled vocabulary format (case-insensitive lookup)."""
        vocabularies = self.settings.get("controlled_vocabularies", {})
        allowed_values = vocabularies.get(enum_name, [])
        # Find the matching value with correct capitalization
        for allowed in allowed_values:
            if value.lower() == allowed.lower():
                return allowed
        # Return original value if no match found
        return value

    def validate_job(self, job: dict[str, Any]) -> list[ValidationError]:
        """Validate a job record."""
        errors = []

        # Required fields
        required_fields = ["job_id", "company", "title", "date_applied"]
        for field in required_fields:
            if not job.get(field):
                errors.append(ValidationError(field, job.get(field), "Required field missing"))

        # Date validation
        if job.get("date_applied") and not self.validate_iso_date(job["date_applied"]):
            errors.append(ValidationError("date_applied", job["date_applied"], "Invalid ISO date format"))

        # Enum validation
        if job.get("status") and not self.validate_enum(job["status"], "status"):
            errors.append(ValidationError("status", job["status"], "Invalid status value"))

        if job.get("stage") and not self.validate_enum(job["stage"], "stage"):
            errors.append(ValidationError("stage", job["stage"], "Invalid stage value"))

        if job.get("source") and not self.validate_enum(job["source"], "source"):
            errors.append(ValidationError("source", job["source"], "Invalid source value"))

        return errors

    def validate_followup(self, followup: dict[str, Any]) -> list[ValidationError]:
        """Validate a follow-up record."""
        errors = []

        # Required fields
        required_fields = ["followup_id", "job_id", "timestamp", "type"]
        for field in required_fields:
            if not followup.get(field):
                errors.append(ValidationError(field, followup.get(field), "Required field missing"))

        # Date validation
        if followup.get("timestamp") and not self.validate_iso_date(followup["timestamp"]):
            errors.append(ValidationError("timestamp", followup["timestamp"], "Invalid ISO date format"))

        # Enum validation
        if followup.get("type") and not self.validate_enum(followup["type"], "followup_type"):
            errors.append(ValidationError("type", followup["type"], "Invalid followup type"))

        return errors

    def check_sla_violations(self, jobs: list[dict[str, Any]], followups: list[dict[str, Any]]) -> dict[str, Any]:
        """Check for SLA violations across jobs and follow-ups."""
        violations = {
            "no_followup": [],
            "interview_no_update": [],
            "screening_no_update": [],
            "offer_response": [],
            "summary": {"total_violations": 0, "jobs_at_risk": 0, "overdue_actions": 0},
        }

        thresholds = self.settings.get("sla_thresholds", {})
        no_followup_days = thresholds.get("no_followup_days", 14)
        interview_days = thresholds.get("interview_no_update_days", 7)
        screening_days = thresholds.get("screening_no_update_days", 10)
        offer_days = thresholds.get("offer_response_days", 5)

        now = datetime.now(UTC)

        # Create followup lookup by job_id
        job_followups = {}
        for fu in followups:
            job_id = fu.get("job_id")
            if job_id:
                if job_id not in job_followups:
                    job_followups[job_id] = []
                job_followups[job_id].append(fu)

        # Check each active job for violations
        active_statuses = ["applied", "viewed", "under consideration", "interview", "offer"]

        for job in jobs:
            if not job.get("job_id") or job.get("status", "").lower() not in active_statuses:
                continue

            job_id = job["job_id"]
            applied_date = job.get("date_applied")
            current_status = job.get("status", "").lower()

            if not applied_date:
                continue

            try:
                applied_dt = datetime.fromisoformat(applied_date.replace("Z", "+00:00"))
                if applied_dt.tzinfo is None:
                    applied_dt = applied_dt.replace(tzinfo=UTC)
            except ValueError:
                continue

            days_since_applied = (now - applied_dt).days
            job_fus = job_followups.get(job_id, [])

            # Find most recent follow-up
            last_followup_date = None
            if job_fus:
                latest_fu = max(job_fus, key=lambda x: x.get("timestamp", ""))
                try:
                    last_followup_date = datetime.fromisoformat(latest_fu["timestamp"].replace("Z", "+00:00"))
                    if last_followup_date.tzinfo is None:
                        last_followup_date = last_followup_date.replace(tzinfo=UTC)
                except ValueError:
                    pass

            # Check for violations based on status
            violation = None

            if current_status == "offer":
                # Offer response SLA
                days_since_last = days_since_applied
                if last_followup_date:
                    days_since_last = (now - last_followup_date).days
                if days_since_last > offer_days:
                    violation = {
                        "type": "offer_response",
                        "job_id": job_id,
                        "company": job.get("company", ""),
                        "title": job.get("title", ""),
                        "days_overdue": days_since_last - offer_days,
                        "applied_date": applied_date,
                        "last_followup": last_followup_date.isoformat() if last_followup_date else None,
                    }
                    violations["offer_response"].append(violation)

            elif current_status == "interview":
                # Interview no update SLA
                days_since_last = days_since_applied
                if last_followup_date:
                    days_since_last = (now - last_followup_date).days
                if days_since_last > interview_days:
                    violation = {
                        "type": "interview_no_update",
                        "job_id": job_id,
                        "company": job.get("company", ""),
                        "title": job.get("title", ""),
                        "days_overdue": days_since_last - interview_days,
                        "applied_date": applied_date,
                        "last_followup": last_followup_date.isoformat() if last_followup_date else None,
                    }
                    violations["interview_no_update"].append(violation)

            elif current_status in ["viewed", "under consideration"]:
                # Screening no update SLA
                days_since_last = days_since_applied
                if last_followup_date:
                    days_since_last = (now - last_followup_date).days
                if days_since_last > screening_days:
                    violation = {
                        "type": "screening_no_update",
                        "job_id": job_id,
                        "company": job.get("company", ""),
                        "title": job.get("title", ""),
                        "days_overdue": days_since_last - screening_days,
                        "applied_date": applied_date,
                        "last_followup": last_followup_date.isoformat() if last_followup_date else None,
                    }
                    violations["screening_no_update"].append(violation)

            else:
                # General no follow-up SLA for "applied" status
                if not job_fus and days_since_applied > no_followup_days:
                    violation = {
                        "type": "no_followup",
                        "job_id": job_id,
                        "company": job.get("company", ""),
                        "title": job.get("title", ""),
                        "days_overdue": days_since_applied - no_followup_days,
                        "applied_date": applied_date,
                        "last_followup": None,
                    }
                    violations["no_followup"].append(violation)

        # Count overdue next actions
        overdue_actions = 0
        for fu in followups:
            next_action = fu.get("next_action")
            if next_action and not next_action.get("done", True):
                when = next_action.get("when")
                if when:
                    try:
                        action_date = datetime.fromisoformat(when).replace(tzinfo=UTC)
                        if action_date < now:
                            overdue_actions += 1
                    except ValueError:
                        pass

        # Update summary
        total_violations = (
            len(violations["no_followup"])
            + len(violations["interview_no_update"])
            + len(violations["screening_no_update"])
            + len(violations["offer_response"])
        )

        violations["summary"] = {
            "total_violations": total_violations,
            "jobs_at_risk": len(
                set(
                    v["job_id"]
                    for category in ["no_followup", "interview_no_update", "screening_no_update", "offer_response"]
                    for v in violations[category]
                )
            ),
            "overdue_actions": overdue_actions,
        }

        return violations

    def validate_journal_entry(self, entry: dict[str, Any]) -> list[ValidationError]:
        """Validate a journal entry."""
        errors = []

        # Required fields
        required_fields = ["entry_id", "timestamp", "text"]
        for field in required_fields:
            if not entry.get(field):
                errors.append(ValidationError(field, entry.get(field), "Required field missing"))

        # Date validation
        if entry.get("timestamp") and not self.validate_iso_date(entry["timestamp"]):
            errors.append(ValidationError("timestamp", entry["timestamp"], "Invalid ISO date format"))

        return errors

    def validate_lead(self, lead: dict[str, Any]) -> list[ValidationError]:
        """Validate a lead record."""
        errors = []

        # Required fields
        required_fields = ["lead_id", "name", "company", "contact_method", "date_contacted", "status"]
        for field in required_fields:
            if not lead.get(field):
                errors.append(ValidationError(field, lead.get(field), f"Required field missing: {field}"))

        # Date validation
        if lead.get("date_contacted") and not self.validate_iso_date(lead["date_contacted"]):
            errors.append(ValidationError("date_contacted", lead["date_contacted"], "Invalid ISO date format (YYYY-MM-DD)"))

        # Enum validation
        if lead.get("status") and not self.validate_enum(lead["status"], "lead_status"):
            errors.append(ValidationError("status", lead["status"], "Invalid lead status"))

        if lead.get("contact_method") and not self.validate_enum(lead["contact_method"], "contact_method"):
            errors.append(ValidationError("contact_method", lead["contact_method"], "Invalid contact method"))

        if lead.get("source") and not self.validate_enum(lead["source"], "lead_source"):
            errors.append(ValidationError("source", lead["source"], "Invalid lead source"))

        # Next action validation if present
        if lead.get("next_action"):
            next_action = lead["next_action"]
            if next_action.get("when") and not self.validate_iso_date(next_action["when"]):
                errors.append(ValidationError("next_action.when", next_action["when"], "Invalid ISO date format"))

        return errors

    def generate_job_id(self, company: str, title: str, date_applied: str) -> str:
        """Generate deterministic job ID with short hash."""
        # Create a fingerprint from company, title, and date
        fingerprint_input = f"{company.lower().strip()}{title.lower().strip()}{date_applied[:10]}"
        # Generate a short hash for uniqueness (12 characters like the old format)
        hash_value = str(abs(hash(fingerprint_input)))
        hash_suffix = hash_value[-12:]  # Take last 12 digits
        return f"job_{hash_suffix}"

    def generate_lead_id(self, name: str, company: str, date_contacted: str) -> str:
        """Generate deterministic lead ID with short hash."""
        # Create a fingerprint from name, company, and date
        fingerprint_input = f"{name.lower().strip()}{company.lower().strip()}{date_contacted[:10]}"
        # Generate a short hash for uniqueness (12 characters)
        hash_value = str(abs(hash(fingerprint_input)))
        hash_suffix = hash_value[-12:]
        return f"lead_{hash_suffix}"

    def ensure_job_ids(self, jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Ensure all jobs have deterministic IDs and detect duplicates."""
        seen_ids = set()
        updated_jobs = []

        for job in jobs:
            if not job.get("job_id"):
                job["job_id"] = self.generate_job_id(
                    job.get("company", ""), job.get("title", ""), job.get("date_applied", "")
                )

            # Check for duplicates
            if job["job_id"] in seen_ids:
                logger.warning(f"Duplicate job_id detected: {job['job_id']}")
                # Add timestamp suffix to make unique
                timestamp_suffix = datetime.now().strftime("%H%M%S")
                job["job_id"] = f"{job['job_id']}_{timestamp_suffix}"

            seen_ids.add(job["job_id"])
            updated_jobs.append(job)

        return updated_jobs

    def rotate_backup(self, file_path: Path) -> None:
        """Create backup and rotate old backups."""
        if not file_path.exists():
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = self.backup_dir / backup_name

        # Copy current file to backup
        shutil.copy2(file_path, backup_path)

        # Rotate backups - keep only latest MAX_BACKUPS
        pattern = f"{file_path.stem}_*{file_path.suffix}"
        backups = sorted(self.backup_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)

        for old_backup in backups[MAX_BACKUPS:]:
            old_backup.unlink()
            logger.info(f"Removed old backup: {old_backup.name}")

    def atomic_save(self, file_path: Path, content: dict[str, Any]) -> bool:
        """Atomically save content to file with backup."""
        try:
            # Create backup first
            self.rotate_backup(file_path)

            # Write to temporary file
            tmp_path = file_path.with_suffix(f"{file_path.suffix}.tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())

            # Atomic rename
            tmp_path.replace(file_path)

            # Log the operation
            self.log_activity(f"SAVE {file_path.name}", content)

            logger.info(f"Atomically saved: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save {file_path}: {e}")
            if tmp_path.exists():
                tmp_path.unlink()
            return False

    def log_activity(self, operation: str, data: dict[str, Any]) -> None:
        """Log data operations to activity log."""
        log_path = self.data_dir / "activity.log"
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "operation": operation,
            "data_size": len(json.dumps(data)) if data else 0,
            "user": "local",
        }

        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")

    def load_jobs(self) -> tuple[list[dict[str, Any]], list[ValidationError]]:
        """Load and validate jobs data."""
        jobs_path = self.data_dir / "jobs.json"

        # Try to load from new schema location first
        if not jobs_path.exists():
            # Migration from old location
            old_jobs_path = Path(__file__).parent / "jobs.json"
            if old_jobs_path.exists():
                logger.info("Migrating jobs.json to data directory")
                shutil.copy2(old_jobs_path, jobs_path)

        if not jobs_path.exists():
            return [], []

        try:
            with open(jobs_path, encoding="utf-8-sig") as f:
                data = json.load(f)

            # Handle both old and new schema formats
            if isinstance(data, list):
                # Old format - wrap in new schema
                jobs_data = data
                schema_version = 1
            else:
                # New format
                jobs_data = data.get("jobs", [])
                schema_version = data.get("schema_version", 2)

            # Ensure job IDs
            jobs_data = self.ensure_job_ids(jobs_data)

            # Validate all jobs
            all_errors = []
            for job in jobs_data:
                errors = self.validate_job(job)
                all_errors.extend(errors)

            # If we migrated or updated IDs, save the new format
            if schema_version == 1 or any(not job.get("job_id") for job in jobs_data):
                self.save_jobs(jobs_data)

            return jobs_data, all_errors

        except Exception as e:
            logger.error(f"Error loading jobs: {e}")
            return [], [ValidationError("file", str(jobs_path), f"Failed to load: {e}")]

    def save_jobs(self, jobs: list[dict[str, Any]]) -> bool:
        """Save jobs data with schema v2."""
        jobs_path = self.data_dir / "jobs.json"

        # Ensure job IDs and validate
        jobs = self.ensure_job_ids(jobs)

        wrapped_data = {"schema_version": 2, "last_modified": datetime.now(UTC).isoformat(), "jobs": jobs}

        return self.atomic_save(jobs_path, wrapped_data)

    def load_followups(self) -> tuple[dict[str, Any], list[ValidationError]]:
        """Load and validate followups data."""
        followups_path = self.data_dir / "followups.json"

        # Try to load from new schema location first
        if not followups_path.exists():
            # Migration from old location
            old_followups_path = Path(__file__).parent / "followups.json"
            if old_followups_path.exists():
                logger.info("Migrating followups.json to data directory")
                shutil.copy2(old_followups_path, followups_path)

        if not followups_path.exists():
            return {"schema_version": 1, "entries": []}, []

        try:
            with open(followups_path, encoding="utf-8-sig") as f:
                data = json.load(f)

            # Ensure schema format
            if not isinstance(data, dict) or "entries" not in data:
                # Old format or corrupted - wrap safely
                data = {"schema_version": 1, "entries": data if isinstance(data, list) else []}

            # Validate entries
            all_errors = []
            for entry in data.get("entries", []):
                errors = self.validate_followup(entry)
                all_errors.extend(errors)

            return data, all_errors

        except Exception as e:
            logger.error(f"Error loading followups: {e}")
            return {"schema_version": 1, "entries": []}, [
                ValidationError("file", str(followups_path), f"Failed to load: {e}")
            ]

    def save_followups(self, followups_data: dict[str, Any]) -> bool:
        """Save followups data with schema validation."""
        followups_path = self.data_dir / "followups.json"

        # Ensure schema format
        if "schema_version" not in followups_data:
            followups_data["schema_version"] = 1

        followups_data["last_modified"] = datetime.now(UTC).isoformat()

        return self.atomic_save(followups_path, followups_data)

    def load_journal(self) -> tuple[dict[str, Any], list[ValidationError]]:
        """Load and validate journal data."""
        journal_path = self.data_dir / "journal.json"

        if not journal_path.exists():
            return {"schema_version": 1, "entries": []}, []

        try:
            with open(journal_path, encoding="utf-8-sig") as f:
                data = json.load(f)

            # Validate entries
            all_errors = []
            for entry in data.get("entries", []):
                errors = self.validate_journal_entry(entry)
                all_errors.extend(errors)

            return data, all_errors

        except Exception as e:
            logger.error(f"Error loading journal: {e}")
            return {"schema_version": 1, "entries": []}, [
                ValidationError("file", str(journal_path), f"Failed to load: {e}")
            ]

    def save_journal(self, journal_data: dict[str, Any]) -> bool:
        """Save journal data with schema validation."""
        journal_path = self.data_dir / "journal.json"

        # Ensure schema format
        if "schema_version" not in journal_data:
            journal_data["schema_version"] = 1

        journal_data["last_modified"] = datetime.now(UTC).isoformat()

        return self.atomic_save(journal_path, journal_data)

    def load_leads(self) -> tuple[dict[str, Any], list[ValidationError]]:
        """Load and validate leads data."""
        leads_path = self.data_dir / "leads.json"

        if not leads_path.exists():
            return {"schema_version": 1, "leads": []}, []

        try:
            with open(leads_path, encoding="utf-8-sig") as f:
                data = json.load(f)

            # Ensure schema format
            if not isinstance(data, dict) or "leads" not in data:
                # Old format or corrupted - wrap safely
                data = {"schema_version": 1, "leads": data if isinstance(data, list) else []}

            # Validate leads
            all_errors = []
            for lead in data.get("leads", []):
                errors = self.validate_lead(lead)
                all_errors.extend(errors)

            return data, all_errors

        except Exception as e:
            logger.error(f"Error loading leads: {e}")
            return {"schema_version": 1, "leads": []}, [
                ValidationError("file", str(leads_path), f"Failed to load: {e}")
            ]

    def save_leads(self, leads_data: dict[str, Any]) -> bool:
        """Save leads data with schema validation."""
        leads_path = self.data_dir / "leads.json"

        # Ensure schema format
        if "schema_version" not in leads_data:
            leads_data["schema_version"] = 1

        leads_data["last_modified"] = datetime.now(UTC).isoformat()

        return self.atomic_save(leads_path, leads_data)


# Global instance
data_manager = DataManager()
