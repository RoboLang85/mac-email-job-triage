from __future__ import annotations

from typing import Protocol

from ..models import MessageRecord


class MessageConnector(Protocol):
    name: str

    def fetch_unread(self, limit: int) -> list[MessageRecord]: ...
