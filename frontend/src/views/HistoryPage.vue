<template>
  <div class="frontend-b-page">
    <ModulePageHeader
      title="历史记录"
      description="查询真实检测任务，按场景、检测类型和状态筛选，并查看或删除属于当前用户的记录。"
      :mock="false"
    >
      <el-button :icon="Refresh" :loading="loading" @click="loadHistory">
        刷新
      </el-button>
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
        <el-button link type="primary" @click="loadHistory">重新加载</el-button>
      </template>
    </el-alert>

    <section class="filter-bar">
      <div class="filter-bar__title">
        <el-icon><Filter /></el-icon>
        <span>记录筛选</span>
      </div>
      <el-select v-model="filters.sceneId" placeholder="全部场景" clearable>
        <el-option
          v-for="scene in scenes"
          :key="scene.id"
          :label="scene.displayName"
          :value="scene.id"
        />
      </el-select>
      <el-select v-model="filters.taskType" placeholder="全部类型" clearable>
        <el-option
          v-for="option in taskTypeOptions"
          :key="option.value"
          :label="option.label"
          :value="option.value"
        />
      </el-select>
      <el-select v-model="filters.status" placeholder="全部状态" clearable>
        <el-option
          v-for="option in statusOptions"
          :key="option.value"
          :label="option.label"
          :value="option.value"
        />
      </el-select>
      <el-button type="primary" :icon="Search" @click="applyFilters">查询</el-button>
      <el-button @click="resetFilters">重置</el-button>
    </section>

    <section class="history-card">
      <el-table
        v-loading="loading"
        :data="history.items"
        row-key="id"
        empty-text="当前筛选条件下暂无检测记录"
      >
        <el-table-column prop="id" label="任务 ID" width="92" />
        <el-table-column prop="sceneName" label="检测场景" min-width="150" show-overflow-tooltip />
        <el-table-column label="检测类型" width="112">
          <template #default="{ row }">{{ taskTypeLabel(row.taskType) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="105">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" effect="light" round>
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="totalImages" label="图片" width="82" align="right" />
        <el-table-column prop="totalObjects" label="缺陷" width="82" align="right" />
        <el-table-column label="总耗时" width="110" align="right">
          <template #default="{ row }">{{ formatDuration(row.totalInferenceTimeMs) }}</template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="170">
          <template #default="{ row }">{{ formatDateTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :icon="View" @click="openDetail(row)">
              详情
            </el-button>
            <el-button
              link
              type="danger"
              :icon="Delete"
              :loading="deletingId === row.id"
              @click="removeHistory(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="history.total > 0"
        class="history-pagination"
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="history.total"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="loadHistory"
        @size-change="handlePageSizeChange"
      />
    </section>

    <el-drawer v-model="detailVisible" title="检测任务详情" size="min(720px, 92vw)">
      <div v-loading="detailLoading" class="detail-content">
        <el-alert
          v-if="detailError"
          :title="detailError"
          type="error"
          show-icon
          :closable="false"
        />

        <template v-if="detail.task && !detailError">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="任务 ID">{{ detail.task.id }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusType(detail.task.status)" effect="light">
                {{ statusLabel(detail.task.status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="检测场景">{{ detail.task.sceneName }}</el-descriptions-item>
            <el-descriptions-item label="检测类型">{{ taskTypeLabel(detail.task.taskType) }}</el-descriptions-item>
            <el-descriptions-item label="图片数量">{{ detail.task.totalImages }}</el-descriptions-item>
            <el-descriptions-item label="缺陷数量">{{ detail.task.totalObjects }}</el-descriptions-item>
            <el-descriptions-item label="置信度阈值">{{ formatNumber(detail.task.confThreshold, 2) }}</el-descriptions-item>
            <el-descriptions-item label="IoU 阈值">{{ formatNumber(detail.task.iouThreshold, 2) }}</el-descriptions-item>
            <el-descriptions-item label="总推理耗时">{{ formatDuration(detail.task.totalInferenceTimeMs) }}</el-descriptions-item>
            <el-descriptions-item label="单图平均耗时">{{ formatDuration(detail.task.avgInferenceTimeMs) }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatDateTime(detail.task.createdAt) }}</el-descriptions-item>
            <el-descriptions-item label="完成时间">{{ formatDateTime(detail.task.completedAt) }}</el-descriptions-item>
          </el-descriptions>

          <el-alert
            v-if="detail.task.errorMessage"
            class="detail-error"
            title="任务错误信息"
            :description="detail.task.errorMessage"
            type="error"
            show-icon
            :closable="false"
          />

          <div class="result-heading">
            <h3>缺陷明细</h3>
            <span>共 {{ detail.results.length }} 条目标记录</span>
          </div>
          <el-table :data="detail.results" empty-text="该任务没有缺陷目标明细" max-height="430">
            <el-table-column label="结果图" width="84">
              <template #default="{ row }">
                <el-image
                  v-if="row.annotatedImageUrl"
                  class="result-image"
                  :src="row.annotatedImageUrl"
                  :preview-src-list="[row.annotatedImageUrl]"
                  preview-teleported
                  fit="cover"
                />
                <span v-else>—</span>
              </template>
            </el-table-column>
            <el-table-column label="文件" min-width="140" show-overflow-tooltip>
              <template #default="{ row }">{{ fileName(row.imagePath) }}</template>
            </el-table-column>
            <el-table-column prop="classNameCn" label="缺陷类别" width="110" />
            <el-table-column label="置信度" width="92" align="right">
              <template #default="{ row }">{{ formatPercent(row.confidence) }}</template>
            </el-table-column>
            <el-table-column label="边界框" min-width="150">
              <template #default="{ row }">{{ formatBbox(row.bbox) }}</template>
            </el-table-column>
          </el-table>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { Delete, Filter, Refresh, Search, View } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { onMounted, reactive, ref } from "vue";
import {
  deleteHistoryApi,
  getHistoryApi,
  getHistoryDetailApi,
} from "@/api/history";
import { getScenesApi } from "@/api/models";
import ModulePageHeader from "@/components/common/ModulePageHeader.vue";
import { getApiErrorMessage } from "@/utils/apiError";

const taskTypeOptions = [
  { value: "single", label: "单图检测" },
  { value: "batch", label: "批量检测" },
  { value: "folder", label: "文件夹检测" },
  { value: "video", label: "视频检测" },
  { value: "camera", label: "摄像头检测" },
];
const statusOptions = [
  { value: "pending", label: "等待中" },
  { value: "processing", label: "处理中" },
  { value: "completed", label: "已完成" },
  { value: "failed", label: "失败" },
];

const loading = ref(false);
const pageError = ref("");
const scenes = ref([]);
const deletingId = ref(null);
const filters = reactive({ sceneId: "", taskType: "", status: "" });
const pagination = reactive({ page: 1, pageSize: 20 });
const history = reactive({ items: [], total: 0 });

const detailVisible = ref(false);
const detailLoading = ref(false);
const detailError = ref("");
const detail = reactive({ task: null, results: [] });

function taskTypeLabel(value) {
  return taskTypeOptions.find((item) => item.value === value)?.label || value || "—";
}

function statusLabel(value) {
  return statusOptions.find((item) => item.value === value)?.label || value || "—";
}

function statusType(value) {
  return { completed: "success", failed: "danger", processing: "primary", pending: "warning" }[value] || "info";
}

function formatDateTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", { hour12: false });
}

function formatDuration(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${number.toFixed(1)} ms` : "—";
}

function formatNumber(value, digits = 1) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : "—";
}

function formatPercent(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${(number * 100).toFixed(1)}%` : "—";
}

function formatBbox(value) {
  return Array.isArray(value) && value.length === 4
    ? value.map((item) => Number(item).toFixed(0)).join(", ")
    : "—";
}

function fileName(path) {
  return path?.split(/[\\/]/).pop() || "—";
}

async function loadScenes() {
  try {
    scenes.value = await getScenesApi();
  } catch (error) {
    pageError.value = getApiErrorMessage(error, "检测场景加载失败");
  }
}

async function loadHistory() {
  loading.value = true;
  pageError.value = "";
  try {
    const data = await getHistoryApi({
      ...filters,
      page: pagination.page,
      pageSize: pagination.pageSize,
    });
    history.items = data.items;
    history.total = data.total;
  } catch (error) {
    history.items = [];
    history.total = 0;
    pageError.value = getApiErrorMessage(error, "历史记录加载失败");
  } finally {
    loading.value = false;
  }
}

function applyFilters() {
  pagination.page = 1;
  loadHistory();
}

function resetFilters() {
  Object.assign(filters, { sceneId: "", taskType: "", status: "" });
  pagination.page = 1;
  loadHistory();
}

function handlePageSizeChange() {
  pagination.page = 1;
  loadHistory();
}

async function openDetail(row) {
  detailVisible.value = true;
  detailLoading.value = true;
  detailError.value = "";
  detail.task = null;
  detail.results = [];
  try {
    Object.assign(detail, await getHistoryDetailApi(row.id));
  } catch (error) {
    detailError.value = getApiErrorMessage(error, "检测详情加载失败");
  } finally {
    detailLoading.value = false;
  }
}

async function removeHistory(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除检测任务 #${row.id} 吗？相关结果记录也会被删除。`,
      "删除历史记录",
      { type: "warning", confirmButtonText: "删除", cancelButtonText: "取消" },
    );
    deletingId.value = row.id;
    await deleteHistoryApi(row.id);
    ElMessage.success("历史记录已删除");
    if (history.items.length === 1 && pagination.page > 1) pagination.page -= 1;
    await loadHistory();
  } catch (error) {
    if (error !== "cancel" && error !== "close") {
      pageError.value = getApiErrorMessage(error, "历史记录删除失败");
    }
  } finally {
    deletingId.value = null;
  }
}

