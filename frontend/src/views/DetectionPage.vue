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
            <div class="el-upload__text">拖入多张钢铁表面图片，或 <em>点击选择</em></div>
          </el-upload>
          <el-divider content-position="left">或上传 ZIP 压缩包</el-divider>
          <div class="zip-upload-row">
            <el-upload
              v-model:file-list="zipFileList"
              :auto-upload="false"
              :limit="1"
              accept=".zip,application/zip"
              :on-change="validateZipFile"
            >
              <el-button :icon="FolderAdd">选择 ZIP</el-button>
            </el-upload>
            <span>最多 20 张图片，ZIP 不超过 50 MB</span>
            <el-button
              type="primary"
              :loading="zipLoading"
              :disabled="zipFileList.length === 0 || !form.modelId"
              @click="startZipDetection"
            >检测 ZIP</el-button>
          </div>
          <div v-if="batchResult" class="batch-summary">
            <el-tag type="info">{{ batchResult.source === "zip" ? "ZIP" : "多图" }}</el-tag>
            <span v-if="batchResult.source === 'zip'">{{ batchResult.zipFilename }} · {{ batchResult.totalImagesInZip }} 张</span>
            <el-tag type="success">成功 {{ batchResult.successCount }}</el-tag>
            <el-tag type="danger">失败 {{ batchResult.failedCount }}</el-tag>
            <span>任务 {{ batchResult.taskId }}</span>
          </div>
          <el-table v-if="batchResult" :data="batchResult.items" stripe row-key="fileName">
            <el-table-column type="expand">
              <template #default="{ row }">
                <div v-if="row.status === 'completed'" class="batch-detail">
                  <div class="batch-image-card">
                    <span>原图</span>
                    <el-image :src="row.originalImageUrl" :preview-src-list="[row.originalImageUrl]" fit="contain" preview-teleported />
                  </div>
                  <div class="batch-image-card batch-image-card--annotated">
                    <span>检测框结果</span>
                    <el-image :src="row.annotatedImageUrl" :preview-src-list="[row.annotatedImageUrl]" fit="contain" preview-teleported />
                  </div>
                  <el-table :data="row.objects" size="small" class="batch-object-table">
                    <el-table-column prop="classNameCn" label="缺陷类别" min-width="100" />
                    <el-table-column label="置信度" width="90">
                      <template #default="scope">{{ (scope.row.confidence * 100).toFixed(1) }}%</template>
                    </el-table-column>
                    <el-table-column label="bbox" min-width="180">
                      <template #default="scope">[{{ scope.row.bbox.map((value) => Math.round(value)).join(", ") }}]</template>
                    </el-table-column>
                  </el-table>
                </div>
                <el-alert v-else :title="row.error || '该图片检测失败'" type="error" :closable="false" />
              </template>
            </el-table-column>
            <el-table-column label="检测框预览" width="150">
              <template #default="{ row }">
                <el-image v-if="row.annotatedImageUrl" class="batch-thumb" :src="row.annotatedImageUrl" :preview-src-list="[row.annotatedImageUrl]" fit="cover" preview-teleported />
                <span v-else>无</span>
              </template>
            </el-table-column>
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
              <div><h3>短视频任务</h3><p>使用当前选择的本地模型抽帧检测，展示关键帧标注图和完整标注视频。</p></div>
            </div>
            <el-upload
              v-model:file-list="videoFileList"
              drag
              :auto-upload="false"
              :limit="1"
              accept=".mp4,.avi,.mov,.mkv,.wmv,.flv"
              :on-change="validateVideoFile"
            >
              <el-icon class="steel-uploader__icon"><VideoCamera /></el-icon>
              <div class="el-upload__text">选择 MP4 / AVI / MOV / MKV 短视频</div>
            </el-upload>
            <el-form label-position="top" class="video-options">
              <el-form-item label="抽帧间隔">
                <el-input-number v-model="videoFrameInterval" :min="1" :max="30" />
                <span class="field-suffix">帧</span>
              </el-form-item>
              <el-form-item label="最多关键帧">
                <el-input-number v-model="videoMaxFrames" :min="1" :max="100" />
                <span class="field-suffix">帧</span>
              </el-form-item>
            </el-form>
            <el-button
              type="primary"
              :loading="videoStatus === 'processing'"
              :disabled="videoFileList.length === 0 || videoStatus === 'processing' || !form.modelId"
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
                <div><span>视频任务</span><strong>{{ videoTaskId }}</strong></div>
                <el-tag :type="videoStatus === 'completed' ? 'success' : videoStatus === 'failed' ? 'danger' : 'warning'">
                  {{ videoStatus === "completed" ? "已完成" : videoStatus === "failed" ? "失败" : "处理中" }}
                </el-tag>
              </div>
              <el-progress type="dashboard" :percentage="videoProgress" :status="videoStatus === 'completed' ? 'success' : videoStatus === 'failed' ? 'exception' : ''" />
              <p>{{ videoMessage }}</p>
              <template v-if="videoResult">
                <div class="video-summary">
                  <el-tag type="primary">本地模型 {{ videoResult.model?.name || "未知" }}</el-tag>
                  <el-tag>时长 {{ videoResult.duration_seconds }}s</el-tag>
                  <el-tag>FPS {{ videoResult.fps }}</el-tag>
                  <el-tag>分辨率 {{ videoResult.video_resolution.width }}×{{ videoResult.video_resolution.height }}</el-tag>
                  <el-tag type="success">目标 {{ videoResult.total_objects }}</el-tag>
                </div>
                <video v-if="videoResult.annotated_video_url" class="annotated-video" :src="videoResult.annotated_video_url" controls preload="metadata" />
                <div class="class-counts">
                  <el-tag v-for="(count, name) in videoResult.class_counts" :key="name" effect="plain">{{ name }} · {{ count }}</el-tag>
                </div>
                <div v-if="thumbnailFrames.length" class="key-frame-grid">
                  <figure v-for="frame in thumbnailFrames" :key="frame.frame_index">
                    <el-image :src="`data:image/jpeg;base64,${frame.annotated_image_base64}`" :preview-src-list="thumbnailFrameUrls" fit="cover" preview-teleported />
                    <figcaption>
                      <strong>{{ frame.timestamp }}s · {{ frame.object_count }} 个目标</strong>
                      <span v-for="item in frame.detections" :key="`${frame.frame_index}-${item.class_id}-${item.bbox.join('-')}`">{{ item.class_name_cn }} {{ (item.confidence * 100).toFixed(1) }}%</span>
                    </figcaption>
                  </figure>
                </div>
                <el-empty v-else description="没有可展示的关键帧" :image-size="72" />
              </template>
            </template>
          </section>
        </div>
      </el-tab-pane>

      <el-tab-pane label="摄像头" name="camera">
        <div class="two-column-cards">
          <section class="workspace-card camera-stage">
            <video ref="cameraVideo" autoplay muted playsinline class="camera-source" />
            <canvas ref="cameraCanvas" class="camera-canvas" width="640" height="480" />
            <div v-if="!cameraActive" class="camera-placeholder">
              <el-icon><VideoCamera /></el-icon><span>摄像头尚未开启</span>
            </div>
          </section>
          <section class="workspace-card camera-control">
            <div class="section-title"><div><h3>浏览器摄像头</h3><p>当前帧经 WebSocket 发送到本地 YOLO 模型，返回真实标注画面。</p></div></div>
            <el-radio-group v-model="cameraMode" :disabled="cameraActive || cameraConnecting" class="camera-mode">
              <el-radio-button value="cpu">CPU 节能</el-radio-button>
              <el-radio-button value="gpu">GPU 加速</el-radio-button>
            </el-radio-group>
            <div class="camera-metrics">
              <div><span>状态</span><strong>{{ cameraConnecting ? "连接中" : cameraActive ? "运行中" : "未启动" }}</strong></div>
              <div><span>本地模型</span><strong>{{ cameraModelName || selectedModelName }}</strong></div>
              <div><span>实时帧率</span><strong>{{ cameraFps }} FPS</strong></div>
              <div><span>推理耗时</span><strong>{{ cameraInferenceTime }} ms</strong></div>
              <div><span>已处理帧</span><strong>{{ cameraFrameCount }}</strong></div>
              <div><span>当前目标</span><strong>{{ cameraDetections.length }}</strong></div>
            </div>
            <el-table v-if="cameraDetections.length" :data="cameraDetections" size="small" max-height="180">
              <el-table-column prop="class_name_cn" label="缺陷" min-width="100" />
              <el-table-column label="置信度" width="90"><template #default="{ row }">{{ (row.confidence * 100).toFixed(1) }}%</template></el-table-column>
              <el-table-column label="bbox" min-width="180"><template #default="{ row }">[{{ row.bbox.map((value) => Math.round(value)).join(", ") }}]</template></el-table-column>
            </el-table>
            <el-button v-if="!cameraActive" type="primary" :icon="VideoCamera" :loading="cameraConnecting" :disabled="!form.modelId" @click="startCamera">开启摄像头</el-button>
            <el-button v-else type="danger" plain native-type="button" @click.stop.prevent="stopCamera">停止摄像头</el-button>
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
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { detectBatchApi, detectSingleApi, detectVideoApi, detectZipApi, getVideoStatusApi } from "@/api/detection";
import { getModelsApi, getScenesApi, isFrontendBMockMode } from "@/api/models";
import { createCameraWs } from "@/utils/cameraWs";
import ModulePageHeader from "@/components/common/ModulePageHeader.vue";
import DetectionResultPanel from "@/components/detection/DetectionResultPanel.vue";

