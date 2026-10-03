---
title: Global Agent Rule
description: Plug-and-play prompt snippet for developer AI assistants
---

Add this section to your local assistant's instructions (`~/.claude/agents/anna-dl.md` or `.cursorrules`):

```markdown
## Book & Literature Retrieval Tool (`anna-dl`)

When asked to find, retrieve, download, or read academic books, textbooks, or non-fiction literature:

1. **CLI Availability:**
   - Command: `anna-dl get --title "<Book Title>" --author "<Author Name>"`

2. **Network Resilience & ISP Block Bypass:**
   - If a request times out, mirror fails, or host cannot be resolved, append `--bypass-dns`:
     `anna-dl get --title "<Book Title>" --author "<Author Name>" --bypass-dns`

3. **Fallback Querying:**
   - When exact titles fail, formulate a concise search query with the author's last name and 2-3 essential keywords:
     `anna-dl get --title "<Book Title>" --query "<AuthorLastName> <Keyword1> <Keyword2>"`

4. **Output Directory:**
   - Output defaults to `./downloads/`. Custom path can be specified via `--output-dir <path>`.
```
