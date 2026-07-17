from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker

from app.api import agent
from app.entity.db_models import ChatMessage, ChatSession, User


def test_history_restores_the_original_image_path_for_agent_context(db_session, monkeypatch):
    user = User(username="chat-image", email="chat-image@example.com", hashed_password="x")
    db_session.add(user)
    db_session.flush()
    session = ChatSession(user_id=user.id, session_uuid="session-with-image")
    db_session.add(session)
    db_session.flush()

    image_path = Path(agent.UPLOAD_DIR) / "history-context-test.jpg"
    image_path.write_bytes(b"image")
    db_session.add_all([
        ChatMessage(session_id=session.id, role="user", content="请分析这张图", image_path=str(image_path)),
        ChatMessage(session_id=session.id, role="assistant", content="已收到图片"),
    ])
    db_session.commit()
    monkeypatch.setattr(agent, "SessionLocal", sessionmaker(bind=db_session.get_bind()))

    history = agent._load_history(session.session_uuid, user.id)

    assert history[0]["role"] == "user"
    assert "请分析这张图" in history[0]["content"]
    assert f"[附件图片路径: {image_path}" in history[0]["content"]
    assert history[1] == {"role": "assistant", "content": "已收到图片"}
    image_path.unlink(missing_ok=True)


def test_save_message_keeps_image_only_user_messages(db_session, monkeypatch, tmp_path):
    user = User(username="image-only", email="image-only@example.com", hashed_password="x")
    db_session.add(user)
    db_session.flush()
    session = ChatSession(user_id=user.id, session_uuid="image-only-session")
    db_session.add(session)
    db_session.flush()

    image_path = tmp_path / "image-only.jpg"
    image_path.write_bytes(b"image")
    monkeypatch.setattr(agent, "SessionLocal", sessionmaker(bind=db_session.get_bind()))
    agent._save_message(session.session_uuid, user.id, "user", "", image_path=str(image_path))

    saved = db_session.query(ChatMessage).filter_by(session_id=session.id).one()
    db_session.refresh(session)
    assert saved.content == ""
    assert saved.image_path == str(image_path)
    assert session.message_count == 1
    assert session.title == "图片消息"


def test_chat_stream_initializes_image_path_for_text_only_requests(db_session, monkeypatch):
    """Text-only requests must reach the history save path without NameError."""
    captured = {}

    async def fake_chat_stream(**kwargs):
        yield {"type": "text_chunk", "content": "收到"}

    monkeypatch.setattr(agent.supervisor_agent, "chat_stream", fake_chat_stream)
    monkeypatch.setattr(agent, "_load_history", lambda *_args: [])
    monkeypatch.setattr(
        agent,
        "_save_message",
        lambda *args, **kwargs: captured.setdefault("calls", []).append((args, kwargs)),
    )

    class User:
        id = 7

    class Request:
        headers = {"content-type": "application/json"}

        async def json(self):
            return {"message": "你好", "session_id": "text-only"}

    import asyncio

    response = asyncio.run(agent.chat_stream(Request(), _current_user=User(), db=db_session))
    asyncio.run(_consume(response.body_iterator))
    assert captured["calls"][0][1]["image_path"] is None


async def _consume(iterator):
    async for _ in iterator:
        pass

def test_delete_chat_session_removes_persisted_messages(db_session):
    user = User(username="delete-chat", email="delete-chat@example.com", hashed_password="x")
    db_session.add(user)
    db_session.flush()
    session = ChatSession(user_id=user.id, session_uuid="delete-chat-session")
    db_session.add(session)
    db_session.flush()
    db_session.add(ChatMessage(session_id=session.id, role="user", content="delete me"))
    db_session.commit()

    result = agent.delete_chat_session(session.session_uuid, current_user=user, db=db_session)

    assert result["id"] == session.session_uuid
    assert db_session.query(ChatSession).filter_by(id=session.id).first() is None
    assert db_session.query(ChatMessage).filter_by(session_id=session.id).count() == 0


