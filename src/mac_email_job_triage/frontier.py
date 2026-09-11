from __future__ import annotations

import httpx


def escalate_summary(
    *, base_url: str, api_key: str, model: str, subject: str, local_summary: str
) -> str:
    """Optional OpenAI-compatible escalation using only already-derived local metadata.

    Raw email bodies are deliberately NOT accepted by this function.
    """
    if not (base_url and api_key and model):
        raise ValueError("Frontier escalation is enabled but not fully configured")
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Review the local triage summary. Return a concise action recommendation.",
            },
            {"role": "user", "content": f"Subject: {subject}\nLocal summary: {local_summary}"},
        ],
        "temperature": 0,
    }
    response = httpx.post(
        base_url.rstrip("/") + "/chat/completions",
        json=payload,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()
