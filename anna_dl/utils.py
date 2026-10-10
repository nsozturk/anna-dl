import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, List

def sanitize_filename(name: str) -> str:
    """
    Strips illegal filesystem characters and limits filename length to 150 characters.
    """
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    return name.strip()[:150]

def clean_query_text(text: str) -> str:
    """
    Removes parentheticals, bracketed notations, and common edition markers.
    """
    text = re.sub(r'\(.*?\)', '', text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\b(ed\.|eds\.|vol\.|rev\.|2nd|3rd|4th|5th)\b', '', text, flags=re.IGNORECASE)
    return text.strip()

def build_queries(title: str, author: str = '', search_query: str = '') -> List[str]:
    """
    Generates an ordered progression of fallback queries:
    1. Explicit custom search query (if supplied)
    2. Full cleaned title + primary author
    3. Short title (pre-colon/dash) + author last name
    4. Short title alone
    5. Cleaned full title alone (if different from short title)
    6. Author last name + top keywords
    7. Niche keywords alone
    """
    queries = []
    if search_query:
        queries.append(search_query)

    clean_title = clean_query_text(title)
    clean_author = clean_query_text(author)
    primary_author = clean_author.split(',')[0].strip() if clean_author else ''
    last_name = primary_author.split()[-1] if primary_author else ''

    if primary_author:
        queries.append(f"{clean_title} {primary_author}".strip())
    else:
        queries.append(clean_title)

    short_title = re.split(r'[:\-—]', clean_title)[0].strip()
    if last_name:
        queries.append(f"{short_title} {last_name}".strip())
    if short_title:
        queries.append(short_title)
    if clean_title and clean_title != short_title:
        queries.append(clean_title)

    stopwords = {'with', 'from', 'this', 'that', 'then', 'than', 'into', 'upon', 'over', 'some', 'such', 'about', 'guide', 'the', 'a', 'an', 'and', 'of', 'in', 'on', 'for', 'to', 'how'}
    sig_words = [w for w in re.findall(r'\b[a-zA-Z]{3,}\b', clean_title) if w.lower() not in stopwords]
    if sig_words:
        if last_name:
            queries.append(f"{last_name} {' '.join(sig_words[:2])}".strip())
            queries.append(f"{last_name} {' '.join(sig_words[:3])}".strip())
        queries.append(f"{' '.join(sig_words[:2])}".strip())

    words = [w for w in re.findall(r'\b\w{4,}\b', clean_title.lower()) if w not in stopwords]
    niche_keywords = " ".join(words[:4])
    if niche_keywords and last_name:
        queries.append(f"{niche_keywords} {last_name}".strip())

    deduped = []
    for q in queries:
        q = q.strip()
        if q and q not in deduped:
            deduped.append(q)

    return deduped

def load_json(filepath: Path, default: Any = None) -> Any:
    """
    Safely reads JSON files, returning default fallback on missing or corrupt files.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save_json(filepath: Path, data: Any) -> None:
    """
    Performs atomic writes using tempfile + os.replace to prevent file corruption.
    """
    filepath = Path(filepath)
    dir_name = filepath.parent
    dir_name.mkdir(parents=True, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(dir=dir_name, text=True)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(temp_path, filepath)
