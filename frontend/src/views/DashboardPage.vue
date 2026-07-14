<template>
  <div class="frontend-b-page">
    <ModulePageHeader
      title="数据看板"
      description="使用当前账号真实检测历史聚合任务、图片、缺陷类别和检测场景数据。"
      :mock="isFrontendBMockMode"
    >
      <span class="updated-at">更新于 {{ dashboard.updatedAt || "—" }}</span>
      <el-button :icon="Refresh" :loading="loading" @click="loadDashboard">刷新</el-button>
    </ModulePageHeader>

    <el-alert
      v-if="pageError"
      class="page-alert"
      :title="pageError"
      type="error"
      show-icon
      :closable="false"
    >
      <template #default>
        <el-button link type="primary" @click="loadDashboard">重新加载</el-button>
      </template>
    </el-alert>

    <section class="filter-bar">
      <div class="filter-bar__title"><el-icon><Filter /></el-icon><span>统计周期</span></div>
      <el-select v-model="filters.days" aria-label="统计周期">
        <el-option label="最近 7 天" :value="7" />
        <el-option label="最近 30 天" :value="30" />
        <el-option label="最近 90 天" :value="90" />
        <el-option label="最近 365 天" :value="365" />
      </el-select>
      <el-button type="primary" @click="loadDashboard">应用</el-button>
      <span class="filter-hint">统计范围由后端 `/history/statistics/summary` 接口提供</span>
    </section>

    <div class="stats-grid">
      <StatCard label="检测任务" :value="dashboard.totals.totalTasks" unit="次" :icon="DocumentChecked" helper="已完成的检测任务" />
      <StatCard label="检测图片" :value="dashboard.totals.totalImages" unit="张" :icon="Picture" accent="#7c3aed" helper="历史任务累计处理图片" />
      <StatCard label="缺陷目标" :value="dashboard.totals.totalObjects" unit="处" :icon="WarningFilled" accent="#f97316" helper="历史结果累计缺陷目标" />
      <StatCard label="平均任务耗时" :value="dashboard.totals.avgInferenceTimeMs" unit="ms" :decimals="1" :icon="Odometer" accent="#10b981" helper="完成任务的平均总推理耗时" />
    </div>

    <div class="dashboard-grid dashboard-grid--primary">
      <EChartPanel title="每日检测任务趋势" subtitle="按创建日期统计检测任务数量" :option="trendOption" :loading="loading" :empty="dashboard.dailyTrend.length === 0" height="330px" />
      <EChartPanel title="缺陷类别分布" subtitle="当前账号历史结果中的目标数量" :option="classOption" :loading="loading" :empty="dashboard.classDistribution.length === 0" height="330px" />
    </div>
    <div class="dashboard-grid dashboard-grid--single">
      <EChartPanel title="检测场景分布" subtitle="已完成任务在各检测场景中的数量" :option="sceneOption" :loading="loading" :empty="dashboard.sceneDistribution.length === 0" height="300px" />
    </div>
  </div>
</template>

<script setup>
import { DocumentChecked, Filter, Odometer, Picture, Refresh, WarningFilled } from "@element-plus/icons-vue";
import { computed, onMounted, reactive, ref } from "vue";
import { isFrontendBMockMode } from "@/api/models";
import { getDashboardApi } from "@/api/statistics";
import EChartPanel from "@/components/charts/EChartPanel.vue";
import StatCard from "@/components/charts/StatCard.vue";
import ModulePageHeader from "@/components/common/ModulePageHeader.vue";
import { getApiErrorMessage } from "@/utils/apiError";

const loading = ref(false);
const pageError = ref("");
const filters = reactive({ days: 30 });
const dashboard = reactive({
  totals: { totalTasks: 0, totalImages: 0, totalObjects: 0, avgInferenceTimeMs: 0 },
  classDistribution: [],
  dailyTrend: [],
  sceneDistribution: [],
  updatedAt: "",
});
const axisStyle = { axisLine: { lineStyle: { color: "#d0d5dd" } }, axisLabel: { color: "#667085" } };

const trendOption = computed(() => ({
  tooltip: { trigger: "axis" },
  color: ["#2563eb"],
  grid: { left: 52, right: 18, top: 28, bottom: 34 },
  xAxis: { type: "category", data: dashboard.dailyTrend.map((item) => item.date), ...axisStyle },
  yAxis: { type: "value", minInterval: 1, splitLine: { lineStyle: { color: "#edf0f5" } }, ...axisStyle },
  series: [{ name: "检测任务", type: "line", smooth: true, symbolSize: 7, areaStyle: { color: "rgba(37,99,235,.08)" }, data: dashboard.dailyTrend.map((item) => item.tasks) }],
}));

const classOption = computed(() => ({
  tooltip: { trigger: "item", formatter: "{b}<br/>{c} 处 · {d}%" },
  color: ["#2563eb", "#7c3aed", "#06b6d4", "#10b981", "#f59e0b", "#f97316"],
  legend: { type: "scroll", orient: "vertical", right: 4, top: "middle" },
  series: [{ type: "pie", radius: ["43%", "70%"], center: ["38%", "53%"], avoidLabelOverlap: true, itemStyle: { borderColor: "#fff", borderWidth: 3 }, label: { show: false }, emphasis: { label: { show: true, fontSize: 15, fontWeight: "bold" } }, data: dashboard.classDistribution }],
}));

const sceneOption = computed(() => ({
  tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
  color: ["#7c3aed"],
  grid: { left: 120, right: 24, top: 20, bottom: 28 },
  xAxis: { type: "value", minInterval: 1, splitLine: { lineStyle: { color: "#edf0f5" } }, ...axisStyle },
  yAxis: { type: "category", data: dashboard.sceneDistribution.map((item) => item.name), ...axisStyle },
  series: [{ type: "bar", barMaxWidth: 34, data: dashboard.sceneDistribution.map((item) => item.value), itemStyle: { borderRadius: [0, 7, 7, 0] } }],
}));

async function loadDashboard() {
  loading.value = true;
  pageError.value = "";
  try {
    const data = await getDashboardApi({ days: filters.days });
    Object.assign(dashboard, data, { updatedAt: new Date().toLocaleString("zh-CN", { hour12: false }) });
  } catch (error) {
    pageError.value = getApiErrorMessage(error, "看板数据加载失败");
  } finally {
    loading.value = false;
  }
}

onMounted(loadDashboard);
</script>

<style lang="scss" scoped>
.frontend-b-page { min-height: 100%; }
.updated-at { color: $text-secondary; font-size: 12px; }
.page-alert { margin-bottom: 16px; }
.filter-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 18px; padding: 14px 16px; border: 1px solid #e7ebf1; border-radius: 12px; background: #fff; }
.filter-bar__title { display: flex; align-items: center; gap: 7px; color: #344054; font-weight: 600; }
.filter-bar :deep(.el-select) { width: 160px; }
.filter-hint { margin-left: auto; color: $text-secondary; font-size: 12px; }
.stats-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 18px; }
.dashboard-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; margin-bottom: 18px; }
.dashboard-grid--primary { grid-template-columns: 1.35fr .85fr; }
.dashboard-grid--single { grid-template-columns: 1fr; }
@media (max-width: 1180px) { .stats-grid { grid-template-columns: repeat(2, 1fr); } .dashboard-grid, .dashboard-grid--primary { grid-template-columns: 1fr; } .filter-bar { flex-wrap: wrap; } .filter-hint { width: 100%; margin-left: 0; } }
@media (max-width: 640px) { .stats-grid { grid-template-columns: 1fr; } .filter-bar :deep(.el-select) { width: 100%; } }
</style>
