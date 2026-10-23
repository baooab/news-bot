"""配置文件 —— 数据源 + AI 摘要 + 话题排序。"""

import os
from pathlib import Path

# 本地开发：从项目根目录 .env 加载（该文件已在 .gitignore，不会提交）
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

# ============================================================
# 数据源（全部直连）
# ============================================================
# 综合 / 民生：澎湃、中新网、人民网、每日环球视野
# 科技商业：IT之家、36氪、Solidot、凤凰科技

SOURCES = [
    # 澎湃新闻 API（热闻 + 精选 + 财经）
    {"type": "thepaper", "name": "澎湃", "url": "https://cache.thepaper.cn/contentapi/wwwIndex/rightSidebar"},
    # 中新网社会 RSS（民生 / 社会向补充）
    {"type": "rss", "name": "中新网", "url": "https://www.chinanews.com.cn/rss/society.xml"},
    # --- 科技 / 商业 ---
    {"type": "rss", "name": "IT之家", "url": "https://www.ithome.com/rss/"},
    # 36氪 gateway 热榜 API（官方 RSS 已被火山引擎检测拦截）
    {"type": "36kr", "name": "36氪",
     "url": "https://gateway.36kr.com/api/mis/nav/home/nav/rank/hot"},
    # 凤凰网科技频道精选池（JSONP）
    {"type": "ifeng", "name": "凤凰科技",
     "url": "https://shankapi.ifeng.com/season/tech/selectedPoolData/20002/204/cb"},
    {"type": "rss", "name": "Solidot", "url": "https://www.solidot.org/index.rss"},
    # 雷峰网 RSS（AI / 科技深度报道）
    {"type": "rss", "name": "雷峰网", "url": "https://www.leiphone.com/feed"},
]

# ============================================================
# 采集参数
# ============================================================
# 日历窗口：只保留今天 + 昨天（例：7/12 运行时丢弃 7/10 及更早）
# RECENT_CALENDAR_DAYS=2 表示保留 2 个自然日；设为 0 关闭过滤
RECENT_CALENDAR_DAYS = int(os.getenv("RECENT_CALENDAR_DAYS", "2"))
# 喂给 AI 的历史期数：把最近 N 期已发标题列给 AI，由 AI 避免跨期重复
RECENT_DEDUP_DAYS = int(os.getenv("RECENT_DEDUP_DAYS", "5"))
MAX_FETCH_PER_FEED = 60                               # 每个 feed 最多抓取条数
REQUEST_TIMEOUT = 15                                  # 网络超时（秒）

# ============================================================
# 科技资讯（12 科技 + 6 民生社会 = 18 条）
# ============================================================
TECH_QUOTA = 12
GENERAL_QUOTA = 6
TARGET_COUNT = TECH_QUOTA + GENERAL_QUOTA

# 喂给 AI 的候选池上限（上下文保护）：超出时按时间截断，不做任何质量判断
AI_CANDIDATE_LIMIT = int(os.getenv("AI_CANDIDATE_LIMIT", "260"))

# ============================================================
# AI 摘要配置（可选，未配置则跳过 AI 增强）
# ============================================================
# 支持 OpenAI 兼容接口：Deepseek / OpenAI / Moonshot / 通义千问等
# 推荐 Deepseek：价格极低，中文效果好
# 仅需配置 AI_API_KEY 即可；URL / MODEL 有默认值
#   AI_API_URL=https://api.deepseek.com/v1/chat/completions
#   AI_MODEL=deepseek-flash
# 注：deepseek-flash 为现行调用名（实为 V4.1-Flash-1017）；旧名 deepseek-v4-flash 已退役


def _env(key, default=""):
    """读取环境变量；空字符串视为未配置（GitHub Actions 未设 Secret 时会注入空值）。"""
    val = os.getenv(key)
    if val is None or not str(val).strip():
        return default
    return val.strip()


AI_API_URL = _env("AI_API_URL", "https://api.deepseek.com/v1/chat/completions")
AI_MODEL = _env("AI_MODEL", "deepseek-flash")
AI_API_KEY = _env("AI_API_KEY", "")

# 是否开启模型思考（reasoning）。DeepSeek Flash 默认开启，但本任务是结构化选材与
# 改写（非推理题），思考会额外消耗数百至数千 token，既挤占输出额度又拖慢响应。
# 默认关闭；若发现编排质量不足，可设为 enabled。
AI_THINKING = _env("AI_THINKING", "disabled")
