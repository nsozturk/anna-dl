import os
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

ARXIV_PDF_BASE = "https://arxiv.org/pdf"
ARXIV_ABS_BASE = "https://arxiv.org/abs"
USER_AGENT = "SenatusAnnaDownloader/1.0 (academic-research; +https://github.com/senatus-ai)"
MIN_PDF_SIZE = 10240  # 10 KB

def download_arxiv_pdf(arxiv_id: str, dest_path: Path, max_retries: int = 3, delay: float = 0.5) -> Tuple[bool, str, int]:
    """
    Downloads an arXiv paper directly to dest_path.
    Returns: (success: bool, message: str, file_size: int)
    """
    dest_path = Path(dest_path)
    clean_id = arxiv_id.strip().rstrip('.')
    if clean_id.lower().startswith("arxiv:"):
        clean_id = clean_id[6:].strip()
    pdf_url = f"{ARXIV_PDF_BASE}/{clean_id}.pdf"
    
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/pdf,application/octet-stream,*/*",
        "Referer": f"{ARXIV_ABS_BASE}/{clean_id}"
    }

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(".tmp")

    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(pdf_url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status != 200:
                    time.sleep(delay * attempt)
                    continue

                with open(temp_path, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)

            # Validate downloaded file
            if not temp_path.exists():
                return False, "File was not written", 0

            file_size = temp_path.stat().st_size
            if file_size < MIN_PDF_SIZE:
                temp_path.unlink(missing_ok=True)
                return False, f"File too small ({file_size} bytes, likely error page)", 0

            # Check PDF header magic bytes
            with open(temp_path, "rb") as f:
                header = f.read(5)
                if not header.startswith(b"%PDF-"):
                    temp_path.unlink(missing_ok=True)
                    return False, f"Invalid PDF magic header ({header})", 0

            # Atomic rename
            temp_path.replace(dest_path)
            return True, "Downloaded successfully via arXiv", file_size

        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Not found on arXiv
                temp_path.unlink(missing_ok=True)
                return False, f"HTTP 404 Not Found on arXiv", 0
            elif e.code in (429, 503):
                # Rate limited or service unavailable, back off
                wait = (delay * 2) * attempt
                time.sleep(wait)
            else:
                time.sleep(delay * attempt)
        except Exception as e:
            time.sleep(delay * attempt)
        finally:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)

    return False, f"Failed after {max_retries} attempts", 0
