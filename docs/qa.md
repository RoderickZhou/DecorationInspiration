# 自检与协作（本地）

## 1. 端到端跑通（raw -> candidates -> report）

```bash
python scripts/convert_raw_to_candidates.py --input data-samples/sample-raw-items.jsonl --output data/raw/candidates.from_raw.jsonl
python scripts/generate_daily_report.py --date 2026-04-30 --input data/raw/candidates.from_raw.jsonl --output data/reports/2026-04-30/report.from_raw.json --actions data-samples/sample-actions.jsonl
```

预览：

```text
http://localhost:8008/demo/renovation-daily-demo.html?data=../data/reports/2026-04-30/report.from_raw.json
```

## 2. 基础校验（无依赖）

校验 candidates：

```bash
python scripts/validate_candidates.py --input data/raw/candidates.from_raw.jsonl
```

校验 report：

```bash
python scripts/validate_report_basic.py --input data/reports/2026-04-30/report.from_raw.json
```

## 3. 生成 Minimax 输入

批量 item_structuring（JSONL）：

```bash
python scripts/prepare_minimax_item_inputs.py --candidates data/raw/candidates.from_raw.jsonl --output data/raw/minimax_item_inputs.jsonl
```

单次 daily_summary（JSON）：

```bash
python scripts/prepare_minimax_daily_summary_input.py --items data/reports/2026-04-30/report.from_raw.json --output data/raw/minimax_daily_summary_input.json
```

## 3.1 运行占位的 Minimax 产出（heuristic）

```bash
python scripts/run_item_structuring.py --mode heuristic --input data/raw/minimax_item_inputs.jsonl --output data/normalized/item_structuring.outputs.jsonl
python scripts/run_daily_summary.py --mode heuristic --input data/raw/minimax_daily_summary_input.json --output data/normalized/daily_summary.output.json
```

## 3.2 运行真实 Minimax（需配置环境变量）

先在项目根放 `.env` 或导出 `MINIMAX_API_KEY` / `MINIMAX_BASE_URL` / `MINIMAX_MODEL`（详情见 docs/minimax-io.md 2.5 节）。

```bash
python scripts/run_item_structuring.py --mode minimax --input data/raw/minimax_item_inputs.jsonl --output data/normalized/item_structuring.outputs.jsonl --concurrency 4
python scripts/run_daily_summary.py --mode minimax --input data/raw/minimax_daily_summary_input.json --output data/normalized/daily_summary.output.json
```

如果 key 未配置或 API 失败，会自动降级到 heuristic，链路不断；行内 `_source` 字段标注每条来源（minimax / cache / heuristic_fallback）。

把产出回注到 report.json：

```bash
python scripts/generate_daily_report.py --date 2026-04-30 --input data/raw/candidates.from_raw.jsonl --output data/reports/2026-04-30/report.with_structured.json --structured-items data/normalized/item_structuring.outputs.jsonl --daily-summary data/normalized/daily_summary.output.json --actions data-samples/sample-actions.jsonl
```

预览：

```text
http://localhost:8008/demo/renovation-daily-demo.html?data=../data/reports/2026-04-30/report.with_structured.json
```

## 4. 多电脑合并 actions

```bash
python scripts/merge_actions_jsonl.py --inputs actions_a.jsonl actions_b.jsonl --output data/actions/merged.actions.jsonl
```
