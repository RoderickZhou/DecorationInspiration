# 产品方向：视频驱动的学习与风格库

**调整日期**：2026-06-01
**触发**：用户两轮迭代（AI 日报 → Lookbook 图墙）后均反馈「感受不到价值」。深聊后定位到根本原因：**他不缺内容、不想被推**，他要的是「把自己已经挑出的好内容沉淀成可学习、可考核、可检索的知识」。

## 核心交互

```
你逛 B 站等网站 → 看到喜欢的视频 → 自己下好 mp4 丢进 data/videos/inbox/
                                       ↓
python scripts/process_inbox.py
                                       ↓
系统自动:
  1. 字幕提取（user.srt > 嵌入字幕 > Whisper 兜底）
  2. ffmpeg 场景检测抽 10-24 关键帧
  3. Minimax 分类: tutorial / style / other
                                       ↓
                  根据类型走两条流水线
        ┌───────────────────────────────────────┐
        │ tutorial：                            │
        │   - 时间戳大纲 outline                │
        │   - 结构化 Markdown 笔记              │
        │   - 10-15 道 4 选 1 MCQ 含答案 + 解释 │
        │ style：                               │
        │   - 整体风格识别（style + space）     │
        │   - 每帧 AI 配文 + design_points      │
        └───────────────────────────────────────┘
                                       ↓
                  浏览器三页面访问
        ┌───────────────────────────────────────┐
        │ index.html  主页：视频列表 + 入口      │
        │ study.html  学习页：播放器+大纲+笔记+考 │
        │ style.html  风格库：跨视频帧+配文+收藏 │
        └───────────────────────────────────────┘
```

## 为什么前两轮都失败

| 形态 | 失败原因 |
|---|---|
| AI 日报 | 用户不想被推；AI 文字虽专业但用不上；只有 5 条假数据 |
| 视觉 Lookbook | 用户已经会自己刷小红书；被动浏览比刷小红书没强多少；没沉淀 |
| **视频学习库** | 用户**已经会主动挑好内容**，工具的价值在**学进去 + 记下来** |

## v0.1 范围（已实现）

### 字幕策略

| 优先级 | 来源 | 速度 | 质量 |
|---|---|---|---|
| 1 | 同名 `<basename>.srt`（用户跟 mp4 一起丢进 inbox） | 即时 | 取决于来源 |
| 2 | mp4 内嵌字幕流（ffmpeg `-map 0:s:0`） | 即时 | 良好 |
| 3 | `faster-whisper small` 模型本地转写 | 慢（CPU 30 分钟视频 ~15-30 分钟） | 中文较好 |

首次跑 Whisper 会下 ~500MB 模型。可用 `--whisper-model tiny` 提速但中文质量降。

### 关键帧抽取

- ffmpeg 场景检测（`select='gt(scene,0.35)'`）抽场景切换帧
- 不够则用固定间隔补足
- 每视频限 10-24 帧
- 输出到 `data/videos/<id>/frames/keyframe_<index>_<ts>.jpg`，800px 宽

### Minimax 调用清单

| 任务 | 输入 | 输出 schema |
|---|---|---|
| classify_video | 标题 + transcript 前 6k 字 | `{type, confidence, reasoning, style_hint, space_hint}` |
| outline (tutorial) | 全 transcript（带时间戳） | `{chapters: [{ts, title, key_points[]}]}` |
| notes (tutorial) | transcript + outline | markdown 字符串 |
| quiz (tutorial) | transcript + outline + notes | `{questions: [{q, options[4], answer_idx, explanation, ts, topic}]}` |
| style+captions (style) | full transcript + 每帧时间戳 + ±15s 上下文 | `{overall: {headline, style_tags, space_tags}, frames: [{ts, caption, design_points, tags}]}` |

每条 prompt 在 `prompts/video_*.md`。schema 在 `schemas/video_*.schema.json`。

所有失败都不阻断管线：单一 Minimax 调用失败 → 该 artifact 缺失，其他继续。

### 三个前端页面

#### `demo/index.html`

- 顶部"如何添加视频"指引
- 三张主卡片：指引 / 学习中心入口 / 风格库入口
- 视频网格：每张卡片 = 封面（首关键帧） + 标题 + 类型徽标 + 时长 + 字幕来源 + 帧数
- 类型徽标：教学（蓝）/ 风格（橙）/ 其他（灰）/ 处理中（暗）

#### `demo/study.html?id=<video_id>`

- 顶部：HTML5 video + `<track>` 字幕同步显示
- 左侧：可点击的章节大纲（点击跳转 video.currentTime）
- 主区 tab：
  - 📝 笔记：内嵌 markdown 渲染（h2/h3/ul/blockquote/strong/code）
  - 📝 考考你：一题一题做，4 选 1，做完显示对错 + 解释 + "回放该段"
  - 🖼️ 关键截图：网格缩略图，点击跳转视频时间戳
- 答题进度 + 得分 localStorage 持久化

#### `demo/style.html?focus=<video_id>?`

- 沿用上一轮 lookbook.html 的瀑布流（CSS columns）+ ❤️ 收藏 + 收藏侧抽屉 + 导出 jsonl
- 数据源：`data/style_index.json`（process_inbox 自动聚合所有 style 视频的 captions）
- 卡片新增：caption 配文、design_points 列表、"来自《视频名》mm:ss"链接（跳 study.html）
- 顶 tab：空间筛 / 第二行 chip：风格筛
- `?focus=<id>` 可锁定只看某视频的帧

## 不在 v0.1 范围

- yt-dlp 自动下载（用户选了 drop 文件路径）
- 跨视频汇总（"厨房精通"主题树、错题本聚合）→ v0.2
- 笔记编辑持久化（仅 localStorage 临时存）→ v0.2
- 简答题 / 默写题（用户只要 MCQ）
- 视觉模型识图（M2.7 纯文本；配文靠转写时间戳上下文）→ v0.3 接 VL 模型
- React 工程版 / 服务端持久化

## 验收方式

让用户准备 1-2 个真实视频（最好 1 个教学 + 1 个风格），drop 进 inbox 跑一次，看：

- 教学视频：能不能播 + 字幕同步 + outline 可跳 + 笔记结构清晰 + MCQ 能答能跳回
- 风格视频：关键帧出现在风格库，配文是不是"基于实际语境的具体设计点"而非泛泛
- 整体感受：跟前两轮（日报 / 图墙）相比，是不是"终于像是个能让我学进东西的工具"
