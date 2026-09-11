from __future__ import annotations

import json
import platform
import shutil
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .config import Settings, mac_memory_gb, recommend_model
from .connectors import GmailImapConnector, OutlookGraphConnector
from .db import Database
from .jobs import fetch_configured_boards, score_job
from .ollama_client import OllamaClient
from .pipeline import run_pipeline
from .render import render_digest

app = typer.Typer(no_args_is_help=True, help="Local email triage and remote-job review.")
console = Console()


def settings() -> Settings:
    return Settings()


def ollama(settings_: Settings) -> OllamaClient:
    return OllamaClient(
        settings_.ollama_base_url,
        settings_.selected_model,
        settings_.ollama_timeout_seconds,
        settings_.ollama_keep_alive,
        settings_.ollama_num_ctx,
    )


@app.command()
def model() -> None:
    """Show the Apple-Silicon model recommendation."""
    memory = mac_memory_gb()
    console.print(f"Detected unified memory: {memory or 'unknown'} GB")
    console.print(f"Recommended Ollama model: [bold]{recommend_model(memory)}[/bold]")


@app.command()
def doctor() -> None:
    """Check prerequisites without reading mail."""
    s = settings()
    table = Table(title="mac-email-job-triage doctor")
    table.add_column("Check")
    table.add_column("Result")
    table.add_row("OS", platform.platform())
    table.add_row("Architecture", platform.machine())
    table.add_row("Unified memory", f"{mac_memory_gb() or 'unknown'} GB")
    table.add_row("Selected model", s.selected_model)
    table.add_row("Ollama CLI", shutil.which("ollama") or "not found")
    table.add_row("Ollama API", "reachable" if ollama(s).health() else "not reachable")
    table.add_row("Gmail", "enabled" if s.gmail_enabled else "disabled")
    table.add_row("Outlook", "enabled" if s.outlook_enabled else "disabled")
    table.add_row("Database", str(s.db_path))
    console.print(table)


@app.command()
def init_db() -> None:
    """Create/update the local SQLite database."""
    s = settings()
    Database(s.db_path)
    console.print(f"Initialized {s.db_path}")


@app.command("run")
def run() -> None:
    """Fetch unread mail, classify only new items, and store results."""
    s = settings()
    connectors = []
    if s.gmail_enabled:
        connectors.append(GmailImapConnector(s.gmail_user, s.gmail_app_password, s.gmail_folder))
    if s.outlook_enabled:
        connectors.append(
            OutlookGraphConnector(
                s.ms_client_id, s.ms_tenant_id, s.token_cache_path, s.outlook_folder
            )
        )
    if not connectors:
        raise typer.BadParameter("Enable at least one connector in .env")
    fetched, classified = run_pipeline(s, connectors)
    console.print(f"Done. Fetched {fetched}; newly classified {classified}.")


@app.command()
def digest(
    minimum_urgency: int = typer.Option(1, min=1, max=5),
    since_hours: int = typer.Option(24, min=1),
) -> None:
    """Render a deterministic Markdown digest from recent local SQLite state."""
    s = settings()
    db = Database(s.db_path)
    path = render_digest(db.digest_rows(minimum_urgency, since_hours), s.output_dir)
    console.print(f"Wrote {path}")


@app.command("jobs-refresh")
def jobs_refresh(score: bool = typer.Option(False, help="Score jobs against resume_profile.md")) -> None:
    """Fetch configured Greenhouse/Lever/Ashby boards; never submits applications."""
    s = settings()
    db = Database(s.db_path)
    jobs = fetch_configured_boards(Path(s.job_boards_path))
    client = ollama(s) if score else None
    profile = ""
    if score:
        profile_path = Path(s.resume_profile_path)
        if not profile_path.exists():
            raise typer.BadParameter(f"Resume profile not found: {profile_path}")
        if not client.health():
            raise RuntimeError("Ollama is not reachable")
        profile = profile_path.read_text(encoding="utf-8")
    for job in jobs:
        fit = score_job(client, job, profile, s.remote_only) if score and client else None
        db.upsert_job(job, fit)
    console.print(f"Stored/refreshed {len(jobs)} job posting(s). No applications were submitted.")


@app.command("pull-model")
def pull_model() -> None:
    """Pull the configured/recommended Ollama model."""
    s = settings()
    if not shutil.which("ollama"):
        raise RuntimeError("Ollama CLI not found")
    subprocess.run(["ollama", "pull", s.selected_model], check=True)


@app.command("show-config")
def show_config() -> None:
    """Show non-secret effective configuration."""
    s = settings()
    safe = {
        "db_path": str(s.db_path),
        "output_dir": str(s.output_dir),
        "email_body_chars": s.triage_email_body_chars,
        "fetch_limit": s.triage_fetch_limit,
        "classify_batch_size": s.triage_classify_batch_size,
        "ollama_base_url": s.ollama_base_url,
        "ollama_model": s.selected_model,
        "ollama_num_ctx": s.ollama_num_ctx,
        "gmail_enabled": s.gmail_enabled,
        "outlook_enabled": s.outlook_enabled,
        "frontier_enabled": s.frontier_enabled,
        "remote_only": s.remote_only,
    }
    console.print_json(json.dumps(safe))
