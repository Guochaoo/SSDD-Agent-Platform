<template>
  <div
    class="chat-page"
    :class="{ hero: !agentStore.hasMessages }"
    @dragenter.prevent="onDragEnter"
    @dragover.prevent="onDragOver"
    @dragleave.prevent="onDragLeave"
    @drop.prevent="onDrop"
  >
    <!-- ── Empty / Hero state ── -->
    <template v-if="!agentStore.hasMessages">
      <div class="hero-content">
        <h1 class="hero-greeting">{{ greeting }}</h1>

        <!-- Prompt card (hero) -->
        <div class="prompt-area">
          <div :class="['prompt-card', { dragover: isDragover }]">
            <textarea
              v-model="heroInput"
              class="prompt-textarea"
              placeholder="输入检测问题…"
              rows="1"
              :disabled="agentStore.isStreaming"
              @keydown.enter.exact.prevent="handleHeroSend"
              @input="autoResize"
              ref="heroTextareaRef"
            />

            <div v-if="agentStore.imagePreviewUrl" class="inline-preview">
              <img :src="agentStore.imagePreviewUrl" alt="preview" />
              <button class="remove-preview" @click="agentStore.clearImage()">
                <el-icon :size="12"><Close /></el-icon>
              </button>
            </div>

            <div class="card-footer">
              <div class="footer-left">
                <ModelSelect v-model="model" />
                <button class="footer-btn" title="上传图片" @click="triggerFileInput">
                  <Image :size="16" />
                </button>
                <input
                  ref="fileInputRef"
                  type="file"
                  accept="image/png,image/jpeg"
                  hidden
                  @change="onFileChange"
                />
              </div>

              <button
                class="send-btn"
                :disabled="!canSend"
                :title="agentStore.isStreaming ? '停止' : '发送'"
                @click="handleHeroSend"
              >
                <el-icon :size="16">
                  <ArrowUpStroke :size="16" v-if="!agentStore.isStreaming" />
                  <CloseBold v-else />
                </el-icon>
              </button>
            </div>
          </div>

          <div v-if="isDragover" class="drag-overlay">
            <el-icon :size="32"><UploadFilled /></el-icon>
            <span>释放以上传图片</span>
          </div>
        </div>

        <div class="quick-chips">
          <button
            v-for="chip in quickChips"
            :key="chip.label"
            class="chip"
            @click="handleChipClick(chip.label)"
          >
            <span>{{ chip.label }}</span>
          </button>
        </div>

        <QuickDetectBar
          :disabled="agentStore.isStreaming || isQuickDetecting"
          @single="handleQuickDetect('single')"
          @batch="handleQuickDetect('batch')"
          @zip="handleQuickDetect('zip')"
        />
      </div>
    </template>

    <!-- ── Normal chat state ── -->
    <template v-else>
      <MessageList
        :messages="agentStore.messages"
        :tool-call="agentStore.currentToolCall"
        :is-streaming="agentStore.isStreaming"
        @regenerate="handleRegenerate"
      />

      <!-- Prompt card (sticky bottom) -->
      <div class="chat-bottom">
        <QuickDetectBar
          class="chat-quick-detect"
          :disabled="agentStore.isStreaming || isQuickDetecting"
          @single="handleQuickDetect('single')"
          @batch="handleQuickDetect('batch')"
          @zip="handleQuickDetect('zip')"
        />

        <div :class="['prompt-card', { dragover: isDragover }]">
          <div v-if="agentStore.imagePreviewUrl" class="inline-preview">
            <img :src="agentStore.imagePreviewUrl" alt="preview" />
            <button class="remove-preview" @click="agentStore.clearImage()">
              <el-icon :size="12"><Close /></el-icon>
            </button>
          </div>

          <textarea
            v-model="chatInput"
            class="prompt-textarea"
            placeholder="输入检测问题…"
            rows="1"
            :disabled="agentStore.isStreaming"
            @keydown.enter.exact.prevent="handleChatSend"
            @input="autoResizeChat"
            ref="chatTextareaRef"
          />

          <div class="card-footer">
            <div class="footer-left">
              <ModelSelect v-model="model" />
              <button class="footer-btn" title="上传图片" @click="triggerFileInput">
                <Image :size="16" />
              </button>
              <input
                ref="fileInputRef"
                type="file"
                accept="image/png,image/jpeg"
                hidden
                @change="onFileChange"
              />
            </div>

            <button
              class="send-btn"
              :disabled="!canSendChat"
              @click="handleChatSend"
            >
              <el-icon :size="16">
                <ArrowUpStroke :size="16" v-if="!agentStore.isStreaming" />
                <CloseBold v-else />
              </el-icon>
            </button>
          </div>
        </div>

        <div v-if="isDragover" class="drag-overlay">
          <el-icon :size="32"><UploadFilled /></el-icon>
          <span>释放以上传图片</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { CloseBold, Close, UploadFilled } from '@element-plus/icons-vue'
