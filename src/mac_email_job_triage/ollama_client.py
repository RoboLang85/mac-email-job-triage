from __future__ import annotations

import json

import httpx
from pydantic import BaseModel


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: int = 300,
        keep_alive: str = "10m",
        num_ctx: int = 8192,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.keep_alive = keep_alive
        self.num_ctx = num_ctx

    def health(self) -> bool:
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            return True
        except httpx.HTTPError:
            return False

    def structured(self, system: str, user: str, response_model: type[BaseModel]) -> BaseModel:
        schema = response_model.model_json_schema()
        grounded_user = (
            user
            + "\n\nReturn data that exactly matches this JSON schema:\n"
            + json.dumps(schema, separators=(",", ":"))
        )
        payload = {
            "model": self.model,
            "stream": False,
            "keep_alive": self.keep_alive,
            "format": schema,
            "options": {"temperature": 0, "num_ctx": self.num_ctx},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": grounded_user},
            ],
        }
        response = httpx.post(
            f"{self.base_url}/api/chat", json=payload, timeout=self.timeout_seconds
        )
        response.raise_for_status()
        content = response.json()["message"]["content"]
        return response_model.model_validate_json(content)
