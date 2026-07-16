from app.config.settings import settings
from app.entity.db_models import DetectionScene, ModelVersion, TrainingMetric, TrainingTask, User
from app.training.training_service import TrainingService


def test_export_does_not_create_artifacts_when_validation_fails(
    db_session, monkeypatch, tmp_path
):
    """导出前验证失败时，不得发布未评估的模型文件或版本记录。"""
    user = User(username="exporter", email="exporter@example.com", hashed_password="x")
    scene = DetectionScene(
        name="export_scene",
        display_name="Export scene",
        category="test",
        class_names=["defect"],
    )
    db_session.add_all([user, scene])
    db_session.commit()

    task = TrainingTask(
        user_id=user.id,
        scene_id=scene.id,
        task_uuid="export-failure",
        status="completed",
        model_name="yolo11n",
        img_size=640,
    )
    db_session.add(task)
    db_session.commit()

    weights = tmp_path / "runs" / "train" / "task_export-failure" / "weights"
    weights.mkdir(parents=True)
    (weights / "best.pt").write_bytes(b"weights")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "TRAIN_OUTPUT_DIR", "runs/train")
    monkeypatch.setattr(
        TrainingService,
        "validate_model",
        staticmethod(lambda *_args, **_kwargs: {"error": "validation unavailable"}),
    )

    result = TrainingService.export_model(db_session, task.id, upload_minio=False)

    assert result == {"error": "模型导出前评估失败: validation unavailable"}
    assert not (tmp_path / "models").exists()


def test_delete_finished_training_task_removes_metrics_and_keeps_model_version(
    db_session, monkeypatch, tmp_path
):
    user = User(username="deleter", email="deleter@example.com", hashed_password="x")
    scene = DetectionScene(
        name="delete_scene", display_name="Delete scene", category="test", class_names=["defect"]
    )
    db_session.add_all([user, scene])
    db_session.commit()
    task = TrainingTask(
        user_id=user.id, scene_id=scene.id, task_uuid="delete-finished", status="completed"
    )
    db_session.add(task)
    db_session.flush()
    db_session.add(TrainingMetric(task_id=task.id, epoch=1, map50=0.5))
    model = ModelVersion(
        scene_id=scene.id,
        training_task_id=task.id,
        version="v1.0.0",
        model_name="saved_model",
        model_path="models/saved.pt",
    )
    db_session.add(model)
    db_session.commit()

    output_dir = tmp_path / "runs" / "train" / "task_delete-finished"
    output_dir.mkdir(parents=True)
    (output_dir / "results.csv").write_text("epoch\n0\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "TRAIN_OUTPUT_DIR", "runs/train")

    result = TrainingService.delete_training_task(db_session, task.id)

    assert result["task_id"] == task.id
    assert db_session.query(TrainingTask).filter_by(id=task.id).first() is None
    assert db_session.query(TrainingMetric).filter_by(task_id=task.id).count() == 0
    db_session.refresh(model)
    assert model.training_task_id is None
    assert not output_dir.exists()
