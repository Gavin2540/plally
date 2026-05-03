"""
Login screen for PlywoodPro.
Shows a centered card with username/password fields.
SHA-256 password verification against users table.
3-attempt lockout with 30-second countdown.
First-run detection redirects to Settings company setup.
"""
import hashlib
import sys
import os

# Ensure project root on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from db.connection import get_connection
from db.init_db import init_database
from utils.backup_manager import auto_backup_on_startup
from utils.updater import check_for_updates_async, download_and_apply_update, CURRENT_VERSION

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

ACCENT = "#2E7D32"
RED = "#C62828"


class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PlywoodPro — Login")
        self.geometry("480x420")
        self.resizable(False, False)

        self.attempts = 0
        self.locked = False
        self.countdown = 0
        self.logged_in_user = None

        self._build()
        self.bind("<Return>", lambda e: self._do_login())

    def _build(self):
        # Dark background
        self.configure(fg_color="#1a1a2e")

        # Center card
        card = ctk.CTkFrame(self, corner_radius=16, width=360, height=340,
                            border_width=2, border_color=ACCENT)
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        # Logo / Title
        ctk.CTkLabel(card, text="PlywoodPro",
                     font=ctk.CTkFont(size=28, weight="bold"),
                     text_color=ACCENT).pack(pady=(30, 5))
        ctk.CTkLabel(card, text="Tally-style Business Suite",
                     font=ctk.CTkFont(size=12), text_color="#888").pack(pady=(0, 25))

        # Username
        ctk.CTkLabel(card, text="Username", anchor="w").pack(padx=40, anchor="w")
        self.user_entry = ctk.CTkEntry(card, width=280, height=36, placeholder_text="Enter username")
        self.user_entry.pack(padx=40, pady=(2, 10))
        self.user_entry.insert(0, "admin")

        # Password
        ctk.CTkLabel(card, text="Password", anchor="w").pack(padx=40, anchor="w")
        self.pass_entry = ctk.CTkEntry(card, width=280, height=36, show="*", placeholder_text="Enter password")
        self.pass_entry.pack(padx=40, pady=(2, 15))

        # Login button
        self.login_btn = ctk.CTkButton(card, text="Login", fg_color=ACCENT,
                                        width=280, height=40,
                                        font=ctk.CTkFont(size=14, weight="bold"),
                                        command=self._do_login)
        self.login_btn.pack(padx=40)

        # Status label
        self.status_label = ctk.CTkLabel(card, text="", text_color=RED,
                                          font=ctk.CTkFont(size=11))
        self.status_label.pack(pady=(10, 0))

    def _do_login(self):
        if self.locked:
            return

        username = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()

        if not username or not password:
            self.status_label.configure(text="Please enter username and password.")
            return

        pw_hash = hashlib.sha256(password.encode()).hexdigest()

        conn = get_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND is_active=1",
            (username,)
        ).fetchone()

        if user and user['password'] == pw_hash:
            # Success
            conn.execute("UPDATE users SET last_login=datetime('now','localtime') WHERE id=?",
                         (user['id'],))
            conn.commit()
            conn.close()

            self.logged_in_user = dict(user)
            self.status_label.configure(text="Login successful!", text_color=ACCENT)

            # Check first-run (company table empty)
            self._open_main_app()
        else:
            conn.close()
            self.attempts += 1
            remaining = 3 - self.attempts
            self.pass_entry.delete(0, "end")

            if self.attempts >= 3:
                self._start_lockout()
            else:
                self.status_label.configure(
                    text=f"Invalid credentials. {remaining} attempt(s) remaining.",
                    text_color=RED)

    def _start_lockout(self):
        self.locked = True
        self.countdown = 30
        self.login_btn.configure(state="disabled")
        self._tick_lockout()

    def _tick_lockout(self):
        if self.countdown > 0:
            self.status_label.configure(
                text=f"Too many attempts. Retry in {self.countdown}s...",
                text_color=RED)
            self.countdown -= 1
            self.after(1000, self._tick_lockout)
        else:
            self.locked = False
            self.attempts = 0
            self.login_btn.configure(state="normal")
            self.status_label.configure(text="You may try again.", text_color="#888")

    def _open_main_app(self):
        self.withdraw()  # Hide login window

        # Check if company is set up
        conn = get_connection()
        company = conn.execute("SELECT COUNT(*) FROM company").fetchone()[0]
        conn.close()

        if company == 0:
            # First run — show settings wizard
            self._show_first_run_setup()
        else:
            auto_backup_on_startup()
            self._launch_main()

    def _show_first_run_setup(self):
        """Show Settings UI for first-time company setup."""
        setup_win = ctk.CTkToplevel(self)
        setup_win.title("PlywoodPro — First Time Setup")
        setup_win.geometry("900x650")
        setup_win.protocol("WM_DELETE_WINDOW", lambda: None)  # Prevent close

        ctk.CTkLabel(setup_win, text="Welcome! Please set up your company first.",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=ACCENT).pack(pady=15)

        from ui.settings_ui import SettingsUI
        settings = SettingsUI(setup_win)
        settings.pack(fill="both", expand=True)

        def on_done():
            conn = get_connection()
            has_company = conn.execute("SELECT COUNT(*) FROM company").fetchone()[0]
            conn.close()
            if has_company > 0:
                setup_win.destroy()
                self._launch_main()
            else:
                CTkMessagebox(title="Required", message="Please save company details first.", icon="warning")

        ctk.CTkButton(setup_win, text="Continue to PlywoodPro", fg_color=ACCENT,
                       width=200, command=on_done).pack(pady=10)

    def _launch_main(self):
        """Launch the main PlywoodPro application."""
        from main import PlywoodProApp
        app = PlywoodProApp(login_window=self, logged_in_user=self.logged_in_user)
        
        def _on_update_available(version: str, url: str):
            """
            Called from background thread when newer version found on GitHub.
            Uses app.after() to safely schedule the popup on the main tkinter thread.
            Waits 4 seconds after login so the dashboard has time to fully load first.
            """
            def _show_update_prompt():
                try:
                    from CTkMessagebox import CTkMessagebox
                    msg = CTkMessagebox(
                        title="Update Available",
                        message=(
                            f"A new version of PlywoodPro is available!\n\n"
                            f"Current version:  {CURRENT_VERSION}\n"
                            f"New version:      {version}\n\n"
                            f"Download and install now?\n"
                            f"The app will restart automatically.\n"
                            f"Your business data will not be affected."
                        ),
                        icon="info",
                        option_1="Update Now",
                        option_2="Remind Me Later"
                    )
                    if msg.get() == "Update Now":
                        CTkMessagebox(
                            title="Downloading Update",
                            message="Downloading update. The app will restart when complete.\nPlease wait and do not close the app.",
                            icon="info",
                            option_1="OK"
                        )
                        download_and_apply_update(url)
                except Exception as e:
                    print(f"[Updater] UI error: {e}")

            app.after(4000, _show_update_prompt)

        check_for_updates_async(_on_update_available)
        
        app.mainloop()


def main():
    init_database()
    app = LoginWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