import { Image, ArrowUpStroke } from '@boxicons/vue'
import { useAgentStore } from '@/stores/agent'
import { useUserStore } from '@/stores/user'
import { useLlmStore } from '@/stores/llm'
import {
  getAgentDetectionHistoryApi,
  searchAgentKnowledgeApi,
  streamAgentChat,
} from '@/api/agent'
import { detectBatchApi, detectSingleApi } from '@/api/detection'
import { getModelsApi, getScenesApi } from '@/api/models'
import MessageList from '@/components/agent/MessageList.vue'
import ModelSelect from '@/components/agent/ModelSelect.vue'
import QuickDetectBar from '@/components/agent/QuickDetectBar.vue'

const agentStore = useAgentStore()
const userStore = useUserStore()

const heroInput = ref('')
const chatInput = ref('')
const heroTextareaRef = ref(null)
const chatTextareaRef = ref(null)
const fileInputRef = ref(null)
const isDragover = ref(false)
const isQuickDetecting = ref(false)
const model = ref(useLlmStore().defaultModel)
let dragCounter = 0

const greeting = computed(() => {
  const hour = new Date().getHours()
  let t = '晚上好'
  if (hour < 12) t = '早上好'
  else if (hour < 18) t = '下午好'
  const name = userStore.username
  return name ? `${t}，${name}` : t
})

const canSend = computed(() => {
  return agentStore.isStreaming || heroInput.value.trim() || agentStore.selectedImage
})

const canSendChat = computed(() => {
  return agentStore.isStreaming || chatInput.value.trim() || agentStore.selectedImage
})

const quickChips = [
  { label: '分析这张钢铁表面的缺陷' },
  { label: '检测结果置信度是多少' },
  { label: '这是什么类型的表面缺陷' },
  { label: '如何区分划痕和裂纹' },
]

const quickDetectOptions = {
  confThreshold: 0.25,
  iouThreshold: 0.45,
}

function summarizeDetectionResult(result) {
  const objects = result?.objects || []
  if (!objects.length) {
    return '未检测到明显缺陷。建议结合生产场景复核阈值后再复检。'
  }

  const statMap = new Map()
  let maxConfidence = 0
  for (const item of objects) {
    const key = item.classNameCn || item.className || '未知缺陷'
    statMap.set(key, (statMap.get(key) || 0) + 1)
    maxConfidence = Math.max(maxConfidence, Number(item.confidence || 0))
  }

  const summary = Array.from(statMap.entries())
    .map(([name, count]) => `${name} ${count} 处`)
    .join('，')

  return `检测完成，共发现 ${objects.length} 处疑似缺陷（${summary}），最高置信度 ${(maxConfidence * 100).toFixed(1)}%。`
}

function onDragEnter() { dragCounter++; isDragover.value = true }
function onDragOver() {}
function onDragLeave() {
  dragCounter--
  if (dragCounter <= 0) { dragCounter = 0; isDragover.value = false }
}
function onDrop(e) {
  dragCounter = 0; isDragover.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) handleSelectedFile(file)
}

function triggerFileInput() { fileInputRef.value?.click() }

function onFileChange(e) {
  const file = e.target?.files?.[0]
  e.target.value = ''
  if (file) handleSelectedFile(file)
}

