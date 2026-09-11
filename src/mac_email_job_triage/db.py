from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .models import JobFit, JobRecord, MessageRecord, TriageDecision

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    thread_id TEXT,
    sender TEXT,
    subject TEXT,
    received_at TEXT,
    body_excerpt TEXT,
    web_link TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    UNIQUE(source, external_id)
);

CREATE TABLE IF NOT EXISTS triage (
    message_id INTEGER PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    needs_reply INTEGER NOT NULL,
    urgency INTEGER NOT NULL,
    summary TEXT NOT NULL,
    confidence REAL NOT NULL,
    model TEXT NOT NULL,
    classified_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY,
    provider TEXT NOT NULL,
    external_id TEXT NOT NULL,
    company TEXT NOT NULL,
    title TEXT NOT NULL,
    location TEXT,
    description_excerpt TEXT,
    apply_url TEXT NOT NULL,
    published_at TEXT,
    workplace_type TEXT,
    compensation TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    relevant INTEGER,
    match_score INTEGER,
    remote_status TEXT,
    rationale TEXT,
    gaps_json TEXT,
    review_status TEXT NOT NULL DEFAULT 'ready_for_review',
    UNIQUE(provider, external_id)
);
"""


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.init()

    @contextmanager
    def connect(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        finally:
            con.close()

    def init(self) -> None:
        with self.connect() as con:
            con.executescript(SCHEMA)

    def upsert_message(self, msg: MessageRecord, body_excerpt: str) -> int:
        now = utcnow()
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO messages
                  (source, external_id, thread_id, sender, subject, received_at, body_excerpt,
                   web_link, first_seen_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source, external_id) DO UPDATE SET
                  thread_id=excluded.thread_id,
                  sender=excluded.sender,
                  subject=excluded.subject,
                  received_at=excluded.received_at,
                  body_excerpt=excluded.body_excerpt,
                  web_link=excluded.web_link,
                  last_seen_at=excluded.last_seen_at
                """,
                (
                    msg.source,
                    msg.external_id,
                    msg.thread_id,
                    msg.sender,
                    msg.subject,
                    msg.received_at.isoformat() if msg.received_at else None,
                    body_excerpt,
                    msg.web_link,
                    now,
                    now,
                ),
            )
            row = con.execute(
                "SELECT id FROM messages WHERE source=? AND external_id=?",
                (msg.source, msg.external_id),
            ).fetchone()
            return int(row["id"])

    def has_triage(self, source: str, external_id: str) -> bool:
        with self.connect() as con:
            row = con.execute(
                """
                SELECT 1 FROM triage t JOIN messages m ON m.id=t.message_id
                WHERE m.source=? AND m.external_id=?
                """,
                (source, external_id),
            ).fetchone()
            return row is not None

    def save_triage(self, message_id: int, decision: TriageDecision, model: str) -> None:
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO triage
                  (message_id, category, needs_reply, urgency, summary, confidence, model, classified_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(message_id) DO UPDATE SET
                  category=excluded.category,
                  needs_reply=excluded.needs_reply,
                  urgency=excluded.urgency,
                  summary=excluded.summary,
                  confidence=excluded.confidence,
                  model=excluded.model,
                  classified_at=excluded.classified_at
                """,
                (
                    message_id,
                    decision.category,
                    int(decision.needs_reply),
                    decision.urgency,
                    decision.summary,
                    decision.confidence,
                    model,
                    utcnow(),
                ),
            )

    def digest_rows(self, minimum_urgency: int = 1, since_hours: int = 24) -> list[sqlite3.Row]:
        from datetime import timedelta

        cutoff = (datetime.now(UTC) - timedelta(hours=max(1, since_hours))).isoformat()
        with self.connect() as con:
            return list(
                con.execute(
                    """
                    SELECT m.source, m.external_id, m.sender, m.subject, m.received_at, m.web_link,
                           t.category, t.needs_reply, t.urgency, t.summary, t.confidence
                    FROM messages m JOIN triage t ON t.message_id=m.id
                    WHERE t.urgency >= ? AND t.classified_at >= ?
                    ORDER BY t.urgency DESC, m.received_at DESC
                    """,
                    (minimum_urgency, cutoff),
                ).fetchall()
            )

    def upsert_job(self, job: JobRecord, fit: JobFit | None = None) -> None:
        now = utcnow()
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO jobs
                  (provider, external_id, company, title, location, description_excerpt, apply_url,
                   published_at, workplace_type, compensation, first_seen_at, last_seen_at,
                   relevant, match_score, remote_status, rationale, gaps_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider, external_id) DO UPDATE SET
                  company=excluded.company,
                  title=excluded.title,
                  location=excluded.location,
                  description_excerpt=excluded.description_excerpt,
                  apply_url=excluded.apply_url,
                  published_at=excluded.published_at,
                  workplace_type=excluded.workplace_type,
                  compensation=excluded.compensation,
                  last_seen_at=excluded.last_seen_at,
                  relevant=COALESCE(excluded.relevant, jobs.relevant),
                  match_score=COALESCE(excluded.match_score, jobs.match_score),
                  remote_status=COALESCE(excluded.remote_status, jobs.remote_status),
                  rationale=COALESCE(excluded.rationale, jobs.rationale),
                  gaps_json=COALESCE(excluded.gaps_json, jobs.gaps_json)
                """,
                (
                    job.provider,
                    job.external_id,
                    job.company,
                    job.title,
                    job.location,
                    job.description[:12000],
                    job.apply_url,
                    job.published_at.isoformat() if job.published_at else None,
                    job.workplace_type,
                    job.compensation,
                    now,
                    now,
                    int(fit.relevant) if fit else None,
                    fit.match_score if fit else None,
                    fit.remote_status if fit else None,
                    fit.rationale if fit else None,
                    json.dumps(fit.gaps) if fit else None,
                ),
            )
