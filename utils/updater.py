"""
Auto-updater for PlywoodPro.
Checks GitHub Releases API for a newer version on every app startup.
Runs in a background thread — completely silent if offline or up to date.
If a newer version is found, calls a callback on the main thread.
"""
import urllib.request
import json
import sys
import os
import subprocess
import threading

GITHUB_REPO = "Gavin2540/plally"
CURRENT_VERSION = "1.1.3"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
DOWNLOAD_FILENAME = "PlywoodPro_update.zip"


def get_latest_release() -> dict | None:
    """
    Fetches the latest release info from GitHub API.
    Returns the parsed JSON dict, or None if offline or any error occurs.
    Timeout is 5 seconds so it never blocks the app.
    """
    try:
        req = urllib.request.Request(
            API_URL,
            headers={"User-Agent": "PlywoodPro-Updater/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def is_newer(latest_tag: str, current: str) -> bool:
    """
    Compares two version strings like '1.3.0' and '1.2.0'.
    Returns True if latest_tag is strictly greater than current.
    Strips leading 'v' before comparing so 'v1.3.0' and '1.3.0' both work.
    """
    try:
        def parse(v):
            return [int(x) for x in v.lstrip("v").split(".")]
        return parse(latest_tag) > parse(current)
    except Exception:
        return False


def get_download_url(release: dict) -> str | None:
    """
    Finds the first .zip asset download URL in the release assets list.
    Returns None if no zip asset is attached to the release.
    """
    for asset in release.get("assets", []):
        if asset.get("name", "").endswith(".zip"):
            return asset["browser_download_url"]
    return None


def download_and_apply_update(url: str, progress_callback=None):
    """
    Downloads the zip from the given URL into the app directory,
    writes a self-deleting batch script that extracts the zip and
    restarts the app, then exits the current process so the batch
    script can overwrite running files.
    progress_callback is optional — called with integer 0-100 during download.
    """
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
    else:
        exe_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    zip_path = os.path.join(exe_dir, DOWNLOAD_FILENAME)
    exe_path = os.path.join(exe_dir, "PlywoodPro.exe")

    def _report(count, block_size, total):
        if progress_callback and total > 0:
            pct = min(int(count * block_size * 100 / total), 100)
            progress_callback(pct)

    urllib.request.urlretrieve(url, zip_path, _report)

    bat_path = os.path.join(exe_dir, "_apply_update.bat")
    bat_content = f"""@echo off
timeout /t 2 /nobreak >nul
echo Applying PlywoodPro update...
powershell -command "Expand-Archive -Path '{zip_path}' -DestinationPath '{exe_dir}' -Force"
if exist "{zip_path}" del "{zip_path}"
echo Update complete. Restarting PlywoodPro...
start "" "{exe_path}"
del "%~f0"
"""
    with open(bat_path, "w") as f:
        f.write(bat_content)

    subprocess.Popen(bat_path, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
    sys.exit(0)


def check_for_updates_async(on_update_available):
    """
    Starts a background daemon thread that checks GitHub for updates.
    on_update_available(version_string, download_url) is called if update found.
    Called from background thread — caller must use .after() for any UI actions.
    Returns immediately and never blocks.
    """
    def _check():
        release = get_latest_release()
        if not release:
            return
        tag = release.get("tag_name", "")
        if is_newer(tag, CURRENT_VERSION):
            url = get_download_url(release)
            if url:
                on_update_available(tag, url)

    threading.Thread(target=_check, daemon=True).start()