function handleSelectedFile(file) {
  const allowed = ['image/jpeg', 'image/png']
  if (!allowed.includes(file.type)) { ElMessage.error('仅支持 JPG 和 PNG 图片'); return }
  if (file.size > 10 * 1024 * 1024) { ElMessage.error('图片大小不能超过 10MB'); return }
  agentStore.setSelectedImage(file)
}

function autoResize() {
  const el = heroTextareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 160) + 'px'
}

function autoResizeChat() {
  const el = chatTextareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 160) + 'px'
}

function handleHeroSend() {
  if (agentStore.isStreaming) {
    agentStore.stopStreaming()
    return
  }
  const text = heroInput.value.trim()
  if (!text && !agentStore.selectedImage) return
  heroInput.value = ''
  handleSend(text)
}

function handleChatSend() {
  if (agentStore.isStreaming) {
    agentStore.stopStreaming()
    return
  }
  const text = chatInput.value.trim()
  if (!text && !agentStore.selectedImage) return
  chatInput.value = ''
  handleSend(text)
}

function handleChipClick(text) { handleSend(text) }

function chooseFiles({ accept, multiple }) {
  return new Promise((resolve) => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = accept
    input.multiple = multiple
    input.onchange = () => resolve(Array.from(input.files || []))
    input.click()
  })
}

async function handleQuickDetect(type) {
  if (agentStore.isStreaming || isQuickDetecting.value) return

  if (type === 'zip') {
    ElMessage.warning('当前后端暂未开放 ZIP 检测接口，请先使用批量图片检测')
    return
  }

  isQuickDetecting.value = true
  try {
    const files = await chooseFiles({
      accept: 'image/png,image/jpeg',
      multiple: type === 'batch',
    })
    if (!files.length) return

    const options = await getQuickDetectOptions()
    if (type === 'single') {
      await runSingleDetect(files[0], options)
    } else {
      await runBatchDetect(files, options)
    }
  } finally {
    isQuickDetecting.value = false
  }
}

async function getQuickDetectOptions() {
  const scenes = await getScenesApi()
  const scene = scenes[0]
  if (!scene) throw new Error('未找到可用检测场景')

  const models = await getModelsApi(scene.id)
  const model = models.find((item) => item.isDefault) || models[0]
  if (!model?.id) throw new Error('未找到可用检测模型')

  return { ...quickDetectOptions, modelId: model.id }
}

async function runSingleDetect(file, options) {
  const previewUrl = URL.createObjectURL(file)
  agentStore.addMessage({
    role: 'user',
    content: `[快捷单图检测] ${file.name}`,
    imagePreviewUrl: previewUrl,
  })
  agentStore.addMessage({
    role: 'assistant',
    content: '正在进行单图检测，请稍候……',
  })
  agentStore.setToolCall({ name: 'detect_single', status: 'running', input: { fileName: file.name } })

  const assistantMessage = agentStore.messages[agentStore.messages.length - 1]
  try {
    const result = await detectSingleApi(file, options)
    assistantMessage.content = `单图检测完成，共发现 ${result.totalObjects || 0} 个疑似缺陷。`
    assistantMessage.detectionResult = result
    assistantMessage.detectionPreviewUrl = previewUrl
    agentStore.setToolCall({ name: 'detect_single', status: 'success', result })
  } catch (error) {
    assistantMessage.content = '单图检测失败，请稍后重试。'
    agentStore.setToolCall({ name: 'detect_single', status: 'error', error: error?.message || '单图检测失败' })
    ElMessage.error(error?.response?.data?.detail || '单图检测失败')
  } finally {
    saveCurrentSession()
  }
}

