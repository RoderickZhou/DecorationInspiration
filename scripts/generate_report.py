from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


STYLE_KEYWORDS = {
    "原木": ["原木"],
    "现代简约": ["现代简约"],
    "温暖简约": ["温暖简约"],
    "奶油风": ["奶油风"],
    "简约": ["简约"],
}

SPACE_KEYWORDS = {
    "儿童房": ["儿童房"],
    "客厅": ["客厅"],
    "厨房": ["厨房"],
    "餐边柜": ["餐边柜"],
}

FAMILY_KEYWORDS = {
    "二孩家庭": ["二孩", "二胎"],
    "长期自住": ["长期自住", "长期使用"],
    "有婴儿": ["婴儿"],
    "学龄儿童": ["7岁", "学习区"],
    "三居": ["三居", "3室"],
}

FEATURE_KEYWORDS = {
    "客厅功能角": ["功能角", "书桌", "工作台"],
    "收纳强": ["整墙柜", "收纳"],
    "低维护": ["低维护", "易清洁"],
    "高频做饭友好": ["高频做饭", "备餐", "电器整合"],
    "儿童活动区": ["活动区"],
    "可成长空间": ["过渡", "后续", "阶段"],
    "整墙收纳": ["整墙柜", "整墙收纳"],
    "灵感图": ["灵感图", "拼贴"],
    "高维护": ["高维护", "开放格"],
}


def infer_tags(text: str) -> dict:
    def match(mapping: dict[str, list[str]]) -> list[str]:
        hits = []
        for label, keywords in mapping.items():
            if any(keyword in text for keyword in keywords):
                hits.append(label)
        return hits

    return {
        "style": match(STYLE_KEYWORDS),
        "space": match(SPACE_KEYWORDS),
        "family": match(FAMILY_KEYWORDS),
        "features": match(FEATURE_KEYWORDS),
    }


def score_item(tags: dict, engagement: dict, text: str) -> tuple[float, list[str], list[str], str]:
    score = 0.45
    reasons = []
    risks = []

    if "二孩家庭" in tags["family"]:
        score += 0.14
        reasons.append("直接命中二孩家庭")
    if "儿童房" in tags["space"]:
        score += 0.12
        reasons.append("覆盖儿童房主题")
    if "客厅功能角" in tags["features"]:
        score += 0.1
        reasons.append("包含客厅功能角")
    if "高频做饭友好" in tags["features"] or "厨房" in tags["space"]:
        score += 0.1
        reasons.append("贴近高频做饭需求")
    if "长期自住" in tags["family"]:
        score += 0.07
        reasons.append("偏长期自住")
    if "低维护" in tags["features"]:
        score += 0.05
        reasons.append("维护成本可控")
    if "灵感图" in tags["features"]:
        score -= 0.06
        risks.append("偏灵感图，落地细节不足")
    if "高维护" in tags["features"]:
        score -= 0.08
        risks.append("高维护元素偏多")
    if "海外案例" in text:
        score -= 0.03
        risks.append("需要结合国内尺寸与供应链再判断")

    likes = engagement.get("likes", 0)
    favorites = engagement.get("favorites", 0)
    score += min((likes + favorites) / 10000, 0.08)

    score = max(0.4, min(score, 0.95))
    summary = build_summary(tags, text)
    return round(score, 2), reasons, risks, summary


def build_summary(tags: dict, text: str) -> str:
    fragments = []
    if tags["family"]:
        fragments.append("适合家庭画像接近的长期自住案例")
    if "儿童房" in tags["space"]:
        fragments.append("重点解决儿童房阶段规划")
    if "客厅功能角" in tags["features"]:
        fragments.append("对客厅功能角有直接参考")
    if "厨房" in tags["space"] or "餐边柜" in tags["space"]:
        fragments.append("厨房与餐边柜思路较实用")
    if not fragments:
        fragments.append("更适合作为审美和布局灵感补充")
    return "，".join(fragments) + "。"


def build_fit_reason(reasons: list[str]) -> str:
    if not reasons:
        return "与目标家庭画像有一定相关性，但仍需结合实际户型进一步判断。"
    return "、".join(reasons[:3]) + "，因此推荐进入日报。"


def build_priority(score: float, index: int) -> int:
    base = int((1 - score) * 100)
    return base + index + 1


