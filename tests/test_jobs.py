from mac_email_job_triage.jobs.scoring import deterministic_remote_status
from mac_email_job_triage.models import JobRecord


def make_job(location: str, workplace_type: str | None = None) -> JobRecord:
    return JobRecord(
        provider="lever",
        external_id="1",
        company="Example",
        title="Security Architect",
        location=location,
        workplace_type=workplace_type,
        apply_url="https://example.com/job",
    )


def test_remote_gate():
    assert deterministic_remote_status(make_job("Remote - US")) == "remote"
    assert deterministic_remote_status(make_job("Phoenix, AZ", "hybrid")) == "not_remote"
    assert deterministic_remote_status(make_job("United States")) == "unclear"
