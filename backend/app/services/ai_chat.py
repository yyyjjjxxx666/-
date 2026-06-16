"""SSE streaming chat service for the floating AI assistant."""
import json
import asyncio
import httpx
from typing import AsyncGenerator

from ..core.config import settings

_SYSTEM_PROMPT = """你是"社团管理系统"的AI智能小助手。帮助用户解答社团、活动、系统使用的问题。

回答要求：语气亲切，简洁明了（150字以内），给出清晰步骤。如果知识库有相关信息优先引用。请使用纯文本回答，不要使用任何Markdown格式符号（如*、**、#、-列表等），不要使用加粗、斜体或代码块。"""

async def stream_chat_response(
    question: str,
    user_context: dict | None = None,
    history: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    """Yield SSE data chunks from DeepSeek streaming response."""
    if not settings.DEEPSEEK_API_KEY:
        yield "AI服务未配置API Key，请联系管理员。"
        return

    # Yield thinking indicator immediately so user sees something
    yield "正在思考..."

    # Query knowledge base (fast after pre-warm)
    kb_context = ""
    try:
        chunks = _sync_kb_query(question, top_k=2)
        if chunks:
            kb_context = "\n".join([c["content"][:200] for c in chunks])
    except Exception:
        pass

    # Build messages
    system = _SYSTEM_PROMPT
    if kb_context:
        system += f"\n\n参考知识：\n{kb_context}"

    user_info = ""
    if user_context:
        parts = []
        if user_context.get("name"):
            parts.append(f"姓名={user_context['name']}")
        if user_context.get("role"):
            parts.append(f"角色={user_context['role']}")
        if user_context.get("interests"):
            parts.append(f"兴趣={user_context['interests']}")
        if user_context.get("club_name"):
            parts.append(f"社团={user_context['club_name']}")
        if parts:
            user_info = f"\n用户信息：{'，'.join(parts)}"

    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question + user_info})

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            async with client.stream(
                "POST",
                f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": messages,
                    "max_tokens": 300,
                    "temperature": 0.7,
                    "stream": True,
                },
            ) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    yield f"[AI调用失败: {resp.status_code}]"
                    return

                first_chunk = True
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0]["delta"].get("content", "")
                        if delta:
                            if first_chunk:
                                # Replace "thinking" indicator with real content
                                yield delta
                                first_chunk = False
                            else:
                                yield delta
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
    except httpx.TimeoutException:
        yield "请求超时，请稍后重试。"
    except Exception as e:
        yield f"抱歉，出错了：{str(e)[:80]}"


def _sync_kb_query(question: str, top_k: int = 2) -> list:
    """Synchronous wrapper for KB query (runs in thread pool)."""
    from .knowledge_base import query as kb_query
    return kb_query(question, top_k=top_k)
