import { describe, expect, it } from "vitest";
import {
  normalizeHistoryDetail,
  normalizeHistoryPage,
} from "@/api/history";

describe("前端 B 历史记录适配", () => {
  it("统一分页任务字段并计算单图平均耗时", () => {
    const page = normalizeHistoryPage({
      total: 1,
      page: 1,
      page_size: 20,
      items: [
        {
          id: 7,
          scene_id: 1,
          scene_name: "钢铁表面缺陷",
          task_type: "batch",
          status: "completed",
          total_images: 4,
          total_objects: 9,
          total_inference_time: 120,
        },
      ],
    });

    expect(page.total).toBe(1);
    expect(page.items[0]).toMatchObject({
      id: 7,
      sceneName: "钢铁表面缺陷",
      taskType: "batch",
      avgInferenceTimeMs: 30,
    });
  });

  it("统一详情中的检测结果字段", () => {
    const detail = normalizeHistoryDetail({
      task: { id: 9, status: "completed" },
      results: [
        {
          id: 2,
          image_path: "demo.jpg",
          annotated_image_url: "/result/demo.jpg",
          class_name: "scratches",
          class_name_cn: "划痕",
          confidence: 0.92,
          bbox: [1, 2, 30, 40],
          inference_time: 18,
        },
      ],
    });

    expect(detail.results[0]).toMatchObject({
      imagePath: "demo.jpg",
      classNameCn: "划痕",
      confidence: 0.92,
      inferenceTimeMs: 18,
    });
  });
});
