from pathlib import Path

from app.config.settings import settings
from app.entity.db_models import DetectionScene, TrainingMetric, TrainingTask, User
from app.training.training_service import TrainingService


def _task(db_session, task_uuid="live1234", epochs=10):
    user = User(username="monitor", email="monitor@example.com", hashed_password="x")
    scene = DetectionScene(
        name="monitor_scene", display_name="Monitor", category="industry",
        class_names=["crazing"], class_names_cn={"crazing": "裂纹"},
    )
    db_session.add_all([user, scene])
    db_session.flush()
    task = TrainingTask(
        user_id=user.id, scene_id=scene.id, task_uuid=task_uuid,
        status="running", epochs=epochs, current_epoch=0, progress=0,
    )
    db_session.add(task)
    db_session.commit()
    return task


def test_status_syncs_completed_epochs_from_results_csv(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "TRAIN_OUTPUT_DIR", str(tmp_path))
    task = _task(db_session)
    output = tmp_path / f"task_{task.task_uuid}"
    output.mkdir()
    (output / "results.csv").write_text(
        "epoch,train/box_loss,metrics/mAP50(B)\n0,0.8,0.2\n1,0.6,0.4\n",
        encoding="utf-8",
    )

    status = TrainingService.get_training_status(db_session, task.id)

    assert status["task"]["current_epoch"] == 2
    assert status["task"]["progress"] == 20
    assert status["latest_metric"]["epoch"] == 2
    assert status["latest_metric"]["map50"] == 0.4


def test_csv_sync_updates_callback_placeholder_without_duplicate(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "TRAIN_OUTPUT_DIR", str(tmp_path))
    task = _task(db_session, task_uuid="repair12")
    db_session.add(TrainingMetric(task_id=task.id, epoch=1, map50=0.0))
    db_session.commit()
    output = tmp_path / f"task_{task.task_uuid}"
    output.mkdir()
    (output / "results.csv").write_text(
        "epoch,metrics/mAP50(B)\n0,0.55\n", encoding="utf-8"
    )

    metrics = TrainingService.get_training_metrics(db_session, task.id)

    assert len(metrics) == 1
    assert metrics[0]["epoch"] == 1
    assert metrics[0]["map50"] == 0.55


def test_csv_sync_does_not_report_stale_database_epoch(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "TRAIN_OUTPUT_DIR", str(tmp_path))
    task = _task(db_session, task_uuid="stale123", epochs=10)
    db_session.add(TrainingMetric(task_id=task.id, epoch=10, map50=0.9))
    db_session.commit()
    output = tmp_path / f"task_{task.task_uuid}"
    output.mkdir()
    (output / "results.csv").write_text(
        "epoch,metrics/mAP50(B)\n0,0.2\n1,0.4\n", encoding="utf-8"
    )

    status = TrainingService.get_training_status(db_session, task.id)

    assert status["task"]["current_epoch"] == 2
    assert status["task"]["progress"] == 20
    assert status["latest_metric"]["epoch"] == 2


def test_one_based_ultralytics_csv_does_not_create_epoch_n_plus_one(tmp_path):
    csv_path = tmp_path / "results.csv"
    csv_path.write_text("epoch,metrics/mAP50(B)\n1,0.2\n2,0.4\n", encoding="utf-8")

    metrics = TrainingService.parse_results_csv(str(csv_path))

    assert [metric["epoch"] for metric in metrics] == [1, 2]
