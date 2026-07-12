"""简报格式化模块 —— 科技资讯 JSON + 纯文本（贴图公众号）。"""

from datetime import datetime

from config import (
    MAX_PER_SOURCE,
    TECH_QUOTA,
    GENERAL_QUOTA,
    TECH_SOURCE_LIMITS,
    TECH_DEDUP_GROUPS,
    GENERAL_SORT_TOPICS,
    GENERAL_ANTI_KEYWORDS,
)
from fetchers import fmt_pub_time
from quotes import get_daily_quote
from tech_score import annotate_tech_scores, is_tech_item, is_disaster_title

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
# 选条（8 科技 + 4 民生社会）
# ============================================================

def _extract_dedup_entities(title):
    """从标题提取科技主体标签（同组共用一个标签）。"""
    title = title or ""
    upper = title.upper()
    found = []
    for group in TECH_DEDUP_GROUPS:
        tag = group[0]
        for entity in group:
            key = entity.upper()
            if key in upper or entity in title:
                found.append(tag)
                break
    return found


def _entity_conflict(used_entities, title):
    tags = _extract_dedup_entities(title)
    if not tags:
        return False
    return any(t in used_entities for t in tags)


def _select_tech_with_dedup(pool, quota, source_limits, seen=None):
    """科技区选条：来源上限 + 同一公司/品牌只保留一条。"""
    seen = seen or set()
    selected = []
    source_count = {}
    used_entities = set()

    for item in pool:
        if len(selected) >= quota:
            break
        key = _item_key(item)
        if key in seen:
            continue
        title = item.get("title", "")
        if _entity_conflict(used_entities, title):
            continue
        src = item["source"]
        limit = source_limits.get(src, MAX_PER_SOURCE)
        if source_count.get(src, 0) >= limit:
            continue
        selected.append(item)
        seen.add(key)
        source_count[src] = source_count.get(src, 0) + 1
        for tag in _extract_dedup_entities(title):
            used_entities.add(tag)

    if len(selected) < quota:
        for item in pool:
            if len(selected) >= quota:
                break
            key = _item_key(item)
            if key in seen:
                continue
            if _entity_conflict(used_entities, item.get("title", "")):
                continue
            selected.append(item)
            seen.add(key)
            for tag in _extract_dedup_entities(item.get("title", "")):
                used_entities.add(tag)

    return selected


def _is_borderline_tech(item):
    """接近科技阈值，应优先归入科技区而非民生社会区。"""
    return item.get("tech_score", 0) >= 20


def _has_tech_leaning(item):
    """科技味明显但未达科技阈值，不应落入民生社会区。"""
    return item.get("tech_score", 0) >= 10


def _is_low_general_item(item):
    """民生社会池：排除国际军事、财经调研、政治执纪反腐等条目。"""
    title = (item.get("title") or "").strip()
    if not title:
        return True
    if any(kw in title for kw in GENERAL_ANTI_KEYWORDS):
        return True
    return False


def _item_key(item):
    return item.get("link") or item.get("title", "")


def _select_with_limits(pool, quota, source_limits, seen=None):
    """按来源上限从池子里选取，保证多样性。"""
    seen = seen or set()
    selected = []
    source_count = {}

    for item in pool:
        if len(selected) >= quota:
            break
        key = _item_key(item)
        if key in seen:
            continue
        src = item["source"]
        limit = source_limits.get(src, MAX_PER_SOURCE)
        if source_count.get(src, 0) >= limit:
            continue
        selected.append(item)
        seen.add(key)
        source_count[src] = source_count.get(src, 0) + 1

    if len(selected) < quota:
        for item in pool:
            if len(selected) >= quota:
                break
            key = _item_key(item)
            if key in seen:
                continue
            selected.append(item)
            seen.add(key)

    return selected


