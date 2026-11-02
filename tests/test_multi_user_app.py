from __future__ import annotations

from pathlib import Path

import pytest

from app import create_app


@pytest.fixture
def client(tmp_path: Path):
    database_path = tmp_path / "jobflow-test.sqlite"
    app = create_app(
        {
            "TESTING": True,
            "ENFORCE_AUTH_IN_TESTS": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path.as_posix()}",
        }
    )
    with app.test_client() as test_client:
        yield test_client


def register(client, username: str, password: str = "password123", pin: str = "1234"):
    return client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "pin": pin, "remember": True},
    )


def login(client, username: str, password: str = "password123"):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def logout(client):
    return client.post("/api/auth/logout")


def test_auth_flow_and_protected_api(client):
    response = client.get("/api/jobs")
    assert response.status_code == 401

    register_response = register(client, "demo_user")
    assert register_response.status_code == 201
    assert register_response.get_json()["user"]["username"] == "demo_user"

    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.get_json()["user"]["username"] == "demo_user"

    logout_response = logout(client)
    assert logout_response.status_code == 200

    post_logout = client.get("/api/auth/me")
    assert post_logout.status_code == 401

    login_response = login(client, "demo_user")
    assert login_response.status_code == 200
    assert login_response.get_json()["user"]["username"] == "demo_user"


def test_user_isolation_for_jobs_leads_followups_and_journal(client):
    register(client, "user_a")
    job_response = client.post(
        "/api/jobs",
        json={
            "company": "Alpha Corp",
            "title": "Data Engineer",
            "date_applied": "2026-04-01",
            "status": "Applied",
            "source": "LinkedIn",
        },
    )
    assert job_response.status_code == 201
    job_id = job_response.get_json()["job_id"]

    followup_response = client.post(
        "/api/followups",
        json={
            "job_id": job_id,
            "type": "note",
            "summary": "Initial follow-up",
            "details": "Waiting for recruiter reply",
            "next_action": {"what": "Check status", "when": "2026-04-08", "done": False},
        },
    )
    assert followup_response.status_code == 201

    lead_response = client.post(
        "/api/leads",
        json={
            "name": "Jane Recruiter",
            "company": "Alpha Corp",
            "contact_method": "email",
            "date_contacted": "2026-04-02",
            "status": "Active",
            "linked_job_id": job_id,
        },
    )
    assert lead_response.status_code == 201

    journal_response = client.post(
        "/api/journal",
        json={
            "title": "Good lead",
            "text": "This process looks promising.",
            "linked_job_id": job_id,
        },
    )
    assert journal_response.status_code == 201

    logout(client)
    register(client, "user_b")

    jobs_response = client.get("/api/jobs")
    assert jobs_response.status_code == 200
    assert jobs_response.get_json() == []

    leads_response = client.get("/api/leads")
    assert leads_response.status_code == 200
    assert leads_response.get_json() == []

    followups_response = client.get("/api/followups")
    assert followups_response.status_code == 200
    assert followups_response.get_json()["entries"] == []

    journal_entries_response = client.get("/api/journal")
    assert journal_entries_response.status_code == 200
    assert journal_entries_response.get_json()["entries"] == []

    forbidden_job_fetch = client.patch(f"/api/jobs/{job_id}/status", json={"status": "Rejected"})
    assert forbidden_job_fetch.status_code == 404


def test_scoped_job_and_followup_crud(client):
    register(client, "solo_user")

    create_response = client.post(
        "/api/jobs",
        json={
            "company": "Beta Labs",
            "title": "Analytics Engineer",
            "date_applied": "2026-04-03",
            "status": "Applied",
            "source": "Company",
        },
    )
    assert create_response.status_code == 201
    job_id = create_response.get_json()["job_id"]

    update_response = client.patch(
        f"/api/jobs/{job_id}/status",
        json={"status": "Interview", "stage": "interview", "notes": "Phone screen scheduled"},
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["job"]["status"] == "Interview"

    followups_response = client.get(f"/api/followups?job_id={job_id}")
    assert followups_response.status_code == 200
    followups = followups_response.get_json()
    assert len(followups) == 1
    assert followups[0]["type"] == "status_change"

    active_jobs_response = client.get("/api/followup/list")
    assert active_jobs_response.status_code == 200
    active_jobs = active_jobs_response.get_json()
    assert len(active_jobs) == 1
    assert active_jobs[0]["job_id"] == job_id
    assert "days_since_applied" in active_jobs[0]
    assert "last_touch" in active_jobs[0]

    close_response = client.post(
        "/api/followups/close_job",
        json={"job_id": job_id, "status": "Rejected", "stage": "closed", "notes": "No offer"},
    )
    assert close_response.status_code == 200
    assert close_response.get_json()["job"]["status"] == "Rejected"

    after_close_response = client.get("/api/followup/list")
    assert after_close_response.status_code == 200
    assert after_close_response.get_json() == []


def test_timeline_groups_confirmed_hires_by_start_date(client):
    register(client, "timeline_user")

    hired_legacy = client.post(
        "/api/jobs",
        json={
            "company": "Thunderbird Resorts",
            "title": "Development Manager",
            "date_applied": "2008-01-01",
            "status": "Hired",
        },
    )
    assert hired_legacy.status_code == 201

    accepted_recent = client.post(
        "/api/jobs",
        json={
            "company": "Modern Systems",
            "title": "Engineering Manager",
            "date_applied": "2024-11-15",
            "status": "Accepted",
        },
    )
    assert accepted_recent.status_code == 201

    timeline_response = client.get("/api/timeline")
    assert timeline_response.status_code == 200
    payload = timeline_response.get_json() or {}
    items = payload.get("items") or []

    right_side_years = {
        int(entry.get("year")): entry.get("right", {}).get("months") or []
        for entry in items
    }
    assert 2008 in right_side_years
    assert 2024 in right_side_years

    months_2008 = [m.get("month") for m in right_side_years[2008]]
    months_2024 = [m.get("month") for m in right_side_years[2024]]
    assert "January" in months_2008
    assert "November" in months_2024