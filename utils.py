"""
Utility functions for JobFlow: date parsing, duration computation, and validation.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import date
from typing import Any


def parse_iso(d: str | None) -> date | None:
    """Parse an ISO date string (YYYY-MM-DD) to a date object. Returns None for falsy input.

    Raises ValueError if the string is not a valid date.
    """
    if not d:
        return None
    return date.fromisoformat(str(d))


def compute_duration_days(start: str | None, end: str | None) -> int | None:
    """Compute the number of days between start and end (inclusive-exclusive).

    - Returns None when either date is missing.
    - Raises ValueError if end < start.
    """
    s = parse_iso(start) if start else None
    e = parse_iso(end) if end else None
    if not s or not e:
        return None
    if e < s:
        raise ValueError("date_end before date_applied")
    return (e - s).days


def format_years_days(days: int | None) -> str:
    """Format total days as '<years> years <rem> days'. Returns '—' when days is None.

    Note: 1 year = 365 days for this simple formatter.
    """
    if days is None:
        return "—"
    years, rem = divmod(int(days), 365)
    return f"{years} years {rem} days"


def validate_dates(date_applied: str | None, date_end: str | None, *, status: str | None = None) -> None:
    """Validate date rules for hired roles.

    Rules:
    - If status != 'hired': no validation needed for end; function returns.
    - If status == 'hired' and date_end present: date_end must be >= date_applied.
    - Missing date_end for hired is allowed (optional), so no error.
    """
    st = (status or "").strip().lower()
    if st != "hired":
        return
    if not date_end:
        return  # optional
    # When end provided, ensure it's >= start by computing duration
    # This will raise ValueError if end < start
    _ = compute_duration_days(date_applied, date_end)


def generate_job_id(company: str, title: str, date_applied: str, source: str) -> str:
    """Generate a stable, deterministic job_id from key fields.

    Uses SHA256 hash of normalized fields to create a short prefix.
    Format: job_<hash>_<short_suffix>
    """
    # Normalize inputs
    parts = [
        (company or "").strip().lower(),
        (title or "").strip().lower(),
        (date_applied or "").strip(),
        (source or "").strip().lower(),
    ]
    composite = "|".join(parts)

    # Generate hash
    hash_obj = hashlib.sha256(composite.encode("utf-8"))
    hash_hex = hash_obj.hexdigest()

    # Take first 12 chars of hash for readability
    short_hash = hash_hex[:12]

    return f"job_{short_hash}"


def ensure_job_ids(jobs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    """Ensure all jobs have a stable job_id. Add if missing.

    Returns:
        (updated_jobs, changed) - modified list and whether any changes were made
    """
    changed = False
    existing_ids = set()

    for job in jobs:
        # If job already has a valid job_id, register it
        if job.get("job_id"):
            existing_ids.add(job["job_id"])

    for job in jobs:
        if job.get("job_id"):
            continue  # Already has ID

        # Generate deterministic ID
        base_id = generate_job_id(
            job.get("company", ""), job.get("title", ""), job.get("date_applied", ""), job.get("source", "")
        )

        # Handle collisions by appending UUID suffix
        job_id = base_id
        if job_id in existing_ids:
            # Collision: append short UUID
            suffix = str(uuid.uuid4())[:8]
            job_id = f"{base_id}_{suffix}"

        job["job_id"] = job_id
        existing_ids.add(job_id)
        changed = True

    return jobs, changed
