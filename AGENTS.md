# AGENTS.md — Agent Specification for anna-dl

This document defines the operational contracts, execution commands, and failure recovery protocols for autonomous AI coding agents (Claude Code, Gemini CLI, Cursor, Antigravity, OpenCode, Codex) working within or using this repository.

---

## 1. Core Agent Capabilities

`anna-dl` is an autonomous CLI tool for resolving and retrieving literature from Anna's Archive and LibGen mirrors without requiring paid API keys or external subscription services.

### Execution Contracts

| Task | Command | Failure Fallback |
|---|---|---|
| **Download Book by Title & Author** | `anna-dl get --title "<Title>" --author "<Author>"` | Add `--bypass-dns` if connection hangs or times out. |
| **Download Book with Specific Query** | `anna-dl get --title "<Title>" --query "<Keyword Query>"` | Shorten query to `Author Last Name + 2 Keywords`. |
| **Download with DNS Bypass** | `anna-dl get --title "<Title>" --author "<Author>" --bypass-dns` | Direct edge IP resolution for ISP-blocked hosts. |
| **Batch Download from Queue** | `anna-dl download --parallel --workers 4` | Run `anna-dl retry --bypass-dns` for remaining items. |
| **Check Archive Status** | `anna-dl status` | Inspect disk vs log state. |

---

## 2. Shadow Library Operational Principles & Hard-Won Truths

### A. Domain Changes & 2026 Takedown History
- **Takedown Notice:** `annas-archive.org` and `annas-archive.se` domains were suspended/seized by global court orders in mid-2026.
- **Active & Verified Working Mirrors (Prioritized in Config):**
  - `https://annas-archive.gl` (Primary verified mirror)
  - `https://annas-archive.pk` (Secondary active mirror)
  - `https://annas-archive.gd` (Tertiary active mirror)
  - `https://annas-archive.vg`
- **LibGen Mirrors:** `libgen.la`, `libgen.gl`, `libgen.vg`, `libgen.is`, `libgen.rs`, and search index `libgen.li`.

### B. DDoS-Guard JS Challenge & HTTP 403 Bypass
- **The Challenge:** Plain HTTP clients (`urllib`, `requests`, `httpx`, `curl_cffi`, terminal `curl`) direct-querying Anna's Archive endpoints frequently trigger DDoS-Guard's JavaScript test and receive `HTTP 403 Forbidden`.
- **The Resolution:**
  1. **Dual Path Resolution:** Primary queries utilize `libgen.li/index.php` which responds directly over plain HTTP.
  2. **Automated Stealth Playwright Solver:** If direct Anna queries hit HTTP 403 / DDoS-Guard, `anna-dl` automatically engages headless Chromium:
     - Disables automation telemetry: `--disable-blink-features=AutomationControlled` and removes `navigator.webdriver`.
     - Awaits DDoS-Guard's `&check=1` redirect (4–6s) until page title no longer contains `DDOS` or `LOADING`.
     - Extracts candidate MD5 hashes from rendered HTML via BeautifulSoup.

### C. Multi-Candidate MD5 Recovery Loop (10 Candidates)
- Top search results may link to rate-limited or temporarily offline file hosters.
- The engine collects up to **10 unique candidate MD5 hashes** and probes each sequentially until an active streaming direct download link (`ads.php` → `get.php`) is verified.

### D. File Integrity Safeguard
- Files under 10 KB are automatically rejected and unlinked to avoid storing HTML error banners or Cloudflare challenge pages.

---

## 3. Non-Interactive CLI Interface

- The tool is designed to run headlessly in subagent and CI/CD pipelines.
- Standard return code `0` signals successful file retrieval.
- Return code `1` signals failure across all candidate mirrors, prompting query refinement.
