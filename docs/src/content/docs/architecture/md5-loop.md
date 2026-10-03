---
title: 10-Candidate MD5 Recovery Loop
description: Resilient multi-candidate failover strategy
---

Traditional downloaders fail immediately if the first search result's download mirror is offline or rate-limited.

`anna-dl` addresses this by:
1. Extracting up to **10 unique candidate MD5 hashes** matching the book query.
2. Sequentially probing LibGen download mirrors (`ads.php` → `get.php`) for each candidate.
3. Validating the stream size (rejecting error files under 10 KB).
4. Terminating the loop with a success as soon as any valid file is saved.
