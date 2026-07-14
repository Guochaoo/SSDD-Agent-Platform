<template>
  <!-- User message: subtle, right-aligned chip -->
  <div v-if="message.role === 'user'" class="user-msg">
    <img
      v-if="message.imagePreviewUrl"
      :src="message.imagePreviewUrl"
      class="user-image"
      alt="上传图片"
    />
    <span class="user-text">{{ message.content }}</span>
  </div>

  <!-- Assistant message: centered, prominent, no avatar -->
  <div v-else class="assistant-msg">
    <div class="assistant-content">
      <div class="markdown-body" v-html="renderedContent" />
      <DetectionResultCard
        v-if="message.detectionResult"
        :result="message.detectionResult"
        :preview-url="message.detectionPreviewUrl"
      />

      <div v-if="message.toolCalls?.length" class="tool-trace">
        <div
          v-for="tool in message.toolCalls"
          :key="tool.id || tool.name || tool.tool_name"
          class="tool-trace-item"
        >
          <span class="tool-name">{{ getToolName(tool) }}</span>
          <el-tag :type="getToolTag(tool)" size="small">{{ getToolStatus(tool) }}</el-tag>
        </div>
      </div>

      <el-alert
        v-if="message.status === 'error'"
        :title="message.errorMessage || '智能体响应失败，请重试'"
        type="error"
        :closable="false"
        show-icon
        class="message-error"
      />
    </div>

    <div v-if="!isLastStreaming && message.content" class="msg-footer">
      <button class="footer-btn" :class="{ copied }" title="复制" @click="handleCopy">
        <el-icon :size="14"><DocumentCopy v-if="!copied" /><Check v-else /></el-icon>
        <span>{{ copied ? '已复制' : '复制' }}</span>
      </button>
      <button class="footer-btn" title="重新生成" @click="$emit('regenerate', message)">
        <el-icon :size="14"><Refresh /></el-icon>
        <span>重新生成</span>
      </button>
      <span class="msg-time">{{ formattedTime }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { DocumentCopy, Check, Refresh } from '@element-plus/icons-vue'
import { renderMarkdown } from '@/utils/markdown'
import DetectionResultCard from './DetectionResultCard.vue'

const props = defineProps({
  message: { type: Object, required: true },
  isLastStreaming: { type: Boolean, default: false },
})

defineEmits(['regenerate'])

const copied = ref(false)
let copyTimer = null

const renderedContent = computed(() => {
  return renderMarkdown(props.message.content || '')
})

const formattedTime = computed(() => {
  if (!props.message.createdAt) return ''
  return new Date(props.message.createdAt).toLocaleTimeString(undefined, {
    hour: 'numeric', minute: '2-digit',
  })
})

function handleCopy() {
  const text = props.message.content || ''
  navigator.clipboard.writeText(text).then(() => {
    copied.value = true
    clearTimeout(copyTimer)
    copyTimer = setTimeout(() => { copied.value = false }, 2000)
  }).catch(() => {})
}

function getToolName(tool) {
  const name = tool.name || tool.tool_name || 'tool'
  const map = {
    detect_single: '单图检测工具',
    detect_batch: '批量检测工具',
    detection_tool: '缺陷检测工具',
    history_query: '检测历史工具',
    knowledge_search: '知识库检索工具',
  }
  return map[name] || name
}

function getToolStatus(tool) {
  const map = {
    running: '运行中',
    success: '成功',
    error: '失败',
  }
  return map[tool.status] || '已调用'
}

function getToolTag(tool) {
  if (tool.status === 'success') return 'success'
  if (tool.status === 'error') return 'danger'
  return 'warning'
}
</script>

<style lang="scss" scoped>
/* ── User message: subtle right-aligned chip, same max-width as assistant ── */
.user-msg {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  width: 100%;
  max-width: 780px;
  margin: 0 auto 4px;
  padding: 6px 24px;
}

.user-image {
  max-width: 120px;
  max-height: 80px;
  border-radius: 8px;
  object-fit: cover;
}

.user-text {
  display: inline-block;
  max-width: 70%;
  padding: 6px 14px;
  background: #f1f1f0;
  color: #525252;
  border-radius: 20px;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

/* ── Assistant message: centered, prominent ── */
.assistant-msg {
  padding: 16px 24px;
  margin-bottom: 8px;
}

.assistant-content {
  max-width: 780px;
  margin: 0 auto;

  .markdown-body {
    font-size: 15px;
    line-height: 1.75;
    color: #171717;

    :deep(p) {
      margin: 0 0 12px;
    }
    :deep(p:last-child) {
      margin-bottom: 0;
    }
    :deep(h1), :deep(h2), :deep(h3), :deep(h4) {
      margin: 20px 0 10px;
      font-weight: 600;
      color: #171717;
    }
    :deep(h1) { font-size: 1.4em; }
    :deep(h2) { font-size: 1.2em; }
    :deep(h3) { font-size: 1.1em; }
    :deep(ul), :deep(ol) {
      padding-left: 20px;
      margin: 8px 0;
    }
    :deep(li) {
      margin: 4px 0;
    }
    :deep(code) {
      background: #f2f3f5;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 13px;
      font-family: 'SF Mono', 'Fira Code', monospace;
    }
    :deep(pre) {
      background: #f8f9fa;
      border: 1px solid #ebebeb;
      padding: 14px 16px;
      border-radius: 10px;
      overflow-x: auto;
      margin: 12px 0;
    }
    :deep(pre code) {
      background: transparent;
      padding: 0;
    }
    :deep(blockquote) {
      border-left: 3px solid #8F8AB0;
      margin: 12px 0;
      padding: 4px 14px;
      color: #737373;
    }
    :deep(table) {
      width: 100%;
      border-collapse: collapse;
      margin: 12px 0;
    }
    :deep(th), :deep(td) {
      border: 1px solid #e8e8e8;
      padding: 8px 12px;
      text-align: left;
      font-size: 14px;
    }
    :deep(th) {
      background: #f8f9fa;
      font-weight: 600;
    }
  }
}
/* ── Footer: actions ── */
.msg-footer {
  max-width: 780px;
  margin: 8px auto 0;
  display: flex;
  align-items: center;
  gap: 4px;
}

.footer-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #a3a3a3;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    color: #525252;
    background: #f1f1f0;
  }

  &.copied {
    color: #67c23a;
  }
}

.msg-time {
  margin-left: 4px;
  font-size: 11px;
  color: #c0c4cc;
}

.tool-trace {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 12px;
  padding: 10px 12px;
  border: 1px solid #f0f0f0;
  border-radius: 10px;
  background: #fafafa;
}

.tool-trace-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
}

.tool-name {
  color: #525252;
}

.message-error {
  margin-top: 12px;
}
</style>
