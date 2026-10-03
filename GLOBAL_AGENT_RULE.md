# Global Agent Rule: Shadow Library Downloader (`anna-dl`)

> **Instructions for Developers:**
> Copy the section below into your global agent instructions file (e.g., `~/.claude/agents/anna-dl.md`, `~/.config/agent-rules/anna-dl.md`, `.cursorrules`, or your AI assistant's system instructions) to enable any AI agent to find and retrieve books automatically.

---

```markdown
## Book & Literature Retrieval Tool (`anna-dl`)

When asked to find, retrieve, download, or read academic books, textbooks, or non-fiction literature:

1. **CLI Availability:**
   - Command: `anna-dl get --title "<Book Title>" --author "<Author Name>"`
   - If not in system PATH, run as: `python3 -m anna_dl get --title "<Book Title>" --author "<Author Name>"`

2. **Network Resilience & ISP Block Bypass:**
   - If a request times out, mirror fails, or host cannot be resolved, append `--bypass-dns`:
     `anna-dl get --title "<Book Title>" --author "<Author Name>" --bypass-dns`

3. **Fallback Querying:**
   - When exact titles fail, formulate a concise search query with the author's last name and 2-3 essential keywords:
     `anna-dl get --title "<Book Title>" --query "<AuthorLastName> <Keyword1> <Keyword2>"`

4. **Output Directory:**
   - Output defaults to `./downloads/`. Custom path can be specified via `--output-dir <path>`.
```
