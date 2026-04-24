"""
Inventory UI for PlywoodPro — 3 tabbed screens:
Tab 1: Stock View, Tab 2: GRN Form, Tab 3: Stock Adjustment
"""

import customtkinter as ctk
from tkinter import ttk
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from CTkMessagebox import CTkMessagebox

from modules.masters import get_all_parties, get_all_items, get_all_godowns
from modules.inventory import (
    get_stock_summary, create_grn, create_stock_adjustment,
    create_godown_transfer, ADJUSTMENT_REASONS,
)
from utils.helpers import format_inr
from utils.date_picker import DatePickerEntry

ACCENT = "#2E7D32"
ACCENT_HOVER = "#1B5E20"
BLUE = "#1565C0"

def _d(v):
    try: return Decimal(str(v)) if v else Decimal("0")
    except: return Decimal("0")


class InventoryUI(ctk.CTkFrame):
    def __init__(self, parent, app=None):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.items = get_all_items()
        self.godowns = get_all_godowns()
        self.grn_lines = []

        title = ctk.CTkLabel(self, text="Inventory Management",
                             font=ctk.CTkFont(size=22, weight="bold"), text_color=ACCENT)
        title.pack(padx=10, pady=(10,5), anchor="w")

        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=5)
        self.tabview.add("Stock View")
        self.tabview.add("GRN")
        self.tabview.add("Stock Adjustment")

        self._build_stock_view(self.tabview.tab("Stock View"))
        self._build_grn_form(self.tabview.tab("GRN"))
        self._build_adjustment_form(self.tabview.tab("Stock Adjustment"))

    # ══════════════════════════════════════════════════════════
    #  TAB 1 — STOCK VIEW
    # ══════════════════════════════════════════════════════════
    def _build_stock_view(self, tab):
        filt = ctk.CTkFrame(tab, fg_color="transparent")
        filt.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(filt, text="Godown:").pack(side="left")
        self.sv_godown = ctk.StringVar(value="All")
        gn = ["All"] + [g['name'] for g in self.godowns]
        ctk.CTkComboBox(filt, variable=self.sv_godown, values=gn, width=180).pack(side="left", padx=5)

        ctk.CTkLabel(filt, text="Category:").pack(side="left", padx=(15,0))
        cats = ["All"] + sorted(set(i.get('category','') for i in self.items if i.get('category')))
        self.sv_cat = ctk.StringVar(value="All")
        ctk.CTkComboBox(filt, variable=self.sv_cat, values=cats, width=160).pack(side="left", padx=5)

        ctk.CTkButton(filt, text="Refresh", fg_color=ACCENT, hover_color=ACCENT_HOVER,
                       width=100, command=self._refresh_stock).pack(side="left", padx=10)

        cols = ('item','category','hsn','unit','godown','qty','reorder','status')
        tc = ctk.CTkFrame(tab, fg_color="transparent")
        tc.pack(fill="both", expand=True, padx=10, pady=5)

        self.sv_tree = ttk.Treeview(tc, columns=cols, show='headings', height=14)
        heads = {'item':('Item',160),'category':('Category',100),'hsn':('HSN',60),
                 'unit':('Unit',50),'godown':('Godown',100),'qty':('Qty',70),
                 'reorder':('Reorder Lvl',80),'status':('Status',90)}
        for c,(t,w) in heads.items():
            self.sv_tree.heading(c, text=t)
            self.sv_tree.column(c, width=w, anchor='e' if c in ('qty','reorder') else 'w')

        self.sv_tree.tag_configure('low', background='#FFCDD2')
        sb = ttk.Scrollbar(tc, orient="vertical", command=self.sv_tree.yview)
        self.sv_tree.configure(yscrollcommand=sb.set)
        self.sv_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._refresh_stock()

    def _refresh_stock(self):
        self.sv_tree.delete(*self.sv_tree.get_children())
        gid = 0
        gname = self.sv_godown.get()
        if gname != "All":
            for g in self.godowns:
                if g['name'] == gname: gid = g['id']; break
        rows = get_stock_summary(godown_id=gid, category=self.sv_cat.get())
        for r in rows:
            tag = ('low',) if r.get('is_low_stock') and r.get('reorder_level',0) > 0 else ()
            status = "LOW STOCK" if (r.get('is_low_stock') and r.get('reorder_level',0) > 0) else "OK"
            self.sv_tree.insert('','end', values=(
                r['item_name'], r.get('category',''), r.get('hsn_code',''),
                r.get('unit',''), r.get('godown_name',''),
                f"{r['qty']:.2f}", r.get('reorder_level',0), status
            ), tags=tag)

    # ══════════════════════════════════════════════════════════
    #  TAB 2 — GRN FORM
    # ══════════════════════════════════════════════════════════
    def _build_grn_form(self, tab):
        hdr = ctk.CTkFrame(tab, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(hdr, text="Supplier:").pack(side="left")
        self.grn_suppliers = get_all_parties(party_type='supplier')
        snames = [s['name'] for s in self.grn_suppliers]
        self.grn_party = ctk.StringVar()
        ctk.CTkComboBox(hdr, variable=self.grn_party, values=snames, width=250).pack(side="left", padx=5)
        if snames: self.grn_party.set(snames[0])

        ctk.CTkLabel(hdr, text="Date:").pack(side="left", padx=(15,0))
        self.grn_date = DatePickerEntry(hdr, width=130)
        self.grn_date.pack(side="left", padx=5)

        ctk.CTkLabel(hdr, text="Ref:").pack(side="left", padx=(15,0))
        self.grn_ref = ctk.StringVar()
        ctk.CTkEntry(hdr, textvariable=self.grn_ref, width=130).pack(side="left", padx=5)

        ctk.CTkLabel(hdr, text="Godown:").pack(side="left", padx=(15,0))
        self.grn_godown = ctk.StringVar()
        gn = [g['name'] for g in self.godowns]
        ctk.CTkComboBox(hdr, variable=self.grn_godown, values=gn, width=160).pack(side="left", padx=5)
        if gn: self.grn_godown.set(gn[0])

        # Add row
        ar = ctk.CTkFrame(tab, fg_color="transparent")
        ar.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(ar, text="Item:").pack(side="left")
        inames = [f"{i['name']} [{i['hsn_code']}]" for i in self.items]
        self.grn_item = ctk.StringVar()
        ctk.CTkComboBox(ar, variable=self.grn_item, values=inames, width=250).pack(side="left", padx=5)
        if inames: self.grn_item.set(inames[0])

        ctk.CTkLabel(ar, text="Qty:").pack(side="left")
        self.grn_qty = ctk.StringVar(value="1")
        ctk.CTkEntry(ar, textvariable=self.grn_qty, width=70).pack(side="left", padx=5)

        ctk.CTkLabel(ar, text="Rate:").pack(side="left")
        self.grn_rate = ctk.StringVar(value="0")
        ctk.CTkEntry(ar, textvariable=self.grn_rate, width=90).pack(side="left", padx=5)

        ctk.CTkButton(ar, text="+ Add", fg_color=BLUE, width=80, command=self._grn_add).pack(side="left", padx=10)
        ctk.CTkButton(ar, text="Delete", fg_color="#C62828", width=80, command=self._grn_del).pack(side="left")

        # Tree
        tc = ctk.CTkFrame(tab, fg_color="transparent")
        tc.pack(fill="both", expand=True, padx=10, pady=5)
        cols = ('item','hsn','qty','unit','rate','total')
        self.grn_tree = ttk.Treeview(tc, columns=cols, show='headings', height=6)
        for c,t,w in [('item','Item',180),('hsn','HSN',60),('qty','Qty',60),
                       ('unit','Unit',50),('rate','Rate',80),('total','Total',100)]:
            self.grn_tree.heading(c, text=t)
            self.grn_tree.column(c, width=w, anchor='e' if c in ('qty','rate','total') else 'w')
        self.grn_tree.pack(side="left", fill="both", expand=True)

        # Buttons
        bf = ctk.CTkFrame(tab, fg_color="transparent")
        bf.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(bf, text="Save & Confirm GRN", fg_color=ACCENT,
                       hover_color=ACCENT_HOVER, width=180, command=self._grn_save).pack(side="left", padx=5)
        ctk.CTkButton(bf, text="Clear", fg_color="#757575", width=80,
                       command=self._grn_clear).pack(side="left", padx=5)

    def _get_item_by_display(self, val):
        for i in self.items:
            if f"{i['name']} [{i['hsn_code']}]" == val: return i
        return None

    def _grn_add(self):
        item = self._get_item_by_display(self.grn_item.get())
        if not item:
            CTkMessagebox(title="Error", message="Select an item.", icon="cancel"); return
        try:
            qty = float(self.grn_qty.get()); rate = float(self.grn_rate.get())
        except:
            CTkMessagebox(title="Error", message="Invalid qty/rate.", icon="cancel"); return
        if qty <= 0:
            CTkMessagebox(title="Error", message="Qty must be > 0.", icon="cancel"); return

        self.grn_lines.append({'item_id':item['id'],'description':item['name'],
            'hsn_code':item.get('hsn_code',''),'qty':qty,'unit':item.get('unit',''),'rate':rate})
        self._grn_refresh()

    def _grn_del(self):
        sel = self.grn_tree.selection()
        if sel:
            idx = self.grn_tree.index(sel[0])
            if 0 <= idx < len(self.grn_lines): self.grn_lines.pop(idx)
            self._grn_refresh()

    def _grn_refresh(self):
        self.grn_tree.delete(*self.grn_tree.get_children())
        for r in self.grn_lines:
            t = r['qty'] * r['rate']
            self.grn_tree.insert('','end', values=(
                r['description'], r['hsn_code'], f"{r['qty']:.2f}",
                r['unit'], f"{r['rate']:.2f}", format_inr(t)))

    def _grn_save(self):
        if not self.grn_lines:
            CTkMessagebox(title="Error", message="Add items first.", icon="cancel"); return
        party = None
        for s in self.grn_suppliers:
            if s['name'] == self.grn_party.get(): party = s; break
        gid = 1
        for g in self.godowns:
            if g['name'] == self.grn_godown.get(): gid = g['id']; break

        header = {'party_id': party['id'] if party else None, 'date': self.grn_date.get_date(),
                  'reference_no': self.grn_ref.get(), 'narration': 'GRN', 'godown_id': gid}
        ok, msg, vid = create_grn(header, self.grn_lines)
        if ok:
            CTkMessagebox(title="Success", message=msg, icon="check")
            self._grn_clear(); self._refresh_stock()
        else:
            CTkMessagebox(title="Error", message=msg, icon="cancel")

    def _grn_clear(self):
        self.grn_lines.clear(); self._grn_refresh()
        self.grn_qty.set("1"); self.grn_rate.set("0"); self.grn_ref.set("")

    # ══════════════════════════════════════════════════════════
    #  TAB 3 — STOCK ADJUSTMENT + GODOWN TRANSFER
    # ══════════════════════════════════════════════════════════
    def _build_adjustment_form(self, tab):
        # ── Adjustment Section ──
        ctk.CTkLabel(tab, text="Stock Adjustment", font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=ACCENT).pack(padx=10, pady=(10,5), anchor="w")
        af = ctk.CTkFrame(tab, corner_radius=10)
        af.pack(fill="x", padx=10, pady=5)

        r1 = ctk.CTkFrame(af, fg_color="transparent"); r1.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(r1, text="Item:").pack(side="left")
        inames = [f"{i['name']} [{i['hsn_code']}]" for i in self.items]
        self.adj_item = ctk.StringVar()
        ctk.CTkComboBox(r1, variable=self.adj_item, values=inames, width=250).pack(side="left", padx=5)
        if inames: self.adj_item.set(inames[0])

        ctk.CTkLabel(r1, text="Godown:").pack(side="left", padx=(15,0))
        gn = [g['name'] for g in self.godowns]
        self.adj_godown = ctk.StringVar()
        ctk.CTkComboBox(r1, variable=self.adj_godown, values=gn, width=160).pack(side="left", padx=5)
        if gn: self.adj_godown.set(gn[0])

        r2 = ctk.CTkFrame(af, fg_color="transparent"); r2.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(r2, text="Type:").pack(side="left")
        self.adj_type = ctk.StringVar(value="Reduce")
        ctk.CTkComboBox(r2, variable=self.adj_type, values=["Add","Reduce"], width=100).pack(side="left", padx=5)

        ctk.CTkLabel(r2, text="Qty:").pack(side="left", padx=(15,0))
        self.adj_qty = ctk.StringVar(value="1")
        ctk.CTkEntry(r2, textvariable=self.adj_qty, width=70).pack(side="left", padx=5)

        ctk.CTkLabel(r2, text="Reason:").pack(side="left", padx=(15,0))
        self.adj_reason = ctk.StringVar(value=ADJUSTMENT_REASONS[0])
        ctk.CTkComboBox(r2, variable=self.adj_reason, values=ADJUSTMENT_REASONS, width=160).pack(side="left", padx=5)

        ctk.CTkLabel(r2, text="Narration:").pack(side="left", padx=(15,0))
        self.adj_narr = ctk.StringVar()
        ctk.CTkEntry(r2, textvariable=self.adj_narr, width=180).pack(side="left", padx=5)

        ctk.CTkButton(af, text="Save Adjustment", fg_color=ACCENT, hover_color=ACCENT_HOVER,
                       width=160, command=self._save_adj).pack(padx=10, pady=10, anchor="w")

        # ── Transfer Section ──
        ctk.CTkLabel(tab, text="Godown Transfer", font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=BLUE).pack(padx=10, pady=(15,5), anchor="w")
        tf = ctk.CTkFrame(tab, corner_radius=10)
        tf.pack(fill="x", padx=10, pady=5)

        r3 = ctk.CTkFrame(tf, fg_color="transparent"); r3.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(r3, text="Item:").pack(side="left")
        self.tr_item = ctk.StringVar()
        ctk.CTkComboBox(r3, variable=self.tr_item, values=inames, width=250).pack(side="left", padx=5)
        if inames: self.tr_item.set(inames[0])

        ctk.CTkLabel(r3, text="From:").pack(side="left", padx=(15,0))
        self.tr_from = ctk.StringVar()
        ctk.CTkComboBox(r3, variable=self.tr_from, values=gn, width=140).pack(side="left", padx=5)
        if gn: self.tr_from.set(gn[0])

        ctk.CTkLabel(r3, text="To:").pack(side="left", padx=(15,0))
        self.tr_to = ctk.StringVar()
        ctk.CTkComboBox(r3, variable=self.tr_to, values=gn, width=140).pack(side="left", padx=5)
        if len(gn) > 1: self.tr_to.set(gn[1])

        ctk.CTkLabel(r3, text="Qty:").pack(side="left", padx=(15,0))
        self.tr_qty = ctk.StringVar(value="1")
        ctk.CTkEntry(r3, textvariable=self.tr_qty, width=70).pack(side="left", padx=5)

        ctk.CTkButton(tf, text="Transfer Stock", fg_color=BLUE, hover_color="#0D47A1",
                       width=160, command=self._save_transfer).pack(padx=10, pady=10, anchor="w")

    def _save_adj(self):
        item = self._get_item_by_display(self.adj_item.get())
        if not item:
            CTkMessagebox(title="Error", message="Select an item.", icon="cancel"); return
        gid = 1
        for g in self.godowns:
            if g['name'] == self.adj_godown.get(): gid = g['id']; break
        try: qty = float(self.adj_qty.get())
        except:
            CTkMessagebox(title="Error", message="Invalid quantity.", icon="cancel"); return

        atype = self.adj_type.get()
        if atype == 'Reduce':
            resp = CTkMessagebox(title="Confirm", message=f"Reduce {qty} units? Reason: {self.adj_reason.get()}",
                                  icon="question", option_1="Yes", option_2="No")
            if resp.get() != "Yes": return

        ok, msg = create_stock_adjustment(item['id'], gid, atype, qty,
                                           self.adj_reason.get(), self.adj_narr.get())
        if ok:
            CTkMessagebox(title="Success", message=msg, icon="check")
            self._refresh_stock()
        else:
            CTkMessagebox(title="Error", message=msg, icon="cancel")

    def _save_transfer(self):
        item = self._get_item_by_display(self.tr_item.get())
        if not item:
            CTkMessagebox(title="Error", message="Select an item.", icon="cancel"); return
        fid = tid = 1
        for g in self.godowns:
            if g['name'] == self.tr_from.get(): fid = g['id']
            if g['name'] == self.tr_to.get(): tid = g['id']
        try: qty = float(self.tr_qty.get())
        except:
            CTkMessagebox(title="Error", message="Invalid quantity.", icon="cancel"); return

        ok, msg = create_godown_transfer(item['id'], fid, tid, qty)
        if ok:
            CTkMessagebox(title="Success", message=msg, icon="check")
            self._refresh_stock()
        else:
            CTkMessagebox(title="Error", message=msg, icon="cancel")
