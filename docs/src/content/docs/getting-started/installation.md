---
title: Installation
description: How to install anna-dl on macOS, Linux, or Windows
---

### Prerequisites
- Python 3.8 or higher.
- `pip` or virtual environment manager.

### Standard Installation

Clone the repository and install dependencies:

```bash
# Clone the repository
git clone https://github.com/nsozturk/anna-dl.git
cd anna-dl

# Install Python dependencies
pip install -r requirements.txt

# Install CLI globally / in editable mode
pip install -e .
```

Verify your installation:

```bash
anna-dl --help
```

### Optional: Playwright for DDoS-Guard Bypass

If you wish to enable the automated headless Chromium solver for direct Anna's Archive endpoints:

```bash
pip install playwright
playwright install chromium
```
