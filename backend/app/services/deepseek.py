"""DeepSeek API integration for AI-powered features."""
import json
import math
import random
import httpx
from ..core.config import settings


# ── Personas for diverse recommendations ──
_RECOMMENDATION_PERSONAS = [
    {
        "name": "热情的社团达人",
        "system": "你是一个充满活力的校园社团达人。你了解每个社团的独特魅力，推荐时像给朋友安利宝藏一样自然热情。",
        "angle": "match",
        "reason_style": "口语化、亲切，像朋友推荐",
    },
    {
        "name": "细心的校园向导",
        "system": "你是一个温暖贴心的学长/学姐。你帮助新生和同学找到适合他们的社团，推荐时关注他们的成长需求。",
        "angle": "explore",
        "reason_style": "温暖鼓励，强调社团能带来的成长",
    },
    {
        "name": "理性的数据分析师",
        "system": "你是一个善于分析数据的社团顾问。你根据社团的活跃度、成员数、活动质量等客观指标来推荐。",
        "angle": "quality",
        "reason_style": "客观理性，引用数据支撑推荐",
    },
    {
        "name": "好奇的跨界探索者",
        "system": "你相信跨领域的学习能带来意想不到的收获。你推荐时不仅考虑兴趣匹配，也鼓励用户尝试新鲜领域。",
        "angle": "explore",
        "reason_style": "激发好奇心，强调跨界价值",
    },
    {
        "name": "幽默的社交达人",
        "system": "你是一个风趣幽默的社交达人。你了解哪些社团氛围好、活动有趣、容易交到朋友，推荐时轻松有趣。",
        "angle": "social",
        "reason_style": "轻松幽默，强调社交和氛围",
    },
    {
        "name": "资深校园观察者",
        "system": "你是一个对校园社团生态了如指掌的观察者。你推荐时会联系社团的口碑和校园文化背景。",
        "angle": "quality",
        "reason_style": "有洞察力，强调口碑和独特价值",
    },
    {
        "name": "AI社团顾问",
        "system": "你是一个专业的高校社团智能顾问。你综合运用标签匹配和内容分析，提供个性化精准推荐。",
        "angle": "match",
        "reason_style": "专业精准，解释匹配逻辑",
    },
    {
        "name": "文艺社团引路人",
        "system": "你是一个温文尔雅的文艺青年。你用诗意的语言描述每个社团的独特气质，帮助用户找到心灵归属。",
        "angle": "social",
        "reason_style": "有诗意和画面感，触动情感",
    },
]

_VARIATION_SEEDS = [
    "推荐语控制在12-25字之间，每条风格不同",
    "至少包含2种不同格式的推荐语：有的用问句开头，有的用感叹，有的用陈述",
    "每条推荐语都用不同的表达方式，避免重复句式",
    "想象你在给不同性格的同学推荐——有人需要鼓励，有人需要数据，有人需要氛围",
    "推荐语中可适当使用emoji增加表现力（但不要过度）",
    "在推荐语中用创意的比喻来描述社团特点",
]


async def chat_completion(messages: list[dict], max_tokens: int = 800, temperature: float = 0.7) -> str:
    """通用 DeepSeek 对话补全调用。"""
    if not settings.DEEPSEEK_API_KEY:
        return "[AI服务未配置API Key]"

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            data = resp.json()
            if resp.status_code != 200:
                return f"[AI调用失败: {data.get('error', {}).get('message', '未知错误')}]"
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[AI调用失败: {str(e)}]"


