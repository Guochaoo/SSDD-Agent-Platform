<template>
  <div class="frontend-b-page">
    <ModulePageHeader
      :title="text.title"
      :description="text.description"
    >
      <span class="updated-at">{{ text.updatedAt }} {{ dashboard.updatedAt || "—" }}</span>
      <el-button :icon="Refresh" :loading="loading" @click="loadDashboard">{{ text.refresh }}</el-button>
    </ModulePageHeader>

    <PageErrorAlert
      v-if="pageError"
      :message="pageError"
      :retry-text="text.reload"
      @retry="loadDashboard"
    />

    <section class="filter-bar">
      <div class="filter-bar__title"><el-icon><Filter /></el-icon><span>{{ text.period }}</span></div>
      <el-select v-model="filters.days" :aria-label="text.period">
        <el-option :label="text.lastDays(7)" :value="7" />
        <el-option :label="text.lastDays(30)" :value="30" />
        <el-option :label="text.lastDays(90)" :value="90" />
        <el-option :label="text.lastDays(365)" :value="365" />
      </el-select>
      <el-select v-model="filters.sceneId" clearable :placeholder="text.allScenes"><el-option v-for="scene in scenes" :key="scene.id" :label="scene.displayName || scene.name" :value="scene.id" /></el-select>
      <el-select v-model="filters.taskType" clearable :placeholder="text.allTypes"><el-option v-for="item in taskTypeOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select>
      <el-select v-model="filters.status" clearable :placeholder="text.completedOnly"><el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select>
      <el-date-picker v-model="filters.dateRange" type="daterange" value-format="YYYY-MM-DD" :start-placeholder="text.startDate" :end-placeholder="text.endDate" />
      <el-button type="primary" @click="loadDashboard">{{ text.apply }}</el-button>
      <span class="filter-hint">{{ text.rangeHint }}</span>
    </section>

    <div class="stats-grid">
      <StatCard :label="text.totalTasks" :value="dashboard.totals.totalTasks" :unit="text.times" :icon="DocumentChecked" :helper="text.totalTasksHelp" />
      <StatCard :label="text.totalImages" :value="dashboard.totals.totalImages" :unit="text.images" :icon="Picture" accent="#7c3aed" :helper="text.totalImagesHelp" />
      <StatCard :label="text.totalObjects" :value="dashboard.totals.totalObjects" :unit="text.objects" :icon="WarningFilled" accent="#f97316" :helper="text.totalObjectsHelp" />
      <StatCard :label="text.avgTime" :value="dashboard.totals.avgInferenceTimeMs" unit="ms" :decimals="1" :icon="Odometer" accent="#10b981" :helper="text.avgTimeHelp" />
    </div>

    <div class="dashboard-grid dashboard-grid--primary">
      <EChartPanel :title="text.trendTitle" :subtitle="text.trendSubtitle" :option="trendOption" :loading="loading" :empty="dashboard.dailyTrend.length === 0" height="330px" />
      <EChartPanel :title="text.classTitle" :subtitle="text.classSubtitle" :option="classOption" :loading="loading" :empty="dashboard.classDistribution.length === 0" height="330px" />
    </div>
    <div class="dashboard-grid dashboard-grid--single">
      <EChartPanel :title="text.sceneTitle" :subtitle="text.sceneSubtitle" :option="sceneOption" :loading="loading" :empty="dashboard.sceneDistribution.length === 0" height="300px" />
    </div>
  </div>
</template>

<script setup>
import { DocumentChecked, Filter, Odometer, Picture, Refresh, WarningFilled } from "@element-plus/icons-vue";
import { computed, onMounted, reactive, ref } from "vue";
import { useSettingsStore } from '@/stores/settings'
import { getDashboardApi } from "@/api/statistics";
import { HISTORY_TASK_TYPE_OPTIONS } from "@/api/history";
import { getScenesApi } from "@/api/models";
import EChartPanel from "@/components/charts/EChartPanel.vue";
import StatCard from "@/components/charts/StatCard.vue";
import ModulePageHeader from "@/components/common/ModulePageHeader.vue";
import PageErrorAlert from "@/components/common/PageErrorAlert.vue";
import { getApiErrorMessage } from "@/utils/apiError";

const loading = ref(false);
const settingsStore = useSettingsStore()
const pageError = ref("");
const filters = reactive({ days: 30, sceneId: '', taskType: '', status: '', dateRange: [] });
const scenes = ref([])
const dashboard = reactive({
  totals: { totalTasks: 0, totalImages: 0, totalObjects: 0, avgInferenceTimeMs: 0 },
  classDistribution: [],
  dailyTrend: [],
  sceneDistribution: [],
  updatedAt: "",
});
const axisStyle = { axisLine: { lineStyle: { color: "#d0d5dd" } }, axisLabel: { color: "#667085" } };

