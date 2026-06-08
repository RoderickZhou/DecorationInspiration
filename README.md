# DecorationInspiration

围绕家庭装修早期决策阶段的**视频驱动学习与风格库**。

**当前主形态：视频学习 + 风格库**（v0.1，见 `docs/video-knowledge-direction.md`）

```
你逛 B 站等地方 → 下好 mp4 丢进 inbox →
  系统自动: ffmpeg 提帧 + 字幕 + Minimax 分类
  分两条线：
    • tutorial → 学习页（outline + 笔记 + MCQ 考核）
    • style    → 风格库（抽设计帧 + AI 配文）
```

主入口：`demo/index.html`（旧的 `lookbook.html` / `renovation-daily-demo.html` 保留备查但不是主路径）

最小启动流程：

```powershell
# 1. 把视频和（可选）同名字幕丢进 inbox
move D:\Downloads\<视频>.mp4 data\videos\inbox\
move D:\Downloads\<视频>.srt data\videos\inbox\

# 2. 端到端跑（首次会下 Whisper 模型；有字幕的话跳过 Whisper）
python scripts/process_inbox.py

# 3. 浏览器打开
# http://localhost:8008/demo/index.html
```

详见 `docs/video-knowledge-direction.md`。

最小链路（v0.1）：

```bash
# 采集真图（360 图搜，覆盖 5 空间，~1000 张）
python scripts/scrape_inspiration_360.py --output data/raw/inspiration_360.raw.jsonl --per-query 30 --skip-aigc

# 转 candidates
python scripts/convert_raw_to_candidates.py --input data/raw/inspiration_360.sampled.jsonl --output data/raw/candidates.360.jsonl

# Minimax 打标
python scripts/prepare_minimax_item_inputs.py --candidates data/raw/candidates.360.jsonl --output data/raw/minimax_item_inputs.360.jsonl
python scripts/run_item_structuring.py --mode minimax --input data/raw/minimax_item_inputs.360.jsonl --output data/normalized/item_structuring.360.outputs.jsonl --concurrency 6

# 出最终 report
python scripts/generate_daily_report.py --date 2026-05-30 --input data/raw/candidates.360.jsonl --output data/reports/2026-05-30/report.lookbook.json --structured-items data/normalized/item_structuring.360.outputs.jsonl --limit 200

# 启服务后浏览器打开
python -m http.server 8008
# -> http://localhost:8008/demo/lookbook.html?data=../data/reports/2026-05-30/report.lookbook.json
```

## 当前内容

- `demo/renovation-daily-demo.html`
  - 数据驱动版装修灵感日报 Demo
  - 页面默认读取 `data-samples/sample-report.json` 动态渲染
  - 支持通过 `?data=...` 指定任意日报 JSON 路径
  - 点击喜欢、收藏、不喜欢会记录到浏览器本地，模拟反馈回流
- `demo/renovation-planner-demo.html`
  - 更偏全局产品视角的装修决策助手假 Demo
- `docs/renovation-daily-prd.md`
  - 第一版产品需求文档
- `docs/minimax-spec.md`
  - Minimax 结构化整理入口规范
- `docs/minimax-io.md`
  - Minimax 输入输出规范（v1）
- `docs/pipeline.md`
  - 原始采集数据 -> candidates -> report.json 的转换流程
- `data-samples/sample-report.json`
  - 可直接喂给前端的日报数据样例
- `data-samples/sample-actions.jsonl`
  - 用户反馈行为样例
- `data-samples/raw-candidates.json`
  - 更贴近采集器输出的原始候选内容样例
- `data-samples/generated-report.json`
  - 由脚本从原始候选内容生成的日报样例
- `scripts/generate_report.py`
  - 旧版日报骨架（保留备查，已被 `generate_daily_report.py` 取代）
- `prompts/`
  - Minimax 的单条结构化和日报汇总 prompt
- `web/`
  - React + Vite 前端工程版日报页面
  - 已支持发现页 / 收藏夹 / 筛选器 / 详情区
- `data-samples/sample-raw-items.jsonl`
  - 原始采集输出样例（raw collector JSONL）
- `data-samples/sample-candidates.jsonl`
  - 采集器输出的候选内容样例（JSONL）
- `schemas/report.schema.json`
  - 前端与脚本的稳定契约：report.json schema
- `scripts/generate_daily_report.py`
  - 从候选内容 JSONL 生成当日 `report.json`
- `scripts/convert_raw_to_candidates.py`
  - raw collector JSONL -> candidates JSONL
- `scripts/prepare_minimax_item_inputs.py`
  - candidates JSONL -> item_structuring 批量输入（JSONL）
