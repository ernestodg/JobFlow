from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any

import bcrypt
from flask import Flask, current_app, g, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import create_engine, text

from core_data import data_manager as legacy_data_manager
from jobflow_models import FollowUp, Job, JournalEntry, Lead, User, db
from utils import compute_duration_days, format_years_days


logger = logging.getLogger(__name__)

DEFAULT_POSTGRES_URI = None
TERMINAL_STATUSES = {"Rejected", "Ghosted", "Withdrawn", "Hired", "Declined", "Offer"}
AI_PROMPT_DEFAULT = (
    "You are a job application assistant. Analyze email text and output JSON only. "
    "Detect explicit hiring pipeline updates for jobs in the message. "
    "Use this schema: "
    '{"updates":[{"job_id":"optional","company":"string","title":"string","status":"Applied|Interview|Offer|Rejected|Ghosted|Withdrawn|Hired|Under Consideration|Viewed|Declined",'
    '"stage":"optional lowercase stage","notes_append":"short reason from email"}]}. '
    "If there is no update, return {\"updates\":[]}. Do not include markdown fences."
)
DEFAULT_SETTINGS = {
    "version": "2.0.0",
    "timezone": "UTC",
    "sla_thresholds": {
        "no_followup_days": 14,
        "interview_no_update_days": 7,
        "screening_no_update_days": 10,
        "offer_response_days": 5,
    },
    "controlled_vocabularies": {
        "status": [
            "Applied",
            "Viewed",
            "Under Consideration",
            "Interview",
            "Offer",
            "Hired",
            "Rejected",
            "Ghosted",
            "Withdrawn",
            "Declined",
        ],
        "stage": ["applied", "screening", "interview", "offer", "employed", "closed"],
        "source": [
            "Email",
            "LazyApply",
            "LinkedIn",
            "Company",
            "CV",
            "Inspira.org",
            "UNOPS Careers",
            "WIPO Careers",
            "WIPO",
            "UNOPS",
            "Referral",
            "Other",
        ],
        "followup_type": ["note", "call", "email", "interview", "status_change", "reminder"],
        "lead_status": ["Active", "Replied", "No Response", "Converted", "Closed"],
        "contact_method": ["email", "linkedin", "phone", "in-person", "other"],
        "lead_source": ["Networking", "LinkedIn", "Referral", "Company Website", "Job Board", "Event", "Other"],
    },
    "ai": {
        "ollama_endpoint": "http://localhost:11434",
        "ollama_model": "llama3.1:latest",
        "timeout_seconds": 45,
        "prompts": {"job_status_update": AI_PROMPT_DEFAULT},
    },
}


def _merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def build_settings(user: User | None = None) -> dict[str, Any]:
    override = user.settings_json if user and isinstance(user.settings_json, dict) else {}
    return _merge_dict(DEFAULT_SETTINGS, override)


def extract_year(date_string: str | None) -> int | None:
    if not date_string:
        return None
    try:
        return datetime.fromisoformat(str(date_string).replace("Z", "+00:00")).year
    except ValueError:
        try:
            return datetime.strptime(str(date_string)[:10], "%Y-%m-%d").year
        except ValueError:
            return None


