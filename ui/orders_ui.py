"""
Orders UI for PlywoodPro.
Tabbed interface: Sales Orders | Purchase Orders.
Each tab shows a list view and a form view for creating new orders.
"""

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from tkinter import ttk, StringVar

from modules.sales import (
    create_sales_order, confirm_sales_order,
    get_sales_orders, convert_so_to_invoice,
)
from modules.purchase import (
    create_purchase_order, confirm_purchase_order,
    get_purchase_orders,
)
from modules.masters import get_all_parties, get_all_items, get_all_godowns
from utils.helpers import format_inr, format_date_display, today_db
from utils.date_picker import DatePickerEntry


class OrdersUI(ctk.CTkFrame):
    """Sales Orders & Purchase Orders management screen."""

    def __init__(self, parent, app=None, tab='sales'):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.initial_tab = tab
        self._build_ui()

    def _build_ui(self):
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=(20, 5))
        ctk.CTkLabel(title_frame, text="📋  Orders",
                      font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")

        self.tabs = ctk.CTkTabview(self, corner_radius=8)
        self.tabs.pack(fill="both", expand=True, padx=20, pady=10)

        self.tab_so = self.tabs.add("Sales Orders")
        self.tab_po = self.tabs.add("Purchase Orders")

        self._build_so_tab()
        self._build_po_tab()

        if self.initial_tab == 'purchase':
            self.tabs.set("Purchase Orders")

    # ══════════════════════════════════════════════════════════════
    #  SALES ORDERS TAB
    # ══════════════════════════════════════════════════════════════

    def _build_so_tab(self):
        top = ctk.CTkFrame(self.tab_so, fg_color="transparent")
        top.pack(fill="x", pady=5)

        ctk.CTkButton(top, text="➕ New Sales Order", fg_color="#2E7D32",
                       hover_color="#1B5E20", command=self._show_so_form).pack(side="left", padx=5)

        self.so_search = ctk.CTkEntry(top, placeholder_text="Search...", width=200)
        self.so_search.pack(side="right", padx=5)
        self.so_search.bind("<Return>", lambda e: self._load_so_list())

        ctk.CTkButton(top, text="🔍", width=30, command=self._load_so_list).pack(side="right")

        # Treeview
        tree_frame = ctk.CTkFrame(self.tab_so)
        tree_frame.pack(fill="both", expand=True, pady=5)

        cols = ("id", "order_no", "date", "party", "total", "status")
        self.so_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=15)
        for c, h, w in zip(cols,
                            ("ID", "Order No", "Date", "Customer", "Total", "Status"),
                            (40, 120, 90, 200, 110, 90)):
            self.so_tree.heading(c, text=h)
            self.so_tree.column(c, width=w, anchor="center" if c != "party" else "w")
        self.so_tree.column("id", width=0, stretch=False)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.so_tree.yview)
        self.so_tree.configure(yscrollcommand=scrollbar.set)
        self.so_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Action buttons
        btn_frame = ctk.CTkFrame(self.tab_so, fg_color="transparent")
        btn_frame.pack(fill="x", pady=5)
        ctk.CTkButton(btn_frame, text="✅ Confirm", fg_color="#1565C0",
                       command=self._confirm_so).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📄 Convert to Invoice", fg_color="#7B1FA2",
                       command=self._convert_so).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="🔄 Refresh", fg_color="#555",
                       command=self._load_so_list).pack(side="right", padx=5)

        self._load_so_list()

    def _load_so_list(self):
        for row in self.so_tree.get_children():
            self.so_tree.delete(row)
        search = self.so_search.get().strip() if hasattr(self, 'so_search') else ''
        orders = get_sales_orders(search=search)
        for i, o in enumerate(orders):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.so_tree.insert("", "end", values=(
                o['id'], o['voucher_no'], format_date_display(o['date']),
                o.get('party_name', ''), format_inr(o['grand_total']),
                o['status'],
            ), tags=(tag,))
        self.so_tree.tag_configure('even', background='#1a1a2e')
        self.so_tree.tag_configure('odd', background='#16213e')

    def _confirm_so(self):
        sel = self.so_tree.selection()
        if not sel:
            CTkMessagebox(title="Select", message="Select an order to confirm.", icon="info")
            return
        vid = self.so_tree.item(sel[0])['values'][0]
        ok, msg = confirm_sales_order(int(vid))
        CTkMessagebox(title="Result", message=msg, icon="check" if ok else "cancel")
        self._load_so_list()

    def _convert_so(self):
        sel = self.so_tree.selection()
        if not sel:
            CTkMessagebox(title="Select", message="Select an order to convert.", icon="info")
            return
        vid = self.so_tree.item(sel[0])['values'][0]
        ok, msg, _ = convert_so_to_invoice(int(vid))
        CTkMessagebox(title="Result", message=msg, icon="check" if ok else "cancel")
        self._load_so_list()

    def _show_so_form(self):
        _OrderFormPopup(self, order_type='Sales Order', save_fn=self._save_so)

    def _save_so(self, header, items):
        ok, msg, _ = create_sales_order(header, items)
        CTkMessagebox(title="Result", message=msg, icon="check" if ok else "cancel")
        self._load_so_list()

    # ══════════════════════════════════════════════════════════════
    #  PURCHASE ORDERS TAB
    # ══════════════════════════════════════════════════════════════

    def _build_po_tab(self):
        top = ctk.CTkFrame(self.tab_po, fg_color="transparent")
        top.pack(fill="x", pady=5)

        ctk.CTkButton(top, text="➕ New Purchase Order", fg_color="#1565C0",
                       hover_color="#0D47A1", command=self._show_po_form).pack(side="left", padx=5)

        self.po_search = ctk.CTkEntry(top, placeholder_text="Search...", width=200)
        self.po_search.pack(side="right", padx=5)
        self.po_search.bind("<Return>", lambda e: self._load_po_list())

        ctk.CTkButton(top, text="🔍", width=30, command=self._load_po_list).pack(side="right")

        tree_frame = ctk.CTkFrame(self.tab_po)
        tree_frame.pack(fill="both", expand=True, pady=5)

        cols = ("id", "order_no", "date", "party", "total", "status")
        self.po_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=15)
        for c, h, w in zip(cols,
                            ("ID", "Order No", "Date", "Supplier", "Total", "Status"),
                            (40, 120, 90, 200, 110, 90)):
            self.po_tree.heading(c, text=h)
            self.po_tree.column(c, width=w, anchor="center" if c != "party" else "w")
        self.po_tree.column("id", width=0, stretch=False)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.po_tree.yview)
        self.po_tree.configure(yscrollcommand=scrollbar.set)
        self.po_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        btn_frame = ctk.CTkFrame(self.tab_po, fg_color="transparent")
        btn_frame.pack(fill="x", pady=5)
        ctk.CTkButton(btn_frame, text="✅ Confirm", fg_color="#2E7D32",
                       command=self._confirm_po).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="🔄 Refresh", fg_color="#555",
                       command=self._load_po_list).pack(side="right", padx=5)

        self._load_po_list()

    def _load_po_list(self):
        for row in self.po_tree.get_children():
            self.po_tree.delete(row)
        search = self.po_search.get().strip() if hasattr(self, 'po_search') else ''
        orders = get_purchase_orders(search=search)
        for i, o in enumerate(orders):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.po_tree.insert("", "end", values=(
                o['id'], o['voucher_no'], format_date_display(o['date']),
                o.get('party_name', ''), format_inr(o['grand_total']),
                o['status'],
            ), tags=(tag,))
        self.po_tree.tag_configure('even', background='#1a1a2e')
        self.po_tree.tag_configure('odd', background='#16213e')

    def _confirm_po(self):
        sel = self.po_tree.selection()
        if not sel:
            CTkMessagebox(title="Select", message="Select an order to confirm.", icon="info")
            return
        vid = self.po_tree.item(sel[0])['values'][0]
        ok, msg = confirm_purchase_order(int(vid))
        CTkMessagebox(title="Result", message=msg, icon="check" if ok else "cancel")
        self._load_po_list()

    def _show_po_form(self):
        _OrderFormPopup(self, order_type='Purchase Order', save_fn=self._save_po)

    def _save_po(self, header, items):
        ok, msg, _ = create_purchase_order(header, items)
        CTkMessagebox(title="Result", message=msg, icon="check" if ok else "cancel")
        self._load_po_list()


