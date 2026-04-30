export const gradients = [
  "linear-gradient(180deg, rgba(191,219,254,0.18), rgba(96,165,250,0.34))",
  "linear-gradient(180deg, rgba(254,215,170,0.18), rgba(251,146,60,0.30))",
  "linear-gradient(180deg, rgba(216,180,254,0.16), rgba(167,139,250,0.32))",
  "linear-gradient(180deg, rgba(187,247,208,0.14), rgba(34,197,94,0.30))",
  "linear-gradient(180deg, rgba(191,219,254,0.16), rgba(37,99,235,0.32))",
  "linear-gradient(180deg, rgba(254,205,211,0.18), rgba(244,114,182,0.28))",
];

const goodTags = new Set([
  "二孩家庭",
  "长期自住",
  "收纳强",
  "高频做饭友好",
  "低维护",
  "可成长空间",
  "易清洁",
]);

const warnTags = new Set(["灵感图", "海外案例", "拼贴灵感", "偏审美"]);
const badTags = new Set(["高维护"]);

export function formatNumber(value) {
  if (!value) return "0";
  if (value >= 10000) return `${(value / 10000).toFixed(1)}w`;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`;
  return String(value);
}

export function formatRelativeDate(dateText) {
  if (!dateText) return "时间未知";

  const date = new Date(dateText);
  const diffMs = Date.now() - date.getTime();
  const diffDays = Math.max(0, Math.floor(diffMs / (1000 * 60 * 60 * 24)));

  if (diffDays === 0) return "今天";
  if (diffDays === 1) return "1 天前";
  if (diffDays < 7) return `${diffDays} 天前`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} 周前`;
  return `${Math.floor(diffDays / 30)} 个月前`;
}

export function getTagTone(tag) {
  if (goodTags.has(tag)) return "good";
  if (warnTags.has(tag)) return "warn";
  if (badTags.has(tag)) return "bad";
  return "";
}

export function collectDisplayTags(item) {
  return [
    ...item.tags.style,
    ...item.tags.space,
    ...item.tags.family,
    ...item.tags.features,
  ].slice(0, 6);
}

export function buildQuickStats(report) {
  return [
    {
      label: "今日新增素材",
      value: report.source_stats.raw_items,
      desc: `去重后 ${report.source_stats.deduplicated_items} 条，来自 ${report.source_stats.source_breakdown.length} 个来源`,
    },
    {
      label: "筛选后推荐",
      value: report.source_stats.recommended_items,
      desc: `控制在 ${report.daily_digest.estimated_read_minutes} 分钟左右可浏览完成`,
    },
    {
      label: "今日主题",
      value: "儿童房 / 客厅角",
      desc: report.today_focus.slice(0, 2).join("；"),
    },
    {
      label: "反馈偏好",
      value: report.feedback_summary.recent_positive_patterns[0],
      desc: `近期偏好：${report.feedback_summary.recent_positive_patterns.slice(0, 4).join(" / ")}`,
    },
  ];
}

export function buildInsightItems(report) {
  return [...report.summary.highlights, ...report.today_focus].slice(0, 3);
}

export function buildQuestionItems(report) {
  return [
    report.summary.question_of_the_day,
    `你最想先解决的是 ${report.today_focus[0]}，还是 ${report.today_focus[1]}？`,
    `从今天的案例看，你更偏向 ${report.daily_digest.top_tags.slice(0, 3).join(" / ")}，这个方向是不是越来越清晰了？`,
  ];
}

export function buildSummaryCards(report) {
  const sourceNames = report.source_stats.source_breakdown
    .map((item) => item.platform)
    .join(" / ");

  return [
    {
      title: "来源统计",
      text: `原始采集 ${report.source_stats.raw_items} 条，去重后 ${report.source_stats.deduplicated_items} 条，规则筛选 ${report.source_stats.filtered_items} 条，最终推荐 ${report.source_stats.recommended_items} 条。`,
      highlight: true,
    },
    {
      title: "Minimax 输出",
      text: "每条内容产出短摘要、标签、适配分和风险点，并汇总为今日主题、日报摘要与关键问题。",
    },
    {
      title: "来源覆盖",
      text: `当前日报来源包含 ${sourceNames}，后续只要保持 JSON 结构一致，前端页面无需大改。`,
    },
  ];
}
