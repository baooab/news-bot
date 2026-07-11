"""简报格式化模块 —— 生成简报 JSON 数据 + 纯文本（日志/公众号）。

规范参考真实公众号「每日资讯简报」调研结果：
  - 扁平编号 1~12，无分类标题
  - 无媒体来源标签
  - 公历 + 星期 + 农历 日期头
  - 【微语】每日金句结尾

最终产物为 JSON，由网页（Bulma）承载渲染。
"""

from datetime import datetime

from config import TARGET_COUNT, MAX_PER_SOURCE
from fetchers import fmt_pub_time
from quotes import get_daily_quote

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
# 选条
# ============================================================

def select_items(sorted_items, count=TARGET_COUNT, max_per_source=MAX_PER_SOURCE):
    """从排好序的新闻中选取 count 条，保证来源多样性。"""
    selected = []
    source_count = {}
    for item in sorted_items:
        src = item["source"]
        if source_count.get(src, 0) >= max_per_source:
            continue
        selected.append(item)
        source_count[src] = source_count.get(src, 0) + 1
        if len(selected) >= count:
            break

    # 不够则放宽限制补齐
    if len(selected) < count:
        for item in sorted_items:
            if item in selected:
                continue
            selected.append(item)
            if len(selected) >= count:
                break

    return selected[:count]


# ============================================================
# 格式化输出
# ============================================================

def _item_text(item):
    """单条新闻文本：优先用 AI 摘要，否则用原标题。"""
    summary = item.get("summary", "")
    if summary:
        return summary
    return item["title"]


def format_plain_text(items):
    """纯文本格式 —— 用于日志和调试预览。"""
    header = get_date_header()
    lines = ["每日资讯简报", header, ""]

    for i, item in enumerate(items, 1):
        lines.append(f"{i}. {_item_text(item)}")

    lines.append("")
    lines.append(f"【微语】{get_daily_quote()}")
    return "\n".join(lines)


# ============================================================
# 简报 JSON 构建（最终产物）
# ============================================================

def build_brief_dict(items):
    """构建简报 JSON 结构（最终产物，由网页承载渲染）。"""
    now = datetime.now()
    return {
        "date": now.strftime("%Y-%m-%d"),
        "date_display": get_date_header(),
        "weekday": WEEKDAYS[now.weekday()],
        "lunar": _get_lunar_str(),
        "overview": "",
        "quote": get_daily_quote(),
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(items),
        "sources": sorted({it["source"] for it in items}),
        "items": [
            {
                "index": idx,
                "title": it["title"],
                "summary": it.get("summary", ""),
                "text": _item_text(it),
                "source": it["source"],
                "link": it.get("link", ""),
                "topic": it.get("topic", "other"),
                "pub_time": it.get("pub_time"),
                "pub_display": fmt_pub_time(it.get("pub_time")),
            }
            for idx, it in enumerate(items, 1)
        ],
    }
