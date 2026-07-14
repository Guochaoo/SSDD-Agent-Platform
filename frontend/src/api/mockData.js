const wait = (ms = 360) => new Promise((resolve) => setTimeout(resolve, ms));

export const steelClasses = [
  { id: 0, name: "crazing", nameCn: "龟裂" },
  { id: 1, name: "inclusion", nameCn: "夹杂" },
  { id: 2, name: "patches", nameCn: "斑块" },
  { id: 3, name: "pitted_surface", nameCn: "麻点" },
  { id: 4, name: "rolled-in_scale", nameCn: "氧化皮压入" },
  { id: 5, name: "scratches", nameCn: "划痕" },
];

export const mockScenes = [
  {
    id: "steel",
    name: "steel",
    displayName: "钢铁表面缺陷",
    classNames: steelClasses.map((item) => item.name),
  },
];

export const mockModels = [
  {
    id: "steel-yolo11n-v1",
    version: "v1.0.0",
    modelName: "steel-defect-yolo11n",
    modelType: "YOLO11n",
    map50: 0.873,
    precision: 0.846,
    recall: 0.812,
    isDefault: true,
    status: "active",
  },
  {
    id: "steel-yolo11s-v2",
    version: "v1.1.0",
    modelName: "steel-defect-yolo11s",
    modelType: "YOLO11s",
    map50: 0.901,
    precision: 0.878,
    recall: 0.841,
    isDefault: false,
    status: "active",
  },
];

function makeObjects(seed = 0) {
  const variants = [
    [
      { classId: 5, confidence: 0.932, bbox: [132, 98, 612, 224] },
      { classId: 3, confidence: 0.861, bbox: [728, 288, 1028, 562] },
      { classId: 1, confidence: 0.784, bbox: [362, 438, 558, 654] },
    ],
    [
      { classId: 0, confidence: 0.905, bbox: [176, 166, 694, 398] },
      { classId: 4, confidence: 0.822, bbox: [756, 374, 1086, 642] },
    ],
    [{ classId: 2, confidence: 0.889, bbox: [284, 218, 894, 516] }],
  ];

  return variants[seed % variants.length].map((item, index) => {
    const classInfo = steelClasses.find((entry) => entry.id === item.classId);
    return {
      id: `${seed}-${index}`,
      ...item,
      className: classInfo.name,
      classNameCn: classInfo.nameCn,
      areaRatio:
        ((item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1])) /
        (1200 * 720),
    };
  });
}

export async function mockDetectSingle(file, options = {}) {
  await wait(720);
  const objects = makeObjects(file?.name?.length || 0);
  return {
    taskId: `mock-detect-${Date.now()}`,
    status: "completed",
    fileName: file?.name || "steel-sample.jpg",
    modelId: options.modelId,
    totalImages: 1,
    totalObjects: objects.length,
    inferenceTimeMs: 86,
    imageWidth: 1200,
    imageHeight: 720,
    objects,
  };
}

export async function mockDetectBatch(files, options = {}) {
  await wait(880);
  const items = files.map((file, index) => {
    const objects = makeObjects(index);
    return {
      id: `mock-batch-${Date.now()}-${index}`,
      fileName: file.name,
      status: "completed",
      totalObjects: objects.length,
      inferenceTimeMs: 72 + index * 11,
      modelId: options.modelId,
      objects,
    };
  });
  return {
    taskId: `mock-batch-${Date.now()}`,
    status: "completed",
    successCount: items.length,
    failedCount: 0,
    items,
  };
}

let taskSequence = 4;
const taskStore = [
  {
    taskId: "train-steel-003",
    taskName: "钢铁缺陷 YOLO11s 调优",
    status: "running",
    modelName: "YOLO11s",
    datasetName: "NEU 钢铁缺陷数据集",
    currentEpoch: 48,
    totalEpochs: 100,
    progress: 48,
    createdAt: "2026-07-13 09:20",
    startedAt: "2026-07-13 09:23",
  },
  {
    taskId: "train-steel-002",
    taskName: "YOLO11n 六类缺陷基线",
    status: "completed",
    modelName: "YOLO11n",
    datasetName: "NEU 钢铁缺陷数据集",
    currentEpoch: 80,
    totalEpochs: 80,
    progress: 100,
    map50: 0.873,
    precision: 0.846,
    recall: 0.812,
    createdAt: "2026-07-12 14:10",
    startedAt: "2026-07-12 14:12",
    completedAt: "2026-07-12 16:46",
  },
  {
    taskId: "train-steel-001",
    taskName: "数据格式验证训练",
    status: "failed",
    modelName: "YOLO11n",
    datasetName: "NEU 钢铁缺陷数据集",
    currentEpoch: 6,
    totalEpochs: 30,
    progress: 20,
    errorMessage: "验证集标签路径不可用（演示状态）",
    createdAt: "2026-07-11 10:08",
    startedAt: "2026-07-11 10:10",
  },
];

