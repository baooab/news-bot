"""标题质量过滤 —— 剔除无效/低信息量新闻。

无效标题特征：
  - 无明确主体、事件或具体数据
  - 引号「猜谜」式表述，读者看不懂在说什么
  - 冒号后仅有评论/隐喻，无事实信息
  - 纯比喻（拦路虎、闹剧等）而无实质内容
  - 空洞通告（告市民书等）无具体措施
"""

import re

from config import TARGET_COUNT

# 有实质信息的新闻常见动作词
_ACTION_VERBS = (
    "发布", "宣布", "通报", "回应", "辟谣", "确认", "否认", "表态", "敦促", "警告",
    "查获", "抓获", "逮捕", "拘留", "判刑", "开庭", "宣判", "立案", "调查", "约谈",
    "死亡", "遇难", "受伤", "失踪", "救援", "撤离", "转移", "停课", "复工", "停课",
    "批准", "通过", "否决", "签署", "达成", "取消", "叫停", "撤销", "暂停", "恢复",
    "涨", "跌", "增", "减", "升", "降", "突破", "创", "刷新", "达", "超", "破",
    "融资", "收购", "合并", "拆分", "裁员", "倒闭", "破产", "上市", "退市", "挂牌",
    "爆炸", "坍塌", "起火", "泄漏", "地震", "预警", "逼近", "登陆", "袭击", "发射",
    "坠毁", "相撞", "泄露", "感染", "确诊", "治愈", "接种", "检测",
    "开通", "通车", "投运", "竣工", "开工", "投产", "落地", "实施", "施行", "生效",
    "制裁", "加征", "豁免", "访华", "出访", "会晤", "谈判", "停火", "撤军",
    "判决", "罚款", "处罚", "问责", "督办", "查处", "整治", "整改",
)

# 冒号后纯评论/情绪，无事实
_FLUFF_AFTER_COLON = re.compile(
    r"^[\s\u3000]*("
    r"可笑|可悲|荒诞|离谱|荒谬|讽刺|意味深长|耐人寻味|一言难尽|值得深思|"
    r"引人发笑|滑天下之大稽|不值一评|闹剧|丑剧|笑话|争议|热议|关注|"
    r"怎么看|如何看|怎看|何为|何以|奈何|？|\?"
    r")+[\s\u3000]*$"
)

# 隐喻/空洞收尾，缺少具体事实
_METAPHOR_TAIL = re.compile(
    r"(遭遇|面临|碰上|遇到|迎来|陷入|卷入|笼罩|承压|受阻)"
    r"(了)?(拦路虎|绊脚石|大考|考验|阻力|瓶颈|困境|难题|阴霾|迷雾|"
    r"风暴|震荡|风波|寒潮|寒冬|十字路口|生死劫|滑铁卢|未知数|问号|"
    r"挑战|困难|压力|危机|波折|变数|障碍|阻力|考验)"
    r"[\s\u3000]*$"
)

# 冒号后空洞：有主体但无具体事件/数据
_VAGUE_AFTER_COLON = re.compile(
    r"^[\s\u3000]*("
    r".{0,12}面临(挑战|困难|压力|考验|阻力|瓶颈|困境|危机)|"
    r".{0,8}遭遇(挑战|困难|阻力|考验|瓶颈|波折)|"
    r"可能(加剧|导致|引发|带来|影响|冲击|波及|推升|推高)|"
    r"或将(引发|导致|带来|影响|加剧)|"
    r"或(将|可能)(引发|导致|带来|影响)|"
    r".*(可能|或将|或许).*(波动|影响|冲击|变化|风险|不确定性)|"
    r"引发(关注|热议|讨论|争议|普遍关注)|"
    r"引(起)?(关注|热议|讨论|争议)|"
    r"值得(关注|深思)|"
    r"受(到)?(关注|瞩目)"
    r")[\s\u3000]*$"
)

# 纯观点/预测，非已发生事实
_SPECULATIVE = re.compile(
    r"(认为|表示|指出|称|警告|提醒|预计|预测|分析|观点|看法|担忧|担心)"
    r".{0,20}(可能|或将|或许|也许|料将|有望|或不|是否会)"
)

