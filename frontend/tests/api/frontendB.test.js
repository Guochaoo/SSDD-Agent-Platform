import { describe, expect, it } from "vitest";
import { normalizeDetectionResponse } from "@/api/detection";
import { normalizeDashboardResponse } from "@/api/statistics";
import { normalizeMetric, normalizeTask } from "@/api/training";

describe("前端 B 检测数据适配", () => {
  it("兼容任务 + 明细表响应字段", () => {
    const result = normalizeDetectionResponse({
      task: {
        id: 18,
        status: "completed",
        total_images: 1,
        total_objects: 1,
        total_inference_time: 86,
      },
      image_width: 1000,
      image_height: 500,
      annotated_image_url: "/result/demo.jpg",
      results: [
        {
          id: 7,
          class_id: 5,
          class_name: "scratches",
          class_name_cn: "划痕",
          confidence: 0.91,
          bbox: [100, 50, 400, 150],
        },
      ],
    });

    expect(result.taskId).toBe("18");
    expect(result.annotatedImageUrl).toBe("/result/demo.jpg");
    expect(result.totalObjects).toBe(1);
    expect(result.objects[0].classNameCn).toBe("划痕");
    expect(result.objects[0].bboxPercent).toEqual([10, 10, 30, 20]);
  });

  it("兼容概要设计中的 record_id + objects 响应", () => {
    const result = normalizeDetectionResponse({
      success: true,
      data: {
        record_id: "uuid-1",
        result_image_url: "/result/uuid-1.jpg",
        detection_time: 0.12,
        summary: { total: 1 },
        objects: [
          {
            class_name: "pitted_surface",
            class_name_cn: "麻点",
            confidence: 0.8,
            x1: 10,
            y1: 20,
            x2: 30,
            y2: 40,
          },
        ],
      },
    });

    expect(result.taskId).toBe("uuid-1");
    expect(result.inferenceTimeMs).toBe(120);
    expect(result.objects[0].bbox).toEqual([10, 20, 30, 40]);
  });
});

describe("前端 B 训练与看板适配", () => {
  it("统一训练任务和指标字段", () => {
    expect(
      normalizeTask({
        task_uuid: "task-1",
        task_name: "基线训练",
        model_name: "YOLO11n",
        dataset_name: "NEU",
        current_epoch: 10,
        total_epochs: 100,
      }),
    ).toMatchObject({
      taskId: "task-1",
      taskName: "基线训练",
      currentEpoch: 10,
      totalEpochs: 100,
    });

    expect(normalizeMetric({ epoch: 3, box_loss: 0.4, map50_95: 0.52 })).toMatchObject({
      epoch: 3,
      boxLoss: 0.4,
      map50_95: 0.52,
    });
  });

  it("将统计字典转换为图表数组", () => {
    const result = normalizeDashboardResponse({
      total_tasks: 10,
      total_images: 20,
      total_objects: 30,
      avg_inference_time: 88,
      class_distribution: { 划痕: 18, 麻点: 12 },
      daily_trend: [{ date: "07-13", images: 20, objects: 30 }],
    });

    expect(result.totals.totalImages).toBe(20);
    expect(result.classDistribution).toEqual([
      { name: "划痕", value: 18 },
      { name: "麻点", value: 12 },
    ]);
  });
});