async function runBatchDetect(files, options) {
  agentStore.addMessage({
    role: 'user',
    content: `[快捷批量检测] ${files.length} 张图片`,
  })
  agentStore.addMessage({
    role: 'assistant',
    content: '正在进行批量检测，请稍候……',
  })
  agentStore.setToolCall({ name: 'detect_batch', status: 'running', input: { count: files.length } })

  const assistantMessage = agentStore.messages[agentStore.messages.length - 1]
  try {
    const result = await detectBatchApi(files, options)
    const totalObjects = (result.items || []).reduce((sum, item) => sum + Number(item.totalObjects || 0), 0)
    assistantMessage.content = `批量检测完成，共处理 ${result.items?.length || files.length} 张图片，发现 ${totalObjects} 个疑似缺陷。`
    assistantMessage.detectionResult = result
    agentStore.setToolCall({ name: 'detect_batch', status: 'success', result })
  } catch (error) {
    assistantMessage.content = '批量检测失败，请稍后重试。'
    agentStore.setToolCall({ name: 'detect_batch', status: 'error', error: error?.message || '批量检测失败' })
    ElMessage.error(error?.response?.data?.detail || '批量检测失败')
  } finally {
    saveCurrentSession()
  }
}

function handleAgentEvent(event) {
  if (event.type === 'text_delta' || event.type === 'text_chunk') {
    const content = event.content || ''
    const lastMsg = agentStore.messages[agentStore.messages.length - 1]
    if (lastMsg?.detectionResult && isStaleMockDetectionText(content)) return
    agentStore.appendAssistantContent(content)
  }
  if (event.type === 'tool_start') {
    agentStore.setToolCall({
      id: event.tool_call_id || event.tool_name,
      name: event.tool_name,
      status: 'running',
      input: event.input,
    })
  }
  if (event.type === 'tool_result') {
    agentStore.setToolCall({
      id: event.tool_call_id || event.tool_name,
      name: event.tool_name,
      status: 'success',
      result: event.result,
    })
    attachToolResultCard(event.result)
  }
  if (event.type === 'message_end') {
    agentStore.isStreaming = false
    agentStore.setConnectionStatus('idle')
    const lastMsg = agentStore.messages[agentStore.messages.length - 1]
    if (lastMsg?.role === 'assistant') lastMsg.status = 'done'
    saveCurrentSession()
  }
  if (event.type === 'error') {
    agentStore.errorMessage = event.message || '智能体请求失败'
    agentStore.isStreaming = false
    agentStore.setConnectionStatus('error')
    agentStore.markLastAssistantError(agentStore.errorMessage)
    ElMessage.error(agentStore.errorMessage)
  }
}

function attachToolResultCard(rawResult) {
  let payload = rawResult
  if (typeof payload === 'string') {
    try { payload = JSON.parse(payload) } catch { return }
  }
  const result = payload?.result || payload
  if (!result || result.error) return
  const detections = result.detections || result.results?.flatMap((item) => item.detections || []) || []
  const assistantMessage = [...agentStore.messages].reverse().find((message) => message.role === 'assistant')
  const userMessage = [...agentStore.messages].reverse().find((message) => message.role === 'user')
  if (!assistantMessage) return
  assistantMessage.detectionResult = {
    taskId: `agent-${Date.now()}`,
    fileName: result.filename || '',
    originalImageUrl: result.image_url || result.originalImageUrl || '',
    annotatedImageUrl: result.annotated_image_url || result.annotatedImageUrl || '',
    totalObjects: result.total_objects ?? result.totalObjects ?? detections.length,
    totalImages: result.total_images ?? 1,
    inferenceTimeMs: Number(result.inference_time ?? result.inference_time_ms ?? result.inferenceTimeMs ?? 0),
    objects: detections.map((item, index) => ({
      id: String(index),
      className: item.class_name || item.className || 'unknown',
      classNameCn: item.class_name_cn || item.classNameCn || item.class_name || 'unknown',
      confidence: Number(item.confidence || 0),
      bbox: Array.isArray(item.bbox) ? item.bbox.map(Number) : [0, 0, 0, 0],
      bboxPercent: null,
    })),
  }
  assistantMessage.detectionPreviewUrl = userMessage?.imagePreviewUrl || ''
  assistantMessage.content = summarizeDetectionResult(assistantMessage.detectionResult)
  saveCurrentSession()
}

function isStaleMockDetectionText(content) {
  return /检测到\s*1\s*处疑似划痕缺陷|置信度约为\s*91|建议进一步检查该区域/.test(content)
}

