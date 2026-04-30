import argparse
import glob
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


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


def parse_time(value: Any) -> Tuple[int, str]:
    if not isinstance(value, str) or not value:
        return (0, "")
    v = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(v)
        return (int(dt.timestamp()), value)
    except Exception:
        return (0, value)


def norm_str(v: Any) -> str:
    return v.strip() if isinstance(v, str) else ""


def dedup_key(entry: Dict[str, Any]) -> Tuple[str, str, str, str, str]:
    t = norm_str(entry.get("time"))
    report_id = norm_str(entry.get("report_id"))
    item_id = norm_str(entry.get("item_id"))
    action = norm_str(entry.get("action"))
    source = norm_str(entry.get("source"))
    return (t, report_id, item_id, action, source)


def expand_inputs(inputs: List[str]) -> List[Path]:
    out: List[Path] = []
    for item in inputs:
        if any(ch in item for ch in ["*", "?", "["]):
            for m in glob.glob(item):
                out.append(Path(m))
        else:
            out.append(Path(item))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="+", required=True, help="actions jsonl paths (supports glob)")
    parser.add_argument("--output", required=True, help="merged actions jsonl")
    args = parser.parse_args()

    paths = expand_inputs(args.inputs)
    merged: List[Dict[str, Any]] = []
    for p in paths:
        merged.extend(read_jsonl(p))

    seen = set()
    deduped: List[Dict[str, Any]] = []
    for row in merged:
        if not isinstance(row, dict):
            continue
        key = dedup_key(row)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    deduped.sort(key=lambda r: (parse_time(r.get("time"))[0], parse_time(r.get("time"))[1]))
    write_jsonl(Path(args.output), deduped)
    print(f"Wrote merged actions: {args.output} ({len(deduped)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

