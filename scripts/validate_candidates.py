import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        raise FileNotFoundError(str(path))
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def is_non_empty_str(v: Any) -> bool:
    return isinstance(v, str) and v.strip() != ""


def safe_int(v: Any) -> int:
    try:
        return int(v)
    except Exception:
        return 0


def validate_row(row: Dict[str, Any], idx: int) -> List[str]:
    errors: List[str] = []
    required = ["platform", "title", "source_url", "cover_url"]
    for key in required:
        if not is_non_empty_str(row.get(key)):
            errors.append(f"line {idx}: missing/empty {key}")

    image_urls = row.get("image_urls")
    if image_urls is not None and not isinstance(image_urls, list):
        errors.append(f"line {idx}: image_urls must be array")

    engagement = row.get("engagement")
    if engagement is not None and not isinstance(engagement, dict):
        errors.append(f"line {idx}: engagement must be object")
    if isinstance(engagement, dict):
        for k in ("likes", "favorites", "comments"):
            if k in engagement and safe_int(engagement.get(k)) < 0:
                errors.append(f"line {idx}: engagement.{k} must be >= 0")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="candidates JSONL")
    args = parser.parse_args()

    rows = read_jsonl(Path(args.input))
    all_errors: List[str] = []
    urls: Dict[str, int] = {}
    platform_counts: Dict[str, int] = {}

    for i, row in enumerate(rows, start=1):
        all_errors.extend(validate_row(row, i))
        url = (row.get("source_url") or "").strip()
        if url:
            urls[url] = urls.get(url, 0) + 1
        platform = (row.get("platform") or "").strip() or "unknown"
        platform_counts[platform] = platform_counts.get(platform, 0) + 1

    dup_urls = [u for u, c in urls.items() if c > 1]
    if dup_urls:
        all_errors.append(f"duplicate source_url count: {len(dup_urls)}")

    if all_errors:
        for e in all_errors:
            print(e)
        raise SystemExit(1)

    print(f"OK candidates: {len(rows)} lines")
    for k, v in sorted(platform_counts.items(), key=lambda x: (-x[1], x[0])):
        print(f"- {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

