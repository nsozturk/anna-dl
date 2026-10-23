import re
from pathlib import Path
from typing import List, Dict, Any, Optional

SECTION_FOLDER_MAP = {
    "1": "01_recursive_self_improvement",
    "2": "02_debate_juries_and_aggregation",
    "3": "03_agent_memory_and_experience_reuse",
    "4": "04_coding_agents_review_and_verification",
    "5": "05_routing_model_selection_and_calibration",
    "6": "06_world_models_replay_and_meta_exploration",
    "7": "07_unverified_and_borderline",
}

def sanitize_filename(name: str, max_len: int = 120) -> str:
    """Strips illegal characters and trims to max_len."""
    # Replace slashes, colons, quotes etc
    clean = re.sub(r'[\\/*?:"<>|]', '', name)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean[:max_len].rstrip(' .')

def parse_research_markdown(filepath: Path) -> List[Dict[str, Any]]:
    """
    Parses Senatus RSI/AGI papers research markdown and extracts structured paper objects.
    """
    text = Path(filepath).read_text(encoding="utf-8")
    
    # Split by level 2 headers
    section_chunks = re.split(r'\n(?=##\s+)', text)
    papers = []
    seen_ids = set()

    for chunk in section_chunks:
        lines = chunk.strip().splitlines()
        if not lines:
            continue
            
        header = lines[0].replace('##', '').strip()
        m_sec = re.match(r'^([0-9]+)\.\s*(.*)', header)
        if not m_sec:
            continue
            
        sec_num = m_sec.group(1)
        sec_title = m_sec.group(2).strip()
        slug = re.sub(r'[^a-zA-Z0-9]+', '_', sec_title.lower()).strip('_')
        folder_name = f"{int(sec_num):02d}_{slug}" if slug else SECTION_FOLDER_MAP.get(sec_num, f"section_0{sec_num}")
        
        # Parse items in this section
        if sec_num == "7":
            # Table parser for Section 7
            for line in lines:
                if line.startswith('|') and not line.startswith('| Claimed') and not line.startswith('|---') and not line.startswith('| Model'):
                    cols = [c.strip() for c in line.split('|')[1:-1]]
                    if len(cols) >= 2:
                        claimed_title = cols[0]
                        id_col = cols[1]
                        notes = cols[2] if len(cols) > 2 else ""
                        
                        # Check for arxiv IDs
                        arxiv_ids = re.findall(r'\b[0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?\b', id_col)
                        if arxiv_ids:
                            # If multiple IDs in one row (e.g. MemSkill / Position / ...)
                            if len(arxiv_ids) > 1 and '/' in claimed_title:
                                title_parts = [t.strip() for t in claimed_title.split('/')]
                                for idx, aid in enumerate(arxiv_ids):
                                    t = title_parts[idx] if idx < len(title_parts) else f"{claimed_title} (Part {idx+1})"
                                    if aid not in seen_ids:
                                        seen_ids.add(aid)
                                        papers.append({
                                            "arxiv_id": aid,
                                            "title": t,
                                            "section_num": sec_num,
                                            "section_title": header,
                                            "folder": folder_name,
                                            "notes": notes,
                                            "is_unverified": True
                                        })
                            else:
                                for aid in arxiv_ids:
                                    if aid not in seen_ids:
                                        seen_ids.add(aid)
                                        papers.append({
                                            "arxiv_id": aid,
                                            "title": claimed_title,
                                            "section_num": sec_num,
                                            "section_title": header,
                                            "folder": folder_name,
                                            "notes": notes,
                                            "is_unverified": True
                                        })
                        else:
                            # Paper with no ID
                            papers.append({
                                "arxiv_id": None,
                                "title": claimed_title,
                                "section_num": sec_num,
                                "section_title": header,
                                "folder": folder_name,
                                "notes": notes,
                                "is_unverified": True
                            })
        else:
            # Bullet list parser for Sections 1 to 6
            current_paper = None
            for line in lines:
                # Top level bullet must start with "- **" with NO leading indentation
                if line.startswith('- **'):
                    m_bullet = re.match(r'^- \*\*([^*]+)\*\*(.*?)$', line)
                    if m_bullet:
                        title = m_bullet.group(1).strip()
                        rest = m_bullet.group(2).strip()
                        
                        # Extract arxiv id
                        m_arxiv = re.search(r'arXiv:([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)', rest)
                        aid = m_arxiv.group(1).strip() if m_arxiv else None
                        
                        # Extract date and affiliation if available
                        parts = [p.strip() for p in re.split(r'\s+[—–-]{1,2}\s+', rest) if p.strip()]
                        date_val = ""
                        affiliation = ""
                        for p in parts:
                            if re.match(r'^202[0-9](?:-[0-9]{2})?', p):
                                date_val = p
                            elif p != f"arXiv:{aid}" and not p.startswith("arXiv:"):
                                affiliation = p
                                
                        current_paper = {
                            "arxiv_id": aid,
                            "title": title,
                            "section_num": sec_num,
                            "section_title": header,
                            "folder": folder_name,
                            "date": date_val,
                            "affiliation": affiliation,
                            "notes": "",
                            "is_unverified": False
                        }
                        if aid:
                            seen_ids.add(aid)
                        papers.append(current_paper)
                elif current_paper and (line.startswith('  - ') or line.startswith('    - ') or line.startswith('\t- ')):
                    # Sub-bullet note
                    note_text = line.strip().lstrip('- ').strip()
                    if current_paper["notes"]:
                        current_paper["notes"] += " " + note_text
                    else:
                        current_paper["notes"] = note_text

    return papers