# 纯辟谣/否定式：只说「某传言不实」，无正面事实或数据
_RUMOR_DEBUNK = re.compile(
    r"系(谣言|不实消息?|不实信息|虚假|伪造|杜撰)$"
    r"|纯属谣言$|网络谣言$|不实传言$"
)

# 公文口号/部署套话：无具体区域、措施、数字
_SLOGAN = re.compile(
    r"(紧盯|确保|全力|切实|扎实|进一步|持续|全面|深入|积极|稳妥)"
    r".{0,16}(落实|部署|推进|做好|抓好|保障|防范|减少|维护|实现|完成|提升|强化)"
    r"|减少(人员)?伤亡"
    r"|确保(生命)?安全"
    r"|守牢.{0,6}底线"
    r"|筑牢.{0,6}防线"
    r"|抓实抓细"
    r"|高标准.{0,8}高质量"
    r"|万无一失"
)

# 空洞通告/倡议，无具体措施或数据
_HOLLOW_NOTICE = re.compile(
    r"(发布|印发|发出|刊播|刊播|刊出)?"
    r"(告市民书|倡议书|公开信|温馨提示|安全提示|防范提示|防御指南|"
    r"告市民|市民书|告知书|健康提示)"
)

# 引号包裹生僻词 + 空洞展望
_QUOTE_RIDDLE = re.compile(
    r'^[「"『\'][^」"』\']{2,14}[」"』\']'
    r".{0,8}(工程|计划|行动|方案|项目|战略)?"
    r"(定义|描绘|书写|谱写|开启|点亮|擘画|勾勒)"
    r".*(未来|新篇章|新征程|新蓝图|新天地)"
)

# 评论稿/猜谜式标题
_OPINION_PREFIX = re.compile(
    r"^(即时评|快评|社评|锐评|夜读|特稿|图集|视频|直播|专题|"
    r"马上评|一周评|记者观察|专家解读|深度|独家|揭秘)"
)

# 主体/机构常见标记
_ENTITY_MARKERS = re.compile(
    r"[\u4e00-\u9fff]{2,}(部|局|院|委|会|省|市|县|区|镇|乡|村|"
    r"集团|公司|银行|大学|学院|医院|法院|检察院|警方|公安|"
    r"政府|国务院|中央|央行|证监会|发改委)"
)

_HAS_DIGIT = re.compile(r"\d|[%％]|亿|万|千|百|元|美元|欧元|人民币|℃|级")


def _has_action(title):
    return any(v in title for v in _ACTION_VERBS)


def _has_entity(title):
    if _ENTITY_MARKERS.search(title):
        return True
    # 中外常见专名：连续 2+ 汉字作为主体，或英文品牌
    if re.search(r"[A-Za-z]{2,}", title):
        return True
    # 台风/地震等自然灾害名
    if re.search(r"(台风|地震|洪涝|暴雨|暴雪|寒潮|高温)", title):
        return True
    return False


def _is_slogan(text):
    """判断是否为无具体信息的公文口号。"""
    text = (text or "").strip()
    if not text or _HAS_DIGIT.search(text):
        return False
    return bool(_SLOGAN.search(text))


