import { useEffect, useMemo, useState } from "react";
import "./App.css";
import reportData from "../../data-samples/sample-report.json";
import generatedReportData from "../../data-samples/generated-report.json";
import FeedCard from "./components/FeedCard";
import SectionHeader from "./components/SectionHeader";
import StatCard from "./components/StatCard";
import {
  appendFeedback,
  buildFeedbackEntry,
  buildLatestActionMap,
  clearFeedback,
  exportFeedback,
  loadFeedback,
} from "./utils/feedback";
import {
  buildInsightItems,
  buildQuestionItems,
  buildQuickStats,
  buildSummaryCards,
  collectDisplayTags,
  formatNumber,
  formatRelativeDate,
  getTagTone,
} from "./utils/report";

function FilterGroup({ title, values, selectedValue, onSelect }) {
  return (
    <div className="filter-group">
      <div className="filter-group-title">{title}</div>
      <div className="filter-chip-row">
        <button
          type="button"
          className={`filter-chip ${selectedValue === "全部" ? "is-active" : ""}`}
          onClick={() => onSelect("全部")}
        >
          全部
        </button>
        {values.map((value) => (
          <button
            key={value}
            type="button"
            className={`filter-chip ${selectedValue === value ? "is-active" : ""}`}
            onClick={() => onSelect(value)}
          >
            {value}
          </button>
        ))}
      </div>
    </div>
  );
}

function DetailPanel({ item, feedbackAction }) {
  if (!item) {
    return (
      <div className="detail-panel detail-empty">
        <strong>还没有选中案例</strong>
        <div className="subtle">点击下方任意卡片的标题或“查看详情”，这里会显示更完整的案例信息。</div>
      </div>
    );
  }

  return (
    <div className="detail-panel">
      <div className="detail-cover-wrap">
        <img className="detail-cover" src={item.cover_url} alt={item.title} />
      </div>
      <div className="detail-body">
        <div className="detail-header">
          <div>
            <div className="eyebrow detail-platform">{item.platform_label || item.platform}</div>
            <h2 className="detail-title">{item.title}</h2>
          </div>
          <div className="detail-score">
            <span className="subtle">匹配度</span>
            <strong>{item.fit_score.toFixed(2)}</strong>
          </div>
        </div>

        <div className="meta">
          <span>{`作者 ${item.author}`}</span>
          <span>{`发布时间 ${formatRelativeDate(item.published_at)}`}</span>
          <span>{`点赞 ${formatNumber(item.engagement.likes)}`}</span>
          <span>{`收藏 ${formatNumber(item.engagement.favorites)}`}</span>
        </div>

        <div className="tag-row">
          {collectDisplayTags(item).map((tag) => (
            <span key={`detail-${item.id}-${tag}`} className={`tag ${getTagTone(tag)}`}>
              {tag}
            </span>
          ))}
        </div>

        <div className="detail-summary">{item.summary}</div>
        <div className="reason">{`适合原因：${item.fit_reason}`}</div>
        <div className="risk">{`注意点：${(item.risk_notes || []).join("；") || "暂无明显风险提示"}`}</div>

        <div className="detail-grid">
          <div className="detail-metric">
            <span className="subtle">入选原因</span>
            <strong>{item.why_selected}</strong>
          </div>
          <div className="detail-metric">
            <span className="subtle">当前反馈</span>
            <strong>{feedbackAction ? `已标记：${feedbackAction}` : "尚未操作"}</strong>
          </div>
          <div className="detail-metric">
            <span className="subtle">原始链接</span>
            <strong className="detail-link-text">{item.source_url}</strong>
          </div>
        </div>
      </div>
    </div>
  );
}