# ══════════════════════════════════════════════════════════════════════
#  ORDER FORM POPUP (shared for SO and PO)
# ══════════════════════════════════════════════════════════════════════

class _OrderFormPopup(ctk.CTkToplevel):
    """Popup form for creating a new Sales Order or Purchase Order."""

    def __init__(self, parent, order_type: str, save_fn):
        super().__init__(parent)
        self.title(f"New {order_type}")
        self.geometry("850x550")
        self.resizable(True, True)
        self.attributes("-topmost", True)
        self.grab_set()

        self.order_type = order_type
        self.save_fn = save_fn
        self.line_items = []

        is_sales = order_type == 'Sales Order'
        parties = get_all_parties(party_type='customer') if is_sales else get_all_parties(party_type='supplier')
        self.party_map = {p['name']: p['id'] for p in parties}
        self.items_list = get_all_items()
        self.item_map = {it['name']: it for it in self.items_list}
        godowns = get_all_godowns()
        self.godown_map = {g['name']: g['id'] for g in godowns}

        self._build_form(is_sales)

    def _build_form(self, is_sales):
        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=15, pady=10)
        hdr.columnconfigure(1, weight=1)
        hdr.columnconfigure(3, weight=1)

        ctk.CTkLabel(hdr, text="Party *").grid(row=0, column=0, sticky="w", padx=5)
        self.cmb_party = ctk.CTkComboBox(hdr, values=list(self.party_map.keys()), width=250)
        self.cmb_party.set('')
        self.cmb_party.grid(row=0, column=1, sticky="ew", padx=5)

        ctk.CTkLabel(hdr, text="Date *").grid(row=0, column=2, sticky="w", padx=5)
        self.dp_date = DatePickerEntry(hdr, width=130)
        self.dp_date.grid(row=0, column=3, sticky="w", padx=5)

        ctk.CTkLabel(hdr, text="Godown").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.cmb_godown = ctk.CTkComboBox(hdr, values=list(self.godown_map.keys()), width=180)
        if self.godown_map:
            self.cmb_godown.set(list(self.godown_map.keys())[0])
        self.cmb_godown.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        ctk.CTkLabel(hdr, text="Reference").grid(row=1, column=2, sticky="w", padx=5, pady=5)
        self.entry_ref = ctk.CTkEntry(hdr, width=180)
        self.entry_ref.grid(row=1, column=3, sticky="w", padx=5, pady=5)

        # Line item entry
        line_frame = ctk.CTkFrame(self, fg_color="transparent")
        line_frame.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(line_frame, text="Item").pack(side="left", padx=3)
        self.cmb_item = ctk.CTkComboBox(line_frame, values=list(self.item_map.keys()), width=200)
        self.cmb_item.set('')
        self.cmb_item.pack(side="left", padx=3)

        ctk.CTkLabel(line_frame, text="Qty").pack(side="left", padx=3)
        self.entry_qty = ctk.CTkEntry(line_frame, width=60, placeholder_text="0")
        self.entry_qty.pack(side="left", padx=3)

        ctk.CTkLabel(line_frame, text="Rate").pack(side="left", padx=3)
        self.entry_rate = ctk.CTkEntry(line_frame, width=80, placeholder_text="0.00")
        self.entry_rate.pack(side="left", padx=3)

        ctk.CTkLabel(line_frame, text="Disc%").pack(side="left", padx=3)
        self.entry_disc = ctk.CTkEntry(line_frame, width=50, placeholder_text="0")
        self.entry_disc.pack(side="left", padx=3)

        ctk.CTkButton(line_frame, text="Add Line", width=80, fg_color="#2E7D32",
                       command=self._add_line).pack(side="left", padx=5)

        # Items treeview
        tree_frame = ctk.CTkFrame(self)
        tree_frame.pack(fill="both", expand=True, padx=15, pady=5)

        cols = ("item", "qty", "rate", "disc", "total")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=8)
        for c, h, w in zip(cols, ("Item", "Qty", "Rate", "Disc%", "Total"),
                            (200, 70, 90, 60, 100)):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor="e" if c != "item" else "w")
        self.tree.pack(fill="both", expand=True)

        # Total + Save
        bot = ctk.CTkFrame(self, fg_color="transparent")
        bot.pack(fill="x", padx=15, pady=10)

        self.lbl_total = ctk.CTkLabel(bot, text="Grand Total: ₹ 0.00",
                                       font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_total.pack(side="left")

        ctk.CTkButton(bot, text="❌ Remove Selected", fg_color="#B71C1C",
                       command=self._remove_line).pack(side="right", padx=5)
        ctk.CTkButton(bot, text="💾 Save Order", fg_color="#2E7D32", width=140,
                       font=ctk.CTkFont(weight="bold"),
                       command=self._save).pack(side="right", padx=5)

    def _add_line(self):
        item_name = self.cmb_item.get().strip()
        if item_name not in self.item_map:
            CTkMessagebox(title="Error", message="Select a valid item.", icon="cancel")
            return
        try:
            qty = float(self.entry_qty.get() or 0)
            rate = float(self.entry_rate.get() or 0)
            disc_pct = float(self.entry_disc.get() or 0)
        except ValueError:
            CTkMessagebox(title="Error", message="Enter valid numbers.", icon="cancel")
            return
        if qty <= 0 or rate <= 0:
            CTkMessagebox(title="Error", message="Qty and Rate must be > 0.", icon="cancel")
            return

        item = self.item_map[item_name]
        gross = qty * rate
        disc_amt = gross * disc_pct / 100
        total = gross - disc_amt

        self.line_items.append({
            'item_id': item['id'], 'description': item['name'],
            'hsn_code': item.get('hsn_code', ''), 'qty': qty,
            'unit': item.get('unit', ''), 'rate': rate,
            'discount_pct': disc_pct,
        })

        self.tree.insert("", "end", values=(
            item_name, f"{qty:.2f}", f"{rate:.2f}", f"{disc_pct:.1f}",
            format_inr(total),
        ))
        self._update_total()

        # Clear inputs
        self.entry_qty.delete(0, "end")
        self.entry_rate.delete(0, "end")
        self.entry_disc.delete(0, "end")
        self.cmb_item.set('')

    def _remove_line(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        self.tree.delete(sel[0])
        if 0 <= idx < len(self.line_items):
            self.line_items.pop(idx)
        self._update_total()

    def _update_total(self):
        total = 0
        for item in self.line_items:
            gross = item['qty'] * item['rate']
            disc = gross * item['discount_pct'] / 100
            total += gross - disc
        self.lbl_total.configure(text=f"Grand Total: {format_inr(total)}")

    def _save(self):
        party_name = self.cmb_party.get().strip()
        if party_name not in self.party_map:
            CTkMessagebox(title="Error", message="Select a valid party.", icon="cancel")
            return
        if not self.line_items:
            CTkMessagebox(title="Error", message="Add at least one line item.", icon="cancel")
            return

        godown_name = self.cmb_godown.get().strip()
        godown_id = self.godown_map.get(godown_name, 1)

        header = {
            'party_id': self.party_map[party_name],
            'date': self.dp_date.get_date(),
            'due_date': '',
            'reference_no': self.entry_ref.get().strip(),
            'narration': '',
            'godown_id': godown_id,
        }

        self.save_fn(header, self.line_items)
        self.destroy()
