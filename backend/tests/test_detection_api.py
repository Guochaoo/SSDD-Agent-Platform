"""检测 API 参数与响应契约测试。"""

import io

from PIL import Image

from app.api.auth import get_current_user
from app.entity.db_models import User
from main import app


def _jpeg_bytes():
    output = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(output, format="JPEG")
    return output.getvalue()


def test_single_detection_requires_authentication(client):
    response = client.post(
        "/api/detection/single",
        data={"model_id": "1"},
        files={"file": ("sample.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert response.status_code == 401


def test_single_detection_validates_threshold(client, db_session):
    user = User(username="api-user", email="api@example.com", hashed_password="x")
    db_session.add(user)
    db_session.commit()
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        response = client.post(
            "/api/detection/single",
            data={"model_id": "1", "conf_threshold": "1.5"},
            files={"file": ("sample.jpg", _jpeg_bytes(), "image/jpeg")},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert response.status_code == 422
