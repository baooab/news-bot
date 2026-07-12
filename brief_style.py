"""「每日资讯简报」公众号风格规范 —— 供 AI 摘要模仿。

参考 365资讯简报 / 每日资讯简报 典型产物与编辑反馈整理。
"""

import re

from quality_filter import is_low_quality_title

# ---------------------------------------------------------------------------
# 风格说明（完整版，附于 AI 提示词）
# ---------------------------------------------------------------------------

STYLE_GUIDE = """
# 「每日资讯简报」风格要求

## 一、整体结构（自上而下）

1. 标题固定为「每日资讯简报」
2. 日期行：公历 + 星期 + 农历（如 2026年07月11日 星期六 农历五月廿七）
3. 正文：12 条新闻，扁平编号 1～12（序号与内容间用顿号，如 1、……）

正文区域**无分类小标题、无媒体来源标签、无今日要点**，读者一眼扫完 12 条。

## 二、正文单条怎么写（核心）

每条 = **谁 + 做了什么 + 结果/数据**，一句话说清，像电报：

| 要素 | 要求 | 示例 |
|------|------|------|
| 主体 | 机构/国家/人物/企业，必须出现 | 央行、统计局、菲律宾、长鑫科技 |
| 动作 | 已发生或已宣布的具体行为 | 发布、批准、造成、启动、开通 |
| 事实 | 措施、结论、事件经过 | 下调起点金额、挂牌督办、发红色预警 |
| 数据 | 有则必留，不可省略 | 1.2%、5000亿元、55人死亡 |

### 推荐句式（按优先级）

1. **机构：具体措施/结论** — 「统计局：5月CPI同比上涨1.2%，环比下降0.1%」
2. **主体 + 动作 + 结果** — 「菲律宾南部强震已造成至少55人死亡、1120人受伤」
3. **主体 + 事件 + 数据** — 「熊猫债存量规模首超5000亿元」

### 语言与篇幅

- 电报体：短句、客观、信息密度高，不加「据悉」「值得注意的是」
- 18～50 字为宜；含多项数据时可略长
- 标题若已清晰完整，可微调措辞但**不得删数字、不得改事实**

## 三、排序逻辑（输入已排好，改写时保持顺序）

国内政策/要闻 → 地方民生 → 社会事件 → 国际新闻 → 其他

## 四、无效条目（禁止写成这样）

以下写法**不是**每日资讯简报风格，必须规避：

1. **猜谜式**：引号内生僻词 + 空洞展望（「百团百项」工程定义上海科创未来）
2. **隐喻式**：拦路虎、闹剧、面临挑战、遭遇波折
3. **观点预测**：官员/专家认为…可能…（无已发生事实）
4. **纯辟谣**：教育部："xxx"系谣言（只说谣言、不说正面事实）
5. **口号套话**：部署抗洪：紧盯高风险区域减少人员伤亡（无具体措施/数字）
6. **空洞通告**：多地发告市民书（无具体安排）
7. **合并快讯**：一条里塞 3 件互不相关的事（应只保留最重要一条）
8. **评论煽情**：可笑闹剧、值得关注、引热议

## 五、合格 vs 不合格对照

| 不合格 | 合格 |
|--------|------|
| 小红书：上市面临挑战 | 小红书赴美 IPO 再因数据合规问题被监管问询 |
| 欧央行官员：AI或加剧通胀波动 | （不合格：纯观点预测，无已发生事实，应跳过） |
| 教育部："教师全面硕士化"系谣言 | 教育部：教师招聘不得强制要求硕士学历（写正面事实） |
| 国常会部署抗洪：紧盯…减少伤亡 | 国常会：启动国家防总四级防汛应急响应 |
""".strip()

# 供 system prompt 使用的精简版
STYLE_SYSTEM_PROMPT = f"""你是「每日资讯简报」公众号的资深编辑，负责把原始标题改写成可直接发布的简报条目。

{STYLE_GUIDE}

你的输出将被程序填入 JSON 的 summaries 数组，每条 summary 对应一条新闻。不要生成今日要点。"""

