"""
知识库服务测试：权限边界（用户隔离 / 系统文档可见性 / 管理员越权访问）

不覆盖 add_chunks / search_similar_chunks：knowledge_chunks 表用了 pgvector 的
Vector 类型，SQLite 测试库里没建这张表（见 conftest.py），向量检索需要连真实
PostgreSQL + pgvector 才能测，这里只测文档级别的增删查权限。
"""
import pytest
from fastapi import HTTPException

from app.entity.db_models import User
from app.services.knowledge_service import knowledge_service


def _make_user(db, username, is_superuser=False):
    user = User(
        username=username, email=f"{username}@example.com",
        hashed_password="x", is_superuser=is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_doc(db, user_id, title="doc"):
    return knowledge_service.create_document(
        db, user_id=user_id, title=title, filename=f"{title}.txt",
        file_url=f"http://minio/knowledge/{title}.txt", file_type="txt",
    )


def test_owner_can_read_and_admin_sees_all(db_session):
    alice = _make_user(db_session, "alice")
    bob = _make_user(db_session, "bob")
    admin = _make_user(db_session, "admin", is_superuser=True)

    alice_doc = _make_doc(db_session, alice.id, "alice-doc")
    _make_doc(db_session, bob.id, "bob-doc")
    system_doc = _make_doc(db_session, None, "system-doc")

    # 非管理员只能看到：自己的 + 系统内置的，看不到别人的私有文档
    alice_visible = knowledge_service.list_documents(db_session, user_id=alice.id, is_superuser=False)
    assert {d.title for d in alice_visible} == {"alice-doc", "system-doc"}

    # 管理员能看到全部
    admin_visible = knowledge_service.list_documents(db_session, user_id=admin.id, is_superuser=True)
    assert {d.title for d in admin_visible} == {"alice-doc", "bob-doc", "system-doc"}

    # get_document：越权访问别人的私有文档要 403，系统文档任何登录用户都能读
    with pytest.raises(HTTPException) as exc:
        knowledge_service.get_document(db_session, alice_doc.id, user_id=bob.id, is_superuser=False)
    assert exc.value.status_code == 403

    got = knowledge_service.get_document(db_session, system_doc.id, user_id=bob.id, is_superuser=False)
    assert got.title == "system-doc"


def test_delete_permission_boundary(db_session):
    alice = _make_user(db_session, "alice")
    bob = _make_user(db_session, "bob")
    admin = _make_user(db_session, "admin", is_superuser=True)

    alice_doc = _make_doc(db_session, alice.id, "alice-doc")
    system_doc = _make_doc(db_session, None, "system-doc")

    # bob 删不了 alice 的文档
    with pytest.raises(HTTPException) as exc:
        knowledge_service.delete_document(db_session, alice_doc.id, user_id=bob.id, is_superuser=False)
    assert exc.value.status_code == 403

    # 普通用户删不了系统内置文档
    with pytest.raises(HTTPException) as exc:
        knowledge_service.delete_document(db_session, system_doc.id, user_id=alice.id, is_superuser=False)
    assert exc.value.status_code == 403

    # 本人可以删自己的文档
    knowledge_service.delete_document(db_session, alice_doc.id, user_id=alice.id, is_superuser=False)
    with pytest.raises(HTTPException) as exc:
        knowledge_service.get_document(db_session, alice_doc.id, user_id=alice.id, is_superuser=False)
    assert exc.value.status_code == 404

    # 管理员可以删系统文档
    knowledge_service.delete_document(db_session, system_doc.id, user_id=admin.id, is_superuser=True)


def test_delete_nonexistent_document_raises_404(db_session):
    alice = _make_user(db_session, "alice")
    with pytest.raises(HTTPException) as exc:
        knowledge_service.delete_document(db_session, 9999, user_id=alice.id, is_superuser=False)
    assert exc.value.status_code == 404
