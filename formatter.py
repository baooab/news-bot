"""简报格式化模块 —— 科技资讯 JSON + 纯文本（贴图公众号）。

本模块只负责格式化输出，不做任何内容选条 / 过滤 / 排序判断 ——
选材与编排全部由 AI 主编完成（见 ai_summary.py / tech_brief_style.py）。
"""

import re
from datetime import datetime

from config import TECH_QUOTA, GENERAL_QUOTA
from fetchers import fmt_pub_time

# ============================================================
# 农历支持（可选依赖）
# ============================================================

try:
    from lunardate import LunarDate
    _LUNAR_OK = True
except ImportError:
    _LUNAR_OK = False

WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

_LUNAR_MONTHS = [
    "正月", "二月", "三月", "四月", "五月", "六月",
    "七月", "八月", "九月", "十月", "冬月", "腊月",
]
_LUNAR_DAYS = [
    "初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
    "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
    "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十",
]


def _get_lunar_str():
    """返回农历日期字符串，如「农历六月十七」。"""
    if not _LUNAR_OK:
        return ""
    today = datetime.now()
    try:
        lunar = LunarDate.fromSolarDate(today.year, today.month, today.day)
        month_str = _LUNAR_MONTHS[lunar.month - 1]
        day_str = _LUNAR_DAYS[lunar.day - 1]
        if lunar.isLeapMonth:
            month_str = "闰" + month_str
        return f"农历{month_str}{day_str}"
    except Exception:
        return ""


def get_date_header():
    """日期头：公历 + 星期 + 农历。"""
    now = datetime.now()
    date_str = now.strftime("%Y年%m月%d日")
    weekday = WEEKDAYS[now.weekday()]
    lunar = _get_lunar_str()
    parts = [date_str, weekday]
    if lunar:
        parts.append(lunar)
    return " ".join(parts)


# ============================================================
# 格式化输出
# ============================================================

def _item_text(item):
    """单条新闻文本：优先用 AI 摘要，否则用原标题。"""
    summary = item.get("summary", "")
    if summary:
        return summary
    return item["title"]


def format_plain_text(items, headline="", overview=""):
    """科技资讯纯文本预览。"""
    header = get_date_header()
    title = headline or "科技资讯"
    lines = [title, header, ""]

    if overview:
        lines.append(overview)
        lines.append("")

    for i, item in enumerate(items, 1):
        lines.append(f"{i}、{_item_text(item)}")

    return "\n".join(lines)


# 向后兼容别名
format_tech_plain_text = format_plain_text


# ============================================================
# 简报 JSON 构建（最终产物）
# ============================================================

def build_brief_dict(items, headline="", overview=""):
    """构建科技资讯 JSON。"""
    now = datetime.now()

    # 成品级去重：AI 偶发「串台」会让两条文案完全相同，成品阶段兜底剔除
    deduped, seen_text = [], set()
    for it in items:
        text = (_item_text(it) or "").strip()
        norm = re.sub(r"\s+", "", text)
        if norm and norm in seen_text:
            print(f"  [去重] 剔除重复文案：{text[:36]}")
            continue
        if norm:
            seen_text.add(norm)
        deduped.append(it)

    items = deduped
    return {
        "series": "科技资讯",
        "headline": headline or "",
        "date": now.strftime("%Y-%m-%d"),
        "date_display": get_date_header(),
        "weekday": WEEKDAYS[now.weekday()],
        "lunar": _get_lunar_str(),
        "overview": overview or "",
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(items),
        "tech_quota": TECH_QUOTA,
        "general_quota": GENERAL_QUOTA,
        "sources": sorted({it["source"] for it in items}),
        "items": [
            {
                "index": idx,
                "title": it["title"],
                "summary": it.get("summary", ""),
                "text": _item_text(it),
                "source": it["source"],
                "link": it.get("link", ""),
                "section": it.get("section", ""),
                "pub_time": it.get("pub_time"),
                "pub_display": fmt_pub_time(it.get("pub_time")),
            }
            for idx, it in enumerate(items, 1)
        ],
    }
