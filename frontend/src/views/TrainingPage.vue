<template>
  <div class="frontend-b-page">
    <ModulePageHeader
      title="训练监控"
      description="查看 YOLO11 训练任务、Epoch 进度、Loss 与 mAP 指标。页面负责监控和展示，实际训练由后端训练服务与模型负责人执行。"
      :mock="isFrontendBMockMode"
    >
      <el-button :icon="Refresh" :loading="loading" @click="loadTasks">刷新任务</el-button>
      <el-button type="primary" :icon="Plus" @click="dialogVisible = true">新建训练</el-button>
    </ModulePageHeader>

    <div class="training-overview">
      <StatCard label="训练任务" :value="tasks.length" unit="个" :icon="List" helper="当前用户任务" />
      <StatCard label="运行中" :value="runningCount" unit="个" :icon="Loading" accent="#f59e0b" helper="自动轮询进度" />
      <StatCard label="最佳 mAP50" :value="bestMap50" unit="%" :decimals="1" :icon="TrendCharts" accent="#10b981" helper="已完成模型" />
      <StatCard label="当前 Epoch" :value="currentTask?.currentEpoch || 0" :unit="`/ ${currentTask?.totalEpochs || 0}`" :icon="Timer" accent="#7c3aed" helper="所选训练任务" />
    </div>

    <div class="training-grid">
      <section class="task-card">
        <div class="panel-heading">
          <div><h3>训练任务</h3><p>选择任务查看实时指标</p></div>
          <el-segmented v-model="statusFilter" :options="statusOptions" size="small" />
        </div>
        <div v-loading="loading" class="task-list">
          <button
            v-for="task in filteredTasks"
            :key="task.taskId"
            class="task-item"
            :class="{ active: task.taskId === selectedTaskId }"
            type="button"
            @click="selectTask(task.taskId)"
          >
            <div class="task-item__top">
              <strong>{{ task.taskName }}</strong>
              <el-tag :type="statusMeta(task.status).type" size="small" effect="light">
                {{ statusMeta(task.status).label }}
              </el-tag>
            </div>
            <p>{{ task.modelName }} · {{ task.datasetName }}</p>
            <el-progress :percentage="task.progress" :status="task.status === 'completed' ? 'success' : task.status === 'failed' ? 'exception' : ''" />
            <div class="task-item__meta"><span>Epoch {{ task.currentEpoch }}/{{ task.totalEpochs }}</span><span>{{ task.createdAt }}</span></div>
          </button>
          <el-empty v-if="!loading && filteredTasks.length === 0" :image-size="72" description="暂无对应任务" />
        </div>
      </section>

      <section class="detail-card" v-loading="detailLoading">
        <template v-if="currentTask">
          <div class="detail-card__header">
            <div>
              <span>当前任务</span>
              <h2>{{ currentTask.taskName }}</h2>
              <p>{{ currentTask.taskId }} · {{ currentTask.modelName }}</p>
            </div>
            <el-tag :type="statusMeta(currentTask.status).type" effect="dark" round>
              {{ statusMeta(currentTask.status).label }}
            </el-tag>
          </div>
          <el-progress
            :percentage="currentTask.progress"
            :stroke-width="12"
            :status="currentTask.status === 'completed' ? 'success' : currentTask.status === 'failed' ? 'exception' : ''"
          />
          <div class="detail-stats">
            <div><span>当前轮次</span><strong>{{ currentTask.currentEpoch }} / {{ currentTask.totalEpochs }}</strong></div>
            <div><span>最新 mAP50</span><strong>{{ lastMetric ? formatPercent(lastMetric.map50) : "—" }}</strong></div>
            <div><span>Precision</span><strong>{{ lastMetric ? formatPercent(lastMetric.precision) : "—" }}</strong></div>
            <div><span>Recall</span><strong>{{ lastMetric ? formatPercent(lastMetric.recall) : "—" }}</strong></div>
          </div>
          <el-alert v-if="currentTask.errorMessage" :title="currentTask.errorMessage" type="error" :closable="false" show-icon />
        </template>
        <el-empty v-else description="请选择训练任务" />
      </section>
    </div>

    <div class="metrics-grid">
      <EChartPanel title="训练损失" subtitle="Box / Class / DFL Loss" :option="lossOption" :empty="metrics.length === 0" :loading="detailLoading" />
      <EChartPanel title="模型评估指标" subtitle="Precision / Recall / mAP" :option="metricOption" :empty="metrics.length === 0" :loading="detailLoading" />
    </div>

    <el-dialog v-model="dialogVisible" title="新建训练任务" width="560px" destroy-on-close>
      <el-alert title="当前为 Mock 模式时，提交只会创建演示任务，不会启动真实 GPU 训练。" type="warning" :closable="false" show-icon />
      <el-form :model="trainingForm" label-position="top" class="training-form">
        <el-form-item label="任务名称"><el-input v-model="trainingForm.taskName" /></el-form-item>
        <div class="form-row">
          <el-form-item label="基础模型"><el-select v-model="trainingForm.modelName"><el-option v-for="name in ['YOLO11n','YOLO11s','YOLO11m']" :key="name" :label="name" :value="name" /></el-select></el-form-item>
          <el-form-item label="训练轮数"><el-input-number v-model="trainingForm.epochs" :min="10" :max="500" /></el-form-item>
        </div>
        <div class="form-row">
          <el-form-item label="图像尺寸"><el-select v-model="trainingForm.imgSize"><el-option label="640" :value="640" /><el-option label="1024" :value="1024" /></el-select></el-form-item>
          <el-form-item label="Batch Size"><el-input-number v-model="trainingForm.batchSize" :min="1" :max="64" /></el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="createTraining">创建任务</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { List, Loading, Plus, Refresh, Timer, TrendCharts } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { getTrainingDetailApi, getTrainingTasksApi, startTrainingApi } from "@/api/training";
