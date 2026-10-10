import re
import time
import urllib.parse
import requests
from typing import List, Tuple, Optional
from bs4 import BeautifulSoup
from anna_dl.config import LIBGEN_SEARCH, LIBGEN_SEARCH_MIRRORS

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

def search_md5_candidates(query: str, anna_mirror: str, max_candidates: int = 15, prefer_format: str = 'pdf') -> List[str]:
    """
    Searches for MD5 hashes across LibGen search mirrors and Anna's Archive with smart ranking.
    Employs fast requests with automatic stealth browser fallback for DDoS-Guard challenges.
    Default format preference: PDF (highest quality/complete scans), with optional EPUB prioritization.
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    candidates = []
    seen = set()

    search_hosts = list(LIBGEN_SEARCH_MIRRORS)
    if LIBGEN_SEARCH and LIBGEN_SEARCH.replace('http://', '').replace('https://', '') not in search_hosts:
        search_hosts.insert(0, LIBGEN_SEARCH.replace('http://', '').replace('https://', ''))

    for host in search_hosts:
        try:
            url = f"http://{host}/index.php"
            resp = requests.get(url, params={'req': query}, headers=headers, timeout=8)
            if resp.status_code == 200 and resp.text:
                soup = BeautifulSoup(resp.text, 'html.parser')
                table = soup.find('table', {'id': 'tablelibgen'}) or soup.find('table')
                if table:
                    rows = table.find_all('tr')[1:]
                    for r in rows:
                        cols = r.find_all(['td', 'th'])
                        if len(cols) < 8:
                            continue
                        link = r.find('a', href=re.compile(r'md5=', re.I))
                        if not link:
                            continue
                        m = re.search(r'md5=([a-fA-F0-9]{32})', link['href'], re.I)
                        if not m:
                            continue
                        md5 = m.group(1).lower()
                        if md5 in seen:
                            continue
                        seen.add(md5)

                        pages = cols[5].get_text(strip=True)
                        size_str = cols[6].get_text(strip=True).lower()
                        ext = cols[7].get_text(strip=True).lower()

                        size_kb = 0.0
                        if 'mb' in size_str:
                            size_kb = float(re.sub(r'[^0-9.]', '', size_str) or 0) * 1024
                        elif 'kb' in size_str:
                            size_kb = float(re.sub(r'[^0-9.]', '', size_str) or 0)

                        is_flyer = (ext == 'pdf' and size_kb < 150 and pages in ('1', '2', '3', '4'))
                        if is_flyer:
                            score = 200
                        elif prefer_format == 'epub':
                            # EPUB-first ranking
                            if ext in ('epub', 'kepub'):
                                score = -100
                            elif ext in ('mobi', 'azw3'):
                                score = -50
                            elif ext == 'pdf':
                                score = 0
                            else:
                                score = 50
                        else:
                            # PDF-first ranking (default)
                            if ext == 'pdf':
                                score = -100
                            elif ext in ('epub', 'kepub'):
                                score = -50
                            elif ext in ('mobi', 'azw3'):
                                score = -30
                            else:
                                score = 50
                        candidates.append((score, -size_kb, md5))

                if candidates:
                    break
        except requests.RequestException:
            continue

    if not candidates:
        # Fallback raw regex across hosts
        for host in search_hosts:
            try:
                resp = requests.get(f"http://{host}/index.php", params={'req': query}, headers=headers, timeout=6)
                if resp.status_code == 200:
                    raw_md5s = re.findall(r'md5=([a-fA-F0-9]{32})', resp.text, re.I)
                    for m in raw_md5s:
                        m_low = m.lower()
                        if m_low not in seen:
                            seen.add(m_low)
                            candidates.append((0, 0, m_low))
                if candidates:
                    break
            except requests.RequestException:
                pass

    hit_ddos_guard = False
    if anna_mirror and len(candidates) < max_candidates:
        try:
            resp = requests.get(f"https://{anna_mirror}/search", params={'q': query}, headers=headers, timeout=6)
            if resp.status_code == 200:
                raw_md5s = re.findall(r'md5/([a-fA-F0-9]{32})', resp.text, re.I)
                for m in raw_md5s:
                    m_low = m.lower()
                    if m_low not in seen:
                        seen.add(m_low)
                        candidates.append((1, 0, m_low))
            elif resp.status_code == 403 or "ddos-guard" in resp.text.lower():
                hit_ddos_guard = True
        except requests.RequestException:
            hit_ddos_guard = True

    # Stealth Playwright fallback if direct HTTP is blocked by DDoS-Guard
    if hit_ddos_guard and len(candidates) < max_candidates and anna_mirror:
        print(f"      [*] Anna mirror returned DDoS challenge. Activating stealth browser fallback...")
        pw_md5s = _search_anna_playwright_stealth(query, anna_mirror)
        for m in pw_md5s:
            m_low = m.lower()
            if m_low not in seen:
                seen.add(m_low)
                candidates.append((2, 0, m_low))

    candidates.sort(key=lambda x: (x[0], x[1]))
    return [c[2] for c in candidates][:max_candidates]

def get_direct_download_url(md5: str, libgen_mirrors: List[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Fetches the download URL and format extension for an MD5 hash from libgen mirrors.
    Validates candidates via pre-flight HEAD checks before streaming.
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    for mirror in libgen_mirrors:
        try:
            url = f"http://{mirror}/ads.php?md5={md5}"
            resp = requests.get(url, headers=headers, timeout=8)
            if resp.status_code == 200:
                ext = "pdf"
                # Check for extension indicators in HTML
                m_ext = re.search(r'Extension:\s*([a-zA-Z0-9]+)', resp.text, re.I)
                if m_ext:
                    ext = m_ext.group(1).lower()
                else:
                    m_file = re.search(r'href="[^"]+\.([a-zA-Z0-9]{3,4})"', resp.text, re.I)
                    if m_file and m_file.group(1).lower() in ('epub', 'pdf', 'mobi', 'azw3', 'djvu'):
                        ext = m_file.group(1).lower()

                match = re.search(r'href="(get\.php\?md5=[^"]+)"', resp.text)
                if match:
                    dl_candidate = f"http://{mirror}/{match.group(1)}"
                    try:
                        chk = requests.head(dl_candidate, headers={'User-Agent': headers['User-Agent'], 'Referer': url}, allow_redirects=True, timeout=5)
                        if chk.status_code == 200 and int(chk.headers.get('Content-Length', 0)) > 10000:
                            return dl_candidate, ext, url
                    except Exception:
                        pass

                match = re.search(r'href="([^"]+\.(pdf|epub|mobi))"', resp.text, re.IGNORECASE)
                if match:
                    link = match.group(1)
                    if not link.startswith('http'):
                        link = f"http://{mirror}/{link}"
                    try:
                        chk = requests.head(link, headers={'User-Agent': headers['User-Agent'], 'Referer': url}, allow_redirects=True, timeout=5)
                        if chk.status_code == 200 and int(chk.headers.get('Content-Length', 0)) > 10000:
                            return link, match.group(2).lower(), url
                    except Exception:
                        pass
        except requests.RequestException:
            continue
    return None, None, None
