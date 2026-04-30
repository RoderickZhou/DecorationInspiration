# 数据处理管线（第一版）

## 目标

把“采集器输出的候选内容”转换为“前端可直接渲染的日报 JSON”，并保留用户反馈回流的入口。

主链路：

`raw collector (jsonl) -> candidates (jsonl) -> report.json -> demo 页面浏览 -> actions.jsonl`

对应文件与脚本：

- raw collector：`data-samples/sample-raw-items.jsonl`
- raw -> candidates：`scripts/convert_raw_to_candidates.py`
- candidates：`data-samples/sample-candidates.jsonl`
- candidates -> report：`scripts/generate_daily_report.py`
- candidates -> item_structuring output：`scripts/run_item_structuring.py`（占位）
- report/items -> daily_summary output：`scripts/run_daily_summary.py`（占位）

## 输入：candidates JSONL

文件：`data-samples/sample-candidates.jsonl`

每行一个 JSON 对象，推荐字段：

- platform：来源平台（如 xiaohongshu / haohaozhu / yidoutang / pinterest / huaban / houzz）
- title：标题
- source_url：原文链接（用于去重与打开原文）
- cover_url：封面图（demo 需要）
- image_urls：图片数组
- author：作者
- published_at：发布时间（ISO 8601）
- engagement：互动数据（likes / favorites / comments）
- text：正文或摘要（用于打标签与适配度判断）

## 输入：raw collector JSONL（建议）

文件：`data-samples/sample-raw-items.jsonl`

建议 schema：`schemas/raw_collector_item.schema.json`

raw -> candidates 的最小转换：

```bash
python scripts/convert_raw_to_candidates.py --input data-samples/sample-raw-items.jsonl --output data/raw/candidates.from_raw.jsonl
```

## 输出：report.json

脚本会生成包含以下顶层字段的 JSON：

- report_date / generated_at / report_id
- user_profile_version / user_profile_snapshot
- source_stats
- today_focus
- summary
- daily_digest
- items
- feedback_summary

示例输出位置：

- `data/reports/2026-04-30/report.json`

## 脚本：生成日报

```bash
python scripts/generate_daily_report.py --date 2026-04-30 --input data-samples/sample-candidates.jsonl --output data/reports/2026-04-30/report.json --actions data-samples/sample-actions.jsonl
```

说明：

- 当前版本用规则/占位逻辑模拟 Minimax 的“摘要、标签、适配度、风险点、日报总结”
- 后续接入 Minimax 时，可以保持 report.json 结构不变，仅替换生成逻辑

如果需要把“结构化整理”和“日报汇总”作为独立工序（便于替换为真实 Minimax 调用），可以使用：

```bash
python scripts/run_item_structuring.py --mode heuristic --input data/raw/minimax_item_inputs.jsonl --output data/normalized/item_structuring.outputs.jsonl
python scripts/run_daily_summary.py --mode heuristic --input data/raw/minimax_daily_summary_input.json --output data/normalized/daily_summary.output.json
python scripts/generate_daily_report.py --date 2026-04-30 --input data/raw/candidates.from_raw.jsonl --output data/reports/2026-04-30/report.with_structured.json --structured-items data/normalized/item_structuring.outputs.jsonl --daily-summary data/normalized/daily_summary.output.json
```

## 预览：日报 Demo

启动静态服务：

```bash
python -m http.server 8008
```

打开默认样例日报：

```text
http://localhost:8008/demo/renovation-daily-demo.html
```

打开自定义日报：

```text
http://localhost:8008/demo/renovation-daily-demo.html?data=../data/reports/2026-04-30/report.json
```
