"""Webhook handler for WAHA callbacks."""

from __future__ import annotations

import json
from typing import Any, Iterable

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


def _normalise_phone(jid: str | None) -> str | None:
    if not isinstance(jid, str) or not jid:
        return None

    number = jid
    if "@" in number:
        number = number.split("@", 1)[0]

    if number.startswith("+"):
        number = number[1:]

    return number


def _unwrap_layers(message: dict[str, Any]) -> dict[str, Any]:
    current = message
    while True:
        if not isinstance(current, dict):
            return {}

        if "message" in current and isinstance(current["message"], dict):
            # payload already points to the inner message
            current = current["message"]
            continue

        if "ephemeralMessage" in current:
            current = current.get("ephemeralMessage", {}).get("message", {})
            continue

        if "viewOnceMessage" in current:
            current = current.get("viewOnceMessage", {}).get("message", {})
            continue

        if "documentWithCaptionMessage" in current:
            current = current.get("documentWithCaptionMessage", {}).get("message", {})
            continue

        return current if isinstance(current, dict) else {}


def _find_context_info(message: dict[str, Any]) -> dict[str, Any]:
    stack: list[dict[str, Any]] = [message]
    while stack:
        current = stack.pop()
        if not isinstance(current, dict):
            continue
        context = current.get("contextInfo")
        if isinstance(context, dict):
            return context
        stack.extend(value for value in current.values() if isinstance(value, dict))
    return {}


def _extract_message_text(message: dict[str, Any]) -> dict[str, Any] | None:
    payload = _unwrap_layers(message)
    if not payload:
        return None

    result: dict[str, Any] = {"content_type": "text", "message": ""}

    if "conversation" in payload:
        result["message"] = payload.get("conversation") or ""
        return result

    if "extendedTextMessage" in payload:
        ext = payload["extendedTextMessage"]
        result["message"] = ext.get("text") or ""
        context = _find_context_info(ext)
        if context:
            stanza = context.get("stanzaId")
            if stanza:
                result["reply_to"] = stanza
                result["is_reply"] = True
        return result

    if "imageMessage" in payload:
        image = payload["imageMessage"]
        result.update({
            "content_type": "image",
            "message": image.get("caption") or "",
            "attachment": image.get("url") or image.get("directPath"),
        })
        context = _find_context_info(image)
        if context:
            stanza = context.get("stanzaId")
            if stanza:
                result["reply_to"] = stanza
                result["is_reply"] = True
        return result

    if "videoMessage" in payload:
        video = payload["videoMessage"]
        result.update({
            "content_type": "video",
            "message": video.get("caption") or "",
            "attachment": video.get("url") or video.get("directPath"),
        })
        return result

    if "audioMessage" in payload:
        audio = payload["audioMessage"]
        result.update({"content_type": "audio", "attachment": audio.get("url") or audio.get("directPath")})
        return result

    if "documentMessage" in payload:
        document = payload["documentMessage"]
        file_name = document.get("fileName")
        result.update(
            {
                "content_type": "document",
                "message": document.get("caption") or file_name or "",
                "attachment": document.get("url") or document.get("directPath"),
            }
        )
        return result

    if "stickerMessage" in payload:
        sticker = payload["stickerMessage"]
        result.update({"content_type": "document", "message": sticker.get("fileEncSha256") or "Sticker"})
        return result

    if "reactionMessage" in payload:
        reaction = payload["reactionMessage"]
        result.update(
            {
                "content_type": "reaction",
                "message": reaction.get("text") or reaction.get("emoji") or "",
                "reply_to": (reaction.get("key") or {}).get("id"),
                "is_reply": True,
            }
        )
        return result

    if "buttonsResponseMessage" in payload:
        button = payload["buttonsResponseMessage"]
        result.update({
            "content_type": "button",
            "message": button.get("selectedDisplayText") or button.get("selectedButtonId") or "",
        })
        context = _find_context_info(button)
        if context:
            stanza = context.get("stanzaId")
            if stanza:
                result["reply_to"] = stanza
                result["is_reply"] = True
        return result

    if "templateButtonReplyMessage" in payload:
        template_reply = payload["templateButtonReplyMessage"]
        result.update(
            {
                "content_type": "button",
                "message": template_reply.get("selectedDisplayText")
                or template_reply.get("selectedId")
                or "",
            }
        )
        return result

    if "listResponseMessage" in payload:
        response = payload["listResponseMessage"]
        result.update(
            {
                "content_type": "button",
                "message": (response.get("title") or response.get("singleSelectReply", {}).get("title") or ""),
            }
        )
        return result

    if "interactiveResponseMessage" in payload:
        interactive = payload["interactiveResponseMessage"]
        native = interactive.get("nativeFlowResponseMessage", {})
        params = native.get("paramsJson") or native.get("responseJson") or native.get("serviceResult")
        if isinstance(params, str):
            message_value = params
        else:
            message_value = frappe.as_json(params or native)
        result.update({"content_type": "flow", "message": message_value})
        return result

    if "locationMessage" in payload:
        location = payload["locationMessage"]
        lat = location.get("degreesLatitude")
        lng = location.get("degreesLongitude")
        name = location.get("name") or location.get("address") or "Location"
        coords = f"{lat},{lng}" if lat is not None and lng is not None else ""
        result.update({"content_type": "location", "message": name, "extra": coords})
        return result

    if "contactMessage" in payload:
        contact = payload["contactMessage"].get("displayName") or "Contact"
        result.update({"content_type": "contact", "message": contact})
        return result

    if "contactsArrayMessage" in payload:
        contacts = payload["contactsArrayMessage"].get("contacts", [])
        if contacts:
            display = contacts[0].get("displayName") or contacts[0].get("vcard") or "Contact"
            result.update({"content_type": "contact", "message": display})
            return result

    return None


