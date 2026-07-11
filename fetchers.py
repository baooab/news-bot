"""新闻抓取模块 v4.0 —— 7 大直连数据源 + 24h 过滤 + 模糊去重 + 话题排序。

数据源：
  综合：中国新闻网 RSS、澎湃新闻 API、联合早报 RSS
  科技：IT之家 RSS、36氪 RSS、虎嗅网 RSS、钛媒体 RSS
"""

import re
import time as time_module
from datetime import datetime
from difflib import SequenceMatcher

import feedparser
import requests

from config import (
    SOURCES,
    HOURS_FILTER,
    REQUEST_TIMEOUT,
    SORT_TOPICS,
    SORT_KEYWORDS,
    MAX_FETCH_PER_FEED,
)
from quality_filter import filter_low_quality

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


# ============================================================
# 1. 采集 —— RSS 源
# ============================================================

def fetch_rss(source_name, url):
    """直接抓取 RSS feed，返回 item 列表。"""
    try:
        resp = requests.get(url, headers=HTTP_HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200 or len(resp.content) < 200:
            print(f"  [{source_name}] HTTP {resp.status_code}, len={len(resp.content)}")
            return []

        feed = feedparser.parse(resp.content)
        items = []
        for entry in feed.entries[:MAX_FETCH_PER_FEED]:
            raw_title = getattr(entry, "title", "")
            title = clean_title(raw_title)
            if not title or len(title) < 8:
                continue
            pub_time = parse_entry_time(entry)
            items.append({
                "source": source_name,
                "title": title,
                "link": getattr(entry, "link", ""),
                "pub_time": pub_time,
            })
        return items
    except Exception as e:
        print(f"  [{source_name}] RSS 获取失败: {e}")
        return []


# ============================================================
# 1b. 采集 —— 澎湃新闻 JSON API
# ============================================================

def fetch_thepaper(source_name, url):
    """抓取澎湃新闻 API（JSON），返回 item 列表。"""
    try:
        resp = requests.get(url, headers=HTTP_HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            print(f"  [{source_name}] HTTP {resp.status_code}")
            return []

        data = resp.json()
        d = data.get("data", {})

        all_entries = []
        for key in ("hotNews", "editorHandpicked", "morningEveningNews", "financialInformationNews"):
            lst = d.get(key, [])
            if isinstance(lst, list):
                all_entries.extend(lst)

        items = []
        for entry in all_entries[:MAX_FETCH_PER_FEED]:
            title = entry.get("name", "").strip()
            title = clean_title(title)
            if not title or len(title) < 8:
                continue
            pub_time = None
            ts = entry.get("pubTimeLong", 0)
            if ts:
                pub_time = ts / 1000
            items.append({
                "source": source_name,
                "title": title,
                "link": entry.get("link", ""),
                "pub_time": pub_time,
            })
        return items
    except Exception as e:
        print(f"  [{source_name}] API 获取失败: {e}")
        return []


# ============================================================
# 采集分发
# ============================================================

def fetch_source(source):
    """根据 source 类型分发到对应的抓取函数。"""
    stype = source.get("type", "rss")
    name = source.get("name", "")
    url = source.get("url", "")

    if stype == "rss":
        return fetch_rss(name, url)
    elif stype == "thepaper":
        return fetch_thepaper(name, url)
    else:
        print(f"  [{name}] 未知源类型: {stype}")
        return []


# ============================================================
# 2. 标题清洗
# ============================================================

def clean_title(title):
    """清理标题：去 HTML 标签、去媒体前缀、去多余空白。"""
    if not title:
        return ""
    title = re.sub(r"<[^>]+>", "", title)
    title = re.sub(r"^[\[【\(《].*?[\]】\)》]\s*", "", title)
    title = title.strip()
    return title


# ============================================================
# 3. 时间解析
# ============================================================

def fmt_pub_time(ts):
    """把时间戳格式化为「MM-DD HH:MM」，无时间戳返回空串。"""
    if not ts:
        return ""
    try:
        return datetime.fromtimestamp(ts).strftime("%m-%d %H:%M")
    except Exception:
        return ""


def parse_entry_time(entry):
    """解析 RSS 条目的发布时间，返回时间戳；解析失败返回 None。"""
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return time_module.mktime(t)
            except Exception:
                pass
    for attr in ("published", "updated"):
        raw = getattr(entry, attr, "")
        if raw:
            for fmt in (
                "%a, %d %b %Y %H:%M:%S %Z",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
            ):
                try:
                    return datetime.strptime(raw.strip(), fmt).timestamp()
                except Exception:
                    continue
    return None


# ============================================================
# 4. 时间过滤
# ============================================================

def filter_by_time(items, hours=HOURS_FILTER):
    """只保留最近 N 小时内发布的新闻。无时间戳的直接丢弃。"""
    if hours <= 0:
        return items

    cutoff = datetime.now().timestamp() - hours * 3600
    kept = []
    dropped = 0
    for item in items:
        t = item.get("pub_time")
        if t is None:
            dropped += 1
        elif t >= cutoff:
            kept.append(item)
        else:
            dropped += 1

    if dropped:
        print(f"  时间过滤：丢弃 {dropped} 条（>{hours}h 或无时间戳）")
    return kept


# ============================================================
# 5. 去重（模糊匹配）
# ============================================================

def _normalize(text):
    return re.sub(r"[\s\W_]+", "", text.lower())


def deduplicate(items, threshold=0.55):
    """基于标题相似度去重，保留先出现的（更重要的一条）。"""
    unique = []
    for item in items:
        norm = _normalize(item["title"])
        is_dup = False
        for existing in unique:
            sim = SequenceMatcher(None, norm, _normalize(existing["title"])).ratio()
            if sim > threshold:
                is_dup = True
                break
        if not is_dup:
            unique.append(item)
    removed = len(items) - len(unique)
    if removed:
        print(f"  模糊去重：移除 {removed} 条重复")
    return unique


# ============================================================
# 6. 话题分类 + 排序
# ============================================================

def classify_topic(title):
    """将新闻标题分入话题类别，用于排序。"""
    for topic in SORT_TOPICS:
        if topic == "other":
            continue
        for kw in SORT_KEYWORDS.get(topic, []):
            if kw in title:
                return topic
    return "other"


def sort_news(items):
    """按话题优先级 + 时效性排序。同话题内按时间倒序。"""
    topic_order = {topic: i for i, topic in enumerate(SORT_TOPICS)}
    items.sort(key=lambda x: (
        topic_order.get(x.get("topic", "other"), 999),
        -(x.get("pub_time") or 0),
    ))
    return items


# ============================================================
# 7. 汇总入口
# ============================================================

def collect_raw():
    """采集全部数据源的原始条目（不做过滤/去重），返回扁平列表。

    这份原始数据会被完整存档为 JSON 供参考。
    """
    all_items = []
    for source in SOURCES:
        items = fetch_source(source)
        if items:
            print(f"  [{source['name']}] 获取 {len(items)} 条")
        all_items.extend(items)
    print(f"\n  原始总计：{len(all_items)} 条")
    return all_items


def process_news(raw_items):
    """对原始条目做：时间过滤 -> 去重 -> 分类 -> 排序，返回精选候选列表。

    不修改传入的 raw_items（内部复制），以便原始数据保持完整。
    """
    all_items = [dict(it) for it in raw_items]

    all_items = filter_by_time(all_items)
    print(f"  时间过滤后：{len(all_items)} 条")

    all_items = deduplicate(all_items)
    print(f"  去重后：{len(all_items)} 条")

    all_items = filter_low_quality(all_items)
    print(f"  质量过滤后：{len(all_items)} 条")

    for item in all_items:
        item["topic"] = classify_topic(item["title"])

    all_items = sort_news(all_items)

    topic_names = {
        "national": "国家政策",
        "local": "地方民生",
        "social": "社会事件",
        "international": "国际新闻",
        "other": "其他",
    }
    dist = {}
    for item in all_items:
        dist[item["topic"]] = dist.get(item["topic"], 0) + 1
    dist_str = " / ".join(
        f"{topic_names.get(t, t)}{c}" for t, c in dist.items() if c > 0
    )
    print(f"  话题分布：{dist_str}")

    return all_items


def fetch_all_news():
    """完整采集流程（向后兼容）：采集原始 -> 处理。"""
    return process_news(collect_raw())


# ============================================================
# 本地测试
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("新闻抓取测试 v4.0 —— 7 大直连数据源")
    print("=" * 60)

    items = fetch_all_news()

    print(f"\n最终结果：{len(items)} 条")
    print("-" * 60)
    for i, item in enumerate(items[:20]):
        pub = ""
        if item.get("pub_time"):
            dt = datetime.fromtimestamp(item["pub_time"])
            hours_ago = (datetime.now() - dt).total_seconds() / 3600
            pub = f" [{dt.strftime('%m-%d %H:%M')}, {hours_ago:.0f}h前]"
        print(f"  {i+1:2d}. [{item['source']}] {item['title'][:45]}{pub}")
