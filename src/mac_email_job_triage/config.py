from __future__ import annotations

import os
import subprocess
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    triage_db_path: str = "~/.mac-email-job-triage/triage.db"
    triage_output_dir: str = "~/.mac-email-job-triage/output"
    triage_email_body_chars: int = 4000
    triage_fetch_limit: int = 50
    triage_classify_batch_size: int = 4
    triage_urgency_escalate_threshold: int = 4

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "auto"
    ollama_keep_alive: str = "10m"
    ollama_timeout_seconds: int = 300
    ollama_num_ctx: int = 8192

    gmail_enabled: bool = False
    gmail_user: str = ""
    gmail_app_password: str = ""
    gmail_folder: str = "INBOX"

    outlook_enabled: bool = False
    ms_client_id: str = ""
    ms_tenant_id: str = "consumers"
    ms_token_cache_path: str = "~/.mac-email-job-triage/msal-token-cache.json"
    outlook_folder: str = "inbox"

    frontier_enabled: bool = False
    frontier_base_url: str = ""
    frontier_api_key: str = ""
    frontier_model: str = ""

    job_boards_path: str = "./job_boards.json"
    resume_profile_path: str = "./resume_profile.md"
    remote_only: bool = True

    @property
    def db_path(self) -> Path:
        return Path(self.triage_db_path).expanduser()

    @property
    def output_dir(self) -> Path:
        return Path(self.triage_output_dir).expanduser()

    @property
    def token_cache_path(self) -> Path:
        return Path(self.ms_token_cache_path).expanduser()

    @property
    def selected_model(self) -> str:
        return recommend_model() if self.ollama_model.strip().lower() == "auto" else self.ollama_model


def mac_memory_gb() -> int | None:
    if os.uname().sysname != "Darwin":
        return None
    try:
        value = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip()
        return round(int(value) / (1024**3))
    except (OSError, ValueError, subprocess.CalledProcessError):
        return None


def recommend_model(memory_gb: int | None = None) -> str:
    memory_gb = memory_gb if memory_gb is not None else mac_memory_gb()
    if memory_gb is None:
        return "qwen3:8b"
    if memory_gb <= 16:
        return "qwen3:8b"
    if memory_gb <= 24:
        return "qwen3:14b"
    return "qwen3:30b"
