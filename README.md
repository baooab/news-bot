# 科技资讯

每天早上 **6 点半**（北京时间）自动采集权威新闻源，AI 生成摘要，产物以 **JSON 数据**输出，并由 **Bulma** 网页承载渲染，通过 **GitHub Pages** 发布。

每日精选 **12 条科技 + 6 条民生社会**（共 18 条）。

## 在线访问

部署完成后访问：

```
https://<你的用户名>.github.io/<仓库名>/
```

例如仓库名为 `news-bot`：`https://yourname.github.io/news-bot/`

| 页面 | 说明 |
|------|------|
| `/`（`index.html`） | 首页，仅展示**当月**科技资讯 |
| `/archive.html` | 历史归档，按**年 → 月 → 日期列表**展示往期简报，支持年份筛选与关键词检索 |
| `/brief.html?date=YYYY-MM-DD` | 简报详情（可编辑、复制公众号版） |

## 数据源

| 类型 | 来源 | 方式 |
|------|------|------|
| 综合 | 澎湃新闻 | JSON API |
| 民生社会 | 中新网（社会频道） | RSS |
| 科技 | IT之家 | RSS |
| 商业 | 36氪 | JSON API |
| 科技 | Solidot | RSS |
| 科技 | 凤凰科技 | JSONP |
| 科技 / AI | 雷峰网 | RSS |

> 如需增减来源，编辑 `config.py` 的 `SOURCES`。

## 编辑立场

本期简报由 AI 以**资深科技主编**身份编排，而非逐条改写标题。核心方法论写在 `tech_brief_style.py` → `EDITORIAL_PRINCIPLES`：

| 原则 | 含义 | 落地方式 |
|------|------|----------|
| **先筛选，后编排** | 候选池是未过滤的原始素材，软文/通稿/重复的剔除由主编完成 | `SELECTION_RULES` + `items` 数组 |
| **先判断，后动笔** | 先回答「这批资讯共同在讲什么主线」，没有主线就按重要性排序，**不硬造趋势** | `EDITORIAL_PRINCIPLES` |
| **编排** | 主编有权重排：最有信号量的开头 → 沿主线展开 → 支撑性在后 → 民生垫底 | `items` 数组顺序即最终顺序 |
| **大历史观** | 把新闻放回产业时间轴：坐标、趋势方向、阶段判断、当日矛盾 | 期标题段一写「主线判断」 |
| **言之有物** | 每个判断必须挂在具体事实上（公司/产品/金额/人数/百分比） | 锚点体系 + 空泛词表拦截 |

### 三个交付物

| 字段 | 说明 | 校验 |
|------|------|------|
| `headline` | 两段式：段一 = 主线判断，段二 = 核心事实 | `is_valid_headline()` + `headline_traceable()` |
| `overview` | 本期导语（2~3 句），呈现主线与矛盾面 | `validate_overview()` |
| `items` | 选中的条目（idx + section + summary），数组顺序即简报顺序 | idx 合法性 + 配额校验，漏选时机械递补 |

> **提示词与代码的契约必须一致**：提示词里写的字数/条数上限，要与校验代码的阈值严格对齐，否则 AI 会被误判不合格而回落到兜底产物。

## 质量治理机制

**本地零过滤**：采集层只做时间窗口与同题去重，软文/通稿/重复/重要性的全部判断交由 AI 主编（规则写在 `tech_brief_style.py` → `SELECTION_RULES`）。本地仅保留对 **AI 产物** 的程序化校验：

| 机制 | 作用 | 实现 |
|------|------|------|
| **AI 选材** | 软文/广告/发布会通稿/辟谣稿/跨期重复的剔除，全部由 AI 判断 | `SELECTION_RULES`（原正则黑名单已全部移除） |
| **跨期去重** | 近 N 期已发标题列给 AI，由 AI 避免连发 | `main.py` → `load_recent_titles()` |
| **AI 摘要校验** | 剥离灌水尾巴、修复粘连错词，不合格回退原标题 | `brief_style.py` |
| **期标题回溯** | 标题中的实体必须能在原文找到出处 | `tech_brief_style.py` → `headline_traceable()` |
| **大历史观闸门** | 拦截「科技浪潮」「白热化」「巨头纷纷加码」等脱离事实的抒发 | `editorial_check.py` → `_HISTORY_VAGUE` |
| **言之有物闸门** | 判断句必须带具体锚点；导语需 ≥2 类锚点且数字须有出处 | `editorial_check.py` → `anchor_count()` |
| **串台拦截** | AI 把 A 条内容写进 B 条时回退原标题，成品级再兜底去重 | `editorial_check.py` → `summary_matches_title()` |
| **机械递补** | AI 漏选时按时间顺序补足配额（不做质量判断） | `ai_summary.py` → `_apply_selection()` |

可调环境变量：

