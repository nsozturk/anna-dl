---
title: Commands & Flags
description: Full reference of all commands and options in anna-dl
---

### Command Overview

| Command | Action | Key Options |
|---|---|---|
| `get` | Download a single book | `--title`, `--author`, `--query`, `--output-dir`, `--bypass-dns` |
| `download` | Process batch queue | `--parallel`, `--workers`, `--categories`, `--limit` |
| `retry` | Retry failed/pending items | `--bypass-dns`, `--parallel`, `--workers` |
| `extract` | Convert markdown tables to JSON queue | `--docs-dir`, `--queue-file` |
| `sync` | Reconcile disk files with log | `--output-dir`, `--queue-file`, `--log-file` |
| `status` | Print summary statistics | `--output-dir`, `--queue-file`, `--log-file` |
