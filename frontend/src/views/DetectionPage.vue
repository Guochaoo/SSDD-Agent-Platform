<template>
  <div class="frontend-b-page">
    <ModulePageHeader
      title="检测工作台"
      description="上传钢铁表面图像，选择模型与阈值，查看缺陷位置、类别和置信度。批量、视频和摄像头模式按同一任务模型组织。"
      :mock="isFrontendBMockMode"
    >
      <el-button :icon="Refresh" @click="resetCurrentMode">重置当前模式</el-button>
    </ModulePageHeader>

    <el-tabs v-model="activeMode" class="mode-tabs">
      <el-tab-pane label="单图检测" name="single">
        <div class="detection-layout">
          <section class="control-card">
            <div class="section-title">
              <div>
                <h3>检测配置</h3>
                <p>支持 JPG、PNG、BMP、TIF，单文件不超过 10 MB</p>
              </div>
              <el-icon><Setting /></el-icon>
            </div>

            <el-alert
              v-if="modelWarmupStatus === 'loading'"
              title="检测模型预热中，请稍候"
              type="info"
              :closable="false"
              show-icon
              class="model-warmup-alert"
            />
            <el-alert
              v-else-if="modelWarmupStatus === 'error'"
              :title="`检测模型预热失败${warmupError ? `：${warmupError}` : ''}，首次检测时将自动加载`"
              type="warning"
              :closable="false"
              show-icon
              class="model-warmup-alert"
            />
            <el-alert
              v-else-if="modelWarmupStatus === 'ready' && (singleLoading || batchLoading)"
              title="模型加载成功，正在进行检测"
              type="success"
              :closable="false"
              show-icon
              class="model-warmup-alert"
            />
            <el-alert
              v-else-if="modelWarmupStatus === 'ready'"
              title="检测模型加载成功，可以开始检测"
              type="success"
              :closable="false"
              show-icon
              class="model-warmup-alert"
            />
            <el-form label-position="top">
              <el-form-item label="检测场景">
                <el-select v-model="form.sceneId" class="full-width" @change="loadModels">
                  <el-option
                    v-for="scene in scenes"
                    :key="scene.id"
                    :label="scene.displayName"
                    :value="scene.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="模型版本">
                <el-select v-model="form.modelId" class="full-width">
                  <el-option
                    v-for="model in models"
                    :key="model.id"
                    :value="model.id"
                    :label="`${model.modelType} · ${model.version}`"
                  >
                    <div class="model-option">
                      <span>{{ model.modelType }} · {{ model.version }}</span>
                      <small>mAP50 {{ formatPercent(model.map50) }}</small>
                    </div>
                  </el-option>
                </el-select>
              </el-form-item>
              <el-form-item>
                <template #label>
                  <span class="slider-label">
                    置信度阈值 <b>{{ form.confThreshold.toFixed(2) }}</b>
                  </span>
                </template>
                <el-slider v-model="form.confThreshold" :min="0.1" :max="0.9" :step="0.05" />
              </el-form-item>
              <el-form-item>
                <template #label>
                  <span class="slider-label">
                    IoU 阈值 <b>{{ form.iouThreshold.toFixed(2) }}</b>
                  </span>
                </template>
                <el-slider v-model="form.iouThreshold" :min="0.1" :max="0.9" :step="0.05" />
              </el-form-item>
            </el-form>

            <el-upload
              ref="singleUploadRef"
              v-model:file-list="singleFileList"
              class="steel-uploader"
              drag
              :auto-upload="false"
              :limit="1"
              :accept="imageAccept"
              :on-change="handleSingleFile"
              :on-remove="clearSingleFile"
              :on-exceed="handleSingleExceed"
            >
              <el-icon class="steel-uploader__icon"><UploadFilled /></el-icon>
              <div class="el-upload__text">拖入钢铁表面图像，或 <em>点击选择</em></div>
              <template #tip>
                <div class="el-upload__tip">上传后仅生成本地预览；点击开始检测才会提交。</div>
              </template>
            </el-upload>

            <el-button
              class="detect-button"
              type="primary"
              size="large"
              :icon="Aim"
              :loading="singleLoading"
              :disabled="!singleFile || !form.modelId"
              @click="startSingleDetection"
            >
              {{ singleLoading ? "正在检测" : "开始缺陷检测" }}
            </el-button>
          </section>

          <DetectionResultPanel
            :preview-url="singlePreviewUrl"
            :result="singleResult"
            :loading="singleLoading"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="批量检测" name="batch">
        <div class="workspace-card">
          <div class="section-title section-title--inline">
            <div>
              <h3>批量图片检测</h3>
              <p>一次最多 20 张；单张失败不会影响其他图片结果。</p>
            </div>
            <el-button
              type="primary"
              :icon="Files"
              :loading="batchLoading"
              :disabled="batchFileList.length === 0"
              @click="startBatchDetection"
            >开始批量检测</el-button>
          </div>
          <el-upload
            ref="batchUploadRef"
            v-model:file-list="batchFileList"
            drag
            multiple
            :auto-upload="false"
            :limit="20"
            :accept="imageAccept"
            :on-change="validateBatchFile"
            :on-exceed="handleBatchExceed"
          >
            <el-icon class="steel-uploader__icon"><FolderAdd /></el-icon>
            <template v-if="batchFileList.length === 0">
              <div class="el-upload__text">拖入多张钢铁表面图片，或 <em>点击选择</em></div>
            </template>
            <template v-else>
              <div class="el-upload__text">拖入图片可新增，或选择操作</div>
              <div class="batch-upload-actions">
                <el-button type="primary" plain @click.stop="openBatchFilePicker()">新增图片</el-button>
                <el-button @click.stop="openBatchFilePicker(true)">重新选择</el-button>
              </div>
            </template>
          </el-upload>
          <div v-if="batchResult" class="batch-summary">
            <el-tag type="success">成功 {{ batchResult.successCount }}</el-tag>
            <el-tag type="danger">失败 {{ batchResult.failedCount }}</el-tag>
            <span>任务 {{ batchResult.taskId }}</span>
          </div>
          <el-table v-if="batchResult" :data="batchResult.items" stripe>
            <el-table-column prop="fileName" label="文件" min-width="220" />
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="row.status === 'completed' ? 'success' : 'danger'" size="small">
                  {{ row.status === "completed" ? "完成" : "失败" }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="totalObjects" label="缺陷数" width="100" />
            <el-table-column label="推理耗时" width="120">
              <template #default="{ row }">{{ row.inferenceTimeMs }} ms</template>
            </el-table-column>
            <el-table-column label="主要缺陷" min-width="180">
              <template #default="{ row }">
                {{ [...new Set(row.objects.map((item) => item.classNameCn))].join("、") }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <el-tab-pane label="视频检测" name="video">
        <div class="two-column-cards">
          <section class="workspace-card">
            <div class="section-title">
              <div><h3>短视频任务</h3><p>当前实现前端任务流程，后端接入后将按帧间隔抽帧检测。</p></div>
            </div>
            <el-upload
              v-model:file-list="videoFileList"
              drag
              :auto-upload="false"
              :limit="1"
              accept="video/mp4,video/webm"
            >
              <el-icon class="steel-uploader__icon"><VideoCamera /></el-icon>
              <div class="el-upload__text">选择 MP4 / WebM 短视频</div>
            </el-upload>
            <el-form label-position="top" class="video-options">
              <el-form-item label="抽帧间隔">
                <el-input-number v-model="videoFrameInterval" :min="1" :max="30" />
                <span class="field-suffix">帧</span>
              </el-form-item>
            </el-form>
            <el-button
              type="primary"
              :disabled="videoFileList.length === 0 || videoStatus === 'processing'"
              @click="startVideoTask"
            >创建视频检测任务</el-button>
          </section>
          <section class="workspace-card video-progress-card">
            <el-result
              v-if="videoStatus === 'idle'"
              icon="info"
              title="等待视频任务"
              sub-title="选择视频并创建任务后，这里将展示进度和关键帧摘要。"
            />
            <template v-else>
              <div class="video-progress-card__header">
                <div><span>模拟任务</span><strong>{{ videoTaskId }}</strong></div>
                <el-tag :type="videoStatus === 'completed' ? 'success' : 'warning'">
                  {{ videoStatus === "completed" ? "已完成" : "处理中" }}
                </el-tag>
              </div>
              <el-progress type="dashboard" :percentage="videoProgress" :status="videoStatus === 'completed' ? 'success' : ''" />
              <p>抽帧间隔：每 {{ videoFrameInterval }} 帧 · 已发现 {{ videoObjectCount }} 处候选缺陷</p>
            </template>
          </section>
        </div>
      </el-tab-pane>

      <el-tab-pane label="摄像头" name="camera">
        <div class="two-column-cards">
          <section class="workspace-card camera-stage">
            <video ref="cameraVideo" autoplay muted playsinline />
            <div v-if="cameraActive" class="camera-box camera-box--one"><span>划痕 91.4%</span></div>
            <div v-if="!cameraActive" class="camera-placeholder">
              <el-icon><VideoCamera /></el-icon><span>摄像头尚未开启</span>
            </div>
          </section>
          <section class="workspace-card camera-control">
            <div class="section-title"><div><h3>浏览器摄像头</h3><p>以 1–5 FPS 的最小演示方式发送帧，后端接口完成后接入 WebSocket。</p></div></div>
            <el-alert
              title="当前仅演示摄像头采集与检测框叠加，不代表真实模型推理。"
              type="warning"
              :closable="false"
              show-icon
            />
            <div class="camera-metrics">
              <div><span>状态</span><strong>{{ cameraActive ? "采集中" : "未启动" }}</strong></div>
              <div><span>目标帧率</span><strong>2 FPS</strong></div>
              <div><span>接口</span><strong>待接入 WS</strong></div>
            </div>
            <el-button v-if="!cameraActive" type="primary" :icon="VideoCamera" @click="startCamera">开启摄像头</el-button>
            <el-button v-else type="danger" plain @click="stopCamera">停止摄像头</el-button>
          </section>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import {
  Aim,
  Files,
  FolderAdd,
  Refresh,
  Setting,
  UploadFilled,
  VideoCamera,
} from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { detectBatchApi, detectSingleApi, getDetectionModelStatus } from "@/api/detection";
import { getModelsApi, getScenesApi, isFrontendBMockMode } from "@/api/models";
import ModulePageHeader from "@/components/common/ModulePageHeader.vue";
import DetectionResultPanel from "@/components/detection/DetectionResultPanel.vue";

const imageAccept = ".jpg,.jpeg,.png,.bmp,.tif,.tiff,.webp";
const activeMode = ref("single");
const scenes = ref([]);
const models = ref([]);
const form = reactive({ sceneId: "", modelId: "", confThreshold: 0.25, iouThreshold: 0.45 });

const singleFileList = ref([]);
const singleUploadRef = ref();
const singleFile = ref(null);
const singlePreviewUrl = ref("");
const singleResult = ref(null);
const singleLoading = ref(false);
const modelWarmupStatus = ref("loading");
const warmupError = ref("");
let warmupTimer;
let warmupRequesting = false;

const batchFileList = ref([]);
const batchUploadRef = ref();
const batchResult = ref(null);
const batchLoading = ref(false);

const videoFileList = ref([]);
const videoFrameInterval = ref(5);
const videoStatus = ref("idle");
const videoProgress = ref(0);
const videoTaskId = ref("");
const videoObjectCount = ref(0);
let videoTimer;

const cameraVideo = ref();
const cameraActive = ref(false);
let cameraStream;

function formatPercent(value) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`;
}

function validateImage(file) {
  const allowed = ["image/jpeg", "image/png", "image/bmp", "image/tiff", "image/webp"];
  if (!allowed.includes(file.type)) {
    ElMessage.warning("请选择 JPG、PNG、BMP、TIF 或 WebP 图片");
    return false;
  }
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.warning("单张图片不能超过 10 MB");
    return false;
  }
  return true;
}

function revokePreview() {
  if (singlePreviewUrl.value) URL.revokeObjectURL(singlePreviewUrl.value);
  singlePreviewUrl.value = "";
}

function handleSingleFile(uploadFile) {
  if (!validateImage(uploadFile.raw)) {
    singleFileList.value = [];
    return;
  }
  revokePreview();
  singleFile.value = uploadFile.raw;
  singlePreviewUrl.value = URL.createObjectURL(uploadFile.raw);
  singleResult.value = null;
}

function clearSingleFile() {
  singleFile.value = null;
  singleResult.value = null;
  revokePreview();
}

function handleSingleExceed(files) {
  const nextFile = files[0];
  if (!nextFile || !validateImage(nextFile)) return;

  singleUploadRef.value?.clearFiles();
  singleUploadRef.value?.handleStart(nextFile);
}

function validateBatchFile(uploadFile) {
  if (!validateImage(uploadFile.raw)) {
    batchFileList.value = batchFileList.value.filter((item) => item.uid !== uploadFile.uid);
  }
}

function handleBatchExceed() {
  ElMessage.info("批量模式一次最多选择 20 张图片");
}

function openBatchFilePicker(replace = false) {
  if (replace) {
    batchUploadRef.value?.clearFiles();
    batchResult.value = null;
  }
  batchUploadRef.value?.$el?.querySelector('input[type="file"]')?.click();
}

async function loadModels() {
  models.value = await getModelsApi(form.sceneId);
  form.modelId = models.value.find((model) => model.isDefault)?.id || models.value[0]?.id || "";
}

async function loadOptions() {
  try {
    scenes.value = await getScenesApi();
    form.sceneId = scenes.value[0]?.id || "";
    await loadModels();
  } catch {
    ElMessage.error("检测场景或模型列表加载失败");
  }
}

async function refreshModelWarmupStatus() {
  if (warmupRequesting || ["ready", "error"].includes(modelWarmupStatus.value)) return;
  warmupRequesting = true;
  try {
    const response = await getDetectionModelStatus();
    modelWarmupStatus.value = response.status || "loading";
    warmupError.value = response.error || "";
  } catch {
    modelWarmupStatus.value = "error";
    warmupError.value = "无法获取模型预热状态";
  } finally {
    warmupRequesting = false;
    clearTimeout(warmupTimer);
    if (modelWarmupStatus.value === "loading") {
      warmupTimer = window.setTimeout(refreshModelWarmupStatus, 1500);
    }
  }
}

async function startSingleDetection() {
  if (!singleFile.value) return;
  singleLoading.value = true;
  singleResult.value = null;
  try {
    singleResult.value = await detectSingleApi(singleFile.value, form);
    ElMessage.success("检测完成");
  } catch {
    ElMessage.error("检测失败，请检查模型服务后重试");
  } finally {
    singleLoading.value = false;
  }
}

async function startBatchDetection() {
  const files = batchFileList.value.map((item) => item.raw).filter(Boolean);
  if (!files.length) return;
  batchLoading.value = true;
  batchResult.value = null;
  try {
    batchResult.value = await detectBatchApi(files, form);
    ElMessage.success(`批量任务完成：${batchResult.value.successCount} 张成功`);
  } catch {
    ElMessage.error("批量检测失败");
  } finally {
    batchLoading.value = false;
  }
}

function startVideoTask() {
  clearInterval(videoTimer);
  videoStatus.value = "processing";
  videoProgress.value = 4;
  videoObjectCount.value = 0;
  videoTaskId.value = `mock-video-${Date.now()}`;
  videoTimer = window.setInterval(() => {
    videoProgress.value = Math.min(100, videoProgress.value + 8);
    videoObjectCount.value += videoProgress.value % 16 === 0 ? 1 : 0;
    if (videoProgress.value >= 100) {
      videoStatus.value = "completed";
      clearInterval(videoTimer);
    }
  }, 420);
}

async function startCamera() {
  if (!navigator.mediaDevices?.getUserMedia) {
    ElMessage.warning("当前浏览器不支持摄像头访问");
    return;
  }
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    cameraVideo.value.srcObject = cameraStream;
    cameraActive.value = true;
  } catch {
    ElMessage.error("无法访问摄像头，请检查浏览器权限");
  }
}

function stopCamera() {
  cameraStream?.getTracks().forEach((track) => track.stop());
  cameraStream = undefined;
  cameraActive.value = false;
  if (cameraVideo.value) cameraVideo.value.srcObject = null;
}

function resetCurrentMode() {
  if (activeMode.value === "single") {
    singleFileList.value = [];
    clearSingleFile();
  } else if (activeMode.value === "batch") {
    batchFileList.value = [];
    batchResult.value = null;
  } else if (activeMode.value === "video") {
    clearInterval(videoTimer);
    videoFileList.value = [];
    videoStatus.value = "idle";
    videoProgress.value = 0;
  } else {
    stopCamera();
  }
}

onMounted(() => {
  loadOptions();
  refreshModelWarmupStatus();
});
onBeforeUnmount(() => {
  revokePreview();
  clearInterval(videoTimer);
  stopCamera();
  clearTimeout(warmupTimer);
});
</script>

<style lang="scss" scoped>
.frontend-b-page { min-height: 100%; }
.mode-tabs :deep(.el-tabs__header) { margin-bottom: 18px; }
.mode-tabs :deep(.el-tabs__item) { height: 44px; font-weight: 600; }
.detection-layout { display: grid; grid-template-columns: minmax(290px, 0.78fr) minmax(480px, 1.55fr); gap: 18px; align-items: start; }
.control-card, .workspace-card { padding: 20px; border: 1px solid #e7ebf1; border-radius: 14px; background: #fff; box-shadow: 0 8px 24px rgba(28, 39, 60, 0.05); }
.section-title { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 18px; }
.section-title h3 { margin: 0; color: #1f2937; font-size: 16px; }
.section-title p { margin: 5px 0 0; color: $text-secondary; font-size: 12px; line-height: 1.55; }
.section-title > .el-icon { color: #2563eb; font-size: 22px; }
.section-title--inline { align-items: center; }
.full-width { width: 100%; }
.model-option { display: flex; align-items: center; justify-content: space-between; gap: 14px; }
.model-option small { color: $text-secondary; }
.slider-label { display: flex; width: 100%; justify-content: space-between; }
.slider-label b { color: #2563eb; }
.steel-uploader { margin-top: 4px; }
.model-warmup-alert { margin-bottom: 14px; }
.steel-uploader :deep(.el-upload-dragger) { padding: 26px 12px; border-radius: 11px; background: #f8fafc; }
.steel-uploader__icon { color: #2563eb; font-size: 36px; }
.batch-upload-actions { display: flex; justify-content: center; gap: 10px; }
.detect-button { width: 100%; margin-top: 18px; }
.workspace-card { min-height: 240px; }
.batch-summary { display: flex; align-items: center; gap: 9px; margin: 18px 0 12px; }
.batch-summary span { margin-left: auto; color: $text-secondary; font-size: 12px; }
.two-column-cards { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.video-options { margin-top: 18px; }
.field-suffix { margin-left: 8px; color: $text-secondary; }
.video-progress-card { display: grid; place-items: center; text-align: center; }
.video-progress-card__header { display: flex; width: 100%; align-items: center; justify-content: space-between; text-align: left; }
.video-progress-card__header span, .video-progress-card__header strong { display: block; }
.video-progress-card__header span { color: $text-secondary; font-size: 11px; }
.video-progress-card__header strong { margin-top: 4px; color: #172033; }
.video-progress-card p { color: $text-secondary; font-size: 12px; }
.camera-stage { position: relative; display: grid; min-height: 390px; place-items: center; overflow: hidden; padding: 0; background: #101828; }
.camera-stage video { width: 100%; height: 100%; min-height: 390px; object-fit: cover; }
.camera-placeholder { display: flex; flex-direction: column; align-items: center; gap: 10px; color: #98a2b3; }
.camera-placeholder .el-icon { font-size: 52px; }
.camera-box { position: absolute; top: 27%; left: 24%; width: 42%; height: 24%; border: 2px solid #fbbf24; }
.camera-box span { position: absolute; top: -24px; left: -2px; padding: 3px 7px; background: #fbbf24; color: #172033; font-size: 11px; font-weight: 700; }
.camera-control { display: flex; flex-direction: column; align-items: stretch; }
.camera-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 20px 0; }
.camera-metrics div { padding: 12px; border-radius: 9px; background: #f7f9fc; }
.camera-metrics span, .camera-metrics strong { display: block; }
.camera-metrics span { color: $text-secondary; font-size: 11px; }
.camera-metrics strong { margin-top: 4px; color: #172033; font-size: 14px; }
@media (max-width: 1080px) { .detection-layout, .two-column-cards { grid-template-columns: 1fr; } }
@media (max-width: 640px) { .camera-metrics { grid-template-columns: 1fr; } }
</style>
