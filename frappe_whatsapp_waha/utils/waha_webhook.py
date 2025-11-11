"""Webhook handler for WAHA callbacks."""

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _

from frappe_whatsapp_waha.frappe_whatsapp_waha.doctype.whatsapp_settings.whatsapp_settings import (
    build_waha_webhook_url,
)


def _extract_payload() -> Any:
    """Return the incoming request payload parsed from the request body."""
    if frappe.request and frappe.request.data:
        try:
            raw = frappe.request.data
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            if raw:
                parsed = json.loads(raw)
                return parsed
        except (ValueError, TypeError):
            pass

    form_dict = getattr(frappe.local, "form_dict", None) or {}
    if isinstance(form_dict, dict):
        # frappe adds control keys like "cmd" that we do not need to store
        return {k: v for k, v in form_dict.items() if k != "cmd"}

    return {}


@frappe.whitelist(allow_guest=True)
def webhook(session: str | None = None) -> dict[str, Any]:
    """Receive events from a WAHA instance and persist them for processing."""
    settings = frappe.get_cached_doc("WhatsApp Settings")
    expected_session = (settings.session or "").strip()

    provided_session = session or frappe.form_dict.get("session")
    if isinstance(provided_session, str):
        provided_session = provided_session.strip()

    if expected_session:
        if not provided_session or provided_session != expected_session:
            frappe.throw(_("Invalid WAHA session"), frappe.PermissionError)

    payload = _extract_payload()

    frappe.get_doc(
        {
            "doctype": "WhatsApp Notification Log",
            "template": "WAHA Webhook",
            "meta_data": frappe.as_json(payload),
        }
    ).insert(ignore_permissions=True)

    return {"status": "ok"}


@frappe.whitelist()
def get_waha_webhook_url(session: str | None = None) -> str:
    """Return the webhook URL that WAHA should be configured to call."""
    if session is None:
        settings = frappe.get_cached_doc("WhatsApp Settings")
        session = settings.session

    return build_waha_webhook_url(session)
