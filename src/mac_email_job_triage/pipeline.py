from __future__ import annotations

from collections.abc import Iterable

from rich.console import Console

from .classifier import classify_batch
from .config import Settings
from .db import Database
from .models import MessageRecord, TriageDecision
from .ollama_client import OllamaClient

console = Console()


def chunks(items: list[MessageRecord], size: int) -> Iterable[list[MessageRecord]]:
    size = max(1, size)
    for start in range(0, len(items), size):
        yield items[start : start + size]


def run_pipeline(settings: Settings, connectors) -> tuple[int, int]:
    db = Database(settings.db_path)
    client = OllamaClient(
        settings.ollama_base_url,
        settings.selected_model,
        settings.ollama_timeout_seconds,
        settings.ollama_keep_alive,
        settings.ollama_num_ctx,
    )
    if not client.health():
        raise RuntimeError("Ollama is not reachable. Start Ollama before running triage.")

    fetched: list[MessageRecord] = []
    for connector in connectors:
        console.print(f"Fetching unread messages from [bold]{connector.name}[/bold]...")
        fetched.extend(connector.fetch_unread(settings.triage_fetch_limit))

    pending = [m for m in fetched if not db.has_triage(m.source, m.external_id)]
    console.print(f"Fetched {len(fetched)} message(s); {len(pending)} require local classification.")

    saved = 0
    for batch in chunks(pending, settings.triage_classify_batch_size):
        decisions = classify_batch(client, batch, settings.triage_email_body_chars)
        for msg in batch:
            decision = decisions.get(msg.external_id)
            if decision is None:
                decision = TriageDecision(
                    category="other",
                    needs_reply=False,
                    urgency=2,
                    summary="Local model did not return a valid decision for this message; review manually.",
                    confidence=0.0,
                )
            message_id = db.upsert_message(msg, (msg.body or "")[: settings.triage_email_body_chars])
            db.save_triage(message_id, decision, settings.selected_model)
            saved += 1
    return len(fetched), saved