import { getScenesApi, isFrontendBMockMode } from "@/api/models";
import EChartPanel from "@/components/charts/EChartPanel.vue";
import StatCard from "@/components/charts/StatCard.vue";
import ModulePageHeader from "@/components/common/ModulePageHeader.vue";

const tasks = ref([]);
const loading = ref(false);
const detailLoading = ref(false);
const selectedTaskId = ref("");
const currentTask = ref(null);
const metrics = ref([]);
const statusFilter = ref("all");
const dialogVisible = ref(false);
const creating = ref(false);
let pollTimer;

const statusOptions = [
  { label: "全部", value: "all" },
  { label: "运行中", value: "running" },
  { label: "已完成", value: "completed" },
  { label: "失败", value: "failed" },
];

const scenes = ref([]);
const trainingForm = reactive({ sceneId: "", taskName: "钢铁缺陷模型训练", modelName: "YOLO11n", epochs: 100, imgSize: 640, batchSize: 16, datasetName: "NEU 钢铁缺陷数据集" });
const filteredTasks = computed(() => statusFilter.value === "all" ? tasks.value : tasks.value.filter((task) => task.status === statusFilter.value));
const runningCount = computed(() => tasks.value.filter((task) => task.status === "running").length);
const bestMap50 = computed(() => Math.max(0, ...tasks.value.map((task) => Number(task.map50 || 0))) * 100);
const lastMetric = computed(() => metrics.value.at(-1));

const chartBase = { tooltip: { trigger: "axis" }, grid: { left: 48, right: 18, top: 42, bottom: 36 }, xAxis: { type: "category", boundaryGap: false, data: computed(() => metrics.value.map((item) => item.epoch)) }, yAxis: { type: "value", splitLine: { lineStyle: { color: "#edf0f5" } } } };
const lossOption = computed(() => ({ ...chartBase, color: ["#2563eb", "#f59e0b", "#8b5cf6"], legend: { data: ["Box Loss", "Class Loss", "DFL Loss"], top: 4 }, xAxis: { ...chartBase.xAxis, data: metrics.value.map((item) => item.epoch) }, series: [{ name: "Box Loss", type: "line", smooth: true, showSymbol: false, data: metrics.value.map((item) => item.boxLoss) }, { name: "Class Loss", type: "line", smooth: true, showSymbol: false, data: metrics.value.map((item) => item.clsLoss) }, { name: "DFL Loss", type: "line", smooth: true, showSymbol: false, data: metrics.value.map((item) => item.dflLoss) }] }));
const metricOption = computed(() => ({ ...chartBase, color: ["#10b981", "#06b6d4", "#f97316", "#7c3aed"], legend: { data: ["Precision", "Recall", "mAP50", "mAP50-95"], top: 4 }, xAxis: { ...chartBase.xAxis, data: metrics.value.map((item) => item.epoch) }, yAxis: { ...chartBase.yAxis, min: 0, max: 1 }, series: [{ name: "Precision", type: "line", smooth: true, showSymbol: false, data: metrics.value.map((item) => item.precision) }, { name: "Recall", type: "line", smooth: true, showSymbol: false, data: metrics.value.map((item) => item.recall) }, { name: "mAP50", type: "line", smooth: true, showSymbol: false, data: metrics.value.map((item) => item.map50) }, { name: "mAP50-95", type: "line", smooth: true, showSymbol: false, data: metrics.value.map((item) => item.map50_95) }] }));

