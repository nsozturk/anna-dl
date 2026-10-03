import re
import time
import urllib.parse
import requests
from typing import List, Tuple, Optional
from bs4 import BeautifulSoup
from anna_dl.config import LIBGEN_SEARCH

def get_working_mirror(mirrors: List[str], headers: dict) -> str:
    """
    Probes mirrors sequentially and returns the first responsive mirror.
    """
    for mirror in mirrors:
        url = f"https://{mirror}/search?q=test"
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                return mirror
        except requests.RequestException:
            continue
    return mirrors[0] if mirrors else ""

def _search_anna_playwright_stealth(query: str, anna_mirror: str) -> List[str]:
    """
    Stealth Playwright solver to resolve Anna's Archive DDoS-Guard JS challenge (&check=1).
    Used as an automated fallback when plain HTTP requests encounter HTTP 403 Forbidden.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return []

    md5_list = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()
            page.add_init_script("delete Object.getPrototypeOf(navigator).webdriver")

            search_url = f"https://{anna_mirror}/search?q={urllib.parse.quote(query)}"
            page.goto(search_url, timeout=30000)

            # Wait for DDoS-Guard challenge resolution (&check=1 redirect)
            for _ in range(12):
                time.sleep(1)
                title = page.title()
                if "DDOS" not in title.upper() and "LOADING" not in title.upper():
                    break
            time.sleep(2)

            html = page.content()
            browser.close()

            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/md5/" in href:
                    match = re.search(r'md5/([a-fA-F0-9]{32})', href, re.IGNORECASE)
                    if match:
                        md5_list.append(match.group(1).lower())
    except Exception as e:
        print(f"      [!] Stealth browser solver notice: {e}")

    return md5_list

def search_md5_candidates(query: str, anna_mirror: str, max_candidates: int = 10) -> List[str]:
    """
    Discovers candidate MD5 hashes across LibGen and Anna's Archive endpoints.
    Employs fast requests with automatic stealth browser fallback for DDoS-Guard challenges.
    """
    md5_list = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    # 1. Primary fast index check: Libgen.li
    try:
        resp = requests.get(
            f"{LIBGEN_SEARCH}/index.php",
            params={'req': query},
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200:
            md5_list.extend(re.findall(r'md5=([a-fA-F0-9]{32})', resp.text, re.IGNORECASE))
    except requests.RequestException:
        pass

    # 2. Secondary comprehensive mirror check: Anna's Archive
    hit_ddos_guard = False
    if len(md5_list) < max_candidates and anna_mirror:
        try:
            resp = requests.get(
                f"https://{anna_mirror}/search",
                params={'q': query},
                headers=headers,
                timeout=10
            )
            if resp.status_code == 200:
                md5_list.extend(re.findall(r'md5/([a-fA-F0-9]{32})', resp.text, re.IGNORECASE))
            elif resp.status_code == 403 or "ddos-guard" in resp.text.lower():
                hit_ddos_guard = True
        except requests.RequestException:
            hit_ddos_guard = True

    # 3. Stealth Playwright fallback if direct HTTP is blocked by DDoS-Guard
    if hit_ddos_guard and len(md5_list) < max_candidates and anna_mirror:
        print(f"      [*] Anna mirror returned DDoS challenge. Activating stealth browser fallback...")
        pw_md5s = _search_anna_playwright_stealth(query, anna_mirror)
        md5_list.extend(pw_md5s)

    # Deduplicate while preserving rank order
    unique = []
    for md5 in md5_list:
        md5_lower = md5.lower()
        if md5_lower not in unique:
            unique.append(md5_lower)
            if len(unique) >= max_candidates:
                break
    return unique

def get_direct_download_url(md5: str, libgen_mirrors: List[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Resolves an MD5 hash into a direct streaming link via ads.php -> get.php token extraction.
    Returns: (download_url, file_extension, referer_url)
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    for mirror in libgen_mirrors:
        try:
            url = f"http://{mirror}/ads.php?md5={md5}"
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                # Direct get.php token link extraction
                match = re.search(r'href="(get\.php\?md5=[^"]+)"', resp.text)
                if match:
                    return f"http://{mirror}/{match.group(1)}", "pdf", url

                # Fallback to explicit direct file links (.pdf / .epub)
                match = re.search(r'href="([^"]+\.(pdf|epub))"', resp.text, re.IGNORECASE)
                if match:
                    link = match.group(1)
                    if not link.startswith('http'):
                        link = f"http://{mirror}/{link}"
                    return link, match.group(2).lower(), url
        except requests.RequestException:
            continue
    return None, None, None
