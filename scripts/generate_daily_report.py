import argparse
import json
import math
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


TZ_CN = timezone(timedelta(hours=8))


def iso_now_cn() -> str:
    return datetime.now(TZ_CN).isoformat(timespec="seconds")


def parse_date(value: Optional[str]) -> str:
    if value:
        return value
    return date.today().isoformat()


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


def read_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def normalize_platform_label(platform: str) -> str:
    labels = {
        "xiaohongshu": "小红书",
        "haohaozhu": "好好住",
        "yidoutang": "一兜糖",
        "pinterest": "Pinterest",
        "huaban": "花瓣",
        "houzz": "Houzz",
    }
    return labels.get(platform, platform)


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
        out = []
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


@dataclass
class UserProfile:
    version: str
    snapshot: Dict[str, Any]

    @staticmethod
    def load(path: Path) -> "UserProfile":
        data = json.loads(path.read_text(encoding="utf-8"))
        return UserProfile(version=data.get("user_profile_version", "v1"), snapshot=data["user_profile_snapshot"])


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


def risk_notes_for(item: Dict[str, Any], tags: Dict[str, List[str]]) -> List[str]:
    text = f"{item.get('title','')} {item.get('text','')}"
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


def pick_today_focus(items: List[Dict[str, Any]]) -> List[str]:
    space_counts: Dict[str, int] = {}
    feature_counts: Dict[str, int] = {}
    for it in items:
        tags = it.get("tags") or {}
        for v in tags.get("space") or []:
            space_counts[v] = space_counts.get(v, 0) + 1
        for v in tags.get("features") or []:
            feature_counts[v] = feature_counts.get(v, 0) + 1

    top_space = sorted(space_counts.items(), key=lambda x: (-x[1], x[0]))[:3]
    top_feat = sorted(feature_counts.items(), key=lambda x: (-x[1], x[0]))[:3]

    focus: List[str] = []
    if any(name == "儿童房" for name, _ in top_space):
        focus.append("儿童房短期先一睡一玩，是否更适合当前孩子年龄差")
    if any(name == "客厅" for name, _ in top_space) or any(name == "客厅功能角" for name, _ in top_feat):
        focus.append("客厅功能角如何嵌入公共空间，同时不影响收纳与动线")
    if any(name in ("厨房", "餐边柜") for name, _ in top_space):
        focus.append("厨房与餐边柜如何同时提升做饭效率与收纳")

    if not focus:
        focus = [
            "今天内容偏向实景与可落地方案，优先把它们转成可执行的判断规则",
            "把喜欢与不喜欢都记录下来，让明天的推荐更准",
            "观察同一主题下的差异点，建立自己的审美边界",
        ]

    return focus[:3]


def top_tags(items: List[Dict[str, Any]], limit: int = 5) -> List[str]:
    counts: Dict[str, int] = {}
    for it in items:
        tags = it.get("tags") or {}
        for group in ("style", "space", "family", "features"):
            for v in tags.get(group) or []:
                counts[v] = counts.get(v, 0) + 1
    return [k for k, _ in sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:limit]]


