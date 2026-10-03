import os
from pathlib import Path
from typing import Dict, Any
from anna_dl.utils import load_json, save_json, sanitize_filename

def sync_log_from_disk(output_dir: Path, queue_file: Path, log_file: Path) -> Dict[str, Any]:
    """
    Scans files on disk and reconciles them against queue entries and download log.
    Returns status statistics dictionary.
    """
    queue = load_json(queue_file, default=[])
    log_data = load_json(log_file, default={})

    disk_files = []
    if output_dir.exists():
        for root, _, files in os.walk(output_dir):
            for file in files:
                if file.endswith(('.pdf', '.epub', '.mobi', '.djvu')):
                    disk_files.append((file, os.path.join(root, file)))

    synced = 0
    success = 0
    failed = 0

    for book in queue:
        item_key = f"{book.get('title', '')} - {book.get('author', '')}"
        title = book.get('title', '')
        author = book.get('author', '')

        base_name = sanitize_filename(f"{title} - {author}")
        found = False

        for f_name, f_path in disk_files:
            if f_name.startswith(base_name):
                found = True
                log_data[item_key] = {
                    'status': 'SUCCESS',
                    'path': f_path,
                    'bytes': os.path.getsize(f_path)
                }
                synced += 1
                success += 1
                break

        if not found:
            if log_data.get(item_key, {}).get('status') == 'SUCCESS':
                log_data[item_key] = {'status': 'FAILED'}
            if log_data.get(item_key, {}).get('status') == 'FAILED':
                failed += 1

    save_json(log_file, log_data)

    total = len(queue)
    not_found = total - success - failed

    return {
        'total': total,
        'success': success,
        'failed': failed,
        'not_found': not_found,
        'remaining': max(0, total - success),
        'synced': synced
    }
