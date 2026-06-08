import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _schema_validate import (  # noqa: E402
    SchemaValidationError,
    load_schema,
    subschema,
    validate_or_raise,
)
from minimax_client import (  # noqa: E402
    MinimaxClient,
    MinimaxConfigError,
    MinimaxError,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DS_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "minimax_daily_summary.schema.json"
DS_PROMPT_PATH = PROJECT_ROOT / "prompts" / "minimax_daily_summary.md"
DEFAULT_CACHE_DIR = PROJECT_ROOT / "data" / "cache" / "daily_summary"


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("input must be a JSON object")
    return data


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def top_tags(items: List[Dict[str, Any]], limit: int = 6) -> List[str]:
    counts: Dict[str, int] = {}
    for it in items:
        tags = it.get("tags") or {}
        for group in ("style", "space", "family", "features"):
            for v in tags.get(group) or []:
                counts[v] = counts.get(v, 0) + 1
    return [k for k, _ in sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:limit]]


def pick_today_focus(items: List[Dict[str, Any]]) -> List[str]:
    tags = top_tags(items, limit=12)
    focus: List[str] = []
    if "儿童房" in tags:
        focus.append("儿童房短期先一睡一玩，是否更适合当前孩子年龄差")
    if "客厅功能角" in tags or "客厅" in tags:
        focus.append("客厅功能角如何嵌入公共空间，同时不影响收纳与动线")
    if "厨房" in tags or "餐边柜" in tags:
        focus.append("厨房与餐边柜如何同时提升做饭效率与收纳")
    if not focus:
        focus = [
            "今天内容偏向实景与可落地方案，优先把它们转成可执行的判断规则",
            "把喜欢与不喜欢都记录下来，让明天的推荐更准",
            "观察同一主题下的差异点，建立自己的审美边界",
        ]
    return focus[:3]


