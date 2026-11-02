from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint


db = SQLAlchemy()


def new_uuid() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


def date_to_iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


def datetime_to_iso(value: datetime | None) -> str | None:
    if not value:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.Text, nullable=False)
    pin_hash = db.Column(db.Text, nullable=True)
    settings_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    jobs = db.relationship("Job", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    followups = db.relationship("FollowUp", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    leads = db.relationship("Lead", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    journal_entries = db.relationship(
        "JournalEntry",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "created_at": datetime_to_iso(self.created_at),
            "has_pin": bool(self.pin_hash),
        }


class Job(db.Model):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("user_id", "legacy_job_id", name="uq_jobs_user_legacy_job_id"),)

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    legacy_job_id = db.Column(db.String(128), nullable=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    company = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    date_applied = db.Column(db.Date, nullable=False)
    date_end = db.Column(db.Date, nullable=True)
    duration_days = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(80), nullable=False, default="Applied")
    stage = db.Column(db.String(80), nullable=False, default="applied")
    source = db.Column(db.String(120), nullable=True)
    location = db.Column(db.String(255), nullable=True)
    job_type = db.Column(db.String(120), nullable=True)
    salary_range = db.Column(db.String(120), nullable=True)
    url = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    country = db.Column(db.String(8), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    user = db.relationship("User", back_populates="jobs")
    followups = db.relationship("FollowUp", back_populates="job", cascade="all, delete-orphan", lazy="dynamic")
    leads = db.relationship("Lead", back_populates="linked_job", lazy="dynamic")
    journal_entries = db.relationship("JournalEntry", back_populates="linked_job", lazy="dynamic")

    def to_dict(self, *, include_counts: bool = False) -> dict:
        payload = {
            "id": self.id,
            "job_id": self.id,
            "legacy_job_id": self.legacy_job_id,
            "user_id": self.user_id,
            "company": self.company,
            "title": self.title,
            "date_applied": date_to_iso(self.date_applied),
            "date_end": date_to_iso(self.date_end),
            "duration_days": self.duration_days,
            "status": self.status,
            "stage": self.stage,
            "source": self.source or "",
            "location": self.location or "",
            "job_type": self.job_type or "",
            "salary_range": self.salary_range or "",
            "url": self.url or "",
            "notes": self.notes or "",
            "country": self.country or "",
            "created_at": datetime_to_iso(self.created_at),
            "updated_at": datetime_to_iso(self.updated_at),
        }
        if include_counts:
            payload["followup_count"] = self.followups.count()
        return payload


class FollowUp(db.Model):
    __tablename__ = "followups"
    __table_args__ = (UniqueConstraint("user_id", "legacy_followup_id", name="uq_followups_user_legacy_followup_id"),)

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    legacy_followup_id = db.Column(db.String(128), nullable=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    job_id = db.Column(db.String(36), db.ForeignKey("jobs.id"), nullable=False, index=True)
    timestamp = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    type = db.Column(db.String(80), nullable=False, default="note")
    summary = db.Column(db.String(255), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    author = db.Column(db.String(80), nullable=True, default="user")
    next_action_when = db.Column(db.Date, nullable=True)
    next_action_done = db.Column(db.Boolean, nullable=False, default=False)
    next_action_what = db.Column(db.String(255), nullable=True)
    tags = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    user = db.relationship("User", back_populates="followups")
    job = db.relationship("Job", back_populates="followups")

    def to_dict(self) -> dict:
        next_action = None
        if self.next_action_what or self.next_action_when:
            next_action = {
                "what": self.next_action_what or "",
                "when": date_to_iso(self.next_action_when),
                "done": bool(self.next_action_done),
            }

        return {
            "id": self.id,
            "followup_id": self.id,
            "legacy_followup_id": self.legacy_followup_id,
            "user_id": self.user_id,
            "job_id": self.job_id,
            "timestamp": datetime_to_iso(self.timestamp),
            "type": self.type,
            "summary": self.summary,
            "details": self.notes or "",
            "notes": self.notes or "",
            "author": self.author or "user",
            "next_action": next_action,
            "tags": list(self.tags or []),
            "created_at": datetime_to_iso(self.created_at),
        }


class Lead(db.Model):
    __tablename__ = "leads"
    __table_args__ = (UniqueConstraint("user_id", "legacy_lead_id", name="uq_leads_user_legacy_lead_id"),)

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    legacy_lead_id = db.Column(db.String(128), nullable=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    company = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    linkedin = db.Column(db.Text, nullable=True)
    contact_method = db.Column(db.String(80), nullable=False)
    date_contacted = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(80), nullable=False, default="Active")
    source = db.Column(db.String(120), nullable=True)
    topic = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    next_action_when = db.Column(db.Date, nullable=True)
    next_action_done = db.Column(db.Boolean, nullable=False, default=False)
    next_action_what = db.Column(db.String(255), nullable=True)
    linked_job_id = db.Column(db.String(36), db.ForeignKey("jobs.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    user = db.relationship("User", back_populates="leads")
    linked_job = db.relationship("Job", back_populates="leads")

    def to_dict(self) -> dict:
        next_action = None
        if self.next_action_what or self.next_action_when:
            next_action = {
                "what": self.next_action_what or "",
                "when": date_to_iso(self.next_action_when),
                "done": bool(self.next_action_done),
            }

        return {
            "id": self.id,
            "lead_id": self.id,
            "legacy_lead_id": self.legacy_lead_id,
            "user_id": self.user_id,
            "name": self.name,
            "company": self.company,
            "role": self.role or "",
            "email": self.email or "",
            "linkedin": self.linkedin or "",
            "contact_method": self.contact_method,
            "date_contacted": date_to_iso(self.date_contacted),
            "status": self.status,
            "source": self.source or "",
            "topic": self.topic or "",
            "notes": self.notes or "",
            "next_action": next_action,
            "linked_job_id": self.linked_job_id,
            "created_at": datetime_to_iso(self.created_at),
            "updated_at": datetime_to_iso(self.updated_at),
        }


class JournalEntry(db.Model):
    __tablename__ = "journal_entries"
    __table_args__ = (UniqueConstraint("user_id", "legacy_entry_id", name="uq_journal_user_legacy_entry_id"),)

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    legacy_entry_id = db.Column(db.String(128), nullable=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    timestamp = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    title = db.Column(db.String(255), nullable=True)
    text = db.Column(db.Text, nullable=False)
    sentiment_score = db.Column(db.Float, nullable=True)
    sentiment_label = db.Column(db.String(40), nullable=True)
    linked_job_id = db.Column(db.String(36), db.ForeignKey("jobs.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    user = db.relationship("User", back_populates="journal_entries")
    linked_job = db.relationship("Job", back_populates="journal_entries")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "entry_id": self.id,
            "legacy_entry_id": self.legacy_entry_id,
            "user_id": self.user_id,
            "timestamp": datetime_to_iso(self.timestamp),
            "title": self.title or "",
            "text": self.text,
            "sentiment_score": self.sentiment_score,
            "sentiment_label": self.sentiment_label,
            "linked_job_id": self.linked_job_id,
            "created_at": datetime_to_iso(self.created_at),
            "updated_at": datetime_to_iso(self.updated_at),
        }