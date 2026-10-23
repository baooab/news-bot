"""「科技资讯」系列风格规范 —— 供 AI 摘要使用（贴图公众号）。"""

import re

from config import TECH_QUOTA, GENERAL_QUOTA, TARGET_COUNT
from brief_style import validate_summary, _fix_glue, _strip_fluff
from quality_filter import is_low_quality_title
from editorial_check import is_vague, anchor_count, summary_matches_title

TECH_STYLE_GUIDE = f"""
# 「科技资讯」贴图系列风格要求

## 整体结构
- 标题系列名：科技资讯（或每日科技资讯）
- 共 {TARGET_COUNT} 条：{TECH_QUOTA} 条科技向 + {GENERAL_QUOTA} 条民生社会（国内民生、社会新闻）
- 扁平编号，无分类小标题、无媒体来源名

## 科技条
- 读者是开发者 / 科技从业者，一句话说清：**谁 + 做了什么 + 关键数据**
- 保留产品名、模型名、版本号、金额、人数等技术实体
- 可在句末用极短影响（≤12 字），如「有望降低发射成本」；禁止空泛评论
- 18～50 字；电报体，不加「据悉」「值得关注」

## 民生社会条
- 国内民生、社会新闻：事故、灾害、教育医疗、消费维权等
- 排除政治执纪反腐（贪污、受贿、双开、立案审查等）
- 排除政治争端与领土主权（南海、台海、两岸、军演等）
- 排除军事军购军备（台军、军购、武器升级等）
- 电报体，保留主体、事件、数字；优先已发生事实

## 禁止写法（与综合简报相同）
- 猜谜式、隐喻式、纯辟谣、口号套话、合并快讯、煽情评论
""".strip()


# ---------------------------------------------------------------------------
# 选材职责：原本地过滤规则全部翻译为 AI 指令（本地不再做任何内容过滤）
# ---------------------------------------------------------------------------

SELECTION_RULES = f"""
# 选材职责（与编排同权重的重要工作）

编辑部采集器不做任何筛选，下面是**未过滤的原始候选池**，混杂着软文、通稿、
营销稿、重复报道。你需要自己完成全部筛选判断：

## 一、这些条目一律不选（即使它看起来像新闻）

1. **软文 / 广告 / 导购**：促销、开售、售价、到手价、国补、以旧换新、
   限时优惠、黄牛溢价、门店活动、运营商套餐资费、福利抽奖
2. **消费电子通稿**：「XX 手机/耳机/显示器上市开售」「三款配色公布」
   「上手/开箱/实测/体验/评测」——产品营销而非行业事件
   （例外：出货量/市场份额/财报等带行业数据的可以选）
3. **发布会通稿**：「XX 发布会举行/圆满举办」「现场展示」——无产品或技术事实
4. **厂商宣传稿**：「助力 XX 规模化落地」「赋能行业」「提供 XX 方案」
5. **预告 / 预热 / 传闻**：即将发布、或将于、爆料称、疑似、谍照
6. **表演 / 猎奇 / 八卦**：机器人翻跟头、互撕、争议回应、娱乐明星
7. **盘点 / 榜单 / 观点文**：盘点、一图看懂、为什么、如何看、「别只盯着 X」
8. **辟谣提醒稿**：「警惕涉 XX 不实信息」「网传系谣言」——本身无信息量
9. **会议通知 / 活动综述**：年会举行、巡展启动、征文、签约仪式
10. **标题党 / 情绪化**：真香、赢麻、炸裂、血亏、等等党

## 二、民生社会区的选材边界

民生社会条只收**国内民生实事**：事故灾害伤亡、案件通报、教育医疗、
社保医保、出行基建、物价消费维权、新规实施。
- 不收：政治执纪反腐（双开/落马/审查调查）、领土主权与台海（南海/两岸/军演）、
  军事军购、娱乐体育游戏、美食旅游星座、国际军事与涉外经贸
- 国际科技/财经事件放科技区，不放民生区

## 三、去重（三重）

1. **同事件多源**：同一事件被多个源报道（标题高度相似），只选信息量最大的
   一条（数字更全、主体更明确的）
2. **同主体多动作**：同一家公司/产品同一天多条动作，只选最重要的一条
3. **跨期不重复**：下方给出近期已发布的标题清单，**这些新闻不要选**；
   同一事件的全新进展可以选，但摘要要体现「新」在哪

## 四、配额是硬约束

- **必须选满 {TECH_QUOTA} 条科技 + {GENERAL_QUOTA} 条民生，恰好 {TARGET_COUNT} 条，不能少选**
- 如果候选池里完美条目不足，从剩余候选中挑**相对最好**的补足配额
  （例如行业数据类报道、地方性但真实的民生新闻），仍然避开明确的软文/广告
- 禁止把空缺留给系统：你少选一条，就会有一条未经判断的条目被机械递补进来，
  那反而更不可控
- 科技条优先级：格局性事件（融资收购/禁令制裁/重大漏洞/开源发布/数据突破）
  > 产品与技术进展 > 行业数据；民生条优先级：伤亡与重大公共事件 > 政策落地 > 地方民生
""".strip()


