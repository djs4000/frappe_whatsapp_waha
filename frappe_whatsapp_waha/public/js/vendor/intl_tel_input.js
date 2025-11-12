(function (root, factory) {
    if (typeof define === "function" && define.amd) {
        define([], factory);
    } else if (typeof module === "object" && module.exports) {
        module.exports = factory();
    } else {
        const exports = factory();
        root.intlTelInput = exports.intlTelInput;
        root.intlTelInputGlobals = exports.intlTelInputGlobals;
    }
})(typeof window !== "undefined" ? window : this, function () {
    const COUNTRY_DATA = [
        { name: "Australia", iso2: "au", dialCode: "61" },
        { name: "Brazil", iso2: "br", dialCode: "55" },
        { name: "Canada", iso2: "ca", dialCode: "1" },
        { name: "France", iso2: "fr", dialCode: "33" },
        { name: "Germany", iso2: "de", dialCode: "49" },
        { name: "India", iso2: "in", dialCode: "91" },
        { name: "Japan", iso2: "jp", dialCode: "81" },
        { name: "South Africa", iso2: "za", dialCode: "27" },
        { name: "United Arab Emirates", iso2: "ae", dialCode: "971" },
        { name: "United Kingdom", iso2: "gb", dialCode: "44" },
        { name: "United States", iso2: "us", dialCode: "1" }
    ];

    const DEFAULT_OPTIONS = {
        initialCountry: "auto",
        preferredCountries: ["us", "in"],
        showDialCode: true,
        nationalMode: false,
        separateDialCode: true
    };

    const MIN_LENGTH = 4;
    const MAX_LENGTH = 15;

    function find_country(iso2) {
        return COUNTRY_DATA.find((country) => country.iso2 === iso2);
    }

    function build_select(countries, preferred, selectedIso) {
        const wrapper = document.createElement("div");
        wrapper.classList.add("iti__flag-container");

        const select = document.createElement("select");
        select.classList.add("iti__country-select");
        select.setAttribute("aria-label", "Select country");

        function append_option(country, group) {
            const option = document.createElement("option");
            option.value = country.iso2;
            option.textContent = `${country.name} (+${country.dialCode})`;
            if (country.iso2 === selectedIso) {
                option.selected = true;
            }
            group.appendChild(option);
        }

        if (preferred.length) {
            const preferredGroup = document.createElement("optgroup");
            preferredGroup.label = "Preferred";
            preferred
                .map((iso) => find_country(iso))
                .filter(Boolean)
                .forEach((country) => append_option(country, preferredGroup));
            if (preferredGroup.childNodes.length) {
                select.appendChild(preferredGroup);
            }
        }

        const othersGroup = document.createElement("optgroup");
        othersGroup.label = "All Countries";
        countries.forEach((country) => append_option(country, othersGroup));
        select.appendChild(othersGroup);

        wrapper.appendChild(select);

        const dialCode = document.createElement("span");
        dialCode.classList.add("iti__selected-dial-code");
        wrapper.appendChild(dialCode);

        return { wrapper, select, dialCode };
    }

    function IntlTelInput(input, options = {}) {
        if (!(input instanceof HTMLElement)) {
            throw new Error("intlTelInput requires an input element");
        }

        this.input = input;
        this.options = Object.assign({}, DEFAULT_OPTIONS, options);
        this.countries = COUNTRY_DATA.slice();
        this._build();
    }

    IntlTelInput.prototype._build = function () {
        this.input.classList.add("iti__input");
        this.input.setAttribute("autocomplete", "tel");
        this.input.setAttribute("inputmode", "tel");

        let selected = null;
        if (this.options.initialCountry && this.options.initialCountry !== "auto") {
            selected = find_country(this.options.initialCountry.toLowerCase());
        }
        if (!selected && this.options.preferredCountries?.length) {
            selected = find_country(this.options.preferredCountries[0].toLowerCase());
        }
        if (!selected) {
            selected = this.countries[0];
        }
        this.selectedCountry = selected;

        const { wrapper, select, dialCode } = build_select(
            this.countries,
            (this.options.preferredCountries || []).map((iso) => iso.toLowerCase()),
            this.selectedCountry.iso2
        );
        this.flagContainer = wrapper;
        this.countrySelect = select;
        this.dialCodeDisplay = dialCode;

        this.wrapper = document.createElement("div");
        this.wrapper.classList.add("iti");
        this.input.parentNode.insertBefore(this.wrapper, this.input);
        this.wrapper.appendChild(wrapper);
        this.wrapper.appendChild(this.input);

        this.countrySelect.addEventListener("change", () => {
            const iso2 = this.countrySelect.value;
            const country = find_country(iso2);
            if (country) {
                this.selectedCountry = country;
                this._update_dial_code();
            }
        });

        this.input.addEventListener("blur", () => this._format_input());
        this.input.addEventListener("input", () => this._toggle_invalid_state(false));

        this._update_dial_code();
    };

    IntlTelInput.prototype._update_dial_code = function () {
        const code = `+${this.selectedCountry.dialCode}`;
        this.dialCodeDisplay.textContent = code;
        if (this.options.separateDialCode && !this.input.value.startsWith(code)) {
            // keep the national significant number in the box
            const national = this.input.value.replace(/^\+?\d*/, "").replace(/\D/g, "");
            this.input.value = national;
        }
    };

    IntlTelInput.prototype._toggle_invalid_state = function (state) {
        if (!state) {
            this.input.classList.remove("iti__input--invalid");
            this.input.removeAttribute("aria-invalid");
            return;
        }
        this.input.classList.add("iti__input--invalid");
        this.input.setAttribute("aria-invalid", "true");
    };

    IntlTelInput.prototype._format_input = function () {
        const raw = this.input.value.trim();
        if (!raw) {
            this._toggle_invalid_state(false);
            return;
        }
        const digits = raw.replace(/\D/g, "");
        const formatted = `+${this.selectedCountry.dialCode}${digits}`;
        if (digits.length < MIN_LENGTH || digits.length > MAX_LENGTH) {
            this._toggle_invalid_state(true);
        } else {
            this._toggle_invalid_state(false);
        }
        if (!this.options.separateDialCode) {
            this.input.value = formatted;
        }
    };

    IntlTelInput.prototype.getNumber = function () {
        const raw = this.input.value.trim();
        if (!raw) {
            return "";
        }
        if (raw.startsWith("+")) {
            return raw.replace(/\s+/g, "");
        }
        const digits = raw.replace(/\D/g, "");
        if (!digits) {
            return "";
        }
        return `+${this.selectedCountry.dialCode}${digits}`;
    };

    IntlTelInput.prototype.setNumber = function (value) {
        if (!value) {
            this.input.value = "";
            this._toggle_invalid_state(false);
            return;
        }
        const digits = value.replace(/[^\d]/g, "");
        if (!digits) {
            this.input.value = "";
            this._toggle_invalid_state(true);
            return;
        }
        for (const country of this.countries) {
            if (digits.startsWith(country.dialCode)) {
                this.selectedCountry = country;
                this.countrySelect.value = country.iso2;
                this._update_dial_code();
                const national = digits.slice(country.dialCode.length);
                this.input.value = this.options.separateDialCode ? national : `+${country.dialCode}${national}`;
                this._toggle_invalid_state(false);
                return;
            }
        }
        this.input.value = `+${digits}`;
        this._toggle_invalid_state(true);
    };

    IntlTelInput.prototype.isValidNumber = function () {
        const number = this.getNumber();
        if (!number) {
            return false;
        }
        const digits = number.replace(/[^\d]/g, "");
        const withoutPlus = digits.slice(digits.indexOf(this.selectedCountry.dialCode));
        const national = withoutPlus.slice(this.selectedCountry.dialCode.length);
        return national.length >= MIN_LENGTH && national.length <= MAX_LENGTH;
    };

    IntlTelInput.prototype.getSelectedCountryData = function () {
        return Object.assign({}, this.selectedCountry);
    };

    IntlTelInput.prototype.destroy = function () {
        this.wrapper?.parentNode?.insertBefore(this.input, this.wrapper);
        this.wrapper?.remove();
        this.input.classList.remove("iti__input", "iti__input--invalid");
        this.input.removeAttribute("aria-invalid");
    };

    const globals = {
        getCountryData() {
            return COUNTRY_DATA.slice();
        }
    };

    return {
        intlTelInput(input, options) {
            return new IntlTelInput(input, options);
        },
        intlTelInputGlobals: globals
    };
});
