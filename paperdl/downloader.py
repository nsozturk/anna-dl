import os
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional

from paperdl.parser import sanitize_filename
from paperdl.arxiv import download_arxiv_pdf
from paperdl.fallback import download_via_annas_fallback

DEFAULT_OUTPUT_DIR = Path.cwd() / "downloads" / "papers"
SENATUS_PAPERS_LINK = Path(os.environ.get("SENATUS_PAPERS_LINK", "")) if os.environ.get("SENATUS_PAPERS_LINK") else None

def is_valid_pdf(path: Path, min_size: int = 10240) -> bool:
    """Checks if a file exists, meets minimum size, and starts with %PDF-."""
    if not path.exists():
        return False
    if path.stat().st_size < min_size:
        return False
    try:
        with open(path, "rb") as f:
            header = f.read(5)
            return header.startswith(b"%PDF-")
    except Exception:
        return False

def download_single_paper(paper: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
    """
    Downloads a single paper, checking arXiv first and falling back to Anna's Archive.
    """
    arxiv_id = paper.get("arxiv_id")
    title = paper.get("title", "Untitled")
    folder_name = paper.get("folder", "general")
    
    clean_title = sanitize_filename(title, max_len=90)
    if arxiv_id:
        filename = f"{arxiv_id}_{clean_title}.pdf"
    else:
        filename = f"{clean_title}.pdf"
        
    dest_path = output_dir / folder_name / filename
    
    # Check if already present and valid
    if is_valid_pdf(dest_path):
        size = dest_path.stat().st_size
        return {
            "arxiv_id": arxiv_id,
            "title": title,
            "section": folder_name,
            "section_title": paper.get("section_title", ""),
            "status": "ALREADY_EXISTS",
            "source": "cache",
            "path": str(dest_path),
            "bytes": size,
            "size_mb": round(size / (1024 * 1024), 2),
            "notes": paper.get("notes", ""),
            "affiliation": paper.get("affiliation", ""),
            "date": paper.get("date", "")
        }

    # 1. Try arXiv direct
    if arxiv_id:
        success, msg, size = download_arxiv_pdf(arxiv_id, dest_path)
        if success:
            return {
                "arxiv_id": arxiv_id,
                "title": title,
                "section": folder_name,
                "section_title": paper.get("section_title", ""),
                "status": "SUCCESS",
                "source": "arxiv",
                "path": str(dest_path),
                "bytes": size,
                "size_mb": round(size / (1024 * 1024), 2),
                "notes": paper.get("notes", ""),
                "affiliation": paper.get("affiliation", ""),
                "date": paper.get("date", "")
            }

    # 2. Try Anna's Archive / LibGen fallback
    success, msg, size = download_via_annas_fallback(title, dest_path, author=paper.get("affiliation", ""))
    if success:
        return {
            "arxiv_id": arxiv_id,
            "title": title,
            "section": folder_name,
            "section_title": paper.get("section_title", ""),
            "status": "SUCCESS",
            "source": "annas_archive_libgen",
            "path": str(dest_path),
            "bytes": size,
            "size_mb": round(size / (1024 * 1024), 2),
            "notes": paper.get("notes", ""),
            "affiliation": paper.get("affiliation", ""),
            "date": paper.get("date", "")
        }

    return {
        "arxiv_id": arxiv_id,
        "title": title,
        "section": folder_name,
        "section_title": paper.get("section_title", ""),
        "status": "FAILED",
        "source": "none",
        "error": msg,
        "path": str(dest_path),
        "bytes": 0,
        "size_mb": 0,
        "notes": paper.get("notes", ""),
        "affiliation": paper.get("affiliation", ""),
        "date": paper.get("date", "")
    }

def run_batch_download(papers: List[Dict[str, Any]], output_dir: Path = DEFAULT_OUTPUT_DIR, max_workers: int = 3) -> Dict[str, Any]:
    """
    Executes batch download with concurrency and generates manifest and INDEX.md.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    
    # Load existing manifest if present
    manifest = {}
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            manifest = {}

    results = []
    total = len(papers)
    print(f"\n🚀 Starting download queue for {total} papers (workers: {max_workers}) -> {output_dir}")

    # Use ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_paper = {
            executor.submit(download_single_paper, p, output_dir): p for p in papers
        }
        
        completed = 0
        for future in as_completed(future_to_paper):
            completed += 1
            paper = future_to_paper[future]
            try:
                res = future.result()
            except Exception as exc:
                res = {
                    "arxiv_id": paper.get("arxiv_id"),
                    "title": paper.get("title"),
                    "section": paper.get("folder"),
                    "status": "ERROR",
                    "error": str(exc),
                    "bytes": 0
                }
            results.append(res)
            
            # Print status
            st = res.get("status")
            size_mb = res.get("size_mb", 0)
            aid = res.get("arxiv_id") or "NO-ID"
            t = res.get("title", "")[:45]
            folder = res.get("section", "")
            
            if st in ("SUCCESS", "ALREADY_EXISTS"):
                src = res.get("source")
                print(f"[{completed}/{total}] [✔ {st}] ({size_mb} MB, {src}) {folder}/{aid} - {t}")
            else:
                print(f"[{completed}/{total}] [✗ {st}] {folder}/{aid} - {t} ({res.get('error', '')})")

            # Update manifest
            key = f"{aid}_{paper.get('title')}"
            manifest[key] = res
            
            # Save manifest periodically
            if completed % 5 == 0 or completed == total:
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(manifest, f, indent=2, ensure_ascii=False)

    # Generate Markdown Index
    generate_markdown_index(results, output_dir)
    
    # Create or update symlink for Senatus if RSI papers
    if "rsi" in str(output_dir).lower() or "senatus" in str(output_dir).lower():
        setup_senatus_symlink(output_dir)

    successes = sum(1 for r in results if r.get("status") in ("SUCCESS", "ALREADY_EXISTS"))
    fails = sum(1 for r in results if r.get("status") not in ("SUCCESS", "ALREADY_EXISTS"))
    total_mb = round(sum(r.get("bytes", 0) for r in results) / (1024 * 1024), 2)
    
    summary = {
        "total": total,
        "successes": successes,
        "failures": fails,
        "total_megabytes": total_mb,
        "output_dir": str(output_dir),
        "manifest": str(manifest_path)
    }
    
    print("\n" + "="*60)
    print(f"🎉 Batch Download Finished:")
    print(f"  Total Processed: {total}")
    print(f"  Successful:      {successes}")
    print(f"  Failed:          {fails}")
    print(f"  Total Size:      {total_mb} MB")
    print(f"  Manifest:        {manifest_path}")
    print("="*60 + "\n")
    
    return summary

def generate_markdown_index(results: List[Dict[str, Any]], output_dir: Path) -> Path:
    """
    Generates a master INDEX.md in the downloads directory referencing all papers.
    """
    index_path = output_dir / "INDEX.md"
    
    # Group results by section
    by_section = {}
    for r in results:
        sec = r.get("section", "other")
        by_section.setdefault(sec, []).append(r)

    dir_title = output_dir.name.replace('_', ' ').replace('-', ' ').title()
    lines = [
        f"# {dir_title} Archive",
        "",
        f"> Generated on {time.strftime('%Y-%m-%d %H:%M:%S')} by Anna `paperdl` Agent.",
        f"> **Total Cataloged**: {len(results)} papers | **Storage**: `{output_dir}`",
        "",
        "---",
        ""
    ]

    for sec, items in sorted(by_section.items()):
        items_sorted = sorted(items, key=lambda x: x.get("arxiv_id") or "")
        lines.append(f"## {sec.replace('_', ' ').title()}")
        lines.append("")
        lines.append("| Status | arXiv ID | Title | Size | Local File |")
        lines.append("|---|---|---|---|---|")
        for item in items_sorted:
            st = "✅" if item.get("status") in ("SUCCESS", "ALREADY_EXISTS") else "❌"
            aid = item.get("arxiv_id") or "—"
            t = item.get("title", "").replace("|", "\\|")
            size = f"{item.get('size_mb', 0)} MB"
            p = item.get("path", "")
            if p and Path(p).exists():
                rel_path = Path(p).name
                file_link = f"[{rel_path}]({sec}/{rel_path})"
            else:
                file_link = "—"
            lines.append(f"| {st} | {aid} | {t} | {size} | {file_link} |")
        lines.append("")

    with open(index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    return index_path

def setup_senatus_symlink(source_dir: Path, target_link: Optional[Path] = SENATUS_PAPERS_LINK) -> None:
    """
    Creates a symlink from Senatus docs to Anna's downloads directory if target_link is provided.
    """
    if not target_link:
        return
    try:
        target_link.parent.mkdir(parents=True, exist_ok=True)
        if target_link.is_symlink() or target_link.exists():
            if target_link.is_symlink() and target_link.resolve() == source_dir.resolve():
                return
            target_link.unlink()
        target_link.symlink_to(source_dir.resolve(), target_is_directory=True)
        print(f"🔗 Linked: {target_link} -> {source_dir}")
    except Exception as e:
        print(f"⚠️ Could not create symlink {target_link}: {e}")