# ---------------------------------------------------------------------------
# 主编视角：编排原则（写给 AI 的方法论，不是模板）
# ---------------------------------------------------------------------------

EDITORIAL_PRINCIPLES = f"""
# 你现在扮演的角色

你不是转写员，是**这份简报的主编**。编辑部里 {TARGET_COUNT} 条资讯是记者交上来的采访素材，
交上来的时候是散的、乱的、按抓取时间堆的。你的工作是当主编：
**先读懂这批素材共同在讲什么，再决定怎么编排。**

## 一、先判断，后动笔（最高优先级）

动笔前必须先回答一个问题：**这 {TARGET_COUNT} 条串起来，是一条什么主线？**

- {TARGET_COUNT} 条往往不是 {TARGET_COUNT} 个独立事件，而是同一件大事的多个侧面
  （例如：多家公司同时下调推理成本 → 主线是「AI 竞争从堆参数转向拼性价比」；
  一边融资、一边裁员、一边降价 → 主线是「行业进入洗牌期」）
- 如果找不到主线，说明这批素材本身没有故事，**那就老老实实按重要性排序，不要硬造趋势**
- **禁止硬造主线**：为了显得有观点而把不相关的新闻强行说成"一场变革"，是本报最严重的错误

## 二、编排（arrangement）——你有权重新排序

- **重排 {TARGET_COUNT} 条的顺序**，让读者按你的主线读下来，而不是按抓取时间
- 排序逻辑：**最有信号量的开头** → 沿着主线展开 → 支撑性事件在后 → 民生社会垫底
- 科技条内部：通常「格局性事件 / 战略级动作」在前，「产品更新 / 单点进展」在后
- 民生社会条内部：按社会影响范围排序，伤亡与重大公共事件在前
- **但**：重排后同类条目不能扎堆（如连续 3 条都是发布会），要有节奏

## 三、大历史观（historical perspective）

「历史观」不是写"这是划时代的时刻"这种废话。**大历史观 = 把这批新闻放回它所在的产业时间轴上。**

你要有这样的判断力：
- **找到坐标**：这条新闻处在什么位置？是先驱者、跟随者，还是被颠覆的旧玩家？
- **看到趋势方向**：技术演进往哪走？成本曲线、替代关系、力量对比在如何变化？
- **看到阶段判断**：这是「萌芽期 / 扩张期 / 洗牌期 / 成熟期」的哪个阶段？
- **看到矛盾**：补贴与退坡、开放与封闭、扩张与代价、效率与规模——当日新闻里常常同时出现对立面

好的大历史观长这样（**必须落在具体事实上**）：
- 「AI 竞争正从比参数转向比成本」
- 「开源阵营开始用价格战挤压闭源」
- 「算力扩张的代价第一次被摆到台面上」
- 「行业从跑马圈地进入洗牌阶段」

差的（**一律禁止**）：
- 「科技浪潮席卷全球」「AI 正在改变世界」「新时代已经开启」
- 「这将是一场深刻的变革」「历史性的一刻」
- 任何脱离本期具体事实的抒情与感叹

## 四、言之有物（substance）——大历史观的落地要求

**每一个判断都必须挂在具体事实上。** 这是本系列的核心纪律。

写期标题和导语时：
- 每句话至少要有一个**具体锚点**：公司名、产品名、模型名、版本号、金额、人数、
  百分比、时间跨度、明确的动作动词（发布/开源/降价/裁员/收购/下架/落地）
- 「模型成本下降」是空话；「MiniMax 开源模型上线 72 小时处理 Token 超 100 万亿」是实话
- 「巨头混战」是空话；「谷歌为建数据中心清场 25 万棵树」是实话
- 判断可以拔高，但**必须同时给出依据**，让读者自己也能验证

反例对照（这些是本报明令禁止的写法）：
| 禁止 | 合格 |
|------|------|
| AI 大模型竞争进入白热化阶段 | OpenAI、谷歌同日发布推理模型，价格战从能力转向单价 |
| 科技巨头纷纷加码算力投资 | 谷歌为建 AI 数据中心非法清场 25 万棵树 |
| 开源生态正在改变行业格局 | DeepSeek 参与宇树科技上市配售，金额约 1.41 亿元 |

## 五、导语（overview）——本期主线

导语是给读者的一句话地图，2～3 句、40～120 字：
- 第一句：**本期主线**，即这批新闻合起来在讲什么趋势（带具体锚点）
- 第二句：**主线里最关键的事实或矛盾**（带数字）
- 不要复述标题，不要写"今天带来 N 条科技资讯"，不要抒情

好例：
> 本期主线是 AI 推理成本被击穿——MiniMax 开源模型 72 小时处理 Token 超 100 万亿，
> OpenAI 同日被曝 AI 监控系统存在漏洞。能力竞赛正在变成成本与可信度的竞赛。

差例：
> 今天科技圈发生了很多interesting的事情，AI 发展日新月异，让我们一起拭目以待。

## 六、禁止写法（与综合简报相同）
- 猜谜式、隐喻式、纯辟谣、口号套话、合并快讯、煽情评论
""".strip()


