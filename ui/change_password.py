"""
Change Password dialog for PlywoodPro.
Validates current password, checks new != current, confirms match.
"""
import hashlib
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from db.connection import get_connection

ACCENT = "#2E7D32"


class ChangePasswordDialog(ctk.CTkToplevel):
    def __init__(self, parent, user_id: int):
        super().__init__(parent)
        self.title("Change Password")
        self.geometry("400x320")
        self.resizable(False, False)
        self.user_id = user_id
        self.grab_set()

        card = ctk.CTkFrame(self, corner_radius=12)
        card.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(card, text="Change Password",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=ACCENT).pack(pady=(15, 20))

        ctk.CTkLabel(card, text="Current Password", anchor="w").pack(padx=30, anchor="w")
        self.current_pw = ctk.CTkEntry(card, width=260, show="*")
        self.current_pw.pack(padx=30, pady=(2, 10))

        ctk.CTkLabel(card, text="New Password", anchor="w").pack(padx=30, anchor="w")
        self.new_pw = ctk.CTkEntry(card, width=260, show="*")
        self.new_pw.pack(padx=30, pady=(2, 10))

        ctk.CTkLabel(card, text="Confirm New Password", anchor="w").pack(padx=30, anchor="w")
        self.confirm_pw = ctk.CTkEntry(card, width=260, show="*")
        self.confirm_pw.pack(padx=30, pady=(2, 15))

        ctk.CTkButton(card, text="Save", fg_color=ACCENT, width=260,
                       command=self._save).pack(padx=30)

    def _save(self):
        cur = self.current_pw.get().strip()
        new = self.new_pw.get().strip()
        confirm = self.confirm_pw.get().strip()

        if not cur or not new or not confirm:
            CTkMessagebox(title="Error", message="All fields are required.", icon="cancel")
            return

        cur_hash = hashlib.sha256(cur.encode()).hexdigest()
        new_hash = hashlib.sha256(new.encode()).hexdigest()

        conn = get_connection()
        user = conn.execute("SELECT password FROM users WHERE id=?", (self.user_id,)).fetchone()

        if not user or user['password'] != cur_hash:
            conn.close()
            CTkMessagebox(title="Error", message="Current password is incorrect.", icon="cancel")
            return

        if cur == new:
            conn.close()
            CTkMessagebox(title="Error", message="New password must be different.", icon="cancel")
            return

        if new != confirm:
            conn.close()
            CTkMessagebox(title="Error", message="New passwords don't match.", icon="cancel")
            return

        if len(new) < 4:
            conn.close()
            CTkMessagebox(title="Error", message="Password must be at least 4 characters.", icon="cancel")
            return

        conn.execute("UPDATE users SET password=? WHERE id=?", (new_hash, self.user_id))
        conn.commit()
        conn.close()

        CTkMessagebox(title="Success", message="Password changed successfully.", icon="check")
        self.destroy()
