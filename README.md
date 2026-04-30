# DecorationInspiration

一个围绕家庭装修早期决策阶段打造的灵感聚合与日报原型仓库。

当前版本聚焦在这条最小链路：

`自动采集 -> 内容整理 -> 日报生成 -> 网页浏览 -> 收藏反馈`

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
  - 原始候选内容转日报 JSON 的脚本骨架
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
  - item_structuring 的占位运行器（heuristic；后续替换为 Minimax 实际调用）
- `scripts/run_daily_summary.py`
  - daily_summary 的占位运行器（heuristic；后续替换为 Minimax 实际调用）

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

```bash
python scripts/generate_report.py
```

默认输入：

- `data-samples/raw-candidates.json`

默认输出：

- `data-samples/generated-report.json`

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