TECH_STYLE_SYSTEM_PROMPT = f"""你是科技公众号「科技资讯」系列的**资深科技主编**，负责把编辑部采集到的当日原始资讯**选材并编排**成一期可发布的简报。

{SELECTION_RULES}

{EDITORIAL_PRINCIPLES}

## 期标题（headline）——强制两段式
- **必须**写成「看点A，看点B」：用**中文逗号「，」**连接**恰好两段**（不要用分号、破折号等其他分隔符）
- 段一 = **主线判断**（体现趋势/格局/阶段，带具体锚点）；段二 = **最能支撑它的核心事实**
- 两段各自：主体 + 关键动作/数据；每段约 8～22 字，**合计不超过 40 字**
- **每段最多一个数字 + 一个公司名/产品名**，不要往段里塞多个事实
- 优先挑科技条里最抓眼的两条（数字、公司名、产品名优先）
- 不要用「科技资讯」「每日简报」等系列名；不要加日期、序号、引号
- **禁止**：单句标题、空泛套话（如「今日硬科技看点速览」「科技热点速递」「今日看点」）
- **禁止**：无锚点的历史判断（如「科技浪潮席卷全球」「AI 改变世界」「新时代开启」）
- 正例：「推理成本战开打，MiniMax开源模型72小时破百亿Token」「谷歌清场25万棵树建数据中心，算力代价上台面」
- 反例：「Google Earth 发布然后撤回了 AI 工具」（只有一段）、「今日硬科技看点速览」（空话）、
  「AI 竞争进入白热化」（无锚点）

输出 JSON：items 数组（选中条目，按最终顺序排列，科技在前民生在后）、headline 期标题、overview 导语。
不要生成今日要点。"""

