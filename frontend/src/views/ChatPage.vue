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
import { streamAgentChat } from '@/api/agent'
import MessageList from '@/components/agent/MessageList.vue'
import ModelSelect from '@/components/agent/ModelSelect.vue'

const agentStore = useAgentStore()
const userStore = useUserStore()

const heroInput = ref('')
const chatInput = ref('')
const heroTextareaRef = ref(null)
const chatTextareaRef = ref(null)
const fileInputRef = ref(null)
const isDragover = ref(false)
const model = ref('gpt-4o-mini')
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

function handleAgentEvent(event) {
  if (event.type === 'text_delta') { agentStore.appendAssistantContent(event.content || '') }
  if (event.type === 'tool_start') { agentStore.setToolCall({ name: event.tool_name, status: 'running', input: event.input }) }
  if (event.type === 'tool_result') { agentStore.setToolCall({ name: event.tool_name, status: 'success', result: event.result }) }
  if (event.type === 'message_end') { agentStore.isStreaming = false }
  if (event.type === 'error') {
    agentStore.errorMessage = event.message || '智能体请求失败'
    agentStore.isStreaming = false
    ElMessage.error(agentStore.errorMessage)
  }
}

function doSend(text) {
  agentStore.addMessage({ role: 'assistant', content: '' })
  agentStore.isStreaming = true
  agentStore.currentToolCall = null
  agentStore.errorMessage = ''

  const formData = new FormData()
  formData.append('message', text)
  formData.append('session_id', agentStore.currentSessionId)
  formData.append('model', model.value)
  if (agentStore.selectedImage) { formData.append('image', agentStore.selectedImage) }

  agentStore.abortController = streamAgentChat(formData, {
    onMessage: handleAgentEvent,
    onDone: () => {
      agentStore.isStreaming = false
      agentStore.abortController = null
      agentStore.clearImage()
      saveCurrentSession()
    },
    onError: () => {
      agentStore.isStreaming = false
      agentStore.abortController = null
      ElMessage.error('智能体服务暂不可用')
    },
  })
}

function handleSend(text) {
  if (!text.trim() && !agentStore.selectedImage) return
  const imgUrl = agentStore.selectedImage ? URL.createObjectURL(agentStore.selectedImage) : ''
  agentStore.addMessage({ role: 'user', content: text, imagePreviewUrl: imgUrl })
  doSend(text)
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
