---
title: Batch & Parallel Downloads
description: Process large queues with multi-worker threads
---

### Batch Sequential Download

```bash
anna-dl download
```

### High-Throughput Parallel Concurrency

Speed up retrieval across independent category groups with 4 concurrent worker threads:

```bash
anna-dl download --parallel --workers 4
```

### Filtering by Category

Download only specific categories (e.g. `01`, `02`):

```bash
anna-dl download --categories 01,02
```

### Retrying Failed Items

```bash
anna-dl retry --bypass-dns
```
