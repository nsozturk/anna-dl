"""Academic paper resolver and multi-source retriever.
Coordinates arXiv, SSRN, Open Access repositories (Unpaywall, OpenAlex, HAL, PoliTO),
Anna's Archive / LibGen fallbacks, and Chrome native anti-bot driving.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from paperdl.arxiv import download_arxiv_pdf
from paperdl.chrome_driver import download_via_chrome, is_valid_pdf
from paperdl.fallback import download_via_annas_fallback

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
ARXIV_RE = re.compile(r"(?:arxiv\.org/(?:pdf|abs|html)/|^|\barxiv:\s*)(\d{4}\.\d{4,5})(?:v\d+)?(?:$|\.pdf|\b)", re.I)
SSRN_RE = re.compile(r"(?:ssrn\.com/(?:abstract(?:_id)?=|sol3/papers\.cfm\?abstract_id=)|^|\bssrn:\s*)(\d{6,8})(?:$|\.pdf|\b)", re.I)
DOI_RE = re.compile(r"(?:doi\.org/|doi:\s*|^)(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)", re.I)


def extract_arxiv_id(text: str) -> str | None:
    m = ARXIV_RE.search(text)
    return m.group(1) if m else None


def extract_ssrn_id(text: str) -> str | None:
    m = SSRN_RE.search(text)
    return m.group(1) if m else None


def extract_doi(text: str) -> str | None:
    m = DOI_RE.search(text)
    return m.group(0).rstrip(".") if m else None


def resolve_unpaywall(doi: str) -> str | None:
    """Queries Unpaywall API for an open-access PDF URL."""
    try:
        clean_doi = urllib.parse.quote(doi)
        url = f"https://api.unpaywall.org/v2/{clean_doi}?email=unpaywall@impactstory.org"
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            best = data.get("best_oa_location") or {}
            if best.get("url_for_pdf"):
                return best["url_for_pdf"]
            for loc in data.get("oa_locations", []):
                if loc.get("url_for_pdf"):
                    return loc["url_for_pdf"]
                if "ssrn" in (loc.get("url") or ""):
                    return loc["url"]
    except Exception:
        pass
    return None


def resolve_openalex(title: str) -> list[str]:
    """Queries OpenAlex for candidate PDF and landing page URLs."""
    candidates = []
    try:
        q = urllib.parse.quote(title)
        url = f"https://api.openalex.org/works?filter=title.search:{q}"
        req = urllib.request.Request(url, headers={"User-Agent": "mailto:research@academic.org"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for w in data.get("results", [])[:3]:
                oa = w.get("open_access", {})
                if oa.get("oa_url"):
                    candidates.append(oa["oa_url"])
                for loc in w.get("locations", []):
                    u = loc.get("pdf_url") or loc.get("landing_page_url")
                    if u and u not in candidates:
                        candidates.append(u)
    except Exception:
        pass
    return candidates


def fetch_stream(url: str, dest: Path, min_bytes: int = 10 * 1024) -> tuple[bool, str, int]:
    """Direct HTTP stream download with authentic headers."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/pdf,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            if len(data) >= min_bytes and data[:5] == b"%PDF-":
                tmp.write_bytes(data)
                tmp.replace(dest)
                return True, "Direct stream download successful", len(data)
            else:
                tmp.unlink(missing_ok=True)
                return False, f"Response is not a valid PDF (length: {len(data)})", len(data)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        tmp.unlink(missing_ok=True)
        return False, f"Direct stream failed: {exc}", 0


