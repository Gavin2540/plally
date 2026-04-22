"""
Masters UI for PlywoodPro.
Provides tabbed screens for managing all master records:
  - Party Master (Customers / Suppliers)
  - Item Master (Products / Stock)
  - Godown Master (Warehouses)
  - Account Master (Chart of Accounts)

Each master has a searchable Treeview list and an Add/Edit form panel.
Double-click any row to open the edit form.
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox

from modules.masters import (
    get_all_parties, get_party_by_id, create_party, update_party, delete_party,
    get_all_items, get_item_by_id, create_item, update_item, delete_item,
    get_all_godowns, get_godown_by_id, create_godown, update_godown, delete_godown,
    get_all_accounts, get_account_by_id, create_account, update_account, delete_account,
    ACCOUNT_GROUPS,
)
from utils.validators import (
    validate_gstin, validate_pan, validate_hsn, validate_pincode,
    validate_phone, validate_email, validate_gst_rate,
    INDIAN_STATES, STATE_NAME_TO_CODE, VALID_GST_RATES,
)
from utils.gst_engine import HSN_CODES_LIST
from utils.helpers import format_inr


# ═══════════════════════════════════════════════════════════════════════
#  MASTER CONTAINER — Holds the Tab View
# ═══════════════════════════════════════════════════════════════════════

class MastersUI(ctk.CTkFrame):
    """Container frame with tabs for each master type."""

    def __init__(self, parent, app=None):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._build_ui()

    def _build_ui(self):
        """Build the tabbed master interface."""
        title = ctk.CTkLabel(
            self, text="📋  Master Data Management",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title.pack(fill="x", padx=20, pady=(20, 5))

        self.tabview = ctk.CTkTabview(self, fg_color="transparent")
        self.tabview.pack(fill="both", expand=True, padx=20, pady=10)

        # Create tabs
        tab_parties = self.tabview.add("Parties")
        tab_items = self.tabview.add("Items")
        tab_godowns = self.tabview.add("Godowns")
        tab_accounts = self.tabview.add("Accounts")

        # Build each tab's content
        self.party_tab = PartyMasterTab(tab_parties)
        self.party_tab.pack(fill="both", expand=True)

        self.item_tab = ItemMasterTab(tab_items)
        self.item_tab.pack(fill="both", expand=True)

        self.godown_tab = GodownMasterTab(tab_godowns)
        self.godown_tab.pack(fill="both", expand=True)

        self.account_tab = AccountMasterTab(tab_accounts)
        self.account_tab.pack(fill="both", expand=True)

    def show_tab(self, tab_name: str):
        """Switch to a specific tab by name."""
        try:
            self.tabview.set(tab_name)
        except ValueError:
            pass


# ═══════════════════════════════════════════════════════════════════════
#  PARTY MASTER TAB
# ═══════════════════════════════════════════════════════════════════════

class PartyMasterTab(ctk.CTkFrame):
    """Party (Customer/Supplier) master with list and form."""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.editing_id = None
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        """Build the party master list and form."""
        # ── Top Bar: Search + Type Filter + Buttons ────────────────
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(top_frame, text="🔍").pack(side="left", padx=(0, 5))
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._load_data())
        self.search_entry = ctk.CTkEntry(
            top_frame, textvariable=self.search_var,
            placeholder_text="Search by name, GSTIN, city, phone...", width=300,
        )
        self.search_entry.pack(side="left", padx=5)

        ctk.CTkLabel(top_frame, text="Type:").pack(side="left", padx=(15, 5))
        self.type_filter = ctk.CTkComboBox(
            top_frame, values=["All", "customer", "supplier", "both"],
            width=120, command=lambda _: self._load_data(),
        )
        self.type_filter.set("All")
        self.type_filter.pack(side="left", padx=5)

        self.btn_add = ctk.CTkButton(
            top_frame, text="➕ Add Party", width=120,
            fg_color="#2E7D32", hover_color="#1B5E20",
            command=self._show_add_form,
        )
        self.btn_add.pack(side="right", padx=5)

        self.btn_delete = ctk.CTkButton(
            top_frame, text="🗑 Delete", width=90,
            fg_color="#C62828", hover_color="#B71C1C",
            command=self._delete_selected,
        )
        self.btn_delete.pack(side="right", padx=5)

        # ── Main Split: List (left) + Form (right) ────────────────
        self.paned = ctk.CTkFrame(self, fg_color="transparent")
        self.paned.pack(fill="both", expand=True, padx=5, pady=5)
        self.paned.columnconfigure(0, weight=3)
        self.paned.columnconfigure(1, weight=2)
        self.paned.rowconfigure(0, weight=1)

        # ── List Panel ─────────────────────────────────────────────
        list_frame = ctk.CTkFrame(self.paned)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        columns = ("id", "name", "type", "gstin", "city", "state", "phone", "balance")
        self.tree = ttk.Treeview(
            list_frame, columns=columns, show="headings", selectmode="browse",
        )

        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Name")
        self.tree.heading("type", text="Type")
        self.tree.heading("gstin", text="GSTIN")
        self.tree.heading("city", text="City")
        self.tree.heading("state", text="State")
        self.tree.heading("phone", text="Phone")
        self.tree.heading("balance", text="Balance")

        self.tree.column("id", width=40, minwidth=40, anchor="center")
        self.tree.column("name", width=180, minwidth=120)
        self.tree.column("type", width=80, minwidth=60, anchor="center")
        self.tree.column("gstin", width=150, minwidth=100)
        self.tree.column("city", width=100, minwidth=70)
        self.tree.column("state", width=120, minwidth=80)
        self.tree.column("phone", width=100, minwidth=80)
        self.tree.column("balance", width=100, minwidth=80, anchor="e")

        scrollbar_y = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<Double-1>", self._on_double_click)

        # ── Form Panel ─────────────────────────────────────────────
        self.form_frame = ctk.CTkScrollableFrame(self.paned, label_text="Party Details")
        self.form_frame.grid(row=0, column=1, sticky="nsew")

        self._build_form()

    def _build_form(self):
        """Build the party add/edit form inside the form panel."""
        f = self.form_frame

        # Name *
        ctk.CTkLabel(f, text="Name *").pack(anchor="w", padx=5, pady=(10, 0))
        self.f_name = ctk.CTkEntry(f, width=280)
        self.f_name.pack(fill="x", padx=5, pady=2)

        # Type *
        ctk.CTkLabel(f, text="Type *").pack(anchor="w", padx=5, pady=(8, 0))
        self.f_type = ctk.CTkComboBox(f, values=["customer", "supplier", "both"], width=180)
        self.f_type.set("customer")
        self.f_type.pack(anchor="w", padx=5, pady=2)

        # GSTIN
        ctk.CTkLabel(f, text="GSTIN").pack(anchor="w", padx=5, pady=(8, 0))
        self.f_gstin = ctk.CTkEntry(f, width=220)
        self.f_gstin.pack(anchor="w", padx=5, pady=2)

        # PAN
        ctk.CTkLabel(f, text="PAN").pack(anchor="w", padx=5, pady=(8, 0))
        self.f_pan = ctk.CTkEntry(f, width=160)
        self.f_pan.pack(anchor="w", padx=5, pady=2)

        # State *
        ctk.CTkLabel(f, text="State *").pack(anchor="w", padx=5, pady=(8, 0))
        self.f_state = ctk.CTkComboBox(
            f, values=INDIAN_STATES, width=250,
            command=self._on_party_state_change,
        )
        self.f_state.set('')
        self.f_state.pack(anchor="w", padx=5, pady=2)

        # State Code (auto-filled)
        ctk.CTkLabel(f, text="State Code").pack(anchor="w", padx=5, pady=(8, 0))
        self.f_state_code = ctk.CTkEntry(f, width=80)
        self.f_state_code.pack(anchor="w", padx=5, pady=2)

        # Address
        ctk.CTkLabel(f, text="Address Line 1").pack(anchor="w", padx=5, pady=(8, 0))
        self.f_addr1 = ctk.CTkEntry(f, width=280)
        self.f_addr1.pack(fill="x", padx=5, pady=2)

        ctk.CTkLabel(f, text="Address Line 2").pack(anchor="w", padx=5, pady=(8, 0))
        self.f_addr2 = ctk.CTkEntry(f, width=280)
        self.f_addr2.pack(fill="x", padx=5, pady=2)

        # City
        ctk.CTkLabel(f, text="City").pack(anchor="w", padx=5, pady=(8, 0))
        self.f_city = ctk.CTkEntry(f, width=200)
        self.f_city.pack(anchor="w", padx=5, pady=2)

        # Pincode
        ctk.CTkLabel(f, text="Pincode").pack(anchor="w", padx=5, pady=(8, 0))
        self.f_pincode = ctk.CTkEntry(f, width=120)
        self.f_pincode.pack(anchor="w", padx=5, pady=2)

        # Phone
        ctk.CTkLabel(f, text="Phone").pack(anchor="w", padx=5, pady=(8, 0))
        self.f_phone = ctk.CTkEntry(f, width=180)
        self.f_phone.pack(anchor="w", padx=5, pady=2)

        # Email
        ctk.CTkLabel(f, text="Email").pack(anchor="w", padx=5, pady=(8, 0))
        self.f_email = ctk.CTkEntry(f, width=250)
        self.f_email.pack(anchor="w", padx=5, pady=2)

        # Credit Limit
        ctk.CTkLabel(f, text="Credit Limit (₹)").pack(anchor="w", padx=5, pady=(8, 0))
        self.f_credit_limit = ctk.CTkEntry(f, width=150)
        self.f_credit_limit.insert(0, "0")
        self.f_credit_limit.pack(anchor="w", padx=5, pady=2)

        # Credit Days
        ctk.CTkLabel(f, text="Credit Days").pack(anchor="w", padx=5, pady=(8, 0))
        self.f_credit_days = ctk.CTkEntry(f, width=100)
        self.f_credit_days.insert(0, "0")
        self.f_credit_days.pack(anchor="w", padx=5, pady=2)

        # Opening Balance
        ctk.CTkLabel(f, text="Opening Balance (₹)").pack(anchor="w", padx=5, pady=(8, 0))
        bal_frame = ctk.CTkFrame(f, fg_color="transparent")
        bal_frame.pack(anchor="w", padx=5, pady=2)
        self.f_opening_bal = ctk.CTkEntry(bal_frame, width=150)
        self.f_opening_bal.insert(0, "0")
        self.f_opening_bal.pack(side="left", padx=(0, 5))
        self.f_bal_type = ctk.CTkComboBox(bal_frame, values=["Dr", "Cr"], width=70)
        self.f_bal_type.set("Dr")
        self.f_bal_type.pack(side="left")

        # ── Form Buttons ───────────────────────────────────────────
        btn_frame = ctk.CTkFrame(f, fg_color="transparent")
        btn_frame.pack(fill="x", padx=5, pady=15)

        self.btn_save = ctk.CTkButton(
            btn_frame, text="💾 Save", width=100,
            fg_color="#2E7D32", hover_color="#1B5E20",
            command=self._save_party,
        )
        self.btn_save.pack(side="left", padx=5)

        self.btn_cancel = ctk.CTkButton(
            btn_frame, text="✖ Cancel", width=100,
            fg_color="#555555", hover_color="#444444",
            command=self.clear_form,
        )
        self.btn_cancel.pack(side="left", padx=5)

    def _on_party_state_change(self, state_name: str):
        """Auto-fill state code when state is selected."""
        code = STATE_NAME_TO_CODE.get(state_name, '')
        self.f_state_code.delete(0, "end")
        self.f_state_code.insert(0, code)

    def _load_data(self):
        """Reload the party list from the database."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        search = self.search_var.get()
        type_filter = self.type_filter.get()
        parties = get_all_parties(search=search, party_type=type_filter)

        for p in parties:
            bal_str = format_inr(p.get('opening_balance', 0))
            bal_type = p.get('balance_type', 'Dr')
            self.tree.insert("", "end", values=(
                p['id'], p['name'], p['type'], p.get('gstin', ''),
                p.get('city', ''), p.get('state', ''),
                p.get('phone', ''), f"{bal_str} {bal_type}",
            ))

    def _on_double_click(self, event):
        """Load selected party into the edit form."""
        selected = self.tree.selection()
        if not selected:
            return
        item = self.tree.item(selected[0])
        party_id = item['values'][0]
        party = get_party_by_id(int(party_id))
        if not party:
            return

        self.editing_id = party['id']
        self._populate_form(party)
        self.btn_save.configure(text="💾 Update")

    def _populate_form(self, data: dict):
        """Fill the form with data from a party record."""
        self.clear_form()
        self.f_name.insert(0, data.get('name', ''))
        self.f_type.set(data.get('type', 'customer'))
        self.f_gstin.insert(0, data.get('gstin', ''))
        self.f_pan.insert(0, data.get('pan', ''))
        if data.get('state'):
            self.f_state.set(data['state'])
        self.f_state_code.insert(0, data.get('state_code', ''))
        self.f_addr1.insert(0, data.get('address_line1', ''))
        self.f_addr2.insert(0, data.get('address_line2', ''))
        self.f_city.insert(0, data.get('city', ''))
        self.f_pincode.insert(0, data.get('pincode', ''))
        self.f_phone.insert(0, data.get('phone', ''))
        self.f_email.insert(0, data.get('email', ''))
        self.f_credit_limit.delete(0, "end")
        self.f_credit_limit.insert(0, str(data.get('credit_limit', 0)))
        self.f_credit_days.delete(0, "end")
        self.f_credit_days.insert(0, str(data.get('credit_days', 0)))
        self.f_opening_bal.delete(0, "end")
        self.f_opening_bal.insert(0, str(data.get('opening_balance', 0)))
        self.f_bal_type.set(data.get('balance_type', 'Dr'))

    def _show_add_form(self):
        """Reset form for adding a new party."""
        self.clear_form()
        self.editing_id = None
        self.btn_save.configure(text="💾 Save")
        self.f_name.focus_set()

    def _validate_form(self) -> tuple[bool, str]:
        """Validate the party form fields."""
        name = self.f_name.get().strip()
        if not name:
            return False, "Party Name is required."

        p_type = self.f_type.get()
        if p_type not in ('customer', 'supplier', 'both'):
            return False, "Party Type must be customer, supplier, or both."

        gstin = self.f_gstin.get().strip()
        valid, msg = validate_gstin(gstin)
        if not valid:
            return False, msg

        pan = self.f_pan.get().strip()
        valid, msg = validate_pan(pan)
        if not valid:
            return False, msg

        pincode = self.f_pincode.get().strip()
        valid, msg = validate_pincode(pincode)
        if not valid:
            return False, msg

        phone = self.f_phone.get().strip()
        valid, msg = validate_phone(phone)
        if not valid:
            return False, msg

        email = self.f_email.get().strip()
        valid, msg = validate_email(email)
        if not valid:
            return False, msg

        try:
            float(self.f_credit_limit.get() or '0')
        except ValueError:
            return False, "Credit Limit must be a number."

        try:
            int(self.f_credit_days.get() or '0')
        except ValueError:
            return False, "Credit Days must be a whole number."

        try:
            float(self.f_opening_bal.get() or '0')
        except ValueError:
            return False, "Opening Balance must be a number."

        return True, ""

    def _save_party(self):
        """Save or update the party from form data."""
        valid, msg = self._validate_form()
        if not valid:
            CTkMessagebox(title="Validation Error", message=msg, icon="cancel")
            return

        data = {
            'name': self.f_name.get().strip(),
            'type': self.f_type.get(),
            'gstin': self.f_gstin.get().strip().upper(),
            'pan': self.f_pan.get().strip().upper(),
            'state': self.f_state.get().strip(),
            'state_code': self.f_state_code.get().strip(),
            'address_line1': self.f_addr1.get().strip(),
            'address_line2': self.f_addr2.get().strip(),
            'city': self.f_city.get().strip(),
            'pincode': self.f_pincode.get().strip(),
            'phone': self.f_phone.get().strip(),
            'email': self.f_email.get().strip(),
            'credit_limit': float(self.f_credit_limit.get() or '0'),
            'credit_days': int(self.f_credit_days.get() or '0'),
            'opening_balance': float(self.f_opening_bal.get() or '0'),
            'balance_type': self.f_bal_type.get(),
        }

        if self.editing_id:
            success, message = update_party(self.editing_id, data)
        else:
            success, message = create_party(data)

        if success:
            CTkMessagebox(title="Success", message=message, icon="check")
            self.clear_form()
            self._load_data()
        else:
            CTkMessagebox(title="Error", message=message, icon="cancel")

    def _delete_selected(self):
        """Delete the selected party after confirmation."""
        selected = self.tree.selection()
        if not selected:
            CTkMessagebox(title="Warning", message="Please select a party to delete.", icon="warning")
            return

        item = self.tree.item(selected[0])
        party_id = item['values'][0]
        party_name = item['values'][1]

        confirm = CTkMessagebox(
            title="Confirm Delete",
            message=f"Are you sure you want to deactivate party '{party_name}'?",
            icon="question", option_1="Yes", option_2="No",
        )
        if confirm.get() == "Yes":
            success, message = delete_party(int(party_id))
            if success:
                CTkMessagebox(title="Success", message=message, icon="check")
                self._load_data()
                self.clear_form()
            else:
                CTkMessagebox(title="Error", message=message, icon="cancel")

    def clear_form(self):
        """Reset all form fields to empty/defaults."""
        self.editing_id = None
        self.btn_save.configure(text="💾 Save")
        for entry in [
            self.f_name, self.f_gstin, self.f_pan, self.f_state_code,
            self.f_addr1, self.f_addr2, self.f_city, self.f_pincode,
            self.f_phone, self.f_email,
        ]:
            entry.delete(0, "end")
        self.f_type.set("customer")
        self.f_state.set('')
        self.f_credit_limit.delete(0, "end")
        self.f_credit_limit.insert(0, "0")
        self.f_credit_days.delete(0, "end")
        self.f_credit_days.insert(0, "0")
        self.f_opening_bal.delete(0, "end")
        self.f_opening_bal.insert(0, "0")
        self.f_bal_type.set("Dr")


