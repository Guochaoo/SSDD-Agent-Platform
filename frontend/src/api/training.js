import request from "@/utils/request";

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
    sceneName: task.scene_name ?? task.sceneName ?? "",
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
  const response = unwrap(await request.get("/training/tasks"));
  return (response?.items ?? response ?? []).map(normalizeTask);
}

export async function getTrainingDetailApi(taskId) {
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
  const requestPayload = {
    scene_id: Number(payload.sceneId),
    model_name: payload.modelName,
    epochs: payload.epochs,
    img_size: payload.imgSize,
    batch_size: payload.batchSize,
    device: payload.device ?? "cpu",
    optimizer: payload.optimizer ?? "SGD",
    lr0: payload.lr0 ?? 0.01,
    augment_config: payload.augmentConfig ?? null,
    train_config: payload.trainConfig ?? null,
    dataset_path: payload.datasetPath ?? null,
  };
  return normalizeTask(
    unwrap(await request.post("/training/start", requestPayload)),
  );
}

export { normalizeMetric, normalizeTask };
 
// Raw endpoint adapters used by the richer training workbench. The normalized
// adapters above remain available to the existing dev dashboard.

export function getTrainingTasks() {
  return request.get('/training/tasks')
}

export function startTraining(payload) {
  return request.post('/training/start', payload)
}

export function getTrainingDatasets() {
  return request.get('/training/datasets')
}

export function downloadTrainingDataset(datasetPath) {
  return request.get(`/training/datasets/${encodeURIComponent(datasetPath)}/download`, { responseType: 'blob', timeout: 120000 })
}

export function deleteTrainingDataset(datasetPath) {
  return request.delete(`/training/datasets/${encodeURIComponent(datasetPath)}`)
}

export function updateTrainingDatasetMetadata(datasetPath, payload) {
  return request.patch(`/training/datasets/${encodeURIComponent(datasetPath)}`, payload)
}

export function uploadTrainingDataset(file, options = {}) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('dataset_format', options.dataset_format || 'auto')
  formData.append('train_ratio', options.train_ratio ?? 0.8)
  formData.append('val_ratio', options.val_ratio ?? 0.1)
  formData.append('test_ratio', options.test_ratio ?? 0.1)
  formData.append('split_seed', options.split_seed ?? 42)
  return request.post('/training/datasets/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function getTrainingStatus(taskId) {
  return request.get(`/training/status/${taskId}`)
}

export function getTrainingMetrics(taskId) {
  return request.get(`/training/metrics/${taskId}`)
}

export function stopTraining(taskId) {
  return request.post(`/training/stop/${taskId}`)
}

export function deleteTrainingTask(taskId) {
  return request.delete(`/training/tasks/${taskId}`)
}

export function downloadTrainingResults(taskUuid) {
  return request.get(`/training/results/${taskUuid}`, {
    responseType: 'blob',
  })
}

export function validateTrainingModel(taskId, payload) {
  return request.post(`/training/validate/${taskId}`, payload, {
    timeout: 300000,
  })
}

export function exportTrainingModel(taskId, payload) {
  return request.post(`/training/export/${taskId}`, payload)
}

export function downloadTrainingModel(taskId) {
  return request.get(`/training/download/${taskId}`, {
    responseType: 'blob',
    timeout: 120000,
  })
}

export function predictTrainingImage(payload) {
  return request.post('/training/predict', payload, {
    timeout: 300000,
  })
}
