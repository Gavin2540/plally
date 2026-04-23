"""
Settings UI for PlywoodPro.
Company setup form that doubles as a first-run wizard when the company table is empty.
Allows editing company profile, GST details, and bank information.
"""

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from modules.masters import get_company, save_company
from utils.validators import (
    validate_gstin, validate_pan, validate_pincode,
    validate_phone, validate_email, INDIAN_STATES, STATE_NAME_TO_CODE,
)


class SettingsUI(ctk.CTkFrame):
    """Company settings and profile management screen."""

    def __init__(self, parent, app=None):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.is_first_run = False
        self._build_ui()
        self._load_company_data()

    def _build_ui(self):
        """Build the complete settings form layout."""
        # ── Title ──────────────────────────────────────────────────
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=(20, 5))

        self.title_label = ctk.CTkLabel(
            title_frame, text="⚙  Company Settings",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        self.title_label.pack(side="left")

        # ── Scrollable Form Area ───────────────────────────────────
        self.scroll_frame = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0,
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Configure grid for two-column layout
        self.scroll_frame.columnconfigure(0, weight=0, minsize=180)
        self.scroll_frame.columnconfigure(1, weight=1)
        self.scroll_frame.columnconfigure(2, weight=0, minsize=20)
        self.scroll_frame.columnconfigure(3, weight=0, minsize=180)
        self.scroll_frame.columnconfigure(4, weight=1)

        row = 0

        # ── Section: Business Details ──────────────────────────────
        section_label = ctk.CTkLabel(
            self.scroll_frame, text="Business Details",
            font=ctk.CTkFont(size=16, weight="bold"), text_color="#2E7D32",
        )
        section_label.grid(row=row, column=0, columnspan=5, sticky="w", pady=(10, 5))
        row += 1

        # Company Name *
        ctk.CTkLabel(self.scroll_frame, text="Company Name *").grid(
            row=row, column=0, sticky="w", pady=5,
        )
        self.entry_name = ctk.CTkEntry(self.scroll_frame, width=300)
        self.entry_name.grid(row=row, column=1, sticky="ew", pady=5, padx=(0, 10))

        # Phone
        ctk.CTkLabel(self.scroll_frame, text="Phone").grid(
            row=row, column=3, sticky="w", pady=5,
        )
        self.entry_phone = ctk.CTkEntry(self.scroll_frame, width=200)
        self.entry_phone.grid(row=row, column=4, sticky="ew", pady=5)
        row += 1

        # Address Line 1
        ctk.CTkLabel(self.scroll_frame, text="Address Line 1").grid(
            row=row, column=0, sticky="w", pady=5,
        )
        self.entry_addr1 = ctk.CTkEntry(self.scroll_frame, width=300)
        self.entry_addr1.grid(row=row, column=1, sticky="ew", pady=5, padx=(0, 10))

        # Email
        ctk.CTkLabel(self.scroll_frame, text="Email").grid(
            row=row, column=3, sticky="w", pady=5,
        )
        self.entry_email = ctk.CTkEntry(self.scroll_frame, width=200)
        self.entry_email.grid(row=row, column=4, sticky="ew", pady=5)
        row += 1

        # Address Line 2
        ctk.CTkLabel(self.scroll_frame, text="Address Line 2").grid(
            row=row, column=0, sticky="w", pady=5,
        )
        self.entry_addr2 = ctk.CTkEntry(self.scroll_frame, width=300)
        self.entry_addr2.grid(row=row, column=1, sticky="ew", pady=5, padx=(0, 10))

        # City
        ctk.CTkLabel(self.scroll_frame, text="City").grid(
            row=row, column=3, sticky="w", pady=5,
        )
        self.entry_city = ctk.CTkEntry(self.scroll_frame, width=200)
        self.entry_city.grid(row=row, column=4, sticky="ew", pady=5)
        row += 1

        # State *
        ctk.CTkLabel(self.scroll_frame, text="State *").grid(
            row=row, column=0, sticky="w", pady=5,
        )
        self.combo_state = ctk.CTkComboBox(
            self.scroll_frame, values=INDIAN_STATES, width=300,
            command=self._on_state_change,
        )
        self.combo_state.set('')
        self.combo_state.grid(row=row, column=1, sticky="ew", pady=5, padx=(0, 10))

        # State Code (auto-filled)
        ctk.CTkLabel(self.scroll_frame, text="State Code").grid(
            row=row, column=3, sticky="w", pady=5,
        )
        self.entry_state_code = ctk.CTkEntry(self.scroll_frame, width=80)
        self.entry_state_code.grid(row=row, column=4, sticky="w", pady=5)
        row += 1

        # Pincode
        ctk.CTkLabel(self.scroll_frame, text="Pincode").grid(
            row=row, column=0, sticky="w", pady=5,
        )
        self.entry_pincode = ctk.CTkEntry(self.scroll_frame, width=120)
        self.entry_pincode.grid(row=row, column=1, sticky="w", pady=5, padx=(0, 10))
        row += 1

        # ── Section: GST & Tax Details ─────────────────────────────
        row += 1
        section_label2 = ctk.CTkLabel(
            self.scroll_frame, text="GST & Tax Details",
            font=ctk.CTkFont(size=16, weight="bold"), text_color="#2E7D32",
        )
        section_label2.grid(row=row, column=0, columnspan=5, sticky="w", pady=(20, 5))
        row += 1

        # GSTIN
        ctk.CTkLabel(self.scroll_frame, text="GSTIN").grid(
            row=row, column=0, sticky="w", pady=5,
        )
        self.entry_gstin = ctk.CTkEntry(self.scroll_frame, width=220)
        self.entry_gstin.grid(row=row, column=1, sticky="w", pady=5, padx=(0, 10))

        # PAN
        ctk.CTkLabel(self.scroll_frame, text="PAN").grid(
            row=row, column=3, sticky="w", pady=5,
        )
        self.entry_pan = ctk.CTkEntry(self.scroll_frame, width=150)
        self.entry_pan.grid(row=row, column=4, sticky="w", pady=5)
        row += 1

        # Financial Year Start Month
        ctk.CTkLabel(self.scroll_frame, text="FY Start Month").grid(
            row=row, column=0, sticky="w", pady=5,
        )
        months = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December',
        ]
        self.combo_fy_month = ctk.CTkComboBox(
            self.scroll_frame, values=months, width=160,
        )
        self.combo_fy_month.set('April')
        self.combo_fy_month.grid(row=row, column=1, sticky="w", pady=5, padx=(0, 10))
        row += 1

        # ── Section: Bank Details ──────────────────────────────────
        row += 1
        section_label3 = ctk.CTkLabel(
            self.scroll_frame, text="Bank Details",
            font=ctk.CTkFont(size=16, weight="bold"), text_color="#2E7D32",
        )
        section_label3.grid(row=row, column=0, columnspan=5, sticky="w", pady=(20, 5))
        row += 1

        # Bank Name
        ctk.CTkLabel(self.scroll_frame, text="Bank Name").grid(
            row=row, column=0, sticky="w", pady=5,
        )
        self.entry_bank_name = ctk.CTkEntry(self.scroll_frame, width=300)
        self.entry_bank_name.grid(row=row, column=1, sticky="ew", pady=5, padx=(0, 10))

        # IFSC
        ctk.CTkLabel(self.scroll_frame, text="IFSC Code").grid(
            row=row, column=3, sticky="w", pady=5,
        )
        self.entry_bank_ifsc = ctk.CTkEntry(self.scroll_frame, width=150)
        self.entry_bank_ifsc.grid(row=row, column=4, sticky="w", pady=5)
        row += 1

        # Account Number
        ctk.CTkLabel(self.scroll_frame, text="Account Number").grid(
            row=row, column=0, sticky="w", pady=5,
        )
        self.entry_bank_account = ctk.CTkEntry(self.scroll_frame, width=250)
        self.entry_bank_account.grid(row=row, column=1, sticky="w", pady=5, padx=(0, 10))
        row += 1

        # ── Section: Business Defaults ─────────────────────────────
        row += 1
        section_label4 = ctk.CTkLabel(
            self.scroll_frame, text="Business Defaults",
            font=ctk.CTkFont(size=16, weight="bold"), text_color="#2E7D32",
        )
        section_label4.grid(row=row, column=0, columnspan=5, sticky="w", pady=(20, 5))
        row += 1

        # Default GST Rate
        ctk.CTkLabel(self.scroll_frame, text="Default GST Rate %").grid(
            row=row, column=0, sticky="w", pady=5,
        )
        self.entry_def_gst = ctk.CTkComboBox(
            self.scroll_frame, values=["0", "5", "12", "18", "28"], width=100,
        )
        self.entry_def_gst.set("18")
        self.entry_def_gst.grid(row=row, column=1, sticky="w", pady=5, padx=(0, 10))

        # Default Payment Terms (days)
        ctk.CTkLabel(self.scroll_frame, text="Payment Terms (days)").grid(
            row=row, column=3, sticky="w", pady=5,
        )
        self.entry_def_terms = ctk.CTkEntry(self.scroll_frame, width=80, placeholder_text="30")
        self.entry_def_terms.grid(row=row, column=4, sticky="w", pady=5)
        row += 1

        # Default Godown
        ctk.CTkLabel(self.scroll_frame, text="Default Godown").grid(
            row=row, column=0, sticky="w", pady=5,
        )
        self.entry_def_godown = ctk.CTkEntry(self.scroll_frame, width=200, placeholder_text="Main Godown")
        self.entry_def_godown.grid(row=row, column=1, sticky="w", pady=5, padx=(0, 10))

        # Default Invoice Narration
        ctk.CTkLabel(self.scroll_frame, text="Invoice Narration").grid(
            row=row, column=3, sticky="w", pady=5,
        )
        self.entry_def_narration = ctk.CTkEntry(self.scroll_frame, width=250, placeholder_text="Goods sold as per invoice")
        self.entry_def_narration.grid(row=row, column=4, sticky="ew", pady=5)
        row += 1

        # Load defaults from SettingsManager
        self._load_defaults()

        # ── Action Buttons ─────────────────────────────────────────
        row += 1
        btn_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        btn_frame.grid(row=row, column=0, columnspan=5, pady=20)

        self.btn_save = ctk.CTkButton(
            btn_frame, text="💾  Save Company Details", width=220, height=40,
            fg_color="#2E7D32", hover_color="#1B5E20",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._save_company,
        )
        self.btn_save.pack(side="left", padx=10)

        self.btn_clear = ctk.CTkButton(
            btn_frame, text="🔄  Clear Form", width=140, height=40,
            fg_color="#555555", hover_color="#444444",
            command=self.clear_form,
        )
        self.btn_clear.pack(side="left", padx=10)

    def _on_state_change(self, state_name: str):
        """Auto-fill state code when state is selected from dropdown."""
        code = STATE_NAME_TO_CODE.get(state_name, '')
        self.entry_state_code.delete(0, "end")
        self.entry_state_code.insert(0, code)

    def _load_company_data(self):
        """Load existing company data into the form, or show first-run banner."""
        company = get_company()
        if company:
            self.is_first_run = False
            self.title_label.configure(text="⚙  Company Settings")

            self._set_entry(self.entry_name, company.get('name', ''))
            self._set_entry(self.entry_addr1, company.get('address_line1', ''))
            self._set_entry(self.entry_addr2, company.get('address_line2', ''))
            self._set_entry(self.entry_city, company.get('city', ''))
            self._set_entry(self.entry_pincode, company.get('pincode', ''))
            self._set_entry(self.entry_phone, company.get('phone', ''))
            self._set_entry(self.entry_email, company.get('email', ''))
            self._set_entry(self.entry_gstin, company.get('gstin', ''))
            self._set_entry(self.entry_pan, company.get('pan', ''))
            self._set_entry(self.entry_bank_name, company.get('bank_name', ''))
            self._set_entry(self.entry_bank_account, company.get('bank_account', ''))
            self._set_entry(self.entry_bank_ifsc, company.get('bank_ifsc', ''))
            self._set_entry(self.entry_state_code, company.get('state_code', ''))

            state = company.get('state', '')
            if state:
                self.combo_state.set(state)

            fy_month = company.get('fy_start_month', 4)
            months = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December',
            ]
            if 1 <= fy_month <= 12:
                self.combo_fy_month.set(months[fy_month - 1])
        else:
            self.is_first_run = True
            self.title_label.configure(
                text="🏢  Welcome to PlywoodPro — Set Up Your Company",
            )

    def _set_entry(self, entry_widget, value):
        """Helper to set an entry widget's value."""
        entry_widget.delete(0, "end")
        if value:
            entry_widget.insert(0, str(value))

    def _validate_form(self) -> tuple[bool, str]:
        """Validate all form fields. Returns (is_valid, error_message)."""
        name = self.entry_name.get().strip()
        if not name:
            return False, "Company Name is required."

        state = self.combo_state.get().strip()
        state_code = self.entry_state_code.get().strip()
        if not state:
            return False, "State is required."
        if not state_code:
            return False, "State Code is required."

        # Validate optional fields
        gstin = self.entry_gstin.get().strip()
        valid, msg = validate_gstin(gstin)
        if not valid:
            return False, msg

        pan = self.entry_pan.get().strip()
        valid, msg = validate_pan(pan)
        if not valid:
            return False, msg

        pincode = self.entry_pincode.get().strip()
        valid, msg = validate_pincode(pincode)
        if not valid:
            return False, msg

        phone = self.entry_phone.get().strip()
        valid, msg = validate_phone(phone)
        if not valid:
            return False, msg

        email = self.entry_email.get().strip()
        valid, msg = validate_email(email)
        if not valid:
            return False, msg

        return True, ""

    def _get_fy_month_number(self) -> int:
        """Convert the selected month name to its number (1-12)."""
        months = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December',
        ]
        selected = self.combo_fy_month.get()
        try:
            return months.index(selected) + 1
        except ValueError:
            return 4  # default to April

    def _save_company(self):
        """Validate form and save company details to the database."""
        valid, msg = self._validate_form()
        if not valid:
            CTkMessagebox(title="Validation Error", message=msg, icon="cancel")
            return

        data = {
            'name': self.entry_name.get().strip(),
            'address_line1': self.entry_addr1.get().strip(),
            'address_line2': self.entry_addr2.get().strip(),
            'city': self.entry_city.get().strip(),
            'state': self.combo_state.get().strip(),
            'state_code': self.entry_state_code.get().strip(),
            'pincode': self.entry_pincode.get().strip(),
            'gstin': self.entry_gstin.get().strip().upper(),
            'pan': self.entry_pan.get().strip().upper(),
            'phone': self.entry_phone.get().strip(),
            'email': self.entry_email.get().strip(),
            'bank_name': self.entry_bank_name.get().strip(),
            'bank_account': self.entry_bank_account.get().strip(),
            'bank_ifsc': self.entry_bank_ifsc.get().strip().upper(),
            'fy_start_month': self._get_fy_month_number(),
            'logo_path': '',
        }

        success, message = save_company(data)
        if success:
            self._save_defaults()
            CTkMessagebox(title="Success", message=message, icon="check")
            self.is_first_run = False
            self.title_label.configure(text="⚙  Company Settings")
            # Update the main window title bar with company name
            if self.app:
                self.app.update_title_bar()
        else:
            CTkMessagebox(title="Error", message=message, icon="cancel")

    def _load_defaults(self):
        """Load business defaults from settings table into form fields."""
        try:
            from utils.settings_manager import get_setting
            gst = get_setting('default_gst_rate', '18')
            self.entry_def_gst.set(gst)
            terms = get_setting('payment_terms_days', '')
            self._set_entry(self.entry_def_terms, terms)
            godown = get_setting('default_godown', '')
            self._set_entry(self.entry_def_godown, godown)
            narration = get_setting('default_narration', '')
            self._set_entry(self.entry_def_narration, narration)
        except Exception:
            pass  # Settings not yet available

    def _save_defaults(self):
        """Persist business defaults via settings table."""
        try:
            from utils.settings_manager import set_setting
            set_setting('default_gst_rate', self.entry_def_gst.get().strip() or '18')
            set_setting('payment_terms_days', self.entry_def_terms.get().strip() or '30')
            set_setting('default_godown', self.entry_def_godown.get().strip())
            set_setting('default_narration', self.entry_def_narration.get().strip())
        except Exception:
            pass

    def clear_form(self):
        """Reset all form fields to empty."""
        for entry in [
            self.entry_name, self.entry_addr1, self.entry_addr2,
            self.entry_city, self.entry_pincode, self.entry_phone,
            self.entry_email, self.entry_gstin, self.entry_pan,
            self.entry_bank_name, self.entry_bank_account, self.entry_bank_ifsc,
            self.entry_state_code,
        ]:
            entry.delete(0, "end")
        self.combo_state.set('')
        self.combo_fy_month.set('April')
