<template>
  <div class="chat-interface">
    <MessageList
      :messages="agentStore.messages"
      :tool-call="agentStore.currentToolCall"
    />

    <ImageAttachment
      :preview-url="agentStore.imagePreviewUrl"
      @select="agentStore.setSelectedImage"
      @remove="agentStore.clearImage"
    />

    <ChatInput
      :loading="agentStore.isStreaming"
      @send="handleSend"
      @stop="agentStore.stopStreaming"
    />
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { useAgentStore } from '@/stores/agent'
import { streamAgentChat } from '@/api/agent'
import MessageList from './MessageList.vue'
import ImageAttachment from './ImageAttachment.vue'
import ChatInput from './ChatInput.vue'

const agentStore = useAgentStore()

function handleAgentEvent(event) {
  if (event.type === 'text_delta') {
    agentStore.appendAssistantContent(event.content || '')
  }

  if (event.type === 'tool_start') {
    agentStore.setToolCall({
      name: event.tool_name,
      status: 'running',
      input: event.input,
    })
  }

  if (event.type === 'tool_result') {
    agentStore.setToolCall({
      name: event.tool_name,
      status: 'success',
      result: event.result,
    })
  }

  if (event.type === 'message_end') {
    agentStore.isStreaming = false
  }

  if (event.type === 'error') {
    agentStore.errorMessage = event.message || '智能体请求失败'
    agentStore.isStreaming = false
    ElMessage.error(agentStore.errorMessage)
  }
}

function handleSend(text) {
  if (!text.trim() && !agentStore.selectedImage) return

  const messageImagePreviewUrl = agentStore.selectedImage
    ? URL.createObjectURL(agentStore.selectedImage)
    : ''

  agentStore.addMessage({
    role: 'user',
    content: text,
    imagePreviewUrl: messageImagePreviewUrl,
  })

  agentStore.addMessage({
    role: 'assistant',
    content: '',
  })

  agentStore.isStreaming = true
  agentStore.currentToolCall = null
  agentStore.errorMessage = ''

  const formData = new FormData()
  formData.append('message', text)
  formData.append('session_id', agentStore.currentSessionId)

  if (agentStore.selectedImage) {
    formData.append('image', agentStore.selectedImage)
  }

  agentStore.abortController = streamAgentChat(formData, {
    onMessage: handleAgentEvent,
    onDone: () => {
      agentStore.isStreaming = false
      agentStore.abortController = null
      agentStore.clearImage()
    },
    onError: () => {
      agentStore.isStreaming = false
      agentStore.abortController = null
      ElMessage.error('智能体服务暂不可用')
    },
  })
}
</script>

<style lang="scss" scoped>
.chat-interface {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
}
</style>