def _sort_general_pool(items):
    """民生社会池：社会/地方民生优先，同类灾害只保留一条，低价值条目靠后。"""
    topic_order = {t: i for i, t in enumerate(GENERAL_SORT_TOPICS)}
    items = sorted(items, key=lambda x: (
        1 if _is_low_general_item(x) else 0,
        topic_order.get(x.get("topic", "other"), 999),
        -(x.get("pub_time") or 0),
    ))

    kept = []
    disaster_seen = False
    for item in items:
        if _is_low_general_item(item):
            continue
        title = item.get("title", "")
        if is_disaster_title(title):
            if disaster_seen:
                continue
            disaster_seen = True
        kept.append(item)
    return kept


def _build_general_pool(items, seen):
    """构建民生社会候选池，优先国内社会/民生。"""
    candidates = [
        it for it in items
        if _item_key(it) not in seen
        and not is_tech_item(it)
        and not _is_borderline_tech(it)
        and not _has_tech_leaning(it)
    ]
    pool = _sort_general_pool(candidates)
    if len(pool) >= GENERAL_QUOTA:
        return pool
    # 不够时从候选中递补（仍跳过低价值条目）
    pool_keys = {_item_key(it) for it in pool}
    for item in _sort_general_pool(candidates):
        key = _item_key(item)
        if key in pool_keys:
            continue
        if _is_low_general_item(item):
            continue
        pool.append(item)
        pool_keys.add(key)
        if len(pool) >= GENERAL_QUOTA * 2:
            break
    return pool


def select_items_tech(sorted_items, tech_quota=TECH_QUOTA, general_quota=GENERAL_QUOTA):
    """科技资讯选条：tech_quota 条科技 + general_quota 条民生社会。"""
    items = annotate_tech_scores([dict(it) for it in sorted_items])
    seen = set()

    tech_pool = sorted(
        [it for it in items if is_tech_item(it) or _is_borderline_tech(it)],
        key=lambda x: (-x.get("tech_score", 0), -(x.get("pub_time") or 0)),
    )
    tech_selected = _select_tech_with_dedup(tech_pool, tech_quota, TECH_SOURCE_LIMITS, seen)

    general_pool = _build_general_pool(items, seen)
    general_selected = _select_with_limits(
        general_pool, general_quota, {}, seen
    )

    total = tech_quota + general_quota
    if len(tech_selected) + len(general_selected) < total:
        for item in items:
            if len(tech_selected) + len(general_selected) >= total:
                break
            key = _item_key(item)
            if key in seen:
                continue
            if len(tech_selected) < tech_quota and is_tech_item(item):
                if not _entity_conflict(
                    {t for it in tech_selected for t in _extract_dedup_entities(it.get("title", ""))},
                    item.get("title", ""),
                ):
                    tech_selected.append(item)
            elif len(general_selected) < general_quota and not is_tech_item(item) and not _is_borderline_tech(item) and not _has_tech_leaning(item) and not _is_low_general_item(item):
                general_selected.append(item)
            seen.add(key)

    result = tech_selected[:tech_quota] + general_selected[:general_quota]
    for i, item in enumerate(result):
        item["section"] = "tech" if i < tech_quota else "general"
    return result


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
    """科技资讯纯文本预览。"""
    header = get_date_header()
    lines = ["科技资讯", header, ""]

    for i, item in enumerate(items, 1):
        lines.append(f"{i}. {_item_text(item)}")

    lines.append("")
    lines.append(f"【微语】{get_daily_quote()}")
    return "\n".join(lines)


# 向后兼容别名
format_tech_plain_text = format_plain_text


# ============================================================
# 简报 JSON 构建（最终产物）
# ============================================================

def build_brief_dict(items):
    """构建科技资讯 JSON。"""
    now = datetime.now()
    return {
        "series": "科技资讯",
        "date": now.strftime("%Y-%m-%d"),
        "date_display": get_date_header(),
        "weekday": WEEKDAYS[now.weekday()],
        "lunar": _get_lunar_str(),
        "overview": "",
        "quote": get_daily_quote(),
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
                "topic": it.get("topic", "other"),
                "section": it.get("section", ""),
                "tech_score": it.get("tech_score"),
                "pub_time": it.get("pub_time"),
                "pub_display": fmt_pub_time(it.get("pub_time")),
            }
            for idx, it in enumerate(items, 1)
        ],
    }
