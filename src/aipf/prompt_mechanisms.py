from __future__ import annotations
import re
from collections import Counter

CLAUSE_RULES = [
    ("reference_role", r"\breference\b|identity preservation|identity lock|preserve exact face|uploaded image|uploaded photo"),
    ("identity", r"\b(face|facial|identity|ethnicity|adult woman|adult man|young woman|young man|character)\b|人物|角色|女性|男性|面部|脸部|身份"),
    ("pose", r"\b(pose|standing|stands|sitting|seated|kneeling|reclining|lying|leaning|turning|looking back|over[- ]the[- ]shoulder)\b|动作|姿势|站立|坐姿|跪姿|躺姿|转身|回眸"),
    ("body_mechanics", r"weight on|weight shifted|center of gravity|one leg|supporting leg|pelvis|hip shift|shoulders? (?:counter|turned)|body weight|knees? bent|重心|承重|支撑腿|骨盆|髋部|肩部反向|屈膝"),
    ("hand_logic", r"\b(hand|hands|finger|fingers|grip|holding|touching|resting|supporting|adjusting|lifting)\b|手指|手部|握住|拿着|触碰|托住|扶住"),
    ("wardrobe", r"\b(wear|wearing|outfit|dress|shirt|skirt|coat|jacket|robe|bikini|swimwear|gown|blouse|trousers|stockings|shoes|boots|costume)\b|服装|穿着|裙装|长裙|上衣|外套|汉服|礼服|鞋靴"),
    ("hair", r"\b(hair|hairstyle|ponytail|bun|braid|bangs|bob|updo|pigtail|chignon|pixie|shag)\b|头发|发型|马尾|盘发|编发|刘海|发髻"),
    ("makeup", r"\b(makeup|lipstick|blush|eyeliner|lashes|complexion|lip color|eye makeup)\b"),
    ("material", r"\b(satin|silk|lace|tulle|cotton|wool|linen|bronze|marble|porcelain|ceramic|paper|ink|pigment|glaze|velvet|latex|knit|metal|stone|woodblock)\b|材质|缎|丝绸|蕾丝|薄纱|青铜|大理石|瓷|陶瓷|纸张|水墨|矿物颜料|釉|刺绣"),
    ("fabric_physics", r"fabric (?:fold|drape|tension|movement)|folds|draping|hem (?:moving|flowing)|ribbons? (?:flow|drape|trail)|gauze (?:flow|float)|cloth (?:movement|response)|skirt (?:movement|flow)"),
    ("artifact_form", r"\b(bust|statue|relief|stele|frieze|vase|jar|bowl|plate|tile|figurine|scroll|album leaf|book page|screen|diorama|artifact)\b"),
    ("environment", r"\b(background|scene|location|environment|bedroom|street|pool|beach|museum|palace|garden|window|forest|city|hotel|studio|lake|underwater|terrace|yacht|shoreline)\b|场景|背景|环境|卧室|街道|泳池|海边|博物馆|宫殿|庭院|窗边|森林|城市|酒店|水下"),
    ("camera", r"\b(camera|lens|mm\b|aperture|f/\d|eye[- ]level|low[- ]angle|high[- ]angle|top[- ]view|overhead|three[- ]quarter|full[- ]body|medium shot|close[- ]up|depth of field|bokeh|framing|perspective)\b|镜头|机位|视角|景别|全身|中景|近景|特写|景深|虚化|透视"),
    ("composition", r"\b(composition|foreground|midground|background|negative space|centered|asymmetr|leading lines|layered depth|visual hierarchy|grid|layout|split|panel)\b|构图|前景|中景|背景|留白|视觉层级|网格|布局|排版|分镜|宫格"),
    ("lighting", r"\b(light|lighting|softbox|rim light|backlight|window light|golden hour|daylight|moonlight|neon|chiaroscuro|shadow|highlight|reflector|diffused|directional)\b|光线|灯光|柔光|轮廓光|逆光|窗光|黄金时刻|月光|霓虹|阴影|高光|反光板"),
    ("color", r"\b(color|colour|palette|tone|saturation|contrast|warm|cool|teal|gold|ivory|pink|blue|red|green|black|white)\b|颜色|配色|色调|饱和度|对比度|冷暖|金色|粉色|蓝色|红色|绿色|黑白"),
    ("emotion", r"\b(mood|emotion|emotional|calm|confident|mysterious|nostalgic|dreamy|quiet|romantic|elegant|restrained|playful|serene|intimate|ethereal)\b|氛围|情绪|神秘|怀旧|梦幻|安静|浪漫|优雅|克制|空灵|温柔|冷艳"),
    ("narrative", r"\b(as if|moment|story|storytelling|caught in|just before|just after|between|discover|encounter|memory|private|secret|journey|micro-story)\b|故事|叙事|瞬间|仿佛|刚刚|相遇|记忆|旅程"),
    ("text_layout", r"\b(title|subtitle|headline|typography|font|label|caption|text|logo|calligraphy|handwritten|poster|magazine cover|infographic)\b|标题|副标题|字体|文字|标签|海报|信息图|书法|手写|排版"),
    ("constraint", r"\b(avoid|do not|don't|must not|no |prohibit|without|keep unchanged|strictly|must )\b|避免|不要|禁止|必须|保持不变|严格"),
    ("quality_low_signal", r"\b(masterpiece|best quality|8k|16k|32k|ultra[- ]?hd|high resolution|high-resolution|hyper[- ]?detailed|ultra[- ]?detailed)\b"),
]