TECH_STYLE_EXAMPLES = [
    {
        "title": "苹果起诉 OpenAI，指控前员工窃取未发布硬件商业机密",
        "summary": "苹果起诉 OpenAI：指控前员工窃取未发布硬件机密文件",
    },
    {
        "title": "长征十号乙火箭一子级海上回收成功，年底前将复用飞行",
        "summary": "长征十号乙：一子级海上网系回收成功，计划年底前复用飞行",
    },
    {
        "title": "OpenRouter 数据显示近半数美国公司调用中国 AI 模型",
        "summary": "OpenRouter：美国企业调用中国 AI 模型占比峰值达 46%",
    },
    {
        "title": "菲律宾南部强震已造成至少55人死亡、1120人受伤",
        "summary": "菲律宾南部强震已造成至少55人死亡、1120人受伤",
    },
]


def format_tech_examples(count=4):
    lines = []
    for ex in TECH_STYLE_EXAMPLES[:count]:
        lines.append(f"原标题：{ex['title']}")
        lines.append(f"贴图条目：{ex['summary']}")
        lines.append("")
    return "\n".join(lines).strip()


def build_tech_ai_user_prompt(items, history_titles=None):
    """构建 AI 主编的 user prompt：原始候选池 + 近期已发标题。"""
    news_lines = []
    for i, item in enumerate(items):
        news_lines.append(f"{i}. [{item['source']}] {item['title']}")
    news_list = "\n".join(news_lines)
    n = len(items)

    history_block = ""
    history = [t for t in (history_titles or []) if t]
    if history:
        hist_lines = "\n".join(f"- {t}" for t in history)
        history_block = f"""
## 近期已发布过的标题（跨期去重依据，以下新闻不要重复选入）
{hist_lines}
"""

    return f"""以下是编辑部采集到的今日 {n} 条**未过滤**原始资讯（已按时间倒序，仅做过同题去重）。

请以**资深科技主编**的身份完成本期制作：先筛选（剔除软文/通稿/重复），再判断主线，
然后排序、改写、起标题、写导语。

## 写法范例（单条改写的语感参考）
{format_tech_examples(4)}

## 本期要交付什么

1. **items** —— 恰好 {TECH_QUOTA + GENERAL_QUOTA} 个对象，**数组顺序 = 简报最终顺序**
   （科技条在前、民生条在后；科技条内部最有信号量的在前）。
   每个对象：
   - **idx**：候选条目的原编号（下面列表里行首的数字），不得重复
   - **section**："tech"（科技条）或 "general"（民生社会条）
   - **summary**：18～50 字电报体，谁 + 做了什么 + 关键数据。
     保留产品名、模型名、版本号、金额、人数；不写来源媒体，不加序号。
     科技条可在句末加 ≤12 字的具体影响；民生条纯事实。

2. **overview** —— 本期导语，2～3 句、40～120 字。
   第一句写主线（选中的新闻合起来在讲什么趋势），第二句写主线里最关键的事实或矛盾。
   **每一句都要有具体锚点**（公司名/产品名/金额/人数/百分比/版本号）。
   禁止「AI 日新月异」「科技浪潮」「令人振奋」这类空话；禁止复述标题。

3. **headline** —— 期标题，**恰好两段**「主线判断，核心事实」，用**中文逗号「，」**分隔。
   段一体现趋势判断（带锚点），段二给出支撑它的关键事实。
   每段 8～22 字、合计不超过 40 字；每段最多一个数字 + 一个公司/产品名。
   禁止单句、禁止空泛套话、禁止无锚点的历史判断、禁止超长。

## 编排前先自问
- 选出来的这 {TECH_QUOTA + GENERAL_QUOTA} 条是不是同一件大事的多个侧面？如果是，主线是什么？
- 有没有对立面同时出现（涨价与降价、扩张与代价、开放与封闭）？
- 如果确实找不到主线，就按重要性排序，不要硬造趋势。
{history_block}
## 待筛选与编排的原始候选（编号即 idx）
{news_list}

请严格按 JSON 返回（不要 markdown 代码块）：
{{"items": [{{"idx": 37, "section": "tech", "summary": "……"}}, {{"idx": 12, "section": "general", "summary": "……"}}, …], "overview": "本期主线……", "headline": "看点A，看点B"}}"""