async def recommend_clubs(
    user_interests: str,
    clubs_data: list[dict],
    user_joined_club_ids: list[int] | None = None,
    user_activity_club_ids: list[int] | None = None,
) -> list[dict]:
    """基于用户兴趣和社团数据，使用 DeepSeek 进行多样化智能推荐。"""
    if not settings.DEEPSEEK_API_KEY:
        return fallback_recommend(user_interests, clubs_data, user_joined_club_ids)

    joined = set(user_joined_club_ids or [])

    # Randomize persona, seed, temperature
    persona = random.choice(_RECOMMENDATION_PERSONAS)
    seed = random.choice(_VARIATION_SEEDS)
    temperature = round(random.uniform(0.75, 1.15), 2)

    # Build rich club text, skip user's own clubs
    clubs_text_lines = []
    for c in clubs_data:
        if c["id"] in joined:
            continue
        recent_acts = c.get("recent_activities", [])
        act_str = ""
        if recent_acts:
            act_str = " | 近期活动: " + "、".join(
                a.get("title", "")[:20] for a in recent_acts[:3]
            )
        clubs_text_lines.append(
            f"- ID:{c['id']} | {c['name']} | 标签:{c.get('tags','')} "
            f"| 描述:{c.get('description','')[:150]} "
            f"| 活动数:{c.get('activity_count',0)} | 成员数:{c.get('member_count',0)} "
            f"| 评分:{c.get('star_rating','暂无')}"
            f"{act_str}"
        )

    if not clubs_text_lines:
        return []

    clubs_text = "\n".join(clubs_text_lines)

    # Build user context
    user_context = f"用户兴趣标签: {user_interests}"
    if user_joined_club_ids:
        user_context += f"\n用户已加入社团ID: {user_joined_club_ids}（避免推荐同类社团，除非确实值得）"
    if user_activity_club_ids:
        user_context += f"\n用户近期参与活动的社团ID: {user_activity_club_ids}（说明用户对这些方向有兴趣）"

    system_msg = (
        f"{persona['system']}\n"
        f"推荐角度偏好: {persona['angle']}。\n"
        f"推荐语风格要求: {persona['reason_style']}。\n"
        f"{seed}\n"
        f"额外要求:\n"
        f"- 不要只推荐纯标签匹配的社团，至少穿插1-2个热门/高品质的探索型推荐\n"
        f"- 推荐排序要综合匹配度、活跃度、成员口碑\n"
        f"- 避免推荐语千篇一律，每条推荐语的表达角度都要不同\n"
    )

    user_msg = (
        f"{user_context}\n\n"
        f"可选社团列表:\n{clubs_text}\n\n"
        f"请返回JSON数组格式（只返回JSON，不要其他文字），每个推荐对象包含:\n"
        f'- club_id: 社团ID（整数）\n'
        f'- reason: 推荐理由（12-25字，风格多样，直接描述亮点）\n'
        f'- category: 推荐类别，从["兴趣匹配","热门推荐","探索新领域","高评分推荐","基于你的活动偏好"]中选择一个\n'
        f"- highlights: 1-2个社团亮点短语的数组\n"
        f"按推荐优先级降序排列，最多5个。\n"
        f'示例格式: [{{"club_id":1,"reason":"喜欢AI的你，一定会爱上这里的比赛氛围✨","category":"兴趣匹配","highlights":["每周技术分享","ACM金牌导师"]}}]'
    )

    result = await chat_completion(
        [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=temperature,
    )

    try:
        text = result.strip()
        if text.startswith("```"):
            text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        if not text.startswith("["):
            # Try to find JSON array
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end != -1:
                text = text[start:end + 1]
        recommendations = json.loads(text)
        for r in recommendations:
            if "category" not in r:
                r["category"] = "综合推荐"
            if "highlights" not in r or not isinstance(r.get("highlights"), list):
                r["highlights"] = []
        return recommendations
    except Exception:
        return fallback_recommend(user_interests, clubs_data, user_joined_club_ids)


def _cosine_similarity(a, b):
    """Pure-Python cosine similarity between two equal-length vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def fallback_recommend(
    user_interests: str,
    clubs_data: list[dict],
    user_joined_club_ids: list[int] | None = None,
) -> list[dict]:
    """语义兜底：使用 sentence-transformers 做相似度匹配。"""
    joined = set(user_joined_club_ids or [])
    candidates = [c for c in clubs_data if c["id"] not in joined]
    if not candidates:
        candidates = clubs_data

    if not user_interests or user_interests == "无特别偏好":
        sorted_clubs = sorted(candidates, key=lambda c: c.get("member_count", 0), reverse=True)
        return [
            {
                "club_id": c["id"],
                "reason": f"热门社团 · {c['name']}",
                "category": "热门推荐",
                "highlights": [c.get("tags", "")] if c.get("tags") else [],
            }
            for c in sorted_clubs[:5]
        ]

    try:
        from .knowledge_base import _get_model
        model = _get_model()

        def _club_text(c):
            recent = " ".join(a.get("title", "") for a in c.get("recent_activities", [])[:3])
            return f"{c.get('name','')} {c.get('tags','')} {c.get('description','')[:200]} {recent}"

        club_texts = [_club_text(c) for c in candidates]
        interest_vec = model.encode([user_interests])[0]
        club_vecs = model.encode(club_texts)

        scored = [
            (float(_cosine_similarity(interest_vec, club_vecs[i])), candidates[i])
            for i in range(len(candidates))
        ]
        scored.sort(key=lambda x: x[0], reverse=True)

        cat_pool = ["兴趣匹配", "可能感兴趣", "推荐关注", "值得一试", "热门推荐"]
        return [
            {
                "club_id": c["id"],
                "reason": f"{cat_pool[min(i, len(cat_pool)-1)]} · {c['name']}",
                "category": cat_pool[min(i, len(cat_pool)-1)],
                "highlights": [c.get("tags", "")] if c.get("tags") else [],
            }
            for i, (_, c) in enumerate(scored[:5])
        ]
    except Exception:
        sorted_clubs = sorted(candidates, key=lambda c: c.get("member_count", 0), reverse=True)
        return [
            {
                "club_id": c["id"],
                "reason": f"热门社团 · {c['name']}",
                "category": "热门推荐",
                "highlights": [],
            }
            for c in sorted_clubs[:5]
        ]


_COPY_PERSONAS = [
    {
        "name": "热情昂扬型",
        "system": "你是一个充满激情的高校社团宣传员。你的文案感染力强，善用感叹号和强有力的动词，让人读后热血沸腾、立刻想报名。",
        "style": "多用感叹句和短句，节奏明快，充满能量感。开头用一句震撼的话抓住注意力。",
    },
    {
        "name": "冷静专业型",
        "system": "你是一个专业的高校社团品牌策划。你的文案理性、有深度，用数据和事实说话，展现社团的专业性和价值。",
        "style": "用冷静克制的语言，强调社团的成就、数据、专业度。适合学术类/科技类社团。格式规范，段落清晰。",
    },
    {
        "name": "幽默风趣型",
        "system": "你是一个风趣幽默的校园段子手。你擅长用轻松诙谐的方式介绍社团，让人会心一笑的同时产生好感。",
        "style": "用轻松口语化表达，适当玩梗，像朋友吐槽一样自然。可以用自问自答或反转式开头。",
    },
    {
        "name": "诗意浪漫型",
        "system": "你是一个有文艺气质的社团诗人。你用优美的文字描绘社团生活，让人感受到社团的独特气质和美好氛围。",
        "style": "用诗意的比喻和画面感的语言，节奏舒缓。适合文艺类/艺术类社团。开头可以用一句诗或一个意象。",
    },
    {
        "name": "紧迫行动型",
        "system": "你是一个擅长制造紧迫感的营销文案高手。你的文案让人产生'再不报名就晚了'的感觉，驱动立即行动。",
        "style": "强调限时、限量、机会难得。用短句和数字制造节奏感。结尾有明确的行动号召。",
    },
    {
        "name": "温暖走心型",
        "system": "你是一个温暖贴心的学长/学姐。你的文案像在跟学弟学妹谈心，分享真实感受，用真诚打动人心。",
        "style": "用第一人称或第二人称，语气亲切温暖。分享真实体验和成长故事。适合志愿类/互助类社团。",
    },
    {
        "name": "简洁现代型",
        "system": "你是一个追求极简风格的品牌文案。你的文案干净利落，没有废话，用最少的字传达最核心的信息。",
        "style": "极简风格，短小精悍。善用换行和留白制造节奏。一句话一行，每句话都有力量。适合现代感强的社团。",
    },
    {
        "name": "校园故事型",
        "system": "你是一个擅长讲故事的校园记者。你用一个小故事或场景切入，让读者产生代入感，自然地引出社团介绍。",
        "style": "以一个小故事或场景开头（如'某个午后的教学楼...'），用叙事的方式呈现社团的价值。有画面感，像微小说。",
    },
]

_POSTER_VARIATION_SEEDS = [
    "标题用问句形式开头，引发好奇（如'想不想...？'或'你还在...吗？'）",
    "标题用感叹形式，加具体数字吸引眼球（如'仅剩3天！'或'第5届...震撼来袭！'）",
    "亮点数量随机3-5个，不要太整齐，每个亮点的句式结构要有变化",
    "CTA按钮文案要有创意，不要用'立即报名'这种平淡表达，用更有行动力的短语",
    "副标题可以适当用emoji点缀，增加视觉吸引力",
    "标题可以用对偶、比喻或反差手法，让海报文案更有设计感和记忆点",
]


async def generate_copy(prompt: str, max_tokens: int = 500) -> str:
    """生成招新文案、活动通知等。每次随机选择文案风格。"""
    persona = random.choice(_COPY_PERSONAS)
    system = (
        f"{persona['system']}\n"
        f"写作风格要求：{persona['style']}\n"
        f"注意：不要写成和其他风格一样的格式，保持本风格的独特性。"
    )
    return await chat_completion([
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ], max_tokens=max_tokens)


async def generate_poster_content(activity_info: dict) -> dict:
    """根据活动信息生成海报的文案内容和动态配色。每次LLM自由创作，无预设限制。"""
    seeds = random.sample(_POSTER_VARIATION_SEEDS, min(2, len(_POSTER_VARIATION_SEEDS)))
    variation = "\n".join(f"- {s}" for s in seeds)

    # Random design direction hints — push LLM away from defaults
    design_hints = random.choice([
        "用一组冷暖对比强烈的配色",
        "用一组温暖舒适的配色",
        "用一组冷峻科技感的配色",
        "用一组自然清新的配色",
        "用一组暗黑高级感的配色",
        "用一组明亮活力的配色",
        "用一组复古胶片感的配色",
        "用一组极简冷淡风的配色",
        "用一组赛博朋克霓虹配色",
        "用一组莫兰迪柔和低饱和配色",
    ])

    prompt = f"""根据以下活动信息，生成一张宣传海报所需的文案内容和配色方案。

活动名称: {activity_info.get('title')}
活动描述: {activity_info.get('description', '')}
活动地点: {activity_info.get('location', '')}
活动时间: {activity_info.get('start_time', '')} 至 {activity_info.get('end_time', '')}

格式变化要求：
{variation}

配色要求：{design_hints}。请根据活动主题自由选择搭配，不要用常见的蓝金/蓝红组合。

请返回JSON格式（只返回JSON，不要其他文字）:
{{
    "headline": "主标题（醒目）",
    "subtitle": "副标题（补充说明）",
    "highlights": ["亮点1", "亮点2", ...],
    "cta": "行动号召文案（创意CTA）",
    "design": {{
        "theme_name": "主题名称（2-4字，如'落日余晖''极光之舞'）",
        "bg_hex": "背景主色HEX（如#0a1628）",
        "bg_mid_hex": "背景渐变色HEX",
        "accent_hex": "强调色HEX（用于标题、按钮）",
        "accent2_hex": "辅助强调色HEX（不同于accent）",
        "card_style": "rounded",
        "gradient_dir": "vertical 或 diagonal",
        "vibe": "配色氛围描述"
    }}
}}"""

    result = await chat_completion(
        [{"role": "user", "content": prompt}],
        temperature=round(random.uniform(0.85, 1.25), 2),
    )
    try:
        if not result.startswith("{"):
            result = result.strip()
        return json.loads(result)
    except json.JSONDecodeError:
        return {
            "headline": activity_info.get("title", "精彩活动"),
            "subtitle": "欢迎参加",
            "highlights": ["精彩内容等你来"],
            "cta": "立即报名",
        }
