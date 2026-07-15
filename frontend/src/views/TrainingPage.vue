<template>
  <div class="training-page">
    <div class="page-header">
      <div>
        <h2>模型训练与监控</h2>
        <p>创建 YOLOv11 训练任务，实时查看训练进度并完成模型评估与导出。</p>
      </div>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        新建训练任务
      </el-button>
    </div>

    <el-alert
      v-if="pageError"
      class="page-alert"
      :title="pageError"
      type="error"
      show-icon
      closable
      @close="pageError = ''"
    />

    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div>
            <span class="card-title">训练任务列表</span>
            <span class="card-caption">共 {{ taskList.length }} 个任务</span>
          </div>
          <el-button text :loading="loadingTasks" @click="fetchTasks">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>

      <el-table
        v-loading="loadingTasks"
        :data="taskList"
        row-key="id"
        stripe
        empty-text="暂无训练任务"
        highlight-current-row
        @current-change="handleCurrentTaskChange"
      >
        <el-table-column prop="task_uuid" label="任务 ID" min-width="108" />
        <el-table-column prop="model_name" label="模型" min-width="106" />
        <el-table-column prop="device" label="设备" min-width="82" />
        <el-table-column label="进度" min-width="188">
          <template #default="{ row }">
            <el-progress
              :percentage="normalizeProgress(row.progress)"
              :status="progressStatus(row.status)"
              :stroke-width="14"
            />
          </template>
        </el-table-column>
        <el-table-column label="Epoch" min-width="96">
          <template #default="{ row }">
            {{ row.current_epoch || 0 }}/{{ row.epochs || 0 }}
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="96">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">
              {{ statusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="168">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="148" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" text @click.stop="selectTask(row)">
              监控
            </el-button>
            <el-button
              v-if="row.status === 'running'"
              size="small"
              type="danger"
              text
              @click.stop="stopTask(row.id)"
            >
              停止
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card v-if="selectedTask" class="section-card" shadow="never">
      <template #header>
        <div class="card-header monitor-header">
          <div>
            <span class="card-title">训练监控 - 任务 {{ selectedTask.task_uuid }}</span>
            <el-tag :type="statusType(selectedTask.status)" size="small">
              {{ statusText(selectedTask.status) }}
            </el-tag>
          </div>
          <div class="monitor-info">
            <span>模型：{{ selectedTask.model_name }}</span>
            <span>设备：{{ selectedTask.device }}</span>
            <span>Epoch：{{ selectedTask.current_epoch || 0 }}/{{ selectedTask.epochs || 0 }}</span>
          </div>
        </div>
      </template>

      <el-alert
        v-if="monitorError"
        class="monitor-alert"
        :title="monitorError"
        type="error"
        show-icon
        :closable="false"
      />

      <el-progress
        class="monitor-progress"
        :percentage="normalizeProgress(selectedTask.progress)"
        :status="progressStatus(selectedTask.status)"
        :stroke-width="18"
      />

      <el-row :gutter="16" class="metric-grid">
        <el-col
          v-for="item in metricCards"
          :key="item.label"
          :xs="12"
          :sm="8"
          :lg="4"
        >
          <div class="metric-item">
            <div class="metric-value">{{ item.value }}</div>
            <div class="metric-label">{{ item.label }}</div>
          </div>
        </el-col>
      </el-row>

      <el-row :gutter="16" class="chart-grid">
        <el-col :xs="24" :lg="12">
          <div ref="lossChartRef" class="chart-panel" />
        </el-col>
        <el-col :xs="24" :lg="12">
          <div ref="mapChartRef" class="chart-panel" />
        </el-col>
      </el-row>
    </el-card>

    <el-card
      v-if="selectedTask && selectedTask.status === 'completed'"
      class="section-card"
      shadow="never"
    >
      <template #header>
        <div class="card-header">
          <div>
            <span class="card-title">模型操作</span>
            <span class="card-caption">仅已完成的训练任务可评估、导出和验证</span>
          </div>
        </div>
      </template>

      <el-space wrap>
        <el-button type="primary" :loading="validating" @click="validateModel">
          评估模型
        </el-button>
        <el-button type="success" @click="showExportDialog = true">
          导出模型
        </el-button>
        <el-button :loading="downloading" @click="downloadModel">
          下载权重
        </el-button>
        <el-button type="warning" @click="openPredictDialog">
          测试验证
        </el-button>
      </el-space>
    </el-card>

    <el-card v-if="evalReport" class="section-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div>
            <span class="card-title">评估报告</span>
            <el-tag size="small">
              {{ evalReport.split === 'test' ? '测试集' : '验证集' }}
            </el-tag>
          </div>
          <span class="card-caption">模型版本 {{ evalReport.model_version || '-' }}</span>
        </div>
      </template>

      <el-row :gutter="16" class="metric-grid evaluation-metrics">
        <el-col
          v-for="item in evalMetricCards"
          :key="item.label"
          :xs="12"
          :sm="6"
        >
          <div class="metric-item">
            <div class="metric-value" :style="{ color: item.color }">{{ item.value }}</div>
            <div class="metric-label">{{ item.label }}</div>
          </div>
        </el-col>
      </el-row>

      <div class="subsection-title">每类 AP 分析</div>
      <el-table
        :data="perClassData"
        stripe
        :row-class-name="tableRowClassName"
        empty-text="评估报告中暂无分类指标"
      >
        <el-table-column prop="class_name" label="类别" min-width="180" />
        <el-table-column label="AP@50" min-width="140">
          <template #default="{ row }">
            <span :class="{ 'weak-value': row.ap50 < 0.5 }">
              {{ formatPercent(row.ap50) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="AP@50-95" min-width="140">
          <template #default="{ row }">{{ formatPercent(row.ap50_95) }}</template>
        </el-table-column>
        <el-table-column label="评价" min-width="120">
          <template #default="{ row }">
            <el-tag :type="apLevel(row.ap50).type" size="small">
              {{ apLevel(row.ap50).text }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>

      <el-alert
        class="plot-notice"
        type="info"
        :closable="false"
        show-icon
        title="混淆矩阵、PR 曲线和 F1 曲线由后端评估过程生成；当前指导书接口未返回图片访问地址。"
      />
    </el-card>

    <el-dialog
      v-model="showCreateDialog"
      title="新建训练任务"
      width="min(620px, 92vw)"
      :close-on-click-modal="false"
    >
      <el-form :model="trainForm" label-width="110px">
        <el-form-item label="训练数据集">
          <div class="dataset-picker">
            <el-select v-model="trainForm.dataset_path" class="full-width" placeholder="选择已准备的数据集">
              <el-option
                v-for="dataset in datasets"
                :key="dataset.path || dataset.name"
                :label="dataset.name"
                :value="dataset.path"
                :disabled="!dataset.ready"
              />
            </el-select>
            <el-upload
              :show-file-list="false"
              accept=".zip"
              :auto-upload="false"
              :on-change="handleDatasetUpload"
            >
              <el-button :loading="uploadingDataset" :icon="UploadFilled">上传 ZIP</el-button>
            </el-upload>
          </div>
          <span class="form-hint">ZIP 根目录必须包含 data.yaml</span>
        </el-form-item>
        <el-form-item label="检测场景">
          <el-select v-model="trainForm.scene_id" class="full-width" placeholder="选择场景">
            <el-option
              v-for="scene in scenes"
              :key="scene.id"
              :label="scene.displayName || scene.name"
              :value="Number(scene.id)"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="基础模型">
          <el-select v-model="trainForm.model_name" class="full-width">
            <el-option label="YOLO11n (Nano，最快)" value="yolo11n" />
            <el-option label="YOLO11s (Small)" value="yolo11s" />
            <el-option label="YOLO11m (Medium)" value="yolo11m" />
            <el-option label="YOLO11l (Large)" value="yolo11l" />
            <el-option label="YOLO11x (XLarge，精度优先)" value="yolo11x" />
          </el-select>
        </el-form-item>

        <el-form-item label="训练轮数">
          <el-slider v-model="trainForm.epochs" :min="10" :max="500" :step="10" show-input />
        </el-form-item>

        <el-form-item label="批次大小">
          <el-input-number v-model="trainForm.batch_size" :min="1" :max="64" :step="1" />
        </el-form-item>

        <el-form-item label="图像尺寸">
          <el-select v-model="trainForm.img_size" class="full-width">
            <el-option label="416" :value="416" />
            <el-option label="512" :value="512" />
            <el-option label="640（默认）" :value="640" />
            <el-option label="768" :value="768" />
          </el-select>
        </el-form-item>

        <el-form-item label="训练设备">
          <el-radio-group v-model="trainForm.device">
            <el-radio value="cpu">CPU（本地）</el-radio>
            <el-radio value="0">GPU:0</el-radio>
            <el-radio value="1">GPU:1</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="优化器">
          <el-select v-model="trainForm.optimizer" class="full-width">
            <el-option label="SGD（推荐）" value="SGD" />
            <el-option label="Adam" value="Adam" />
            <el-option label="AdamW" value="AdamW" />
          </el-select>
        </el-form-item>

        <el-form-item label="初始学习率">
          <el-input-number
            v-model="trainForm.lr0"
            :min="0.0001"
            :max="0.1"
            :step="0.001"
            :precision="4"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="createTask">
          启动训练
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="showExportDialog"
      title="导出模型"
      width="min(520px, 92vw)"
      :close-on-click-modal="false"
    >
      <el-form :model="exportForm" label-width="100px">
        <el-form-item label="版本号">
          <el-input v-model="exportForm.version" placeholder="留空则自动生成，如 v1.0.0" />
        </el-form-item>
        <el-form-item label="版本描述">
          <el-input
            v-model="exportForm.description"
            type="textarea"
            :rows="3"
            placeholder="描述本次训练的主要变更"
          />
        </el-form-item>
        <el-form-item label="设为默认">
          <el-switch v-model="exportForm.set_default" />
          <span class="form-hint">设为该场景的默认检测模型</span>
        </el-form-item>
        <el-form-item label="上传 MinIO">
          <el-switch v-model="exportForm.upload_minio" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showExportDialog = false">取消</el-button>
        <el-button type="primary" :loading="exporting" @click="exportModel">
          确认导出
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="showPredictDialog"
      title="测试图验证"
      width="min(980px, 94vw)"
      :close-on-click-modal="false"
      @closed="disposePredictChart"
    >
      <el-row :gutter="20">
        <el-col :xs="24" :md="10">
          <el-upload
            drag
            action=""
            :auto-upload="false"
            :on-change="handlePredictFileChange"
            :limit="1"
            accept="image/jpeg,image/png,image/bmp,image/webp"
          >
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div>拖拽图片到此处，或 <em>点击选择</em></div>
            <template #tip>
              <div class="el-upload__tip">支持 JPG、PNG、BMP、WebP 格式</div>
            </template>
          </el-upload>

          <el-form label-width="72px" class="predict-settings">
            <el-form-item label="置信度">
              <el-slider
                v-model="predictConf"
                :min="0.05"
                :max="0.95"
                :step="0.05"
                show-input
              />
            </el-form-item>
            <el-form-item label="IoU">
              <el-slider
                v-model="predictIou"
                :min="0.1"
                :max="0.9"
                :step="0.05"
                show-input
              />
            </el-form-item>
          </el-form>

          <el-button
            class="full-width"
            type="primary"
            :loading="predicting"
            :disabled="!predictFile"
            @click="runPredict"
          >
            开始检测
          </el-button>
        </el-col>

        <el-col :xs="24" :md="14">
          <div v-if="predictResult" class="predict-result">
            <img
              :src="annotatedImageSrc"
              class="annotated-image"
              alt="模型测试验证标注结果"
            />
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="检测目标数">
                {{ predictResult.total_objects }}
              </el-descriptions-item>
              <el-descriptions-item label="推理耗时">
                {{ predictResult.inference_time }} ms
              </el-descriptions-item>
            </el-descriptions>
            <div ref="predictChartRef" class="predict-chart" />
            <el-table :data="predictResult.detections || []" stripe size="small" max-height="210">
              <el-table-column prop="class_name" label="类别" min-width="110" />
              <el-table-column label="置信度" min-width="96">
                <template #default="{ row }">{{ formatPercent(row.confidence) }}</template>
              </el-table-column>
              <el-table-column label="位置" min-width="180">
                <template #default="{ row }">{{ formatBoundingBox(row.bbox) }}</template>
              </el-table-column>
            </el-table>
          </div>
          <el-empty v-else description="上传一张全新测试图片并点击检测" />
        </el-col>
      </el-row>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { Plus, Refresh, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import {
  downloadTrainingModel,
  exportTrainingModel,
  getTrainingDatasets,
  getTrainingMetrics,
  getTrainingStatus,
  getTrainingTasks,
  predictTrainingImage,
  startTraining,
  stopTraining,
  uploadTrainingDataset,
  validateTrainingModel,
} from '@/api/training'
import { getScenesApi } from '@/api/models'
import { getApiErrorMessage } from '@/utils/apiError'

const POLL_INTERVAL = 5000
const RUNNING_STATUSES = new Set(['pending', 'running'])

const taskList = ref([])
const loadingTasks = ref(false)
const pageError = ref('')
const monitorError = ref('')
const selectedTask = ref(null)
const showCreateDialog = ref(false)
const creating = ref(false)

const lossChartRef = ref(null)
const mapChartRef = ref(null)
let lossChart = null
let mapChart = null
let pollTimer = null

const evalReport = ref(null)
const validating = ref(false)

const showExportDialog = ref(false)
const exporting = ref(false)
const downloading = ref(false)
const exportForm = ref({
  version: '',
  description: '',
  set_default: true,
  upload_minio: true,
})

const showPredictDialog = ref(false)
const predicting = ref(false)
const predictFile = ref(null)
const predictConf = ref(0.25)
const predictIou = ref(0.45)
const predictResult = ref(null)
const predictChartRef = ref(null)
let predictChart = null

const trainForm = ref({
  scene_id: null,
  dataset_path: '',
  model_name: 'yolo11n',
  epochs: 50,
  batch_size: 8,
  img_size: 640,
  device: 'cpu',
  optimizer: 'SGD',
  lr0: 0.01,
})
const scenes = ref([])
const datasets = ref([])
const uploadingDataset = ref(false)

const metricCards = computed(() => {
  const task = selectedTask.value
  if (!task) return []
  const metric = task.latest_metric

  return [
    { label: 'Epoch', value: `${metric?.epoch ?? task.current_epoch ?? 0}/${task.epochs ?? 0}` },
    { label: 'Box Loss', value: formatMetric(metric?.box_loss) },
    { label: 'Cls Loss', value: formatMetric(metric?.cls_loss) },
    { label: 'Precision', value: formatPercent(metric?.precision) },
    { label: 'mAP@50', value: formatPercent(metric?.map50) },
    { label: 'mAP@50-95', value: formatPercent(metric?.map50_95) },
  ]
})

const evalMetricCards = computed(() => {
  const overall = evalReport.value?.overall
  if (!overall) return []

  return [
    {
      label: 'Precision',
      value: formatPercent(overall.precision),
      color: overall.precision > 0.7 ? '#67c23a' : '#e6a23c',
    },
    {
      label: 'Recall',
      value: formatPercent(overall.recall),
      color: overall.recall > 0.7 ? '#67c23a' : '#e6a23c',
    },
    {
      label: 'mAP@50',
      value: formatPercent(overall.map50),
      color: overall.map50 > 0.5 ? '#67c23a' : '#f56c6c',
    },
    {
      label: 'mAP@50-95',
      value: formatPercent(overall.map50_95),
      color: overall.map50_95 > 0.3 ? '#67c23a' : '#f56c6c',
    },
  ]
})

const perClassData = computed(() => {
  const perClass = evalReport.value?.per_class
  if (!perClass) return []

  return Object.entries(perClass)
    .map(([className, metrics]) => ({
      class_name: className,
      ap50: metrics.ap50,
      ap50_95: metrics.ap50_95,
    }))
    .sort((a, b) => b.ap50 - a.ap50)
})

const annotatedImageSrc = computed(() => {
  const image = predictResult.value?.annotated_image
  if (!image) return ''
  return image.startsWith('data:') ? image : `data:image/jpeg;base64,${image}`
})

function statusType(status) {
  return {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info',
  }[status] || 'info'
}

function statusText(status) {
  return {
    pending: '等待中',
    running: '训练中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
  }[status] || status || '-'
}

function progressStatus(status) {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'exception'
  return undefined
}

function normalizeProgress(value) {
  const progress = Number(value)
  if (!Number.isFinite(progress)) return 0
  return Math.min(100, Math.max(0, Math.round(progress)))
}

function formatMetric(value) {
  return Number.isFinite(Number(value)) ? Number(value).toFixed(4) : '-'
}

function formatPercent(value) {
  return Number.isFinite(Number(value)) ? `${(Number(value) * 100).toFixed(1)}%` : '-'
}

function formatDateTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

function formatBoundingBox(bbox) {
  if (!Array.isArray(bbox)) return '-'
  return `[${bbox.map((value) => Number(value).toFixed(0)).join(', ')}]`
}

function apLevel(ap50) {
  if (ap50 >= 0.7) return { type: 'success', text: '优秀' }
  if (ap50 >= 0.5) return { type: 'warning', text: '良好' }
  return { type: 'danger', text: '需改进' }
}

function tableRowClassName({ row }) {
  return row.ap50 < 0.5 ? 'weak-row' : ''
}

function normalizeTaskStatusResponse(response) {
  if (!response) return null
  const task = response.task || response
  return {
    ...task,
    latest_metric: response.latest_metric ?? task.latest_metric ?? null,
  }
}

async function fetchTasks() {
  loadingTasks.value = true
  pageError.value = ''
  try {
    scenes.value = await getScenesApi()
    if (!trainForm.value.scene_id) trainForm.value.scene_id = Number(scenes.value[0]?.id) || null
    const response = await getTrainingTasks()
    taskList.value = response.items || []
  } catch (error) {
    console.error('获取训练任务列表失败', error)
    pageError.value = getApiErrorMessage(error, '训练任务列表加载失败')
  } finally {
    loadingTasks.value = false
  }
}

function handleCurrentTaskChange(task) {
  if (task) selectTask(task)
}

async function fetchDatasets() {
  try {
    const response = await getTrainingDatasets()
    datasets.value = response.items || []
    if (!trainForm.value.dataset_path) {
      trainForm.value.dataset_path = datasets.value.find((item) => item.ready)?.path ?? ''
    }
  } catch (error) {
    console.error('获取训练数据集失败', error)
    pageError.value = getApiErrorMessage(error, '训练数据集加载失败')
  }
}

async function handleDatasetUpload(uploadFile) {
  if (!uploadFile.raw) return
  uploadingDataset.value = true
  pageError.value = ''
  try {
    const dataset = await uploadTrainingDataset(uploadFile.raw)
    await fetchDatasets()
    trainForm.value.dataset_path = dataset.path
    ElMessage.success('数据集上传并校验通过')
  } catch (error) {
    console.error('上传训练数据集失败', error)
    pageError.value = getApiErrorMessage(error, '训练数据集上传失败')
  } finally {
    uploadingDataset.value = false
  }
}

async function selectTask(task) {
  stopPolling()
  selectedTask.value = { ...task }
  evalReport.value = null
  predictResult.value = null

  await nextTick()
  initCharts()
  await fetchMetrics()

  if (RUNNING_STATUSES.has(selectedTask.value?.status)) {
    startPolling()
  }
}

function initCharts() {
  lossChart?.dispose()
  mapChart?.dispose()
  lossChart = lossChartRef.value ? echarts.init(lossChartRef.value) : null
  mapChart = mapChartRef.value ? echarts.init(mapChartRef.value) : null
  updateCharts([])
}

async function fetchMetrics() {
  if (!selectedTask.value) return
  const taskId = selectedTask.value.id

  try {
    const [metricsResponse, statusResponse] = await Promise.all([
      getTrainingMetrics(taskId),
      getTrainingStatus(taskId),
    ])
    const metrics = metricsResponse.metrics || []
    const taskStatus = normalizeTaskStatusResponse(statusResponse)

    if (taskStatus) {
      selectedTask.value = { ...selectedTask.value, ...taskStatus }
      const index = taskList.value.findIndex((task) => task.id === taskStatus.id)
      if (index !== -1) {
        taskList.value[index] = { ...taskList.value[index], ...taskStatus }
      }
    }

    updateCharts(metrics)

    if (!RUNNING_STATUSES.has(selectedTask.value.status)) {
      stopPolling()
    }
    monitorError.value = ''
  } catch (error) {
    console.error('获取训练监控数据失败', error)
    monitorError.value = getApiErrorMessage(error, '训练监控数据加载失败')
  }
}

function updateCharts(metrics) {
  const epochs = metrics.map((metric) => metric.epoch)

  lossChart?.setOption({
    title: { text: '训练损失曲线', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { data: ['Box Loss', 'Cls Loss', 'DFL Loss'], bottom: 0 },
    grid: { left: 54, right: 24, top: 52, bottom: 56 },
    xAxis: { type: 'category', data: epochs, name: 'Epoch' },
    yAxis: { type: 'value', name: 'Loss', scale: true },
    series: [
      { name: 'Box Loss', type: 'line', smooth: true, data: metrics.map((m) => m.box_loss) },
      { name: 'Cls Loss', type: 'line', smooth: true, data: metrics.map((m) => m.cls_loss) },
      { name: 'DFL Loss', type: 'line', smooth: true, data: metrics.map((m) => m.dfl_loss) },
    ],
  })

  mapChart?.setOption({
    title: { text: '评估指标曲线', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { data: ['mAP@50', 'mAP@50-95', 'Precision', 'Recall'], bottom: 0 },
    grid: { left: 54, right: 24, top: 52, bottom: 56 },
    xAxis: { type: 'category', data: epochs, name: 'Epoch' },
    yAxis: { type: 'value', name: '指标值', min: 0, max: 1 },
    series: [
      {
        name: 'mAP@50',
        type: 'line',
        smooth: true,
        data: metrics.map((m) => m.map50),
        lineStyle: { color: '#409eff' },
        itemStyle: { color: '#409eff' },
      },
      {
        name: 'mAP@50-95',
        type: 'line',
        smooth: true,
        data: metrics.map((m) => m.map50_95),
        lineStyle: { color: '#67c23a' },
        itemStyle: { color: '#67c23a' },
      },
      {
        name: 'Precision',
        type: 'line',
        smooth: true,
        data: metrics.map((m) => m.precision),
        lineStyle: { type: 'dashed', color: '#e6a23c' },
        itemStyle: { color: '#e6a23c' },
      },
      {
        name: 'Recall',
        type: 'line',
        smooth: true,
        data: metrics.map((m) => m.recall),
        lineStyle: { type: 'dashed', color: '#f56c6c' },
        itemStyle: { color: '#f56c6c' },
      },
    ],
  })
}

function startPolling() {
  stopPolling()
  pollTimer = window.setInterval(fetchMetrics, POLL_INTERVAL)
}

function stopPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

async function createTask() {
  if (!trainForm.value.scene_id) {
    ElMessage.warning('请先选择检测场景')
    return
  }
  if (!trainForm.value.dataset_path) {
    ElMessage.warning('请先选择训练数据集')
    return
  }
  creating.value = true
  pageError.value = ''
  try {
    const response = await startTraining(trainForm.value)
    ElMessage.success(`训练任务已创建：${response.task_uuid}`)
    showCreateDialog.value = false
    await fetchTasks()
    const task = taskList.value.find((item) => item.id === response.id)
    if (task) await selectTask(task)
  } catch (error) {
    console.error('创建训练任务失败', error)
    pageError.value = getApiErrorMessage(error, '训练任务创建失败')
  } finally {
    creating.value = false
  }
}

async function stopTask(taskId) {
  pageError.value = ''
  try {
    await ElMessageBox.confirm('确定要停止当前训练任务吗？训练进度将被保留。', '确认停止', {
      type: 'warning',
    })
    await stopTraining(taskId)
    ElMessage.success('训练任务已停止')
    await fetchTasks()
    if (selectedTask.value?.id === taskId) await fetchMetrics()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      console.error('停止训练任务失败', error)
      pageError.value = getApiErrorMessage(error, '训练任务停止失败')
    }
  }
}

async function validateModel() {
  if (!selectedTask.value) return
  validating.value = true
  pageError.value = ''
  try {
    const response = await validateTrainingModel(selectedTask.value.id, {
      split: 'val',
      conf: 0.001,
      iou: 0.6,
    })
    evalReport.value = response
    ElMessage.success(`评估完成：mAP@50 ${formatPercent(response.overall?.map50)}`)
  } catch (error) {
    console.error('模型评估失败', error)
    pageError.value = getApiErrorMessage(error, '模型评估失败')
  } finally {
    validating.value = false
  }
}

async function exportModel() {
  if (!selectedTask.value) return
  exporting.value = true
  pageError.value = ''
  try {
    const response = await exportTrainingModel(selectedTask.value.id, {
      ...exportForm.value,
      version: exportForm.value.version || null,
      description: exportForm.value.description || null,
    })
    ElMessage.success(response.message || '模型导出成功')
    showExportDialog.value = false
  } catch (error) {
    console.error('模型导出失败', error)
    pageError.value = getApiErrorMessage(error, '模型导出失败')
  } finally {
    exporting.value = false
  }
}

async function downloadModel() {
  if (!selectedTask.value) return
  downloading.value = true
  pageError.value = ''
  try {
    const blob = await downloadTrainingModel(selectedTask.value.id)
    triggerBlobDownload(blob, `best_${selectedTask.value.task_uuid}.pt`)
    ElMessage.success('模型权重下载已开始')
  } catch (error) {
    console.error('模型权重下载失败', error)
    pageError.value = getApiErrorMessage(error, '模型权重下载失败')
  } finally {
    downloading.value = false
  }
}

function triggerBlobDownload(blob, filename) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

function openPredictDialog() {
  showPredictDialog.value = true
  predictFile.value = null
  predictResult.value = null
}

function handlePredictFileChange(file) {
  const allowedTypes = ['image/jpeg', 'image/png', 'image/bmp', 'image/webp']
  if (!allowedTypes.includes(file.raw?.type)) {
    predictFile.value = null
    ElMessage.warning('请选择 JPG、PNG、BMP 或 WebP 图片')
    return
  }
  predictFile.value = file.raw
  predictResult.value = null
}

async function runPredict() {
  if (!predictFile.value || !selectedTask.value) return
  predicting.value = true
  pageError.value = ''
  try {
    const formData = new FormData()
    formData.append('file', predictFile.value)
    formData.append('task_id', String(selectedTask.value.id))
    formData.append('conf', String(predictConf.value))
    formData.append('iou', String(predictIou.value))

    predictResult.value = await predictTrainingImage(formData)
    await nextTick()
    renderPredictChart(predictResult.value.class_counts || {})
    ElMessage.success(`检测完成：发现 ${predictResult.value.total_objects} 个目标`)
  } catch (error) {
    console.error('测试图验证失败', error)
    pageError.value = getApiErrorMessage(error, '测试图验证失败')
  } finally {
    predicting.value = false
  }
}

function renderPredictChart(classCounts) {
  disposePredictChart()
  if (!predictChartRef.value) return

  predictChart = echarts.init(predictChartRef.value)
  predictChart.setOption({
    title: { text: '类别统计', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'item' },
    legend: { type: 'scroll', bottom: 0 },
    series: [
      {
        name: '目标数量',
        type: 'pie',
        radius: ['35%', '62%'],
        center: ['50%', '45%'],
        data: Object.entries(classCounts).map(([name, value]) => ({ name, value })),
      },
    ],
  })
}

function disposePredictChart() {
  predictChart?.dispose()
  predictChart = null
}

function resizeCharts() {
  lossChart?.resize()
  mapChart?.resize()
  predictChart?.resize()
}

onMounted(() => {
  fetchTasks()
  fetchDatasets()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  stopPolling()
  lossChart?.dispose()
  mapChart?.dispose()
  disposePredictChart()
  window.removeEventListener('resize', resizeCharts)
})
</script>

<style lang="scss" scoped>
.training-page {
  width: 100%;
}

.page-alert,
.monitor-alert {
  margin-bottom: 16px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 20px;

  h2 {
    margin: 0;
    color: $text-primary;
    font-size: 24px;
  }

  p {
    margin: 8px 0 0;
    color: $text-secondary;
    font-size: 14px;
  }
}

.section-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;

  > div {
    display: flex;
    align-items: center;
    gap: 10px;
  }
}

.card-title {
  color: $text-primary;
  font-weight: 600;
}

.card-caption,
.form-hint {
  color: $text-secondary;
  font-size: 12px;
}

.form-hint {
  margin-left: 8px;
}

.monitor-info {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 16px;
  color: $text-secondary;
  font-size: 13px;
}

.monitor-progress {
  margin-bottom: 18px;
}

.metric-grid {
  row-gap: 16px;
}

.metric-item {
  height: 84px;
  padding: 14px 10px;
  text-align: center;
  background: #f8fafc;
  border: 1px solid #ebeef5;
  border-radius: $border-radius-md;
}

.metric-value {
  color: $text-primary;
  font-size: 21px;
  font-weight: 700;
}

.metric-label {
  margin-top: 6px;
  color: $text-secondary;
  font-size: 12px;
}

.chart-grid {
  margin-top: 18px;
  row-gap: 16px;
}

.chart-panel {
  height: 350px;
  border: 1px solid #ebeef5;
  border-radius: $border-radius-md;
}

.evaluation-metrics {
  margin-bottom: 22px;
}

.subsection-title {
  margin: 0 0 12px;
  color: $text-primary;
  font-weight: 600;
}

.weak-value {
  color: $danger-color;
  font-weight: 600;
}

.plot-notice {
  margin-top: 16px;
}

.full-width {
  width: 100%;
}

.dataset-picker {
  display: flex;
  width: 100%;
  gap: 8px;
}

.upload-icon {
  margin-bottom: 8px;
  color: $text-secondary;
  font-size: 42px;
}

.predict-settings {
  margin-top: 18px;
}

.predict-result {
  min-height: 380px;
}

.annotated-image {
  display: block;
  width: 100%;
  max-height: 360px;
  margin-bottom: 12px;
  object-fit: contain;
  background: #f5f7fa;
  border-radius: $border-radius-md;
}

.predict-chart {
  height: 240px;
  margin: 12px 0;
}

:deep(.weak-row) {
  --el-table-tr-bg-color: #fef0f0;
}

@media (max-width: 768px) {
  .page-header,
  .monitor-header,
  .card-header {
    align-items: stretch;
    flex-direction: column;
  }

  .page-header .el-button {
    width: 100%;
  }

  .monitor-info {
    justify-content: flex-start;
  }
}
</style>
