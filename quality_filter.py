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
    "下调", "上调", "调整", "放宽", "缩短", "延长", "降低", "提高",
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

# 辟谣提醒稿 —— 通知读者「别信」，本身不是有信息量的新闻条目。
# 单独成规则，因为它常带日期编号与震级，不能走「有数字即豁免」的逻辑。
_RUMOR_ALERT = re.compile(
    r"(警惕|注意防范|勿信勿传|请勿传播).{0,20}(不实信息|不实消息|谣言|虚假信息)"
    r"|^警惕涉.{0,24}(不实信息|不实消息|谣言|虚假信息)"
    r"|涉.{0,16}(不实信息|不实消息|谣言)(信息|通报|公告)?$"
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

# 体验/探访类软文特稿：无政策、数据或事件结果
_SOFT_FEATURE = re.compile(
    r"(赴|走进|探访|参观|打卡|游历|来到|逐浪).{0,36}"
    r"(体验|感受|感悟|领略|沉浸|读懂).{0,16}"
    r"(文化|风情|魅力|之美|韵味|传统|东坡)|"
    r"(体验|感受|感悟|领略|读懂).{0,10}(文化|风情|魅力|之美|东坡)|"
    r"跨越千年.{0,16}(读懂|体验|感悟)"
)

# 引号包裹生僻词 + 空洞展望
_QUOTE_RIDDLE = re.compile(
    r'^[「"『\'][^」"』\']{2,14}[」"』\']'
    r".{0,8}(工程|计划|行动|方案|项目|战略)?"
    r"(定义|描绘|书写|谱写|开启|点亮|擘画|勾勒)"
    r".*(未来|新篇章|新征程|新蓝图|新天地)"
)

# 标题党 / 情绪煽动式
_CLICKBAIT = re.compile(
    r"(捅了马蜂窝|"
    r"彻底凉了|凉透了|这下.{0,8}凉了|"
    r"翻车了|炸锅了|破防了|搞事情|"
    r"育儿大法|赚钱大法|搞钱大法|"
    r"终于出手了|最适合做.{0,16}的(厂商|品牌|公司)|"
    r"曾经.{0,16}第一.{0,20}(凉了|没落|衰落|不行))"
    r"[？?！!…]*"
)

# 暖心/励志特稿（即便含「N年」也无硬新闻事实）
_HUMAN_INTEREST = re.compile(
    r"(续写大爱|大爱无疆|温暖人间|爱心接力|感人泪目|催人泪下|"
    r"圆梦师范|圆梦大学|圆梦校园|失亲.{0,12}抚养|被老师抚养|"
    r"暖心故事|温情时刻)"
)

# 动物/萌宠软文
_ANIMAL_SOFT = re.compile(
    r"^当.{0,24}(宝宝|小猫|小狗|松鼠|流浪猫|流浪狗|小动物).{0,30}"
    r"(坠落|街头|走失|获救|被困|意外)|"
    r"(松鼠宝宝|猫咪宝宝|狗狗).{0,20}(坠落|街头|走失)"
)

# 空洞政策表述：进一步优化/调整…但无具体数据或措施
_VAGUE_POLICY = re.compile(
    r"(进一步|持续|全面|深入|积极|稳妥).{0,10}"
    r"(优化|调整|完善|加强|推进|做好).{0,20}"
    r"(政策|措施|工作|力度|环境|机制)|"
    r"优化调整.{0,16}(政策|措施|工作)"
)

# 评论稿/猜谜式标题（开头栏目名；兼容｜/|分隔）
_OPINION_PREFIX = re.compile(
    r"^(即时评|快评|社评|锐评|时评|夜读|特稿|图集|视频|直播|专题|"
    r"马上评|一周评|记者观察|专家解读|深度|独家|揭秘)"
    r"(?:\s*[｜|：:])?"
)

# 媒体时评/评论员文章（含「新华时评：」）
_COMMENTARY = re.compile(
    r"(新华时评|人民时评|光明时评|经济日报|评论员文章|本报评论员|"
    r"[\u4e00-\u9fff]{0,6}时评)[：:]|"
    r"^(时评|评论)[：:]"
)

# 娱乐软广 / 情怀致敬
_ENTERTAINMENT_SOFT = re.compile(
    r"从[《「\"].{1,24}[》」\"]到[《「\"].{1,24}[》」\"]|"
    r"致敬.{0,16}(初心|情怀|经典|梦想)|"
    r"(电影|影视).{0,8}初心"
)

# 主体/机构常见标记（「大学生」不算「大学」）
_ENTITY_MARKERS = re.compile(
    r"[\u4e00-\u9fff]{2,}(部|局|院|委|会|省|市|县|区|镇|乡|村|"
    r"集团|公司|银行|大学(?!生)|学院|医院|法院|检察院|警方|公安|"
    r"政府|国务院|中央|央行|证监会|发改委)"
)

# 真实数据信号；避免「千年/百姓」等文学用词误触
_HAS_DIGIT = re.compile(
    r"\d|[%％]|亿|万|千万|百万|千亿|百亿|"
    r"元|美元|欧元|人民币|℃|级|"
    r"[一二三四五六七八九十两]+[年月日天成倍]"
)

# 末尾无单位的 1～2 位尾巴数字（如「广阔天地0」），不算有效数据
_TRAILING_JUNK_DIGIT = re.compile(r"[\u4e00-\u9fff]\d{1,2}$")



# 疑问句标题：以问号结尾 —— 多为科普/评论，非事实陈述
_QUESTION_TITLE = re.compile(
    r"[？?]\s*$"
    r"|(如何|怎么|怎样|为什么|为何|多少|哪些|是不是|能否|该不该|该不该)$"
)

# 纯科普/常识解读：不是新闻事件
_SCIENCE_EXPLAIN = re.compile(
    r"^(为什么|你知道|你知道吗|涨知识|冷知识|科普|解读一下|一图|图解|"
    r"原来|其实|真相是|揭秘.{0,6}背后)"
)

# 栏目化前缀（追加到标题开头的栏目名）
_COLUMN_PREFIX = re.compile(
    r"^(马上评|快评|社评|锐评|时评|夜读|特稿|图集|视频|直播|专题|"
    r"马上评|一周评|记者观察|专家解读|深度|独家|揭秘|记者手记|蹲点|"
    r"现场|直击|回访|对话|专访|口述|讲述|记录|纪实|侧记|观察|思考|"
    r"微观察|瞭望|扫描|透视|聚焦|关注|追踪|连载|系列|"
    r"走进中国|走进|蹲点|探访|上看下看|图说|现场直击|"
    r"共话|共谱|同绘|绘出|新观察|一线见闻|蹲点调查|"
    r"深度观察|独家探访|对话实录|旧闻新知)"
    r"(?:\s*[｜|：:（(])"
)

# 媒体自营栏目前缀：「36氪首发丨」「独家丨」等 —— 是分发标记，不是新闻内容
_SELF_BRAND_PREFIX = re.compile(
    r"^[0-9一-鿿A-Za-z]{2,8}(首发|独家|专稿|原创|快讯|聚焦|报道)丨"
)

# 活动 / 展览启动类通稿：无实质事实，仅告知活动开始
_ACTIVITY_LAUNCH = re.compile(
    r"(展|活动|演出|赛事|巡展|论坛|仪式|展览|书展|影展|画展|音乐会)"
    r".{0,10}(启动|开幕|开展|举行|拉开帷幕|启幕)"
)

# 活动报道 / 会议综述：不是硬新闻
_EVENT_REPORT = re.compile(
    r"(齐聚|相聚|汇聚|共话|共谱|共谋|共绘|同绘|共庆|共襄|联袂|同台|登台|亮相活动)"
    r"|(举行|举办|召开|开幕|闭幕|收官|落幕|启幕|开展|隆重|热烈|圆满|成功举办|隆重举办|系列活动)"
    r".{0,20}(大会|论坛|峰会|展会|节|活动|研讨会|交流会|座谈会|博览会|嘉年华|年会|开幕式|闭幕式)"
    r"|(共话|共谱|共谋|共绘|同绘|探讨|商议).{0,10}(发展|高质量|产业|未来|愿景|新篇章)"
    r"|(产业发展|高质量发展|新篇章|新征程).{0,6}(大会|论坛|峰会|研讨会|交流会)"
    # 「XX年会在XX举行」这类纯会议通知 —— 只有时间地点主办方，没有实质事件
    r"|\d{4}年.{0,12}(年会|大会|论坛|峰会|展会|研讨会)"
    r".{0,14}(在|于)[^，。]{2,12}(举行|举办|召开|开幕|启幕)"
    # 「XX活动圆满结束」这类活动综述
    r"|.{0,12}(活动|赛事|比赛|大会|论坛|年会|培训|演练)"
    r".{0,6}(圆满|顺利|成功)(举行|举办|结束|落幕|收官)"
)

# 纯会议通知 / 年会通稿：只有时间地点主办方，没有实质事件
_MEETING_NOTICE = re.compile(
    r"\d{4}年.{0,26}(年会|大会|论坛|峰会|展会|研讨会|博览会)"
    r".{0,18}(举行|举办|召开|开幕|启幕)"
    r"|\d{4}年.{0,26}(比武|大赛|竞赛)"
    r".{0,10}(结束|落幕|收官|圆满|顺利|成功)"
    r"|(年会|大会|论坛|峰会|展会|研讨会)"
    r".{0,12}(在|于)[^，。]{2,12}(举行|举办|召开|开幕|启幕)"
    r"|.{0,20}(活动|赛事|比赛|大会|论坛|年会|培训|演练|比武)"
    r".{0,6}(圆满|顺利|成功)(举行|举办|结束|落幕|收官)"
    # 「XX大会今日开幕」——只有开幕动作，无实质发布/签约/数据
    r"|\d{4}年?[^，。]{0,14}(大会|论坛|峰会|展会)"
    r".{0,6}(今日|昨日|日前)?(开幕|启幕)"
)

# 建议 / 指导类：非既成事实
_ADVICE_TYPE = re.compile(
    r"(该如何|应如何|该怎么做|要怎么做|如何自查|怎样自查|请注意|敬请|"
    r"温馨提示|请各位|广大.{0,6}注意|别忘了|收好这份)"
)

# 研究部署型通稿：有会议主体，但动作只是「研究/统筹/部署有关工作」，
# 没有具体措施、数据或结果 —— 例如「国常会：研究统筹人口与经济社会发展有关工作」
_RESEARCH_DEPLOY = re.compile(
    r"(研究|统筹|部署|安排|审议|研究部署).{0,20}"
    r"(有关|相关|下一步|重点)(工作|问题|事项|措施)"
)

# 科普 / 学术趣闻：非科技产业新闻
_SCIENCE_TRIVIA = re.compile(
    r"(科学家.{0,10}(确认|发现|证实).{0,12}(植物|动物|生物|物种|昆虫|鸟类|菌|苔))|"
    r"(食肉植物|食虫植物|新物种|首次发现.{0,8}(植物|动物))"
)

# 硬新闻信号：有具体主体 + 已发生的动作
_HARD_NEWS = re.compile(
    r"(发布|公布|通报|宣布|批准|通过|否决|签署|立案|查处|调查|判刑|宣判|"
    r"抓获|逮捕|拘留|查获|召回|停产|停售|下架|上线|投运|通车|开工|竣工|"
    r"起诉|受理|处罚|罚款|没收|追缴|救援|遇难|死亡|受伤|失踪|确诊|"
    r"出台|印发|实施|施行|生效|落地|上调|下调|调整|取消|关闭|开放)"
)


def _has_action(title):
    return any(v in title for v in _ACTION_VERBS)


def _has_real_digit(title):
    """是否含有效数据信号（忽略末尾无单位垃圾数字）。"""
    text = _TRAILING_JUNK_DIGIT.sub(lambda m: m.group(0)[0], title or "")
    return bool(_HAS_DIGIT.search(text))


# 实质数据：金额、比例、人数、企业数、产品数 —— 年份/届次不算
_SUBSTANTIVE_DATA = re.compile(
    r"\d+(?:\.\d+)?\s*(?:亿|万亿|万|千|百|%|％|元|美元|人|家|款|项|个|款产品)"
    r"|超\d+|\d+\s*(?:余|多)?\s*(?:亿|万|千|百)"
    r"|首次|首发|发布|签约|落地|突破|揭牌|投产"
)


def _has_substantive_data(title):
    """是否含实质数据（而非仅有年份）。"""
    return bool(_SUBSTANTIVE_DATA.search(title or ""))


def _has_entity(title):
    if _ENTITY_MARKERS.search(title):
        return True
    # 直辖市 / 港澳简称
    if re.search(r"(北京|上海|天津|重庆|香港|澳门)", title):
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
    if not text or _has_real_digit(text):
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

    # 1a. 栏目化前缀（马上评｜、直击：、对话 等）
    if _COLUMN_PREFIX.match(title):
        return True, "栏目体"

    # 1a1. 媒体自营栏目前缀（36氪首发丨、独家丨）—— 分发标记，非新闻内容
    if _SELF_BRAND_PREFIX.match(title):
        return True, "自营栏目前缀"

    # 1a1b. 活动 / 展览启动通稿 —— 只有「活动开始」这一事实
    if _ACTIVITY_LAUNCH.search(title) and not _has_substantive_data(title):
        return True, "活动启动通稿"

    # 1a2. 疑问句标题 —— 科普/评论而非事实陈述
    #     问号出现在句中或句尾都算（分析式标题），除非是明确的疑问式事实提问
    if "？" in title or "?" in title:
        if not _has_real_digit(title):
            return True, "疑问句标题"
        # 带数字仍可能是分析稿：问号在句子中部
        q_pos = max(title.find("？"), title.find("?"))
        if q_pos > 0 and q_pos < len(title) - 1:
            return True, "疑问句标题"

    # 1a3. 纯科普/常识解读开头
    if _SCIENCE_EXPLAIN.match(title):
        return True, "科普体"

    # 1a3b. 活动报道 / 会议综述
    if _EVENT_REPORT.search(title) and not _has_real_digit(title):
        return True, "活动综述"

    # 1a3b2. 纯会议通知 / 年会通稿 —— 年份数字不算实质数据，无条件拦截
    # （含企业数、金额、签约等实质内容的会议报道予以豁免）
    if _MEETING_NOTICE.search(title) and not _has_substantive_data(title):
        return True, "会议通知"

    # 1a3b2b. 研究部署型通稿 —— 只有「研究/统筹有关工作」，无具体措施与数据
    if _RESEARCH_DEPLOY.search(title) and not _has_substantive_data(title):
        return True, "研究部署通稿"

    # 1a3c. 学术趣闻（食肉植物、新物种等）
    if _SCIENCE_TRIVIA.search(title):
        return True, "学术趣闻"

    # 1a3d. 栏目名出现在括号内（如「（走进中国乡村）…」）
    if re.match(r"^[（(][^）)]{2,12}[）)]", title):
        return True, "栏目体"

    # 1a3e. 建议 / 指导类内容
    if _ADVICE_TYPE.search(title):
        return True, "建议指导类"

    # 1b. 时评/评论员文章
    if _COMMENTARY.search(title):
        return True, "时评评论"

    # 1c. 标题党 / 情绪煽动
    if _CLICKBAIT.search(title):
        return True, "标题党"

    # 1d. 娱乐情怀软文
    if _ENTERTAINMENT_SOFT.search(title) and not _has_real_digit(title):
        return True, "娱乐软文"

    # 1e. 暖心励志特稿
    if _HUMAN_INTEREST.search(title):
        return True, "暖心特稿"

    # 1f. 萌宠/动物软文
    if _ANIMAL_SOFT.search(title):
        return True, "动物软文"

    # 1g. 空洞政策（无具体数据）
    if _VAGUE_POLICY.search(title) and not _has_real_digit(title):
        return True, "空洞政策"

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
            if not _has_real_digit(after):
                if _RUMOR_DEBUNK.search(after) or _RUMOR_DEBUNK.search(title):
                    return True, "纯辟谣无事实"
                if _is_slogan(after):
                    return True, "口号式表述"
                if _VAGUE_AFTER_COLON.match(after) or _METAPHOR_TAIL.search(after):
                    return True, "冒号后空洞"
                if _SPECULATIVE.search(after):
                    return True, "观点预测式"
                # 时评冒号后纯口号/虚空表述
                if re.search(
                    r"(迎难而上|广阔天地|新篇章|新征程|新蓝图|砥砺前行|"
                    r"再出发|再启航|向未来|谱新篇)",
                    after,
                ) and not _has_action(after):
                    return True, "冒号后空洞"
            if len(after) <= 20 and _FLUFF_AFTER_COLON.match(after):
                return True, "冒号后无事实"
            if not _has_real_digit(after) and not _has_action(after):
                if re.search(r"(闹剧|笑话|可悲|可笑|引热议|引关注|引争议|值得关注)$", after):
                    return True, "冒号后无事实"

    # 3b. 整句观点预测（如「某某认为…可能…」）
    if not _has_real_digit(title) and _SPECULATIVE.search(title):
        return True, "观点预测式"

    # 3c. 整句纯辟谣（如 教育部："xxx"系谣言）
    if not _has_real_digit(title) and _RUMOR_DEBUNK.search(title):
        return True, "纯辟谣无事实"

    # 3c2. 辟谣提醒稿（「警惕涉XX不实信息」）—— 无条件拦截。
    #     这类稿常带日期编号（2026·10·23）与震级，不能走数字豁免。
    if _RUMOR_ALERT.search(title):
        return True, "辟谣提醒稿"

    # 3d. 整句或后半段口号套话
    if not _has_real_digit(title) and _is_slogan(title):
        return True, "口号式表述"

    # 4. 隐喻式收尾
    if _METAPHOR_TAIL.search(title) and not _has_real_digit(title):
        return True, "隐喻无实质"

    # 5. 空洞通告
    if _HOLLOW_NOTICE.search(title) and not _has_real_digit(title):
        return True, "空洞通告"

    # 5b. 体验/探访类软文（无数据则视为无实质）
    if _SOFT_FEATURE.search(title) and not _has_real_digit(title):
        return True, "软文无实质"

    # 6. 综合低信息量：无主体 + 无动作 + 无数据
    if not _has_entity(title) and not _has_action(title) and not _has_real_digit(title):
        return True, "缺少主体与事件"

    # 7. 有主体但几乎无事件：短标题 + 无动作 + 无数据 + 抽象收尾
    abstract_tail = re.search(
        r"(未来|新篇章|新征程|新蓝图|意义重大|影响深远|值得关注|引热议|引关注)$",
        title,
    )
    if abstract_tail and not _has_action(title) and not _has_real_digit(title):
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
