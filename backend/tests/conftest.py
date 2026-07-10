"""
pytest 共享 fixture
使用内存 SQLite 作为测试数据库：足以验证建表、唯一约束、外键、JSON 读写、
事务回滚等核心逻辑，速度快且不需要真实 Postgres。

注意：knowledge_chunks 表的 embedding 列用的是 pgvector 的 VECTOR 类型，
SQLite 不支持，所以测试库建表时会跳过这张表——RAG 相关测试需要连真实的
Postgres + pgvector（可以另外接 testcontainers 或本地 docker-compose 的库来跑）。
"""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database.session import Base
from app.entity import db_models  # noqa: F401  确保所有模型都注册到 Base.metadata


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    # SQLite 默认不强制外键约束，这里手动开启，否则外键相关的测试没有意义
    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    tables = [t for name, t in Base.metadata.tables.items() if name != "knowledge_chunks"]
    Base.metadata.create_all(bind=engine, tables=tables)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
