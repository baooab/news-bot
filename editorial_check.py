"""主编视角校验层 —— 「大历史观」与「言之有物」的程序化闸门。

提示词约束模型行为，但模型仍会偶发越界。本模块把编辑纪律翻译成可执行判定：

1. 大历史观 —— 拒绝「科技浪潮」「改变世界」这类脱离事实的抒情
2. 言之有物 —— 每个判断必须挂在具体锚点上（数字/专名/动作）
3. 编排秩序 —— AI 重排后仍须保持科技在前、民生垫底的结构约束

所有校验都是"降级"而非"报错"：不合格时回退到安全版本，绝不让坏内容进成品。
"""

import re

from config import TECH_QUOTA

# ---------------------------------------------------------------------------
# 一、空泛历史词汇（大而无当的历史抒发）
# ---------------------------------------------------------------------------

# 这些词单独出现时不含信息量；出现即判定为空泛

_HISTORY_VAGUE = re.compile(
    r"(科技浪潮|技术浪潮|浪潮席卷|席卷全球|改变世界|改变未来|"
    r"新时代|新时代已经|历史性|划时代|里程碑式|具有里程碑|"
    r"深刻变革|伟大变革|时代洪流|历史潮流|大势所趋|"
    r"日新月异|突飞猛进|蓬勃发展|欣欣向荣|蒸蒸日上|"
    r"令人振奋|振奋人心|拭目以待|未来可期|值得期待|"
    r"开启了?新篇章|新纪元|新征程|新起点|"
    r"一场变革|一场革命|质的飞跃|全面爆发|"
    r"彻底改变.{0,6}(格局|行业|世界|生态)|"
    r"将彻底(改变|颠覆|重塑)|"
    r"重塑.{0,4}(格局|行业|生态|未来)|"
    r"颠覆性(突破|进展|变革)|"
    r"划时代|革命性(突破|进展)|"
    r"万亿级市场|千亿级赛道|风口上的|"
    r"白热化|风生水起|群雄逐鹿|逐鹿中原|"
    r"各路资本|资本狂欢|风口|浪潮|巨头纷纷|纷纷加码|争相布局|"
    r"大举|竞相|纷纷(加码|入场|布局|涌入))"
)

# 抒情但无锚点的常见句式
_VAGUE_PATTERN = re.compile(
    r"(在.{0,12}的时代|随着.{0,12}的(发展|进步|到来)|"
    r"正以.{0,12}(的速度|的姿态)|无疑(是|将)|"
    r"我们(正|将)?迎来|标志着.{0,10}的(到来|开启))"
)

# ---------------------------------------------------------------------------
# 二、言之有物：具体锚点
# ---------------------------------------------------------------------------

# 数字类锚点：金额、比例、数量、版本号
_ANCHOR_NUM = re.compile(
    r"\d"
)

# 英文专名 / 产品名 / 模型名
_ANCHOR_EN = re.compile(r"[A-Za-z][A-Za-z0-9.\-]{1,}")

# 中文品牌与机构（可扩展）
_ANCHOR_BRAND = re.compile(
    r"(OpenAI|ChatGPT|Claude|Gemini|Llama|DeepSeek|MiniMax|谷歌|Google|苹果|Apple|"
    r"微软|Microsoft|亚马逊|Amazon|特斯拉|Tesla|英伟达|NVIDIA|AMD|Intel|"
    r"华为|小米|字节|腾讯|阿里|百度|美团|京东|蚂蚁|阿里云|"
    r"字节跳动|抖音|飞书|钉钉|智谱|月之暗面|零一万物|商汤|寒武纪|"
    r"海康|大疆|中兴|联想|甲骨文|红帽|宇树|小米汽车|比亚迪|蔚来|理想|"
    r"OpenRouter|Anthropic|Mistral|Hugging|GitHub|GitLab|Linux|Android|iOS|"
    r"雷峰网|固态|新华社|央视|国务院|央行|工信部|发改委|教育部|统计局|"
    r"网信办|市场监管|人社部|卫健委|应急管理)"
)