def build_report(raw_data: dict) -> dict:
    report_date = datetime.now(timezone.utc).astimezone().date().isoformat()
    source_breakdown = defaultdict(lambda: {"raw_items": 0, "recommended_items": 0})
    processed_items = []
    tag_counter = Counter()

    for index, item in enumerate(raw_data["items"]):
        text = " ".join(
            [
                item.get("title", ""),
                item.get("content_text", ""),
                " ".join(item.get("detected_keywords", [])),
            ]
        )
        tags = infer_tags(text)
        score, reasons, risks, summary = score_item(tags, item.get("engagement", {}), text)
        if not risks:
            risks = ["暂无明显风险提示"]

        source_breakdown[item["platform"]]["raw_items"] += 1
        if score >= 0.65:
            source_breakdown[item["platform"]]["recommended_items"] += 1

        all_tags = tags["style"] + tags["space"] + tags["family"] + tags["features"]
        tag_counter.update(all_tags)

        processed_items.append(
            {
                "id": item["id"],
                "platform": item["platform"],
                "platform_label": item.get("platform_label", item["platform"]),
                "title": item["title"],
                "source_url": item["source_url"],
                "cover_url": item["cover_url"],
                "image_urls": item.get("image_urls", []),
                "author": item["author"],
                "published_at": item["published_at"],
                "engagement": item["engagement"],
                "tags": tags,
                "summary": summary,
                "fit_score": score,
                "fit_reason": build_fit_reason(reasons),
                "risk_notes": risks,
                "why_selected": "；".join(reasons[:4]) if reasons else "作为补充型灵感收录。",
                "display_priority": build_priority(score, index),
            }
        )

    recommended_items = [item for item in processed_items if item["fit_score"] >= 0.65]
    recommended_items.sort(key=lambda item: (-item["fit_score"], item["display_priority"]))
    for index, item in enumerate(recommended_items, start=1):
        item["display_priority"] = index

    sorted_sources = [
        {
            "platform": platform,
            "raw_items": stats["raw_items"],
            "recommended_items": stats["recommended_items"],
        }
        for platform, stats in sorted(source_breakdown.items())
    ]

    top_tags = [tag for tag, _ in tag_counter.most_common(5)]
    focus = ["儿童房规划", "客厅功能角", "厨房与餐边柜"]

    return {
        "report_date": report_date,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "report_id": f"daily_report_{report_date.replace('-', '_')}",
        "user_profile_version": "v1",
        "user_profile_snapshot": {
            "house_area_net_sqm": raw_data["profile_context"]["house_area_net_sqm"],
            "layout_preference": raw_data["profile_context"]["layout_preference"],
            "residency_plan": raw_data["profile_context"]["residency_plan"],
            "cooking_frequency": raw_data["profile_context"]["cooking_frequency"],
            "key_needs": raw_data["profile_context"]["key_needs"],
        },
        "source_stats": {
            "raw_items": len(raw_data["items"]),
            "deduplicated_items": len(raw_data["items"]),
            "filtered_items": len(recommended_items),
            "recommended_items": len(recommended_items),
            "source_breakdown": sorted_sources,
        },
        "today_focus": focus,
        "summary": {
            "headline": "当前更值得优先关注实景、长期自住、低维护且贴近二孩家庭的案例。",
            "highlights": [
                "儿童房、客厅功能角和厨房餐边柜仍然是最值得持续观察的三大主题。",
                "高分案例普遍同时命中家庭结构、收纳和低维护三个条件。",
                "灵感图适合拓宽方向，但仍需用真实案例做最后判断。",
            ],
            "question_of_the_day": "你更想先判断儿童房阶段方案，还是先把客厅功能角的形态想清楚？",
            "fit_direction": [
                "优先看真实落地案例，不让纯视觉图主导判断。",
                "继续偏向原木、温暖简约和低维护方向。",
                "将收藏行为反馈回模型后，再逐步做更强的个性化推荐。",
            ],
        },
        "daily_digest": {
            "estimated_read_minutes": 3,
            "recommended_browse_order": focus + ["风格拓展"],
            "top_tags": top_tags,
        },
        "feedback_summary": {
            "recent_positive_patterns": [
                "二孩家庭",
                "原木",
                "客厅功能角",
                "厨房餐边柜",
            ]
        },
        "items": recommended_items,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a report.json from raw candidates.")
    parser.add_argument(
        "--input",
        default="data-samples/raw-candidates.json",
        help="Path to raw candidates JSON.",
    )
    parser.add_argument(
        "--output",
        default="data-samples/generated-report.json",
        help="Path to generated report JSON.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    input_path = repo_root / args.input
    output_path = repo_root / args.output

    raw_data = json.loads(input_path.read_text(encoding="utf-8"))
    report = build_report(raw_data)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Generated {output_path}")


if __name__ == "__main__":
    main()