function App() {
  const [reportMode, setReportMode] = useState("sample");
  const report = reportMode === "sample" ? reportData : generatedReportData;
  const [feedbackEntries, setFeedbackEntries] = useState(() => loadFeedback());
  const [view, setView] = useState("discover");
  const [styleFilter, setStyleFilter] = useState("全部");
  const [spaceFilter, setSpaceFilter] = useState("全部");
  const [platformFilter, setPlatformFilter] = useState("全部");
  const [selectedItemId, setSelectedItemId] = useState(null);

  const sortedItems = useMemo(
    () => [...report.items].sort((a, b) => a.display_priority - b.display_priority),
    [report.items],
  );
  const latestActionMap = useMemo(
    () => buildLatestActionMap(feedbackEntries),
    [feedbackEntries],
  );
  const favoriteIds = useMemo(
    () =>
      Object.entries(latestActionMap)
        .filter(([, action]) => action === "favorite")
        .map(([itemId]) => itemId),
    [latestActionMap],
  );
  const availableStyles = useMemo(
    () => [...new Set(sortedItems.flatMap((item) => item.tags.style))],
    [sortedItems],
  );
  const availableSpaces = useMemo(
    () => [...new Set(sortedItems.flatMap((item) => item.tags.space))],
    [sortedItems],
  );
  const availablePlatforms = useMemo(
    () => [...new Set(sortedItems.map((item) => item.platform_label || item.platform))],
    [sortedItems],
  );
  const filteredItems = useMemo(() => {
    return sortedItems.filter((item) => {
      const styleOk = styleFilter === "全部" || item.tags.style.includes(styleFilter);
      const spaceOk = spaceFilter === "全部" || item.tags.space.includes(spaceFilter);
      const platformOk =
        platformFilter === "全部" ||
        (item.platform_label || item.platform) === platformFilter;
      const favoriteOk = view !== "favorites" || favoriteIds.includes(item.id);
      return styleOk && spaceOk && platformOk && favoriteOk;
    });
  }, [sortedItems, styleFilter, spaceFilter, platformFilter, view, favoriteIds]);
  const selectedItem = useMemo(
    () => filteredItems.find((item) => item.id === selectedItemId) || sortedItems.find((item) => item.id === selectedItemId) || filteredItems[0] || sortedItems[0] || null,
    [filteredItems, selectedItemId, sortedItems],
  );

  useEffect(() => {
    if (!selectedItemId && sortedItems[0]) {
      setSelectedItemId(sortedItems[0].id);
    }
  }, [selectedItemId, sortedItems]);

  useEffect(() => {
    if (selectedItem && !selectedItemId) {
      setSelectedItemId(selectedItem.id);
    }
  }, [selectedItem, selectedItemId]);

  const handleAction = (item, index, action) => {
    const entry = buildFeedbackEntry(
      report.report_id,
      item.id,
      action,
      index + 1,
      item.platform,
    );
    const nextEntries = appendFeedback(entry);
    setFeedbackEntries(nextEntries);

    if (action === "open_source") {
      window.open(item.source_url, "_blank", "noopener,noreferrer");
    }
  };

  const handleSelectItem = (item) => {
    setSelectedItemId(item.id);
  };

  const handleExport = () => {
    exportFeedback(feedbackEntries);
  };

  const handleClear = () => {
    clearFeedback();
    setFeedbackEntries([]);
  };

  const handleResetFilters = () => {
    setStyleFilter("全部");
    setSpaceFilter("全部");
    setPlatformFilter("全部");
  };

  const heroTags = [
    "四口常住",
    "两个儿子",
    `${report.user_profile_snapshot.house_area_net_sqm} 平到手`,
    report.user_profile_snapshot.cooking_frequency,
    report.user_profile_snapshot.residency_plan,
  ];

  return (
    <div className="page-shell">
      <div className="container">
        <div className="feedback-banner">
          <div>
            <strong>{`反馈记录已开启，当前已保存 ${feedbackEntries.length} 条本地动作`}</strong>
            <div className="subtle">
              React 工程版继续使用浏览器本地存储模拟 actions.jsonl 回流，后续可无缝替换成接口写入。
            </div>
          </div>
          <div className="toolbar">
            <div className="view-tabs">
              <button
                type="button"
                className={`view-tab ${reportMode === "sample" ? "is-active" : ""}`}
                onClick={() => setReportMode("sample")}
              >
                样例日报
              </button>
              <button
                type="button"
                className={`view-tab ${reportMode === "generated" ? "is-active" : ""}`}
                onClick={() => setReportMode("generated")}
              >
                脚本日报
              </button>
            </div>
            <button type="button" className="btn-export" onClick={handleExport}>
              导出反馈 JSONL
            </button>
            <button type="button" className="btn-clear" onClick={handleClear}>
              清空本地反馈
            </button>
          </div>
        </div>

        <section className="hero">
          <div className="card hero-main">
            <div>
              <div className="eyebrow">装修灵感日报 / React App</div>
              <h1>
                {`每天 ${report.daily_digest.estimated_read_minutes} 分钟`}
                <br />
                把海量装修内容变成可判断的灵感流
              </h1>
              <p>{report.summary.headline}</p>
            </div>
            <div className="hero-tags">
              {heroTags.map((tag) => (
                <span key={tag} className="badge">
                  {tag}
                </span>
              ))}
            </div>
          </div>

          <div className="quick-stats">
            {buildQuickStats(report).map((stat) => (
              <StatCard key={stat.label} {...stat} />
            ))}
          </div>
        </section>

        <section className="card">
          <SectionHeader
            title="今天值得先看的重点"
            description="这一栏直接来自日报摘要与主题结果，让你先抓住当天最值得判断的方向。"
            pill="Minimax 自动摘要 + React 组件渲染"
          />
          <div className="insight-grid">
            {buildInsightItems(report).map((text, index) => (
              <div key={text} className="insight">
                <strong>{`重点 ${index + 1}`}</strong>
                <div>{text}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="card section-gap">
          <SectionHeader
            title="今日推荐卡片"
            description="这一版补上了视图切换、筛选和详情区，已经开始接近真正的产品结构。"
            pill={`${report.source_stats.recommended_items} 条精选 / 当前命中 ${filteredItems.length} 条`}
          />

          <div className="view-toolbar">
            <div className="view-tabs">
              <button
                type="button"
                className={`view-tab ${view === "discover" ? "is-active" : ""}`}
                onClick={() => setView("discover")}
              >
                发现页
              </button>
              <button
                type="button"
                className={`view-tab ${view === "favorites" ? "is-active" : ""}`}
                onClick={() => setView("favorites")}
              >
                收藏夹
              </button>
            </div>
            <div className="subtle">{`当前收藏 ${favoriteIds.length} 条，当前筛中 ${filteredItems.length} 条`}</div>
          </div>

          <div className="workspace-grid">
            <aside className="card workspace-sidebar">
              <SectionHeader
                title="筛选器"
                description="先按风格、空间和来源缩小范围，再看详情区和卡片列表。"
              />
              <FilterGroup
                title="风格"
                values={availableStyles}
                selectedValue={styleFilter}
                onSelect={setStyleFilter}
              />
              <FilterGroup
                title="空间"
                values={availableSpaces}
                selectedValue={spaceFilter}
                onSelect={setSpaceFilter}
              />
              <FilterGroup
                title="来源"
                values={availablePlatforms}
                selectedValue={platformFilter}
                onSelect={setPlatformFilter}
              />
              <div className="workspace-sidebar-actions">
                <button type="button" className="btn-clear" onClick={handleResetFilters}>
                  重置筛选
                </button>
              </div>
            </aside>

            <div className="workspace-main">
              <DetailPanel
                item={selectedItem}
                feedbackAction={selectedItem ? latestActionMap[selectedItem.id] : ""}
              />

              {filteredItems.length ? (
                <div className="feed-grid">
                  {filteredItems.map((item, index) => (
                    <FeedCard
                      key={item.id}
                      item={item}
                      index={index}
                      activeAction={latestActionMap[item.id]}
                      onAction={handleAction}
                      onSelect={handleSelectItem}
                      selected={selectedItem?.id === item.id}
                    />
                  ))}
                </div>
              ) : (
                <div className="empty-state">
                  <strong>当前没有匹配的案例</strong>
                  <div className="subtle">可以切回“发现页”或重置筛选条件继续查看。</div>
                </div>
              )}
            </div>
          </div>
        </section>

        <section className="two-col section-gap">
          <div className="card">
            <SectionHeader
              title="今天最适合你家的方向"
              description="这里使用日报中的适配方向和近期正向反馈，帮助你收敛判断。"
            />
            <div className="panel-list">
              {report.summary.fit_direction.map((text, index) => (
                <div key={text} className="panel-item">
                  <strong>{`方向 ${index + 1}`}</strong>
                  <div>{text}</div>
                  {report.feedback_summary.recent_positive_patterns[index] ? (
                    <div className="subtle section-note">
                      {`近期反馈加权：${report.feedback_summary.recent_positive_patterns[index]}`}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <SectionHeader
              title="今天该思考的问题"
              description="日报每天保留一个关键问题，帮助你把“看图”转化成“逐步做决定”。"
            />
            <div className="panel-list">
              {buildQuestionItems(report).map((question, index) => (
                <div key={question} className="panel-item">
                  <strong>{`问题 ${index + 1}`}</strong>
                  <div>{question}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="card section-gap">
          <SectionHeader
            title="页面背后的系统输出"
            description="这部分对应采集、模型整理和反馈回流，方便后续直接扩成真正的数据产品。"
          />
          <div className="summary-grid">
            {buildSummaryCards(report).map((card) => (
              <div
                key={card.title}
                className={`summary-card ${card.highlight ? "highlight" : ""}`}
              >
                <h3>{card.title}</h3>
                <p className="subtle">{card.text}</p>
              </div>
            ))}
          </div>
        </section>

        <div className="footer">
          当前版本直接读取仓库里的样例日报数据，后续只要把真实 report.json 接进来，页面结构无需重做。
        </div>
      </div>
    </div>
  );
}

export default App;
