from pathlib import Path

from mac_email_job_triage.db import Database
from mac_email_job_triage.models import MessageRecord, TriageDecision


def test_message_idempotency(tmp_path: Path):
    db = Database(tmp_path / "triage.db")
    msg = MessageRecord(source="gmail", external_id="42", subject="hello", body="body")
    first = db.upsert_message(msg, "body")
    second = db.upsert_message(msg, "body")
    assert first == second
    assert not db.has_triage("gmail", "42")
    db.save_triage(
        first,
        TriageDecision(
            category="personal", needs_reply=True, urgency=3, summary="Reply requested", confidence=0.9
        ),
        "test-model",
    )
    assert db.has_triage("gmail", "42")
