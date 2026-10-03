import argparse
import sys
from pathlib import Path
from anna_dl import config
from anna_dl.download import download_batch, download_parallel, download_book
from anna_dl.search import get_working_mirror
from anna_dl.extract import extract_books
from anna_dl.sync import sync_log_from_disk
from anna_dl.utils import load_json

def main():
    parser = argparse.ArgumentParser(
        prog="anna-dl",
        description="anna-dl — Resilient, Zero-Key Shadow Library Downloader CLI & Agent"
    )
    parser.add_argument(
        'command',
        choices=['get', 'download', 'retry', 'extract', 'sync', 'status'],
        help="Action to perform: get (single book), download (queue), retry (failed), extract (from md), sync (verify disk), status"
    )

    parser.add_argument('--title', type=str, help="Book title (required for 'get')")
    parser.add_argument('--author', type=str, default='', help="Author name")
    parser.add_argument('--query', type=str, default='', help="Custom search query override")

    parser.add_argument('--output-dir', type=Path, default=Path(config.DEFAULT_OUTPUT_DIR), help="Output directory (default: ./downloads)")
    parser.add_argument('--queue-file', type=Path, default=Path(config.DEFAULT_QUEUE_FILE), help="Path to books_queue.json")
    parser.add_argument('--log-file', type=Path, default=Path(config.DEFAULT_LOG_FILE), help="Path to download_log.json")
    parser.add_argument('--bypass-dns', action='store_true', help="Bypass DNS blocks for shadow library domains via direct edge IP")

    parser.add_argument('--limit', type=int, default=0, help="Limit number of books to download in batch (0 = all)")
    parser.add_argument('--categories', type=str, default='', help="Comma-separated category prefixes to filter by")
    parser.add_argument('--parallel', action='store_true', help="Enable multi-worker parallel downloading")
    parser.add_argument('--workers', type=int, default=4, help="Worker concurrency level (default: 4)")

    parser.add_argument('--docs-dir', type=Path, help="Directory containing markdown book catalogs for 'extract'")

    args = parser.parse_args()

    if args.bypass_dns:
        config.enable_dns_bypass()

    try:
        if args.command == 'get':
            if not args.title:
                print("Error: --title is required for 'get' command.")
                print("Usage: anna-dl get --title 'Atomic Habits' --author 'James Clear'")
                sys.exit(1)

            args.output_dir.mkdir(parents=True, exist_ok=True)
            anna_mirror = get_working_mirror(config.ANNA_MIRRORS, config.HEADERS)
            book_dict = {
                'title': args.title,
                'author': args.author,
                'search_query': args.query
            }
            log_data = load_json(args.log_file, default={})
            ok = download_book(book_dict, anna_mirror, args.output_dir, log_data, args.log_file)
            sys.exit(0 if ok else 1)

        elif args.command == 'extract':
            if not args.docs_dir:
                print("Error: --docs-dir is required for 'extract' command.")
                sys.exit(1)
            count = extract_books(args.docs_dir, args.queue_file)
            print(f"[✔] Successfully extracted {count} book(s) into {args.queue_file}")

        elif args.command in ('download', 'retry'):
            args.output_dir.mkdir(parents=True, exist_ok=True)
            queue = load_json(args.queue_file, default=[])
            if not queue:
                print(f"[!] Queue file {args.queue_file} is empty or not found.")
                print("Tip: Use `anna-dl get --title '...'` for single books or `anna-dl extract --docs-dir ...` to create a queue.")
                sys.exit(1)

            if args.command == 'retry':
                log_data = load_json(args.log_file, default={})
                queue = [
                    b for b in queue
                    if log_data.get(f"{b.get('title', '')} - {b.get('author', '')}", {}).get('status') != 'SUCCESS'
                ]
                print(f"[*] Retrying {len(queue)} pending/failed book(s)...")

            if args.parallel:
                download_parallel(queue, args.output_dir, args.log_file, args.categories, args.workers)
            else:
                download_batch(queue, args.output_dir, args.queue_file, args.log_file, args.limit, args.categories)

        elif args.command == 'sync':
            stats = sync_log_from_disk(args.output_dir, args.queue_file, args.log_file)
            print("[✔] Synchronization complete:")
            for k, v in stats.items():
                print(f"  • {k}: {v}")

        elif args.command == 'status':
            stats = sync_log_from_disk(args.output_dir, args.queue_file, args.log_file)
            print("Current Download Status:")
            for k, v in stats.items():
                print(f"  • {k}: {v}")

    except KeyboardInterrupt:
        print("\n[!] Execution interrupted by user.")
        sys.exit(1)

if __name__ == "__main__":
    main()