METHOD_RULES = {
    "emotion": r"\b(mood|emotion|atmosphere|nostalgic|mysterious|dreamy|restrained|ethereal|romantic|quiet)\b|氛围|情绪|梦幻|怀旧|神秘|克制|空灵|浪漫",
    "structure": r"\b(composition|lighting|camera|subject|environment|wardrobe|layout|material|aspect ratio|scene:)\b|构图|灯光|镜头|主体|场景|服装|布局|材质|画幅",
    "result": r"\b(create|generate|depict|show|final image|should look|image should)\b|生成|创建|请生成|呈现",
    "process": r"\b(shot on|photographed with|lit with|post[- ]processing|fabrication|cast using|painted with|printed from)\b|拍摄|摄影|后期|制作工艺|铸造|绘制|印刷",
    "reference": r"\b(style reference|reference image|in the style|inspired by|era|art nouveau|film noir|ukiyo-e)\b",
    "variable_template": r"\[[^\]]+\]|\{[^\}]+\}|【[^】]+】|\bfill in\b|\btemplate\b|模板|填写",
    "constraint": r"\b(avoid|do not|must not|no [a-z]|prohibit|constraints?)\b|避免|不要|禁止|必须|约束",
    "narrative": r"\b(as if|story|storytelling|caught in|just before|just after|secret|journey|memory)\b|故事|叙事|仿佛|旅程|记忆",
    "medium": r"\b(film scan|watercolor|ink painting|woodblock|porcelain|bronze|marble|paper craft|magazine|photograph|poster|mural)\b|摄影|水彩|水墨|木版|瓷器|青铜|大理石|纸艺|杂志|海报|壁画",
    "design_system": r"\b(layout|grid|title at|left side|right side|top|bottom|columns?|panel|visual hierarchy|negative space)\b|布局|排版|网格|标题|左侧|右侧|顶部|底部|分栏|视觉层级|留白",
}

LOW_SIGNAL_TERMS = {
    "masterpiece": r"\bmasterpiece\b",
    "8k_16k_hype": r"\b(?:8k|16k|32k)\b",
    "best_quality": r"\bbest quality\b",
    "generic_ultra_detail": r"\bultra[- ]?(?:detailed|realistic|hd)\b|\bhyper[- ]?detailed\b",
    "camera_brand": r"\b(?:Hasselblad|Canon EOS|Sony A7|Nikon|Leica|Fujifilm)\b",
}


def split_clauses(prompt: str) -> list[str]:
    prompt = prompt.replace("\r\n", "\n")
    units=[]
    for line in prompt.splitlines():
        line=line.strip(" \t-*•")
        if not line: continue
        # Preserve short labeled clauses while splitting prose sentences.
        parts=re.split(r"(?<=[.!?])\s+(?=[A-Z\[\{])", line)
        units.extend(x.strip() for x in parts if x.strip())
    return units


def classify_clause(text: str) -> list[str]:
    low=text.casefold(); out=[]
    for category,pattern in CLAUSE_RULES:
        if re.search(pattern, low, flags=re.I): out.append(category)
    if not out: out=["other"]
    return out


def detect_prompt_methods(prompt: str) -> list[str]:
    return [name for name,pattern in METHOD_RULES.items() if re.search(pattern,prompt,flags=re.I)]


def low_signal_audit(prompt: str) -> dict:
    findings=[]
    for name,pattern in LOW_SIGNAL_TERMS.items():
        matches=re.findall(pattern,prompt,flags=re.I)
        if matches:
            status="context_dependent" if name=="camera_brand" else "unverified_low_signal"
            findings.append({"term_class":name,"count":len(matches),"status":status})
    # repeated adjective-ish tokens
    words=re.findall(r"\b[a-z][a-z-]{3,}\b",prompt.casefold())
    repeats=[{"token":w,"count":n,"status":"potentially_redundant"} for w,n in Counter(words).most_common() if n>=5 and w in {"realistic","elegant","natural","beautiful","detailed","soft","cinematic","premium","high"}]
    return {"findings":findings,"repeated_descriptors":repeats,"low_signal_count":sum(x["count"] for x in findings)}


def decompose_prompt(prompt: str) -> dict:
    clauses=[]; category_counts=Counter()
    for i,text in enumerate(split_clauses(prompt),1):
        cats=classify_clause(text)
        for c in cats: category_counts[c]+=1
        clauses.append({"clause_id":f"c{i:03d}","text":text,"categories":cats})
    return {
        "schema_version":"1.0",
        "clauses":clauses,
        "category_counts":dict(category_counts),
        "prompt_methods":detect_prompt_methods(prompt),
        "low_signal":low_signal_audit(prompt),
    }


def quality_audit(prompt: str) -> dict:
    d=decompose_prompt(prompt); counts=d["category_counts"]
    issues=[]
    if counts.get("quality_low_signal",0)>=3:
        issues.append({"code":"low_signal_density","severity":"warning","message":"Several quality-hype clauses appear; test whether they contribute before retaining them."})
    if counts.get("constraint",0)>10:
        issues.append({"code":"constraint_density","severity":"warning","message":"Constraint density is high; prefer targeted likely failure modes."})
    if counts.get("pose",0) and not counts.get("body_mechanics",0):
        issues.append({"code":"pose_without_mechanics","severity":"info","message":"Pose is described without explicit support/weight mechanics."})
    if counts.get("wardrobe",0) and counts.get("material",0)==0:
        issues.append({"code":"wardrobe_material_vague","severity":"info","message":"Wardrobe is present without a visible material cue."})
    if counts.get("camera",0)>=3 and d["low_signal"]["low_signal_count"]:
        issues.append({"code":"technical_specificity_audit","severity":"info","message":"Technical specificity and low-signal terms coexist; verify that each camera/quality clause controls a visible outcome."})
    return {"decomposition":d,"issues":issues}
