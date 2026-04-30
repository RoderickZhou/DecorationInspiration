# Minimax 处理入口规范

这份文档定义的是“采集器输出原始候选内容”进入模型处理后，如何稳定产出前端和日报系统可消费的数据结构。

目标链路：

`raw-candidates.json -> Minimax 结构化整理 -> report.json -> web 前端展示 -> actions.jsonl 反馈回流`

## 1. 入口职责

Minimax 在这套系统里不负责爬取，不负责页面展示，主要负责：

- 判断内容是否值得进入日报
- 生成一句适合卡片展示的短摘要
- 提取统一标签
- 判断与当前家庭画像的匹配度
- 输出注意点和入选原因
- 汇总成“今日摘要”和“今日问题”

## 2. 输入格式

模型的输入对象建议按单条候选内容组织，字段可以来自采集器或预处理器：

```json
{
  "profile_context": {
    "house_area_net_sqm": 98,
    "layout_preference": "3室",
    "household": "四口常住，两个儿子，年龄差较大",
    "residency_plan": "纯自住长期居住",
    "cooking_frequency": "高频做饭",
    "key_needs": ["儿童房规划", "客厅功能角", "厨房与餐边柜", "全屋收纳", "低维护"]
  },
  "candidate": {
    "id": "raw_xhs_001",
    "platform": "xiaohongshu",
    "platform_label": "小红书",
    "title": "98平二孩家庭原木风三居，先做一睡一玩的儿童房",
    "source_url": "https://example.com/post/001",
    "cover_url": "https://example.com/image.jpg",
    "image_urls": ["https://example.com/image.jpg"],
    "author": "住进原木里",
    "published_at": "2026-04-28T20:12:00+08:00",
    "engagement": {
      "likes": 3248,
      "favorites": 2411,
      "comments": 387
    },
    "content_text": "实景案例，房屋套内接近98平...",
    "media_type": "mixed",
    "detected_keywords": ["98平", "二孩家庭", "儿童房", "原木"]
  }
}
```

## 3. 输出格式

模型输出必须能直接合并到 `report.json` 的 `items[]` 中。推荐字段如下：

```json
{
  "id": "raw_xhs_001",
  "platform": "xiaohongshu",
  "platform_label": "小红书",
  "title": "98平二孩家庭原木风三居，先做一睡一玩的儿童房",
  "source_url": "https://example.com/post/001",
  "cover_url": "https://example.com/image.jpg",
  "image_urls": ["https://example.com/image.jpg"],
  "author": "住进原木里",
  "published_at": "2026-04-28T20:12:00+08:00",
  "engagement": {
    "likes": 3248,
    "favorites": 2411,
    "comments": 387
  },
  "tags": {
    "style": ["原木", "现代简约"],
    "space": ["儿童房", "客厅", "厨房"],
    "family": ["二孩家庭", "长期自住", "三居"],
    "features": ["客厅功能角", "收纳强", "低维护"]
  },
  "summary": "二孩家庭实景案例，先做一睡一玩，客厅再嵌入大人功能角，整体对当前家庭很有参考价值。",
  "fit_score": 0.91,
  "fit_reason": "面积、家庭结构、使用周期和生活方式都与目标家庭高度接近。",
  "risk_notes": ["开放格略多，杂物管理要再加强"],
  "why_selected": "同时命中儿童房、客厅功能角、二孩家庭和长期自住四个高优先级条件。",
  "display_priority": 1
}
```

## 4. 字段约束

- `summary`
  - 1 句话
  - 30 到 60 字为宜
  - 适合直接展示在卡片上
- `fit_score`
  - 0 到 1
  - 保留两位小数
- `tags`
  - 分类必须稳定
  - 不同来源尽量复用同一套标签，不要每个平台各自发散
- `risk_notes`
  - 1 到 3 条
  - 只保留真正会影响判断的注意点
- `why_selected`
  - 说明为什么值得进入日报
  - 不要写得像总结，要像筛选理由

## 5. 建议标签体系

### 风格

- 原木
- 现代简约
- 温暖简约
- 奶油风
- 简约
- 法式
- 侘寂

### 空间

- 儿童房
- 客厅
- 厨房
- 餐边柜
- 主卧
- 阳台
- 卫生间

### 家庭画像

- 二孩家庭
- 长期自住
- 有婴儿
- 学龄儿童
- 三居

### 特征

- 客厅功能角
- 收纳强
- 低维护
- 高频做饭友好
- 儿童活动区
- 可成长空间
- 灵感图
- 高维护

## 6. 日报级汇总输出

在单条内容处理完成后，Minimax 还需要做一次日报级汇总，推荐输出：

- `headline`
- `highlights`
- `question_of_the_day`
- `fit_direction`
- `today_focus`
- `top_tags`

这些字段已经被当前前端工程使用。

## 7. 与脚本的分工

- 脚本负责：
  - 读写文件
  - 规则去重
  - 规则初筛
  - 排序与聚合
  - 生成 `report.json`
- Minimax 负责：
  - 标签和摘要
  - 适配度判断
  - 风险提示
  - 日报摘要

## 8. 当前仓库对应文件

- 原始候选样例：`data-samples/raw-candidates.json`
- 日报样例：`data-samples/sample-report.json`
- 脚本骨架：`scripts/generate_report.py`
- 前端工程：`web/`

## 9. 当前建议

- 先用脚本和样例数据把数据链路跑通
- 再把 Minimax 接成稳定的结构化入口
- 最后再接真实采集器和反馈学习
