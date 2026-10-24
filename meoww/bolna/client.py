"""Thin client for the parts of the Bolna API that Meoww uses."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx

BASE_URL = "https://api.bolna.ai"


class BolnaError(Exception):
    """Bolna returned an error response, or is not configured."""


class BolnaClient:
    def __init__(self, api_key: Optional[str] = None, timeout: float = 180.0):
        api_key = api_key or os.environ.get("BOLNA_API_KEY")
        if not api_key:
            raise BolnaError("BOLNA_API_KEY is not set. Add it to .env.")
        self._http = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    def _request(self, method: str, path: str, **kwargs) -> Any:
        resp = self._http.request(method, path, **kwargs)
        if resp.status_code >= 400:
            raise BolnaError(f"{method} {path} -> {resp.status_code}: {resp.text[:500]}")
        return resp.json() if resp.content else None

    def list_dispositions(self, agent_id: str) -> List[Dict[str, Any]]:
        """Dispositions visible to this agent.

        Bolna replies with {"agent_dispositions": [...], "global_dispositions":
        [...]} - the agent's own plus any account-wide ones. Both are flattened
        here, since either kind occupying a name is a reason not to create it
        again. An older deployment returning a bare list still works.
        """
        resp = self._request("GET", "/dispositions/", params={"agent_id": agent_id})
        if isinstance(resp, list):
            return resp
        if not isinstance(resp, dict):
            return []
        found: List[Dict[str, Any]] = []
        for group in ("agent_dispositions", "global_dispositions"):
            found.extend(d for d in (resp.get(group) or []) if isinstance(d, dict))
        return found

    def bulk_create_dispositions(self, agent_id: str, dispositions: List[Dict[str, Any]]) -> List[str]:
        """Create several dispositions at once. Bolna does this atomically."""
        body = {"agent_id": agent_id, "dispositions": dispositions}
        return (self._request("POST", "/dispositions/bulk", json=body) or {}).get("ids", [])

    def update_disposition(self, disposition_id: str, fields: Dict[str, Any]) -> None:
        """Change an existing disposition's question, options or model."""
        self._request("PUT", f"/dispositions/{disposition_id}", json=fields)

    def test_dispositions(self, agent_id: str, transcript: str) -> Dict[str, Any]:
        """Run the agent's dispositions against a transcript. No call is made."""
        body = {"transcript": transcript}
        resp = self._request("POST", f"/v2/agent/{agent_id}/dispositions/test", json=body)
        return (resp or {}).get("extracted_data", {})

    def get_execution(self, execution_id: str) -> Dict[str, Any]:
        """A finished call: transcript, recording, and extracted_data."""
        return self._request("GET", f"/executions/{execution_id}")
