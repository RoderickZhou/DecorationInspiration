import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


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


def load_profile_snapshot(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["user_profile_snapshot"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", required=True, help="candidates JSONL")
    parser.add_argument("--profile", default=str(Path("data") / "user_profile.v1.json"))
    parser.add_argument("--output", required=True, help="output JSONL for minimax item_structuring inputs")
    args = parser.parse_args()

    snapshot = load_profile_snapshot(Path(args.profile))
    candidates = read_jsonl(Path(args.candidates))
    tasks: List[Dict[str, Any]] = []
    for cand in candidates:
        tasks.append(
            {
                "schema_version": "v1",
                "task": "item_structuring",
                "user_profile_snapshot": snapshot,
                "candidate": cand,
            }
        )

    write_jsonl(Path(args.output), tasks)
    print(f"Wrote minimax inputs: {args.output} ({len(tasks)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

