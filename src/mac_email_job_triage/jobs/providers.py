from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx

from ..models import JobRecord


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=UTC)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def fetch_greenhouse(company: str, board: str) -> list[JobRecord]:
    response = httpx.get(
        f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs",
        params={"content": "true"},
        timeout=30,
    )
    response.raise_for_status()
    jobs = []
    for item in response.json().get("jobs", []):
        jobs.append(
            JobRecord(
                provider="greenhouse",
                external_id=str(item["id"]),
                company=company,
                title=item.get("title") or "",
                location=((item.get("location") or {}).get("name")) or "",
                description=item.get("content") or "",
                apply_url=item.get("absolute_url") or "",
                published_at=None,
            )
        )
    return jobs


def fetch_lever(company: str, board: str) -> list[JobRecord]:
    response = httpx.get(
        f"https://api.lever.co/v0/postings/{board}", params={"mode": "json"}, timeout=30
    )
    response.raise_for_status()
    jobs = []
    for item in response.json():
        categories = item.get("categories") or {}
        workplace = item.get("workplaceType")
        description_parts = [item.get("descriptionPlain") or ""]
        for block in item.get("lists") or []:
            description_parts.append(block.get("text") or "")
            content = block.get("content") or ""
            description_parts.append(content if isinstance(content, str) else " ".join(content))
        jobs.append(
            JobRecord(
                provider="lever",
                external_id=str(item["id"]),
                company=company,
                title=item.get("text") or "",
                location=categories.get("location") or "",
                description="\n".join(x for x in description_parts if x),
                apply_url=item.get("hostedUrl") or item.get("applyUrl") or "",
                published_at=_parse_dt(item.get("createdAt")),
                workplace_type=workplace,
            )
        )
    return jobs


def fetch_ashby(company: str, board: str) -> list[JobRecord]:
    response = httpx.get(
        f"https://api.ashbyhq.com/posting-api/job-board/{board}",
        params={"includeCompensation": "true"},
        timeout=30,
    )
    response.raise_for_status()
    jobs = []
    for item in response.json().get("jobs", []):
        comp = item.get("compensation")
        jobs.append(
            JobRecord(
                provider="ashby",
                external_id=str(item.get("jobUrl") or item.get("applyUrl") or item["title"]),
                company=company,
                title=item.get("title") or "",
                location=item.get("location") or "",
                description=item.get("descriptionPlain") or item.get("descriptionHtml") or "",
                apply_url=item.get("applyUrl") or item.get("jobUrl") or "",
                published_at=_parse_dt(item.get("publishedAt")),
                workplace_type=item.get("workplaceType"),
                compensation=json.dumps(comp, ensure_ascii=False) if comp else None,
            )
        )
    return jobs


def fetch_configured_boards(path: Path) -> list[JobRecord]:
    if not path.exists():
        raise FileNotFoundError(
            f"Job board configuration not found: {path}. Copy job_boards.example.json first."
        )
    config = json.loads(path.read_text(encoding="utf-8"))
    jobs: list[JobRecord] = []
    for board in config:
        if not board.get("enabled", True):
            continue
        provider = board["provider"].lower()
        company = board["company"]
        token = board["board"]
        if provider == "greenhouse":
            jobs.extend(fetch_greenhouse(company, token))
        elif provider == "lever":
            jobs.extend(fetch_lever(company, token))
        elif provider == "ashby":
            jobs.extend(fetch_ashby(company, token))
        else:
            raise ValueError(f"Unsupported job provider: {provider}")
    return jobs
