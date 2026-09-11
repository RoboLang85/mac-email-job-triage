from __future__ import annotations

from imap_tools import AND, MailBox

from ..models import MessageRecord


class GmailImapConnector:
    name = "gmail"

    def __init__(self, user: str, app_password: str, folder: str = "INBOX"):
        if not user or not app_password:
            raise ValueError("Gmail user/app password are required when Gmail is enabled")
        self.user = user
        self.app_password = app_password
        self.folder = folder

    def fetch_unread(self, limit: int) -> list[MessageRecord]:
        records: list[MessageRecord] = []
        with MailBox("imap.gmail.com").login(
            self.user, self.app_password, initial_folder=self.folder
        ) as mailbox:
            for msg in mailbox.fetch(AND(seen=False), limit=limit, mark_seen=False):
                text = msg.text or ""
                records.append(
                    MessageRecord(
                        source=self.name,
                        external_id=str(msg.uid),
                        thread_id=None,
                        sender=msg.from_ or "",
                        subject=msg.subject or "",
                        received_at=msg.date,
                        body=text,
                    )
                )
        return records
