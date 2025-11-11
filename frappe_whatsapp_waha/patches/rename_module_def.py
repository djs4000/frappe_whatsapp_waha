"""Patch helpers for normalising the Module Def entry."""

from __future__ import annotations

import frappe

MODULE_NAME = "Frappe WhatsApp WAHA"
LEGACY_NAMES = (
    "Frappe Whatsapp",
    "Frappe WhatsApp",
)


def execute() -> None:
    """Ensure the Module Def record uses the canonical module name.

    Existing installations may still have the module registered under older
    names. We migrate those records to the desired "Frappe WhatsApp WAHA"
    entry so that DocTypes referencing the new module name remain valid.
    """

    if frappe.db.exists("Module Def", MODULE_NAME):
        return

    for legacy_name in LEGACY_NAMES:
        if not frappe.db.exists("Module Def", legacy_name):
            continue

        frappe.rename_doc(
            "Module Def",
            legacy_name,
            MODULE_NAME,
            force=True,
            ignore_permissions=True,
        )
        return

    # As a fallback, create the module definition so that metadata remains
    # consistent with modules.txt.
    frappe.get_doc(
        {
            "doctype": "Module Def",
            "module_name": MODULE_NAME,
            "app_name": "frappe_whatsapp_waha",
        }
    ).insert(ignore_permissions=True, ignore_if_duplicate=True)
