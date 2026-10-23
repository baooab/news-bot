"""「每日资讯简报」公众号风格规范 —— 供 AI 摘要模仿。

参考 365资讯简报 / 每日资讯简报 典型产物与编辑反馈整理。
"""

import re

from quality_filter import is_low_quality_title

# ---------------------------------------------------------------------------
# 风格说明（完整版，附于 AI 提示词）
# ---------------------------------------------------------------------------

STYLE_GUIDE = """
# 「每日资讯简报」风格要求

## 一、整体结构（自上而下）

1. 标题固定为「每日资讯简报」
2. 日期行：公历 + 星期 + 农历（如 2026年07月11日 星期六 农历五月廿七）
3. 正文：12 条新闻，扁平编号 1～12（序号与内容间用顿号，如 1、……）

正文区域**无分类小标题、无媒体来源标签、无今日要点**，读者一眼扫完 12 条。

## 二、正文单条怎么写（核心）

每条 = **谁 + 做了什么 + 结果/数据**，一句话说清，像电报：

| 要素 | 要求 | 示例 |
|------|------|------|
| 主体 | 机构/国家/人物/企业，必须出现 | 央行、统计局、菲律宾、长鑫科技 |
| 动作 | 已发生或已宣布的具体行为 | 发布、批准、造成、启动、开通 |
| 事实 | 措施、结论、事件经过 | 下调起点金额、挂牌督办、发红色预警 |
| 数据 | 有则必留，不可省略 | 1.2%、5000亿元、55人死亡 |

### 推荐句式（按优先级）

1. **机构：具体措施/结论** — 「统计局：5月CPI同比上涨1.2%，环比下降0.1%」
2. **主体 + 动作 + 结果** — 「菲律宾南部强震已造成至少55人死亡、1120人受伤」
3. **主体 + 事件 + 数据** — 「熊猫债存量规模首超5000亿元」

### 语言与篇幅

- 电报体：短句、客观、信息密度高，不加「据悉」「值得注意的是」
- 18～50 字为宜；含多项数据时可略长
- 标题若已清晰完整，可微调措辞但**不得删数字、不得改事实**

## 三、排序逻辑（输入已排好，改写时保持顺序）

国内政策/要闻 → 地方民生 → 社会事件 → 国际新闻 → 其他

## 四、无效条目（禁止写成这样）

以下写法**不是**每日资讯简报风格，必须规避：

1. **猜谜式**：引号内生僻词 + 空洞展望（「百团百项」工程定义上海科创未来）
2. **隐喻式**：拦路虎、闹剧、面临挑战、遭遇波折
3. **观点预测**：官员/专家认为…可能…（无已发生事实）
4. **纯辟谣**：教育部："xxx"系谣言（只说谣言、不说正面事实）
5. **口号套话**：部署抗洪：紧盯高风险区域减少人员伤亡（无具体措施/数字）
6. **空洞通告**：多地发告市民书（无具体安排）
7. **合并快讯**：一条里塞 3 件互不相关的事（应只保留最重要一条）
8. **评论煽情**：可笑闹剧、值得关注、引热议

## 五、合格 vs 不合格对照

| 不合格 | 合格 |
|--------|------|
| 小红书：上市面临挑战 | 小红书赴美 IPO 再因数据合规问题被监管问询 |
| 欧央行官员：AI或加剧通胀波动 | （不合格：纯观点预测，无已发生事实，应跳过） |
| 教育部："教师全面硕士化"系谣言 | 教育部：教师招聘不得强制要求硕士学历（写正面事实） |
| 国常会部署抗洪：紧盯…减少伤亡 | 国常会：启动国家防总四级防汛应急响应 |
""".strip()

# 供 system prompt 使用的精简版
STYLE_SYSTEM_PROMPT = f"""你是「每日资讯简报」公众号的资深编辑，负责把原始标题改写成可直接发布的简报条目。

{STYLE_GUIDE}

你的输出将被程序填入 JSON 的 summaries 数组，每条 summary 对应一条新闻。不要生成今日要点。"""

