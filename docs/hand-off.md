# 装修灵感日报项目交接说明

## 1. 项目定位

这是一个围绕家庭装修早期决策阶段打造的灵感聚合与日报原型项目。

当前版本聚焦这条最小链路：

`自动采集 -> 内容整理 -> 日报生成 -> 网页浏览 -> 收藏反馈`

目标不是一开始就做完整装修平台，而是先做一个每天只花 2-3 分钟就能浏览的“装修灵感日报”，帮助用户逐步建立判断力。

---

## 2. 当前用户画像

这个项目当前是围绕以下真实场景设计的：

- 房屋建筑面积约 132 平，到手面积约 98 平
- 四口常住
- 大儿子 7 岁，小儿子 8 个月
- 纯自住，长期居住，不考虑换房
- 倾向 3 室布局
- 高频做饭，厨房与餐边柜优先级高
- 全屋收纳都重要
- 希望在客厅保留自己的功能角
- 当前对装修认知较少，需要通过大量案例图片建立判断力
- 计划 2028 年初开始装修

这个画像直接影响了推荐逻辑、标签体系和日报内容筛选方向。

---

## 3. 当前仓库

- GitHub 仓库：`https://github.com/RoderickZhou/DecorationInspiration`
- 当前本地目录：`C:\Users\Administrator\Documents\DecorationInspiration`
- 已成功推送到远程 `main`
- 最近一次已知成功提交：
  - `ccc8957`
  - commit message: `Add renovation inspiration demos, PRD, and sample data`

如果在另一台电脑继续工作，建议直接克隆仓库：

```bash
git clone https://github.com/RoderickZhou/DecorationInspiration.git
```

---

## 4. 当前仓库结构

```text
DecorationInspiration/
  .gitignore
  README.md
  demo/
    renovation-daily-demo.html
    renovation-planner-demo.html
  docs/
    renovation-daily-prd.md
  data-samples/
    sample-report.json
    sample-actions.jsonl
```

---

## 5. 每个文件的作用

### 根目录

- `README.md`
  - 仓库说明
  - 概述当前原型、目录结构、目标用户场景、后续方向

- `.gitignore`
  - 忽略系统垃圾文件、编辑器目录、日志和导出的本地反馈文件

### demo

- `demo/renovation-planner-demo.html`
  - 偏“全局产品形态”的装修决策助手静态假 Demo
  - 用于展示产品范围、核心模块和产品分期

- `demo/renovation-daily-demo.html`
  - 当前最重要的页面
  - 已改造成**数据驱动版 Demo**
  - 会读取 `sample-report.json` 动态渲染日报
  - 支持用户点击：
    - 喜欢
    - 收藏
    - 不喜欢
    - 查看原文
  - 用户动作会先写入浏览器 `localStorage`，模拟未来 `actions.jsonl` 回流
  - 页面提供：
    - 导出反馈 JSONL
    - 清空本地反馈

### docs

- `docs/renovation-daily-prd.md`
  - 第一版产品需求文档
  - 包含：
    - 产品定位
    - 用户画像
    - 第一版功能范围
    - 推荐逻辑
    - 标签体系
    - 数据结构
    - 技术方案建议

### data-samples

- `data-samples/sample-report.json`
  - 可直接喂给前端渲染的日报样例数据
  - 包含：
    - 用户画像快照
    - 来源统计
    - 今日主题
    - 日报摘要
    - 推荐卡片
    - 近期反馈偏好

- `data-samples/sample-actions.jsonl`
  - 用户反馈行为样例
  - 用于模拟：
    - like
    - favorite
    - dislike
    - skip
    - open_source

---

## 6. 当前已经完成的工作

### 6.1 产品方向已经明确

当前结论不是做单一“小红书爬虫”，而是做：

**装修灵感聚合 + 个性化日报推荐 + 反馈学习**

多平台只是来源，不是产品本体。

### 6.2 核心产品结构已完成原型化

已经形成两层原型：

- 全局产品假 Demo
- 每日灵感日报 Demo

### 6.3 第一版 PRD 已完成

PRD 已明确：

- 第一版优先做：
  - 自动采集
  - 去重与初筛
  - Minimax 摘要、标签、适配度判断
  - 日报 HTML 页面生成
  - 收藏/喜欢/不喜欢/跳过反馈

- 第一版暂不做：
  - 完整装修公司评分系统
  - 完整比价系统
  - 合同分析
  - 云端多端同步
  - 完整对话式装修顾问

### 6.4 数据结构已落地

已经确定并产出了第一版可用结构：

- `report.json`
- `actions.jsonl`

并且日报页面已经切换成读取 `sample-report.json` 的方式运行。

### 6.5 GitHub 仓库已创建并推送

仓库已经不是空白状态，而是有：

- 文档
- Demo
- 样例数据
- README

---

## 7. 当前关键产品决策

这些是继续开发时不要轻易推翻的关键结论。

### 7.1 主流程建议

主系统应该是：

`采集器 -> 规则清洗 -> Minimax 结构化整理 -> report.json -> 前端日报页 -> 用户反馈 -> 次日更准`

### 7.2 Hermes 不应站在主链路中央

当前判断是：

- 日常自动运行的主链路，更适合程序化管线 + Minimax
- Hermes 更适合辅助位，例如：
  - 试验新站点
  - 帮忙整理专题
  - 做探索性工作

不要把 Hermes 放在“每天都必须经过”的主流程中心。

### 7.3 Minimax 的职责已明确

Minimax 在第一版里更适合做：