- `scripts/prepare_minimax_daily_summary_input.py`
  - report.json -> daily_summary 单次输入（JSON）
- `scripts/validate_candidates.py`
  - candidates JSONL 的基础校验（无依赖）
- `scripts/validate_report_basic.py`
  - report.json 的基础校验（无依赖）
- `scripts/merge_actions_jsonl.py`
  - 合并/去重/排序多份 actions.jsonl（多电脑协作）
- `scripts/run_item_structuring.py`
  - item_structuring 运行器，支持 `--mode heuristic`（无依赖兜底）和 `--mode minimax`（真实 API + 并发 + 缓存 + 失败降级）
- `scripts/run_daily_summary.py`
  - daily_summary 运行器，支持 `--mode heuristic` 和 `--mode minimax`（同上）
- `scripts/minimax_client.py`
  - Minimax HTTP client（urllib，无第三方依赖）；读取 `.env` 或环境变量 `MINIMAX_API_KEY/BASE_URL/MODEL`
- `scripts/_schema_validate.py`
  - 最小 JSON Schema 校验器，用于校验 Minimax 输出

## 目标用户场景

- 房屋建筑面积约 132 平，到手面积约 98 平
- 四口常住
- 大儿子 7 岁，小儿子 8 个月
- 纯自住长期居住
- 高频做饭
- 重点关注儿童房、客厅功能角、厨房与餐边柜、全屋收纳

## 仓库结构

```text
DecorationInspiration/
  data/
    user_profile.v1.json
    raw/
    normalized/
    reports/
  scripts/
    convert_raw_to_candidates.py
    generate_daily_report.py
  prompts/
    minimax_item_structuring.md
    minimax_daily_summary.md
  demo/
    renovation-daily-demo.html
    renovation-planner-demo.html
  docs/
    minimax-io.md
    pipeline.md
    renovation-daily-prd.md
    minimax-spec.md
    hand-off.md
    qa.md
  schemas/
    raw_collector_item.schema.json
    candidate.schema.json
    minimax_item_structuring.schema.json
    minimax_daily_summary.schema.json
    report.schema.json
  data-samples/
    raw-candidates.json
    generated-report.json
    sample-raw-items.jsonl
    sample-candidates.jsonl
    sample-report.json
    sample-actions.jsonl
  prompts/
    item-structuring.md
    daily-digest.md
  scripts/
    generate_report.py
    convert_raw_to_candidates.py
    generate_daily_report.py
    prepare_minimax_item_inputs.py
    prepare_minimax_daily_summary_input.py
    run_item_structuring.py
    run_daily_summary.py
    validate_candidates.py
    validate_report_basic.py
    merge_actions_jsonl.py
  web/
    src/
    package.json
```

## 当前原型能力

- 多来源装修灵感内容的日报展示结构
- 用户画像驱动的推荐方向表达
- 可直接供前端开发使用的数据样例
- 收藏 / 喜欢 / 不喜欢 / 查看原文的前端交互模拟
- React 工程版前端页面
- 原始候选内容到日报 JSON 的脚本骨架
- Minimax 结构化整理规范与 prompt

## 运行方式

### 前端工程

```bash
cd web
npm install
npm run dev
```

### 日报生成脚本

主管线脚本是 `scripts/generate_daily_report.py`（参考下面"本地运行"小节）。`scripts/generate_report.py` 是旧版骨架，仅保留备查。

## 当前完成状态

- 已完成静态 Demo 和 React 工程版前端
- 已完成日报样例数据和反馈样例数据
- 已完成原始候选内容样例
- 已完成日报生成脚本骨架
- 已完成 Minimax 输入输出规范和 prompt 文档

## 本地运行

生成一份日报 JSON：

```bash
python scripts/generate_daily_report.py --date 2026-04-30 --input data-samples/sample-candidates.jsonl --output data/reports/2026-04-30/report.json --actions data-samples/sample-actions.jsonl
```

启动静态服务并预览：

```bash
python -m http.server 8008
```

```text
http://localhost:8008/demo/renovation-daily-demo.html
http://localhost:8008/demo/renovation-daily-demo.html?data=../data/reports/2026-04-30/report.json
```

## 下一步建议

- 接真实采集器，把原始候选内容自动写入 `raw-candidates.json`
- 接 Minimax API，让脚本从规则骨架升级为模型结构化处理
- 增加收藏页、详情页和接口化数据源
- 增加反馈学习逻辑，让下一日报告真正根据收藏行为调整排序

## 说明

当前仓库以原型、文档和样例数据为主，目的是先把产品形态、数据结构和前端交互链路跑通，再逐步接入真实采集与模型处理能力。