# 空泛期标题（禁止出现）
_GENERIC_HEADLINE = re.compile(
    r"(今日|每日|本期).{0,6}(看点|速览|速递|盘点|汇总|热点)"
    r"|硬科技看点|科技看点|资讯速览|科技速递|热点速览|一图看懂|一文读懂"
)


def normalize_tech_summary(title, summary):
    """科技条目摘要归一：清洗粘连词与尾部废话，不合格回退原标题。

    额外拦截「串台」——AI 把别的条目的内容写进来（成品会出现两条一模一样的文案）。
    """
    summary = (summary or "").strip()
    summary = re.sub(r"^\d+[\.、\)]\s*", "", summary)
    summary = _fix_glue(summary)
    summary = _strip_fluff(summary)
    if validate_summary(title, summary):
        # 摘要必须确实在讲这条标题的事
        if not summary_matches_title(title, summary):
            return _fix_glue(title)
        return summary
    return _fix_glue(title)


def _compress_clause(text, max_len=18):
    """把单条新闻压成适合期标题的短句。

    截断时按「完整词」切，绝不从实体中间切断
    （如 macOS26.6.1 → macOS26.6.1T、M3.1 Flash → M3.1Fl）。
    """
    text = (text or "").strip()
    text = re.sub(r"^\d+[\.、\)]\s*", "", text)
    text = text.strip("「」『』“”\"'【】[]")
    # 只取第一分句
    text = re.split(r"[，,。；;：:\n|｜/、]", text, maxsplit=1)[0].strip()
    text = _tidy_segment(text)
    if len(text) <= max_len:
        return text

    # 按完整词切分：中文逐字，拉丁/数字整体算一个词
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9.\-]*|[一-鿿]|\s+", text)
    kept, length = [], 0
    prev_was_space = True
    for tok in tokens:
        if tok.isspace():
            prev_was_space = True
            continue
        # 拉丁/数字词之间保留空格（M3.1 Flash）
        needs_space = (
            prev_was_space
            and kept
            and re.match(r"[A-Za-z0-9]", tok)
            and re.search(r"[A-Za-z0-9]$", kept[-1])
            and not re.search(r"[一-鿿]$", kept[-1])
        )
        extra = 1 if needs_space else 0
        if length + len(tok) + extra > max_len:
            break
        if needs_space:
            kept.append(" ")
        kept.append(tok)
        length += len(tok) + extra
        prev_was_space = False

    out = "".join(kept).strip().rstrip("的了吗呢吧与及和")
    # 去掉末尾残缺的英文片段（如 26.6.1T → 26.6.1）
    out = re.sub(r"[A-Za-z0-9]\d[A-Za-z]$", "", out)
    return out


def _tidy_segment(text):
    """规范中英混排间距：中文与拉丁/数字之间不留空格，拉丁词之间保留空格。

    「M3.1 Flash」保留词内空格；「谷歌 为建」去掉中文间多余空格。
    """
    text = re.sub(r"[ \t]{2,}", " ", (text or "").strip())
    text = re.sub(r"(?<=[一-鿿])[ \t]+(?=[A-Za-z0-9])", "", text)
    text = re.sub(r"(?<=[A-Za-z0-9])[ \t]+(?=[一-鿿])", "", text)
    return text.strip()

