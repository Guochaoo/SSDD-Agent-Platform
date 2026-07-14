<template>
  <div class="frontend-b-page">
    <ModulePageHeader
      title="数据看板"
      description="从检测任务、缺陷明细和模型指标中聚合关键数据，观察缺陷类别、每日趋势和模型表现。"
      :mock="isFrontendBMockMode"
    >
      <span class="updated-at">更新于 {{ dashboard.updatedAt || "—" }}</span>
      <el-button :icon="Refresh" :loading="loading" @click="loadDashboard">刷新</el-button>
    </ModulePageHeader>

    <section class="filter-bar">
      <div class="filter-bar__title"><el-icon><Filter /></el-icon><span>统计筛选</span></div>
      <el-date-picker v-model="filters.dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" />
      <el-select v-model="filters.sceneId" placeholder="检测场景" clearable><el-option label="钢铁表面缺陷" :value="1" /></el-select>
      <el-select v-model="filters.modelId" placeholder="模型版本" clearable><el-option v-for="model in models" :key="model.id" :label="`${model.modelType} ${model.version}`" :value="model.id" /></el-select>
      <el-button type="primary" @click="loadDashboard">应用筛选</el-button>
    </section>

    <div class="stats-grid">
      <StatCard label="检测任务" :value="dashboard.totals.totalTasks" unit="次" :icon="DocumentChecked" helper="单图 / 批量 / 视频任务" />
      <StatCard label="检测图片" :value="dashboard.totals.totalImages" unit="张" :icon="Picture" accent="#7c3aed" helper="当前筛选范围" />
      <StatCard label="缺陷目标" :value="dashboard.totals.totalObjects" unit="处" :icon="WarningFilled" accent="#f97316" helper="六类钢铁表面缺陷" />
      <StatCard label="平均推理耗时" :value="dashboard.totals.avgInferenceTimeMs" unit="ms" :decimals="1" :icon="Odometer" accent="#10b981" helper="单张图片平均值" />
    </div>

    <div class="dashboard-grid dashboard-grid--primary">
      <EChartPanel title="每日检测趋势" subtitle="图片数与缺陷目标数" :option="trendOption" :loading="loading" :empty="dashboard.dailyTrend.length === 0" height="330px" />
      <EChartPanel title="缺陷类别分布" subtitle="当前筛选范围内的目标数量" :option="classOption" :loading="loading" :empty="dashboard.classDistribution.length === 0" height="330px" />
    </div>
    <div class="dashboard-grid">
      <EChartPanel title="置信度分布" subtitle="按检测置信度区间统计" :option="confidenceOption" :loading="loading" :empty="dashboard.confidenceDistribution.length === 0" />
      <EChartPanel title="模型指标对比" subtitle="mAP50 / Precision / Recall" :option="modelOption" :loading="loading" :empty="dashboard.modelMetrics.length === 0" />
    </div>
  </div>
</template>

<script setup>
import { DocumentChecked, Filter, Odometer, Picture, Refresh, WarningFilled } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";
import { getModelsApi, isFrontendBMockMode } from "@/api/models";
import { getDashboardApi } from "@/api/statistics";
import EChartPanel from "@/components/charts/EChartPanel.vue";
import StatCard from "@/components/charts/StatCard.vue";
import ModulePageHeader from "@/components/common/ModulePageHeader.vue";

const loading = ref(false);
const models = ref([]);
const filters = reactive({ dateRange: [], sceneId: 1, modelId: "" });
const dashboard = reactive({ totals: { totalTasks: 0, totalImages: 0, totalObjects: 0, avgInferenceTimeMs: 0 }, classDistribution: [], dailyTrend: [], confidenceDistribution: [], modelMetrics: [], updatedAt: "" });
const axisStyle = { axisLine: { lineStyle: { color: "#d0d5dd" } }, axisLabel: { color: "#667085" } };

