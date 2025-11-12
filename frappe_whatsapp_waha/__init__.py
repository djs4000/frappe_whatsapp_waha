
__version__ = '1.0.7'


def _register_intl_tel_fieldtype() -> None:
    """Expose the custom fieldtype to Frappe's metadata registry."""

    try:
        import frappe  # type: ignore
    except Exception:
        return

    fieldtype = "Intl Tel Input"

    try:
        from frappe.model import meta  # type: ignore
    except Exception:
        return

    data_fieldtypes = getattr(meta, "data_fieldtypes", None)
    if isinstance(data_fieldtypes, list) and fieldtype not in data_fieldtypes:
        data_fieldtypes.append(fieldtype)

    default_fieldtype_map = getattr(meta, "default_fieldtype_map", None)
    if isinstance(default_fieldtype_map, dict) and fieldtype not in default_fieldtype_map:
        default_fieldtype_map[fieldtype] = "Data"


_register_intl_tel_fieldtype()
