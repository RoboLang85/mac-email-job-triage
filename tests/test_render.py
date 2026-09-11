from pathlib import Path

from mac_email_job_triage.render import render_digest


def test_render_strips_tracking_query(tmp_path: Path):
    rows = [
        {
            "urgency": 5,
            "subject": "Action required",
            "source": "outlook",
            "sender": "a@example.com",
            "category": "other",
            "needs_reply": 1,
            "summary": "Review this.",
            "web_link": "https://example.com/message?id=secret#frag",
        }
    ]
    path = render_digest(rows, tmp_path)
    text = path.read_text()
    assert "https://example.com/message" in text
    assert "id=secret" not in text
