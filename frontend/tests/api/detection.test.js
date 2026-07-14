import { describe, expect, it } from "vitest";
import { normalizeDetectionResponse } from "@/api/detection";

describe("detection api", () => {
  it("normalizes the local YOLO snake_case response", () => {
    const result = normalizeDetectionResponse({
      task_id: 42,
      status: "completed",
      filename: "steel.webp",
      image_width: 640,
      image_height: 480,
      total_objects: 1,
      inference_time_ms: 37.5,
      objects: [
        {
          class_id: 3,
          class_name: "pitted",
          class_name_cn: "pitted defect",
          confidence: 0.88,
          bbox: [16, 24, 116, 124],
        },
      ],
    });

    expect(result.taskId).toBe("42");
    expect(result.inferenceTimeMs).toBe(37.5);
    expect(result.fileName).toBe("steel.webp");
    expect(result.objects[0].className).toBe("pitted");
  });
});