def test_saved_assistant_message_keeps_agent_tool_trace(db_session, monkeypatch):
    user = User(username="tool-trace", email="tool-trace@example.com", hashed_password="x")
    db_session.add(user)
    db_session.commit()
    monkeypatch.setattr(agent, "SessionLocal", sessionmaker(bind=db_session.get_bind()))

    agent._save_message(
        "tool-trace-session", user.id, "assistant", "done",
        tool_calls=[{"name": "detect_single_image", "status": "success", "result": "{}"}],
    )

    saved = db_session.query(ChatMessage).one()
    assert saved.tool_calls == [{"name": "detect_single_image", "status": "success", "result": "{}"}]


def test_save_message_rejects_session_uuid_owned_by_another_user(db_session, monkeypatch):
    owner = User(username="session-owner", email="owner@example.com", hashed_password="x")
    other = User(username="session-other", email="other@example.com", hashed_password="x")
    db_session.add_all([owner, other])
    db_session.flush()
    db_session.add(ChatSession(user_id=owner.id, session_uuid="shared-session-uuid"))
    db_session.commit()
    monkeypatch.setattr(agent, "SessionLocal", sessionmaker(bind=db_session.get_bind()))

    with pytest.raises(HTTPException) as exc_info:
        agent._save_message("shared-session-uuid", other.id, "user", "不能接管")

    assert exc_info.value.status_code == 409
    assert db_session.query(ChatSession).count() == 1
    assert db_session.query(ChatMessage).count() == 0


def test_chat_stream_rejects_foreign_session_before_streaming(db_session):
    owner = User(username="stream-owner", email="stream-owner@example.com", hashed_password="x")
    other = User(username="stream-other", email="stream-other@example.com", hashed_password="x")
    db_session.add_all([owner, other])
    db_session.flush()
    db_session.add(ChatSession(user_id=owner.id, session_uuid="foreign-stream-session"))
    db_session.commit()

    class Request:
        headers = {"content-type": "application/json"}

        async def json(self):
            return {"message": "你好", "session_id": "foreign-stream-session"}

    import asyncio

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(agent.chat_stream(Request(), _current_user=other, db=db_session))

    assert exc_info.value.status_code == 409


def test_admin_can_list_and_read_other_users_sessions(db_session):
    admin = User(
        username="chat-admin", email="chat-admin@example.com", hashed_password="x",
        is_superuser=True,
    )
    owner = User(username="chat-owner", email="chat-owner@example.com", hashed_password="x")
    db_session.add_all([admin, owner])
    db_session.flush()
    session = ChatSession(user_id=owner.id, session_uuid="admin-visible-session", title="用户会话")
    db_session.add(session)
    db_session.flush()
    db_session.add(ChatMessage(session_id=session.id, role="user", content="仅用于管理员查看"))
    db_session.commit()

    sessions = agent.list_chat_sessions(current_user=admin, db=db_session)
    detail = agent.get_chat_session(session.session_uuid, current_user=admin, db=db_session)

    assert sessions[0]["owner_id"] == owner.id
    assert sessions[0]["owner_username"] == owner.username
    assert detail["owner_username"] == owner.username
    assert detail["messages"][0]["content"] == "仅用于管理员查看"


def test_regular_user_cannot_read_other_users_session(db_session):
    owner = User(username="private-owner", email="private-owner@example.com", hashed_password="x")
    other = User(username="private-other", email="private-other@example.com", hashed_password="x")
    db_session.add_all([owner, other])
    db_session.flush()
    db_session.add(ChatSession(user_id=owner.id, session_uuid="private-session"))
    db_session.commit()

    assert agent.list_chat_sessions(current_user=other, db=db_session) == []
    with pytest.raises(HTTPException) as exc_info:
        agent.get_chat_session("private-session", current_user=other, db=db_session)

    assert exc_info.value.status_code == 404
