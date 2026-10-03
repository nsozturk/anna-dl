---
title: Claude Code & AI Agents
description: Autonomous integration for LLMs and coding assistants
---

`anna-dl` is designed from the ground up for agentic execution. It operates without interactive prompts, returns standard POSIX exit codes (`0` on success, `1` on failure), and performs atomic JSON logging.

### Execution Contracts

When an AI agent (Claude Code, Gemini CLI, Cursor, Antigravity, OpenCode, Codex) needs to download a book:

```bash
anna-dl get --title "<Book Title>" --author "<Author Name>"
```

If the command fails due to connection reset or domain filtering, the agent immediately retries with:

```bash
anna-dl get --title "<Book Title>" --author "<Author Name>" --bypass-dns
```