def is_low_quality_title(title):
    """判断标题是否低质量。返回 (是否无效, 原因)。"""
    title = (title or "").strip()
    if not title:
        return True, "空标题"

    # 1. 评论/猜谜栏目名开头
    if _OPINION_PREFIX.match(title):
        return True, "评论/栏目体"

    # 2. 引号猜谜 + 空洞展望
    if _QUOTE_RIDDLE.search(title):
        return True, "引号猜谜式"

    # 3. 冒号后无实质信息（优先于动作词检测，避免「上市」等弱动词误放行）
    for sep in ("：", ":"):
        if sep in title:
            before, after = title.split(sep, 1)
            after = after.strip()
            if not after:
                continue
            if not _HAS_DIGIT.search(after):
                if _RUMOR_DEBUNK.search(after) or _RUMOR_DEBUNK.search(title):
                    return True, "纯辟谣无事实"
                if _is_slogan(after):
                    return True, "口号式表述"
                if _VAGUE_AFTER_COLON.match(after) or _METAPHOR_TAIL.search(after):
                    return True, "冒号后空洞"
                if _SPECULATIVE.search(after):
                    return True, "观点预测式"
            if len(after) <= 20 and _FLUFF_AFTER_COLON.match(after):
                return True, "冒号后无事实"
            if not _HAS_DIGIT.search(after) and not _has_action(after):
                if re.search(r"(闹剧|笑话|可悲|可笑|引热议|引关注|引争议|值得关注)$", after):
                    return True, "冒号后无事实"

    # 3b. 整句观点预测（如「某某认为…可能…」）
    if not _HAS_DIGIT.search(title) and _SPECULATIVE.search(title):
        return True, "观点预测式"

    # 3c. 整句纯辟谣（如 教育部："xxx"系谣言）
    if not _HAS_DIGIT.search(title) and _RUMOR_DEBUNK.search(title):
        return True, "纯辟谣无事实"

    # 3d. 整句或后半段口号套话
    if not _HAS_DIGIT.search(title) and _is_slogan(title):
        return True, "口号式表述"

    # 4. 隐喻式收尾
    if _METAPHOR_TAIL.search(title) and not _HAS_DIGIT.search(title):
        return True, "隐喻无实质"

    # 5. 空洞通告
    if _HOLLOW_NOTICE.search(title) and not _HAS_DIGIT.search(title):
        return True, "空洞通告"

    # 6. 综合低信息量：无主体 + 无动作 + 无数据
    if not _has_entity(title) and not _has_action(title) and not _HAS_DIGIT.search(title):
        return True, "缺少主体与事件"

    # 7. 有主体但几乎无事件：短标题 + 无动作 + 无数据 + 抽象收尾
    abstract_tail = re.search(
        r"(未来|新篇章|新征程|新蓝图|意义重大|影响深远|值得关注|引热议|引关注)$",
        title,
    )
    if abstract_tail and not _has_action(title) and not _HAS_DIGIT.search(title):
        return True, "空洞展望"

    return False, ""


def filter_low_quality(items, verbose=True):
    """过滤低质量标题，返回保留列表。"""
    kept = []
    dropped = []
    for item in items:
        bad, reason = is_low_quality_title(item.get("title", ""))
        if bad:
            dropped.append((item, reason))
        else:
            kept.append(item)

    if verbose and dropped:
        print(f"  质量过滤：丢弃 {len(dropped)} 条低信息量标题")
        for item, reason in dropped[:8]:
            t = item.get("title", "")[:42]
            print(f"    - [{reason}] {t}")
        if len(dropped) > 8:
            print(f"    ... 另有 {len(dropped) - 8} 条")

    return kept


def _item_text_for_filter(item):
    """取用于质量判断的展示文本（摘要优先）。"""
    return (item.get("summary") or item.get("title") or "").strip()


def _item_dedupe_key(item):
    return item.get("link") or item.get("title", "")


def filter_selected_items(selected, pool, count=TARGET_COUNT, verbose=True):
    """过滤精选条目中低质量项（含 AI 摘要），从 pool 递补至 count 条。"""
    kept = []
    seen = set()

    def try_add(item):
        key = _item_dedupe_key(item)
        if key in seen:
            return False, "重复"
        text = _item_text_for_filter(item)
        bad, reason = is_low_quality_title(text)
        if bad:
            return False, reason
        seen.add(key)
        kept.append(item)
        return True, ""

    dropped = []
    for item in selected:
        ok, reason = try_add(item)
        if not ok:
            dropped.append((item, reason))

    for item in pool:
        if len(kept) >= count:
            break
        key = _item_dedupe_key(item)
        if key in seen:
            continue
        text = item.get("title", "")
        bad, reason = is_low_quality_title(text)
        if bad:
            continue
        seen.add(key)
        kept.append(dict(item))

    if verbose and dropped:
        print(f"  精选过滤：移除 {len(dropped)} 条无效/低质量条目")
        for item, reason in dropped[:6]:
            t = _item_text_for_filter(item)[:42]
            print(f"    - [{reason}] {t}")
        if len(dropped) > 6:
            print(f"    ... 另有 {len(dropped) - 6} 条")
    if verbose and len(kept) < count:
        print(f"  [WARN] 过滤后仅 {len(kept)} 条（目标 {count}）")

    return kept[:count]
