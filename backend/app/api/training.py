"""
训练任务与模型版本 API 路由
- POST /api/training/tasks                  创建训练任务
- GET  /api/training/tasks                   我的训练任务列表
- GET  /api/training/tasks/{task_id}/metrics 训练指标曲线
- GET  /api/training/models/{scene_id}       某场景下的模型版本列表
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import get_db
from app.entity.db_models import TrainingTask, User
from app.entity.schemas import TrainingTaskCreate, TrainingTaskResponse, TrainingMetricResponse, ModelVersionResponse
from app.services.training_service import training_service

router = APIRouter(prefix="/api/training", tags=["模型训练"])


def _task_to_response(task) -> TrainingTaskResponse:
    data = TrainingTaskResponse.model_validate(task)
    data.scene_name = task.scene.display_name if task.scene else None
    return data


@router.post("/tasks", response_model=TrainingTaskResponse, status_code=201)
def create_training_task(
    payload: TrainingTaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建训练任务，初始状态为 pending，实际训练由后端 B 的训练进程接手"""
    task = training_service.create_task(
        db,
        user_id=current_user.id,
        scene_id=payload.scene_id,
        model_name=payload.model_name,
        epochs=payload.epochs,
        img_size=payload.img_size,
        batch_size=payload.batch_size,
        device=payload.device,
        optimizer=payload.optimizer,
        lr0=payload.lr0,
        augment_config=payload.augment_config,
    )
    return _task_to_response(task)


@router.get("/tasks", response_model=list[TrainingTaskResponse])
def list_training_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """我的训练任务列表；管理员可看到所有人的"""
    tasks = training_service.list_tasks_by_user(db, current_user.id, current_user.is_superuser)
    return [_task_to_response(t) for t in tasks]


@router.get("/tasks/{task_id}/metrics", response_model=list[TrainingMetricResponse])
def get_training_metrics(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """按 epoch 顺序返回训练指标，供前端绘制 loss/mAP 曲线"""
    task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="训练任务不存在")
    if task.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="无权访问该训练任务")
    return training_service.list_metrics(db, task_id)


@router.get("/models/{scene_id}", response_model=list[ModelVersionResponse])
def list_model_versions(
    scene_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """某场景下的全部可用模型版本"""
    models = training_service.list_model_versions(db, scene_id)
    result = []
    for m in models:
        data = ModelVersionResponse.model_validate(m)
        data.scene_name = m.scene.display_name if m.scene else None
        result.append(data)
    return result
