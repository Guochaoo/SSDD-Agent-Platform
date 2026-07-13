import request from "@/utils/request";
import { isFrontendBMockMode } from "./models";
import { mockGetDashboard } from "./mockData";

function unwrap(payload) {
  return payload?.data ?? payload;
}

export function normalizeDashboardResponse(payload) {
  const data = unwrap(payload) ?? {};
  return {
    totals: {
      totalTasks: data.totals?.totalTasks ?? data.total_tasks ?? 0,
      totalImages: data.totals?.totalImages ?? data.total_images ?? 0,
      totalObjects: data.totals?.totalObjects ?? data.total_objects ?? 0,
      avgInferenceTimeMs:
        data.totals?.avgInferenceTimeMs ?? data.avg_inference_time ?? 0,
    },
    classDistribution:
      data.classDistribution ??
      Object.entries(data.class_distribution ?? {}).map(([name, value]) => ({
        name,
        value,
      })),
    dailyTrend: data.dailyTrend ?? data.daily_trend ?? [],
    confidenceDistribution:
      data.confidenceDistribution ?? data.confidence_distribution ?? [],
    modelMetrics: data.modelMetrics ?? data.model_metrics ?? [],
    updatedAt: data.updatedAt ?? data.updated_at ?? "",
  };
}

export async function getDashboardApi(params = {}) {
  if (isFrontendBMockMode) {
    return normalizeDashboardResponse(await mockGetDashboard(params));
  }
  return normalizeDashboardResponse(
    await request.get("/history/statistics/summary", {
      params: { days: params.days ?? 30 },
    }),
  );
}
