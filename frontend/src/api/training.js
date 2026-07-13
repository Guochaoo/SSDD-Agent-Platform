import request from "@/utils/request";
import { isFrontendBMockMode } from "./models";
import {
  mockGetTrainingDetail,
  mockGetTrainingTasks,
  mockStartTraining,
} from "./mockData";

function unwrap(payload) {
  return payload?.data ?? payload;
}

function normalizeTask(task) {
  const rawTaskId = task.id ?? task.task_id ?? task.taskId ?? task.task_uuid;
  return {
    // Backend status and metrics routes use the numeric database id. Keep the
    // UUID separately for display and future external integrations.
    taskId: Number.isFinite(Number(rawTaskId))
      ? Number(rawTaskId)
      : String(rawTaskId ?? ""),
    taskUuid: task.task_uuid ?? task.taskUuid ?? "",
    taskName: task.task_name ?? task.taskName ?? "未命名训练任务",
    status: task.status ?? "pending",
    modelName: task.model_name ?? task.modelName ?? "YOLO11n",
    datasetName: task.dataset_name ?? task.datasetName ?? "未指定数据集",
    currentEpoch: task.current_epoch ?? task.currentEpoch ?? 0,
    totalEpochs: task.total_epochs ?? task.epochs ?? task.totalEpochs ?? 0,
    progress: Number(task.progress ?? 0),
    map50: task.map50,
    precision: task.precision,
    recall: task.recall,
    errorMessage: task.error_message ?? task.errorMessage ?? "",
    createdAt: task.created_at ?? task.createdAt,
    startedAt: task.started_at ?? task.startedAt,
    completedAt: task.completed_at ?? task.completedAt,
  };
}

function normalizeMetric(metric) {
  return {
    epoch: Number(metric.epoch),
    boxLoss: metric.box_loss ?? metric.boxLoss ?? null,
    clsLoss: metric.cls_loss ?? metric.clsLoss ?? null,
    dflLoss: metric.dfl_loss ?? metric.dflLoss ?? null,
    precision: metric.precision ?? null,
    recall: metric.recall ?? null,
    map50: metric.map50 ?? null,
    map50_95: metric.map50_95 ?? null,
    lr: metric.lr ?? null,
  };
}

export async function getTrainingTasksApi() {
  if (isFrontendBMockMode) return mockGetTrainingTasks();
  const response = unwrap(await request.get("/training/tasks"));
  return (response?.items ?? response ?? []).map(normalizeTask);
}

export async function getTrainingDetailApi(taskId) {
  if (isFrontendBMockMode) return mockGetTrainingDetail(taskId);
  const [status, metrics] = await Promise.all([
    request.get(`/training/status/${taskId}`),
    request.get(`/training/metrics/${taskId}`),
  ]);
  const statusData = unwrap(status) ?? {};
  const task = normalizeTask(statusData.task ?? statusData);
  const metricData = unwrap(metrics);
  return {
    ...task,
    metrics: (metricData?.metrics ?? metricData?.items ?? metricData ?? []).map(normalizeMetric),
  };
}

export async function startTrainingApi(payload) {
  if (isFrontendBMockMode) return mockStartTraining(payload);
  const requestPayload = {
    scene_id: Number(payload.sceneId),
    model_name: payload.modelName,
    epochs: payload.epochs,
    img_size: payload.imgSize,
    batch_size: payload.batchSize,
    device: payload.device ?? "0",
    optimizer: payload.optimizer ?? "SGD",
    lr0: payload.lr0 ?? 0.01,
    augment_config: payload.augmentConfig ?? null,
  };
  return normalizeTask(
    unwrap(await request.post("/training/start", requestPayload)),
  );
}

export { normalizeMetric, normalizeTask };
