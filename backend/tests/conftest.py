import sys
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, types
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from pgvector.sqlalchemy import Vector

# SQLite 没有 pgvector 扩展，测试库连不上真正的 vector 类型。knowledge_chunks 表
# 里唯一用到 Vector 的就是 embedding 列，这里把它在 SQLite 方言下编译成 BLOB，
# 只是为了让表能建出来、外键级联删除等 ORM 行为可以测；向量本身的相似度检索
# （cosine_distance 是 pgvector 提供的 SQL 函数）在 SQLite 下仍然测不了，
# 需要连真实 PostgreSQL + pgvector 才能验证。
@compiles(Vector, "sqlite")
def _compile_vector_sqlite(type_, compiler, **kw):
    return "BLOB"

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ["DEBUG"] = "true"

from app.database.session import Base, get_db  # noqa: E402
from app.entity import db_models  # noqa: E402,F401
from main import app  # noqa: E402


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