const imageAccept = ".jpg,.jpeg,.png,.bmp,.tif,.tiff";
const activeMode = ref("single");
const scenes = ref([]);
const models = ref([]);
const form = reactive({ sceneId: "", modelId: "", confThreshold: 0.25, iouThreshold: 0.45 });

const singleFileList = ref([]);
const singleFile = ref(null);
const singlePreviewUrl = ref("");
const singleResult = ref(null);
const singleLoading = ref(false);

const batchFileList = ref([]);
const batchResult = ref(null);
const batchLoading = ref(false);
const zipFileList = ref([]);
const zipLoading = ref(false);

const videoFileList = ref([]);
const videoFrameInterval = ref(5);
const videoMaxFrames = ref(50);
const videoStatus = ref("idle");
const videoProgress = ref(0);
const videoTaskId = ref("");
const videoMessage = ref("");
const videoResult = ref(null);
let videoPollTimer;
const thumbnailFrames = computed(() =>
  (videoResult.value?.key_frames ?? []).filter((frame) => frame.annotated_image_base64).slice(0, 6),
);

const cameraVideo = ref();
const cameraCanvas = ref();
const cameraActive = ref(false);
const cameraConnecting = ref(false);
const cameraMode = ref("cpu");
const cameraFps = ref(0);
const cameraFrameCount = ref(0);
const cameraInferenceTime = ref(0);
const cameraDetections = ref([]);
let cameraStream;
let cameraWs;