# 公众号典型写法（few-shot）
STYLE_EXAMPLES = [
    {
        "title": "央行征求意见：将个人投资人认购大额存单起点金额降至不低于20万元人民币",
        "summary": "央行征求意见：将个人投资人认购大额存单起点金额降至不低于20万元人民币",
    },
    {
        "title": "统计局：5月全国居民消费价格同比上涨1.2%，环比下降0.1%",
        "summary": "统计局：5月全国居民消费价格同比上涨1.2%，环比下降0.1%",
    },
    {
        "title": "菲律宾南部强震已造成至少55人死亡、1120人受伤、38人失踪",
        "summary": "菲律宾南部强震已造成至少55人死亡、1120人受伤、38人失踪",
    },
    {
        "title": "国务院安委会对福建泉州“7·9”重大火灾查处挂牌督办",
        "summary": "国务院安委会对福建泉州“7·9”重大火灾查处挂牌督办",
    },
    {
        "title": "最高级别！中央气象台时隔两年再发暴雨红色预警",
        "summary": "中央气象台时隔两年再发暴雨红色预警",
    },
    {
        "title": "市场发行热度大幅升温，熊猫债存量规模首超5000亿元",
        "summary": "熊猫债存量规模首超5000亿元，发行热度大幅升温",
    },
]

TOPIC_LABELS = {
    "national": "国家政策",
    "local": "地方民生",
    "social": "社会事件",
    "international": "国际新闻",
    "other": "其他",
}


def format_style_examples(count=5):
    """格式化 few-shot 范例文本。"""
    lines = []
    for ex in STYLE_EXAMPLES[:count]:
        lines.append(f"原标题：{ex['title']}")
        lines.append(f"简报条目：{ex['summary']}")
        lines.append("")
    return "\n".join(lines).strip()


def build_ai_user_prompt(items):
    """构建含完整风格要求 + 待改写列表的用户提示词。"""
    news_lines = []
    for i, item in enumerate(items):
        topic = TOPIC_LABELS.get(item.get("topic", "other"), "其他")
        news_lines.append(f"{i + 1}. [{topic}] {item['title']}")
    news_list = "\n".join(news_lines)
    n = len(items)

    return f"""请严格按上方「每日资讯简报」风格要求，改写以下 {n} 条新闻。

## 写法范例
{format_style_examples(5)}

## 输出要求
1. summaries 数组长度必须 = {n}，与输入序号一一对应
2. 每条只写一件事；原标题含「丨」「；」等多条快讯时，只保留最重要的一条
3. 保留主体、事件、数字/比例/金额/人数；优先「机构：」句式
4. 不要加序号、不要写来源媒体名

## 待改写新闻（已按 政策→地方→社会→国际 排序）
{news_list}

请严格按 JSON 返回（不要 markdown 代码块）：
{{"summaries": ["条目1", "条目2", ...]}}"""


def _extract_numbers(text):
    return set(re.findall(r"\d+(?:\.\d+)?[%％]?|\d+万|\d+亿", text or ""))


# ============================================================
# AI 灌水检测
# ============================================================

# 尾部废话：AI 常在原标题后追加无信息量的评语
_FLUFF_TAIL = re.compile(
    r"(，|,)?\s*"
    r"(控制成本与资源消耗|引发关注|引发热议|引发讨论|引起关注|备受关注|"
    r"引发市场关注|未来可期|未来已来|值得期待|值得关注|受到关注|"
    r"由谁.{0,8}待定|具体.{0,8}待定|后续.{0,8}待定|"
    r"有望进一步|将进一步|也进一步|正在进一步|"
    r"标志着|象征着|彰显了|体现了|凸显了|"
    r"具有.{0,8}里程碑意义|"
    r"这一消息|此举|该举措|这意味着|可以说|值得一提的是)"
    r"\s*[。\.！!]?$"
)

# 纯口水话（整句只有评语，没有事实）
_FLUFF_ONLY = re.compile(
    r"^[\s，,。.！!？?、；;：:]*(?:"
    r"引发关注|引发热议|值得关注|受到关注|备受瞩目|令人期待|"
    r"未来可期|不容忽视|意义重大|影响深远|"
    r".+引发(?:了)?(?:广泛|热烈)?(?:关注|热议|讨论)"
    r")[\s。.！!]*$"
)

# 句末多余标点
_TRAILING_PUNCT = re.compile(r"[。\.，,；;、\s]+$")

