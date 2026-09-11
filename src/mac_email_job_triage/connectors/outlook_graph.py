from __future__ import annotations

import html
import re
from pathlib import Path

import httpx
import msal

from ..models import MessageRecord

GRAPH = "https://graph.microsoft.com/v1.0"


def _strip_html(value: str) -> str:
    value = re.sub(r"<script.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(value).split())


class OutlookGraphConnector:
    name = "outlook"

    def __init__(self, client_id: str, tenant_id: str, token_cache_path: Path, folder: str = "inbox"):
        if not client_id:
            raise ValueError("MS_CLIENT_ID is required when Outlook is enabled")
        self.client_id = client_id
        self.tenant_id = tenant_id or "consumers"
        self.token_cache_path = token_cache_path
        self.folder = folder

    def _token(self) -> str:
        self.token_cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache = msal.SerializableTokenCache()
        if self.token_cache_path.exists():
            cache.deserialize(self.token_cache_path.read_text(encoding="utf-8"))
        app = msal.PublicClientApplication(
            self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}",
            token_cache=cache,
        )
        scopes = ["Mail.Read"]
        result = None
        accounts = app.get_accounts()
        if accounts:
            result = app.acquire_token_silent(scopes, account=accounts[0])
        if not result:
            flow = app.initiate_device_flow(scopes=scopes)
            if "user_code" not in flow:
                raise RuntimeError(f"Could not initiate Microsoft device flow: {flow}")
            print(flow["message"])
            result = app.acquire_token_by_device_flow(flow)
        if cache.has_state_changed:
            self.token_cache_path.write_text(cache.serialize(), encoding="utf-8")
            self.token_cache_path.chmod(0o600)
        token = result.get("access_token") if result else None
        if not token:
            raise RuntimeError(f"Microsoft authentication failed: {result}")
        return token

    def fetch_unread(self, limit: int) -> list[MessageRecord]:
        token = self._token()
        url = f"{GRAPH}/me/mailFolders/{self.folder}/messages"
        params = {
            "$top": str(min(limit, 100)),
            "$filter": "isRead eq false",
            "$select": "id,conversationId,subject,from,receivedDateTime,body,bodyPreview,webLink",
        }
        response = httpx.get(
            url,
            params=params,
            headers={
                "Authorization": f"Bearer {token}",
                "Prefer": 'outlook.body-content-type="text"',
            },
            timeout=60,
        )
        response.raise_for_status()
        records: list[MessageRecord] = []
        items = response.json().get("value", [])
        items.sort(key=lambda item: item.get("receivedDateTime") or "", reverse=True)
        for item in items:
            sender = (((item.get("from") or {}).get("emailAddress") or {}).get("address")) or ""
            body = ((item.get("body") or {}).get("content")) or item.get("bodyPreview") or ""
            if ((item.get("body") or {}).get("contentType") or "").lower() == "html":
                body = _strip_html(body)
            records.append(
                MessageRecord(
                    source=self.name,
                    external_id=item["id"],
                    thread_id=item.get("conversationId"),
                    sender=sender,
                    subject=item.get("subject") or "",
                    received_at=item.get("receivedDateTime"),
                    body=body,
                    web_link=item.get("webLink"),
                )
            )
        return records
