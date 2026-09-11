from mac_email_job_triage.config import recommend_model


def test_model_recommendations():
    assert recommend_model(16) == "qwen3:8b"
    assert recommend_model(24) == "qwen3:14b"
    assert recommend_model(32) == "qwen3:30b"
    assert recommend_model(64) == "qwen3:30b"
