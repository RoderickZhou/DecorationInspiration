import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("report must be a JSON object")
    return data


def is_non_empty_str(v: Any) -> bool:
    return isinstance(v, str) and v.strip() != ""


def ensure(cond: bool, msg: str, errors: List[str]) -> None:
    if not cond:
        errors.append(msg)


def validate_report(report: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for k in ("report_date", "generated_at", "report_id", "user_profile_version"):
        ensure(is_non_empty_str(report.get(k)), f"missing/empty {k}", errors)

    ensure(isinstance(report.get("user_profile_snapshot"), dict), "user_profile_snapshot must be object", errors)
    ensure(isinstance(report.get("source_stats"), dict), "source_stats must be object", errors)
    ensure(isinstance(report.get("items"), list) and len(report["items"]) > 0, "items must be non-empty array", errors)

    source_stats = report.get("source_stats") or {}
    if isinstance(source_stats, dict):
        for k in ("raw_items", "deduplicated_items", "filtered_items", "recommended_items"):
            ensure(isinstance(source_stats.get(k), int) and source_stats.get(k) >= 0, f"source_stats.{k} must be >=0 int", errors)
        if isinstance(source_stats.get("recommended_items"), int) and isinstance(report.get("items"), list):
            ensure(source_stats["recommended_items"] == len(report["items"]), "source_stats.recommended_items must equal len(items)", errors)

    items = report.get("items") or []
    display_priorities: Set[int] = set()
    ids: Set[str] = set()

    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            errors.append(f"items[{idx}] must be object")
            continue
        for k in ("id", "platform", "title", "source_url", "cover_url", "summary", "fit_reason", "why_selected"):
            ensure(is_non_empty_str(item.get(k)), f"items[{idx}].{k} missing/empty", errors)

        item_id = item.get("id")
        if isinstance(item_id, str):
            ensure(item_id not in ids, f"duplicate item id: {item_id}", errors)
            ids.add(item_id)

        fit_score = item.get("fit_score")
        ensure(isinstance(fit_score, (int, float)) and 0 <= float(fit_score) <= 1, f"items[{idx}].fit_score must be 0..1", errors)

        risk_notes = item.get("risk_notes")
        ensure(isinstance(risk_notes, list) and len(risk_notes) >= 1, f"items[{idx}].risk_notes must be non-empty array", errors)

        tags = item.get("tags")
        ensure(isinstance(tags, dict), f"items[{idx}].tags must be object", errors)
        if isinstance(tags, dict):
            for group in ("style", "space", "family", "features"):
                ensure(group in tags and isinstance(tags.get(group), list), f"items[{idx}].tags.{group} must be array", errors)

        dp = item.get("display_priority")
        ensure(isinstance(dp, int) and dp >= 1, f"items[{idx}].display_priority must be int >=1", errors)
        if isinstance(dp, int):
            ensure(dp not in display_priorities, f"duplicate display_priority: {dp}", errors)
            display_priorities.add(dp)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="report.json")
    args = parser.parse_args()

    report = read_json(Path(args.input))
    errors = validate_report(report)
    if errors:
        for e in errors:
            print(e)
        raise SystemExit(1)
    print("OK report")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

