# 每日资讯简报

每天早 7 点自动采集权威新闻源，AI 生成摘要，产物以 **JSON 数据**输出，并由 **Bulma** 网页承载渲染，通过 **GitHub Pages** 发布。

## 在线访问

部署完成后访问：

```
https://<你的用户名>.github.io/<仓库名>/
```

例如仓库名为 `news-bot`：`https://yourname.github.io/news-bot/`

## 数据源

| 类型 | 来源 | 方式 |
|------|------|------|
| 综合 | 澎湃新闻 | JSON API |
| 综合 | 联合早报 | RSS |
| 科技 | IT之家 | RSS |
| 商业 | 36氪 | RSS |

> 如需增减来源，编辑 `config.py` 的 `SOURCES`。

## 工作流程

```
4 大数据源采集（原始数据存档）
→ 24h 过滤 → 去重 → 质量过滤 → 话题排序 → 精选 12 条
→ AI 摘要增强 → 无效条目过滤/递补 → 构建简报 JSON → 提交到仓库
→ GitHub Pages 自动部署
```

## 输出产物

**JSON 数据（提交到仓库）**

- `data/briefs/YYYY-MM-DD.json` — 精选简报（12 条 + 微语 + 农历日期）
- `data/raw/YYYY-MM-DD.json` — 全部原始数据，按来源分组
- `data/index.json` — 简报索引（供首页读取）

**静态网页（GitHub Pages 发布）**

- `index.html` — 首页，列出所有简报
- `brief.html?date=YYYY-MM-DD` — 简报详情（可编辑、复制公众号版）
- `quotes.json` — 微语库（详情页点击切换）

## 部署到 GitHub Pages

### 1. Fork / 推送仓库

将本仓库推送到 GitHub（默认分支 `main`）。

### 2. 启用 GitHub Pages（GitHub Actions 方式）

1. 打开仓库 **Settings → Pages**
2. **Build and deployment → Source** 选择 **GitHub Actions**
3. 保存后，推送代码或手动运行 **Deploy GitHub Pages** workflow

首次部署可在 **Actions** 页选择 `Deploy GitHub Pages` → **Run workflow**。

### 3. 启用每日自动生成（可选）

1. **Settings → Actions → General** → 允许 Actions 运行
2. **Settings → Secrets → Actions** 添加 AI 相关 Secret（见下表）
3. 每日北京时间 07:00 自动运行 `Daily News Brief`，或手动触发

| Secret | 值 | 说明 |
|--------|---|------|
| `AI_API_URL` | `https://api.deepseek.com/v1/chat/completions` | API 地址（OpenAI 兼容） |
| `AI_API_KEY` | `sk-xxxxxxxx` | 你的 API Key |
| `AI_MODEL` | `deepseek-chat` | 模型名 |

未配置 AI Secret 时仍可运行，仅跳过 AI 摘要增强。

### 4. 本地开发

```bash
pip install -r requirements.txt
python main.py
python -m http.server 8000
# 浏览器打开 http://localhost:8000/
```

> 本地预览须通过 HTTP 服务器访问（`file://` 无法 fetch JSON）。

## 简报 JSON 结构

```jsonc
{
  "date": "2026-07-11",
  "date_display": "2026年07月11日 星期六 农历五月廿七",
  "overview": "",
  "quote": "每日微语",
  "count": 12,
  "sources": ["澎湃", "联合早报", "IT之家", "36氪"],
  "items": [
    {
      "index": 1,
      "title": "原始标题",
      "summary": "AI 一句话摘要",
      "text": "展示文本（有摘要用摘要，否则用标题）",
      "source": "澎湃",
      "link": "https://...",
      "topic": "national",
      "pub_time": 1783738193.3,
      "pub_display": "07-11 10:49"
    }
  ]
}
```

## 简报格式

- **标题**：每日资讯简报
- **日期**：公历 + 星期 + 农历
- **正文**：12 条新闻，扁平编号，无分类、无来源标签
- **结尾**：【微语】每日金句

## 项目结构

```
├── .github/workflows/
│   ├── daily-news.yml        # 每日采集 + 提交 JSON
│   └── pages.yml             # GitHub Pages 部署
├── data/
│   ├── index.json
│   ├── briefs/
│   └── raw/
├── config.py
├── fetchers.py
├── quality_filter.py
├── brief_style.py
├── ai_summary.py
├── formatter.py
├── quotes.py / quotes.json
├── main.py
├── index.html
├── brief.html
├── 404.html
├── .nojekyll
└── requirements.txt
```

## 自定义

- **新闻条数**：`config.py` → `TARGET_COUNT`（默认 12）
- **时间范围**：`HOURS_FILTER`（默认 24 小时）
- **来源限制**：`MAX_PER_SOURCE`
- **排序优先级**：`SORT_KEYWORDS`
- **微语库**：编辑 `quotes.json`
