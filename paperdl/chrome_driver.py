"""Google Chrome native automation driver via AppleScript (macOS).
Bypasses Cloudflare Turnstile, DDoS-Guard, Akamai, and Elsevier/SSRN/MDPI bot challenges
by leveraging the user's running, authenticated browser session and authentic Mac TLS stack.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

DOWNLOADS = Path.home() / "Downloads"


def is_chrome_running() -> bool:
    try:
        res = subprocess.run(["pgrep", "-i", "Google Chrome"], capture_output=True, text=True)
        return res.returncode == 0 and bool(res.stdout.strip())
    except Exception:
        return False


def run_applescript(script: str) -> str:
    res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"AppleScript error: {res.stderr.strip()}")
    return res.stdout.strip()


def is_valid_pdf(path: Path, min_bytes: int = 10 * 1024) -> bool:
    try:
        if not path.is_file() or path.stat().st_size < min_bytes:
            return False
        return path.read_bytes()[:5] == b"%PDF-"
    except OSError:
        return False


def download_via_chrome(
    url: str,
    output_path: Path,
    timeout: int = 25,
    click_selector: str | None = None,
) -> tuple[bool, str, int]:
    """
    Opens url in a new tab of the running Google Chrome, waits for the download to finish
    in ~/Downloads, validates the PDF, and moves it to output_path.
    """
    if not is_chrome_running():
        return False, "Google Chrome is not running. Please open Chrome first.", 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    before_pdfs = {f: f.stat().st_mtime for f in DOWNLOADS.glob("*.pdf")}

    # Default selector handles SSRN Delivery links, generic PDF links, and download buttons
    selector = click_selector or (
        'a[href*=\\"Delivery.cfm\\"], a[href*=\\"/pdf\\"], a.download-button, a.btn-download, .button-link'
    )

    script = f'''
tell application "Google Chrome"
    set newTab to make new tab at end of tabs of window 1 with properties {{URL:"{url}"}}
    delay 4
    try
        tell newTab to execute javascript "var a = document.querySelector('{selector}'); if(a) a.click();"
    end try
    delay 4
    close newTab
end tell
'''
    try:
        run_applescript(script)
    except Exception as exc:
        return False, f"Failed executing AppleScript in Chrome: {exc}", 0

    # Wait for file to land in ~/Downloads
    downloaded_file: Path | None = None
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(1)
        # If there are active Chrome downloads, keep waiting
        if list(DOWNLOADS.glob("*.crdownload")):
            continue

        after_pdfs = {f: f.stat().st_mtime for f in DOWNLOADS.glob("*.pdf")}
        new_or_modified = [f for f, mtime in after_pdfs.items() if f not in before_pdfs or mtime > before_pdfs[f]]
        if new_or_modified:
            # Pick the most recently modified PDF
            new_or_modified.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            candidate = new_or_modified[0]
            if is_valid_pdf(candidate):
                downloaded_file = candidate
                break

    if not downloaded_file:
        return False, f"Download timed out after {timeout}s (no new PDF detected in ~/Downloads)", 0

    try:
        shutil.copy2(downloaded_file, output_path)
        if is_valid_pdf(output_path):
            size = output_path.stat().st_size
            return True, f"Successfully downloaded via Chrome ({size} bytes)", size
        else:
            return False, "Downloaded file failed PDF validation", 0
    except Exception as exc:
        return False, f"Failed moving downloaded file: {exc}", 0
