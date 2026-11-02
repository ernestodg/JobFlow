import sys
from pathlib import Path

# Ensure app and utils are importable - must be at top for E402
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pytest

from app import app, is_terminal
from utils import compute_duration_days, ensure_job_ids, format_years_days, generate_job_id, validate_dates


def test_compute_duration_days():
    assert compute_duration_days("2023-01-01", "2023-01-31") == 30
    assert compute_duration_days("2023-01-01", None) is None
    assert compute_duration_days(None, "2023-01-31") is None


def test_format_years_days():
    # 400 days = 1 year (365) + 35 days
    assert format_years_days(400) == "1 years 35 days"
    assert format_years_days(None) == "—"


def test_end_cannot_be_before_start():
    with pytest.raises(ValueError):
        validate_dates("2023-02-01", "2023-01-01", status="Hired")


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_timeline_includes_duration_fields(client):
    """If there are any right-side (hired) items, they should include duration fields."""
    res = client.get("/api/timeline")
    assert res.status_code == 200
    data = res.get_json() or {}
    items = data.get("items", [])
    # Flatten right-side items
    right_items = []
    for it in items:
        right = (it or {}).get("right", {})
        for m in right.get("months") or []:
            right_items.extend(m.get("items") or [])
    if right_items:
        h = right_items[0]
        # Fields should be present per spec
        assert "date_start" in h
        assert "date_end" in h
        assert "duration_days" in h
        assert "duration_text" in h


# -----------------------------
# Job ID Tests
# -----------------------------


def test_generate_job_id_deterministic():
    """Job ID should be deterministic for same inputs."""
    id1 = generate_job_id("ACME Corp", "Engineer", "2025-01-15", "LinkedIn")
    id2 = generate_job_id("ACME Corp", "Engineer", "2025-01-15", "LinkedIn")
    assert id1 == id2
    assert id1.startswith("job_")


def test_generate_job_id_different_for_different_inputs():
    """Different jobs should get different IDs."""
    id1 = generate_job_id("ACME", "Engineer", "2025-01-15", "LinkedIn")
    id2 = generate_job_id("ACME", "Developer", "2025-01-15", "LinkedIn")
    assert id1 != id2


def test_ensure_job_ids_adds_missing():
    """ensure_job_ids should add job_id to records missing it."""
    jobs = [
        {"company": "A", "title": "X", "date_applied": "2025-01-01", "source": "S"},
        {"company": "B", "title": "Y", "date_applied": "2025-01-02", "source": "T"},
    ]
    updated, changed = ensure_job_ids(jobs)
    assert changed is True
    assert all("job_id" in j for j in updated)
    assert updated[0]["job_id"].startswith("job_")


def test_ensure_job_ids_idempotent():
    """Running ensure_job_ids twice should not change anything."""
    jobs = [{"company": "A", "title": "X", "date_applied": "2025-01-01", "source": "S"}]
    updated1, changed1 = ensure_job_ids(jobs)
    assert changed1 is True
    id_first = updated1[0]["job_id"]

    updated2, changed2 = ensure_job_ids(updated1)
    assert changed2 is False
    assert updated2[0]["job_id"] == id_first


def test_ensure_job_ids_handles_collisions():
    """Collisions should resolve with UUID suffix."""
    # Same normalized fields → collision
    jobs = [
        {"company": "ACME", "title": "Eng", "date_applied": "2025-01-01", "source": "L"},
        {"company": "acme", "title": "eng", "date_applied": "2025-01-01", "source": "l"},  # same normalized
    ]
    updated, changed = ensure_job_ids(jobs)
    assert changed is True
    # Both should have IDs, second should have suffix
    assert updated[0]["job_id"] != updated[1]["job_id"]


# -----------------------------
# Terminal Status Tests
# -----------------------------


def test_is_terminal():
    """Test terminal status detection."""
    assert is_terminal("rejected") is True
    assert is_terminal("Ghosted") is True
    assert is_terminal("HIRED") is True
    assert is_terminal("applied") is False
    assert is_terminal("interviewing") is False


# -----------------------------
# Follow-Up API Tests
# -----------------------------


def test_active_jobs_excludes_terminal(client):
    """GET /api/followup/list should exclude terminal statuses."""
    res = client.get("/api/followup/list")
    assert res.status_code == 200
    jobs = res.get_json() or []
    # All returned jobs should have non-terminal status
    for job in jobs:
        assert not is_terminal(job.get("status", ""))


def test_active_jobs_includes_derived_fields(client):
    """Active jobs should include days_since_applied, last_touch, next_action_due."""
    res = client.get("/api/followup/list")
    assert res.status_code == 200
    jobs = res.get_json() or []
    if jobs:
        first = jobs[0]
        assert "days_since_applied" in first
        assert "last_touch" in first
        assert "next_action_due" in first
