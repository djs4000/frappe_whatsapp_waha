const INTL_TEL_INPUT_CDN = "https://cdn.jsdelivr.net/npm/intl-tel-input@25.12.5/build/js/intlTelInput.min.js";
const INTL_TEL_INPUT_UTILS_CDN = "https://cdn.jsdelivr.net/npm/intl-tel-input@25.12.5/build/js/utils.js";

frappe.ui.form.ControlIntlTelInput = class ControlIntlTelInput extends frappe.ui.form.ControlData {
    static input_type = "tel";

    make_input() {
        super.make_input();
        this.input?.setAttribute("type", "tel");
        this.input?.setAttribute("autocomplete", "tel");
        this.input?.setAttribute("placeholder", this.df.placeholder || frappe._("Enter phone number"));

        this._ensure_plugin();
    }

    _ensure_plugin() {
        if (typeof window.intlTelInput === "function") {
            this._init_plugin();
            return;
        }

        if (!this._intlLoader) {
            this._intlLoader = frappe
                .require([INTL_TEL_INPUT_CDN])
                .catch((error) => {
                    console.error("Failed to load intl-tel-input", error);
                });
        }

        if (this._intlLoader) {
            this._intlLoader.then(() => {
                if (typeof window.intlTelInput === "function") {
                    this._init_plugin();
                }
            });
        }
    }

    _init_plugin() {
        if (this.iti || typeof window.intlTelInput !== "function") {
            return;
        }

        const preferred = (this.df.preferred_countries || "us,in")
            .split(",")
            .map((code) => code.trim().toLowerCase())
            .filter(Boolean);

        const initOptions = {
            preferredCountries: preferred.length ? preferred : ["us", "in"],
            initialCountry: (this.df.default_country || "auto").toLowerCase(),
            separateDialCode: true,
            strictMode: true,
            validationNumberTypes: ["FIXED_LINE_OR_MOBILE"],
            loadUtils: () => import(INTL_TEL_INPUT_UTILS_CDN),
        };

        this.iti = window.intlTelInput(this.input, initOptions);

        if (this.value) {
            this.iti.setNumber(this.value);
        }

        this.input.addEventListener("blur", () => {
            if (this.frm && this.df.reqd && !this.get_input_value()) {
                this._toggle_error(true);
                return;
            }
            this._toggle_error(!this.is_valid());
        });
    }

    is_valid() {
        if (!this.iti) {
            return (this.get_input_value() || "").trim().length > 0;
        }
        if (!this.get_input_value()) {
            return true;
        }
        return this.iti.isValidNumber();
    }

    get_input_value() {
        if (this.iti) {
            return this.iti.getNumber();
        }
        return super.get_input_value();
    }

    set_formatted_input(value) {
        super.set_formatted_input(value);
        if (this.iti) {
            this.iti.setNumber(value);
        }
    }

    parse(value) {
        if (!value && this.iti) {
            this.iti.setNumber("");
        }
        return super.parse(value);
    }

    validate(value) {
        if (!value) {
            return value;
        }
        if (!this.is_valid()) {
            frappe.throw({
                message: frappe._("Please enter a valid international phone number."),
                title: frappe._("Invalid Phone Number")
            });
        }
        return this.get_input_value();
    }

    _toggle_error(state) {
        if (!this.input) {
            return;
        }
        this.input.classList.toggle("iti__input--invalid", Boolean(state));
        if (this.input.parentElement?.classList.contains("iti")) {
            this.input.parentElement.classList.toggle("iti--invalid", Boolean(state));
        }
        if (state) {
            this.input.setAttribute("aria-invalid", "true");
        } else {
            this.input.removeAttribute("aria-invalid");
        }
    }
};

frappe.ui.form.control_map = Object.assign({}, frappe.ui.form.control_map, {
    "Intl Tel Input": "IntlTelInput",
});