function doSend(text) {
  agentStore.addMessage({ role: 'assistant', content: '', status: 'streaming', toolCalls: [] })
  agentStore.isStreaming = true
  agentStore.setConnectionStatus('connecting')
  agentStore.currentToolCall = null
  agentStore.errorMessage = ''

  const formData = new FormData()
  formData.append('message', buildContextualMessage(text))
  formData.append('session_id', agentStore.currentSessionId)
  formData.append('model', model.value)
  if (agentStore.selectedImage) { formData.append('image', agentStore.selectedImage) }

  agentStore.abortController = streamAgentChat(formData, {
    onMessage: handleAgentEvent,
    onRetry: ({ retryCount }) => {
      agentStore.reconnectCount = retryCount
      agentStore.setConnectionStatus('reconnecting')
      ElMessage.warning(`连接中断，正在第 ${retryCount} 次重连...`)
    },
    onDone: () => {
      agentStore.isStreaming = false
      agentStore.setConnectionStatus('idle')
      agentStore.abortController = null
      agentStore.clearImage()
      saveCurrentSession()
    },
    onError: (error) => {
      agentStore.isStreaming = false
      agentStore.setConnectionStatus('error')
      agentStore.abortController = null
      agentStore.markLastAssistantError(error?.message || '智能体服务暂不可用')
      ElMessage.error('智能体服务暂不可用')
    },
  })
}

function buildContextualMessage(text) {
  const context = buildLocalContext()
  if (!context) return text
  return `${text}\n\n[前端上下文]\n${context}`
}

function buildLocalContext() {
  const recentMessages = agentStore.messages
    .slice(-6)
    .map((message) => `${message.role}: ${message.content || ''}`.slice(0, 180))
    .join('\n')

  const latestDetection = [...agentStore.messages]
    .reverse()
    .find((message) => message.detectionResult)

  const parts = []
  if (recentMessages) parts.push(`最近对话:\n${recentMessages}`)
  if (latestDetection?.detectionResult) {
    parts.push(`最近检测结果: ${JSON.stringify({
      taskId: latestDetection.detectionResult.taskId,
      totalObjects: latestDetection.detectionResult.totalObjects,
      status: latestDetection.detectionResult.status,
    })}`)
  }
  return parts.join('\n')
}

function handleSend(text) {
  if (!text.trim() && !agentStore.selectedImage) return
  const imgUrl = agentStore.selectedImage ? URL.createObjectURL(agentStore.selectedImage) : ''
  agentStore.addMessage({ role: 'user', content: text, imagePreviewUrl: imgUrl })

  doSend(text)
}

async function runSingleDetectInChat(file, previewUrl) {
  agentStore.addMessage({
    role: 'assistant',
    content: '正在分析钢铁表面图像……',
  })
  agentStore.setToolCall({ name: 'detect_single', status: 'running', input: { fileName: file.name } })

  const assistantMessage = agentStore.messages[agentStore.messages.length - 1]
  try {
    const options = await getQuickDetectOptions()
    const result = await detectSingleApi(file, options)
    assistantMessage.content = summarizeDetectionResult(result)
    assistantMessage.detectionResult = result
    assistantMessage.detectionPreviewUrl = previewUrl
    agentStore.setToolCall({ name: 'detect_single', status: 'success', result })
  } catch (error) {
    assistantMessage.content = '检测失败，请检查后端服务、模型和鉴权状态后重试。'
    agentStore.setToolCall({ name: 'detect_single', status: 'error', error: error?.message || '检测失败' })
    ElMessage.error(error?.response?.data?.detail || '检测失败')
  } finally {
    agentStore.clearImage()
    saveCurrentSession()
  }
}

async function checkAgentToolContracts() {
  if (!localStorage.getItem('ssdd_token')) return

  try {
    await Promise.allSettled([
      getAgentDetectionHistoryApi({ page: 1, pageSize: 1 }),
      searchAgentKnowledgeApi('钢铁表面缺陷', { limit: 1 }),
    ])
  } catch {
    // Contract probes are best-effort and must not block chat.
  }
}

