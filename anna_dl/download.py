import os
import requests
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Dict, Any, Optional

from anna_dl.utils import build_queries, sanitize_filename, save_json, load_json
from anna_dl.search import search_md5_candidates, get_direct_download_url, get_working_mirror
from anna_dl.config import HEADERS, LIBGEN_MIRRORS, MIN_FILE_SIZE, ANNA_MIRRORS

def download_file(url: str, referer: str, dest_path: Path, min_size: int = MIN_FILE_SIZE) -> bool:
    """
    Streaming download with auto-resume via curl and fallback to requests,
    including file size and magic byte validation.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(f"{dest_path.suffix}.tmp")
    if temp_path.exists() and temp_path.stat().st_size < min_size:
        temp_path.unlink(missing_ok=True)

    # 1. Try curl with auto-resume and HTTP/1.1
    try:
        cmd = [
            'curl', '-C', '-', '--http1.1', '-sSL',
            '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            '--connect-timeout', '10',
            '--max-time', '60',
            '-e', referer or '',
            url,
            '-o', str(temp_path)
        ]
        for attempt in range(2):
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if temp_path.exists():
                if temp_path.stat().st_size < min_size:
                    temp_path.unlink(missing_ok=True)
                    break
                with open(temp_path, 'rb') as f:
                    magic = f.read(10)
                if magic.startswith(b'<!DOC') or magic.startswith(b'<html'):
                    temp_path.unlink(missing_ok=True)
                    break
                temp_path.replace(dest_path)
                return True
            else:
                break
    except Exception:
        if temp_path.exists() and temp_path.stat().st_size < min_size:
            temp_path.unlink(missing_ok=True)

    # 2. Fallback to requests stream
    headers = HEADERS.copy()
    if referer:
        headers['Referer'] = referer

    try:
        with requests.get(url, headers=headers, stream=True, timeout=45) as r:
            r.raise_for_status()
            with open(temp_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)

        if temp_path.exists():
            if temp_path.stat().st_size < min_size:
                temp_path.unlink(missing_ok=True)
                return False
            with open(temp_path, 'rb') as f:
                magic = f.read(10)
            if magic.startswith(b'<!DOC') or magic.startswith(b'<html'):
                temp_path.unlink(missing_ok=True)
                return False
            temp_path.replace(dest_path)
            return True
    except Exception:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        return False

    return False

def download_book(
    book: Dict[str, Any],
    anna_mirror: str,
    output_dir: Path,
    log_data: Optional[Dict[str, Any]] = None,
    log_file: Optional[Path] = None
) -> bool:
    """
    Full resilient retrieval pipeline for a single book:
    Multi-query fallbacks -> 10-candidate MD5 resolution -> direct stream -> validation.
    """
    title = book.get('title', 'Unknown')
    author = book.get('author', 'Unknown')
    group = book.get('category_group', book.get('category', ''))
    subcat = book.get('subcategory', '')

    queries = build_queries(title, author, book.get('search_query', ''))
    print(f"\n🔍 Searching for: {title} ({author})")

    for query in queries:
        print(f"  ↳ Trying query: '{query}'")
        md5_candidates = search_md5_candidates(query, anna_mirror)
        if md5_candidates:
            print(f"    [+] Found {len(md5_candidates)} MD5 candidate(s). Resolving download mirrors...")
            for idx, md5 in enumerate(md5_candidates, 1):
                url, ext, referer = get_direct_download_url(md5, LIBGEN_MIRRORS)
                if url and ext:
                    filename = sanitize_filename(f"{title} - {author}.{ext}")
                    if group and subcat:
                        dest_path = output_dir / sanitize_filename(group) / sanitize_filename(subcat) / filename
                    elif group:
                        dest_path = output_dir / sanitize_filename(group) / filename
                    else:
                        dest_path = output_dir / filename

                    print(f"    [+] Probing candidate #{idx} ({md5[:8]}...) -> {ext.upper()} stream...")
                    if download_file(url, referer or '', dest_path):
                        # Detect true format from magic bytes
                        with open(dest_path, 'rb') as fp:
                            magic = fp.read(4)
                        if magic == b'PK\x03\x04' and dest_path.suffix != '.epub':
                            new_path = dest_path.with_suffix('.epub')
                            dest_path.rename(new_path)
                            dest_path = new_path
                        elif magic.startswith(b'%PDF') and dest_path.suffix != '.pdf':
                            new_path = dest_path.with_suffix('.pdf')
                            dest_path.rename(new_path)
                            dest_path = new_path

                        size_mb = round(dest_path.stat().st_size / (1024 * 1024), 2)
                        print(f"    [✔] SUCCESS ({size_mb} MB) -> {dest_path}", flush=True)
                        if log_data is not None and log_file is not None:
                            item_key = f"{title} - {author}"
                            log_data[item_key] = {
                                'status': 'SUCCESS',
                                'path': str(dest_path),
                                'bytes': dest_path.stat().st_size
                            }
                            save_json(log_file, log_data)
                        return True

    print(f"    [-] Exhausted all candidates for '{title}'.", flush=True)
    if log_data is not None and log_file is not None:
        item_key = f"{title} - {author}"
        log_data[item_key] = {'status': 'FAILED'}
        save_json(log_file, log_data)
    return False

def download_batch(
    books: List[Dict[str, Any]],
    output_dir: Path,
    queue_file: Path,
    log_file: Path,
    limit: int = 0,
    categories: str = ''
) -> None:
    """
    Sequential batch download with category filtering and atomic progress tracking.
    """
    anna_mirror = get_working_mirror(ANNA_MIRRORS, HEADERS)
    log_data = load_json(log_file, default={})
    cats = [c.strip() for c in categories.split(',')] if categories else []

    count = 0
    for book in books:
        if limit > 0 and count >= limit:
            break
        group = str(book.get('category_group', book.get('category', '')))
        if cats and not any(group.startswith(c) or group == c for c in cats):
            continue

        item_key = f"{book.get('title', '')} - {book.get('author', '')}"
        if log_data.get(item_key, {}).get('status') == 'SUCCESS':
            continue

        download_book(book, anna_mirror, output_dir, log_data, log_file)
        count += 1

def download_parallel(
    books: List[Dict[str, Any]],
    output_dir: Path,
    log_file: Path,
    categories: str = '',
    max_workers: int = 4
) -> None:
    """
    Multi-threaded parallel download using ThreadPoolExecutor.
    """
    anna_mirror = get_working_mirror(ANNA_MIRRORS, HEADERS)
    log_data = load_json(log_file, default={})
    lock = threading.Lock()
    cats = [c.strip() for c in categories.split(',')] if categories else []

    books_to_download = []
    for book in books:
        group = str(book.get('category_group', book.get('category', '')))
        if cats and not any(group.startswith(c) or group == c for c in cats):
            continue
        item_key = f"{book.get('title', '')} - {book.get('author', '')}"
        if log_data.get(item_key, {}).get('status') == 'SUCCESS':
            continue

        # Check if already present on disk in any valid extension
        title = book.get('title', '')
        author = book.get('author', '')
        subcat = str(book.get('subcategory', ''))
        already_on_disk = False
        for ext in ('pdf', 'epub', 'mobi', 'azw3'):
            fn = sanitize_filename(f"{title} - {author}.{ext}")
            if group and subcat:
                p = output_dir / sanitize_filename(group) / sanitize_filename(subcat) / fn
            elif group:
                p = output_dir / sanitize_filename(group) / fn
            else:
                p = output_dir / fn
            if p.exists() and p.stat().st_size > 10000:
                already_on_disk = True
                log_data[item_key] = {'status': 'SUCCESS', 'path': str(p), 'bytes': p.stat().st_size}
                break
        if already_on_disk:
            continue

        books_to_download.append(book)

    save_json(log_file, log_data)
    print(f"🚀 Starting parallel download for {len(books_to_download)} book(s) across {max_workers} worker(s)...", flush=True)

    def worker(book):
        title = book.get('title', 'Unknown')
        author = book.get('author', 'Unknown')
        group = book.get('category_group', book.get('category', ''))
        subcat = book.get('subcategory', '')
        item_key = f"{title} - {author}"

        queries = build_queries(title, author, book.get('search_query', ''))
        for query in queries:
            md5_candidates = search_md5_candidates(query, anna_mirror)
            for md5 in md5_candidates:
                url, ext, referer = get_direct_download_url(md5, LIBGEN_MIRRORS)
                if url and ext:
                    filename = sanitize_filename(f"{title} - {author}.{ext}")
                    if group and subcat:
                        dest_path = output_dir / sanitize_filename(group) / sanitize_filename(subcat) / filename
                    elif group:
                        dest_path = output_dir / sanitize_filename(group) / filename
                    else:
                        dest_path = output_dir / filename

                    if download_file(url, referer or '', dest_path):
                        # Detect true format from magic bytes
                        with open(dest_path, 'rb') as fp:
                            magic = fp.read(4)
                        if magic == b'PK\x03\x04' and dest_path.suffix != '.epub':
                            new_path = dest_path.with_suffix('.epub')
                            dest_path.rename(new_path)
                            dest_path = new_path
                        elif magic.startswith(b'%PDF') and dest_path.suffix != '.pdf':
                            new_path = dest_path.with_suffix('.pdf')
                            dest_path.rename(new_path)
                            dest_path = new_path

                        size_mb = round(dest_path.stat().st_size / (1024 * 1024), 2)
                        print(f"  [✔] SUCCESS ({size_mb} MB) -> {dest_path.name}", flush=True)
                        with lock:
                            log_data[item_key] = {
                                'status': 'SUCCESS',
                                'path': str(dest_path),
                                'bytes': dest_path.stat().st_size
                            }
                            save_json(log_file, log_data)
                        return True
        print(f"  [✖] FAILED -> {item_key}", flush=True)
        with lock:
            log_data[item_key] = {'status': 'FAILED'}
            save_json(log_file, log_data)
        return False

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(worker, books_to_download))