onMounted(async () => {
  await Promise.all([loadScenes(), loadHistory()]);
});
</script>

<style lang="scss" scoped>
.frontend-b-page { min-height: 100%; }
.page-alert { margin-bottom: 16px; }
.filter-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 18px; padding: 14px 16px; border: 1px solid #e7ebf1; border-radius: 12px; background: #fff; }
.filter-bar__title { display: flex; align-items: center; gap: 7px; margin-right: auto; color: #344054; font-weight: 600; }
.filter-bar :deep(.el-select) { width: 160px; }
.history-card { overflow: hidden; padding: 8px 16px 16px; border: 1px solid #e7ebf1; border-radius: 14px; background: #fff; box-shadow: 0 8px 24px rgba(28, 39, 60, 0.05); }
.history-pagination { justify-content: flex-end; margin-top: 16px; }
.detail-content { min-height: 180px; }
.detail-error { margin-top: 16px; }
.result-heading { display: flex; align-items: baseline; justify-content: space-between; margin: 24px 0 12px; }
.result-heading h3 { margin: 0; color: #1f2937; font-size: 16px; }
.result-heading span { color: $text-secondary; font-size: 12px; }
.result-image { width: 54px; height: 42px; border-radius: 6px; }
@media (max-width: 900px) { .filter-bar { flex-wrap: wrap; } .filter-bar__title { width: 100%; } .filter-bar :deep(.el-select) { flex: 1; min-width: 140px; } }
</style>
