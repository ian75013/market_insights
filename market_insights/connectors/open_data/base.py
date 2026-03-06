from __future__ import annotations

from dataclasses import dataclass
import httpx


@dataclass
class FetchResult:
    provider: str
    payload: list[dict]
    used_network: bool
    fallback_used: bool = False


class BaseHTTPConnector:
    provider_name = "base"

    def __init__(self, use_network: bool = False, timeout: float = 20.0) -> None:
        self.use_network = use_network
        self.timeout = timeout

    def get_json(self, url: str) -> dict | list:
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()

    def get_text(self, url: str) -> str:
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.text