def retrieve_paper(
    identifier: str,
    dest: Path,
    use_chrome: bool = False,
    title_hint: str | None = None,
) -> tuple[bool, str, int]:
    """
    Unified multi-tiered retrieval pipeline:
    1. ArXiv (direct open access stream)
    2. SSRN (direct Delivery URL or Chrome native automation)
    3. Unpaywall / OpenAlex Open Access resolution
    4. Anna's Archive / LibGen mirror multi-candidate loop
    5. Native Google Chrome AppleScript automation (Cloudflare/bot challenge bypass)
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if is_valid_pdf(dest):
        sz = dest.stat().st_size
        return True, f"File already exists and is valid ({sz} bytes)", sz

    # Tier 1: ArXiv ID
    arxiv_id = extract_arxiv_id(identifier)
    if arxiv_id:
        print(f"[*] Detected arXiv ID: {arxiv_id}. Probing arXiv Open Access...")
        ok, msg, sz = download_arxiv_pdf(arxiv_id, dest)
        if ok and is_valid_pdf(dest):
            return True, f"arXiv: {msg}", sz

    # Tier 2: SSRN Abstract ID
    ssrn_id = extract_ssrn_id(identifier)
    if ssrn_id:
        print(f"[*] Detected SSRN ID: {ssrn_id}. Attempting direct delivery stream...")
        direct_ssrn = f"https://papers.ssrn.com/sol3/Delivery.cfm/{ssrn_id}.pdf?abstractid={ssrn_id}&mirid=1"
        ok, msg, sz = fetch_stream(direct_ssrn, dest)
        if ok and is_valid_pdf(dest):
            return True, "SSRN direct delivery stream", sz

        # SSRN blocked direct stream (Cloudflare 403) -> Drive native Chrome
        print("[*] SSRN blocked direct HTTP stream. Activating Chrome native driver...")
        abs_url = f"https://papers.ssrn.com/sol3/papers.cfm?abstract_id={ssrn_id}"
        ok_chrome, msg_chrome, sz_chrome = download_via_chrome(abs_url, dest)
        if ok_chrome and is_valid_pdf(dest):
            return True, f"SSRN via Chrome: {msg_chrome}", sz_chrome

    # Tier 3: Direct URL
    if identifier.startswith("http://") or identifier.startswith("https://"):
        print(f"[*] Fetching direct URL: {identifier}...")
        ok, msg, sz = fetch_stream(identifier, dest)
        if ok and is_valid_pdf(dest):
            return True, "Direct URL stream", sz

        if use_chrome or "403" in msg or "cloudflare" in msg.lower():
            print("[*] Direct fetch failed or blocked. Trying via Chrome driver...")
            ok_chrome, msg_chrome, sz_chrome = download_via_chrome(identifier, dest)
            if ok_chrome and is_valid_pdf(dest):
                return True, f"URL via Chrome: {msg_chrome}", sz_chrome

    # Tier 4: DOI lookup via Unpaywall
    doi = extract_doi(identifier)
    if doi:
        print(f"[*] Querying Unpaywall for DOI {doi}...")
        oa_url = resolve_unpaywall(doi)
        if oa_url:
            print(f"[*] Unpaywall found OA location: {oa_url}")
            ok, msg, sz = fetch_stream(oa_url, dest)
            if ok and is_valid_pdf(dest):
                return True, f"Unpaywall OA: {msg}", sz
            # If OA URL blocked by Cloudflare, try via Chrome
            ok_c, msg_c, sz_c = download_via_chrome(oa_url, dest)
            if ok_c and is_valid_pdf(dest):
                return True, f"Unpaywall OA via Chrome: {msg_c}", sz_c

    # Tier 5: Anna's Archive & LibGen fallback loop
    query_title = title_hint or identifier
    print(f"[*] Querying Anna's Archive & LibGen mirrors for '{query_title}'...")
    ok_anna, msg_anna, sz_anna = download_via_annas_fallback(query_title, dest)
    if ok_anna and is_valid_pdf(dest):
        return True, f"Anna's Archive / LibGen: {msg_anna}", sz_anna

    # Tier 6: OpenAlex discovery
    print(f"[*] Checking OpenAlex for alternative repository links...")
    oa_links = resolve_openalex(query_title)
    for link in oa_links:
        print(f"[*] Trying OpenAlex link: {link}...")
        ok, msg, sz = fetch_stream(link, dest)
        if ok and is_valid_pdf(dest):
            return True, f"OpenAlex OA link: {msg}", sz
        ok_c, msg_c, sz_c = download_via_chrome(link, dest)
        if ok_c and is_valid_pdf(dest):
            return True, f"OpenAlex link via Chrome: {msg_c}", sz_c

    return False, f"All retrieval tiers exhausted for '{identifier}'", 0
