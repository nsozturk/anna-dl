---
title: DNS Bypass Engine
description: Bypassing ISP censorship and domain blocking
---

### How DNS Blocking Works

In multiple countries and university networks, ISPs block access to `libgen` or `annas-archive` by returning poisoned DNS results or refusing to resolve the domain names.

### The anna-dl Solution

`anna-dl` includes a built-in monkey-patch for `socket.getaddrinfo`:

```bash
anna-dl get --title "Deep Work" --author "Cal Newport" --bypass-dns
```

When `--bypass-dns` is provided, all shadow library host queries resolve directly to Cloudflare edge IP (`104.21.34.70`), completely bypassing local ISP DNS servers.