# 已知合法英文词（含驼峰），不被拆分
_KEEP_TOGETHER = {
    "deepmind", "openai", "chatgpt", "github", "gitlab", "kubernetes",
    "javascript", "typescript", "python", "linux", "android", "iphone", "ipad",
    "macbook", "imac", "icloud", "itunes", "webcam", "airpods", "cann",
    "pytorch", "tensorflow", "langchain", "midjourney", "huggingface",
    "gemma", "wenxin", "mistral", "mixtral", "copilot", "linkedin", "openjdk",
    "gradle", "maven", "kotlin", "swift", "unity", "unreal", "ffmpeg",
    "mpeg4", "sha256", "base64", "utf8", "ipv4", "ipv6", "wifi", "bluetooth",
    "spacex", "apple", "google", "microsoft", "amazon", "meta", "tesla",
    "nvidia", "amd", "intel", "samsung", "huawei", "xiaomi", "alibaba",
    "tencent", "baidu", "bytedance", "tiktok", "oracle", "rust", "unity3d",
}

# 中英粘连：中文后紧跟英文单词
_GLUE_CJK_LATIN = re.compile(r"(?<=[一-鿿])(?=[A-Za-z][a-z])")
# 英文粘连：驼峰但不在白名单内（如 AIToken）
_GLUE_CAMEL = re.compile(r"(?<=[a-z])(?=[A-Z])")

# 常见实体粘连修复表：粘连形态 -> 正确写法
_KNOWN_GLUE = {
    "spacexai": "SpaceX AI",
    "aitoken": "AI Token",
    "aichatgpt": "AI ChatGPT",
    "openaigpt": "OpenAI GPT",
    "chatgptapp": "ChatGPT App",
    "appleintelligence": "Apple Intelligence",
    "googledeepmind": "Google DeepMind",
    "applevision": "Apple Vision",
    "byteDance": "ByteDance",
    "huggingface": "Hugging Face",
    "openai o1": "OpenAI o1",
}


def _fix_glue(text):
    """修复中英粘连词（如 AIToken / SpaceXAI），保留已知英文单词原样。"""
    if not text:
        return text

    # 1) 已知粘连形态精确修复（不区分大小写匹配词边界）
    def _known(m):
        low = m.group(0).lower()
        if low in _KNOWN_GLUE:
            return " " + _KNOWN_GLUE[low]
        return m.group(0)

    text = re.sub(r"[A-Za-z][A-Za-z0-9]*", _known, text)

    def _split_camel(m):
        seg = m.group(0)
        if seg.lower() in _KEEP_TOGETHER:
            return seg
        # 在驼峰处插入空格：AI Token / Space X AI
        parts = re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z]+|[a-z]+", seg)
        if len(parts) >= 2:
            return " " + " ".join(parts)
        return seg

    # 2) 驼峰拆分
    text = _GLUE_CAMEL.sub(_split_camel, text)
    # 3) 中文与英文之间补空格
    text = _GLUE_CJK_LATIN.sub(" ", text)

    return re.sub(r"[ \t]{2,}", " ", text).strip()


def _strip_fluff(text):
    """剥离尾部废话与多余标点。"""
    if not text:
        return text
    text = _TRAILING_PUNCT.sub("", text.strip())
    prev = None
    while prev != text:
        prev = text
        text = _FLUFF_TAIL.sub("", text).strip()
        text = _TRAILING_PUNCT.sub("", text)
    return text


def validate_summary(title, summary):
    """校验 AI 摘要是否符合简报风格；不合格则回退原标题。"""
    summary = (summary or "").strip()
    if not summary or len(summary) < 6:
        return False

    # 0) 纯口水话，无事实
    if _FLUFF_ONLY.match(summary):
        return False

    # 1) 尾部灌水：剥离后若信息量不足则判不合格
    stripped = _strip_fluff(summary)
    if len(stripped) < len(summary):
        if len(stripped) < 8:
            return False
        if not validate_summary(title, stripped):
            return False
        summary = stripped

    # 2) 整体比原标题长出太多 —— AI 在复述/扩写
    if len(summary) > max(len(title) * 1.6, len(title) + 12):
        return False

    bad, _ = is_low_quality_title(summary)
    if bad:
        return False

    title_nums = _extract_numbers(title)
    if title_nums and not (_extract_numbers(summary) & title_nums):
        return False

    if len(summary) < len(title) * 0.35 and not _extract_numbers(summary):
        return False

    return True


def normalize_summary(title, summary):
    """校验不通过时回退原标题；并清洗粘连词、尾部废话。"""
    summary = (summary or "").strip()
    summary = re.sub(r"^\d+[\.、\)]\s*", "", summary)
    summary = _fix_glue(summary)
    summary = _strip_fluff(summary)
    if validate_summary(title, summary):
        return summary
    # 回退时同样清洗原标题，避免粘连词带入成品
    return _fix_glue(title)