- 内容审核
- 摘要生成
- 标签提取
- 适配度判断
- 风险点提炼
- 每日报告总结

不建议让 Minimax 直接负责采集。

### 7.4 来源优先级已明确

第一优先级：

- 小红书
- 好好住
- 一兜糖
- Pinterest
- 花瓣

第二优先级：

- Houzz
- Dezeen
- ArchDaily
- gooood

第三优先级：

- Behance
- Dribbble
- 拓者设计吧
- 如室
- AD

### 7.5 当前产品阶段重点

现在最重要的不是“覆盖所有平台”，而是把下面这条链路跑顺：

`自动采集 -> 自动筛选 -> 自动摘要 -> 生成日报 -> 用户反馈 -> 次日更准`

---

## 8. 当前页面运行方式

### 8.1 推荐打开方式

在仓库根目录下启动静态服务，例如：

```bash
python -m http.server 8123
```

然后打开：

```text
http://localhost:8123/demo/renovation-daily-demo.html
```

### 8.2 为什么不能只双击 HTML

`renovation-daily-demo.html` 使用 `fetch()` 读取 JSON 文件。

如果直接用 `file://` 打开，很可能被浏览器拦截本地读取。

所以应优先通过本地静态服务打开。

### 8.3 当前动态页面行为

页面会读取：

- `../data-samples/sample-report.json`

页面里的用户动作不会直接改写本地文件，因为纯静态页面没有写文件权限。

当前采用的是：

- 动作先写入浏览器 `localStorage`
- 支持导出 JSONL

这是为了模拟未来真实系统里的：

- `actions.jsonl`

---

## 9. 当前已知限制

### 9.1 还没有真实采集器

目前仓库里还没有真正的多平台采集脚本，只是完成了：

- 产品形态
- 数据结构
- 页面原型
- 样例数据

### 9.2 还没有 Minimax 输入输出规范文件

虽然职责已经定义清楚，但仓库里还没有专门的：

- prompt 文件
- 输入输出 schema 文档
- 调用脚本

### 9.3 还没有日报生成脚本

当前 `sample-report.json` 是人工生成的样例，不是脚本自动产出。

### 9.4 `reply-to-hermes.md` 没进仓库

之前曾生成过一个给 Hermes 的回复文档，但当前原始文件不在 `Documents` 下，因此没有进入仓库。

这不影响主项目。

---

## 10. 最推荐的下一步

如果在另一台电脑继续，最建议按以下顺序推进。

### 第一步：搭第一版项目骨架

建议新增：

```text
scripts/
prompts/
src/ 或 web/
```

其中：

- `scripts/`
  - 放数据转换、日报生成、导入导出脚本
- `prompts/`
  - 放 Minimax 的摘要、标签、适配度判断 prompt
- `web/` 或前端目录
  - 放真正前端工程，而不是单个 HTML 文件

### 第二步：补 Minimax 处理入口规范

建议新增一份明确文档：

- 输入原始候选内容长什么样
- Minimax 输出结构化条目长什么样
- 每个字段的含义是什么

### 第三步：做日报生成脚本

先不接真实爬虫，也可以先做：

- `raw candidates -> normalized items -> report.json`

只要日报生成脚本跑通，后面换任何采集器都能接进来。

### 第四步：将前端 Demo 工程化

从静态 HTML 迁移到真正前端工程，例如：

- `React`
- `Next.js`

但这是在脚本链路开始稳定之后再做。

---

## 11. 建议另一台电脑上的 AI 先读哪些文件

如果要让新的 AI 接手后尽量和当前状态保持一致，建议按这个顺序读取：

### 必读顺序

1. 本文档：
   - `装修项目交接说明.md`
2. 仓库根说明：
   - `README.md`
3. 产品需求：
   - `docs/renovation-daily-prd.md`
4. 数据结构样例：
   - `data-samples/sample-report.json`
   - `data-samples/sample-actions.jsonl`
5. 页面原型：
   - `demo/renovation-daily-demo.html`
   - `demo/renovation-planner-demo.html`

### AI 接手时建议说明

可以把下面这段话原样给新的 AI：

```text
请先阅读桌面的《装修项目交接说明.md》，再阅读仓库 README、PRD、sample-report.json、sample-actions.jsonl 和两个 demo 页面。这个项目当前目标是做“装修灵感日报”，主链路是 自动采集 -> Minimax 结构化整理 -> report.json -> 前端日报页 -> 用户反馈。当前最推荐的下一步是：搭第一版项目骨架、补 Minimax 输入输出规范、做日报生成脚本。请在不推翻现有产品方向和数据结构的前提下继续推进。
```

---

## 12. 当前 Git 和认证状态说明

这是当前电脑上的状态，仅供参考：

- `gh auth status` 可用
- GitHub 当前走 `https`
- `ssh -T git@github.com` 不可用，报 `Permission denied (publickey)`

也就是说，这台电脑当前是用：

- GitHub CLI 登录态 + HTTPS 推送

完成的仓库上传。

另一台电脑如果要继续推送，可以：

- 重新登录 `gh`
- 或自己配置 SSH

---

## 13. 最简结论

这个项目现在不是空想阶段，而是已经具备：

- GitHub 仓库
- 清晰的产品方向
- 第一版 PRD
- 两个 Demo
- 可直接供前端使用的样例数据
- 初步反馈回流模拟

当前最值得继续做的是：

**把“样例驱动的原型”推进成“可运行的数据处理工程”。**

最优先顺序仍然是：

`项目骨架 -> Minimax 规范 -> 日报生成脚本 -> 真实采集器`
