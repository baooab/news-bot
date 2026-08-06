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

## 期标题（headline）——强制两段式
- **必须**写成「看点A，看点B」：用中文逗号「，」连接**恰好两段**科技要点，禁止只有一段
- 两段各自提炼不同新闻：主体 + 关键动作/数据；每段约 6～16 字，合计约 14～32 字
- 优先挑前 8 条科技里最抓眼的两条（数字、公司名、产品名优先）
- 不要用「科技资讯」「每日简报」等系列名；不要加日期、序号、引号
- **禁止**：单句标题、空泛套话（如「今日硬科技看点速览」「科技热点速递」「今日看点」）
- 正例：「折叠屏预增20%，Anthropic自研AI芯片」「长鑫冲刺上市，OpenAI推出智能体」
- 反例：「Google Earth 发布然后撤回了 AI 工具」（只有一段）、「今日硬科技看点速览」（空话）

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
1. headline：**必须**为两段式「看点A，看点B」（中文逗号分隔，恰好两段），禁止单句或空泛套话
2. summaries 长度 = {n}，与输入序号一一对应
3. 每条只写一件事；多事件快讯只保留最重要一条
4. 保留数字、公司名、产品名；不要加序号、不要写来源媒体
5. 第 1～{tech_count} 条可适当点出技术/行业影响（极短）

## 待改写
{news_list}

请严格按 JSON 返回（不要 markdown 代码块）：
{{"headline": "看点A，看点B", "summaries": ["条目1", "条目2", ...]}}"""


# 空泛期标题（禁止出现）
_GENERIC_HEADLINE = re.compile(
    r"(今日|每日|本期).{0,6}(看点|速览|速递|盘点|汇总|热点)"
    r"|硬科技看点|科技看点|资讯速览|科技速递|热点速览|一图看懂|一文读懂"
)


def normalize_tech_summary(title, summary):
    summary = (summary or "").strip()
    summary = re.sub(r"^\d+[\.、\)]\s*", "", summary)
    if validate_summary(title, summary):
        return summary
    return title


def _compress_clause(text, max_len=16):
    """把单条新闻压成适合期标题的短句。"""
    text = (text or "").strip()
    text = re.sub(r"^\d+[\.、\)]\s*", "", text)
    text = text.strip("「」『』“”\"'【】[]")
    # 只取第一分句
    text = re.split(r"[，,。；;：:\n|｜/、]", text, maxsplit=1)[0].strip()
    text = re.sub(r"\s+", "", text)
    if len(text) > max_len:
        text = text[:max_len].rstrip("的了吗呢吧与及和")
    return text


def _split_two_parts(text):
    """尝试拆成恰好两段（仅认中文/英文逗号）；成功返回 (a, b)，否则 None。"""
    text = (text or "").strip()
    if not text:
        return None

    for sep in ("，", ","):
        if sep not in text:
            continue
        parts = [p.strip() for p in text.split(sep) if p.strip()]
        # 恰好两段；多于两段说明不是规范期标题
        if len(parts) == 2:
            # 段内空白压掉，贴近「折叠屏预增20%，Anthropic自研AI芯片」风格
            a = re.sub(r"\s+", "", parts[0])
            b = re.sub(r"\s+", "", parts[1])
            if a and b:
                return a, b
        return None
    return None


def is_valid_headline(text):
    """两段式期标题是否合格。"""
    text = (text or "").strip()
    if not text or _GENERIC_HEADLINE.search(text):
        return False
    parts = _split_two_parts(text)
    if not parts:
        return False
    a, b = parts
    if a == b:
        return False
    if not (4 <= len(a) <= 18 and 4 <= len(b) <= 18):
        return False
    joined = f"{a}，{b}"
    if not (12 <= len(joined) <= 36):
        return False
    if is_low_quality_title(joined)[0]:
        return False
    return True


def build_fallback_headline(items, tech_count=8):
    """从精选条目拼两段式期标题（绝不回落到空话）。"""
    pool = list(items or [])[: max(tech_count, 2)]
    clauses = []
    seen = set()
    for item in pool:
        raw = (item.get("summary") or item.get("title") or "").strip()
        clause = _compress_clause(raw)
        if not clause or len(clause) < 4:
            continue
        key = clause.lower()
        if key in seen:
            continue
        seen.add(key)
        clauses.append(clause)
        if len(clauses) >= 2:
            break

    if len(clauses) >= 2:
        return f"{clauses[0]}，{clauses[1]}"
    if len(clauses) == 1 and len(pool) >= 2:
        second = _compress_clause(
            pool[1].get("summary") or pool[1].get("title") or ""
        )
        if second and second != clauses[0]:
            return f"{clauses[0]}，{second}"
    if len(clauses) == 1:
        # 仍只有一段时，用第二条原标题硬拆一点信息，避免单句/空话
        extra = _compress_clause((pool[1].get("title") if len(pool) > 1 else "") or "行业动态更新")
        if extra == clauses[0]:
            extra = "科技圈新进展"
        return f"{clauses[0]}，{extra}"
    return "科技要闻速递，行业动态更新"


def normalize_headline(headline, items=None):
    """清洗期标题；不合格则用前两条科技看点拼两段式兜底。"""
    text = (headline or "").strip()
    text = text.strip("「」『』“”\"'")
    text = re.sub(r"^[【\[]|[】\]]$", "", text).strip()
    text = re.sub(r"^(科技资讯|每日科技资讯)[：:\s|｜·\-—]*", "", text).strip()

    parts = _split_two_parts(text)
    if parts:
        candidate = f"{parts[0]}，{parts[1]}"
        if is_valid_headline(candidate):
            return candidate

    return build_fallback_headline(items or [])
