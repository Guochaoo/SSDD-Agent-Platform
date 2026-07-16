"""场景与训练服务测试：唯一约束、默认模型切换事务、训练指标写入"""
import pytest
from fastapi import HTTPException

from app.entity.db_models import User
from app.services.scene_service import scene_service
from app.services.training_service import training_service


def _make_user(db):
    user = User(username="alice", email="alice@example.com", hashed_password="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_scene_name_must_be_unique(db_session):
    scene_service.create_scene(db_session, "steel_surface_defect", "钢铁表面缺陷检测", "industry", ["crazing"])
    with pytest.raises(HTTPException) as exc:
        scene_service.create_scene(db_session, "steel_surface_defect", "重复场景", "industry", ["x"])
    assert exc.value.status_code == 400


def test_training_task_lifecycle_and_metrics(db_session):
    user = _make_user(db_session)
    scene = scene_service.create_scene(db_session, "steel_surface_defect", "钢铁表面缺陷检测", "industry", ["crazing"])

    task = training_service.create_task(db_session, user.id, scene.id, epochs=10)
    assert task.status == "pending"
    assert task.task_uuid  # 自动生成了唯一标识

    training_service.start_task(db_session, task.id)
    training_service.record_epoch_metric(db_session, task.id, epoch=1, box_loss=0.5, map50=0.3)
    training_service.record_epoch_metric(db_session, task.id, epoch=5, box_loss=0.2, map50=0.6)
    completed = training_service.complete_task(db_session, task.id)

    assert completed.status == "completed"
    assert completed.current_epoch == 5
    assert completed.progress == 100

    metrics = training_service.list_metrics(db_session, task.id)
    assert [m.epoch for m in metrics] == [1, 5]  # 按 epoch 顺序返回，用于画曲线


def test_set_default_model_swaps_atomically(db_session):
    """切换默认模型：同一场景任意时刻只能有一个默认模型"""
    user = _make_user(db_session)
    scene = scene_service.create_scene(db_session, "steel_surface_defect", "钢铁表面缺陷检测", "industry", ["crazing"])

    m1 = training_service.create_model_version(db_session, scene.id, "v1.0.0", "yolov11n", "/models/v1.pt")
    m2 = training_service.create_model_version(db_session, scene.id, "v1.1.0", "yolov11n", "/models/v2.pt")

    scene_service.set_default_model(db_session, scene.id, m1.id)
    db_session.refresh(m1)
    assert m1.is_default is True

    scene_service.set_default_model(db_session, scene.id, m2.id)
    db_session.refresh(m1)
    db_session.refresh(m2)
    assert m1.is_default is False  # 旧默认被自动取消
    assert m2.is_default is True


def test_scene_model_list_keeps_non_default_versions_visible(db_session):
    user = _make_user(db_session)
    scene = scene_service.create_scene(db_session, "visible_versions", "Visible versions", "industry", ["crazing"])
    old_model = training_service.create_model_version(db_session, scene.id, "v1.0.0", "yolo11n", "/models/v1.pt")
    current_model = training_service.create_model_version(db_session, scene.id, "v3.0.0", "yolo11n", "/models/v3.pt")
    deleted_model = training_service.create_model_version(db_session, scene.id, "v0.9.0", "yolo11n", "/models/old.pt")
    scene_service.set_default_model(db_session, scene.id, current_model.id)
    deleted_model.status = "deleted"
    db_session.commit()

    models = scene_service.list_model_versions(db_session, scene.id)

    assert [model.id for model in models] == [current_model.id, old_model.id]


def test_archived_model_cannot_become_default(db_session):
    scene = scene_service.create_scene(db_session, "active_default", "Active default", "industry", ["crazing"])
    model = training_service.create_model_version(db_session, scene.id, "v1.0.0", "yolo11n", "/models/v1.pt")
    model.status = "archived"
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        scene_service.set_default_model(db_session, scene.id, model.id)

    assert exc.value.status_code == 404


def test_training_task_rejects_unknown_scene(db_session):
    user = _make_user(db_session)
    with pytest.raises(HTTPException) as exc:
        training_service.create_task(db_session, user.id, scene_id=999999)
    assert exc.value.status_code == 404