function statusMeta(status) { return { running: { label: "运行中", type: "warning" }, completed: { label: "已完成", type: "success" }, failed: { label: "失败", type: "danger" }, pending: { label: "等待中", type: "info" }, cancelled: { label: "已取消", type: "info" } }[status] || { label: status, type: "info" }; }
function formatPercent(value) { return value == null ? "—" : `${(Number(value) * 100).toFixed(1)}%`; }

async function loadTasks() {
  loading.value = true;
  try {
    scenes.value = await getScenesApi();
    if (!trainingForm.sceneId) trainingForm.sceneId = scenes.value[0]?.id || "";
    tasks.value = await getTrainingTasksApi();
    if (!selectedTaskId.value && tasks.value.length) await selectTask(tasks.value[0].taskId);
  } catch { ElMessage.error("训练任务加载失败"); }
  finally { loading.value = false; }
}

async function selectTask(taskId, silent = false) {
  selectedTaskId.value = taskId;
  if (!silent) detailLoading.value = true;
  try {
    const detail = await getTrainingDetailApi(taskId);
    currentTask.value = detail;
    metrics.value = detail.metrics || [];
    const index = tasks.value.findIndex((task) => task.taskId === taskId);
    if (index >= 0) tasks.value[index] = { ...tasks.value[index], ...detail, metrics: undefined };
    setupPolling();
  } catch { if (!silent) ElMessage.error("训练详情加载失败"); }
  finally { detailLoading.value = false; }
}

function setupPolling() {
  clearInterval(pollTimer);
  if (currentTask.value?.status === "running") pollTimer = window.setInterval(() => selectTask(selectedTaskId.value, true), 3000);
}

async function createTraining() {
  if (!trainingForm.sceneId) {
    ElMessage.warning("请先创建或选择检测场景");
    return;
  }
  creating.value = true;
  try {
    const task = await startTrainingApi(trainingForm);
    tasks.value.unshift(task);
    dialogVisible.value = false;
    ElMessage.success("训练任务已创建");
    await selectTask(task.taskId);
  } catch { ElMessage.error("训练任务创建失败"); }
  finally { creating.value = false; }
}

onMounted(loadTasks);
onBeforeUnmount(() => clearInterval(pollTimer));
</script>

<style lang="scss" scoped>
.frontend-b-page { min-height: 100%; }
.training-overview { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 18px; }
.training-grid { display: grid; grid-template-columns: minmax(320px, .8fr) minmax(470px, 1.25fr); gap: 18px; margin-bottom: 18px; }
.task-card, .detail-card { min-width: 0; padding: 20px; border: 1px solid #e7ebf1; border-radius: 14px; background: #fff; box-shadow: 0 8px 24px rgba(28,39,60,.05); }
.panel-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.panel-heading h3 { margin: 0; color: #1f2937; font-size: 16px; }
.panel-heading p { margin: 4px 0 0; color: $text-secondary; font-size: 12px; }
.task-list { display: flex; max-height: 480px; flex-direction: column; gap: 10px; overflow-y: auto; }
.task-item { width: 100%; padding: 14px; border: 1px solid #e7ebf1; border-radius: 11px; background: #fff; color: inherit; cursor: pointer; text-align: left; transition: .2s; }
.task-item:hover, .task-item.active { border-color: #93b4f4; background: #f5f8ff; }
.task-item__top, .task-item__meta { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.task-item__top strong { overflow: hidden; color: #172033; text-overflow: ellipsis; white-space: nowrap; }
.task-item p, .task-item__meta { color: $text-secondary; font-size: 11px; }
.task-item p { margin: 6px 0 9px; }
.task-item__meta { margin-top: 5px; }
.detail-card__header { display: flex; justify-content: space-between; gap: 18px; margin-bottom: 20px; }
.detail-card__header span { color: #2563eb; font-size: 11px; font-weight: 700; letter-spacing: .08em; }
.detail-card__header h2 { margin: 6px 0; color: #172033; font-size: 21px; }
.detail-card__header p { margin: 0; color: $text-secondary; font-size: 12px; }
.detail-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 20px 0; }
.detail-stats div { padding: 13px; border-radius: 10px; background: #f7f9fc; }
.detail-stats span, .detail-stats strong { display: block; }
.detail-stats span { color: $text-secondary; font-size: 11px; }
.detail-stats strong { margin-top: 5px; color: #172033; font-size: 16px; }
.metrics-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.training-form { margin-top: 18px; }
.form-row { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }
.form-row :deep(.el-select) { width: 100%; }
@media (max-width: 1180px) { .training-overview { grid-template-columns: repeat(2, 1fr); } .training-grid, .metrics-grid { grid-template-columns: 1fr; } }
@media (max-width: 640px) { .training-overview, .detail-stats, .form-row { grid-template-columns: 1fr; } .panel-heading { flex-direction: column; } }
</style>
