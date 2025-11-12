"""Public API for sending WhatsApp messages through WAHA."""

from __future__ import annotations

import json
from typing import Iterable

import frappe
from frappe import _


def _serialise_parameters(parameters: Iterable[object] | None) -> str | None:
    """Return the JSON encoded payload used for template parameters."""

    if not parameters:
        return None

    serialised = {str(idx): value for idx, value in enumerate(parameters, start=1)}
    return json.dumps(serialised)


def _build_base_doc(to: str, *, message: str | None, content_type: str) -> dict[str, object]:
    if not to:
        frappe.throw(_("Recipient is required"))

    return {
        "doctype": "WhatsApp Message",
        "type": "Outgoing",
        "to": to,
        "message": message or "",
        "message_type": "Manual",
        "content_type": content_type,
    }


@frappe.whitelist()
def send_message(
    *,
    to: str,
    message: str | None = None,
    template: str | None = None,
    parameters: list[object] | tuple[object, ...] | None = None,
    media_url: str | None = None,
    content_type: str | None = None,
    reply_to: str | None = None,
    reaction: str | None = None,
) -> dict[str, object]:
    """Send a WhatsApp message using the configured WAHA instance."""

    final_content_type = content_type or "text"
    doc_fields = _build_base_doc(to, message=message or reaction, content_type=final_content_type)

    if reaction:
        doc_fields["content_type"] = "reaction"
        doc_fields["message"] = reaction
        if reply_to:
            doc_fields["reply_to_message_id"] = reply_to
            doc_fields["is_reply"] = 1
    elif template:
        doc_fields["message_type"] = "Template"
        doc_fields["template"] = template
        serialised = _serialise_parameters(parameters)
        if serialised:
            doc_fields["body_param"] = serialised
    else:
        doc_fields["message"] = message or ""

    if media_url:
        doc_fields["attach"] = media_url
        if final_content_type == "text":
            doc_fields["content_type"] = "image"

    if reply_to and not doc_fields.get("reply_to_message_id"):
        doc_fields["reply_to_message_id"] = reply_to
        doc_fields["is_reply"] = 1

    doc = frappe.get_doc(doc_fields)
    doc.insert(ignore_permissions=True)

    return {"name": doc.name, "message_id": doc.message_id, "status": doc.status}


def send_whatsapp_message(**kwargs) -> dict[str, object]:
    """Backward compatible helper referenced in the documentation."""

    return send_message(**kwargs)


@frappe.whitelist()
def get_message_status(message_id: str) -> dict[str, object]:
    """Return the status of a previously sent message."""

    if not message_id:
        frappe.throw(_("message_id is required"))

    doc_name = frappe.db.get_value("WhatsApp Message", {"message_id": message_id}, "name")
    if not doc_name:
        frappe.throw(_("Message not found"))

    doc = frappe.get_doc("WhatsApp Message", doc_name)
    return {"name": doc.name, "status": doc.status, "message_id": doc.message_id}
