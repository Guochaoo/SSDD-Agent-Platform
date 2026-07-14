import request from "@/utils/request";
import { isFrontendBMockMode } from "./models";
import { mockDetectBatch, mockDetectSingle } from "./mockData";

function unwrap(payload) {
  return payload?.data ?? payload;
}

function normalizeObject(item, index, imageWidth, imageHeight) {
  const bbox = item.bbox ?? [item.x1, item.y1, item.x2, item.y2];
  const [x1 = 0, y1 = 0, x2 = 0, y2 = 0] = bbox;
  return {
    id: String(item.id ?? index),
    classId: item.class_id ?? item.classId ?? 0,
    className: item.class_name ?? item.className ?? "unknown",
    classNameCn:
      item.class_name_cn ?? item.classNameCn ?? item.class_name ?? "未知缺陷",
    confidence: Number(item.confidence ?? 0),
    bbox: [x1, y1, x2, y2].map(Number),
    bboxPercent: imageWidth && imageHeight
      ? [
          (x1 / imageWidth) * 100,
          (y1 / imageHeight) * 100,
          ((x2 - x1) / imageWidth) * 100,
          ((y2 - y1) / imageHeight) * 100,
        ]
      : null,
    areaRatio: item.area_ratio ?? item.areaRatio ?? null,
  };
}

export function normalizeDetectionResponse(payload) {
  const data = unwrap(payload) ?? {};
  const task = data.task ?? data;
  const imageWidth = data.image_width ?? data.imageWidth;
  const imageHeight = data.image_height ?? data.imageHeight;
  const rawObjects = data.objects ?? data.results ?? data.defect_results ?? [];
  const objects = rawObjects.map((item, index) =>
    normalizeObject(item, index, imageWidth, imageHeight),
  );
  return {
    taskId: String(task.id ?? data.record_id ?? data.task_id ?? data.taskId ?? ""),
    status: task.status ?? data.status ?? "completed",
    fileName: data.filename ?? data.fileName ?? "",
    originalImageUrl: data.image_url ?? data.originalImageUrl ?? "",
    annotatedImageUrl:
      data.annotated_image_url ?? data.result_image_url ?? data.annotatedImageUrl ?? "",
    totalImages: task.total_images ?? data.totalImages ?? 1,
    totalObjects:
      task.total_objects ?? data.totalObjects ?? data.summary?.total ?? objects.length,
    inferenceTimeMs:
      task.total_inference_time ?? data.inference_time_ms ?? data.inferenceTimeMs ??
      (data.detection_time != null ? data.detection_time * 1000 : 0),
    imageWidth,
    imageHeight,
    objects,
  };
}

export async function detectSingleApi(file, options) {
  if (isFrontendBMockMode) {
    return normalizeDetectionResponse(await mockDetectSingle(file, options));
  }
  const formData = new FormData();
  formData.append("file", file);
  formData.append("model_id", options.modelId);
  formData.append("conf_threshold", String(options.confThreshold));
  formData.append("iou_threshold", String(options.iouThreshold));
  const response = await request.post("/detection/single", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 120000,
  });
  return normalizeDetectionResponse(response);
}

export async function detectBatchApi(files, options) {
  if (isFrontendBMockMode) return mockDetectBatch(files, options);
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  formData.append("model_id", options.modelId);
  formData.append("conf_threshold", String(options.confThreshold));
  formData.append("iou_threshold", String(options.iouThreshold));
  const data = unwrap(
    await request.post("/detection/batch", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 300000,
    }),
  );
  return {
    taskId: String(data.task_id ?? data.taskId ?? ""),
    status: data.status ?? "completed",
    successCount: data.success_count ?? data.successCount ?? 0,
    failedCount: data.failed_count ?? data.failedCount ?? 0,
    items: (data.items ?? []).map((item) => ({
      ...normalizeDetectionResponse(item),
      status: item.status,
      fileName: item.file_name ?? item.fileName ?? "",
      error: item.error ?? null,
    })),
  };
}
