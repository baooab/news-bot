# 科技资讯

每天早上 **6 点半**（北京时间）自动采集权威新闻源，AI 生成摘要，产物以 **JSON 数据**输出，并由 **Bulma** 网页承载渲染，通过 **GitHub Pages** 发布。

每日精选 **8 条科技 + 4 条民生社会**（共 12 条）。

## 在线访问

部署完成后访问：

```
https://<你的用户名>.github.io/<仓库名>/
```

例如仓库名为 `news-bot`：`https://yourname.github.io/news-bot/`

| 页面 | 说明 |
|------|------|
| `/`（`index.html`） | 首页，仅展示**当月**科技资讯 |
| `/archive.html` | 历史归档，按月份筛选、关键词检索往期简报 |
| `/brief.html?date=YYYY-MM-DD` | 简报详情（可编辑、复制公众号版） |

## 数据源

| 类型 | 来源 | 方式 |
|------|------|------|
| 综合 | 澎湃新闻 | JSON API |
| 民生社会 | 中新网（社会频道） | RSS |
| 科技 | IT之家 | RSS |
| 商业 | 36氪 | RSS |
| 科技 | Solidot | RSS |
| 科技 | 凤凰科技 | JSONP |

> 如需增减来源，编辑 `config.py` 的 `SOURCES`。

## 工作流程

```
6 大数据源采集（原始数据存档）
→ 日历过滤（今天 + 昨天）→ 去重 → 质量过滤 → 话题排序 / 科技打分
→ 精选 8 科技 + 4 民生社会
→ AI 摘要增强 → 无效条目过滤/递补 → 构建简报 JSON → 提交到仓库
→ GitHub Pages 自动部署（含首页、归档页、详情页）
```

## 输出产物

**JSON 数据（提交到仓库）**

- `data/briefs/YYYY-MM-DD.json` — 精选简报（8+4 条 + 标题 headline + 农历日期）
- `data/raw/YYYY-MM-DD.json` — 全部原始数据，按来源分组
- `data/index.json` — 简报索引（供首页 / 归档页读取）

**静态网页（GitHub Pages 发布）**

- `index.html` — 首页，只列出当月简报
- `archive.html` — 归档页，浏览与查询历史简报
- `brief.html?date=YYYY-MM-DD` — 简报详情（可编辑、复制公众号版）
- `404.html` — 未找到页面时回首页

## 部署到 GitHub Pages

### 1. Fork / 推送仓库

将本仓库推送到 GitHub（默认分支 `main`）。

### 2. 启用 GitHub Pages（GitHub Actions 方式）

1. 打开仓库 **Settings → Pages**
2. **Build and deployment → Source** 选择 **GitHub Actions**
3. 保存后，推送代码或手动运行 **Deploy GitHub Pages** workflow

首次部署可在 **Actions** 页选择 `Deploy GitHub Pages` → **Run workflow**。

`pages.yml` 会将 `index.html`、`archive.html`、`brief.html`、`404.html` 与 `data/` 一并发布。

### 3. 启用每日自动生成（可选）

1. **Settings → Actions → General** → 允许 Actions 运行
2. **Settings → Secrets → Actions** 添加 AI 相关 Secret（见下表）
3. 每日北京时间 **06:30** 自动运行 `Daily News Brief`，或手动触发

未配置 AI Secret 时仍可运行，仅跳过 AI 摘要。**只需配置 `AI_API_KEY` 即可**（URL / MODEL 有默认值）。

| Secret | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `AI_API_KEY` | ✅ | — | 你的 API Key |
| `AI_API_URL` | | `https://api.deepseek.com/v1/chat/completions` | OpenAI 兼容接口地址 |
| `AI_MODEL` | | `deepseek-v4-flash` | 模型名 |

本地也可复制 `.env.example` 为 `.env` 填写上述变量（`.env` 已在 `.gitignore`，不会提交）。

### 4. 本地开发

```bash
pip install -r requirements.txt
python main.py
python -m http.server 8000
# 浏览器打开 http://localhost:8000/
# 归档页：http://localhost:8000/archive.html
```

> 本地预览须通过 HTTP 服务器访问（`file://` 无法 fetch JSON）。

## 简报 JSON 结构

```jsonc
{
  "series": "科技资讯",
  "headline": "当日标题（AI / 规则生成）",
  "date": "2026-08-06",
  "date_display": "2026年08月06日 星期四 农历六月廿四",
  "weekday": "星期四",
  "lunar": "农历六月廿四",
  "overview": "",
  "generated_at": "2026-08-06 07:03:50",
  "count": 12,
  "tech_quota": 8,
  "general_quota": 4,
  "sources": ["IT之家", "Solidot", "中新网", "澎湃"],
  "items": [
    {
      "index": 1,
      "title": "原始标题",
      "summary": "AI 一句话摘要",
      "text": "展示文本（有摘要用摘要，否则用标题）",
      "source": "Solidot",
      "link": "https://...",
      "topic": "other",
      "section": "tech",       // tech | general
      "tech_score": 56,
      "pub_time": 1785917558.0,
      "pub_display": "08-05 16:12"
    }
  ]
}
```

## 简报格式

- **系列名**：科技资讯
- **标题**：当日 headline（概括当日要点）
- **日期**：公历 + 星期 + 农历
- **正文**：前 8 条科技 + 后 4 条民生社会，扁平编号
- **详情页**：可编辑条目、切换原始池、复制公众号版

## 项目结构

```
├── .github/workflows/
│   ├── daily-news.yml        # 每日采集 + 提交 JSON（06:30 北京时间）
│   └── pages.yml             # GitHub Pages 部署
├── data/
│   ├── index.json
│   ├── briefs/
│   └── raw/
├── config.py                 # 数据源、配额、过滤与 AI 配置
├── fetchers.py
├── quality_filter.py
├── tech_score.py             # 科技相关度打分
├── brief_style.py
├── tech_brief_style.py
├── ai_summary.py
├── formatter.py
├── main.py
├── index.html                # 首页（当月）
├── archive.html              # 历史归档
├── brief.html                # 简报详情
├── 404.html
├── .env.example
├── .nojekyll
└── requirements.txt
```

## 自定义

- **科技 / 民生条数**：`config.py` → `TECH_QUOTA` / `GENERAL_QUOTA`（默认 8 + 4）
- **日历过滤**：`RECENT_CALENDAR_DAYS`（默认 `2`，即今天 + 昨天；`0` 关闭）
- **来源限制**：`MAX_PER_SOURCE`
- **排序优先级**：`SORT_KEYWORDS` / `SORT_TOPICS`
- **科技打分**：`TECH_KEYWORDS` / `TECH_SOURCE_SCORES`
