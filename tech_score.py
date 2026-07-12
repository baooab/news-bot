"""科技相关性打分 —— 供科技资讯系列选条使用。"""

import re

from config import (
    TECH_SOURCE_SCORES,
    TECH_KEYWORDS,
    TECH_ANTI_KEYWORDS,
    TECH_SCORE_THRESHOLD,
)


_DISASTER = re.compile(r"台风|暴雨|洪涝|防汛|抗洪|红色预警")


def score_tech_relevance(item):
    """返回 0–100 的科技相关性分数。"""
    title = (item.get("title") or "").strip()
    source = item.get("source", "")
    if not title:
        return 0

    score = TECH_SOURCE_SCORES.get(source, 0)

    title_upper = title.upper()
    for kw in TECH_KEYWORDS:
        if kw.upper() in title_upper or kw in title:
            score += 8

    for kw in TECH_ANTI_KEYWORDS:
        if kw in title:
            score -= 20

    # 含数字/版本号略加分
    if re.search(r"\d+(?:\.\d+)+|\d+[%％]|v\d+", title, re.I):
        score += 5

    return max(0, min(100, score))


def is_tech_item(item, threshold=TECH_SCORE_THRESHOLD):
    return score_tech_relevance(item) >= threshold


def is_disaster_title(title):
    return bool(_DISASTER.search(title or ""))


def annotate_tech_scores(items):
    """为条目附加 tech_score 字段（原地修改）。"""
    for item in items:
        item["tech_score"] = score_tech_relevance(item)
    return items
