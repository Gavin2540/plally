"""
Date Picker widget for PlywoodPro.
A reusable date picker that shows CTkEntry with DD/MM/YYYY display.
On click, opens a CTkToplevel calendar popup.
.get_date() returns YYYY-MM-DD for DB storage.
.set_date(yyyy_mm_dd_str) sets the display.
"""

import customtkinter as ctk
from datetime import datetime, date
import calendar


class DatePickerEntry(ctk.CTkFrame):
    """A date entry widget with a popup calendar picker."""

    def __init__(self, parent, width=130, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._date_value = date.today()
        self._popup = None

        self._entry = ctk.CTkEntry(self, width=width - 30, placeholder_text="DD/MM/YYYY")
        self._entry.pack(side="left")
        self._entry.insert(0, self._date_value.strftime("%d/%m/%Y"))
        self._entry.bind("<Button-1>", self._open_popup)
        self._entry.bind("<FocusOut>", self._parse_manual_entry)

        self._btn = ctk.CTkButton(
            self, text="📅", width=28, height=28,
            fg_color="#555", hover_color="#444",
            command=self._open_popup,
        )
        self._btn.pack(side="left", padx=(2, 0))

    def get_date(self) -> str:
        """Return date in YYYY-MM-DD format for DB storage."""
        self._parse_manual_entry()
        return self._date_value.strftime("%Y-%m-%d")

    def set_date(self, yyyy_mm_dd_str: str):
        """Set date from YYYY-MM-DD string."""
        if not yyyy_mm_dd_str:
            self._date_value = date.today()
        else:
            try:
                self._date_value = datetime.strptime(yyyy_mm_dd_str[:10], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                self._date_value = date.today()
        self._update_entry()

    def set_today(self):
        """Set to today's date."""
        self._date_value = date.today()
        self._update_entry()

    def _update_entry(self):
        """Update the entry field with current date value."""
        self._entry.delete(0, "end")
        self._entry.insert(0, self._date_value.strftime("%d/%m/%Y"))

    def _parse_manual_entry(self, event=None):
        """Try to parse what user typed manually."""
        text = self._entry.get().strip()
        if not text:
            return
        # Try DD/MM/YYYY
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                self._date_value = datetime.strptime(text, fmt).date()
                return
            except ValueError:
                continue

    def _open_popup(self, event=None):
        """Open calendar popup near the entry."""
        if self._popup and self._popup.winfo_exists():
            self._popup.focus_force()
            return

        self._parse_manual_entry()

        self._popup = ctk.CTkToplevel(self)
        self._popup.title("Select Date")
        self._popup.geometry("280x290")
        self._popup.resizable(False, False)
        self._popup.attributes("-topmost", True)
        self._popup.grab_set()

        # Position near the entry
        try:
            x = self.winfo_rootx()
            y = self.winfo_rooty() + self.winfo_height() + 2
            self._popup.geometry(f"+{x}+{y}")
        except Exception:
            pass

        self._cal_year = self._date_value.year
        self._cal_month = self._date_value.month

        self._build_calendar()

    def _build_calendar(self):
        """Build the calendar grid inside the popup."""
        if not self._popup or not self._popup.winfo_exists():
            return

        # Clear existing widgets
        for w in self._popup.winfo_children():
            w.destroy()

        # Navigation bar
        nav = ctk.CTkFrame(self._popup, fg_color="transparent")
        nav.pack(fill="x", padx=5, pady=5)

        ctk.CTkButton(nav, text="◀", width=30, fg_color="#555",
                       command=self._prev_month).pack(side="left", padx=2)

        month_name = calendar.month_name[self._cal_month]
        ctk.CTkLabel(nav, text=f"{month_name} {self._cal_year}",
                      font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", expand=True)

        ctk.CTkButton(nav, text="▶", width=30, fg_color="#555",
                       command=self._next_month).pack(side="right", padx=2)

        # Day headers
        day_frame = ctk.CTkFrame(self._popup, fg_color="transparent")
        day_frame.pack(fill="x", padx=5)
        for i, day in enumerate(["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]):
            ctk.CTkLabel(day_frame, text=day, width=35,
                          font=ctk.CTkFont(size=10, weight="bold"),
                          text_color="#888").grid(row=0, column=i, padx=1)

        # Calendar grid
        cal_frame = ctk.CTkFrame(self._popup, fg_color="transparent")
        cal_frame.pack(fill="both", expand=True, padx=5, pady=2)

        cal = calendar.monthcalendar(self._cal_year, self._cal_month)
        today = date.today()

        for row_idx, week in enumerate(cal):
            for col_idx, day in enumerate(week):
                if day == 0:
                    ctk.CTkLabel(cal_frame, text="", width=35).grid(
                        row=row_idx, column=col_idx, padx=1, pady=1)
                else:
                    d = date(self._cal_year, self._cal_month, day)
                    is_today = (d == today)
                    is_selected = (d == self._date_value)

                    if is_selected:
                        fg = "#2E7D32"
                        tc = "#FFFFFF"
                    elif is_today:
                        fg = "#1565C0"
                        tc = "#FFFFFF"
                    else:
                        fg = "transparent"
                        tc = None

                    btn = ctk.CTkButton(
                        cal_frame, text=str(day), width=35, height=28,
                        fg_color=fg, hover_color="#333",
                        text_color=tc,
                        font=ctk.CTkFont(size=11),
                        command=lambda d=day: self._select_date(d),
                    )
                    btn.grid(row=row_idx, column=col_idx, padx=1, pady=1)

        # Today button
        ctk.CTkButton(self._popup, text="Today", width=80, height=25,
                       fg_color="#1565C0", hover_color="#0D47A1",
                       command=self._select_today).pack(pady=5)

    def _prev_month(self):
        if self._cal_month == 1:
            self._cal_month = 12
            self._cal_year -= 1
        else:
            self._cal_month -= 1
        self._build_calendar()

    def _next_month(self):
        if self._cal_month == 12:
            self._cal_month = 1
            self._cal_year += 1
        else:
            self._cal_month += 1
        self._build_calendar()

    def _select_date(self, day: int):
        self._date_value = date(self._cal_year, self._cal_month, day)
        self._update_entry()
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
        self._popup = None

    def _select_today(self):
        self._date_value = date.today()
        self._update_entry()
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
        self._popup = None
