"""AI 摘要模块 —— 对精选新闻生成一句话摘要。

模仿公众号「每日资讯简报」风格，完整风格要求见 brief_style.STYLE_GUIDE。
"""

import json

import requests

from config import AI_API_URL, AI_API_KEY, AI_MODEL, REQUEST_TIMEOUT
from brief_style import (
    STYLE_SYSTEM_PROMPT,
    build_ai_user_prompt,
    normalize_summary,
)


def is_ai_enabled():
    """检查 AI 是否已配置。"""
    return bool(AI_API_KEY and AI_API_URL)


def ai_enhance(items):
    """对精选新闻列表进行 AI 增强。

    返回 (None, items)：不再生成今日要点；items 每条新增 summary 字段。
    """
    if not is_ai_enabled():
        print("[AI] 未配置 API Key，跳过 AI 增强")
        return None, items

    print(f"[AI] 使用 {AI_MODEL} 生成摘要（每日资讯简报风格）...")

    prompt = build_ai_user_prompt(items)

    try:
        content = _call_api(prompt)
        summaries = _parse_response(content, len(items))
        if summaries is None:
            print("[AI] 响应解析失败，使用原始标题")
            return None, items

        applied = 0
        for i, item in enumerate(items):
            raw = summaries[i] if i < len(summaries) else ""
            final = normalize_summary(item["title"], raw)
            if final != item["title"]:
                applied += 1
            item["summary"] = final

        print(f"[AI] 摘要生成完成：{applied} 条改写")
        return None, items

    except Exception as e:
        print(f"[AI] 调用失败: {e}，使用原始标题")
        return None, items


def _call_api(prompt):
    """调用 OpenAI 兼容 API。"""
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": STYLE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.25,
        "max_tokens": 2500,
    }
    resp = requests.post(AI_API_URL, headers=headers, json=data, timeout=REQUEST_TIMEOUT * 2)
    resp.raise_for_status()
    result = resp.json()
    return result["choices"][0]["message"]["content"]


def _parse_response(content, expected_count):
    """解析 AI 返回的 JSON 响应，仅提取 summaries。"""
    content = content.strip()

    if content.startswith("```"):
        lines = content.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        content = "\n".join(lines).strip()

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
        else:
            return None

    summaries = data.get("summaries", [])
    if not isinstance(summaries, list):
        return None

    while len(summaries) < expected_count:
        summaries.append("")

    return summaries[:expected_count]
