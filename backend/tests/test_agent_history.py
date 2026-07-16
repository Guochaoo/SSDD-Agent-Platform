from pathlib import Path

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
