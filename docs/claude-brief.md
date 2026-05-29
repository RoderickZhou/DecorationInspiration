# Claude 接入说明（项目概览与进度）

## 1. 项目地址

- 本地项目目录：`C:\Users\Administrator\Documents\DecorationInspiration`
- GitHub 仓库：`https://github.com/RoderickZhou/DecorationInspiration`

## 2. 项目目标

这是一个围绕家庭装修早期决策阶段打造的“灵感聚合 + 日报推荐 + 反馈回流”原型工程。

主链路目标：

`自动采集 -> 内容整理 -> 日报生成 -> 网页浏览 -> 收藏反馈`

当前阶段优先把“产品形态 + 数据契约 + 可跑通管线”做扎实，再逐步接入真实采集与 Minimax 实际调用。

## 3. 目标用户画像（当前默认）

- 房屋建筑面积约 132 平，到手面积约 98 平
- 四口常住
- 大儿子 7 岁，小儿子 8 个月
- 纯自住长期居住
- 高频做饭
- 重点关注：儿童房、客厅功能角、厨房与餐边柜、全屋收纳、低维护

该画像以 `data/user_profile.v1.json` 为准，并会参与后续适配度判断与解释。

## 4. 当前仓库结构（核心目录）

```text
DecorationInspiration/
  README.md
  demo/
  web/
  data/
  data-samples/
  schemas/
  scripts/
  prompts/
  docs/
```

## 5. 已开发的内容（按模块）

### 5.1 前端展示

目标：把 `report.json` 以“2-3 分钟可浏览”的日报形式展示，并提供反馈入口。

- 静态 Demo（纯 HTML）
  - `demo/renovation-daily-demo.html`
    - 默认读取 `data-samples/sample-report.json`
    - 支持 `?data=...` 指定 report.json 路径
    - 用户操作（喜欢/收藏/不喜欢）写入浏览器本地存储，用于模拟反馈回流
  - `demo/renovation-planner-demo.html`
    - 更偏全局产品视角的“装修决策助手”概念页面

- 工程化前端（React + Vite）
  - `web/`
    - 当前支持：发现页 / 收藏夹 / 筛选器 / 详情区 / 本地反馈导出
    - 现阶段仍主要用于验证“数据结构可渲染 + 交互可记录”

### 5.2 数据样例与数据契约（Schema）

目标：在真实采集器尚未接入前，先把“输入/输出结构”固定下来，保证前端、脚本、模型之间契约稳定。

- 样例数据（用于前端与脚本测试）
  - `data-samples/sample-raw-items.jsonl`：采集器原始输出样例（raw collector）
  - `data-samples/sample-candidates.jsonl`：候选内容样例（candidates）
  - `data-samples/sample-report.json`：日报样例（report.json）
  - `data-samples/sample-actions.jsonl`：用户反馈样例（actions.jsonl）

- JSON Schema（稳定契约）
  - `schemas/raw_collector_item.schema.json`
  - `schemas/candidate.schema.json`
  - `schemas/report.schema.json`
  - `schemas/minimax_item_structuring.schema.json`
  - `schemas/minimax_daily_summary.schema.json`

### 5.3 数据处理管线（脚本）

目标：把 raw/candidates 变成 report.json，并给 Minimax 留出“结构化整理”和“日报汇总”两个可替换节点。

- 关键脚本
  - `scripts/convert_raw_to_candidates.py`
    - raw collector JSONL -> candidates JSONL
  - `scripts/generate_daily_report.py`
    - candidates JSONL -> report.json
    - 当前可用规则/占位逻辑模拟 Minimax 输出，保证端到端可跑通
  - `scripts/prepare_minimax_item_inputs.py`
    - candidates -> item_structuring 输入（JSONL）
  - `scripts/prepare_minimax_daily_summary_input.py`
    - report/items -> daily_summary 输入（JSON）
  - `scripts/run_item_structuring.py` / `scripts/run_daily_summary.py`
    - 目前是 heuristic 占位运行器，后续替换成 Minimax 实际调用
  - `scripts/validate_candidates.py` / `scripts/validate_report_basic.py`
    - 无依赖基础校验（适合 CI 或本地自检）
  - `scripts/merge_actions_jsonl.py`
    - 合并/去重/排序多份 actions.jsonl，支持多电脑协作

## 6. 当前进度结论（做到哪一步）

已完成：

- 产品形态（日报浏览 + 收藏反馈）的可运行原型
- `report.json` / `actions.jsonl` / candidates/raw 的数据结构固化（含 Schema）
- raw -> candidates -> report 的端到端可运行管线（当前 Minimax 以 heuristic 占位）
- Minimax IO 的输入输出规范文档与 prompts 草案

未完成（下一阶段工作）：

- 真实采集器（小红书/好好住/一兜糖/Pinterest/花瓣等）的稳定数据落地
- Minimax 实际 API 调用与缓存、重试、降级
- 使用 actions.jsonl 的真实反馈学习（把收藏/不喜欢纳入次日报告排序）
- Web 前端从“本地样例读取”升级为“读取 data/reports 或 API 返回”

## 7. 推荐 Claude 的阅读顺序

1. `README.md`
2. `docs/hand-off.md`
3. `docs/pipeline.md`
4. `docs/minimax-io.md`
5. `docs/renovation-daily-prd.md`
6. `schemas/report.schema.json` 与 `schemas/candidate.schema.json`
7. `scripts/generate_daily_report.py` 与 `scripts/convert_raw_to_candidates.py`
8. `demo/renovation-daily-demo.html` 与 `web/`

## 8. 本地快速复现（验证链路）

### 8.1 跑通 raw -> candidates -> report

```bash
python scripts/convert_raw_to_candidates.py --input data-samples/sample-raw-items.jsonl --output data/raw/candidates.from_raw.jsonl
python scripts/generate_daily_report.py --date 2026-04-30 --input data/raw/candidates.from_raw.jsonl --output data/reports/2026-04-30/report.from_raw.json --actions data-samples/sample-actions.jsonl
```

### 8.2 预览日报 Demo（静态）

```bash
python -m http.server 8008
```

```text
http://localhost:8008/demo/renovation-daily-demo.html
http://localhost:8008/demo/renovation-daily-demo.html?data=../data/reports/2026-04-30/report.from_raw.json
```

### 8.3 启动 React 前端

```bash
cd web
npm install
npm run dev
```

