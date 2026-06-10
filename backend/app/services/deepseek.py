"""DeepSeek API integration for AI-powered features."""
import httpx
from ..core.config import settings


async def chat_completion(messages: list[dict], max_tokens: int = 800, temperature: float = 0.7) -> str:
    """通用 DeepSeek 对话补全调用。"""
    if not settings.DEEPSEEK_API_KEY:
        return "[AI服务未配置API Key]"

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


async def recommend_clubs(user_interests: str, clubs_data: list[dict]) -> list[dict]:
    """基于用户兴趣和社团数据，使用DeepSeek进行智能推荐。"""
    if not settings.DEEPSEEK_API_KEY:
        return fallback_recommend(user_interests, clubs_data)

    clubs_text = "\n".join(
        f"- ID:{c['id']} | {c['name']} | 标签:{c.get('tags','')} | 描述:{c.get('description','')[:100]} | 活动数:{c.get('activity_count',0)} | 成员数:{c.get('member_count',0)}"
        for c in clubs_data
    )
    prompt = f"""你是一个社团推荐系统。根据用户的兴趣标签，从以下社团列表中推荐最匹配的社团。

用户兴趣: {user_interests}

社团列表:
{clubs_text}

请返回JSON数组格式，包含推荐社团ID和简短推荐语，按匹配度降序排列，最多5个:
[{{"club_id": 1, "reason": "羽毛球爱好者聚集地"}}, ...]

推荐语要求：每条约10字以内，直接描述社团亮点或为什么适合，不要出现"该用户兴趣为""该社团标签为"等分析性文字。只返回JSON数组。"""

    result = await chat_completion([{"role": "user", "content": prompt}])
    try:
        import json
        if result.startswith("[") or result.startswith("```"):
            result = result.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        recommendations = json.loads(result)
        return recommendations
    except (json.JSONDecodeError, KeyError):
        return fallback_recommend(user_interests, clubs_data)


def fallback_recommend(user_interests: str, clubs_data: list[dict]) -> list[dict]:
    """兜底方案：基于标签关键词匹配。"""
    if not user_interests:
        return [{"club_id": c["id"], "reason": "热门社团"} for c in clubs_data[:5]]

    keywords = set(user_interests.replace("，", ",").split(","))
    scored = []
    for c in clubs_data:
        tags = set((c.get("tags") or "").replace("，", ",").split(","))
        score = len(keywords & tags)
        if score > 0:
            scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"club_id": c["id"], "reason": f"{c['name']}"} for _, c in scored[:5]]


async def generate_copy(prompt: str, max_tokens: int = 500) -> str:
    """生成招新文案、活动通知等。"""
    system = "你是一个高校社团宣传文案专家。根据用户提供的信息，生成吸引人的文案。语言风格活泼但不轻浮。"
    return await chat_completion([
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ], max_tokens=max_tokens)


async def generate_poster_content(activity_info: dict) -> dict:
    """根据活动信息生成海报的文案内容（标题、标语、要点等）。"""
    prompt = f"""根据以下活动信息，生成一张宣传海报所需的文案内容。

活动名称: {activity_info.get('title')}
活动描述: {activity_info.get('description', '')}
活动地点: {activity_info.get('location', '')}
活动时间: {activity_info.get('start_time', '')} 至 {activity_info.get('end_time', '')}

请返回JSON格式（只返回JSON，不要其他文字）:
{{
    "headline": "主标题（醒目，10字以内）",
    "subtitle": "副标题（补充说明，15字以内）",
    "highlights": ["亮点1", "亮点2", "亮点3"],
    "cta": "行动号召文案（如：立即报名/扫码参加等）"
}}"""

    result = await chat_completion([{"role": "user", "content": prompt}])
    try:
        import json
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
