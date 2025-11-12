frappe.provide('frappe_whatsapp_waha.contact');

(() => {
    const INTL_TEL_INPUT_CSS = 'https://cdnjs.cloudflare.com/ajax/libs/intl-tel-input/17.0.19/css/intlTelInput.min.css';
    const INTL_TEL_INPUT_JS = 'https://cdnjs.cloudflare.com/ajax/libs/intl-tel-input/17.0.19/js/intlTelInput.min.js';
    const INTL_TEL_INPUT_UTILS = 'https://cdnjs.cloudflare.com/ajax/libs/intl-tel-input/17.0.19/js/utils.js';
    const NEW_OPTION_VALUE = '__new';

    let intlTelInputLoader;

    function loadIntlTelInput() {
        if (!intlTelInputLoader) {
            intlTelInputLoader = new Promise((resolve, reject) => {
                try {
                    frappe.dom.load_css(INTL_TEL_INPUT_CSS);
                } catch (error) {
                    console.warn('Unable to load intl-tel-input CSS', error); // eslint-disable-line no-console
                }

                frappe.require([INTL_TEL_INPUT_JS], () => {
                    if (window.intlTelInput) {
                        resolve(window.intlTelInput);
                    } else {
                        reject(new Error('intl-tel-input failed to load.'));
                    }
                });
            });
        }

        return intlTelInputLoader;
    }

    function makePhoneTableReadOnly(frm) {
        const phoneField = frm.get_field('phone_nos');
        if (!phoneField || !phoneField.grid) {
            return;
        }

        const { grid } = phoneField;
        grid.cannot_add_rows = true;
        grid.cannot_delete_rows = true;
        grid.static_rows = true;

        if (grid.wrapper) {
            grid.wrapper.find('.grid-add-row').hide();
            grid.wrapper.find('.grid-remove-rows').hide();
        }

        if (grid.docfields) {
            grid.docfields.forEach((df) => {
                df.read_only = 1;
                df.in_place_edit = false;
            });
        }

        grid.refresh && grid.refresh();
    }

    function addPhoneManageButton(frm) {
        const phoneField = frm.get_field('phone_nos');
        if (!phoneField || !phoneField.grid || phoneField.grid.__phone_button_added) {
            return;
        }

        phoneField.grid.add_custom_button(__('Add or Edit Phone Number'), () => {
            openPhoneDialog(frm);
        });
        phoneField.grid.__phone_button_added = true;
    }

    function buildExistingPhoneOptions(frm) {
        const options = [{ label: __('New Phone Number'), value: NEW_OPTION_VALUE }];
        (frm.doc.phone_nos || []).forEach((row) => {
            const label =
                row.phone ||
                row.phone_number ||
                (typeof row.__str__ === 'function' ? row.__str__() : row.name);
            options.push({ label, value: row.name });
        });

        return options;
    }

    function getPhoneRow(frm, name) {
        return (frm.doc.phone_nos || []).find((row) => row.name === name);
    }

    function getDefaultCountryIso2(frm) {
        const countries =
            window.intlTelInputGlobals &&
            typeof window.intlTelInputGlobals.getCountryData === 'function'
                ? window.intlTelInputGlobals.getCountryData()
                : [];

        const candidates = [];

        if (frm && frm.doc) {
            if (frm.doc.country) {
                candidates.push(frm.doc.country);
            }

            (frm.doc.phone_nos || []).forEach((row) => {
                if (row.country) {
                    candidates.push(row.country);
                }
            });
        }

        if (frappe.boot && frappe.boot.sysdefaults && frappe.boot.sysdefaults.country) {
            candidates.push(frappe.boot.sysdefaults.country);
        }

        for (let i = 0; i < candidates.length; i += 1) {
            const candidate = candidates[i];
            if (typeof candidate === 'string') {
                const normalized = candidate.trim().toLowerCase();
                if (normalized) {
                    const direct = countries.find((country) => country.iso2 === normalized);
                    if (direct) {
                        return direct.iso2;
                    }

                    const byName = countries.find((country) => country.name.toLowerCase() === normalized);
                    if (byName) {
                        return byName.iso2;
                    }
                }
            }
        }

        return 'us';
    }

    function openPhoneDialog(frm) {
        const dialog = new frappe.ui.Dialog({
            title: __('Manage Phone Number'),
            fields: [
                {
                    label: __('Select Number'),
                    fieldname: 'existing_number',
                    fieldtype: 'Select',
                    options: buildExistingPhoneOptions(frm),
                    default: NEW_OPTION_VALUE,
                    reqd: 1,
                },
                {
                    label: __('Phone Number'),
                    fieldname: 'phone_number',
                    fieldtype: 'Data',
                    reqd: 1,
                },
            ],
            primary_action_label: __('Save'),
            primary_action(values) {
                const iti = dialog.__iti;

                const saveNumber = (formatted) => {
                    const selected = values.existing_number;
                    if (selected && selected !== NEW_OPTION_VALUE) {
                        const row = getPhoneRow(frm, selected);
                        if (row) {
                            frappe.model.set_value(row.doctype, row.name, 'phone', formatted);
                        }
                    } else {
                        const row = frm.add_child('phone_nos');
                        frappe.model.set_value(row.doctype, row.name, 'phone', formatted);
                    }

                    frm.refresh_field('phone_nos');
                    dialog.hide();
                };

                if (!iti) {
                    const manual = (values.phone_number || '').trim();
                    if (!manual) {
                        frappe.msgprint(__('Please enter a phone number.'));
                        return;
                    }

                    saveNumber(manual);
                    return;
                }

                const process = () => {
                    const isValid = iti.isValidNumber();
                    if (!isValid) {
                        frappe.msgprint({
                            title: __('Invalid Number'),
                            message: __('Please enter a valid phone number.'),
                            indicator: 'red',
                        });
                        return;
                    }

                    const formatted = window.intlTelInputUtils
                        ? iti.getNumber(window.intlTelInputUtils.numberFormat.E164)
                        : iti.getNumber();

                    if (!formatted) {
                        frappe.msgprint(__('Could not determine the formatted number.'));
                        return;
                    }

                    saveNumber(formatted);
                };

                if (iti.promise) {
                    iti.promise.then(process);
                } else {
                    process();
                }
            },
        });

        dialog.onhide = () => {
            if (dialog.__iti) {
                dialog.__iti.destroy();
                dialog.__iti = null;
            }
        };

        const existingField = dialog.get_field('existing_number');
        const phoneField = dialog.get_field('phone_number');

        if (!existingField.get_value()) {
            existingField.set_value(NEW_OPTION_VALUE);
        }

        const handleExistingChange = () => {
            const selected = existingField.get_value();
            if (selected && selected !== NEW_OPTION_VALUE) {
                const row = getPhoneRow(frm, selected);
                const phone = row && row.phone ? row.phone : '';
                phoneField.set_value(phone);
                if (dialog.__iti) {
                    dialog.__iti.setNumber(phone);
                }
            } else {
                phoneField.set_value('');
                if (dialog.__iti) {
                    dialog.__iti.setNumber('');
                }
            }
        };

        existingField.$input && existingField.$input.on('change', handleExistingChange);

        loadIntlTelInput()
            .then((intlTelInput) => {
                const input = phoneField.$input && phoneField.$input.get(0);
                if (!input) {
                    throw new Error('Phone input not found');
                }

                const defaultCountry = getDefaultCountryIso2(frm);

                dialog.__iti = intlTelInput(input, {
                    initialCountry: defaultCountry,
                    nationalMode: false,
                    utilsScript: INTL_TEL_INPUT_UTILS,
                });

                handleExistingChange();
            })
            .catch((error) => {
                console.error(error); // eslint-disable-line no-console
                frappe.msgprint({
                    title: __('Error'),
                    message: __('Failed to load phone input validation. You can still enter numbers manually.'),
                    indicator: 'orange',
                });
            });

        dialog.show();
    }

    frappe.ui.form.on('Contact', {
        refresh(frm) {
            makePhoneTableReadOnly(frm);
            addPhoneManageButton(frm);
        },
        onload_post_render(frm) {
            makePhoneTableReadOnly(frm);
            addPhoneManageButton(frm);
        },
    });
})();
