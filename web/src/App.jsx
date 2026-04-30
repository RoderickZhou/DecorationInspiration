import { useMemo, useState } from "react";
import "./App.css";
import reportData from "../../data-samples/sample-report.json";
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
} from "./utils/report";

function App() {
  const report = reportData;
  const [feedbackEntries, setFeedbackEntries] = useState(() => loadFeedback());

  const sortedItems = useMemo(
    () => [...report.items].sort((a, b) => a.display_priority - b.display_priority),
    [report.items],
  );
  const latestActionMap = useMemo(
    () => buildLatestActionMap(feedbackEntries),
    [feedbackEntries],
  );

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

  const handleExport = () => {
    exportFeedback(feedbackEntries);
  };

  const handleClear = () => {
    clearFeedback();
    setFeedbackEntries([]);
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
            description="推荐卡片现在由 React 组件渲染，后续可以很自然扩成详情页、收藏页和筛选器。"
            pill={`${report.source_stats.recommended_items} 条精选 / 当前展示 ${sortedItems.length} 条`}
          />
          <div className="feed-grid">
            {sortedItems.map((item, index) => (
              <FeedCard
                key={item.id}
                item={item}
                index={index}
                activeAction={latestActionMap[item.id]}
                onAction={handleAction}
              />
            ))}
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
