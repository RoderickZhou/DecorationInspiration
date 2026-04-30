import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="daily_summary input JSON")
    parser.add_argument("--output", required=True, help="daily_summary output JSON")
    parser.add_argument("--mode", choices=["heuristic", "minimax"], default="heuristic")
    args = parser.parse_args()

    payload = read_json(Path(args.input))
    items = payload.get("items") or []
    if not isinstance(items, list) or not items:
        raise ValueError("items must be a non-empty array")

    payload["schema_version"] = "v1"
    payload["task"] = "daily_summary"

    if args.mode == "minimax":
        raise RuntimeError("minimax mode is not wired yet; use --mode heuristic for now")

    output = {
        "today_focus": pick_today_focus(items),
        "summary": summarize(items),
        "daily_digest": {
            "estimated_read_minutes": int(math.ceil(max(1, len(items)) / 5)),
            "recommended_browse_order": ["儿童房", "客厅功能角", "厨房与餐边柜", "风格拓展"],
            "top_tags": top_tags(items, limit=6),
        },
    }
    payload["output"] = output

    write_json(Path(args.output), payload)
    print(f"Wrote daily_summary output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