def summarize(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    tags = top_tags(items, limit=8)
    headline = "今天推荐更偏向实景落地与高匹配度案例，帮助你把“看图”转成可判断的方向。"
    if tags:
        headline = f"今天推荐更偏向 {tags[0]} / {tags[1] if len(tags) > 1 else tags[0]} 等方向的可落地案例。"

    highlights: List[str] = []
    if "二孩家庭" in tags:
        highlights.append("二孩家庭视角的案例更多，便于参考过渡型儿童区与成长路径")
    if "客厅功能角" in tags:
        highlights.append("客厅功能角更常与整墙收纳、边角书桌或餐边柜延伸结合出现")
    if "高频做饭友好" in tags or "餐边柜" in tags:
        highlights.append("高频做饭相关内容更强调电器整合、备餐台面与餐边柜动线")
    if not highlights:
        highlights = [
            "优先看实景落地案例，不让概念图主导判断",
            "优先看收纳与动线细节，避免只学外观",
            "继续围绕儿童房、客厅功能角与厨房收纳三条主线积累样本",
        ]

    question = "对于你家当前阶段，儿童房短期先一睡一玩，是否比立刻彻底分房更实用？"
    if "厨房" in tags or "餐边柜" in tags:
        question = "如果每天高频做饭，你更想先把厨房动线优化，还是先确定餐边柜电器整合？"

    fit_direction = [
        "优先看温暖简约与低维护风格，不急着追求高维护网红感",
        "优先看实景落地案例，用“可抄作业”替代概念图",
        "继续重点观察儿童房、客厅功能角与厨房收纳三个主题",
    ]

    return {
        "headline": headline,
        "highlights": highlights[:3],
        "question_of_the_day": question,
        "fit_direction": fit_direction,
    }


def heuristic_output(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "today_focus": pick_today_focus(items),
        "summary": summarize(items),
        "daily_digest": {
            "estimated_read_minutes": int(math.ceil(max(1, len(items)) / 5)),
            "recommended_browse_order": ["儿童房", "客厅功能角", "厨房与餐边柜", "风格拓展"],
            "top_tags": top_tags(items, limit=6),
        },
    }


def _slim_item(item: Dict[str, Any]) -> Dict[str, Any]:
    keep = ("id", "platform", "platform_label", "title", "tags", "fit_score",
            "fit_reason", "summary", "risk_notes", "why_selected")
    return {k: item[k] for k in keep if k in item}


def _cache_key(model: str, prompt: str, payload: Dict[str, Any]) -> str:
    fingerprint = json.dumps(
        {"model": model, "prompt": prompt, "payload": payload},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()


def _cache_read(cache_dir: Optional[Path], key: str) -> Optional[Dict[str, Any]]:
    if not cache_dir:
        return None
    path = cache_dir / f"{key}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _cache_write(cache_dir: Optional[Path], key: str, output: Dict[str, Any]) -> None:
    if not cache_dir:
        return
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{key}.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _call_minimax(
    client: MinimaxClient,
    prompt: str,
    profile: Dict[str, Any],
    slim_items: List[Dict[str, Any]],
    output_schema: Dict[str, Any],
    schema_base: Path,
) -> Dict[str, Any]:
    user_payload = json.dumps(
        {"user_profile_snapshot": profile, "items": slim_items},
        ensure_ascii=False,
    )
    resp = client.chat_json(prompt, user_payload)
    output = resp.get("output") if isinstance(resp, dict) and "output" in resp else resp
    if not isinstance(output, dict):
        raise MinimaxError(f"unexpected response shape: {str(resp)[:200]}")
    validate_or_raise(output, output_schema, schema_base)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="daily_summary input JSON")
    parser.add_argument("--output", required=True, help="daily_summary output JSON")
    parser.add_argument("--mode", choices=["heuristic", "minimax"], default="heuristic")
    parser.add_argument(
        "--cache-dir",
        default=str(DEFAULT_CACHE_DIR),
        help="cache directory; pass empty string '' to disable",
    )
    parser.add_argument("--force-refresh", action="store_true", help="ignore existing cache hits")
    parser.add_argument("--fail-fast", action="store_true", help="surface errors instead of falling back")
    args = parser.parse_args()

    payload = read_json(Path(args.input))
    items = payload.get("items") or []
    if not isinstance(items, list) or not items:
        raise ValueError("items must be a non-empty array")
    profile = payload.get("user_profile_snapshot") or {}

    payload["schema_version"] = "v1"
    payload["task"] = "daily_summary"

    mode = args.mode
    client: Optional[MinimaxClient] = None
    if mode == "minimax":
        try:
            client = MinimaxClient()
        except MinimaxConfigError as e:
            print(f"[warn] {e}; falling back to heuristic mode", file=sys.stderr)
            mode = "heuristic"

    output: Dict[str, Any]
    source = "heuristic"
    if mode == "heuristic":
        output = heuristic_output(items)
    else:
        assert client is not None
        prompt = DS_PROMPT_PATH.read_text(encoding="utf-8")
        schema = load_schema(DS_SCHEMA_PATH)
        output_schema = subschema(schema, "/properties/output")
        slim = [_slim_item(it) for it in items]
        cache_dir = Path(args.cache_dir) if args.cache_dir else None
        key = _cache_key(client.model, prompt, {"user_profile_snapshot": profile, "items": slim})
        if args.force_refresh and cache_dir:
            (cache_dir / f"{key}.json").unlink(missing_ok=True)
        cached = _cache_read(cache_dir, key)
        if cached is not None:
            output = cached
            source = "cache"
        else:
            try:
                output = _call_minimax(client, prompt, profile, slim, output_schema, DS_SCHEMA_PATH)
                _cache_write(cache_dir, key, output)
                source = "minimax"
            except (MinimaxError, SchemaValidationError) as e:
                if args.fail_fast:
                    raise
                print(f"[warn] daily_summary: fallback to heuristic ({str(e)[:200]})", file=sys.stderr)
                output = heuristic_output(items)
                source = "heuristic_fallback"
                payload["_fallback_reason"] = str(e)

    payload["output"] = output
    payload["_source"] = source

    write_json(Path(args.output), payload)
    print(f"Wrote daily_summary output: {args.output} (source={source})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