# 明确的动作动词 —— 「做了什么」
_ANCHOR_VERB = re.compile(
    r"(发布|开源|上线|下架|降价|涨价|收购|并购|融资|裁员|招人|扩产|量产|"
    r"交付|落地|部署|关停|停售|召回|处罚|罚款|立案|通报|"
    r"推出|首发|亮相|进军|入局|加码|收缩|转型|"
    r"批准|通过|签署|启动|竣工|通车|投用|启用|通报|遇难|受伤|失踪|"
    r"上升|下降|增长|下滑|突破|刷新|创.{0,4}新高|首超|超.{0,4}|"
    r"起诉|指控|窃取|告|禁|封|查|抓|曝光|被曝|曝出|披露|回应|"
    r"开打|打响|提速|升级|降速|砍单|砍掉|合并|拆分|关停|缩减|扩张|"
    r"清场|搬迁|裁员|挖角|挖人|加盟|离职|辞职|接任|卸任)"
)

# 时间跨度锚点
_ANCHOR_TIME = re.compile(
    r"(今年|去年|明年|本月|上月|本周|上季度|今年来|近\d+年|"
    r"\d+年\d*月|\d+月\d+日|年底前|年初|上半年|下半年|Q[1-4]|"
    r"过去\d+年|未来\d+年|数年来|多年来)"
)

# 产业判断词 —— 有信息量的结构性表述（区别于纯抒情）
_ANCHOR_STRUCTURE = re.compile(
    r"(成本战|价格战|算力|推理|训练|开源|闭源|商业化|产业化|量产|落地|"
    r"军备竞赛|格局|洗牌|清场|转型|迁移|拐点|卡位|入场|退出|退坡|"
    r"补贴|反垄断|监管|合规|出海|国产替代|供应链|产能|基建|"
    r"参数|性价比|生态|标准|专利|人才|投融资|并购)"
)


def has_anchor(text):
    """文本是否含具体锚点（数字 / 专名 / 动作 / 时间跨度 / 产业结构词）。"""
    if not text:
        return False
    return bool(
        _ANCHOR_NUM.search(text)
        or _ANCHOR_EN.search(text)
        or _ANCHOR_BRAND.search(text)
        or _ANCHOR_VERB.search(text)
        or _ANCHOR_TIME.search(text)
        or _ANCHOR_STRUCTURE.search(text)
    )


def anchor_count(text):
    """锚点数量（用于衡量信息密度）。"""
    if not text:
        return 0
    n = 0
    if _ANCHOR_NUM.search(text):
        n += 1
    if _ANCHOR_EN.search(text):
        n += 1
    if _ANCHOR_BRAND.search(text):
        n += 1
    if _ANCHOR_VERB.search(text):
        n += 1
    if _ANCHOR_TIME.search(text):
        n += 1
    if _ANCHOR_STRUCTURE.search(text):
        n += 1
    return n


def is_vague(text, require_anchor=True):
    """是否为空泛的历史抒发 / 脱离事实的感叹。

    require_anchor=True 时，除命中空泛词表外，还要求文本自带锚点。
    用于「单独成句」的场景（如导语）。
    用于「段一判断 + 段二事实」的场景时，应传 require_anchor=False，
    因为判断句可以不含锚点，锚点由另一段提供。
    """
    if not text:
        return True
    text = text.strip()
    if not text:
        return True
    if _HISTORY_VAGUE.search(text):
        return True
    if _VAGUE_PATTERN.search(text):
        return True
    # 整句只有抒情、没有任何锚点
    if require_anchor and len(text) >= 8 and not has_anchor(text):
        return True
    return False


# ---------------------------------------------------------------------------
# 三、导语（overview）校验
# ---------------------------------------------------------------------------

# 导语长度区间（超出即为不合格）
OVERVIEW_MIN = 30
OVERVIEW_MAX = 160

# 导语禁止的开场套话（"今天我们来聊聊…" / "本期带大家看看…"）
# 注意：尾部动词是必需的，否则「本期主线是…」这类正常表述会被误杀
_OVERVIEW_BOILERPLATE = re.compile(
    r"^(今天|今日|本期|这一期)[，,]?\s*"
    r"(我们|大家|你)?\s*"
    r"(来|一起|一起)?\s*"
    r"(看看|瞧瞧|看下|看一下|聊|聊一聊|聊聊|盘点|回顾|了解|分享|梳理|盘点一下)"
)