def summarize(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    tags = top_tags(items, limit=8)
    headline = "今天推荐更偏向实景落地与高匹配度案例，帮助你把“看图”转成可判断的方向。"
    if tags:
        headline = f"今天推荐更偏向 {tags[0]} / {tags[1] if len(tags) > 1 else tags[0]} 等方向的可落地案例。"

    highlights = []
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


def breakdown_stats(raw: List[Dict[str, Any]], items: List[Dict[str, Any]], filtered_count: int) -> Dict[str, Any]:
    by_source: Dict[str, Dict[str, int]] = {}
    for it in raw:
        platform = it.get("platform") or "unknown"
        by_source.setdefault(platform, {"platform": platform, "raw_items": 0, "recommended_items": 0})
        by_source[platform]["raw_items"] += 1

    for it in items:
        platform = it.get("platform") or "unknown"
        by_source.setdefault(platform, {"platform": platform, "raw_items": 0, "recommended_items": 0})
        by_source[platform]["recommended_items"] += 1

    dedup = len({(it.get("source_url") or "").strip() for it in raw if (it.get("source_url") or "").strip()})

    return {
        "raw_items": len(raw),
        "deduplicated_items": dedup,
        "filtered_items": filtered_count,
        "recommended_items": len(items),
        "source_breakdown": sorted(by_source.values(), key=lambda x: (-x["raw_items"], x["platform"])),
    }


def load_actions(path: Optional[Path]) -> List[Dict[str, Any]]:
    if not path:
        return []
    if not path.exists():
        return []
    return read_jsonl(path)


def feedback_summary(actions: List[Dict[str, Any]], items: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_id = {it["id"]: it for it in items}
    pos: Dict[str, int] = {}
    neg: Dict[str, int] = {}

    for entry in actions:
        action = entry.get("action")
        item_id = entry.get("item_id")
        item = by_id.get(item_id)
        if not item:
            continue
        tags = item.get("tags") or {}
        pool = []
        pool.extend(tags.get("style") or [])
        pool.extend(tags.get("space") or [])
        pool.extend(tags.get("family") or [])
        pool.extend(tags.get("features") or [])
        if action in ("like", "favorite"):
            for t in pool:
                pos[t] = pos.get(t, 0) + 1
        if action == "dislike":
            for t in pool:
                neg[t] = neg.get(t, 0) + 1

    def top(d: Dict[str, int]) -> List[str]:
        return [k for k, _ in sorted(d.items(), key=lambda x: (-x[1], x[0]))[:5]]

    if not pos and not neg:
        tags = top_tags(items, limit=8)
        return {
            "recent_positive_patterns": tags[:5],
            "recent_negative_patterns": ["纯概念图", "过度装饰", "高维护"],
        }

    return {
        "recent_positive_patterns": top(pos),
        "recent_negative_patterns": top(neg),
    }


def build_item(item: Dict[str, Any], idx: int, report_day: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    platform = (item.get("platform") or "unknown").strip()
    title = (item.get("title") or "").strip()
    source_url = (item.get("source_url") or "").strip()
    cover_url = (item.get("cover_url") or "").strip()
    image_urls = item.get("image_urls") or []
    author = (item.get("author") or "").strip() or "unknown"
    published_at = (item.get("published_at") or "").strip() or iso_now_cn()

    text = item.get("text") or ""
    tag_text = f"{title} {text}"
    tags = extract_tags(tag_text)
    fit_score, fit_reason = compute_fit(tags, profile)

    ymd = report_day.replace("-", "")
    item_id = item.get("id") or f"{platform}_{ymd}_{idx:03d}"

    engagement = item.get("engagement") or {}
    engagement_payload = {
        "likes": safe_int(engagement.get("likes")),
        "favorites": safe_int(engagement.get("favorites")),
        "comments": safe_int(engagement.get("comments")),
    }

    summary = (item.get("summary") or "").strip()
    if not summary:
        summary = "偏可落地的实景/方案样本，建议结合户型尺寸与动线细节一起判断。"

    why_selected = (item.get("why_selected") or "").strip()
    if not why_selected:
        hits = []
        if "儿童房" in tags.get("space", []):
            hits.append("儿童房")
        if "客厅功能角" in tags.get("features", []):
            hits.append("客厅功能角")
        if "餐边柜" in tags.get("space", []) or "厨房" in tags.get("space", []):
            hits.append("厨房/餐边柜")
        if "收纳强" in tags.get("features", []):
            hits.append("收纳")
        why_selected = f"命中 { ' / '.join(hits) if hits else '当前阶段的核心关注点' }。"

    return {
        "id": item_id,
        "platform": platform,
        "platform_label": normalize_platform_label(platform),
        "title": title,
        "source_url": source_url,
        "cover_url": cover_url,
        "image_urls": image_urls,
        "author": author,
        "published_at": published_at,
        "engagement": engagement_payload,
        "tags": tags,
        "summary": summary,
        "fit_score": fit_score,
        "fit_reason": fit_reason,
        "risk_notes": risk_notes_for(item, tags),
        "why_selected": why_selected,
        "display_priority": idx,
    }


def load_structured_items(path: Optional[Path]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    if not path:
        return {}
    rows = read_jsonl(path)
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("task") != "item_structuring":
            continue
        candidate = row.get("candidate") or {}
        output = row.get("output") or {}
        if not isinstance(candidate, dict) or not isinstance(output, dict):
            continue
        platform = (candidate.get("platform") or "").strip()
        source_url = (candidate.get("source_url") or "").strip()
        if not platform or not source_url:
            continue
        out[(platform, source_url)] = output
    return out


def apply_structured_output(item_payload: Dict[str, Any], structured_output: Dict[str, Any]) -> None:
    for key in ("summary", "tags", "fit_score", "fit_reason", "risk_notes", "why_selected"):
        if key in structured_output:
            item_payload[key] = structured_output[key]


def load_daily_summary(path: Optional[Path]) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    payload = read_json(path)
    if not isinstance(payload, dict):
        return None
    if payload.get("task") != "daily_summary":
        return None
    output = payload.get("output")
    if not isinstance(output, dict):
        return None
    return output


def select_recommended(raw: List[Dict[str, Any]], profile: Dict[str, Any], report_day: str, limit: int) -> Tuple[List[Dict[str, Any]], int]:
    deduped: List[Dict[str, Any]] = []
    seen_urls: set = set()

    for row in raw:
        url = (row.get("source_url") or "").strip()
        if not url:
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(row)

    filtered: List[Dict[str, Any]] = []
    for row in deduped:
        if not (row.get("title") and row.get("cover_url")):
            continue
        filtered.append(row)

    built: List[Dict[str, Any]] = [build_item(row, i + 1, report_day, profile) for i, row in enumerate(filtered)]
    built.sort(key=lambda x: (-x["fit_score"], x["display_priority"]))

    selected = built[: max(1, min(limit, len(built)))]
    for i, it in enumerate(selected, start=1):
        it["display_priority"] = i

    return selected, len(filtered)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", dest="report_date", default=None)
    parser.add_argument("--input", required=True, help="JSONL raw candidates file")
    parser.add_argument("--output", required=True, help="Output report.json path")
    parser.add_argument("--profile", default=str(Path("data") / "user_profile.v1.json"))
    parser.add_argument("--actions", default=None, help="Optional actions.jsonl to compute feedback summary")
    parser.add_argument("--limit", type=int, default=14)
    parser.add_argument("--structured-items", default=None, help="Optional item_structuring outputs JSONL")
    parser.add_argument("--daily-summary", default=None, help="Optional daily_summary output JSON")
    args = parser.parse_args()

    report_day = parse_date(args.report_date)
    profile = UserProfile.load(Path(args.profile))

    raw = read_jsonl(Path(args.input))
    items, filtered_count = select_recommended(raw, profile.snapshot, report_day, limit=args.limit)

    structured = load_structured_items(Path(args.structured_items) if args.structured_items else None)
    if structured:
        for it in items:
            key = (it.get("platform") or "", it.get("source_url") or "")
            output = structured.get(key)
            if output:
                apply_structured_output(it, output)

    report_id = f"daily_report_{report_day.replace('-', '_')}"
    daily_summary_output = load_daily_summary(Path(args.daily_summary) if args.daily_summary else None)
    report_payload = {
        "report_date": report_day,
        "generated_at": iso_now_cn(),
        "report_id": report_id,
        "user_profile_version": profile.version,
        "user_profile_snapshot": profile.snapshot,
        "source_stats": breakdown_stats(raw, items, filtered_count),
        "today_focus": (daily_summary_output or {}).get("today_focus") or pick_today_focus(items),
        "summary": (daily_summary_output or {}).get("summary") or summarize(items),
        "daily_digest": (daily_summary_output or {}).get("daily_digest")
        or {
            "estimated_read_minutes": int(math.ceil(max(1, len(items)) / 5)),
            "recommended_browse_order": ["儿童房", "客厅功能角", "厨房与餐边柜", "风格拓展"],
            "top_tags": top_tags(items, limit=5),
        },
        "items": items,
        "feedback_summary": feedback_summary(load_actions(Path(args.actions) if args.actions else None), items),
    }

    write_json(Path(args.output), report_payload)
    print(f"Wrote report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

