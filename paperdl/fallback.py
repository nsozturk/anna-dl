import os
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

from bookdl import config
from bookdl.search import search_md5_candidates, get_direct_download_url, get_working_mirror
from bookdl.download import download_file
from bookdl.utils import sanitize_filename, build_queries

def download_via_annas_fallback(title: str, dest_path: Path, author: str = "") -> Tuple[bool, str, int]:
    """
    Attempts to download a paper/document using Anna's Archive and LibGen mirrors.
    """
    dest_path = Path(dest_path)
    anna_mirror = get_working_mirror(config.ANNA_MIRRORS, config.HEADERS)
    queries = build_queries(title, author)
    
    for query in queries:
        md5_candidates = search_md5_candidates(query, anna_mirror, max_candidates=5)
        if not md5_candidates:
            continue
            
        for md5 in md5_candidates:
            url, ext, referer = get_direct_download_url(md5, config.LIBGEN_MIRRORS)
            if url and ext:
                target_file = dest_path.with_suffix(f".{ext}")
                if download_file(url, referer or "", target_file):
                    # Check PDF magic if pdf
                    if ext == "pdf":
                        with open(target_file, "rb") as f:
                            header = f.read(5)
                            if not header.startswith(b"%PDF-"):
                                target_file.unlink(missing_ok=True)
                                continue
                    size = target_file.stat().st_size
                    return True, f"Downloaded via Anna's Archive/LibGen ({md5[:8]})", size

    return False, "Not found on Anna's Archive / LibGen mirrors", 0