def normalize_status(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "Applied"

    mapping = {
        "applied": "Applied",
        "viewed": "Viewed",
        "under consideration": "Under Consideration",
        "interview": "Interview",
        "interviewing": "Interview",
        "offer": "Offer",
        "hired": "Hired",
        "rejected": "Rejected",
        "ghosted": "Ghosted",
        "withdrawn": "Withdrawn",
        "declined": "Declined",
    }
    return mapping.get(raw.lower(), raw.title())


def normalize_stage(value: str | None, status: str | None = None) -> str:
    raw = str(value or "").strip().lower()
    if raw:
        return raw
    normalized_status = normalize_status(status)
    if normalized_status == "Interview":
        return "interview"
    if normalized_status == "Offer":
        return "offer"
    if normalized_status == "Hired":
        return "employed"
    if normalized_status in {"Rejected", "Ghosted", "Withdrawn", "Declined"}:
        return "closed"
    return "applied"


def normalize_source(value: str | None) -> str:
    raw = str(value or "").strip()
    return raw or "Other"


def is_terminal(status: str | None) -> bool:
    return normalize_status(status) in TERMINAL_STATUSES


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
        except ValueError:
            return None


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def _resolve_database_uri(configured_uri: str | None) -> str:
    if configured_uri:
        return configured_uri

    raise RuntimeError(
        "Database not configured. Set JOBFLOW_DATABASE_URL or DATABASE_URL."
    )

def _hash_secret(secret: str) -> str:
    return bcrypt.hashpw(secret.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _check_secret(secret: str, secret_hash: str | None) -> bool:
    if not secret or not secret_hash:
        return False
    return bcrypt.checkpw(secret.encode("utf-8"), secret_hash.encode("utf-8"))


def _default_data_paths(root: Path) -> tuple[Path, Path, Path, Path]:
    data_dir = root / "data"
    return (
        data_dir / "jobs.json",
        data_dir / "followups.json",
        data_dir / "journal.json",
        data_dir / "leads.json",
    )


def _serialize_job(job: Job) -> dict[str, Any]:
    payload = job.to_dict(include_counts=True)
    applied = _parse_iso_date(payload.get("date_applied"))
    if applied:
        payload["days_since_applied"] = (datetime.now(UTC).date() - applied).days
    else:
        payload["days_since_applied"] = None
    if payload.get("duration_days") is None and payload.get("date_applied") and payload.get("date_end"):
        payload["duration_days"] = compute_duration_days(payload.get("date_applied"), payload.get("date_end"))
    if payload.get("duration_days") is not None:
        payload["duration_text"] = format_years_days(payload["duration_days"])
    return payload


def _job_query_for_user(user: User):
    return Job.query.filter_by(user_id=user.id)


def _followup_query_for_user(user: User):
    return FollowUp.query.filter_by(user_id=user.id)


def _lead_query_for_user(user: User):
    return Lead.query.filter_by(user_id=user.id)


def _journal_query_for_user(user: User):
    return JournalEntry.query.filter_by(user_id=user.id)


def _ensure_test_user() -> User:
    user = User.query.filter_by(username="test-user").first()
    if user:
        return user
    user = User(username="test-user", password_hash=_hash_secret("test-password"))
    db.session.add(user)
    db.session.commit()
    return user


def get_current_user() -> User | None:
    cached = getattr(g, "_current_user", None)
    if cached is not None:
        return cached

    if current_app.config.get("TESTING") and not current_app.config.get("ENFORCE_AUTH_IN_TESTS", False):
        user = _ensure_test_user()
        g._current_user = user
        return user

    user_id = session.get("user_id")
    if not user_id:
        g._current_user = None
        return None

    user = db.session.get(User, user_id)
    g._current_user = user
    return user


def api_login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Authentication required"}), 401
        return view(*args, **kwargs)

    return wrapped


def page_login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if not user:
            return redirect(url_for("login_page", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def _job_to_sla_payload(job: Job) -> dict[str, Any]:
    payload = _serialize_job(job)
    payload["job_id"] = job.id
    return payload


def _followup_to_sla_payload(entry: FollowUp) -> dict[str, Any]:
    return entry.to_dict()


def _get_sla_violations(user: User) -> dict[str, Any]:
    jobs = [_job_to_sla_payload(job) for job in _job_query_for_user(user).all()]
    followups = [_followup_to_sla_payload(entry) for entry in _followup_query_for_user(user).all()]
    return legacy_data_manager.check_sla_violations(jobs, followups)


def _enrich_active_job(job: Job) -> dict[str, Any]:
    payload = _serialize_job(job)
    ordered_followups = job.followups.order_by(FollowUp.timestamp.desc()).all()
    payload["last_touch"] = payload.get("date_applied")
    payload["next_action_due"] = None
    payload["next_action_text"] = None
    if ordered_followups:
        latest = ordered_followups[0].to_dict()
        payload["last_touch"] = (latest.get("timestamp") or "")[:10] or payload.get("date_applied")
        pending = next(
            (item for item in ordered_followups if item.next_action_when and not item.next_action_done),
            None,
        )
        if pending:
            payload["next_action_due"] = pending.next_action_when.isoformat()
            payload["next_action_text"] = pending.next_action_what
    return payload


def _timeline_group(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    months: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        if item.get("displayDate"):
            month_name = datetime.strptime(item["displayDate"], "%Y-%m-%d").strftime("%B")
        else:
            month_name = "Unknown"
        months[month_name].append(item)
    ordered: list[dict[str, Any]] = []
    for month in sorted(months.keys(), key=lambda value: datetime.strptime(value, "%B").month if value != "Unknown" else 13):
        ordered.append({"month": month, "items": months[month]})
    return ordered


def _build_timeline(jobs: list[Job]) -> list[dict[str, Any]]:
    by_year: dict[int, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: {"left": [], "right": []})
    for job in jobs:
        applied = job.date_applied.isoformat()
        applied_year = job.date_applied.year
        normalized_status = normalize_status(job.status)
        base_item = {
            "job_id": job.id,
            "company": job.company,
            "title": job.title,
            "status": normalized_status,
            "country": job.country or "",
            "displayDate": applied,
        }
        by_year[applied_year]["left"].append(base_item)

        if normalized_status in {"Hired", "Accepted"}:
            # Group confirmed hires by start month/year so historical roles stay in their original period.
            start_date = applied
            end_date = job.date_end.isoformat() if job.date_end else None
            duration = job.duration_days
            if duration is None and end_date:
                duration = compute_duration_days(start_date, end_date)
            by_year[extract_year(start_date) or applied_year]["right"].append(
                {
                    **base_item,
                    "displayDate": start_date,
                    "date_start": start_date,
                    "date_end": end_date,
                    "duration_days": duration,
                    "duration_text": format_years_days(duration),
                }
            )

    items: list[dict[str, Any]] = []
    for year in sorted(by_year.keys(), reverse=True):
        items.append(
            {
                "year": year,
                "left": {"months": _timeline_group(by_year[year]["left"])},
                "right": {"months": _timeline_group(by_year[year]["right"])},
            }
        )
    return items


def _build_sankey(jobs: list[Job]) -> dict[str, Any]:
    node_index: dict[str, int] = {}
    nodes: list[str] = []
    sources: list[int] = []
    targets: list[int] = []
    values: list[int] = []
    counts: Counter[tuple[str, str]] = Counter()

    for job in jobs:
        counts[(normalize_source(job.source), normalize_status(job.status))] += 1

    def get_node(value: str) -> int:
        if value not in node_index:
            node_index[value] = len(nodes)
            nodes.append(value)
        return node_index[value]

    for (source, status), count in counts.items():
        sources.append(get_node(source))
        targets.append(get_node(status))
        values.append(count)

    return {"nodes": nodes, "links": {"source": sources, "target": targets, "value": values}}


def _candidate_followup_type(status: str) -> str:
    if normalize_status(status) in {"Interview", "Offer", "Hired", "Rejected", "Ghosted", "Withdrawn", "Declined"}:
        return "status_change"
    return "note"


def _extract_json_payload(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        return {"updates": []}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {"updates": []}
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(raw[start : end + 1])
                return parsed if isinstance(parsed, dict) else {"updates": []}
            except json.JSONDecodeError:
                return {"updates": []}
    return {"updates": []}


def _norm_text(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _find_job_match(jobs: list[Job], update: dict[str, Any]) -> Job | None:
    target_id = str(update.get("job_id") or "").strip()
    if target_id:
        for job in jobs:
            if job.id == target_id or job.legacy_job_id == target_id:
                return job

    company = _norm_text(update.get("company"))
    title = _norm_text(update.get("title"))
    best: tuple[int, Job | None] = (0, None)
    for job in jobs:
        score = 0
        if company and company in _norm_text(job.company):
            score += 2
        if title and title in _norm_text(job.title):
            score += 2
        if score > best[0]:
            best = (score, job)
    return best[1] if best[0] >= 2 else None


def _call_ollama(endpoint: str, model: str, system_prompt: str, email_text: str, timeout_seconds: int) -> str:
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": email_text},
        ],
        "format": "json",
        "options": {"temperature": 0.1},
    }
    request_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint.rstrip("/") + "/api/chat",
        data=request_data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=max(5, int(timeout_seconds))) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Could not reach Ollama endpoint: {body}") from exc

    message = parsed.get("message", {}) if isinstance(parsed, dict) else {}
    return str(message.get("content") or parsed.get("response") or "")


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    root = Path(__file__).resolve().parent
    templates = root / "app" / "templates"
    static = root / "app" / "static"
    test_config = dict(test_config or {})

    app = Flask(__name__, template_folder=str(templates), static_folder=str(static))
    app.config["JSON_SORT_KEYS"] = False
    secret_key = os.getenv("JOBFLOW_SECRET_KEY")
    if not secret_key:
        raise RuntimeError(
            "JOBFLOW_SECRET_KEY must be configured."
        )
    app.config["SECRET_KEY"] = secret_key

    configured_db = test_config.pop("SQLALCHEMY_DATABASE_URI", None) or os.getenv("JOBFLOW_DATABASE_URL") or os.getenv("DATABASE_URL")

    app.config["SQLALCHEMY_DATABASE_URI"] = _resolve_database_uri(configured_db)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.context_processor
    def inject_auth_state() -> dict[str, Any]:
        user = get_current_user()
        return {
            "current_username": user.username if user else None,
            "is_authenticated": bool(user),
        }

    @app.get("/login")
    def login_page():
        if get_current_user():
            return redirect(url_for("index"))
        return render_template("login.html")

    @app.get("/register")
    def register_page():
        if get_current_user():
            return redirect(url_for("index"))
        return render_template("register.html")

    @app.get("/logout")
    def logout_page():
        session.clear()
        return redirect(url_for("login_page"))

    @app.route("/")
    @page_login_required
    def index():
        return render_template("index.html")

    @app.route("/stats2")
    @page_login_required
    def stats2_page():
        return render_template("stats2.html")

    @app.route("/leads")
    @page_login_required
    def leads_page():
        return render_template("leads.html")

    @app.get("/api/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    @app.post("/api/auth/register")
    def auth_register():
        payload = request.get_json(silent=True) or {}
        username = str(payload.get("username") or "").strip()
        password = str(payload.get("password") or "")
        pin = str(payload.get("pin") or "").strip()

        if not username or not password:
            return jsonify({"error": "username and password are required"}), 400
        if len(password) < 8:
            return jsonify({"error": "password must be at least 8 characters"}), 400
        if User.query.filter_by(username=username).first():
            return jsonify({"error": "username already exists"}), 409

        user = User(
            username=username,
            password_hash=_hash_secret(password),
            pin_hash=_hash_secret(pin) if pin else None,
            settings_json=DEFAULT_SETTINGS,
        )
        db.session.add(user)
        db.session.commit()
        session["user_id"] = user.id
        session.permanent = bool(payload.get("remember"))
        return jsonify({"user": user.to_dict()}), 201

    @app.post("/api/auth/login")
    def auth_login():
        payload = request.get_json(silent=True) or {}
        username = str(payload.get("username") or "").strip()
        password = str(payload.get("password") or "")
        user = User.query.filter_by(username=username).first()
        if not user or not _check_secret(password, user.password_hash):
            return jsonify({"error": "Invalid username or password"}), 401
        session["user_id"] = user.id
        session.permanent = bool(payload.get("remember"))
        return jsonify({"user": user.to_dict()})

    @app.post("/api/auth/pin")
    def auth_pin_login():
        payload = request.get_json(silent=True) or {}
        username = str(payload.get("username") or "").strip()
        pin = str(payload.get("pin") or "")
        user = User.query.filter_by(username=username).first()
        if not user or not _check_secret(pin, user.pin_hash):
            return jsonify({"error": "Invalid username or PIN"}), 401
        session["user_id"] = user.id
        session.permanent = True
        return jsonify({"user": user.to_dict()})

    @app.post("/api/auth/logout")
    def auth_logout():
        session.clear()
        return jsonify({"success": True})

    @app.get("/api/auth/me")
    @api_login_required
    def auth_me():
        return jsonify({"user": get_current_user().to_dict()})

    @app.get("/api/settings")
    @api_login_required
    def get_settings():
        return jsonify({"settings": build_settings(get_current_user())})

    @app.put("/api/settings")
    @api_login_required
    def update_settings():
        payload = request.get_json(silent=True) or {}
        user = get_current_user()
        user.settings_json = _merge_dict(build_settings(user), payload)
        db.session.commit()
        return jsonify({"success": True, "settings": build_settings(user)})

    @app.post("/api/ai/process-emails")
    @api_login_required
    def process_emails():
        payload = request.get_json(silent=True) or {}
        email_text = str(payload.get("email_text") or "").strip()
        if not email_text:
            return jsonify({"error": "email_text is required"}), 400

        user = get_current_user()
        settings = build_settings(user)
        ai_settings = settings.get("ai", {})
        jobs = _job_query_for_user(user).all()
        try:
            raw_content = _call_ollama(
                str(ai_settings.get("ollama_endpoint") or DEFAULT_SETTINGS["ai"]["ollama_endpoint"]),
                str(ai_settings.get("ollama_model") or DEFAULT_SETTINGS["ai"]["ollama_model"]),
                str(ai_settings.get("prompts", {}).get("job_status_update") or AI_PROMPT_DEFAULT),
                email_text,
                int(ai_settings.get("timeout_seconds") or 45),
            )
        except Exception as exc:
            return jsonify({"error": str(exc)}), 502

        parsed = _extract_json_payload(raw_content)
        candidates = []
        for item in parsed.get("updates", []):
            if not isinstance(item, dict):
                continue
            matched = _find_job_match(jobs, item)
            candidates.append(
                {
                    "job_id": matched.id if matched else item.get("job_id"),
                    "matched": bool(matched),
                    "company": matched.company if matched else item.get("company", ""),
                    "title": matched.title if matched else item.get("title", ""),
                    "status": normalize_status(item.get("status")),
                    "stage": normalize_stage(item.get("stage"), item.get("status")),
                    "notes_append": str(item.get("notes_append") or "").strip(),
                }
            )
        return jsonify({"raw": raw_content, "updates": candidates})

    @app.post("/api/ai/apply-email-updates")
    @api_login_required
    def apply_email_updates():
        payload = request.get_json(silent=True) or {}
        updates = payload.get("updates")
        if not isinstance(updates, list):
            return jsonify({"error": "updates list is required"}), 400

        applied = 0
        followups_created = 0
        user = get_current_user()
        jobs = {job.id: job for job in _job_query_for_user(user).all()}
        for update in updates:
            if not isinstance(update, dict):
                continue
            job_id = str(update.get("job_id") or "").strip()
            job = jobs.get(job_id)
            if not job:
                continue
            job.status = normalize_status(update.get("status"),)
            job.stage = normalize_stage(update.get("stage"), job.status)
            notes_append = str(update.get("notes_append") or "").strip()
            if notes_append:
                job.notes = f"{job.notes}\nAI email update ({datetime.now().date().isoformat()}): {notes_append}".strip() if job.notes else f"AI email update ({datetime.now().date().isoformat()}): {notes_append}"
            followup = FollowUp(
                user_id=user.id,
                job_id=job.id,
                type=_candidate_followup_type(job.status),
                summary=f"Status updated to {job.status}",
                notes=notes_append,
                timestamp=datetime.now(UTC),
            )
            db.session.add(followup)
            applied += 1
            followups_created += 1

        db.session.commit()
        return jsonify({"success": True, "applied": applied, "followups_created": followups_created})

    @app.get("/api/years")
    @api_login_required
    def get_years():
        user = get_current_user()
        years = sorted({job.date_applied.year for job in _job_query_for_user(user).all() if job.date_applied}, reverse=True)
        return jsonify({"years": years})

    @app.get("/api/sankey")
    @api_login_required
    def get_sankey():
        user = get_current_user()
        jobs = _job_query_for_user(user).all()
        year = request.args.get("year", type=int)
        if year:
            jobs = [job for job in jobs if job.date_applied and job.date_applied.year == year]
        return jsonify(_build_sankey(jobs))

    @app.get("/api/status_counts")
    @api_login_required
    def get_status_counts():
        user = get_current_user()
        year = request.args.get("year", type=int)
        jobs = _job_query_for_user(user).all()
        if year:
            jobs = [job for job in jobs if job.date_applied and job.date_applied.year == year]
        counts = Counter(normalize_status(job.status) for job in jobs)
        ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return jsonify({"labels": [item[0] for item in ordered], "counts": [item[1] for item in ordered]})

    @app.get("/api/timeline")
    @api_login_required
    def get_timeline():
        user = get_current_user()
        jobs = _job_query_for_user(user).order_by(Job.date_applied.desc()).all()
        return jsonify({"items": _build_timeline(jobs)})

    @app.get("/api/jobs")
    @api_login_required
    def list_jobs():
        user = get_current_user()
        jobs = _job_query_for_user(user).order_by(Job.date_applied.desc(), Job.created_at.desc()).all()
        year = request.args.get("year", type=int)
        source = (request.args.get("source") or "").strip().lower()
        status = (request.args.get("status") or "").strip().lower()
        if year:
            jobs = [job for job in jobs if job.date_applied and job.date_applied.year == year]
        if source:
            jobs = [job for job in jobs if (job.source or "").lower() == source]
        if status:
            jobs = [job for job in jobs if normalize_status(job.status).lower() == status]
        return jsonify([_serialize_job(job) for job in jobs])

    @app.post("/api/jobs")
    @api_login_required
    def create_job():
        payload = request.get_json(silent=True) or {}
        required_fields = ["company", "title", "date_applied"]
        missing = [field for field in required_fields if not payload.get(field)]
        if missing:
            return jsonify({"error": "Validation failed", "details": [{"field": field, "message": "Required field"} for field in missing]}), 400
        applied_date = _parse_iso_date(payload.get("date_applied"))
        if not applied_date:
            return jsonify({"error": "Validation failed", "details": [{"field": "date_applied", "message": "Invalid ISO date"}]}), 400
        user = get_current_user()
        job = Job(
            user_id=user.id,
            legacy_job_id=str(payload.get("job_id") or "").strip() or None,
            company=str(payload.get("company") or "").strip(),
            title=str(payload.get("title") or "").strip(),
            date_applied=applied_date,
            date_end=_parse_iso_date(payload.get("date_end")),
            duration_days=payload.get("duration_days"),
            status=normalize_status(payload.get("status")),
            stage=normalize_stage(payload.get("stage"), payload.get("status")),
            source=normalize_source(payload.get("source")),
            location=str(payload.get("location") or "").strip() or None,
            job_type=str(payload.get("job_type") or "").strip() or None,
            salary_range=str(payload.get("salary_range") or "").strip() or None,
            url=str(payload.get("url") or "").strip() or None,
            notes=str(payload.get("notes") or "").strip() or None,
            country=str(payload.get("country") or "").strip() or None,
        )
        db.session.add(job)
        db.session.commit()
        return jsonify({"success": True, "job": _serialize_job(job), "job_id": job.id}), 201

    def _get_owned_job(job_id: str) -> Job | None:
        user = get_current_user()
        return _job_query_for_user(user).filter((Job.id == job_id) | (Job.legacy_job_id == job_id)).first()

    @app.put("/api/jobs/<job_id>")
    @api_login_required
    def update_job(job_id: str):
        job = _get_owned_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        payload = request.get_json(silent=True) or {}
        if "company" in payload:
            job.company = str(payload.get("company") or "").strip() or job.company
        if "title" in payload:
            job.title = str(payload.get("title") or "").strip() or job.title
        if "date_applied" in payload:
            applied = _parse_iso_date(payload.get("date_applied"))
            if not applied:
                return jsonify({"error": "Validation failed", "details": [{"field": "date_applied", "message": "Invalid ISO date"}]}), 400
            job.date_applied = applied
        if "date_end" in payload:
            job.date_end = _parse_iso_date(payload.get("date_end"))
        if "status" in payload:
            job.status = normalize_status(payload.get("status"))
        if "stage" in payload or "status" in payload:
            job.stage = normalize_stage(payload.get("stage"), payload.get("status") or job.status)
        if "source" in payload:
            job.source = normalize_source(payload.get("source"))
        if "location" in payload:
            job.location = str(payload.get("location") or "").strip() or None
        if "job_type" in payload:
            job.job_type = str(payload.get("job_type") or "").strip() or None
        if "salary_range" in payload:
            job.salary_range = str(payload.get("salary_range") or "").strip() or None
        if "url" in payload:
            job.url = str(payload.get("url") or "").strip() or None
        if "notes" in payload:
            job.notes = str(payload.get("notes") or "").strip() or None
        if "country" in payload:
            job.country = str(payload.get("country") or "").strip() or None
        if job.date_end and job.date_applied:
            job.duration_days = compute_duration_days(job.date_applied.isoformat(), job.date_end.isoformat())
        db.session.commit()
        return jsonify({"success": True, "job": _serialize_job(job), "job_id": job.id})

    @app.delete("/api/jobs/<job_id>")
    @api_login_required
    def delete_job(job_id: str):
        job = _get_owned_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        db.session.delete(job)
        db.session.commit()
        return jsonify({"success": True, "deleted": True, "job_id": job_id})

    @app.put("/api/jobs/<int:index>")
    @api_login_required
    def update_job_by_index(index: int):
        user = get_current_user()
        jobs = _job_query_for_user(user).order_by(Job.date_applied.desc(), Job.created_at.desc()).all()
        if index < 0 or index >= len(jobs):
            return jsonify({"error": "Job not found"}), 404
        return update_job(jobs[index].id)

    @app.delete("/api/jobs/<int:index>")
    @api_login_required
    def delete_job_by_index(index: int):
        user = get_current_user()
        jobs = _job_query_for_user(user).order_by(Job.date_applied.desc(), Job.created_at.desc()).all()
        if index < 0 or index >= len(jobs):
            return jsonify({"error": "Job not found"}), 404
        return delete_job(jobs[index].id)

    @app.get("/api/jobs/sla-violations")
    @api_login_required
    def get_job_sla_violations():
        return jsonify(_get_sla_violations(get_current_user()))

    @app.patch("/api/jobs/<job_id>/status")
    @api_login_required
    def update_job_status(job_id: str):
        job = _get_owned_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        payload = request.get_json(silent=True) or {}
        status = normalize_status(payload.get("status"))
        job.status = status
        job.stage = normalize_stage(payload.get("stage"), status)
        if is_terminal(status) and not job.date_end:
            job.date_end = datetime.now(UTC).date()
        if job.date_end and job.date_applied:
            job.duration_days = compute_duration_days(job.date_applied.isoformat(), job.date_end.isoformat())

        followup = FollowUp(
            user_id=job.user_id,
            job_id=job.id,
            type="status_change",
            summary=f"Status updated to {status}",
            notes=str(payload.get("notes") or "").strip() or None,
            timestamp=datetime.now(UTC),
        )
        db.session.add(followup)
        db.session.commit()
        return jsonify({"success": True, "job": _serialize_job(job), "job_id": job.id})

    @app.post("/api/jobs/bulk-update")
    @api_login_required
    def bulk_update_jobs():
        payload = request.get_json(silent=True) or {}
        updates = payload.get("updates") or payload.get("jobs")
        if not isinstance(updates, list):
            return jsonify({"error": "updates list is required"}), 400
        updated = 0
        for item in updates:
            if not isinstance(item, dict) or not item.get("job_id"):
                continue
            job = _get_owned_job(str(item.get("job_id")))
            if not job:
                continue
            if "status" in item:
                job.status = normalize_status(item.get("status"))
            if "stage" in item or "status" in item:
                job.stage = normalize_stage(item.get("stage"), item.get("status") or job.status)
            if "notes" in item:
                job.notes = str(item.get("notes") or "").strip() or None
            updated += 1
        db.session.commit()
        return jsonify({"success": True, "updated": updated})

    @app.get("/api/jobs/statistics")
    @api_login_required
    def get_job_statistics():
        user = get_current_user()
        jobs = _job_query_for_user(user).all()
        followups = _followup_query_for_user(user).all()
        status_counts = Counter(normalize_status(job.status) for job in jobs)
        source_counts = Counter(normalize_source(job.source) for job in jobs)
        return jsonify(
            {
                "summary": {
                    "total_jobs": len(jobs),
                    "active_jobs": len([job for job in jobs if not is_terminal(job.status)]),
                    "terminal_jobs": len([job for job in jobs if is_terminal(job.status)]),
                },
                "status_counts": dict(status_counts),
                "source_counts": dict(source_counts),
                "followup_activity": {
                    "total_followups": len(followups),
                    "avg_per_job": len(followups) / len(jobs) if jobs else 0,
                },
            }
        )

    @app.get("/api/followup/list")
    @api_login_required
    def get_followup_list():
        user = get_current_user()
        jobs = [job for job in _job_query_for_user(user).all() if not is_terminal(job.status)]
        items = [_enrich_active_job(job) for job in jobs]
        items.sort(key=lambda item: item.get("next_action_due") or "9999-12-31")
        return jsonify(items)

    @app.get("/api/followups")
    @api_login_required
    def get_followups():
        user = get_current_user()
        job_id = str(request.args.get("job_id") or "").strip()
        query = _followup_query_for_user(user).order_by(FollowUp.timestamp.desc())
        if job_id:
            job = _get_owned_job(job_id)
            if not job:
                return jsonify([])
            return jsonify([entry.to_dict() for entry in query.filter_by(job_id=job.id).all()])
        return jsonify({"entries": [entry.to_dict() for entry in query.all()]})

    @app.post("/api/followups")
    @api_login_required
    def add_followup():
        payload = request.get_json(silent=True) or {}
        job = _get_owned_job(str(payload.get("job_id") or ""))
        if not job:
            return jsonify({"error": "Job not found"}), 404
        summary = str(payload.get("summary") or "").strip()
        if not summary:
            return jsonify({"error": "summary is required"}), 400
        next_action = payload.get("next_action") if isinstance(payload.get("next_action"), dict) else None
        entry = FollowUp(
            user_id=job.user_id,
            job_id=job.id,
            type=str(payload.get("type") or "note").strip() or "note",
            summary=summary,
            notes=str(payload.get("details") or payload.get("notes") or "").strip() or None,
            author=str(payload.get("author") or "user").strip() or "user",
            timestamp=_parse_iso_datetime(payload.get("timestamp")) or datetime.now(UTC),
            next_action_what=str(next_action.get("what") or "").strip() if next_action else None,
            next_action_when=_parse_iso_date(next_action.get("when")) if next_action else None,
            next_action_done=bool(next_action.get("done")) if next_action else False,
            tags=payload.get("tags") if isinstance(payload.get("tags"), list) else [],
        )
        db.session.add(entry)
        db.session.commit()
        return jsonify({"success": True, "entry": entry.to_dict()}), 201

    def _get_owned_followup(entry_id: str) -> FollowUp | None:
        user = get_current_user()
        return _followup_query_for_user(user).filter((FollowUp.id == entry_id) | (FollowUp.legacy_followup_id == entry_id)).first()

    @app.patch("/api/followups/<entry_id>")
    @api_login_required
    def update_followup(entry_id: str):
        entry = _get_owned_followup(entry_id)
        if not entry:
            return jsonify({"error": "Follow-up not found"}), 404
        payload = request.get_json(silent=True) or {}
        if "type" in payload:
            entry.type = str(payload.get("type") or "note").strip() or "note"
        if "summary" in payload:
            entry.summary = str(payload.get("summary") or "").strip() or entry.summary
        if "details" in payload or "notes" in payload:
            entry.notes = str(payload.get("details") or payload.get("notes") or "").strip() or None
        if "timestamp" in payload:
            parsed = _parse_iso_datetime(payload.get("timestamp"))
            if parsed:
                entry.timestamp = parsed
        if "tags" in payload and isinstance(payload.get("tags"), list):
            entry.tags = payload["tags"]
        next_action = payload.get("next_action") if isinstance(payload.get("next_action"), dict) else None
        if next_action is not None:
            entry.next_action_what = str(next_action.get("what") or "").strip() or None
            entry.next_action_when = _parse_iso_date(next_action.get("when"))
            entry.next_action_done = bool(next_action.get("done"))
        db.session.commit()
        return jsonify({"success": True, "entry": entry.to_dict()})

    @app.delete("/api/followups/<entry_id>")
    @api_login_required
    def delete_followup(entry_id: str):
        entry = _get_owned_followup(entry_id)
        if not entry:
            return jsonify({"error": "Follow-up not found"}), 404
        db.session.delete(entry)
        db.session.commit()
        return jsonify({"success": True, "deleted": True, "entry_id": entry_id})

    @app.post("/api/followups/close_job")
    @api_login_required
    def close_job_from_followups():
        payload = request.get_json(silent=True) or {}
        job = _get_owned_job(str(payload.get("job_id") or ""))
        if not job:
            return jsonify({"error": "Job not found"}), 404
        status = normalize_status(payload.get("status") or payload.get("final_status"))
        job.status = status
        job.stage = normalize_stage(payload.get("stage"), status)
        job.date_end = datetime.now(UTC).date()
        job.duration_days = compute_duration_days(job.date_applied.isoformat(), job.date_end.isoformat())
        followup = FollowUp(
            user_id=job.user_id,
            job_id=job.id,
            type="status_change",
            summary=f"Job closed as {status}",
            notes=str(payload.get("notes") or "").strip() or None,
            timestamp=datetime.now(UTC),
        )
        db.session.add(followup)
        db.session.commit()
        return jsonify({"success": True, "job": _serialize_job(job), "job_id": job.id})

    @app.get("/api/followups/enhanced")
    @api_login_required
    def get_followups_enhanced():
        user = get_current_user()
        entries = [entry.to_dict() for entry in _followup_query_for_user(user).order_by(FollowUp.timestamp.desc()).all()]
        violations = _get_sla_violations(user)
        violated_job_ids = {
            item["job_id"]
            for category in ["no_followup", "interview_no_update", "screening_no_update", "offer_response"]
            for item in violations.get(category, [])
        }
        enriched = []
        for entry in entries:
            job = _get_owned_job(entry["job_id"])
            enriched.append(
                {
                    **entry,
                    "company": job.company if job else "",
                    "title": job.title if job else "",
                    "has_sla_violation": entry["job_id"] in violated_job_ids,
                }
            )
        return jsonify({"followups": enriched, "summary": {"total_followups": len(entries), "validation_errors": 0}})

    @app.get("/api/followups/sla")
    @api_login_required
    def get_followups_sla():
        return jsonify(_get_sla_violations(get_current_user()))

    @app.post("/api/followups/bulk")
    @api_login_required
    def bulk_update_followups():
        payload = request.get_json(silent=True) or {}
        updates = payload.get("updates")
        if not isinstance(updates, list):
            return jsonify({"error": "updates list is required"}), 400
        updated = 0
        for item in updates:
            if not isinstance(item, dict) or not item.get("entry_id"):
                continue
            entry = _get_owned_followup(str(item.get("entry_id")))
            if not entry:
                continue
            if "next_action_done" in item:
                entry.next_action_done = bool(item.get("next_action_done"))
            updated += 1
        db.session.commit()
        return jsonify({"success": True, "updated": updated})

    @app.get("/api/followups/search")
    @api_login_required
    def search_followups():
        user = get_current_user()
        query_text = str(request.args.get("q") or "").strip().lower()
        entries = [entry.to_dict() for entry in _followup_query_for_user(user).order_by(FollowUp.timestamp.desc()).all()]
        if query_text:
            entries = [
                entry
                for entry in entries
                if query_text in (entry.get("summary") or "").lower() or query_text in (entry.get("details") or "").lower()
            ]
        return jsonify({"followups": entries, "count": len(entries)})

    @app.get("/api/followups/analytics")
    @api_login_required
    def followups_analytics():
        user = get_current_user()
        entries = [entry.to_dict() for entry in _followup_query_for_user(user).all()]
        by_type = Counter(entry.get("type") or "note" for entry in entries)
        pending = [entry for entry in entries if entry.get("next_action") and not entry["next_action"].get("done")]
        return jsonify({"totals": {"count": len(entries), "pending_actions": len(pending)}, "by_type": dict(by_type)})

    @app.get("/api/calendar")
    @api_login_required
    def get_calendar():
        user = get_current_user()
        year = request.args.get("year", type=int)
        events: list[dict[str, Any]] = []
        for job in _job_query_for_user(user).all():
            if job.date_applied and (not year or job.date_applied.year == year):
                events.append(
                    {
                        "date": job.date_applied.isoformat(),
                        "event_type": "job_application",
                        "title": f"Applied: {job.company} - {job.title}",
                        "details": {"job_id": job.id, "status": job.status},
                        "color": "#667eea",
                    }
                )
        for followup in _followup_query_for_user(user).all():
            event_year = followup.timestamp.year if followup.timestamp else None
            if event_year and (not year or event_year == year):
                events.append(
                    {
                        "date": followup.timestamp.date().isoformat(),
                        "event_type": "followup",
                        "title": f"Follow-up: {followup.summary}",
                        "details": {"followup_id": followup.id, "type": followup.type},
                        "color": "#764ba2",
                    }
                )
            if followup.next_action_when and not followup.next_action_done and (not year or followup.next_action_when.year == year):
                events.append(
                    {
                        "date": followup.next_action_when.isoformat(),
                        "event_type": "next_action",
                        "title": f"Action: {followup.next_action_what or 'Follow-up'}",
                        "details": {"followup_id": followup.id},
                        "color": "#ff8a65",
                    }
                )
        for lead in _lead_query_for_user(user).all():
            if lead.date_contacted and (not year or lead.date_contacted.year == year):
                events.append(
                    {
                        "date": lead.date_contacted.isoformat(),
                        "event_type": "lead_contact",
                        "title": f"Lead Contact: {lead.name} - {lead.company}",
                        "details": {"lead_id": lead.id, "status": lead.status},
                        "color": "#42a5f5",
                    }
                )
            if lead.next_action_when and not lead.next_action_done and (not year or lead.next_action_when.year == year):
                events.append(
                    {
                        "date": lead.next_action_when.isoformat(),
                        "event_type": "lead_next_action",
                        "title": f"Lead Action: {lead.next_action_what or 'Follow-up'} - {lead.name}",
                        "details": {"lead_id": lead.id},
                        "color": "#66bb6a",
                    }
                )
        events.sort(key=lambda item: item["date"])
        return jsonify({"events": events})

    @app.get("/api/leads")
    @api_login_required
    def list_leads():
        user = get_current_user()
        return jsonify([lead.to_dict() for lead in _lead_query_for_user(user).order_by(Lead.date_contacted.desc()).all()])

    @app.post("/api/leads")
    @api_login_required
    def create_lead():
        payload = request.get_json(silent=True) or {}
        missing = [field for field in ["name", "company", "contact_method", "date_contacted", "status"] if not payload.get(field)]
        if missing:
            return jsonify({"error": f"Missing required field: {missing[0]}"}), 400
        contacted = _parse_iso_date(payload.get("date_contacted"))
        if not contacted:
            return jsonify({"error": "Invalid date_contacted"}), 400
        next_action = payload.get("next_action") if isinstance(payload.get("next_action"), dict) else None
        user = get_current_user()
        lead = Lead(
            user_id=user.id,
            legacy_lead_id=str(payload.get("lead_id") or "").strip() or None,
            name=str(payload.get("name") or "").strip(),
            company=str(payload.get("company") or "").strip(),
            role=str(payload.get("role") or "").strip() or None,
            email=str(payload.get("email") or "").strip() or None,
            linkedin=str(payload.get("linkedin") or "").strip() or None,
            contact_method=str(payload.get("contact_method") or "").strip(),
            date_contacted=contacted,
            status=str(payload.get("status") or "Active").strip(),
            source=str(payload.get("source") or "").strip() or None,
            topic=str(payload.get("topic") or "").strip() or None,
            notes=str(payload.get("notes") or "").strip() or None,
            next_action_what=str(next_action.get("what") or "").strip() if next_action else None,
            next_action_when=_parse_iso_date(next_action.get("when")) if next_action else None,
            next_action_done=bool(next_action.get("done")) if next_action else False,
        )
        linked_job_id = str(payload.get("linked_job_id") or "").strip()
        if linked_job_id:
            linked_job = _get_owned_job(linked_job_id)
            lead.linked_job_id = linked_job.id if linked_job else None
        db.session.add(lead)
        db.session.commit()
        return jsonify(lead.to_dict()), 201

    def _get_owned_lead(lead_id: str) -> Lead | None:
        user = get_current_user()
        return _lead_query_for_user(user).filter((Lead.id == lead_id) | (Lead.legacy_lead_id == lead_id)).first()

    @app.patch("/api/leads/<lead_id>")
    @api_login_required
    def update_lead(lead_id: str):
        lead = _get_owned_lead(lead_id)
        if not lead:
            return jsonify({"error": "Lead not found"}), 404
        payload = request.get_json(silent=True) or {}
        for field in ["name", "company", "role", "email", "linkedin", "contact_method", "status", "source", "topic", "notes"]:
            if field in payload:
                setattr(lead, field, str(payload.get(field) or "").strip() or None)
        if "date_contacted" in payload:
            contacted = _parse_iso_date(payload.get("date_contacted"))
            if not contacted:
                return jsonify({"error": "Invalid date_contacted"}), 400
            lead.date_contacted = contacted
        next_action = payload.get("next_action") if isinstance(payload.get("next_action"), dict) else None
        if next_action is not None:
            lead.next_action_what = str(next_action.get("what") or "").strip() or None
            lead.next_action_when = _parse_iso_date(next_action.get("when"))
            lead.next_action_done = bool(next_action.get("done"))
        db.session.commit()
        return jsonify(lead.to_dict())

    @app.delete("/api/leads/<lead_id>")
    @api_login_required
    def delete_lead(lead_id: str):
        lead = _get_owned_lead(lead_id)
        if not lead:
            return jsonify({"error": "Lead not found"}), 404
        deleted = lead.to_dict()
        db.session.delete(lead)
        db.session.commit()
        return jsonify({"message": "Lead deleted", "deleted_lead": deleted})

    @app.post("/api/leads/convert_to_job")
    @api_login_required
    def convert_lead_to_job():
        payload = request.get_json(silent=True) or {}
        lead = _get_owned_lead(str(payload.get("lead_id") or ""))
        if not lead:
            return jsonify({"error": "Lead not found"}), 404
        job_payload = payload.get("job_payload") if isinstance(payload.get("job_payload"), dict) else None
        if not job_payload:
            return jsonify({"error": "job_payload is required"}), 400
        applied_date = _parse_iso_date(job_payload.get("date_applied")) or datetime.now(UTC).date()
        job = Job(
            user_id=lead.user_id,
            company=str(job_payload.get("company") or lead.company).strip(),
            title=str(job_payload.get("title") or "").strip(),
            date_applied=applied_date,
            status=normalize_status(job_payload.get("status")),
            stage=normalize_stage(job_payload.get("stage"), job_payload.get("status")),
            source=normalize_source(job_payload.get("source")),
            notes=f"Converted from lead: {lead.topic or ''} - {lead.notes or ''}".strip(" -"),
        )
        db.session.add(job)
        db.session.flush()
        lead.status = "Converted"
        lead.linked_job_id = job.id
        db.session.commit()
        return jsonify({"message": "Lead converted to job", "job": _serialize_job(job), "lead": lead.to_dict()}), 201

    @app.get("/api/journal")
    @api_login_required
    def list_journal_entries():
        user = get_current_user()
        entries = [entry.to_dict() for entry in _journal_query_for_user(user).order_by(JournalEntry.timestamp.desc()).all()]
        return jsonify({"entries": entries})

    @app.post("/api/journal")
    @api_login_required
    def create_journal_entry():
        payload = request.get_json(silent=True) or {}
        text = str(payload.get("text") or "").strip()
        if not text:
            return jsonify({"error": "text is required"}), 400
        user = get_current_user()
        linked_job_id = None
        if payload.get("linked_job_id"):
            linked_job = _get_owned_job(str(payload.get("linked_job_id")))
            linked_job_id = linked_job.id if linked_job else None
        entry = JournalEntry(
            user_id=user.id,
            legacy_entry_id=str(payload.get("entry_id") or "").strip() or None,
            timestamp=_parse_iso_datetime(payload.get("timestamp")) or datetime.now(UTC),
            title=str(payload.get("title") or "").strip() or None,
            text=text,
            sentiment_score=payload.get("sentiment_score"),
            sentiment_label=str(payload.get("sentiment_label") or "").strip() or None,
            linked_job_id=linked_job_id,
        )
        db.session.add(entry)
        db.session.commit()
        return jsonify({"entry": entry.to_dict()}), 201

    def _get_owned_journal_entry(entry_id: str) -> JournalEntry | None:
        user = get_current_user()
        return _journal_query_for_user(user).filter((JournalEntry.id == entry_id) | (JournalEntry.legacy_entry_id == entry_id)).first()

    @app.patch("/api/journal/<entry_id>")
    @api_login_required
    def update_journal_entry(entry_id: str):
        entry = _get_owned_journal_entry(entry_id)
        if not entry:
            return jsonify({"error": "Journal entry not found"}), 404
        payload = request.get_json(silent=True) or {}
        if "title" in payload:
            entry.title = str(payload.get("title") or "").strip() or None
        if "text" in payload:
            text = str(payload.get("text") or "").strip()
            if not text:
                return jsonify({"error": "text is required"}), 400
            entry.text = text
        if "sentiment_score" in payload:
            entry.sentiment_score = payload.get("sentiment_score")
        if "sentiment_label" in payload:
            entry.sentiment_label = str(payload.get("sentiment_label") or "").strip() or None
        db.session.commit()
        return jsonify({"entry": entry.to_dict()})

    @app.delete("/api/journal/<entry_id>")
    @api_login_required
    def delete_journal_entry(entry_id: str):
        entry = _get_owned_journal_entry(entry_id)
        if not entry:
            return jsonify({"error": "Journal entry not found"}), 404
        db.session.delete(entry)
        db.session.commit()
        return jsonify({"success": True, "deleted": True, "entry_id": entry_id})

    def _metrics_payload(user: User) -> dict[str, Any]:
        jobs = _job_query_for_user(user).all()
        followups = _followup_query_for_user(user).all()
        journal_entries = _journal_query_for_user(user).all()
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "data_points": len(jobs),
            "by_source": dict(Counter(normalize_source(job.source) for job in jobs)),
            "by_status": dict(Counter(normalize_status(job.status) for job in jobs)),
            "funnel": dict(Counter(normalize_stage(job.stage) for job in jobs)),
            "followup_metrics": {"count": len(followups)},
            "sentiment_trends": {"count": len(journal_entries)},
        }

    @app.get("/api/metrics/cache")
    @api_login_required
    def get_metrics_cache():
        return jsonify(_metrics_payload(get_current_user()))

    @app.post("/api/admin/rebuild_cache")
    @api_login_required
    def rebuild_cache():
        return jsonify({"success": True, "cache": _metrics_payload(get_current_user())})

    @app.get("/api/admin/health")
    @api_login_required
    def admin_health():
        user = get_current_user()
        return jsonify({"status": "ok", "username": user.username, "timestamp": datetime.now(UTC).isoformat()})

    @app.get("/api/stats2/scatter")
    @api_login_required
    def stats2_scatter():
        user = get_current_user()
        year = request.args.get("year", type=int)
        source = (request.args.get("source") or "").strip().lower()
        status = (request.args.get("status") or "").strip().lower()
        jobs = _job_query_for_user(user).all()
        if year:
            jobs = [job for job in jobs if job.date_applied and job.date_applied.year == year]
        if source:
            jobs = [job for job in jobs if (job.source or "").lower() == source]
        if status:
            jobs = [job for job in jobs if normalize_status(job.status).lower() == status]
        followups = _followup_query_for_user(user).all()
        job_ids = {job.id for job in jobs}
        return jsonify(
            {
                "applications_over_time": [
                    {
                        "date": job.date_applied.isoformat(),
                        "cumulative_count": index + 1,
                        "source": job.source,
                        "status": job.status,
                    }
                    for index, job in enumerate(sorted(jobs, key=lambda item: item.date_applied))
                ],
                "mood_vs_productivity": [
                    {
                        "sentiment_score": entry.sentiment_score,
                        "productivity": 1,
                        "date": entry.timestamp.date().isoformat(),
                        "job_id": entry.linked_job_id,
                    }
                    for entry in _journal_query_for_user(user).all()
                    if entry.linked_job_id in job_ids and entry.sentiment_score is not None
                ],
                "followup_timing_outcome": [
                    {
                        "days_after_application": (followup.timestamp.date() - followup.job.date_applied).days,
                        "outcome": followup.job.status,
                        "type": followup.type,
                    }
                    for followup in followups
                    if followup.job_id in job_ids and followup.job and followup.job.date_applied
                ],
                "duration_vs_source": [
                    {
                        "duration_days": _serialize_job(job).get("duration_days") or 0,
                        "source": job.source,
                        "outcome": job.status,
                    }
                    for job in jobs
                    if is_terminal(job.status)
                ],
            }
        )

    @app.get("/api/stats2/heatmap")
    @api_login_required
    def stats2_heatmap():
        user = get_current_user()
        jobs = _job_query_for_user(user).all()
        apps_by_weekday_week: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for job in jobs:
            week_key = f"Week {job.date_applied.isocalendar()[1]}"
            weekday = job.date_applied.strftime("%A")
            apps_by_weekday_week[week_key][weekday] += 1
        weeks = sorted(apps_by_weekday_week.keys())
        z_matrix = [[apps_by_weekday_week[week].get(day, 0) for week in weeks] for day in weekdays]
        followup_entries = _followup_query_for_user(user).all()
        followup_types = sorted({entry.type for entry in followup_entries})
        followup_weeks = sorted({f"Week {entry.timestamp.isocalendar()[1]}" for entry in followup_entries})
        followup_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for entry in followup_entries:
            followup_counts[f"Week {entry.timestamp.isocalendar()[1]}"][entry.type] += 1
        followup_z = [[followup_counts[week].get(ftype, 0) for week in followup_weeks] for ftype in followup_types]
        return jsonify(
            {
                "applications_weekday_week": {"z": z_matrix, "x": weeks, "y": weekdays, "colorscale": "Blues"},
                "followup_intensity": {
                    "z": followup_z,
                    "x": followup_weeks,
                    "y": followup_types,
                    "colorscale": "RdYlGn",
                },
                "mood_vs_activity": {
                    "z": [[1, 2], [3, 4]],
                    "x": ["Low Activity", "High Activity"],
                    "y": ["Negative", "Positive"],
                    "colorscale": "PuBuGn",
                },
                "hourly_engagement": {
                    "z": [[0] * 24 for _ in range(7)],
                    "x": [f"{hour}:00" for hour in range(24)],
                    "y": weekdays,
                    "colorscale": "Viridis",
                },
            }
        )

    return app