import argparse
import sys
from pathlib import Path

from paperdl.parser import parse_research_markdown
from paperdl.downloader import run_batch_download, DEFAULT_OUTPUT_DIR, is_valid_pdf
from paperdl.resolver import retrieve_paper

def main():
    parser = argparse.ArgumentParser(description="paperdl — Academic Paper Retrieval & Downloader Agent for Anna")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Command: md
    parser_md = subparsers.add_parser("md", help="Download all papers parsed from a research markdown file")
    parser_md.add_argument("markdown_file", type=Path, help="Path to research markdown file")
    parser_md.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Destination directory")
    parser_md.add_argument("--workers", type=int, default=3, help="Concurrent worker threads (default 3)")

    # Command: get
    parser_get = subparsers.add_parser("get", help="Download a single paper by arXiv ID, SSRN ID, DOI, URL, or Title")
    parser_get.add_argument("--arxiv", type=str, help="arXiv ID (e.g. 2306.13661)")
    parser_get.add_argument("--ssrn", type=str, help="SSRN Abstract ID (e.g. 4857230)")
    parser_get.add_argument("--doi", type=str, help="Digital Object Identifier (e.g. 10.1016/...)")
    parser_get.add_argument("--url", type=str, help="Direct URL to paper or PDF")
    parser_get.add_argument("--title", type=str, help="Paper title")
    parser_get.add_argument("--chrome", action="store_true", help="Force or enable Google Chrome native bypass")
    parser_get.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Destination directory")
    parser_get.add_argument("--dest", type=Path, help="Explicit destination file path (overrides --output-dir)")

    # Command: status
    parser_status = subparsers.add_parser("status", help="Check status of paper archive")
    parser_status.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory to check")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "md":
        if not args.markdown_file.exists():
            print(f"Error: file not found: {args.markdown_file}")
            sys.exit(1)
        papers = parse_research_markdown(args.markdown_file)
        summary = run_batch_download(papers, output_dir=args.output_dir, max_workers=args.workers)
        sys.exit(0 if summary["failures"] == 0 else 1)

    elif args.command == "get":
        if args.dest:
            dest = args.dest
        else:
            output_dir = args.output_dir
            output_dir.mkdir(parents=True, exist_ok=True)
            if args.arxiv:
                dest = output_dir / f"arxiv_{args.arxiv}.pdf"
            elif args.ssrn:
                dest = output_dir / f"ssrn_{args.ssrn}.pdf"
            elif args.doi:
                clean_doi = args.doi.replace("/", "_")
                dest = output_dir / f"doi_{clean_doi}.pdf"
            elif args.title:
                clean_title = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in args.title)[:60]
                dest = output_dir / f"{clean_title}.pdf"
            elif args.url:
                dest = output_dir / "downloaded_paper.pdf"
            else:
                print("Error: Specify at least one identifier (--arxiv, --ssrn, --doi, --url, or --title)")
                sys.exit(1)

        identifier = args.arxiv or args.ssrn or args.doi or args.url or args.title
        print(f"Resolving paper identifier: '{identifier}' -> {dest}")
        ok, msg, sz = retrieve_paper(
            identifier=identifier,
            dest=dest,
            use_chrome=args.chrome,
            title_hint=args.title,
        )
        if ok:
            mb = sz / (1024 * 1024)
            print(f"\n[✔] SUCCESS ({mb:.2f} MB): {dest}\n    Method: {msg}")
            sys.exit(0)
        else:
            print(f"\n[✗] FAILED: {msg}")
            sys.exit(1)

    elif args.command == "status":
        out = args.output_dir
        if not out.exists():
            print(f"Directory {out} does not exist.")
            sys.exit(0)
        pdf_files = list(out.glob("**/*.pdf"))
        valid_files = [f for f in pdf_files if is_valid_pdf(f)]
        total_size = sum(f.stat().st_size for f in valid_files)
        print(f"Archive Status for {out}:")
        print(f"  Total Valid PDFs: {len(valid_files)}")
        print(f"  Total Size:       {total_size / (1024 * 1024):.2f} MB")
        manifest = out / "manifest.json"
        if manifest.exists():
            print(f"  Manifest:         {manifest}")

if __name__ == "__main__":
    main()
