"""Utilities for storing WhatsApp templates locally for WAHA."""

from __future__ import annotations

import json

import frappe
from frappe.model.document import Document


class WhatsAppTemplates(Document):
    """Store template metadata that will be rendered locally before sending."""

    def validate(self):
        if not self.language_code or self.has_value_changed("language"):
            lang_code = frappe.db.get_value("Language", self.language) or "en"
            self.language_code = lang_code.replace("-", "_")

        if self.sample_values and not self.field_names:
            # Keep field_names in sync when only sample values are provided.
            try:
                values = json.loads(self.sample_values)
                if isinstance(values, dict):
                    self.field_names = ",".join(values.keys())
            except (TypeError, json.JSONDecodeError):
                pass

    def after_insert(self):
        if self.template_name and not self.actual_name:
            self.actual_name = self.template_name.lower().replace(" ", "_")
            self.db_set("actual_name", self.actual_name)

    def update_template(self):
        # Templates are rendered locally; there is nothing to sync with WAHA.
        return

    def on_trash(self):
        # Nothing to clean up remotely.
        return


@frappe.whitelist()
def fetch():
    frappe.throw("Fetching templates from Meta is not supported when using the WAHA integration.")
