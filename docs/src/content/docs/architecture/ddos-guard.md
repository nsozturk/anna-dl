---
title: DDoS-Guard JS Solver
description: Automated headless browser challenge resolution
---

### The HTTP 403 Challenge

In mid-2026, Anna's Archive endpoints enabled aggressive DDoS-Guard JavaScript tests. Any direct HTTP request from standard scraping libraries (`urllib`, `requests`, `httpx`, `curl_cffi`, terminal `curl`) fails with `HTTP 403 Forbidden`.

### The Solution

`anna-dl` implements a dual-path architecture:

1. **Fast Search:** Queries `libgen.li` index directly via plain HTTP.
2. **Stealth Headless Chromium:** If direct Anna queries hit HTTP 403 / DDoS-Guard, `anna-dl` automatically launches headless Chromium:
   - Sets `--disable-blink-features=AutomationControlled`
   - Removes `navigator.webdriver`
   - Waits for the `&check=1` redirect to complete until the page title stops containing "DDOS"
   - Extracts candidate MD5 hashes from rendered HTML via BeautifulSoup.
