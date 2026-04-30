import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


TZ_CN = timezone(timedelta(hours=8))


def iso_now_cn() -> str:
    return datetime.now(TZ_CN).isoformat(timespec="seconds")


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


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


KEYWORDS_STYLE = [
    ("原木", "原木"),
    ("奶油", "奶油风"),
    ("侘寂", "侘寂"),
    ("现代简约", "现代简约"),
    ("简约", "简约"),
    ("温暖", "温暖简约"),
]

KEYWORDS_SPACE = [
    ("儿童房", "儿童房"),
    ("客厅", "客厅"),
    ("功能角", "客厅"),
    ("厨房", "厨房"),
    ("餐边柜", "餐边柜"),
    ("餐厅", "餐厅"),
]

KEYWORDS_FEATURES = [
    ("功能角", "客厅功能角"),
    ("收纳", "收纳强"),
    ("低维护", "低维护"),
    ("耐住", "长期耐住"),
    ("高频做饭", "高频做饭友好"),
    ("动线", "动线清晰"),
    ("可成长", "可成长空间"),
    ("海外", "海外案例"),
    ("灵感", "灵感图"),
]

KEYWORDS_FAMILY = [
    ("二孩", "二孩家庭"),
    ("二胎", "二孩家庭"),
    ("长期自住", "长期自住"),
    ("自住", "长期自住"),
    ("三居", "三居"),
    ("3室", "三居"),
    ("有婴儿", "有婴儿"),
    ("婴儿", "有婴儿"),
    ("学龄", "学龄儿童"),
]


def extract_tags(text: str) -> Dict[str, List[str]]:
    text = text or ""

    def uniq(values: Iterable[str]) -> List[str]:
        seen = set()
        out: List[str] = []
        for v in values:
            if v in seen:
                continue
            seen.add(v)
            out.append(v)
        return out

    style = uniq([tag for k, tag in KEYWORDS_STYLE if k in text])
    space = uniq([tag for k, tag in KEYWORDS_SPACE if k in text])
    family = uniq([tag for k, tag in KEYWORDS_FAMILY if k in text])
    features = uniq([tag for k, tag in KEYWORDS_FEATURES if k in text])

    if "餐边柜" in text and "高频做饭友好" not in features:
        features.append("高频做饭友好")

    return {
        "style": style or ["现代简约"],
        "space": space or [],
        "family": family or ["长期自住"],
        "features": features or [],
    }


def compute_fit(item_tags: Dict[str, List[str]], profile: Dict[str, Any]) -> Tuple[float, str]:
    key_needs = set(profile.get("key_needs") or [])
    reasons: List[str] = []

    def hit(tag: str, reason: str) -> None:
        if tag in key_needs:
            reasons.append(reason)

    hit("儿童房规划", "命中儿童房规划")
    hit("客厅功能角", "命中客厅功能角")
    hit("厨房与餐边柜", "命中厨房与餐边柜")
    hit("全屋收纳", "命中全屋收纳")
    hit("低维护", "命中低维护偏好")
    hit("长期耐住", "命中长期耐住偏好")

    score = 0.55
    if "儿童房" in item_tags.get("space", []):
        score += 0.12
    if "厨房" in item_tags.get("space", []) or "餐边柜" in item_tags.get("space", []):
        score += 0.1
    if "客厅功能角" in item_tags.get("features", []):
        score += 0.08
    if "收纳强" in item_tags.get("features", []):
        score += 0.07
    if "二孩家庭" in item_tags.get("family", []):
        score += 0.06
    if "灵感图" in item_tags.get("features", []):
        score -= 0.08
    if "海外案例" in item_tags.get("features", []):
        score -= 0.06

    score = max(0.2, min(0.99, score))

    if not reasons:
        reasons = ["与当前阶段的核心关注点存在一定相关性，可作为补充样本参考。"]

    return (round(score, 2), "；".join(reasons[:3]))


def risk_notes_for(candidate: Dict[str, Any], tags: Dict[str, List[str]]) -> List[str]:
    text = f"{candidate.get('title','')} {candidate.get('text','')}"
    risks: List[str] = []
    if "开放格" in text:
        risks.append("开放格略多，杂物管理需要加强")
    if "奶油风" in tags.get("style", []) or "奶油" in text:
        risks.append("维护成本偏高，孩子使用场景要更谨慎")
    if "灵感图" in tags.get("features", []):
        risks.append("更偏灵感图，落地细节不足，需要结合户型尺寸再判断")
    if "海外案例" in tags.get("features", []):
        risks.append("海外生活习惯与国内差异大，需要本地化适配")
    if not risks:
        risks.append("关注尺寸、动线与收纳细节，避免只学外观")
    return risks[:3]


def why_selected_for(tags: Dict[str, List[str]]) -> str:
    hits: List[str] = []
    if "儿童房" in tags.get("space", []):
        hits.append("儿童房")
    if "客厅功能角" in tags.get("features", []):
        hits.append("客厅功能角")
    if "餐边柜" in tags.get("space", []) or "厨房" in tags.get("space", []):
        hits.append("厨房/餐边柜")
    if "收纳强" in tags.get("features", []):
        hits.append("收纳")
    return f"命中 { ' / '.join(hits) if hits else '当前阶段的核心关注点' }。"


def build_output(candidate: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
    title = (candidate.get("title") or "").strip()
    text = candidate.get("text") or ""
    tag_text = f"{title} {text}"

    tags = extract_tags(tag_text)
    fit_score, fit_reason = compute_fit(tags, profile)

    summary = (candidate.get("summary") or "").strip()
    if not summary:
        summary = "偏可落地的实景/方案样本，建议结合户型尺寸与动线细节一起判断。"

    why_selected = (candidate.get("why_selected") or "").strip()
    if not why_selected:
        why_selected = why_selected_for(tags)

    return {
        "summary": summary,
        "tags": tags,
        "fit_score": float(f"{fit_score:.2f}"),
        "fit_reason": fit_reason,
        "risk_notes": risk_notes_for(candidate, tags),
        "why_selected": why_selected,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="item_structuring inputs JSONL")
    parser.add_argument("--output", required=True, help="item_structuring outputs JSONL")
    parser.add_argument("--mode", choices=["heuristic", "minimax"], default="heuristic")
    args = parser.parse_args()

    rows = read_jsonl(Path(args.input))
    out_rows: List[Dict[str, Any]] = []

    for row in rows:
        candidate = row.get("candidate") or {}
        profile = row.get("user_profile_snapshot") or {}
        row["schema_version"] = "v1"
        row["task"] = "item_structuring"

        if args.mode == "minimax":
            raise RuntimeError("minimax mode is not wired yet; use --mode heuristic for now")

        row["output"] = build_output(candidate, profile)
        out_rows.append(row)

    write_jsonl(Path(args.output), out_rows)
    print(f"Wrote item_structuring outputs: {args.output} ({len(out_rows)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

