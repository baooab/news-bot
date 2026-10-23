"""AI 主编模块 —— 选材 + 分区 + 排序 + 摘要 + 期标题 + 导语，全权交由 AI。

本地不做任何内容过滤：原始候选池（仅做过时间窗口与同题去重）整体交给 AI，
AI 自行剔除软文/通稿/重复报道，并完成分区与编排。本地只做：
  1. 输出契约校验（idx 合法、配额、摘要格式）
  2. 摘要串台检测（summary_matches_title，不合格回退原标题）
  3. AI 漏选时的机械递补（按时间顺序，不做质量判断）
  4. AI 不可用 / 解析失败时的机械兜底
"""

import json

import requests

from config import (
    AI_API_URL, AI_API_KEY, AI_MODEL, AI_THINKING, REQUEST_TIMEOUT,
    TECH_QUOTA, GENERAL_QUOTA, TARGET_COUNT,
)
from tech_brief_style import (
    TECH_STYLE_SYSTEM_PROMPT,
    build_tech_ai_user_prompt,
    normalize_tech_summary,
    normalize_headline,
)
from editorial_check import build_fallback_overview, normalize_overview


def is_ai_enabled():
    return bool(AI_API_KEY and AI_API_URL)


def ai_compose(candidates, history_titles=None):
    """把原始候选池全权交给 AI 主编。

    参数：
      candidates      原始候选条目列表（时间倒序，已同题去重）
      history_titles  近 N 期已发布标题（跨期去重依据，由 AI 判断）

    返回 (headline, items, overview)：
      headline  本期两段式标题
      items     最终条目（AI 选中的 + 机械递补的），每条含 summary / section
      overview  本期导语
    """
    if not is_ai_enabled():
        print("[AI] 未配置 API Key，使用时间倒序机械兜底")
        return _fallback_compose(candidates)

    print(f"[AI] 使用 {AI_MODEL} 选材编排（候选 {len(candidates)} 条，全权交由 AI）...")

    try:
        content = _call_api(build_tech_ai_user_prompt(candidates, history_titles))
        parsed = _parse_response(content)
        if parsed is None:
            print("[AI] 响应解析失败，使用机械兜底")
            return _fallback_compose(candidates)

        final, ai_cnt, fill_cnt = _apply_selection(parsed.get("items") or [], candidates)
        print(f"[AI] 主编选中 {ai_cnt} 条" + (f"，机械递补 {fill_cnt} 条" if fill_cnt else ""))

        # 导语：校验通过才采用，不合格走程序化兜底（只陈述可核对的事实）
        raw_overview = parsed.get("overview", "")
        overview = normalize_overview(raw_overview, final)
        if overview:
            print(f"[AI] 导语：{overview[:40]}…")
        else:
            if raw_overview.strip():
                print(f"[AI] 导语未通过校验，原文：{raw_overview[:80]}")
            overview = build_fallback_overview(final, tech_count=TECH_QUOTA)
            if overview:
                print(f"[AI] 使用事实兜底导语：{overview[:40]}…")

        headline = normalize_headline(parsed.get("headline", ""), final)
        print(f"[AI] 期标题：{headline}")
        return headline, final, overview

    except Exception as e:
        print(f"[AI] 调用失败: {e}，使用机械兜底")
        return _fallback_compose(candidates)


# ---------------------------------------------------------------------------
# AI 输出 → 最终条目
# ---------------------------------------------------------------------------

def _apply_selection(ai_items, candidates):
    """按 AI 的选择构建最终条目；配额不足时机械递补。

    返回 (final_items, ai_selected_count, filled_count)。
    """
    n = len(candidates)
    final = []
    used = set()
    tech_cnt = gen_cnt = 0

    for it in ai_items:
        try:
            idx = int(it.get("idx"))
        except (TypeError, ValueError):
            continue
        if not (0 <= idx < n) or idx in used:
            continue

        section = "general" if it.get("section") == "general" else "tech"
        if section == "tech" and tech_cnt >= TECH_QUOTA:
            continue
        if section == "general" and gen_cnt >= GENERAL_QUOTA:
            continue

        cand = dict(candidates[idx])
        cand["section"] = section
        cand["summary"] = normalize_tech_summary(cand["title"], it.get("summary", ""))
        final.append(cand)
        used.add(idx)
        if section == "tech":
            tech_cnt += 1
        else:
            gen_cnt += 1

    ai_cnt = len(final)

    # 机械递补：AI 漏选时按候选顺序（时间倒序）补足配额，不做质量判断
    filled = 0
    for idx, cand in enumerate(candidates):
        if tech_cnt >= TECH_QUOTA and gen_cnt >= GENERAL_QUOTA:
            break
        if idx in used:
            continue
        cand = dict(cand)
        if tech_cnt < TECH_QUOTA:
            cand["section"] = "tech"
            tech_cnt += 1
        else:
            cand["section"] = "general"
            gen_cnt += 1
        cand["summary"] = ""
        final.append(cand)
        used.add(idx)
        filled += 1

    # 稳定排序：科技在前民生在后，AI 给出的相对顺序保留
    final.sort(key=lambda x: 0 if x["section"] == "tech" else 1)
    return final, ai_cnt, filled


def _fallback_compose(candidates):
    """AI 不可用 / 失败时的机械兜底：时间倒序取前 TARGET_COUNT 条，用原标题。"""
    items = [dict(it) for it in candidates[:TARGET_COUNT]]
    for i, it in enumerate(items):
        it["section"] = "tech" if i < TECH_QUOTA else "general"
        it["summary"] = ""
    headline = normalize_headline("", items)
    return headline, items, ""


# ---------------------------------------------------------------------------
# API 调用与解析
# ---------------------------------------------------------------------------

def _call_api(prompt):
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": TECH_STYLE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.45,
        # 输出：18 条 {idx, section, summary} + 导语 + 期标题
        "max_tokens": 5200,
        # 关闭思考：选材改写属提取类任务，思考会挤占输出额度且拖慢响应
        "thinking": {
            "type": "enabled" if AI_THINKING.lower() == "enabled" else "disabled"
        },
    }
    resp = requests.post(AI_API_URL, headers=headers, json=data, timeout=REQUEST_TIMEOUT * 2)
    resp.raise_for_status()
    result = resp.json()
    return result["choices"][0]["message"]["content"]


def _parse_response(content):
    """解析 AI 返回的 JSON；返回 {items, headline, overview} 或 None。"""
    content = (content or "").strip()

    if content.startswith("```"):
        lines = [l for l in content.split("\n") if not l.strip().startswith("```")]
        content = "\n".join(lines).strip()

    data = None
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(content[start:end + 1])
            except json.JSONDecodeError:
                return None
    if not isinstance(data, dict):
        return None

    items = data.get("items")
    if not isinstance(items, list):
        return None

    cleaned = []
    for it in items:
        if not isinstance(it, dict):
            continue
        cleaned.append({
            "idx": it.get("idx"),
            "section": it.get("section", "tech"),
            "summary": it.get("summary", "") or "",
        })

    return {
        "items": cleaned,
        "headline": data.get("headline", ""),
        "overview": data.get("overview", "") or "",
    }