# 公众号典型写法（few-shot）
STYLE_EXAMPLES = [
    {
        "title": "央行征求意见：将个人投资人认购大额存单起点金额降至不低于20万元人民币",
        "summary": "央行征求意见：将个人投资人认购大额存单起点金额降至不低于20万元人民币",
    },
    {
        "title": "统计局：5月全国居民消费价格同比上涨1.2%，环比下降0.1%",
        "summary": "统计局：5月全国居民消费价格同比上涨1.2%，环比下降0.1%",
    },
    {
        "title": "菲律宾南部强震已造成至少55人死亡、1120人受伤、38人失踪",
        "summary": "菲律宾南部强震已造成至少55人死亡、1120人受伤、38人失踪",
    },
    {
        "title": "国务院安委会对福建泉州“7·9”重大火灾查处挂牌督办",
        "summary": "国务院安委会对福建泉州“7·9”重大火灾查处挂牌督办",
    },
    {
        "title": "最高级别！中央气象台时隔两年再发暴雨红色预警",
        "summary": "中央气象台时隔两年再发暴雨红色预警",
    },
    {
        "title": "市场发行热度大幅升温，熊猫债存量规模首超5000亿元",
        "summary": "熊猫债存量规模首超5000亿元，发行热度大幅升温",
    },
]

TOPIC_LABELS = {
    "national": "国家政策",
    "local": "地方民生",
    "social": "社会事件",
    "international": "国际新闻",
    "other": "其他",
}


def format_style_examples(count=5):
    """格式化 few-shot 范例文本。"""
    lines = []
    for ex in STYLE_EXAMPLES[:count]:
        lines.append(f"原标题：{ex['title']}")
        lines.append(f"简报条目：{ex['summary']}")
        lines.append("")
    return "\n".join(lines).strip()


def build_ai_user_prompt(items):
    """构建含完整风格要求 + 待改写列表的用户提示词。"""
    news_lines = []
    for i, item in enumerate(items):
        topic = TOPIC_LABELS.get(item.get("topic", "other"), "其他")
        news_lines.append(f"{i + 1}. [{topic}] {item['title']}")
    news_list = "\n".join(news_lines)
    n = len(items)

    return f"""请严格按上方「每日资讯简报」风格要求，改写以下 {n} 条新闻。

## 写法范例
{format_style_examples(5)}

## 输出要求
1. summaries 数组长度必须 = {n}，与输入序号一一对应
2. 每条只写一件事；原标题含「丨」「；」等多条快讯时，只保留最重要的一条
3. 保留主体、事件、数字/比例/金额/人数；优先「机构：」句式
4. 不要加序号、不要写来源媒体名

## 待改写新闻（已按 政策→地方→社会→国际 排序）
{news_list}

请严格按 JSON 返回（不要 markdown 代码块）：
{{"summaries": ["条目1", "条目2", ...]}}"""


def _extract_numbers(text):
    return set(re.findall(r"\d+(?:\.\d+)?[%％]?|\d+万|\d+亿", text or ""))


def validate_summary(title, summary):
    """校验 AI 摘要是否符合简报风格；不合格则回退原标题。"""
    summary = (summary or "").strip()
    if not summary or len(summary) < 6:
        return False

    bad, _ = is_low_quality_title(summary)
    if bad:
        return False

    title_nums = _extract_numbers(title)
    if title_nums and not (_extract_numbers(summary) & title_nums):
        return False

    if len(summary) < len(title) * 0.35 and not _extract_numbers(summary):
        return False

    return True


def normalize_summary(title, summary):
    """校验不通过时回退原标题；去掉序号前缀等。"""
    summary = (summary or "").strip()
    summary = re.sub(r"^\d+[\.、\)]\s*", "", summary)
    if validate_summary(title, summary):
        return summary
    return title
