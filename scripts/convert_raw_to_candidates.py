import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def pick_cover_url(raw: Dict[str, Any]) -> str:
    images = raw.get("images") or []
    for img in images:
        url = (img.get("url") or "").strip()
        if url:
            return url
    return ""


def pick_image_urls(raw: Dict[str, Any]) -> List[str]:
    images = raw.get("images") or []
    out: List[str] = []
    for img in images:
        url = (img.get("url") or "").strip()
        if url:
            out.append(url)
    return out


def safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def to_candidate(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    platform = (raw.get("platform") or "").strip()
    source_url = (raw.get("canonical_url") or "").strip()
    title = (raw.get("title") or "").strip()

    if not platform or not source_url or not title:
        return None

    cover_url = pick_cover_url(raw)
    if not cover_url:
        return None

    metrics = raw.get("metrics") or {}
    engagement = {
        "likes": safe_int(metrics.get("likes")),
        "favorites": safe_int(metrics.get("favorites")),
        "comments": safe_int(metrics.get("comments")),
    }

    return {
        "platform": platform,
        "title": title,
        "source_url": source_url,
        "cover_url": cover_url,
        "image_urls": pick_image_urls(raw),
        "author": (raw.get("author") or "").strip(),
        "published_at": (raw.get("published_at") or "").strip(),
        "engagement": engagement,
        "text": (raw.get("content_text") or "").strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="raw collector JSONL")
    parser.add_argument("--output", required=True, help="candidates JSONL")
    args = parser.parse_args()

    raw_rows = read_jsonl(Path(args.input))
    candidates: List[Dict[str, Any]] = []
    for row in raw_rows:
        cand = to_candidate(row)
        if cand:
            candidates.append(cand)

    write_jsonl(Path(args.output), candidates)
    print(f"Wrote candidates: {args.output} ({len(candidates)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

