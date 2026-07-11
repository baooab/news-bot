"""每日资讯简报 —— 主入口（GitHub Actions）。

流程：
  采集全部数据源原始数据（存档）
  -> 24h 过滤 -> 去重 -> 质量过滤 -> 话题排序 -> 精选 12 条
  -> AI 摘要增强 -> 无效条目过滤/递补 -> 构建简报 JSON
  -> 输出 data/briefs/YYYY-MM-DD.json（简报）
     data/raw/YYYY-MM-DD.json（全部原始数据，供参考）
     data/index.json（简报索引，供首页读取）

最终产物为 JSON 数据，由网页（index.html / brief.html，Bulma）承载渲染。
"""

import os
import json
import glob
from datetime import datetime

from config import TARGET_COUNT
from fetchers import collect_raw, process_news, fmt_pub_time
from formatter import select_items, format_plain_text, build_brief_dict
from ai_summary import ai_enhance, is_ai_enabled
from quality_filter import filter_selected_items

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
BRIEFS_DIR = os.path.join(DATA_DIR, "briefs")
RAW_DIR = os.path.join(DATA_DIR, "raw")

WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def build_raw_dict(raw_items):
    """把原始条目按来源分组，构建原始数据 JSON 结构。"""
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


def main():
    print("=" * 55)
    print("  每日资讯简报 —— 开始执行")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    # 1. 采集原始数据（完整存档）
    from config import SOURCES
    print(f"\n[1/6] 采集新闻（{len(SOURCES)} 大数据源）...")
    raw_items = collect_raw()
    if not raw_items:
        print("[ERROR] 未获取到任何新闻")
        return False

    # 2. 处理：过滤 -> 去重 -> 分类 -> 排序
    print("\n[2/6] 过滤 / 去重 / 排序...")
    sorted_news = process_news(raw_items)
    print(f"  可用新闻：{len(sorted_news)} 条")

    # 3. 选条
    print(f"\n[3/6] 精选 {TARGET_COUNT} 条...")
    selected = select_items(sorted_news)
    print(f"  入选 {len(selected)} 条")

    # 4. AI 摘要
    print("\n[4/6] AI 摘要增强...")
    if is_ai_enabled():
        _, enhanced = ai_enhance(selected)
    else:
        print("  [跳过] 未配置 AI API（设置 AI_API_URL + AI_API_KEY 启用）")
        enhanced = selected

    # 4b. 过滤 AI 产出中的无效条目，从候选池递补
    print("\n[4b/6] 过滤无效条目 / 递补...")
    enhanced = filter_selected_items(enhanced, sorted_news, count=TARGET_COUNT)
    print(f"  最终入选 {len(enhanced)} 条")

    # 5. 构建 JSON
    print("\n[5/6] 构建 JSON...")
    brief = build_brief_dict(enhanced)
    raw = build_raw_dict(raw_items)

    # 控制台预览
    print(f"\n{'─' * 50}")
    print(format_plain_text(enhanced))
    print(f"{'─' * 50}")

    # 6. 写入文件
    print("\n[6/6] 保存 JSON...")
    today = brief["date"]

    brief_path = os.path.join(BRIEFS_DIR, f"{today}.json")
    raw_path = os.path.join(RAW_DIR, f"{today}.json")

    _write_json(brief_path, brief)
    print(f"  简报:   data/briefs/{today}.json（{brief['count']} 条）")

    _write_json(raw_path, raw)
    print(f"  原始:   data/raw/{today}.json（{raw['total']} 条 / {len(raw['sources'])} 源）")

    generate_index()

    print(f"\n{'=' * 55}")
    print("  执行完成！")
    print(f"{'=' * 55}")
    return True


def generate_index():
    """扫描 data/briefs/*.json 生成 data/index.json（供首页读取）。"""
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
            "count": data.get("count", 0),
            "overview": data.get("overview", ""),
            "sources": data.get("sources", []),
        })

    index = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(briefs),
        "briefs": briefs,
    }
    _write_json(os.path.join(DATA_DIR, "index.json"), index)
    print(f"  索引:   data/index.json（{len(briefs)} 篇）")


if __name__ == "__main__":
    main()
