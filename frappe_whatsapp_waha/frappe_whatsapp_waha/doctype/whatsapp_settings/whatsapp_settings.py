# Copyright (c) 2022, djs4000 and contributors
# For license information, please see license.txt

from urllib.parse import quote

from frappe.model.document import Document
from frappe.utils import get_url


def build_waha_webhook_url(session: str | None = None) -> str:
    """Return the fully-qualified webhook URL for WAHA callbacks."""
    path = "/api/method/frappe_whatsapp_waha.utils.waha_webhook.webhook"
    base_url = get_url(path)

    if session:
        return f"{base_url}?session={quote(session)}"

    return base_url


class WhatsAppSettings(Document):
    def validate(self):
        """Ensure derived fields stay in sync with user provided values."""
        self.waha_webhook_url = build_waha_webhook_url(self.session)
