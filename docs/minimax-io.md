# Minimax 输入输出规范（v1）

## 目标

在不改变现有 `report.json` 结构的前提下，把 Minimax 放到“结构化整理”和“日报汇总”两个位置：

- item_structuring：单条候选内容 -> 结构化字段（summary/tags/fit/risk/why）
- daily_summary：一组结构化条目 -> 今日主题与摘要（today_focus/summary/daily_digest）

## 0. 基础数据

### user_profile_snapshot

来自：`data/user_profile.v1.json` 的 `user_profile_snapshot`。

在 Minimax 推理时会一并提供，用于“适配度判断”和“解释原因”。

## 1) item_structuring

### 输入（JSON）

schema：`schemas/minimax_item_structuring.schema.json`

```json
{
  "schema_version": "v1",
  "task": "item_structuring",
  "user_profile_snapshot": { },
  "candidate": { }
}
```

其中 `candidate` 每行来源建议遵循：`schemas/candidate.schema.json`。

生成批量输入（JSONL）：

```bash
python scripts/prepare_minimax_item_inputs.py --candidates data-samples/sample-candidates.jsonl --output data/raw/minimax_item_inputs.jsonl
```

占位运行（先用 heuristic 模拟，后续替换为 Minimax 实际调用）：

```bash
python scripts/run_item_structuring.py --mode heuristic --input data/raw/minimax_item_inputs.jsonl --output data/normalized/item_structuring.outputs.jsonl
```

### 输出（JSON）

Minimax 只输出一个 JSON 对象（不要输出额外文本），把结果放在 `output` 字段：

```json
{
  "schema_version": "v1",
  "task": "item_structuring",
  "output": {
    "summary": "一句话摘要，强调可落地的信息",
    "tags": {
      "style": ["原木", "现代简约"],
      "space": ["儿童房", "厨房"],
      "family": ["二孩家庭", "长期自住"],
      "features": ["客厅功能角", "收纳强", "低维护"]
    },
    "fit_score": 0.91,
    "fit_reason": "为什么对当前用户匹配，用用户画像里的需求点解释",
    "risk_notes": ["注意点 1", "注意点 2"],
    "why_selected": "为什么值得进日报（与当天主题/核心需求的关系）"
  }
}
```

约束：

- `fit_score`：0-1，保留两位小数
- `risk_notes`：至少 1 条
- 标签必须分组，且每组必须存在（为空数组也要给出）

## 2) daily_summary

### 输入（JSON）

schema：`schemas/minimax_daily_summary.schema.json`

```json
{
  "schema_version": "v1",
  "task": "daily_summary",
  "user_profile_snapshot": { },
  "items": [ ]
}
```

其中 `items` 是已结构化条目（至少包含 tags/fit_score/summary/risk_notes 等）。

生成单次输入（JSON）：

```bash
python scripts/prepare_minimax_daily_summary_input.py --items data/reports/2026-04-30/report.json --output data/raw/minimax_daily_summary_input.json
```

占位运行（先用 heuristic 模拟，后续替换为 Minimax 实际调用）：

```bash
python scripts/run_daily_summary.py --mode heuristic --input data/raw/minimax_daily_summary_input.json --output data/normalized/daily_summary.output.json
```

### 输出（JSON）

同样只输出一个 JSON 对象（不要输出额外文本），把结果放在 `output` 字段：

```json
{
  "schema_version": "v1",
  "task": "daily_summary",
  "output": {
    "today_focus": ["主题 1", "主题 2", "主题 3"],
    "summary": {
      "headline": "一句话总结今天推荐的方向",
      "highlights": ["亮点 1", "亮点 2", "亮点 3"],
      "question_of_the_day": "当天关键问题",
      "fit_direction": ["方向 1", "方向 2", "方向 3"]
    },
    "daily_digest": {
      "estimated_read_minutes": 3,
      "recommended_browse_order": ["儿童房", "客厅功能角", "厨房与餐边柜", "风格拓展"],
      "top_tags": ["二孩家庭", "原木", "收纳强", "餐边柜"]
    }
  }
}
```

## 3) 与 report.json 的关系

最终 `report.json` 的字段来源建议如下：

- `items[*].summary/tags/fit_score/fit_reason/risk_notes/why_selected`：来自 item_structuring
- `today_focus/summary/daily_digest`：来自 daily_summary

`report.json` 的整体结构建议遵循：`schemas/report.schema.json`。