| 变量 | 默认 | 说明 |
|------|------|------|
| `RECENT_CALENDAR_DAYS` | `2` | 采集窗口（今天 + 昨天） |
| `RECENT_DEDUP_DAYS` | `5` | 喂给 AI 的历史期数（跨期去重依据） |
| `AI_CANDIDATE_LIMIT` | `260` | 候选池上限（超出按时间截断，上下文保护） |
| `AI_API_KEY` | — | 配置后启用 AI 编排与摘要 |

## 工作流程

```
6 大数据源采集（原始数据存档）
→ 日历窗口（今天 + 昨天）→ 同题去重 → 时间倒序 → 候选池截断
→ AI 主编全权处理：筛选软文/跨期去重/分区/排序/逐条改写/导语/两段式标题
→ 本地仅做输出契约校验与机械递补 → 构建简报 JSON → 提交到仓库
→ GitHub Pages 自动部署（含首页、归档页、详情页）
```

## 输出产物

**JSON 数据（提交到仓库）**

- `data/briefs/YYYY-MM-DD.json` — 精选简报（12+6 条 + 标题 headline + 农历日期）
- `data/raw/YYYY-MM-DD.json` — 全部原始数据，按来源分组
- `data/index.json` — 简报索引（供首页 / 归档页读取）

**静态网页（GitHub Pages 发布）**

- `index.html` — 首页，只列出当月简报
- `archive.html` — 归档页，按年 / 月分组列出每期日期，可点击进入详情
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
3. 每日北京时间 **21:00** 自动运行 `Daily News Brief`，或手动触发

未配置 AI Secret 时仍可运行，仅跳过 AI 摘要。**只需配置 `AI_API_KEY` 即可**（URL / MODEL 有默认值）。

| Secret | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `AI_API_KEY` | ✅ | — | 你的 API Key |
| `AI_API_URL` | | `https://api.deepseek.com/v1/chat/completions` | OpenAI 兼容接口地址 |
| `AI_MODEL` | | `deepseek-flash` | 模型名（现行调用名，实为 V4.1-Flash-1017） |

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
  "overview": "本期主线导语（AI 主编生成，言之有物）",
  "generated_at": "2026-08-06 07:03:50",
  "count": 18,
  "tech_quota": 12,
  "general_quota": 6,
  "sources": ["IT之家", "Solidot", "中新网", "澎湃"],
  "items": [
    {
      "index": 1,
      "title": "原始标题",
      "summary": "AI 一句话摘要",
      "text": "展示文本（有摘要用摘要，否则用标题）",
      "source": "Solidot",
      "link": "https://...",
      "section": "tech",       // tech | general（由 AI 主编分区）
      "pub_time": 1785917558.0,
      "pub_display": "08-05 16:12"
    }
  ]
}
```

## 简报格式

- **系列名**：科技资讯
- **标题**：两段式 headline（段一 = 主线判断，段二 = 核心事实）
- **导语**：overview（本期主线，呈现主线与矛盾面）
- **日期**：公历 + 星期 + 农历
- **正文**：12 条科技 + 6 条民生社会，扁平编号（选材、分区与顺序均由 AI 主编决定）
- **详情页**：可编辑条目、切换原始池、复制公众号版

## 项目结构

```
├── .github/workflows/
│   ├── daily-news.yml        # 每日采集 + 提交 JSON（21:00 北京时间）
│   └── pages.yml             # GitHub Pages 部署
├── data/
│   ├── index.json
│   ├── briefs/
│   └── raw/
├── config.py                 # 数据源、配额与 AI 配置
├── fetchers.py               # 采集 + 时间窗口 + 同题去重（零内容过滤）
├── quality_filter.py         # AI 产物标题校验（供 brief_style / tech_brief_style 使用）
├── editorial_check.py        # 主编纪律闸门（大历史观 / 言之有物 / 串台）
├── brief_style.py
├── tech_brief_style.py       # 主编提示词（选材规则 + 编排原则 + 期标题规范）
├── ai_summary.py             # AI 全权选材编排：调用 / 契约校验 / 机械递补
├── formatter.py              # 纯格式化输出（JSON + 纯文本）
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

- **科技 / 民生条数**：`config.py` → `TECH_QUOTA` / `GENERAL_QUOTA`（默认 12 + 6）
  改完后提示词、校验层、前端文案会**自动跟随**（均从 config 读取，不再硬编码条数）
- **选材规则**：`tech_brief_style.py` → `SELECTION_RULES`（AI 选材边界，原本地正则黑名单已移除）
- **日历窗口**：`RECENT_CALENDAR_DAYS`（默认 `2`，即今天 + 昨天；`0` 关闭）
- **跨期历史**：`RECENT_DEDUP_DAYS`（默认 `5` 期，喂给 AI 做跨期去重依据）
- **候选池上限**：`AI_CANDIDATE_LIMIT`（默认 `260`，超出按时间截断）
