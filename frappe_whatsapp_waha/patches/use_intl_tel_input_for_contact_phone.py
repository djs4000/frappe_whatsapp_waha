"""Switch Contact Phone.phone to the Intl Tel Input fieldtype."""

from __future__ import annotations

import frappe

FIELD_NAME = "phone"
DOCTYPE = "Contact Phone"
FIELD_TYPE = "Intl Tel Input"


def execute() -> None:
    if not frappe.db.exists("DocField", {"parent": DOCTYPE, "fieldname": FIELD_NAME}):
        return

    docfield_name, current_type = frappe.db.get_value(
        "DocField",
        {"parent": DOCTYPE, "fieldname": FIELD_NAME},
        ["name", "fieldtype"],
    )

    if not docfield_name or current_type == FIELD_TYPE:
        return

    frappe.db.set_value("DocField", docfield_name, "fieldtype", FIELD_TYPE)
    frappe.clear_cache(doctype=DOCTYPE)
