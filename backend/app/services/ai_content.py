"""AI content generation: tags, descriptions, activity summaries."""

from .deepseek import chat_completion


async def suggest_tags(description: str) -> str:
    """Suggest 3-5 comma-separated tags based on a description."""
    if not description.strip():
        return ""
    prompt = f"""基于以下描述，提取3-5个关键词标签（逗号分隔，每个标签2-4字）。标签要简洁准确：
描述：{description[:300]}
请直接返回标签，如：科技创新,人工智能,编程实践。不要其他文字。"""
    result = await chat_completion([{"role": "user", "content": prompt}], max_tokens=80, temperature=0.5)
    return result.strip().rstrip("。，、.")


async def generate_description(keywords: str) -> str:
    """Generate an attractive club description from keywords."""
    if not keywords.strip():
        return ""
    prompt = f"""用以下关键词生成一段120字以内的社团简介。语言要有号召力和吸引力，突出社团价值：
关键词：{keywords}
请直接返回简介文本，不要其他格式。"""
    result = await chat_completion([{"role": "user", "content": prompt}], max_tokens=250, temperature=0.7)
    return result.strip()


async def generate_activity_summary(activity_title: str, activity_desc: str, checkin_count: int,
                                      registration_count: int, location: str) -> str:
    """Generate a post-event summary."""
    prompt = f"""为已结束的活动写一段100字以内的总结报告：
活动名称：{activity_title}
活动描述：{activity_desc[:200]}
签到人数：{checkin_count}/{registration_count}
地点：{location}

请写一段流畅的活动总结，内容包含活动开展情况和成果。直接返回总结文本。"""
    result = await chat_completion([{"role": "user", "content": prompt}], max_tokens=250, temperature=0.5)
    return result.strip()
