"""「科技资讯」系列风格规范 —— 供 AI 摘要使用（贴图公众号）。"""

import re

from brief_style import validate_summary
from quality_filter import is_low_quality_title

TECH_STYLE_GUIDE = """
# 「科技资讯」贴图系列风格要求

## 整体结构
- 标题系列名：科技资讯（或每日科技资讯）
- 共 12 条：前 8 条为科技向，后 4 条为民生社会（国内民生、社会新闻）
- 扁平编号，无分类小标题、无媒体来源名

## 科技条（第 1～8 条）
- 读者是开发者 / 科技从业者，一句话说清：**谁 + 做了什么 + 关键数据**
- 保留产品名、模型名、版本号、金额、人数等技术实体
- 可在句末用极短影响（≤12 字），如「有望降低发射成本」；禁止空泛评论
- 18～50 字；电报体，不加「据悉」「值得关注」

## 民生社会条（第 9～12 条）
- 国内民生、社会新闻：事故、灾害、教育医疗、消费维权等
- 排除政治执纪反腐（贪污、受贿、双开、立案审查等）
- 排除政治争端与领土主权（南海、台海、两岸、军演等）
- 排除军事军购军备（台军、军购、武器升级等）
- 电报体，保留主体、事件、数字；优先已发生事实

## 禁止写法（与综合简报相同）
- 猜谜式、隐喻式、纯辟谣、口号套话、合并快讯、煽情评论
""".strip()

TECH_STYLE_SYSTEM_PROMPT = f"""你是科技公众号「科技资讯」系列的资深编辑，负责把标题改写成适合贴图发布的单条文案，并为整期起一个吸引人的标题。

{TECH_STYLE_GUIDE}

## 期标题（headline）
- 根据当日期内容提炼，突出 1～2 个最抓眼的科技看点
- 12～28 字；可带数字、公司名、产品名；口语感、适合公众号推送
- 不要用「科技资讯」「每日简报」等系列名；不要加日期、序号、引号
- 示例：「长鑫冲刺上市，OpenAI 扔出智能体」「火箭网系回收成功，特斯拉电池又破纪录」

输出 JSON：headline 为期标题，summaries 与输入序号一一对应。不要生成今日要点。"""

TECH_STYLE_EXAMPLES = [
    {
        "title": "苹果起诉 OpenAI，指控前员工窃取未发布硬件商业机密",
        "summary": "苹果起诉 OpenAI：指控前员工窃取未发布硬件机密文件",
    },
    {
        "title": "长征十号乙火箭一子级海上回收成功，年底前将复用飞行",
        "summary": "长征十号乙：一子级海上网系回收成功，计划年底前复用飞行",
    },
    {
        "title": "OpenRouter 数据显示近半数美国公司调用中国 AI 模型",
        "summary": "OpenRouter：美国企业调用中国 AI 模型占比峰值达 46%",
    },
    {
        "title": "菲律宾南部强震已造成至少55人死亡、1120人受伤",
        "summary": "菲律宾南部强震已造成至少55人死亡、1120人受伤",
    },
]


def format_tech_examples(count=4):
    lines = []
    for ex in TECH_STYLE_EXAMPLES[:count]:
        lines.append(f"原标题：{ex['title']}")
        lines.append(f"贴图条目：{ex['summary']}")
        lines.append("")
    return "\n".join(lines).strip()


def build_tech_ai_user_prompt(items, tech_count=8):
    news_lines = []
    for i, item in enumerate(items):
        section = "科技" if i < tech_count else "民生"
        news_lines.append(f"{i + 1}. [{section}] {item['title']}")
    news_list = "\n".join(news_lines)
    n = len(items)

    return f"""请严格按「科技资讯」系列风格，改写以下 {n} 条（前 {tech_count} 条科技向，后 {n - tech_count} 条民生社会向）。

## 写法范例
{format_tech_examples(4)}

## 输出要求
1. headline：根据本期内容起一个吸引人的期标题（12～28 字）
2. summaries 长度 = {n}，与输入序号一一对应
3. 每条只写一件事；多事件快讯只保留最重要一条
4. 保留数字、公司名、产品名；不要加序号、不要写来源媒体
5. 第 1～{tech_count} 条可适当点出技术/行业影响（极短）

## 待改写
{news_list}

请严格按 JSON 返回（不要 markdown 代码块）：
{{"headline": "期标题", "summaries": ["条目1", "条目2", ...]}}"""


def normalize_tech_summary(title, summary):
    summary = (summary or "").strip()
    summary = re.sub(r"^\d+[\.、\)]\s*", "", summary)
    if validate_summary(title, summary):
        return summary
    return title


def normalize_headline(headline, items=None):
    """清洗期标题；失败时用首条科技看点兜底。"""
    text = (headline or "").strip()
    text = text.strip("「」『』“”\"'")
    text = re.sub(r"^[【\[]|[】\]]$", "", text).strip()
    text = re.sub(r"^(科技资讯|每日科技资讯)[：:\s|｜·\-—]*", "", text).strip()
    if 8 <= len(text) <= 36 and not is_low_quality_title(text)[0]:
        return text
    if items:
        first = (items[0].get("summary") or items[0].get("title") or "").strip()
        first = re.sub(r"[，,。；;].*$", "", first)
        if 6 <= len(first) <= 28:
            return first
    return "今日硬科技看点速览"