const trendOption = computed(() => ({ tooltip: { trigger: "axis" }, color: ["#2563eb", "#f97316"], legend: { data: ["检测图片", "缺陷目标"], top: 4 }, grid: { left: 52, right: 18, top: 46, bottom: 34 }, xAxis: { type: "category", data: dashboard.dailyTrend.map((item) => item.date), ...axisStyle }, yAxis: { type: "value", splitLine: { lineStyle: { color: "#edf0f5" } }, ...axisStyle }, series: [{ name: "检测图片", type: "line", smooth: true, symbolSize: 7, areaStyle: { color: "rgba(37,99,235,.08)" }, data: dashboard.dailyTrend.map((item) => item.images) }, { name: "缺陷目标", type: "line", smooth: true, symbolSize: 7, data: dashboard.dailyTrend.map((item) => item.objects) }] }));
const classOption = computed(() => ({ tooltip: { trigger: "item", formatter: "{b}<br/>{c} 处 · {d}%" }, color: ["#2563eb", "#7c3aed", "#06b6d4", "#10b981", "#f59e0b", "#f97316"], legend: { type: "scroll", orient: "vertical", right: 4, top: "middle" }, series: [{ type: "pie", radius: ["43%", "70%"], center: ["38%", "53%"], avoidLabelOverlap: true, itemStyle: { borderColor: "#fff", borderWidth: 3 }, label: { show: false }, emphasis: { label: { show: true, fontSize: 15, fontWeight: "bold" } }, data: dashboard.classDistribution }] }));
const confidenceOption = computed(() => ({ tooltip: { trigger: "axis" }, color: ["#10b981"], grid: { left: 52, right: 18, top: 28, bottom: 42 }, xAxis: { type: "category", data: dashboard.confidenceDistribution.map((item) => item.range), ...axisStyle }, yAxis: { type: "value", splitLine: { lineStyle: { color: "#edf0f5" } }, ...axisStyle }, series: [{ type: "bar", barMaxWidth: 42, data: dashboard.confidenceDistribution.map((item) => item.count), itemStyle: { borderRadius: [7, 7, 0, 0] } }] }));
const modelOption = computed(() => ({ tooltip: { trigger: "axis" }, color: ["#2563eb", "#10b981", "#f59e0b"], legend: { data: ["mAP50", "Precision", "Recall"], top: 0 }, grid: { left: 48, right: 18, top: 42, bottom: 42 }, xAxis: { type: "category", data: dashboard.modelMetrics.map((item) => item.name), axisLabel: { color: "#667085", interval: 0 }, axisLine: axisStyle.axisLine }, yAxis: { type: "value", min: 0, max: 1, splitLine: { lineStyle: { color: "#edf0f5" } }, ...axisStyle }, series: ["map50", "precision", "recall"].map((key, index) => ({ name: ["mAP50", "Precision", "Recall"][index], type: "bar", barMaxWidth: 30, data: dashboard.modelMetrics.map((item) => item[key]) })) }));

async function loadDashboard() {
  loading.value = true;
  try {
    const sceneId = Number(filters.sceneId) || 1;
    const [data, modelList] = await Promise.all([getDashboardApi({ start_date: filters.dateRange?.[0], end_date: filters.dateRange?.[1], scene_id: sceneId, model_id: filters.modelId }), getModelsApi(sceneId)]);
    Object.assign(dashboard, data);
    models.value = modelList;
  } catch { ElMessage.error("看板数据加载失败"); }
  finally { loading.value = false; }
}

onMounted(loadDashboard);
</script>

<style lang="scss" scoped>
.frontend-b-page { min-height: 100%; }
.updated-at { color: $text-secondary; font-size: 12px; }
.filter-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 18px; padding: 14px 16px; border: 1px solid #e7ebf1; border-radius: 12px; background: #fff; }
.filter-bar__title { display: flex; align-items: center; gap: 7px; margin-right: auto; color: #344054; font-weight: 600; }
.filter-bar :deep(.el-select) { width: 170px; }
.stats-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 18px; }
.dashboard-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; margin-bottom: 18px; }
.dashboard-grid--primary { grid-template-columns: 1.35fr .85fr; }
@media (max-width: 1180px) { .stats-grid { grid-template-columns: repeat(2, 1fr); } .dashboard-grid, .dashboard-grid--primary { grid-template-columns: 1fr; } .filter-bar { flex-wrap: wrap; } .filter-bar__title { width: 100%; } }
@media (max-width: 640px) { .stats-grid { grid-template-columns: 1fr; } .filter-bar :deep(.el-date-editor), .filter-bar :deep(.el-select) { width: 100%; } }
</style>