def _create_incoming_message(message: dict[str, Any], push_name: str | None = None) -> None:
    key = message.get("key") or {}
    if key.get("fromMe"):
        return

    message_id = key.get("id")
    if not message_id:
        return

    if frappe.db.exists("WhatsApp Message", {"message_id": message_id}):
        return

    sender = _normalise_phone(key.get("participant") or key.get("remoteJid"))
    if not sender:
        return

    parsed = _extract_message_text(message)
    if not parsed:
        return

    doc = {
        "doctype": "WhatsApp Message",
        "type": "Incoming",
        "from": sender,
        "message_id": message_id,
        "message": parsed.get("message") or parsed.get("extra") or "",
        "content_type": parsed.get("content_type") or "text",
        "profile_name": push_name or message.get("pushName"),
    }

    if parsed.get("reply_to"):
        doc["reply_to_message_id"] = parsed["reply_to"]
        doc["is_reply"] = 1
    if parsed.get("extra") and parsed.get("content_type") == "location":
        doc["message"] = f"{doc['message']} ({parsed['extra']})".strip()

    inserted = frappe.get_doc(doc).insert(ignore_permissions=True)

    attachment = parsed.get("attachment")
    if attachment:
        inserted.attach = attachment
        inserted.save(ignore_permissions=True)


def _handle_messages_upsert(payload: dict[str, Any]) -> None:
    messages: Iterable[Any]
    if isinstance(payload, dict):
        messages = payload.get("messages") or payload.get("data") or []
    elif isinstance(payload, list):
        messages = payload
    else:
        messages = []

    for message in messages:
        if isinstance(message, dict):
            _create_incoming_message(message, push_name=message.get("pushName"))


def _handle_messages_update(payload: dict[str, Any]) -> None:
    updates: Iterable[Any]
    if isinstance(payload, dict):
        updates = payload.get("messages") or payload.get("data") or payload.get("updates") or []
    elif isinstance(payload, list):
        updates = payload
    else:
        updates = []

    for update in updates:
        if not isinstance(update, dict):
            continue
        key = update.get("key") or {}
        message_id = key.get("id") or update.get("id")
        if not message_id:
            continue

        status = (update.get("update") or {}).get("status") or update.get("status")
        if not status:
            continue

        name = frappe.db.get_value("WhatsApp Message", {"message_id": message_id}, "name")
        if not name:
            continue

        doc = frappe.get_doc("WhatsApp Message", name)
        doc.status = status
        doc.save(ignore_permissions=True)


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

    event = (payload.get("event") or payload.get("type") or "").lower()
    data = payload.get("data") if isinstance(payload, dict) else {}

    if event == "messages.upsert":
        _handle_messages_upsert(data or payload)
    elif event == "messages.update":
        _handle_messages_update(data or payload)
    elif isinstance(payload, dict) and payload.get("messages"):
        _handle_messages_upsert(payload)

    return {"status": "ok"}


@frappe.whitelist()
def get_waha_webhook_url(session: str | None = None) -> str:
    """Return the webhook URL that WAHA should be configured to call."""
    if session is None:
        settings = frappe.get_cached_doc("WhatsApp Settings")
        session = settings.session

    return build_waha_webhook_url(session)
