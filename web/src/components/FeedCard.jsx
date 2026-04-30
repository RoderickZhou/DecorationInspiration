import {
  collectDisplayTags,
  formatNumber,
  formatRelativeDate,
  getTagTone,
  gradients,
} from "../utils/report";

function ActionButton({ action, active, onClick }) {
  const labelMap = {
    like: "喜欢",
    favorite: "收藏",
    dislike: "不喜欢",
    open_source: "查看原文",
  };

  const classMap = {
    like: "btn-like",
    favorite: "btn-save",
    dislike: "btn-dislike",
    open_source: "btn-source",
  };

  return (
    <button
      type="button"
      className={`${classMap[action]} ${active ? "button-active" : ""}`}
      onClick={onClick}
    >
      {labelMap[action]}
    </button>
  );
}

function FeedCard({ item, index, activeAction, onAction }) {
  const tags = collectDisplayTags(item);
  const gradient = gradients[index % gradients.length];
  const sourceLabel = item.platform_label || item.platform;
  const meta = [
    `点赞 ${formatNumber(item.engagement.likes)}`,
    `收藏 ${formatNumber(item.engagement.favorites)}`,
    `发布时间 ${formatRelativeDate(item.published_at)}`,
  ];

  return (
    <article className="feed-card">
      <div
        className="feed-cover"
        style={{
          backgroundImage: `${gradient}, url('${item.cover_url}')`,
        }}
      >
        <div className="cover-meta">
          <div className="cover-badges">
            <span className="badge">{sourceLabel}</span>
            <span className="badge">{`匹配度 ${item.fit_score.toFixed(2)}`}</span>
          </div>
        </div>
      </div>

      <div className="feed-body">
        <h3 className="feed-title">{item.title}</h3>
        <div className="meta">
          {meta.map((line) => (
            <span key={line}>{line}</span>
          ))}
        </div>

        <div className="tag-row">
          {tags.map((tag) => (
            <span key={`${item.id}-${tag}`} className={`tag ${getTagTone(tag)}`}>
              {tag}
            </span>
          ))}
        </div>

        <p>{item.summary}</p>
        <div className="reason">{`适合原因：${item.fit_reason}`}</div>
        <div className="risk">{`注意点：${(item.risk_notes || []).join("；") || "暂无明显风险提示"}`}</div>
        <div className="subtle">{`入选原因：${item.why_selected}`}</div>

        <div className="actions">
          <ActionButton
            action="like"
            active={activeAction === "like"}
            onClick={() => onAction(item, index, "like")}
          />
          <ActionButton
            action="favorite"
            active={activeAction === "favorite"}
            onClick={() => onAction(item, index, "favorite")}
          />
          <ActionButton
            action="dislike"
            active={activeAction === "dislike"}
            onClick={() => onAction(item, index, "dislike")}
          />
          <ActionButton
            action="open_source"
            active={false}
            onClick={() => onAction(item, index, "open_source")}
          />
        </div>
      </div>
    </article>
  );
}

export default FeedCard;