def _split_two_parts(text):
    """尝试拆成恰好两段；成功返回 (a, b)，否则 None。

    分隔符：中文/英文逗号（主），分号（兼容 AI 偶尔用「；」分段）。
    """
    text = (text or "").strip()
    if not text:
        return None

    for sep in ("，", ",", "；", ";"):
        if sep not in text:
            continue
        parts = [p.strip() for p in text.split(sep) if p.strip()]
        # 恰好两段；多于两段说明不是规范期标题
        if len(parts) == 2:
            # 规范中英间距：中文与拉丁间不留空格，拉丁词间保留（如 M3.1 Flash）
            a = _tidy_segment(parts[0])
            b = _tidy_segment(parts[1])
            if a and b:
                return a, b
        return None
    return None


def is_valid_headline(text):
    """两段式期标题是否合格。"""
    text = (text or "").strip()
    if not text or _GENERIC_HEADLINE.search(text):
        return False
    parts = _split_two_parts(text)
    if not parts:
        return False
    a, b = parts
    if a == b:
        return False
    if not (4 <= len(a) <= 24 and 4 <= len(b) <= 24):
        return False
    joined = f"{a}，{b}"
    if not (12 <= len(joined) <= 44):
        return False
    # 「缺少主体与事件」这条规则针对新闻正文，不适用于期标题段一
    # （段一是主线判断，天然没有主体；主体由段二的事实承担）
    bad, reason = is_low_quality_title(joined)
    if bad and reason != "缺少主体与事件":
        return False
    # 言之有物：整条标题合计至少要有 2 类具体锚点（数字/专名/动作/时间）
    # 段一是「主线判断」，可不含锚点；锚点由段二的事实提供
    if anchor_count(joined) < 2:
        return False
    # 大历史观：不得是脱离事实的空泛历史抒发
    # 判断句可以不含锚点，但不能命中空泛词表
    if is_vague(a, require_anchor=False) or is_vague(b, require_anchor=False):
        return False
    return True


# 具体信号：数字 / 英文实体 / 品牌专名
_CONCRETE_NUM = re.compile(r"\d")
_CONCRETE_EN = re.compile(r"[A-Za-z]{2,}")
_CONCRETE_BRAND = re.compile(
    r"(OpenAI|ChatGPT|苹果|谷歌|微软|华为|小米|英伟达|特斯拉|亚马逊|字节|腾讯|"
    r"阿里|百度|DeepSeek|宇树|寒武纪|甲骨文|红帽|联想|Solidot|雷峰网)"
)


def _has_concrete(segment):
    """片段是否含具体信息（数字、英文实体或品牌专名）。"""
    if not segment:
        return False
    return bool(
        _CONCRETE_NUM.search(segment)
        or _CONCRETE_EN.search(segment)
        or _CONCRETE_BRAND.search(segment)
    )


# ============================================================
# 期标题字符回溯校验
# ============================================================

# 粘连错词：AI 常把两个实体粘在一起（AIToken / SpaceXAI / 5G手机）
_GLUE_WORD = re.compile(
    r"(AI[A-Z][a-z]|[a-z][A-Z][a-z]|"
    r"(?<=[a-z])(?=[A-Z])|"
    r"(?<=[一-鿿])(?=[A-Za-z][a-z]))"
)


def headline_traceable(headline, items):
    """期标题中的实体必须能在原标题中找到出处。

    防止 AI 拼出不存在的词（如「SpaceXAI」「AIToken」）。
    做法：抽出标题中的字母/数字片段，逐个回查原始标题集合。
    """
    text = (headline or "").strip()
    if not text:
        return False

    corpus = " ".join(
        (it.get("title") or "") + " " + (it.get("summary") or "")
        for it in (items or [])
    )
    if not corpus.strip():
        return True

    # 抽取英文/数字片段
    frags = re.findall(r"[A-Za-z][A-Za-z0-9.\-]*|\d+(?:\.\d+)?", text)
    if not frags:
        return True

    corpus_norm = re.sub(r"\s+", "", corpus).lower()
    for frag in frags:
        f = frag.lower()
        if len(f) < 2:
            continue
        # 片段必须原样出现，或其两段拼接形式出现在原文
        if f in corpus_norm:
            continue
        if len(f) >= 4:
            # 尝试拆分：AI Token -> ai / token
            parts = re.findall(r"[A-Za-z0-9.]+", frag)
            if len(parts) >= 2:
                if all(p.lower() in corpus_norm for p in parts):
                    continue
            # 尝试在片段内部插入空格（AIToken -> AI Token）
            spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", frag).replace(" ", "").lower()
            if spaced in corpus_norm:
                continue
        return False
    return True


