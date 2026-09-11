from __future__ import annotations

from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


def _safe_link(value: str | None) -> str | None:
    if not value:
        return None
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"}:
        return None
    # Strip query/fragment so tracking parameters are not copied into digests.
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def render_digest(rows, output_dir: Path, title: str = "Email Triage Digest") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    path = output_dir / f"digest_{stamp}.md"
    lines = [f"# {title}", ""]
    if not rows:
        lines.append("No classified messages matched the digest filter.")
    for row in rows:
        reply = "reply likely" if row["needs_reply"] else "no reply indicated"
        lines.extend(
            [
                f"## [{row['urgency']}/5] {row['subject'] or '(no subject)'}",
                f"- Source: {row['source']}",
                f"- From: {row['sender'] or 'unknown'}",
                f"- Category: {row['category']}",
                f"- Action: {reply}",
                f"- Summary: {row['summary']}",
            ]
        )
        link = _safe_link(row["web_link"])
        if link:
            lines.append(f"- Link: {link}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
