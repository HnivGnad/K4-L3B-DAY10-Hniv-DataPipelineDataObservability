from __future__ import annotations

import json
import logging
import re
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode

from core.config import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_text(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """parse Crossref payload thanh list PaperRecord."""
    records = []
    items = payload.get("message", {}).get("items", [])
    
    for item in items:
        paper_id = item.get("DOI", "").strip()
        title_list = item.get("title", [])
        title = _clean_text(title_list[0]) if title_list else ""
        
        if not paper_id or not title:
            continue
            
        summary = _clean_text(item.get("abstract", ""))
        
        authors = []
        for author in item.get("author", []):
            given = author.get("given", "")
            family = author.get("family", "")
            if given or family:
                authors.append(f"{given} {family}".strip())
                
        categories = item.get("subject", [])
        primary_category = categories[0] if categories else ""
        
        published = ""
        pub_date_parts = item.get("published", {}).get("date-parts", [])
        if pub_date_parts and pub_date_parts[0]:
            parts = pub_date_parts[0]
            if len(parts) >= 1:
                year = parts[0]
                month = parts[1] if len(parts) >= 2 else 1
                day = parts[2] if len(parts) >= 3 else 1
                published = f"{year}-{month:02d}-{day:02d}"
                
        updated = published
        
        abs_url = item.get("URL", "")
        
        pdf_url = ""
        for link in item.get("link", []):
            if link.get("content-type") == "application/pdf":
                pdf_url = link.get("URL", "")
                break
                
        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=""
            )
        )
        
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """goi source API, luu raw response, parse thanh records."""
    base_url = "https://api.crossref.org/works"
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    url = f"{base_url}?{urlencode(params)}"
    
    payload = None
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "DataPipelineLab/1.0 (mailto:student@example.com)"})
            with urllib.request.urlopen(req, timeout=10) as response:
                payload = json.loads(response.read().decode('utf-8'))
                break
        except HTTPError as e:
            if e.code in (429, 503):
                time.sleep(2 ** attempt)
                continue
            else:
                logger.warning(f"HTTPError {e.code} fetching from API.")
                break
        except Exception as e:
            logger.warning(f"Error fetching from API: {e}")
            break
            
    if payload:
        settings.paths.raw_api_response.parent.mkdir(parents=True, exist_ok=True)
        with open(settings.paths.raw_api_response, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    else:
        if settings.paths.raw_api_response.exists():
            with open(settings.paths.raw_api_response, "r", encoding="utf-8") as f:
                payload = json.load(f)
        else:
            return []
            
    records = parse_crossref_payload(payload)
    
    settings.paths.raw_records_json.parent.mkdir(parents=True, exist_ok=True)
    records_dict = [asdict(r) for r in records]
    with open(settings.paths.raw_records_json, "w", encoding="utf-8") as f:
        json.dump(records_dict, f, ensure_ascii=False, indent=2)
        
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """doc JSON snapshot va map thanh `PaperRecord`."""
    if not path.exists():
        return []
        
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    records = []
    for item in data:
        records.append(PaperRecord(**item))
        
    return records