# ═══════════════════════════════════════════════════════════════════════
#  ITEM MASTER TAB
# ═══════════════════════════════════════════════════════════════════════

ITEM_CATEGORIES = [
    'Plywood', 'Blockboard', 'MDF', 'Flush Door', 'Particle Board',
    'Veneer', 'Laminate', 'Hardware', 'Adhesive', 'Other',
]

THICKNESS_OPTIONS = [
    '3mm', '4mm', '6mm', '9mm', '12mm', '16mm', '18mm', '25mm', 'Custom',
]

SIZE_OPTIONS = ['8x4 ft', '7x3.5 ft', '6x3 ft', 'Custom']

UNIT_OPTIONS = ['Sheets', 'Sq.Ft', 'Kg', 'Nos', 'Running Ft']


class ItemMasterTab(ctk.CTkFrame):
    """Item (Product/Stock) master with list and form."""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.editing_id = None
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        """Build the item master list and form."""
        # ── Top Bar ────────────────────────────────────────────────
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(top_frame, text="🔍").pack(side="left", padx=(0, 5))
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._load_data())
        self.search_entry = ctk.CTkEntry(
            top_frame, textvariable=self.search_var,
            placeholder_text="Search by name, HSN, category...", width=280,
        )
        self.search_entry.pack(side="left", padx=5)

        ctk.CTkLabel(top_frame, text="Category:").pack(side="left", padx=(15, 5))
        self.cat_filter = ctk.CTkComboBox(
            top_frame, values=["All"] + ITEM_CATEGORIES,
            width=130, command=lambda _: self._load_data(),
        )
        self.cat_filter.set("All")
        self.cat_filter.pack(side="left", padx=5)

        self.btn_add = ctk.CTkButton(
            top_frame, text="➕ Add Item", width=120,
            fg_color="#2E7D32", hover_color="#1B5E20",
            command=self._show_add_form,
        )
        self.btn_add.pack(side="right", padx=5)

        self.btn_delete = ctk.CTkButton(
            top_frame, text="🗑 Delete", width=90,
            fg_color="#C62828", hover_color="#B71C1C",
            command=self._delete_selected,
        )
        self.btn_delete.pack(side="right", padx=5)

        # ── Main Split ────────────────────────────────────────────
        self.paned = ctk.CTkFrame(self, fg_color="transparent")
        self.paned.pack(fill="both", expand=True, padx=5, pady=5)
        self.paned.columnconfigure(0, weight=3)
        self.paned.columnconfigure(1, weight=2)
        self.paned.rowconfigure(0, weight=1)

        # ── List Panel ─────────────────────────────────────────────
        list_frame = ctk.CTkFrame(self.paned)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        columns = ("id", "name", "category", "hsn", "unit", "gst", "purchase", "sale", "stock")
        self.tree = ttk.Treeview(
            list_frame, columns=columns, show="headings", selectmode="browse",
        )

        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Name")
        self.tree.heading("category", text="Category")
        self.tree.heading("hsn", text="HSN")
        self.tree.heading("unit", text="Unit")
        self.tree.heading("gst", text="GST%")
        self.tree.heading("purchase", text="Purchase ₹")
        self.tree.heading("sale", text="Sale ₹")
        self.tree.heading("stock", text="Opening Stk")

        self.tree.column("id", width=40, minwidth=40, anchor="center")
        self.tree.column("name", width=180, minwidth=120)
        self.tree.column("category", width=100, minwidth=70)
        self.tree.column("hsn", width=70, minwidth=50, anchor="center")
        self.tree.column("unit", width=70, minwidth=50, anchor="center")
        self.tree.column("gst", width=55, minwidth=45, anchor="center")
        self.tree.column("purchase", width=90, minwidth=70, anchor="e")
        self.tree.column("sale", width=90, minwidth=70, anchor="e")
        self.tree.column("stock", width=80, minwidth=60, anchor="e")

        scrollbar_y = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar_y.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<Double-1>", self._on_double_click)

        # ── Form Panel ─────────────────────────────────────────────
        self.form_frame = ctk.CTkScrollableFrame(self.paned, label_text="Item Details")
        self.form_frame.grid(row=0, column=1, sticky="nsew")

        self._build_form()

    def _build_form(self):
        """Build the item add/edit form."""
        f = self.form_frame

        # Name *
        ctk.CTkLabel(f, text="Name *").pack(anchor="w", padx=5, pady=(10, 0))
        self.f_name = ctk.CTkEntry(f, width=280)
        self.f_name.pack(fill="x", padx=5, pady=2)

        # Category
        ctk.CTkLabel(f, text="Category *").pack(anchor="w", padx=5, pady=(8, 0))
        self.f_category = ctk.CTkComboBox(f, values=ITEM_CATEGORIES, width=200)
        self.f_category.set("Plywood")
        self.f_category.pack(anchor="w", padx=5, pady=2)

        # HSN Code *
        ctk.CTkLabel(f, text="HSN Code *").pack(anchor="w", padx=5, pady=(8, 0))
        hsn_display = [f"{h[0]} — {h[1]} ({int(h[2])}%)" for h in HSN_CODES_LIST]
        self.f_hsn = ctk.CTkComboBox(
            f, values=hsn_display, width=320,
            command=self._on_hsn_change,
        )
        self.f_hsn.set(hsn_display[0])
        self.f_hsn.pack(anchor="w", padx=5, pady=2)

        self.f_hsn_manual = ctk.CTkEntry(f, width=120, placeholder_text="or type HSN")
        self.f_hsn_manual.pack(anchor="w", padx=5, pady=2)

        # Unit *
        ctk.CTkLabel(f, text="Unit *").pack(anchor="w", padx=5, pady=(8, 0))
        self.f_unit = ctk.CTkComboBox(f, values=UNIT_OPTIONS, width=150)
        self.f_unit.set("Sheets")
        self.f_unit.pack(anchor="w", padx=5, pady=2)

        # Thickness
        ctk.CTkLabel(f, text="Thickness").pack(anchor="w", padx=5, pady=(8, 0))
        self.f_thickness = ctk.CTkComboBox(f, values=THICKNESS_OPTIONS, width=120)
        self.f_thickness.set('')
        self.f_thickness.pack(anchor="w", padx=5, pady=2)

        # Size
        ctk.CTkLabel(f, text="Size").pack(anchor="w", padx=5, pady=(8, 0))
        self.f_size = ctk.CTkComboBox(f, values=SIZE_OPTIONS, width=150)
        self.f_size.set('')
        self.f_size.pack(anchor="w", padx=5, pady=2)

        # GST Rate *
        ctk.CTkLabel(f, text="GST Rate (%) *").pack(anchor="w", padx=5, pady=(8, 0))
        gst_vals = [str(int(r)) for r in VALID_GST_RATES]
        self.f_gst_rate = ctk.CTkComboBox(f, values=gst_vals, width=100)
        self.f_gst_rate.set("18")
        self.f_gst_rate.pack(anchor="w", padx=5, pady=2)

        # Purchase Rate
        ctk.CTkLabel(f, text="Purchase Rate (₹) *").pack(anchor="w", padx=5, pady=(8, 0))
        self.f_purchase_rate = ctk.CTkEntry(f, width=150)
        self.f_purchase_rate.insert(0, "0")
        self.f_purchase_rate.pack(anchor="w", padx=5, pady=2)

        # Sale Rate
        ctk.CTkLabel(f, text="Sale Rate (₹) *").pack(anchor="w", padx=5, pady=(8, 0))
        self.f_sale_rate = ctk.CTkEntry(f, width=150)
        self.f_sale_rate.insert(0, "0")
        self.f_sale_rate.pack(anchor="w", padx=5, pady=2)

        # Reorder Level
        ctk.CTkLabel(f, text="Reorder Level").pack(anchor="w", padx=5, pady=(8, 0))
        self.f_reorder = ctk.CTkEntry(f, width=100)
        self.f_reorder.insert(0, "0")
        self.f_reorder.pack(anchor="w", padx=5, pady=2)

        # Opening Stock
        ctk.CTkLabel(f, text="Opening Stock").pack(anchor="w", padx=5, pady=(8, 0))
        self.f_opening_stock = ctk.CTkEntry(f, width=100)
        self.f_opening_stock.insert(0, "0")
        self.f_opening_stock.pack(anchor="w", padx=5, pady=2)

        # Description
        ctk.CTkLabel(f, text="Description").pack(anchor="w", padx=5, pady=(8, 0))
        self.f_desc = ctk.CTkEntry(f, width=280)
        self.f_desc.pack(fill="x", padx=5, pady=2)

        # ── Buttons ────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(f, fg_color="transparent")
        btn_frame.pack(fill="x", padx=5, pady=15)

        self.btn_save = ctk.CTkButton(
            btn_frame, text="💾 Save", width=100,
            fg_color="#2E7D32", hover_color="#1B5E20",
            command=self._save_item,
        )
        self.btn_save.pack(side="left", padx=5)

        self.btn_cancel = ctk.CTkButton(
            btn_frame, text="✖ Cancel", width=100,
            fg_color="#555555", hover_color="#444444",
            command=self.clear_form,
        )
        self.btn_cancel.pack(side="left", padx=5)

    def _on_hsn_change(self, value: str):
        """Auto-fill GST rate when HSN code is selected from dropdown."""
        for code, desc, rate in HSN_CODES_LIST:
            if value.startswith(code):
                self.f_gst_rate.set(str(int(rate)))
                self.f_hsn_manual.delete(0, "end")
                self.f_hsn_manual.insert(0, code)
                break

    def _get_hsn_code(self) -> str:
        """Extract the HSN code from either the dropdown or manual entry."""
        manual = self.f_hsn_manual.get().strip()
        if manual:
            return manual
        dropdown = self.f_hsn.get()
        for code, desc, rate in HSN_CODES_LIST:
            if dropdown.startswith(code):
                return code
        return dropdown.split(' ')[0] if dropdown else ''

    def _load_data(self):
        """Reload the item list from the database."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        search = self.search_var.get()
        cat_filter = self.cat_filter.get()
        items = get_all_items(search=search, category=cat_filter)

        for it in items:
            self.tree.insert("", "end", values=(
                it['id'], it['name'], it.get('category', ''),
                it.get('hsn_code', ''), it.get('unit', ''),
                f"{it.get('gst_rate', 18)}%",
                format_inr(it.get('purchase_rate', 0)),
                format_inr(it.get('sale_rate', 0)),
                it.get('opening_stock', 0),
            ))

    def _on_double_click(self, event):
        """Load selected item into the edit form."""
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])['values']
        item_id = values[0]
        item = get_item_by_id(int(item_id))
        if not item:
            return

        self.editing_id = item['id']
        self._populate_form(item)
        self.btn_save.configure(text="💾 Update")

    def _populate_form(self, data: dict):
        """Fill the form with data from an item record."""
        self.clear_form()
        self.f_name.insert(0, data.get('name', ''))
        if data.get('category'):
            self.f_category.set(data['category'])
        self.f_hsn_manual.insert(0, data.get('hsn_code', ''))
        if data.get('unit'):
            self.f_unit.set(data['unit'])
        if data.get('thickness'):
            self.f_thickness.set(data['thickness'])
        if data.get('size'):
            self.f_size.set(data['size'])
        self.f_gst_rate.set(str(int(data.get('gst_rate', 18))))
        self.f_purchase_rate.delete(0, "end")
        self.f_purchase_rate.insert(0, str(data.get('purchase_rate', 0)))
        self.f_sale_rate.delete(0, "end")
        self.f_sale_rate.insert(0, str(data.get('sale_rate', 0)))
        self.f_reorder.delete(0, "end")
        self.f_reorder.insert(0, str(data.get('reorder_level', 0)))
        self.f_opening_stock.delete(0, "end")
        self.f_opening_stock.insert(0, str(data.get('opening_stock', 0)))
        self.f_desc.insert(0, data.get('description', ''))

    def _show_add_form(self):
        """Reset form for adding a new item."""
        self.clear_form()
        self.editing_id = None
        self.btn_save.configure(text="💾 Save")
        self.f_name.focus_set()

    def _validate_form(self) -> tuple[bool, str]:
        """Validate the item form fields."""
        name = self.f_name.get().strip()
        if not name:
            return False, "Item Name is required."

        hsn_code = self._get_hsn_code()
        valid, msg = validate_hsn(hsn_code)
        if not valid:
            return False, msg

        unit = self.f_unit.get()
        if unit not in UNIT_OPTIONS:
            return False, f"Unit must be one of: {', '.join(UNIT_OPTIONS)}"

        gst_str = self.f_gst_rate.get()
        valid, msg = validate_gst_rate(gst_str)
        if not valid:
            return False, msg

        try:
            float(self.f_purchase_rate.get() or '0')
        except ValueError:
            return False, "Purchase Rate must be a number."

        try:
            float(self.f_sale_rate.get() or '0')
        except ValueError:
            return False, "Sale Rate must be a number."

        try:
            float(self.f_reorder.get() or '0')
        except ValueError:
            return False, "Reorder Level must be a number."

        try:
            float(self.f_opening_stock.get() or '0')
        except ValueError:
            return False, "Opening Stock must be a number."

        return True, ""

    def _save_item(self):
        """Save or update the item from form data."""
        valid, msg = self._validate_form()
        if not valid:
            CTkMessagebox(title="Validation Error", message=msg, icon="cancel")
            return

        data = {
            'name': self.f_name.get().strip(),
            'category': self.f_category.get(),
            'hsn_code': self._get_hsn_code(),
            'unit': self.f_unit.get(),
            'thickness': self.f_thickness.get(),
            'size': self.f_size.get(),
            'gst_rate': float(self.f_gst_rate.get()),
            'purchase_rate': float(self.f_purchase_rate.get() or '0'),
            'sale_rate': float(self.f_sale_rate.get() or '0'),
            'reorder_level': float(self.f_reorder.get() or '0'),
            'opening_stock': float(self.f_opening_stock.get() or '0'),
            'description': self.f_desc.get().strip(),
        }

        if self.editing_id:
            success, message = update_item(self.editing_id, data)
        else:
            success, message = create_item(data)

        if success:
            CTkMessagebox(title="Success", message=message, icon="check")
            self.clear_form()
            self._load_data()
        else:
            CTkMessagebox(title="Error", message=message, icon="cancel")

    def _delete_selected(self):
        """Delete the selected item after confirmation."""
        selected = self.tree.selection()
        if not selected:
            CTkMessagebox(title="Warning", message="Please select an item to delete.", icon="warning")
            return

        values = self.tree.item(selected[0])['values']
        item_id = values[0]
        item_name = values[1]

        confirm = CTkMessagebox(
            title="Confirm Delete",
            message=f"Are you sure you want to deactivate item '{item_name}'?",
            icon="question", option_1="Yes", option_2="No",
        )
        if confirm.get() == "Yes":
            success, message = delete_item(int(item_id))
            if success:
                CTkMessagebox(title="Success", message=message, icon="check")
                self._load_data()
                self.clear_form()
            else:
                CTkMessagebox(title="Error", message=message, icon="cancel")

    def clear_form(self):
        """Reset all form fields to defaults."""
        self.editing_id = None
        self.btn_save.configure(text="💾 Save")
        for entry in [self.f_name, self.f_hsn_manual, self.f_desc]:
            entry.delete(0, "end")
        self.f_category.set("Plywood")
        self.f_unit.set("Sheets")
        self.f_thickness.set('')
        self.f_size.set('')
        self.f_gst_rate.set("18")
        for entry in [self.f_purchase_rate, self.f_sale_rate, self.f_reorder, self.f_opening_stock]:
            entry.delete(0, "end")
            entry.insert(0, "0")


# ═══════════════════════════════════════════════════════════════════════
#  GODOWN MASTER TAB
# ═══════════════════════════════════════════════════════════════════════

class GodownMasterTab(ctk.CTkFrame):
    """Godown (Warehouse) master with list and form."""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.editing_id = None
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        """Build the godown master list and form."""
        # ── Top Bar ────────────────────────────────────────────────
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(top_frame, text="🔍").pack(side="left", padx=(0, 5))
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._load_data())
        self.search_entry = ctk.CTkEntry(
            top_frame, textvariable=self.search_var,
            placeholder_text="Search godowns...", width=250,
        )
        self.search_entry.pack(side="left", padx=5)

        self.btn_add = ctk.CTkButton(
            top_frame, text="➕ Add Godown", width=130,
            fg_color="#2E7D32", hover_color="#1B5E20",
            command=self._show_add_form,
        )
        self.btn_add.pack(side="right", padx=5)

        self.btn_delete = ctk.CTkButton(
            top_frame, text="🗑 Delete", width=90,
            fg_color="#C62828", hover_color="#B71C1C",
            command=self._delete_selected,
        )
        self.btn_delete.pack(side="right", padx=5)

        # ── Main Split ────────────────────────────────────────────
        self.paned = ctk.CTkFrame(self, fg_color="transparent")
        self.paned.pack(fill="both", expand=True, padx=5, pady=5)
        self.paned.columnconfigure(0, weight=3)
        self.paned.columnconfigure(1, weight=2)
        self.paned.rowconfigure(0, weight=1)

        # ── List Panel ─────────────────────────────────────────────
        list_frame = ctk.CTkFrame(self.paned)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        columns = ("id", "name", "address")
        self.tree = ttk.Treeview(
            list_frame, columns=columns, show="headings", selectmode="browse",
        )

        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Name")
        self.tree.heading("address", text="Address")

        self.tree.column("id", width=50, minwidth=40, anchor="center")
        self.tree.column("name", width=200, minwidth=120)
        self.tree.column("address", width=300, minwidth=150)

        scrollbar_y = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar_y.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<Double-1>", self._on_double_click)

        # ── Form Panel ─────────────────────────────────────────────
        self.form_frame = ctk.CTkFrame(self.paned, corner_radius=8)
        self.form_frame.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(
            self.form_frame, text="Godown Details",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(15, 5))

        # Name *
        ctk.CTkLabel(self.form_frame, text="Name *").pack(anchor="w", padx=15, pady=(15, 0))
        self.f_name = ctk.CTkEntry(self.form_frame, width=280)
        self.f_name.pack(fill="x", padx=15, pady=2)

        # Address
        ctk.CTkLabel(self.form_frame, text="Address").pack(anchor="w", padx=15, pady=(10, 0))
        self.f_address = ctk.CTkEntry(self.form_frame, width=280)
        self.f_address.pack(fill="x", padx=15, pady=2)

        # Buttons
        btn_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=20)

        self.btn_save = ctk.CTkButton(
            btn_frame, text="💾 Save", width=100,
            fg_color="#2E7D32", hover_color="#1B5E20",
            command=self._save_godown,
        )
        self.btn_save.pack(side="left", padx=5)

        self.btn_cancel = ctk.CTkButton(
            btn_frame, text="✖ Cancel", width=100,
            fg_color="#555555", hover_color="#444444",
            command=self.clear_form,
        )
        self.btn_cancel.pack(side="left", padx=5)

    def _load_data(self):
        """Reload the godown list from the database."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        search = self.search_var.get()
        godowns = get_all_godowns(search=search)

        for g in godowns:
            self.tree.insert("", "end", values=(
                g['id'], g['name'], g.get('address', ''),
            ))

    def _on_double_click(self, event):
        """Load selected godown into the edit form."""
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])['values']
        godown_id = values[0]
        godown = get_godown_by_id(int(godown_id))
        if not godown:
            return

        self.editing_id = godown['id']
        self.clear_form()
        self.f_name.insert(0, godown.get('name', ''))
        self.f_address.insert(0, godown.get('address', ''))
        self.btn_save.configure(text="💾 Update")

    def _show_add_form(self):
        """Reset form for adding a new godown."""
        self.clear_form()
        self.editing_id = None
        self.btn_save.configure(text="💾 Save")
        self.f_name.focus_set()

    def _save_godown(self):
        """Save or update the godown from form data."""
        name = self.f_name.get().strip()
        if not name:
            CTkMessagebox(title="Validation Error", message="Godown Name is required.", icon="cancel")
            return

        data = {
            'name': name,
            'address': self.f_address.get().strip(),
        }

        if self.editing_id:
            success, message = update_godown(self.editing_id, data)
        else:
            success, message = create_godown(data)

        if success:
            CTkMessagebox(title="Success", message=message, icon="check")
            self.clear_form()
            self._load_data()
        else:
            CTkMessagebox(title="Error", message=message, icon="cancel")

    def _delete_selected(self):
        """Delete the selected godown after confirmation."""
        selected = self.tree.selection()
        if not selected:
            CTkMessagebox(title="Warning", message="Please select a godown to delete.", icon="warning")
            return

        values = self.tree.item(selected[0])['values']
        godown_id = values[0]
        godown_name = values[1]

        confirm = CTkMessagebox(
            title="Confirm Delete",
            message=f"Are you sure you want to deactivate godown '{godown_name}'?",
            icon="question", option_1="Yes", option_2="No",
        )
        if confirm.get() == "Yes":
            success, message = delete_godown(int(godown_id))
            if success:
                CTkMessagebox(title="Success", message=message, icon="check")
                self._load_data()
                self.clear_form()
            else:
                CTkMessagebox(title="Error", message=message, icon="cancel")

    def clear_form(self):
        """Reset all form fields."""
        self.editing_id = None
        self.btn_save.configure(text="💾 Save")
        self.f_name.delete(0, "end")
        self.f_address.delete(0, "end")