function metricSeries(totalEpochs = 80, currentEpoch = totalEpochs) {
  const sampleStep = currentEpoch > 40 ? 4 : 2;
  const points = [];
  for (let epoch = 1; epoch <= currentEpoch; epoch += sampleStep) {
    const progress = epoch / totalEpochs;
    points.push({
      epoch,
      boxLoss: Number((1.82 * Math.exp(-2.4 * progress) + 0.16).toFixed(4)),
      clsLoss: Number((1.47 * Math.exp(-2.1 * progress) + 0.12).toFixed(4)),
      dflLoss: Number((1.12 * Math.exp(-1.7 * progress) + 0.2).toFixed(4)),
      precision: Number((0.52 + 0.36 * progress).toFixed(4)),
      recall: Number((0.47 + 0.37 * progress).toFixed(4)),
      map50: Number((0.38 + 0.52 * progress).toFixed(4)),
      map50_95: Number((0.2 + 0.43 * progress).toFixed(4)),
      lr: Number((0.01 * (1 - progress * 0.92)).toFixed(6)),
    });
  }
  return points;
}

export async function mockGetTrainingTasks() {
  await wait();
  return taskStore.map((task) => ({ ...task }));
}

export async function mockGetTrainingDetail(taskId) {
  await wait(260);
  const task = taskStore.find((item) => item.taskId === taskId) || taskStore[0];
  if (task.status === "running" && task.currentEpoch < task.totalEpochs) {
    task.currentEpoch = Math.min(task.currentEpoch + 1, task.totalEpochs);
    task.progress = Math.round((task.currentEpoch / task.totalEpochs) * 100);
  }
  return {
    ...task,
    metrics: metricSeries(task.totalEpochs, task.currentEpoch),
  };
}

export async function mockStartTraining(payload) {
  await wait(520);
  const task = {
    taskId: `train-steel-${String(taskSequence++).padStart(3, "0")}`,
    taskName: payload.taskName || "新建钢铁缺陷训练",
    status: "running",
    modelName: payload.modelName || "YOLO11n",
    datasetName: payload.datasetName || "NEU 钢铁缺陷数据集",
    currentEpoch: 1,
    totalEpochs: payload.epochs || 100,
    progress: 1,
    createdAt: new Date().toLocaleString("zh-CN", { hour12: false }),
    startedAt: new Date().toLocaleString("zh-CN", { hour12: false }),
  };
  taskStore.unshift(task);
  return { ...task };
}

export async function mockGetDashboard() {
  await wait(460);
  return {
    totals: {
      totalTasks: 1286,
      totalImages: 3480,
      totalObjects: 7926,
      avgInferenceTimeMs: 94.6,
    },
    classDistribution: [
      { name: "划痕", value: 2184 },
      { name: "麻点", value: 1672 },
      { name: "夹杂", value: 1294 },
      { name: "龟裂", value: 1098 },
      { name: "氧化皮压入", value: 936 },
      { name: "斑块", value: 742 },
    ],
    dailyTrend: [
      { date: "07-07", images: 286, objects: 612 },
      { date: "07-08", images: 342, objects: 768 },
      { date: "07-09", images: 418, objects: 958 },
      { date: "07-10", images: 396, objects: 884 },
      { date: "07-11", images: 472, objects: 1062 },
      { date: "07-12", images: 508, objects: 1198 },
      { date: "07-13", images: 436, objects: 1034 },
    ],
    confidenceDistribution: [
      { range: "0.25–0.50", count: 832 },
      { range: "0.50–0.70", count: 1964 },
      { range: "0.70–0.85", count: 3026 },
      { range: "0.85–1.00", count: 2104 },
    ],
    modelMetrics: mockModels.map((model) => ({
      name: `${model.modelType} ${model.version}`,
      map50: model.map50,
      precision: model.precision,
      recall: model.recall,
    })),
    updatedAt: new Date().toLocaleString("zh-CN", { hour12: false }),
  };
}
