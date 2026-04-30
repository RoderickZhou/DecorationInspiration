# DecorationInspiration

一个围绕家庭装修早期决策阶段打造的灵感聚合与日报原型仓库。

当前版本聚焦在这条最小链路：

`自动采集 -> 内容整理 -> 日报生成 -> 网页浏览 -> 收藏反馈`

## 当前内容

- `demo/renovation-daily-demo.html`
  - 数据驱动版装修灵感日报 Demo
  - 页面会读取 `sample-report.json` 动态渲染
  - 点击喜欢、收藏、不喜欢会记录到浏览器本地，模拟反馈回流
- `demo/renovation-planner-demo.html`
  - 更偏全局产品视角的装修决策助手假 Demo
- `docs/renovation-daily-prd.md`
  - 第一版产品需求文档
- `data-samples/sample-report.json`
  - 可直接喂给前端的日报数据样例
- `data-samples/sample-actions.jsonl`
  - 用户反馈行为样例

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
  demo/
    renovation-daily-demo.html
    renovation-planner-demo.html
  docs/
    renovation-daily-prd.md
  data-samples/
    sample-report.json
    sample-actions.jsonl
```

## 当前原型能力

- 多来源装修灵感内容的日报展示结构
- 用户画像驱动的推荐方向表达
- 可直接供前端开发使用的数据样例
- 收藏 / 喜欢 / 不喜欢 / 查看原文的前端交互模拟

## 下一步建议

- 增加真实采集器输出的原始数据样例
- 增加 Minimax 输入输出规范
- 增加日报生成脚本
- 增加收藏夹页和详情页

## 说明

当前仓库以原型、文档和样例数据为主，目的是先把产品形态、数据结构和前端交互链路跑通，再逐步接入真实采集与模型处理能力。
