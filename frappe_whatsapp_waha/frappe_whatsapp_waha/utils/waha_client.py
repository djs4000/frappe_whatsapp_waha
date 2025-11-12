"""Light-weight client for interacting with a WAHA instance."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

import requests

import frappe


class WahaAPIError(Exception):
    """Exception raised when a WAHA API request fails."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        payload: Any | None = None,
        url: str | None = None,
        method: str | None = None,
        params: dict[str, Any] | None = None,
        request_payload: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}
        self.url = url
        self.method = method
        self.params = params or {}
        self.request_payload = request_payload


@dataclass(slots=True)
class WahaResponse:
    """Container for WAHA responses."""

    data: dict[str, Any]

    def message_id(self) -> str | None:
        """Return the message identifier if the response contains one."""

        candidates = (
            "message_id",
            "messageId",
            "id",
            "key",
            "key_id",
        )

        for candidate in candidates:
            value = self.data.get(candidate)
            if isinstance(value, str) and value:
                return value

        # Some WAHA responses wrap data inside a nested dict
        if "messages" in self.data and isinstance(self.data["messages"], list):
            first = self.data["messages"][0]
            if isinstance(first, dict):
                return WahaResponse(first).message_id()

        return None


class WahaClient:
    """HTTP client used to talk to the configured WAHA instance."""

    def __init__(self, *, base_url: str, session: str | None, token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = (session or "").strip() or None
        self._token = token

    @classmethod
    def from_settings(cls) -> "WahaClient":
        """Build a client from the stored WhatsApp settings."""

        settings = frappe.get_cached_doc("WhatsApp Settings")
        token = settings.get_password("token")
        if not token:
            frappe.throw("WAHA API key is missing from WhatsApp Settings")

        if not settings.url:
            frappe.throw("WAHA Host URL is missing from WhatsApp Settings")

        return cls(base_url=settings.url, session=settings.session, token=token)

    # ---- request helpers -------------------------------------------------

    def _headers(self, *, json_body: bool = True) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self._token}"}
        if json_body:
            headers["Content-Type"] = "application/json"
        return headers

    def _request(self, method: str, path: str, *, json_payload: dict[str, Any] | None = None) -> WahaResponse:
        url = f"{self._base_url}/{path.lstrip('/')}"
        params = {"session": self._session} if self._session else None

        try:
            response = requests.request(
                method,
                url,
                params=params,
                headers=self._headers(json_body=json_payload is not None),
                json=json_payload,
                timeout=frappe.conf.get("waha_timeout", 30),
            )
        except requests.RequestException as exc:
            raise WahaAPIError(
                str(exc),
                url=url,
                method=method,
                params=params or {},
                request_payload=json_payload,
            ) from exc

        if response.ok:
            try:
                return WahaResponse(response.json() if response.content else {})
            except ValueError:
                # Non JSON response (e.g. empty string). Return empty payload.
                return WahaResponse({})

        payload: dict[str, Any]
        message: str

        try:
            payload = response.json()
            message = payload.get("error") or payload.get("message") or json.dumps(payload)
        except ValueError:
            payload = {"error": response.text}
            message = response.text or f"WAHA request failed with status {response.status_code}"

        raise WahaAPIError(
            message.strip(),
            status_code=response.status_code,
            payload=payload,
            url=response.url,
            method=method,
            params=params or {},
            request_payload=json_payload,
        )

    # ---- public API ------------------------------------------------------

    def send_text(self, phone: str, body: str, *, preview_url: bool = True) -> WahaResponse:
        payload = {"phone": phone, "body": body}
        if preview_url:
            payload["previewUrl"] = True
        return self._request("POST", "api/sendText", json_payload=payload)

    def send_media_from_url(self, phone: str, url: str, *, caption: str | None = None) -> WahaResponse:
        payload = {"phone": phone, "url": url}
        if caption:
            payload["caption"] = caption
            payload["body"] = caption
        return self._request("POST", "api/sendFileFromUrl", json_payload=payload)

    def send_reaction(self, phone: str, message_id: str, emoji: str) -> WahaResponse:
        payload = {"phone": phone, "messageId": message_id, "reaction": emoji}
        return self._request("POST", "api/sendReaction", json_payload=payload)