def validate_overview(overview, items=None):
    """校验导语是否言之有物。

    判定标准（全部满足才算合格）：
    1. 长度在 30~160 字之间
    2. 不含空泛历史词汇
    3. 不以套话开场（"今天我们来…"）
    4. 至少含 2 个锚点 —— 一个判断句至少要有两个具体支撑
    5. 若给出 items，导语中的专名/数字应能在原标题中找到出处（防止编造）
    """
    text = (overview or "").strip()
    if not text:
        return False, "空导语"

    length = len(text)
    if length < OVERVIEW_MIN:
        return False, f"导语过短({length}字)"
    if length > OVERVIEW_MAX:
        return False, f"导语过长({length}字)"

    if is_vague(text):
        return False, "含空泛历史词汇"

    if _OVERVIEW_BOILERPLATE.match(text):
        return False, "套话开场"

    ac = anchor_count(text)
    if ac < 2:
        return False, f"锚点不足({ac}个)"

    # 防编造：导语里的数字应在原标题中出现过
    if items:
        corpus = " ".join(
            (it.get("title") or "") + " " + (it.get("summary") or "")
            for it in items
        )
        nums = set(re.findall(r"\d+(?:\.\d+)?", text))
        if nums:
            corpus_nums = set(re.findall(r"\d+(?:\.\d+)?", corpus))
            unknown = {n for n in nums if n not in corpus_nums}
            # 允许少量数字是 AI 的合理归纳（如"3家"），但不能全是编的
            if len(unknown) > max(1, len(nums) // 2):
                return False, f"数字无出处({sorted(unknown)[:3]})"

    return True, ""


def normalize_overview(overview, items=None):
    """校验通过返回清洗后的导语，否则返回空字符串（由上层决定是否生成兜底）。"""
    text = (overview or "").strip()
    text = re.sub(r"^[\"'「『【\[]|[\"'」』】\]]$", "", text).strip()
    text = re.sub(r"\s+", " ", text)
    ok, _ = validate_overview(text, items)
    return text if ok else ""


def build_fallback_overview(items, tech_count=TECH_QUOTA):
    """兜底导语：从本期事实里直接拼一条"有锚点"的综述。

    不做任何主观判断，只陈述本期事实里可核对的内容 —— 保证言之有物。
    """
    pool = list(items or [])[:tech_count]
    if not pool:
        return ""

    facts = []
    for item in pool[:3]:
        raw = (item.get("summary") or item.get("title") or "").strip()
        if not raw:
            continue
        clause = re.split(r"[，,。；;：:]", raw, maxsplit=1)[0].strip()
        if len(clause) >= 6:
            facts.append(clause)
        if len(facts) >= 3:
            break

    if len(facts) < 2:
        return ""

    return "本期要闻：" + "；".join(facts) + "。"


# ---------------------------------------------------------------------------
# 四、编排（order）校验
# ---------------------------------------------------------------------------

def validate_order(order, n, tech_count=TECH_QUOTA):
    """校验 AI 返回的重排顺序。

    约束：
    1. 必须是 1..n 的完整排列（不能漏、不能重）
    2. 科技条（1..tech_count）必须仍排在民生条（tech_count+1..n）之前
       —— 否则简报结构被破坏
    """
    if not order:
        return False, "无order"

    try:
        seq = [int(x) for x in order]
    except (TypeError, ValueError):
        return False, "order非整数"

    if len(seq) != n:
        return False, f"order长度{len(seq)}≠{n}"

    if sorted(seq) != list(range(1, n + 1)):
        return False, "order非完整排列"

    # 分区约束：科技条目必须全在前
    tech_positions = [i for i, v in enumerate(seq) if v <= tech_count]
    gen_positions = [i for i, v in enumerate(seq) if v > tech_count]
    if tech_positions and gen_positions:
        if max(tech_positions) > min(gen_positions):
            return False, "科技/民生分区被打乱"

    return True, ""


def repair_order(order, n, tech_count=TECH_QUOTA):
    """修复 AI 返回的不完整 order。

    条数变多后，AI 更容易漏写或重复某个序号。此时与其整份丢弃主编判断，
    不如做「最小修复」：
    1. 去掉重复出现的序号（保留首次）
    2. 按缺失的序号补齐（缺失项追加到末尾）
    3. 若科技/民生分区被打乱，则强制把科技条提到前面、民生条压后

    返回 (修复后的 order, 说明) ；无法修复时返回 (None, 原因)。
    """
    if not order:
        return None, "无order"

    try:
        seq = [int(x) for x in order]
    except (TypeError, ValueError):
        return None, "order非整数"

    valid = [v for v in seq if 1 <= v <= n]
    seen = set()
    deduped = []
    for v in valid:
        if v not in seen:
            seen.add(v)
            deduped.append(v)

    missing = [v for v in range(1, n + 1) if v not in seen]
    repaired = deduped + missing

    # 分区约束：科技条全在前，民生条全在后
    # 注意比较的是「位置」而非「序号值」—— 序号小不等于位置靠前
    tech_positions = [i for i, v in enumerate(repaired) if v <= tech_count]
    gen_positions = [i for i, v in enumerate(repaired) if v > tech_count]
    if tech_positions and gen_positions and max(tech_positions) > min(gen_positions):
        # 分区被打乱：强制分区（保持各自内部相对顺序）
        tech_part = [v for v in repaired if v <= tech_count]
        gen_part = [v for v in repaired if v > tech_count]
        repaired = tech_part + gen_part
        note = "分区已强制修正"
    else:
        note = ""

    if len(deduped) != len(valid):
        note = (note + "；" if note else "") + f"去除重复 {len(valid) - len(deduped)} 项"
    if missing:
        note = (note + "；" if note else "") + f"补齐缺失 {len(missing)} 项"

    return repaired, note or "无需修复"


def apply_order(items, order):
    """按 order 重排条目；order 非法时保持原序。"""
    if not order:
        return list(items)
    try:
        seq = [int(x) for x in order]
    except (TypeError, ValueError):
        return list(items)
    if sorted(seq) != list(range(1, len(items) + 1)):
        return list(items)
    return [items[i - 1] for i in seq]


# ---------------------------------------------------------------------------
# 五、摘要与标题的语义一致性
# ---------------------------------------------------------------------------

def summary_matches_title(title, summary, threshold=0.34):
    """摘要是否确实在讲这条标题的事。

    AI 偶尔会「串台」——把 A 条的摘要写成 B 条的内容，
    表现为成品里出现两条一模一样的文案。
    做法：抽取标题与摘要各自的实体/关键词，���求重合度。
    """
    title = (title or "").strip()
    summary = (summary or "").strip()
    if not title or not summary:
        return True

    if summary == title:
        return True

    def _tokens(text):
        # 英文/数字词 + 中文 2-4 字词块
        latin = set(w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9.\-]{1,}", text))
        digits = set(re.findall(r"\d+(?:\.\d+)?", text))
        cjk = set()
        for run in re.findall(r"[一-鿿]+", text):
            for i in range(len(run)):
                for size in (2, 3, 4):
                    if i + size <= len(run):
                        cjk.add(run[i:i + size])
        return latin | digits, cjk

    t_latin, t_cjk = _tokens(title)
    s_latin, s_cjk = _tokens(summary)

    # 数字必须能对上（强信号）
    t_num = set(re.findall(r"\d+(?:\.\d+)?", title))
    s_num = set(re.findall(r"\d+(?:\.\d+)?", summary))
    if t_num and not (s_num & t_num):
        return False

    # 英文专名重合
    if t_latin & s_latin:
        return True

    # 中文词块重合
    shared_cjk = t_cjk & s_cjk
    if not shared_cjk:
        # 标题里的实词在摘要中一个都没出现 —— 强烈怀疑串台
        return False

    # 重合比例
    ratio = len(shared_cjk) / max(len(t_cjk), 1)
    return ratio >= threshold or len(shared_cjk) >= 2

