from __future__ import annotations

import argparse
import json
from pathlib import Path

from jobflow_app import _hash_secret, _parse_iso_date, _parse_iso_datetime, create_app, normalize_source, normalize_stage, normalize_status
from jobflow_models import FollowUp, Job, JournalEntry, Lead, User, db


def _load_json(path: Path, default: dict | list) -> dict | list:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _iter_jobs(payload: dict | list) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [item for item in payload.get("jobs", []) if isinstance(item, dict)]
    return []


def _iter_followups(payload: dict | list) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [item for item in payload.get("entries", []) if isinstance(item, dict)]
    return []


def _iter_leads(payload: dict | list) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [item for item in payload.get("leads", []) if isinstance(item, dict)]
    return []


def _iter_journal_entries(payload: dict | list) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [item for item in payload.get("entries", []) if isinstance(item, dict)]
    return []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate JobFlow JSON data into the database for a specific user.")
    parser.add_argument("--username", required=True, help="Target username for imported data")
    parser.add_argument("--password", required=True, help="Password for the target user")
    parser.add_argument("--pin", default="", help="Optional PIN for quick login")
    parser.add_argument("--data-dir", default="data", help="Directory containing jobs.json, followups.json, leads.json, and journal.json")
    parser.add_argument("--database-url", default="", help="Optional SQLAlchemy database URL override")
    parser.add_argument("--replace-existing", action="store_true", help="Delete the user's existing DB data before import")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_dir = Path(args.data_dir).resolve()

    app = create_app(
        {
            "SQLALCHEMY_DATABASE_URI": args.database_url or None,
            "TESTING": False,
        }
    )

    with app.app_context():
        user = User.query.filter_by(username=args.username).first()
        if not user:
            user = User(
                username=args.username,
                password_hash=_hash_secret(args.password),
                pin_hash=_hash_secret(args.pin) if args.pin else None,
            )
            db.session.add(user)
            db.session.commit()
        else:
            user.password_hash = _hash_secret(args.password)
            user.pin_hash = _hash_secret(args.pin) if args.pin else user.pin_hash
            db.session.commit()

        if args.replace_existing:
            FollowUp.query.filter_by(user_id=user.id).delete()
            JournalEntry.query.filter_by(user_id=user.id).delete()
            Lead.query.filter_by(user_id=user.id).delete()
            Job.query.filter_by(user_id=user.id).delete()
            db.session.commit()

        jobs_payload = _load_json(data_dir / "jobs.json", {"jobs": []})
        followups_payload = _load_json(data_dir / "followups.json", {"entries": []})
        leads_payload = _load_json(data_dir / "leads.json", {"leads": []})
        journal_payload = _load_json(data_dir / "journal.json", {"entries": []})

        legacy_job_map: dict[str, str] = {}
        created_jobs = 0
        created_followups = 0
        created_leads = 0
        created_journal = 0

        existing_jobs = {
            job.legacy_job_id: job
            for job in Job.query.filter_by(user_id=user.id).all()
            if job.legacy_job_id
        }

        for payload in _iter_jobs(jobs_payload):
            legacy_job_id = str(payload.get("job_id") or "").strip() or None
            job = existing_jobs.get(legacy_job_id) if legacy_job_id else None
            applied_date = _parse_iso_date(payload.get("date_applied"))
            if not applied_date:
                continue
            if not job:
                job = Job(user_id=user.id, legacy_job_id=legacy_job_id)
                db.session.add(job)
                created_jobs += 1

            job.company = str(payload.get("company") or "").strip()
            job.title = str(payload.get("title") or "").strip()
            job.date_applied = applied_date
            job.date_end = _parse_iso_date(payload.get("date_end"))
            job.duration_days = payload.get("duration_days")
            job.status = normalize_status(payload.get("status"))
            job.stage = normalize_stage(payload.get("stage"), payload.get("status"))
            job.source = normalize_source(payload.get("source"))
            job.location = str(payload.get("location") or "").strip() or None
            job.job_type = str(payload.get("job_type") or "").strip() or None
            job.salary_range = str(payload.get("salary_range") or "").strip() or None
            job.url = str(payload.get("url") or "").strip() or None
            job.notes = str(payload.get("notes") or "").strip() or None
            job.country = str(payload.get("country") or "").strip() or None

            db.session.flush()
            if legacy_job_id:
                legacy_job_map[legacy_job_id] = job.id

        existing_followups = {
            entry.legacy_followup_id: entry
            for entry in FollowUp.query.filter_by(user_id=user.id).all()
            if entry.legacy_followup_id
        }
        for payload in _iter_followups(followups_payload):
            legacy_id = str(payload.get("id") or payload.get("followup_id") or "").strip() or None
            job_id = legacy_job_map.get(str(payload.get("job_id") or "").strip())
            if not job_id:
                continue
            entry = existing_followups.get(legacy_id) if legacy_id else None
            next_action = payload.get("next_action") if isinstance(payload.get("next_action"), dict) else None
            if not entry:
                entry = FollowUp(user_id=user.id, job_id=job_id, legacy_followup_id=legacy_id)
                db.session.add(entry)
                created_followups += 1
            entry.job_id = job_id
            entry.timestamp = _parse_iso_datetime(payload.get("timestamp")) or entry.timestamp
            entry.type = str(payload.get("type") or "note").strip() or "note"
            entry.summary = str(payload.get("summary") or "Imported follow-up").strip()
            entry.notes = str(payload.get("details") or payload.get("notes") or "").strip() or None
            entry.author = str(payload.get("author") or "user").strip() or "user"
            entry.next_action_what = str(next_action.get("what") or "").strip() if next_action else None
            entry.next_action_when = _parse_iso_date(next_action.get("when")) if next_action else None
            entry.next_action_done = bool(next_action.get("done")) if next_action else False
            entry.tags = payload.get("tags") if isinstance(payload.get("tags"), list) else []

        existing_leads = {
            lead.legacy_lead_id: lead
            for lead in Lead.query.filter_by(user_id=user.id).all()
            if lead.legacy_lead_id
        }
        for payload in _iter_leads(leads_payload):
            legacy_id = str(payload.get("lead_id") or "").strip() or None
            contacted = _parse_iso_date(payload.get("date_contacted"))
            if not contacted:
                continue
            lead = existing_leads.get(legacy_id) if legacy_id else None
            next_action = payload.get("next_action") if isinstance(payload.get("next_action"), dict) else None
            if not lead:
                lead = Lead(user_id=user.id, legacy_lead_id=legacy_id)
                db.session.add(lead)
                created_leads += 1
            lead.name = str(payload.get("name") or "").strip()
            lead.company = str(payload.get("company") or "").strip()
            lead.role = str(payload.get("role") or "").strip() or None
            lead.email = str(payload.get("email") or "").strip() or None
            lead.linkedin = str(payload.get("linkedin") or "").strip() or None
            lead.contact_method = str(payload.get("contact_method") or "other").strip()
            lead.date_contacted = contacted
            lead.status = str(payload.get("status") or "Active").strip()
            lead.source = str(payload.get("source") or "").strip() or None
            lead.topic = str(payload.get("topic") or "").strip() or None
            lead.notes = str(payload.get("notes") or "").strip() or None
            lead.next_action_what = str(next_action.get("what") or "").strip() if next_action else None
            lead.next_action_when = _parse_iso_date(next_action.get("when")) if next_action else None
            lead.next_action_done = bool(next_action.get("done")) if next_action else False
            linked_legacy_job_id = str(payload.get("linked_job_id") or "").strip()
            lead.linked_job_id = legacy_job_map.get(linked_legacy_job_id)

        existing_journal = {
            entry.legacy_entry_id: entry
            for entry in JournalEntry.query.filter_by(user_id=user.id).all()
            if entry.legacy_entry_id
        }
        for payload in _iter_journal_entries(journal_payload):
            legacy_id = str(payload.get("entry_id") or payload.get("id") or "").strip() or None
            text = str(payload.get("text") or "").strip()
            if not text:
                continue
            entry = existing_journal.get(legacy_id) if legacy_id else None
            if not entry:
                entry = JournalEntry(user_id=user.id, legacy_entry_id=legacy_id)
                db.session.add(entry)
                created_journal += 1
            entry.timestamp = _parse_iso_datetime(payload.get("timestamp")) or entry.timestamp
            entry.title = str(payload.get("title") or "").strip() or None
            entry.text = text
            entry.sentiment_score = payload.get("sentiment_score")
            entry.sentiment_label = str(payload.get("sentiment_label") or "").strip() or None
            linked_legacy_job_id = str(payload.get("linked_job_id") or "").strip()
            entry.linked_job_id = legacy_job_map.get(linked_legacy_job_id)

        db.session.commit()

        print(f"User: {user.username}")
        print(f"Jobs imported: {created_jobs}")
        print(f"Follow-ups imported: {created_followups}")
        print(f"Leads imported: {created_leads}")
        print(f"Journal entries imported: {created_journal}")


if __name__ == "__main__":
    main()