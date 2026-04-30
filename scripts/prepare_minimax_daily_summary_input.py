import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def load_profile_snapshot(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["user_profile_snapshot"]


def load_items(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "items" in data:
        return data["items"]
    if isinstance(data, list):
        return data
    raise ValueError("Unsupported input: expected report.json (with items) or a JSON array of items")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--items", required=True, help="report.json or items.json")
    parser.add_argument("--profile", default=str(Path("data") / "user_profile.v1.json"))
    parser.add_argument("--output", required=True, help="output JSON for minimax daily_summary input")
    args = parser.parse_args()

    snapshot = load_profile_snapshot(Path(args.profile))
    items = load_items(Path(args.items))
    payload = {
        "schema_version": "v1",
        "task": "daily_summary",
        "user_profile_snapshot": snapshot,
        "items": items,
    }
    write_json(Path(args.output), payload)
    print(f"Wrote minimax daily summary input: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

