from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..models import get_db
from ..models.user import User
from ..models.chat import Conversation, Message
from ..core.security import decode_access_token
from ..services.ai_chat import stream_chat_response

router = APIRouter(tags=["AI助手"])


def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    payload = decode_access_token(authorization[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="登录已过期")
    user = db.query(User).get(int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


@router.get("/conversations")
def list_conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all conversations for the current user, ordered by last update."""
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return [
        {
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            "message_count": db.query(Message).filter(Message.conversation_id == c.id).count(),
        }
        for c in conversations
    ]


@router.post("/conversations")
def create_conversation(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new conversation."""
    conv = Conversation(user_id=user.id, title="新对话")
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return {
        "id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
    }


@router.get("/conversations/{conversation_id}/messages")
def get_messages(conversation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all messages for a conversation."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a conversation and all its messages."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    db.delete(conv)
    db.commit()
    return {"message": "对话已删除"}


@router.put("/conversations/{conversation_id}/title")
def update_title(conversation_id: int, title: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Rename a conversation."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    new_title = title.get("title", "").strip()
    if not new_title or len(new_title) > 100:
        raise HTTPException(status_code=400, detail="标题不能为空且不超过100字")
    conv.title = new_title
    db.commit()
    return {"message": "标题已更新", "title": new_title}


@router.post("/conversations/{conversation_id}/chat")
async def chat_message(conversation_id: int, body: dict, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """SSE streaming chat. Saves both user and AI messages to the database."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")

    question = body.get("message", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="消息不能为空")

    # Save user message
    user_msg = Message(conversation_id=conv.id, role="user", content=question)
    db.add(user_msg)
    db.commit()

    # Load history (all messages in this conversation)
    history_msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    # Build history for the AI context (all messages except the last user one)
    history = [{"role": m.role, "content": m.content} for m in history_msgs[:-1]]

    # Build user context
    user_context = {
        "name": user.real_name or user.username,
        "role": user.role.value if hasattr(user.role, 'value') else user.role,
    }
    if user.club_id:
        from ..models.club import Club
        club = db.query(Club).get(user.club_id)
        if club:
            user_context["club_name"] = club.name

    async def event_generator():
        full_response = ""
        try:
            async for chunk in stream_chat_response(question, user_context=user_context, history=history):
                if await request.is_disconnected():
                    break
                full_response += chunk
                yield f"data: {chunk}\n\n"
        except Exception as e:
            yield f"data: [错误: {str(e)[:80]}]\n\n"

        # Save AI response to database
        if full_response:
            try:
                ai_msg = Message(conversation_id=conv.id, role="assistant", content=full_response)
                db.add(ai_msg)
                # Auto-title: use first user message to generate title
                if conv.title == "新对话" and len(history_msgs) <= 2:
                    conv.title = question[:30] + ("..." if len(question) > 30 else "")
                conv.updated_at = datetime.utcnow()
                db.commit()
            except Exception:
                pass

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