function handleRegenerate(message) {
  const idx = agentStore.messages.findIndex(m => m.id === message.id)
  if (idx <= 0) return
  const userMsg = agentStore.messages[idx - 1]
  if (userMsg?.role !== 'user') return
  agentStore.messages.splice(idx - 1, 2)
  agentStore.addMessage({ role: 'user', content: userMsg.content || '', imagePreviewUrl: userMsg.imagePreviewUrl })
  doSend(userMsg.content || '')
}

// ── Session history ──
function saveCurrentSession() {
  if (!agentStore.hasMessages) return
  agentStore.saveSession()
}

checkAgentToolContracts()
</script>

<style lang="scss" scoped>
.chat-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
  position: relative;

  &.hero {
    justify-content: center;
  }
}

/* ── Hero ── */
.hero-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px;
  gap: 28px;
}

.hero-greeting {
  font-size: 34px;
  font-weight: 700;
  color: #171717;
  letter-spacing: -0.5px;
  margin: 0;
  text-align: center;
}

/* ── Prompt area wrapper ── */
.prompt-area {
  width: 100%;
  max-width: 640px;
  position: relative;
}

/* ── Unified prompt card ── */
.prompt-card {
  background: #fff;
  border: 1px solid #e4e4e7;
  border-radius: 16px;
  padding: 8px 10px 4px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.04);
  transition: border-color 0.2s, box-shadow 0.2s;

  &:focus-within {
    border-color: #c4c4ca;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
  }

  &.dragover {
    border-color: #8F8AB0;
    border-style: dashed;
    background: #faf8fd;
  }
}

.prompt-textarea {
  width: 100%;
  border: 0;
  outline: 0;
  resize: none;
  font-size: 15px;
  line-height: 1.55;
  color: #171717;
  background: transparent;
  padding: 6px 4px;
  font-family: inherit;
  min-height: 28px;
  max-height: 160px;

  &::placeholder { color: #a3a3a3; }
  &:disabled { opacity: 0.5; }
}

/* ── Card footer ── */
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  padding-top: 4px;
  border-top: 1px solid #f2f2f4;
  margin-top: 4px;
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 2px;
}

/* ── Buttons ── */
.footer-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px; height: 20px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #737373;
  cursor: pointer;
  transition: all 0.15s;

  &:hover { background: #f1f1f0; color: #171717; }
}

.send-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px; height: 28px;
  border: 0;
  border-radius: 8px;
  background: #000000;
  color: #ffffff;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;

  &:hover:not(:disabled) { background: #262626; }
  &:disabled { opacity: 0.3; cursor: not-allowed; }
}

/* ── Inline image preview ── */
.inline-preview {
  position: relative;
  display: inline-block;
  margin: 4px 4px 0;

  img {
    width: 64px; height: 48px;
    border-radius: 8px;
    object-fit: cover;
    border: 1px solid #e8e8e8;
  }

  .remove-preview {
    position: absolute;
    top: -6px; right: -6px;
    width: 20px; height: 20px;
    border-radius: 50%;
    border: 0;
    background: #525252;
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    padding: 0;

    &:hover { background: #171717; }
  }
}

/* ── Drag overlay ── */
.drag-overlay {
  position: absolute;
  inset: 0;
  border-radius: 16px;
  background: rgba(250, 248, 253, 0.92);
  border: 2px dashed #8F8AB0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #8F8AB0;
  font-size: 14px;
  font-weight: 500;
  z-index: 10;
  pointer-events: none;
}

/* ── Quick chips ── */
.quick-chips {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  max-width: 640px;
}

.chat-quick-detect {
  max-width: 720px;
  margin: 0 auto 8px;
  justify-content: flex-start;
}

.chip {
  display: inline-flex;
  align-items: center;
  padding: 6px 14px;
  border: 1px solid #e0e0e0;
  border-radius: 20px;
  background: #fff;
  color: #525252;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;

  &:hover {
    border-color: #8F8AB0;
    color: #8F8AB0;
    background: #f8f7fb;
  }
}

/* ── Chat bottom (sticky input area) ── */
.chat-bottom {
  position: sticky;
  bottom: 0;
  padding: 12px 16px 16px;
  background: linear-gradient(to top, #fff 80%, transparent);
  z-index: 10;

  .prompt-card {
    max-width: 720px;
    margin: 0 auto;
  }
}
</style>
