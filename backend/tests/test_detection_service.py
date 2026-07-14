"""YOLO 单图、批量检测服务测试。"""

import io
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image

from app.entity.db_models import DetectionScene, DetectionTask, ModelVersion, User
from app.services.detection_service import DetectionService


def _image_upload(filename="sample.jpg", content_type="image/jpeg", color="white"):
    output = io.BytesIO()
    Image.new("RGB", (32, 24), color).save(output, format="JPEG")
    return UploadFile(filename=filename, file=io.BytesIO(output.getvalue()), headers={"content-type": content_type})


def _seed_detection_data(db_session, model_path):
    user = User(username="detector", email="detector@example.com", hashed_password="x")
    scene = DetectionScene(
        name="steel_surface_defect",
        display_name="钢铁表面缺陷检测",
        category="industry",
        class_names=["crazing", "scratches"],
        class_names_cn={"crazing": "裂纹", "scratches": "划痕"},
    )
    db_session.add_all([user, scene])
    db_session.flush()
    model = ModelVersion(
        scene_id=scene.id,
        version="v1.0.0",
        model_name="ssdd_yolo11n_v1",
        model_type="yolo11n",
        model_path=str(model_path),
        is_default=True,
    )
    db_session.add(model)
    db_session.commit()
    return user, model


class _FakeTensor:
    def __init__(self, value):
        self.value = value

    def item(self):
        return self.value

    def __getitem__(self, _index):
        return self

    def tolist(self):
        return self.value


class _FakeResult:
    names = {0: "crazing", 1: "scratches"}
    boxes = [
        SimpleNamespace(
            cls=_FakeTensor(1),
            conf=_FakeTensor(0.91),
            xyxy=_FakeTensor([1.0, 2.0, 20.0, 16.0]),
        )
    ]

    @staticmethod
    def plot():
        pytest.importorskip("numpy")
        import numpy as np

        return np.zeros((24, 32, 3), dtype=np.uint8)


class _FakeModel:
    def predict(self, **_kwargs):
        return [_FakeResult()]


class _FakeMinIO:
    def __init__(self):
        self.uploaded = []
        self.deleted = []

    def upload_bytes(self, object_name, data, content_type):
        self.uploaded.append((object_name, data, content_type))
        return f"http://minio/ssdd-images/{object_name}"

    def delete_by_url(self, url):
        self.deleted.append(url)


@pytest.mark.asyncio
async def test_single_detection_persists_result(db_session, tmp_path, monkeypatch):
    weights = tmp_path / "model.pt"
    weights.write_bytes(b"weights")
    user, model_version = _seed_detection_data(db_session, weights)
    minio = _FakeMinIO()
    service = DetectionService()
    monkeypatch.setattr(service, "_get_model", lambda _version: _FakeModel())
    monkeypatch.setattr("app.services.detection_service.MinIOClient", lambda: minio)

    response = await service.detect_single(
        db_session, user.id, _image_upload(), model_version.id, 0.25, 0.45
    )

    assert response["status"] == "completed"
    assert response["total_objects"] == 1
    assert response["objects"][0]["class_name_cn"] == "划痕"
    assert len(minio.uploaded) == 2
    task = db_session.query(DetectionTask).filter_by(id=response["task_id"]).one()
    assert task.status == "completed"
    assert task.total_images == 1
    assert task.results[0].bbox == [1.0, 2.0, 20.0, 16.0]


@pytest.mark.asyncio
async def test_single_detection_marks_invalid_image_failed(db_session, tmp_path, monkeypatch):
    weights = tmp_path / "model.pt"
    weights.write_bytes(b"weights")
    user, model_version = _seed_detection_data(db_session, weights)
    service = DetectionService()
    monkeypatch.setattr(service, "_get_model", lambda _version: _FakeModel())
    monkeypatch.setattr("app.services.detection_service.MinIOClient", _FakeMinIO)
    upload = UploadFile(
        filename="broken.jpg",
        file=io.BytesIO(b"not-an-image"),
        headers={"content-type": "image/jpeg"},
    )

    with pytest.raises(HTTPException, match="图片内容无法解析"):
        await service.detect_single(db_session, user.id, upload, model_version.id, 0.25, 0.45)

    task = db_session.query(DetectionTask).one()
    assert task.status == "failed"
    assert task.error_message == "图片内容无法解析"


@pytest.mark.asyncio
async def test_batch_detection_keeps_partial_success(db_session, tmp_path, monkeypatch):
    weights = tmp_path / "model.pt"
    weights.write_bytes(b"weights")
    user, model_version = _seed_detection_data(db_session, weights)
    service = DetectionService()
    monkeypatch.setattr(service, "_get_model", lambda _version: _FakeModel())
    monkeypatch.setattr("app.services.detection_service.MinIOClient", _FakeMinIO)
    broken = UploadFile(
        filename="broken.txt",
        file=io.BytesIO(b"bad"),
        headers={"content-type": "text/plain"},
    )

    response = await service.detect_batch(
        db_session,
        user.id,
        [_image_upload("ok.jpg"), broken],
        model_version.id,
        0.25,
        0.45,
    )

    assert response["success_count"] == 1
    assert response["failed_count"] == 1
    assert response["items"][0]["status"] == "completed"
    assert response["items"][1]["status"] == "failed"
    task = db_session.query(DetectionTask).one()
    assert task.status == "completed"
    assert task.total_images == 2
    assert task.total_objects == 1


def test_model_path_must_exist(tmp_path):
    with pytest.raises(HTTPException, match="模型权重不存在"):
        DetectionService._resolve_model_path(str(tmp_path / "missing.pt"))
