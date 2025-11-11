"""Installation helpers for frappe_whatsapp_waha."""

from __future__ import annotations

import frappe

MODULE_NAME = "Frappe WhatsApp WAHA"
LEGACY_MODULE_NAMES = ("Frappe Whatsapp",)


def before_install() -> None:
    """Ensure duplicate Module Def records do not block installation.

    Older releases of the app registered the module as "Frappe Whatsapp".
    Additionally, partial installs may leave behind a stale Module Def with
    the desired name. Frappe's installation routine attempts to insert a new
    Module Def for each entry in ``modules.txt`` and aborts if a record with
    the same primary key already exists. We proactively remove any legacy or
    duplicate Module Def rows so that the automatic creation step succeeds.
    """

    # Remove any Module Def rows that would collide with the module declared
    # in modules.txt. This keeps installation idempotent even if a previous
    # attempt partially populated the database.
    frappe.db.delete("Module Def", {"name": MODULE_NAME})

    for legacy_name in LEGACY_MODULE_NAMES:
        frappe.db.delete("Module Def", {"name": legacy_name})
