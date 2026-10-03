---
title: Quick Start
description: Start downloading books directly using anna-dl CLI
---

Download single books on the fly without setting up queue files:

### Basic Download by Title and Author

```bash
anna-dl get --title "Atomic Habits" --author "James Clear"
```

### Custom Query Override

```bash
anna-dl get --title "Thinking, Fast and Slow" --query "Kahneman Thinking Fast"
```

### Bypass ISP / DNS Censorship

If your network provider filters shadow library domains:

```bash
anna-dl get --title "Deep Work" --author "Cal Newport" --bypass-dns
```

### Custom Destination Directory

```bash
anna-dl get --title "Clean Code" --author "Robert Martin" --output-dir ./my-library
```