function formatPercent(value) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`;
}

function validateImage(file) {
  const allowed = ["image/jpeg", "image/png", "image/bmp", "image/tiff"];
  if (!allowed.includes(file.type)) {
    ElMessage.warning("请选择 JPG、PNG、BMP 或 TIF 图片");
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

function handleSingleExceed() {
  ElMessage.info("单图模式一次只能选择一张图片，请先移除当前图片");
}

function validateBatchFile(uploadFile) {
  if (!validateImage(uploadFile.raw)) {
    batchFileList.value = batchFileList.value.filter((item) => item.uid !== uploadFile.uid);
  }
}

function handleBatchExceed() {
  ElMessage.info("批量模式一次最多选择 20 张图片");
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

function validateZipFile(uploadFile) {
  const file = uploadFile.raw;
  if (!file?.name.toLowerCase().endsWith(".zip")) {
    ElMessage.warning("请选择 ZIP 压缩包");
    zipFileList.value = [];
    return;
  }
  if (file.size > 50 * 1024 * 1024) {
    ElMessage.warning("ZIP 文件不能超过 50 MB");
    zipFileList.value = [];
  }
}

async function startZipDetection() {
  const file = zipFileList.value[0]?.raw;
  if (!file) return;
  zipLoading.value = true;
  batchResult.value = null;
  try {
    batchResult.value = await detectZipApi(file, form);
    ElMessage.success(`ZIP 检测完成：${batchResult.value.successCount} 张成功`);
  } catch {
    ElMessage.error("ZIP 检测失败");
  } finally {
    zipLoading.value = false;
  }
}

function validateVideoFile(uploadFile) {
  if (uploadFile.raw?.size > 50 * 1024 * 1024) {
    ElMessage.warning("视频文件不能超过 50 MB");
    videoFileList.value = [];
  }
}

async function pollVideoStatus() {
  try {
    const data = await getVideoStatusApi(videoTaskId.value);
    videoStatus.value = data.status;
    videoProgress.value = Math.round(data.progress ?? 0);
    videoMessage.value = data.message ?? "视频处理中...";
    if (data.status === "completed") {
      videoResult.value = data.result ?? null;
      clearInterval(videoPollTimer);
      ElMessage.success("视频检测完成");
    } else if (data.status === "failed") {
      clearInterval(videoPollTimer);
      ElMessage.error(data.message || "视频检测失败");
    }
  } catch {
    clearInterval(videoPollTimer);
    videoStatus.value = "failed";
  }
}

async function startVideoTask() {
  const file = videoFileList.value[0]?.raw;
  if (!file) return;
  clearInterval(videoPollTimer);
  videoStatus.value = "processing";
  videoProgress.value = 0;
  videoMessage.value = "正在上传视频...";
  videoResult.value = null;
  try {
    const data = await detectVideoApi(file, {
      ...form,
      frameSampleRate: videoFrameInterval.value,
      maxFrames: videoMaxFrames.value,
    });
    videoTaskId.value = String(data.task_id);
    videoMessage.value = data.message;
    videoPollTimer = window.setInterval(pollVideoStatus, 1500);
    await pollVideoStatus();
  } catch {
    videoStatus.value = "failed";
    videoMessage.value = "视频上传或任务创建失败";
  }
}

async function startCamera() {
  if (!navigator.mediaDevices?.getUserMedia) {
    ElMessage.warning("当前浏览器不支持摄像头访问");
    return;
  }
  try {
    cameraConnecting.value = true;
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
      audio: false,
    });
    cameraVideo.value.srcObject = cameraStream;
    await cameraVideo.value.play();
    cameraCanvas.value.width = cameraVideo.value.videoWidth || 640;
    cameraCanvas.value.height = cameraVideo.value.videoHeight || 480;
    cameraWs = createCameraWs({
      mode: cameraMode.value,
      conf: form.confThreshold,
      iou: form.iouThreshold,
      modelId: form.modelId,
      onConfigOk: () => {
        cameraConnecting.value = false;
        requestAnimationFrame(sendCameraFrame);
      },
      onResult: handleCameraResult,
      onFrameSkipped: (data) => window.setTimeout(sendCameraFrame, data.retry_after_ms ?? 300),
      onError: (message) => {
        cameraConnecting.value = false;
        ElMessage.error(message);
      },
      onClose: () => { cameraConnecting.value = false; },
    });
    cameraWs.connect();
    cameraActive.value = true;
  } catch {
    cameraConnecting.value = false;
    ElMessage.error("无法访问摄像头，请检查浏览器权限");
  }
}

function sendCameraFrame() {
  if (!cameraActive.value || !cameraWs?.isConnected || cameraVideo.value?.readyState < 2) return;
  const size = cameraMode.value === "cpu" ? 416 : 640;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const context = canvas.getContext("2d");
  const width = cameraVideo.value.videoWidth;
  const height = cameraVideo.value.videoHeight;
  const scale = Math.min(size / width, size / height);
  context.fillStyle = "#000";
  context.fillRect(0, 0, size, size);
  context.drawImage(cameraVideo.value, (size - width * scale) / 2, (size - height * scale) / 2, width * scale, height * scale);
  cameraWs.sendFrame(canvas.toDataURL("image/jpeg", 0.6).split(",")[1]);
}

function handleCameraResult(data) {
  cameraFps.value = data.fps ?? 0;
  cameraFrameCount.value = data.frame_count ?? 0;
  cameraInferenceTime.value = data.inference_time ?? 0;
  cameraDetections.value = data.detections ?? [];
  const image = new Image();
  image.onload = () => {
    const context = cameraCanvas.value?.getContext("2d");
    if (!context) return;
    cameraCanvas.value.width = image.width;
    cameraCanvas.value.height = image.height;
    context.drawImage(image, 0, 0);
    requestAnimationFrame(sendCameraFrame);
  };
  image.src = `data:image/jpeg;base64,${data.annotated_frame}`;
}

function stopCamera() {
  cameraWs?.close();
  cameraWs = undefined;
  cameraStream?.getTracks().forEach((track) => track.stop());
  cameraStream = undefined;
  cameraActive.value = false;
  cameraConnecting.value = false;
  cameraFps.value = 0;
  cameraFrameCount.value = 0;
  cameraInferenceTime.value = 0;
  cameraDetections.value = [];
  if (cameraVideo.value) cameraVideo.value.srcObject = null;
  cameraCanvas.value?.getContext("2d")?.clearRect(0, 0, cameraCanvas.value.width, cameraCanvas.value.height);
}

function resetCurrentMode() {
  if (activeMode.value === "single") {
    singleFileList.value = [];
    clearSingleFile();
  } else if (activeMode.value === "batch") {
    batchFileList.value = [];
    zipFileList.value = [];
    batchResult.value = null;
  } else if (activeMode.value === "video") {
    clearInterval(videoPollTimer);
    videoFileList.value = [];
    videoStatus.value = "idle";
    videoProgress.value = 0;
    videoResult.value = null;
    videoMessage.value = "";
  } else {
    stopCamera();
  }
}

onMounted(loadOptions);
onBeforeUnmount(() => {
  revokePreview();
  clearInterval(videoPollTimer);
  stopCamera();
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
.steel-uploader :deep(.el-upload-dragger) { padding: 26px 12px; border-radius: 11px; background: #f8fafc; }
.steel-uploader__icon { color: #2563eb; font-size: 36px; }
.detect-button { width: 100%; margin-top: 18px; }
.workspace-card { min-height: 240px; }
.batch-summary { display: flex; align-items: center; gap: 9px; margin: 18px 0 12px; }
.batch-summary span { color: $text-secondary; font-size: 12px; }
.batch-summary > span:last-child { margin-left: auto; }
.zip-upload-row { display: flex; align-items: center; gap: 12px; }
.zip-upload-row > span { flex: 1; color: $text-secondary; font-size: 12px; }
.batch-thumb { width: 118px; height: 74px; border-radius: 7px; background: #101828; }
.batch-detail { display: grid; grid-template-columns: minmax(220px, 1fr) minmax(220px, 1fr); gap: 14px; padding: 12px 18px; }
.batch-image-card { overflow: hidden; border: 1px solid #e7ebf1; border-radius: 10px; background: #f8fafc; }
.batch-image-card > span { display: block; padding: 8px 10px; color: $text-secondary; font-size: 12px; font-weight: 600; }
.batch-image-card :deep(.el-image) { display: block; width: 100%; height: 260px; background: #101828; }
.batch-image-card--annotated { border-color: #bfdbfe; }
.batch-object-table { grid-column: 1 / -1; }
.two-column-cards { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.video-options { margin-top: 18px; }
.field-suffix { margin-left: 8px; color: $text-secondary; }
.video-progress-card { display: grid; place-items: center; text-align: center; }
.video-progress-card__header { display: flex; width: 100%; align-items: center; justify-content: space-between; text-align: left; }
.video-progress-card__header span, .video-progress-card__header strong { display: block; }
.video-progress-card__header span { color: $text-secondary; font-size: 11px; }
.video-progress-card__header strong { margin-top: 4px; color: #172033; }
.video-progress-card p { color: $text-secondary; font-size: 12px; }
.video-summary, .class-counts { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin: 12px 0; }
.annotated-video { width: 100%; max-height: 300px; border-radius: 10px; background: #101828; }
.key-frame-grid { display: grid; width: 100%; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-top: 12px; }
.key-frame-grid figure { margin: 0; overflow: hidden; border: 1px solid #e7ebf1; border-radius: 8px; background: #f8fafc; }
.key-frame-grid :deep(.el-image) { display: block; width: 100%; aspect-ratio: 16 / 9; background: #101828; }
.key-frame-grid figcaption { display: flex; flex-direction: column; gap: 3px; padding: 7px; color: $text-secondary; font-size: 11px; }
.camera-stage { position: relative; display: grid; min-height: 390px; place-items: center; overflow: hidden; padding: 0; background: #101828; }
.camera-source { position: absolute; width: 1px; height: 1px; opacity: 0; }
.camera-canvas { display: block; width: 100%; min-height: 390px; object-fit: contain; }
.camera-placeholder { display: flex; flex-direction: column; align-items: center; gap: 10px; color: #98a2b3; }
.camera-placeholder .el-icon { font-size: 52px; }
.camera-control { display: flex; flex-direction: column; align-items: stretch; }
.camera-mode { margin-bottom: 4px; }
.camera-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 16px 0; }
.camera-metrics div { padding: 12px; border-radius: 9px; background: #f7f9fc; }
.camera-metrics span, .camera-metrics strong { display: block; }
.camera-metrics span { color: $text-secondary; font-size: 11px; }
.camera-metrics strong { margin-top: 4px; color: #172033; font-size: 14px; }
@media (max-width: 1080px) { .detection-layout, .two-column-cards, .batch-detail { grid-template-columns: 1fr; } .batch-object-table { grid-column: 1; } }
@media (max-width: 640px) { .camera-metrics { grid-template-columns: 1fr; } .zip-upload-row { align-items: stretch; flex-direction: column; } }
</style>
