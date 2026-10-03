# anna-dl v1.0.0 — Initial Stable Release 🚀

We are excited to announce the initial open-source release of **`anna-dl`**, an ultra-resilient, zero-key Shadow Library downloader CLI and autonomous AI Agent engine.

### 🌟 Key Features

* **Zero Paid API Keys Required**: No donation keys, subscription tokens, or fast-download vouchers needed. Operates freely and sustainably over verified public endpoints.
* **Pure Python Core**: High-speed, lightweight operation (`requests` + regex) with negligible startup latency and low memory footprint.
* **DDoS-Guard JS Challenge Solver**: Automated fallback with stealth headless Chromium (`--disable-blink-features=AutomationControlled` + `delete navigator.webdriver`) to resolve JavaScript challenges and `&check=1` redirects when plain HTTP gets blocked with HTTP 403.
* **10-Candidate MD5 Recovery Loop**: Instead of failing when the first mirror has a dead link, `anna-dl` extracts up to 10 unique MD5 candidates and sequentially probes working download mirrors.
* **Direct Token Link Extraction**: Dynamically resolves fast download tokens (`ads.php` → `get.php`) on the fly.
* **Progressive Query Sanitizer**: Strips parentheticals, edition notes, and long subtitles, generating 4-tier fallback queries.
* **DNS Bypass Engine**: Built-in monkeypatch for ISP/DNS-blocked regions (resolving directly to Cloudflare IP `104.21.34.70`).
* **Agent-First Native Architecture**: Shipped with root `AGENTS.md` and `GLOBAL_AGENT_RULE.md` for seamless autonomous execution in Claude Code, Gemini CLI, Cursor, Antigravity, OpenCode, and Codex.

### 📦 Installation

```bash
git clone https://github.com/<owner>/anna-dl.git
cd anna-dl
pip install -r requirements.txt
pip install -e .
```

### 🚀 Quick Start

```bash
anna-dl get --title "Atomic Habits" --author "James Clear"
```
