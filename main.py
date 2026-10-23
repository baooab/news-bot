"""科技资讯 —— 主入口（GitHub Actions）。

流程（本地零过滤，选材与编排全权交由 AI 主编）：
  采集全部数据源原始数据（存档）
  -> 时间窗口（今天+昨天）-> 同题去重 -> 时间倒序 -> 候选池截断
  -> AI 主编：筛选软文/去重/分区/排序/摘要/期标题/导语
  -> 本地仅做输出契约校验与机械递补
  -> data/briefs/、data/raw/、data/index.json
"""

import os
import json
import glob
from datetime import datetime

from config import (
    TECH_QUOTA, GENERAL_QUOTA, TARGET_COUNT,
    RECENT_DEDUP_DAYS, AI_CANDIDATE_LIMIT,
)
from fetchers import collect_raw, filter_by_recency, deduplicate, sort_news, fmt_pub_time
from ai_summary import ai_compose, is_ai_enabled
from formatter import format_plain_text, build_brief_dict

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


def load_recent_titles(days=RECENT_DEDUP_DAYS, exclude_date=None):
    """读取最近 N 期简报的标题清单，作为跨期去重依据交给 AI 判断。"""
    files = sorted(glob.glob(os.path.join(BRIEFS_DIR, "*.json")), reverse=True)
    titles = []
    seen_dates = set()
    for filepath in files:
        date_str = os.path.basename(filepath).replace(".json", "")
        if exclude_date and date_str == exclude_date:
            continue
        if date_str in seen_dates:
            continue
        seen_dates.add(date_str)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        for item in data.get("items", []):
            t = item.get("title") or item.get("text") or ""
            if t:
                titles.append(t)
        if len(seen_dates) >= days:
            break
    return titles


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
            # 配额随配置变化，前端据此渲染，避免硬编码过时
            "tech_quota": data.get("tech_quota", TECH_QUOTA),
            "general_quota": data.get("general_quota", GENERAL_QUOTA),
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
        print("[ERROR] 时间窗口内无可用新闻")
        return False

    print("\n[2/5] 同题去重 / 时间倒序（本地零过滤，不做任何质量判断）...")
    candidates = deduplicate(raw_items)
    candidates = sort_news(candidates)
    if len(candidates) > AI_CANDIDATE_LIMIT:
        print(f"  候选 {len(candidates)} 条超出上限，按时间截断至 {AI_CANDIDATE_LIMIT} 条")
        candidates = candidates[:AI_CANDIDATE_LIMIT]
    print(f"  候选池：{len(candidates)} 条")

    history = load_recent_titles(
        days=RECENT_DEDUP_DAYS,
        exclude_date=datetime.now().strftime("%Y-%m-%d"),
    )
    if history:
        print(f"  载入近 {RECENT_DEDUP_DAYS} 期已发标题 {len(history)} 条（交由 AI 跨期去重）")

    print(f"\n[3/5] AI 主编选材编排（目标 {TECH_QUOTA} 科技 + {GENERAL_QUOTA} 民生社会）...")
    headline, final, overview = ai_compose(candidates, history_titles=history)
    print(f"  最终 {len(final)} 条")

    print("\n[4/5] 构建 JSON / 保存...")
    brief = build_brief_dict(final, headline=headline, overview=overview)
    raw = build_raw_dict(raw_items)
    today = brief["date"]

    print(f"\n{'─' * 50}")
    print(format_plain_text(final, headline=headline, overview=overview))
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