# ═══════════════════════════════════════════════════════════════════════
#  ACCOUNT MASTER TAB
# ═══════════════════════════════════════════════════════════════════════

class AccountMasterTab(ctk.CTkFrame):
    """Account (Chart of Accounts) master with list and form."""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.editing_id = None
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        """Build the account master list and form."""
        # ── Top Bar ────────────────────────────────────────────────
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(top_frame, text="🔍").pack(side="left", padx=(0, 5))
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._load_data())
        self.search_entry = ctk.CTkEntry(
            top_frame, textvariable=self.search_var,
            placeholder_text="Search accounts...", width=250,
        )
        self.search_entry.pack(side="left", padx=5)

        ctk.CTkLabel(top_frame, text="Group:").pack(side="left", padx=(15, 5))
        self.group_filter = ctk.CTkComboBox(
            top_frame, values=["All"] + ACCOUNT_GROUPS,
            width=180, command=lambda _: self._load_data(),
        )
        self.group_filter.set("All")
        self.group_filter.pack(side="left", padx=5)

        self.btn_add = ctk.CTkButton(
            top_frame, text="➕ Add Account", width=130,
            fg_color="#2E7D32", hover_color="#1B5E20",
            command=self._show_add_form,
        )
        self.btn_add.pack(side="right", padx=5)

        self.btn_delete = ctk.CTkButton(
            top_frame, text="🗑 Delete", width=90,
            fg_color="#C62828", hover_color="#B71C1C",
            command=self._delete_selected,
        )
        self.btn_delete.pack(side="right", padx=5)

        # ── Main Split ────────────────────────────────────────────
        self.paned = ctk.CTkFrame(self, fg_color="transparent")
        self.paned.pack(fill="both", expand=True, padx=5, pady=5)
        self.paned.columnconfigure(0, weight=3)
        self.paned.columnconfigure(1, weight=2)
        self.paned.rowconfigure(0, weight=1)

        # ── List Panel ─────────────────────────────────────────────
        list_frame = ctk.CTkFrame(self.paned)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        columns = ("id", "name", "group", "balance", "type", "system")
        self.tree = ttk.Treeview(
            list_frame, columns=columns, show="headings", selectmode="browse",
        )

        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Account Name")
        self.tree.heading("group", text="Group")
        self.tree.heading("balance", text="Opening Bal")
        self.tree.heading("type", text="Dr/Cr")
        self.tree.heading("system", text="System")

        self.tree.column("id", width=40, minwidth=40, anchor="center")
        self.tree.column("name", width=180, minwidth=120)
        self.tree.column("group", width=150, minwidth=100)
        self.tree.column("balance", width=100, minwidth=80, anchor="e")
        self.tree.column("type", width=50, minwidth=40, anchor="center")
        self.tree.column("system", width=60, minwidth=50, anchor="center")

        scrollbar_y = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar_y.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<Double-1>", self._on_double_click)

        # ── Form Panel ─────────────────────────────────────────────
        self.form_frame = ctk.CTkFrame(self.paned, corner_radius=8)
        self.form_frame.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(
            self.form_frame, text="Account Details",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(15, 5))

        # Name *
        ctk.CTkLabel(self.form_frame, text="Account Name *").pack(
            anchor="w", padx=15, pady=(15, 0),
        )
        self.f_name = ctk.CTkEntry(self.form_frame, width=280)
        self.f_name.pack(fill="x", padx=15, pady=2)

        # Group *
        ctk.CTkLabel(self.form_frame, text="Account Group *").pack(
            anchor="w", padx=15, pady=(10, 0),
        )
        self.f_group = ctk.CTkComboBox(
            self.form_frame, values=ACCOUNT_GROUPS, width=250,
        )
        self.f_group.set(ACCOUNT_GROUPS[0])
        self.f_group.pack(anchor="w", padx=15, pady=2)

        # Opening Balance
        ctk.CTkLabel(self.form_frame, text="Opening Balance (₹)").pack(
            anchor="w", padx=15, pady=(10, 0),
        )
        bal_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        bal_frame.pack(anchor="w", padx=15, pady=2)
        self.f_opening_bal = ctk.CTkEntry(bal_frame, width=150)
        self.f_opening_bal.insert(0, "0")
        self.f_opening_bal.pack(side="left", padx=(0, 5))
        self.f_bal_type = ctk.CTkComboBox(bal_frame, values=["Dr", "Cr"], width=70)
        self.f_bal_type.set("Dr")
        self.f_bal_type.pack(side="left")

        # System account notice
        self.system_notice = ctk.CTkLabel(
            self.form_frame, text="",
            text_color="#FFA000", font=ctk.CTkFont(size=11),
        )
        self.system_notice.pack(anchor="w", padx=15, pady=(10, 0))

        # Buttons
        btn_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=20)

        self.btn_save = ctk.CTkButton(
            btn_frame, text="💾 Save", width=100,
            fg_color="#2E7D32", hover_color="#1B5E20",
            command=self._save_account,
        )
        self.btn_save.pack(side="left", padx=5)

        self.btn_cancel = ctk.CTkButton(
            btn_frame, text="✖ Cancel", width=100,
            fg_color="#555555", hover_color="#444444",
            command=self.clear_form,
        )
        self.btn_cancel.pack(side="left", padx=5)

    def _load_data(self):
        """Reload the account list from the database."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        search = self.search_var.get()
        group_filter = self.group_filter.get()
        accounts = get_all_accounts(search=search, group_name=group_filter)

        for a in accounts:
            self.tree.insert("", "end", values=(
                a['id'], a['name'], a['group_name'],
                format_inr(a.get('opening_balance', 0)),
                a.get('balance_type', 'Dr'),
                "✔" if a.get('is_system') else "",
            ))

    def _on_double_click(self, event):
        """Load selected account into the edit form."""
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])['values']
        account_id = values[0]
        account = get_account_by_id(int(account_id))
        if not account:
            return

        self.editing_id = account['id']
        self.clear_form()
        self.f_name.insert(0, account.get('name', ''))
        self.f_group.set(account.get('group_name', ACCOUNT_GROUPS[0]))
        self.f_opening_bal.delete(0, "end")
        self.f_opening_bal.insert(0, str(account.get('opening_balance', 0)))
        self.f_bal_type.set(account.get('balance_type', 'Dr'))
        self.btn_save.configure(text="💾 Update")

        if account.get('is_system'):
            self.system_notice.configure(
                text="⚠ System account — name and group are locked.",
            )
            self.f_name.configure(state="disabled")
            self.f_group.configure(state="disabled")
        else:
            self.system_notice.configure(text="")
            self.f_name.configure(state="normal")
            self.f_group.configure(state="normal")

    def _show_add_form(self):
        """Reset form for adding a new account."""
        self.clear_form()
        self.editing_id = None
        self.btn_save.configure(text="💾 Save")
        self.f_name.configure(state="normal")
        self.f_group.configure(state="normal")
        self.system_notice.configure(text="")
        self.f_name.focus_set()

    def _save_account(self):
        """Save or update the account from form data."""
        name = self.f_name.get().strip()
        if not name:
            CTkMessagebox(title="Validation Error", message="Account Name is required.", icon="cancel")
            return

        group = self.f_group.get()
        if group not in ACCOUNT_GROUPS:
            CTkMessagebox(
                title="Validation Error",
                message="Please select a valid Account Group.", icon="cancel",
            )
            return

        try:
            opening_bal = float(self.f_opening_bal.get() or '0')
        except ValueError:
            CTkMessagebox(
                title="Validation Error",
                message="Opening Balance must be a number.", icon="cancel",
            )
            return

        data = {
            'name': name,
            'group_name': group,
            'opening_balance': opening_bal,
            'balance_type': self.f_bal_type.get(),
        }

        if self.editing_id:
            success, message = update_account(self.editing_id, data)
        else:
            success, message = create_account(data)

        if success:
            CTkMessagebox(title="Success", message=message, icon="check")
            self.clear_form()
            self._load_data()
        else:
            CTkMessagebox(title="Error", message=message, icon="cancel")

    def _delete_selected(self):
        """Delete the selected account after confirmation."""
        selected = self.tree.selection()
        if not selected:
            CTkMessagebox(title="Warning", message="Please select an account to delete.", icon="warning")
            return

        values = self.tree.item(selected[0])['values']
        account_id = values[0]
        account_name = values[1]

        confirm = CTkMessagebox(
            title="Confirm Delete",
            message=f"Are you sure you want to deactivate account '{account_name}'?",
            icon="question", option_1="Yes", option_2="No",
        )
        if confirm.get() == "Yes":
            success, message = delete_account(int(account_id))
            if success:
                CTkMessagebox(title="Success", message=message, icon="check")
                self._load_data()
                self.clear_form()
            else:
                CTkMessagebox(title="Error", message=message, icon="cancel")

    def clear_form(self):
        """Reset all form fields."""
        self.editing_id = None
        self.btn_save.configure(text="💾 Save")
        self.f_name.configure(state="normal")
        self.f_group.configure(state="normal")
        self.f_name.delete(0, "end")
        self.f_group.set(ACCOUNT_GROUPS[0])
        self.f_opening_bal.delete(0, "end")
        self.f_opening_bal.insert(0, "0")
        self.f_bal_type.set("Dr")
        self.system_notice.configure(text="")