# 期标题中常见的「生硬拼接」形态：实体被压缩成怪词
_BAD_HEADLINE_SHAPE = re.compile(
    r"(SpaceXAI|AIToken|GPUAI|AIkit|AIOS|AIops|"
    r"ChatGPT4|GPT4o|GPT5|GPT6|"
    r"model\d|API接口|SDK工具|"
    r"[A-Za-z0-9]\d[A-Z]$)"
)

# 常见错字/漏字（AI 改写期标题时高频出错）
_TYPO_FIX = {
    "被曝漏": "被曝出漏洞",
    "曝漏": "曝出漏洞",
    "被发现漏洞": "被发现存在漏洞",
    "被曝有漏洞": "被曝存在漏洞",
}


def headline_readable(headline):
    """期标题是否可读 —— 不含生硬拼接的怪词、无截断痕迹。"""
    text = (headline or "")
    if not text:
        return False
    if _BAD_HEADLINE_SHAPE.search(text):
        return False
    # 段落不得以「数字+大写字母」结尾（截断痕迹，如 macOS26.6.1T）
    for part in re.split(r"[，,]", text):
        part = part.strip()
        if re.search(r"[A-Za-z0-9]\d[A-Z]$", part):
            return False
    return True


def normalize_headline(headline, items=None):
    """清洗期标题；不合格则用前两条科技看点拼两段式兜底。"""
    text = (headline or "").strip()
    text = text.strip("「」『』“”\"'")
    text = re.sub(r"^[【\[]|[】\]]$", "", text).strip()
    text = re.sub(r"^(科技资讯|每日科技资讯)[：:\s|｜·\-—]*", "", text).strip()
    text = _fix_glue(text)

    # 常见错字修正
    for wrong, right in _TYPO_FIX.items():
        if wrong in text:
            text = text.replace(wrong, right)

    parts = _split_two_parts(text)
    if parts:
        candidate = f"{parts[0]}，{parts[1]}"
        if (
            is_valid_headline(candidate)
            and headline_readable(candidate)
            and headline_traceable(candidate, items)
        ):
            return candidate

    return build_fallback_headline(items or [])


def build_fallback_headline(items, tech_count=TECH_QUOTA):
    """从精选条目拼两段式期标题（绝不回落到空话）。"""
    pool = list(items or [])[: max(tech_count, 2)]
    clauses = []
    seen = set()
    for item in pool:
        raw = (item.get("summary") or item.get("title") or "").strip()
        clause = _compress_clause(raw)
        if not clause or len(clause) < 4:
            continue
        key = clause.lower()
        if key in seen:
            continue
        seen.add(key)
        clauses.append(clause)
        if len(clauses) >= 2:
            break

    if len(clauses) >= 2:
        return f"{clauses[0]}，{clauses[1]}"
    if len(clauses) == 1 and len(pool) >= 2:
        second = _compress_clause(
            pool[1].get("summary") or pool[1].get("title") or ""
        )
        if second and second != clauses[0]:
            return f"{clauses[0]}，{second}"
    if len(clauses) == 1:
        # 仍只有一段时，用第二条原标题硬拆一点信息，避免单句/空话
        extra = _compress_clause((pool[1].get("title") if len(pool) > 1 else "") or "行业动态更新")
        if extra == clauses[0]:
            extra = "科技圈新进展"
        return f"{clauses[0]}，{extra}"
    return "科技要闻速递，行业动态更新"
