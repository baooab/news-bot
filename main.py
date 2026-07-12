"""科技资讯 —— 主入口（GitHub Actions）。

流程：
  采集全部数据源原始数据（存档）
  -> 过滤（今天+昨天）-> 去重 -> 质量过滤 -> 话题排序
  -> 精选 6 科技 + 6 民生社会 -> AI 摘要 -> 过滤递补
  -> data/briefs/、data/raw/、data/index.json
"""

import os
import json
import glob
from datetime import datetime

from config import TECH_QUOTA, GENERAL_QUOTA
from fetchers import collect_raw, process_news, filter_by_recency, fmt_pub_time
from formatter import select_items_tech, format_plain_text, build_brief_dict
from ai_summary import ai_enhance, is_ai_enabled
from quality_filter import filter_selected_items
from tech_score import is_tech_item, annotate_tech_scores

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
BRIEFS_DIR = os.path.join(DATA_DIR, "briefs")
RAW_DIR = os.path.join(DATA_DIR, "raw")

WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def build_raw_dict(raw_items):
    now = datetime.now()
    by_source = {}
    for it in raw_items:
        by_source.setdefault(it["source"], []).append({
            "title": it["title"],
            "link": it.get("link", ""),
            "pub_time": it.get("pub_time"),
            "pub_display": fmt_pub_time(it.get("pub_time")),
        })
    return {
        "date": now.strftime("%Y-%m-%d"),
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(raw_items),
        "source_count": {k: len(v) for k, v in by_source.items()},
        "sources": by_source,
    }


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _enhance_and_filter(selected, sorted_news):
    if is_ai_enabled():
        headline, enhanced = ai_enhance(selected)
    else:
        print("  [跳过] 未配置 AI API（在 Secrets 中设置 AI_API_KEY 即可启用）")
        from tech_brief_style import normalize_headline
        enhanced = selected
        headline = normalize_headline("", enhanced)

    annotate_tech_scores(sorted_news)

    def _borderline(it):
        return it.get("tech_score", 0) >= 20

    tech_pool = [it for it in sorted_news if is_tech_item(it) or _borderline(it)]
    general_pool = [it for it in sorted_news if not is_tech_item(it) and not _borderline(it)]
    general_fallback = general_pool  # 递补仅限非科技条目
    tech_part = filter_selected_items(
        enhanced[:TECH_QUOTA], tech_pool + sorted_news, count=TECH_QUOTA
    )
    general_part = filter_selected_items(
        enhanced[TECH_QUOTA:], general_fallback, count=GENERAL_QUOTA
    )
    result = tech_part + general_part
    for i, item in enumerate(result):
        item["section"] = "tech" if i < TECH_QUOTA else "general"
    return headline, result


def generate_index():
    pattern = os.path.join(BRIEFS_DIR, "*.json")
    files = sorted(glob.glob(pattern), reverse=True)

    briefs = []
    for filepath in files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        date_str = data.get("date") or os.path.basename(filepath).replace(".json", "")
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            display = f"{dt.strftime('%Y年%m月%d日')} {WEEKDAYS[dt.weekday()]}"
        except ValueError:
            display = date_str

        briefs.append({
            "date": date_str,
            "display": display,
            "series": data.get("series", "科技资讯"),
            "headline": data.get("headline", ""),
            "count": data.get("count", 0),
            "sources": data.get("sources", []),
        })

    index = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(briefs),
        "briefs": briefs,
    }
    _write_json(os.path.join(DATA_DIR, "index.json"), index)
    print(f"  索引:   data/index.json（{len(briefs)} 篇）")


def main():
    print("=" * 55)
    print("  科技资讯 —— 开始执行")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    from config import SOURCES
    print(f"\n[1/5] 采集新闻（{len(SOURCES)} 大数据源）...")
    raw_items = collect_raw()
    if not raw_items:
        print("[ERROR] 未获取到任何新闻")
        return False
    raw_items = filter_by_recency(raw_items)
    if not raw_items:
        print("[ERROR] 时间过滤后无可用新闻")
        return False

    print("\n[2/5] 过滤 / 去重 / 排序...")
    sorted_news = process_news(raw_items, skip_recency_filter=True)
    print(f"  可用新闻：{len(sorted_news)} 条")

    print(f"\n[3/5] 精选 {TECH_QUOTA} 科技 + {GENERAL_QUOTA} 民生社会...")
    selected = select_items_tech(sorted_news)
    tech_cnt = sum(1 for it in selected if it.get("section") == "tech")
    print(f"  入选 {tech_cnt} 科技 + {len(selected) - tech_cnt} 民生社会")

    print("\n[4/5] AI 摘要 / 过滤递补...")
    headline, final = _enhance_and_filter(selected, sorted_news)
    print(f"  最终 {len(final)} 条")

    print("\n[5/5] 构建 JSON / 保存...")
    brief = build_brief_dict(final, headline=headline)
    raw = build_raw_dict(raw_items)
    today = brief["date"]

    print(f"\n{'─' * 50}")
    print(format_plain_text(final, headline=headline))
    print(f"{'─' * 50}")

    _write_json(os.path.join(BRIEFS_DIR, f"{today}.json"), brief)
    print(f"  简报:   data/briefs/{today}.json（{brief['count']} 条）")

    _write_json(os.path.join(RAW_DIR, f"{today}.json"), raw)
    print(f"  原始:   data/raw/{today}.json（{raw['total']} 条）")

    generate_index()

    print(f"\n{'=' * 55}")
    print("  执行完成！")
    print(f"{'=' * 55}")
    return True


if __name__ == "__main__":
    main()
