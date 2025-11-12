"""WhatsApp message handling for WAHA integration."""

from __future__ import annotations

import json
from typing import Any, Iterable

import frappe
from frappe.model.document import Document

from frappe_whatsapp_waha.frappe_whatsapp_waha.utils.waha_client import (
    WahaAPIError,
    WahaClient,
)


class WhatsAppMessage(Document):
    """Send WhatsApp messages via the configured WAHA instance."""

    def before_insert(self):
        """Send the message before the document is saved."""

        if self.type != "Outgoing":
            return

        if not self.message_type:
            self.message_type = "Manual"

        try:
            if self.message_type == "Template" and not self.message_id:
                self._send_template_message()
            else:
                self._send_standard_message()
            self.status = "Success"
        except WahaAPIError as exc:
            self.status = "Failed"
            self._log_api_error("Message", exc.payload)
            frappe.throw(f"Failed to send message: {exc}")
        except Exception:
            self.status = "Failed"
            raise

    # ------------------------------------------------------------------
    # Message preparation helpers

    def _send_standard_message(self) -> None:
        client = WahaClient.from_settings()
        recipient = self.format_number(self.to)
        message_body = self.message or ""

        if self.content_type == "reaction":
            if not self.reply_to_message_id:
                frappe.throw("A reply_to_message_id is required to send reactions")
            response = client.send_reaction(recipient, self.reply_to_message_id, message_body)
        elif self.content_type in {"document", "image", "video", "audio"}:
            link = self._prepare_attachment_link(self.attach)
            if not link:
                frappe.throw("Attachment link is required for media messages")
            response = client.send_media_from_url(recipient, link, caption=message_body or None)
        else:
            response = client.send_text(recipient, message_body, preview_url=True)

        self.message_id = response.message_id()
        self._log_api_success("Message", response.data)

    def _send_template_message(self) -> None:
        template = frappe.get_doc("WhatsApp Templates", self.template)
        parameters = self._collect_template_parameters(template)

        if parameters:
            self.template_parameters = json.dumps(parameters)

        message_segments: list[str] = []

        if template.header_type == "TEXT" and template.header:
            message_segments.append(self._render_template_text(template.header, parameters))

        message_segments.append(self._render_template_text(template.template, parameters))

        if template.footer:
            message_segments.append(template.footer)

        media_link = self._get_template_media_link(template)
        if media_link:
            self.content_type = "image" if template.header_type == "IMAGE" else "document"
        else:
            self.content_type = "text"

        message = "\n\n".join(filter(None, message_segments))
        self.notify(message=message, content_type=self.content_type, media_link=media_link)

    # ------------------------------------------------------------------
    # WAHA interaction

    def notify(self, *, message: str, content_type: str = "text", media_link: str | None = None) -> None:
        client = WahaClient.from_settings()
        recipient = self.format_number(self.to)

        if content_type == "reaction":
            if not self.reply_to_message_id:
                frappe.throw("Cannot send a reaction without a reference message")
            response = client.send_reaction(recipient, self.reply_to_message_id, message)
        elif media_link:
            response = client.send_media_from_url(recipient, media_link, caption=message or None)
        else:
            response = client.send_text(recipient, message, preview_url=True)

        self.message_id = response.message_id()
        self._log_api_success("Message", response.data)

    # ------------------------------------------------------------------
    # Utilities

    def format_number(self, number: str) -> str:
        """Remove leading + signs from numbers."""

        if number.startswith("+"):
            return number[1:]
        return number

    @frappe.whitelist()
    def send_read_receipt(self):
        frappe.throw("Marking messages as read is not supported with the WAHA integration yet.")

    def _prepare_attachment_link(self, attach: str | None) -> str | None:
        if not attach:
            return None
        if attach.startswith("http"):
            return attach
        return f"{frappe.utils.get_url()}/{attach.lstrip('/')}"

    def _collect_template_parameters(self, template) -> list[Any]:
        if not template.sample_values:
            return []

        field_names = template.field_names.split(",") if template.field_names else template.sample_values.split(",")
        values: list[Any] = []

        if self.body_param is not None:
            params = list(json.loads(self.body_param).values())
            values.extend(params)
        elif getattr(self.flags, "custom_ref_doc", None):
            custom_values = self.flags.custom_ref_doc
            for field_name in field_names:
                values.append(custom_values.get(field_name.strip()))
        else:
            ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
            for field_name in field_names:
                values.append(ref_doc.get_formatted(field_name.strip()))

        return values

    def _render_template_text(self, template_text: str, parameters: Iterable[Any]) -> str:
        text = template_text or ""
        for idx, value in enumerate(parameters, start=1):
            text = text.replace(f"{{{{{idx}}}}}", frappe.utils.cstr(value))
        return text

    def _get_template_media_link(self, template) -> str | None:
        if template.header_type == "IMAGE":
            if self.attach:
                return self._prepare_attachment_link(self.attach)
            if template.sample:
                return self._prepare_attachment_link(template.sample)
        if template.header_type == "DOCUMENT" and self.attach:
            return self._prepare_attachment_link(self.attach)
        return None

    def _log_api_error(self, template: str, payload: dict[str, Any]):
        frappe.get_doc(
            {
                "doctype": "WhatsApp Notification Log",
                "template": template,
                "meta_data": frappe.as_json(payload or {}),
            }
        ).insert(ignore_permissions=True)

    def _log_api_success(self, template: str, payload: dict[str, Any]):
        frappe.get_doc(
            {
                "doctype": "WhatsApp Notification Log",
                "template": template,
                "meta_data": frappe.as_json(payload or {}),
            }
        ).insert(ignore_permissions=True)


def on_doctype_update():
    frappe.db.add_index("WhatsApp Message", ["reference_doctype", "reference_name"])


@frappe.whitelist()
def send_template(to, reference_doctype, reference_name, template):
    doc = frappe.get_doc(
        {
            "doctype": "WhatsApp Message",
            "to": to,
            "type": "Outgoing",
            "message_type": "Template",
            "reference_doctype": reference_doctype,
            "reference_name": reference_name,
            "content_type": "text",
            "template": template,
        }
    )
    doc.insert(ignore_permissions=True)
