from __future__ import annotations

import argparse
import copy
import json
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CadenceConfig:
    applied_email_days: int = 5
    applied_lazyapply_days: int = 7
    second_reminder_offset_days: int = 14


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _parse_iso_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)


def _new_followup_id(ts: str) -> str:
    compact_ts = ts.replace(":", "").replace("-", "").replace(".", "")
    return f"fu_{compact_ts}_{random.randint(1000, 9999)}"


def _entry_has_tags(entry: dict[str, Any], required: set[str]) -> bool:
    tags = set(entry.get("tags", []))
    return required.issubset(tags)


def update_followup_cadence(
    jobs_payload: dict[str, Any],
    followups_payload: dict[str, Any],
    config: CadenceConfig,
) -> tuple[int, int]:
    jobs = jobs_payload.get("jobs", [])
    entries = followups_payload.get("entries", [])

    job_map: dict[str, dict[str, Any]] = {
        str(job.get("job_id")): job for job in jobs if job.get("job_id")
    }

    existing_second_reminder_job_ids = {
        str(entry.get("job_id"))
        for entry in entries
        if _entry_has_tags(entry, {"auto-generated-second-reminder"})
    }

    updated_first_reminders = 0
    added_second_reminders = 0

    for entry in entries:
        if not _entry_has_tags(entry, {"auto-generated", "status:Applied"}):
            continue
        if entry.get("type") != "note":
            continue

        next_action = entry.get("next_action")
        if not isinstance(next_action, dict):
            continue

        job_id = str(entry.get("job_id", ""))
        job = job_map.get(job_id)
        if not job:
            continue

        date_applied = str(job.get("date_applied", ""))
        try:
            applied_dt = _parse_iso_date(date_applied)
        except ValueError:
            continue

        source = str(job.get("source", ""))
        first_days = config.applied_email_days if source == "Email" else config.applied_lazyapply_days
        first_due = (applied_dt + timedelta(days=first_days)).strftime("%Y-%m-%d")

        if str(next_action.get("when", "")) != first_due:
            next_action["when"] = first_due
            updated_first_reminders += 1

        if job_id in existing_second_reminder_job_ids:
            continue

        second_due_dt = datetime.strptime(first_due, "%Y-%m-%d") + timedelta(days=config.second_reminder_offset_days)
        second_due = second_due_dt.strftime("%Y-%m-%d")

        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        second_entry = {
            "id": _new_followup_id(ts),
            "job_id": job_id,
            "timestamp": ts,
            "author": "user",
            "type": "note",
            "summary": "Second follow-up reminder",
            "details": "Auto-generated second reminder based on follow-up cadence rules.",
            "next_action": {
                "what": "If no response, send a second follow-up message and decide whether to archive as stale.",
                "when": second_due,
                "done": False,
            },
            "tags": [
                "auto-generated",
                "auto-generated-second-reminder",
                "cadence:+14d",
                "status:Applied",
                f"source:{source}",
            ],
        }

        entries.append(second_entry)
        existing_second_reminder_job_ids.add(job_id)
        added_second_reminders += 1

    return updated_first_reminders, added_second_reminders


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update follow-up cadence for applied jobs and optionally add second reminders."
    )
    parser.add_argument(
        "--jobs",
        default="data/jobs.json",
        help="Path to jobs JSON file (default: data/jobs.json)",
    )
    parser.add_argument(
        "--followups",
        default="data/followups.json",
        help="Path to followups JSON file (default: data/followups.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing files",
    )
    parser.add_argument(
        "--email-days",
        type=int,
        default=5,
        help="Days after apply date for first reminder when source is Email (default: 5)",
    )
    parser.add_argument(
        "--lazyapply-days",
        type=int,
        default=7,
        help="Days after apply date for first reminder when source is LazyApply/other (default: 7)",
    )
    parser.add_argument(
        "--second-offset-days",
        type=int,
        default=14,
        help="Days after first reminder for second reminder (default: 14)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    jobs_path = Path(args.jobs)
    followups_path = Path(args.followups)

    jobs_payload = _load_json(jobs_path)
    followups_payload = _load_json(followups_path)

    config = CadenceConfig(
        applied_email_days=args.email_days,
        applied_lazyapply_days=args.lazyapply_days,
        second_reminder_offset_days=args.second_offset_days,
    )

    updated_count, added_count = update_followup_cadence(
        jobs_payload=jobs_payload,
        followups_payload=followups_payload,
        config=config,
    )

    if args.dry_run:
        print(f"[dry-run] First reminders updated: {updated_count}")
        print(f"[dry-run] Second reminders added: {added_count}")
        return

    backup_path = followups_path.with_suffix(followups_path.suffix + ".bak_cadence")
    _save_json(backup_path, _load_json(followups_path))
    _save_json(followups_path, followups_payload)

    print(f"First reminders updated: {updated_count}")
    print(f"Second reminders added: {added_count}")
    print(f"Backup written: {backup_path}")


if __name__ == "__main__":
    main()