const text = computed(() => settingsStore.isEnglish ? {
  title: 'Dashboard',
  description: 'Aggregate detection tasks, images, defect classes and scenes from the current account.',
  updatedAt: 'Updated at',
  refresh: 'Refresh',
  reload: 'Reload',
  period: 'Period',
  allScenes: 'All scenes',
  allTypes: 'All task types',
  completedOnly: 'Completed only',
  startDate: 'Start date',
  endDate: 'End date',
  lastDays: (days) => `Last ${days} days`,
  apply: 'Apply',
  rangeHint: 'Statistics are provided by `/history/statistics/summary`.',
  totalTasks: 'Detection tasks',
  totalImages: 'Images',
  totalObjects: 'Defects',
  avgTime: 'Average time',
  times: '',
  images: '',
  objects: '',
  totalTasksHelp: 'Completed detection tasks',
  totalImagesHelp: 'Images processed by historical tasks',
  totalObjectsHelp: 'Defect targets in historical results',
  avgTimeHelp: 'Average total inference time',
  trendTitle: 'Daily Detection Trend',
  trendSubtitle: 'Task count by creation date',
  classTitle: 'Defect Class Distribution',
  classSubtitle: 'Target counts in historical results',
  sceneTitle: 'Detection Scene Distribution',
  sceneSubtitle: 'Completed tasks by scene',
  taskSeries: 'Detection tasks',
  objectUnit: 'defects',
  loadFailed: 'Failed to load dashboard data',
} : {
  title: '数据看板',
  description: '使用当前账号真实检测历史聚合任务、图片、缺陷类别和检测场景数据。',
  updatedAt: '更新于',
  refresh: '刷新',
  reload: '重新加载',
  period: '统计周期',
  allScenes: '全部场景',
  allTypes: '全部任务类型',
  completedOnly: '仅已完成任务',
  startDate: '开始日期',
  endDate: '结束日期',
  lastDays: (days) => `最近 ${days} 天`,
  apply: '应用',
  rangeHint: '统计范围由后端 `/history/statistics/summary` 接口提供',
  totalTasks: '检测任务',
  totalImages: '检测图片',
  totalObjects: '缺陷目标',
  avgTime: '平均任务耗时',
  times: '次',
  images: '张',
  objects: '处',
  totalTasksHelp: '已完成的检测任务',
  totalImagesHelp: '历史任务累计处理图片',
  totalObjectsHelp: '历史结果累计缺陷目标',
  avgTimeHelp: '完成任务的平均总推理耗时',
  trendTitle: '每日检测任务趋势',
  trendSubtitle: '按创建日期统计检测任务数量',
  classTitle: '缺陷类别分布',
  classSubtitle: '当前账号历史结果中的目标数量',
  sceneTitle: '检测场景分布',
  sceneSubtitle: '已完成任务在各检测场景中的数量',
  taskSeries: '检测任务',
  objectUnit: '处',
  loadFailed: '看板数据加载失败',
})

const taskTypeOptions = computed(() => HISTORY_TASK_TYPE_OPTIONS.map((item) => ({
  ...item,
  label: settingsStore.isEnglish ? item.value : item.label,
})))
const statusOptions = computed(() => settingsStore.isEnglish ? [
  { value: 'pending', label: 'Pending' }, { value: 'processing', label: 'Processing' },
  { value: 'completed', label: 'Completed' }, { value: 'failed', label: 'Failed' },
] : [
  { value: 'pending', label: '等待中' }, { value: 'processing', label: '处理中' },
  { value: 'completed', label: '已完成' }, { value: 'failed', label: '失败' },
])

const trendOption = computed(() => ({
  tooltip: { trigger: "axis" },
  color: ["#2563eb"],
  grid: { left: 52, right: 18, top: 28, bottom: 34 },
  xAxis: { type: "category", data: dashboard.dailyTrend.map((item) => item.date), ...axisStyle },
  yAxis: { type: "value", minInterval: 1, splitLine: { lineStyle: { color: "#edf0f5" } }, ...axisStyle },
  series: [{ name: text.value.taskSeries, type: "line", smooth: true, symbolSize: 7, areaStyle: { color: "rgba(37,99,235,.08)" }, data: dashboard.dailyTrend.map((item) => item.tasks) }],
}));

const classOption = computed(() => ({
  tooltip: { trigger: "item", formatter: `{b}<br/>{c} ${text.value.objectUnit} · {d}%` },
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
    const data = await getDashboardApi({
      days: filters.days,
      sceneId: filters.sceneId,
      taskType: filters.taskType,
      status: filters.status,
      startDate: filters.dateRange?.[0],
      endDate: filters.dateRange?.[1],
    });
    Object.assign(dashboard, data, { updatedAt: new Date().toLocaleString(settingsStore.isEnglish ? "en-US" : "zh-CN", { hour12: false }) });
  } catch (error) {
    pageError.value = getApiErrorMessage(error, text.value.loadFailed);
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  try { scenes.value = await getScenesApi() } catch { scenes.value = [] }
  await loadDashboard()
});
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
