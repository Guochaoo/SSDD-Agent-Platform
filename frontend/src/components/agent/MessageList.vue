<template>
  <div class="message-list">
    <div v-if="!messages.length && !isStreaming" class="empty-state">
      <p>开始对话，询问钢铁表面缺陷相关问题。</p>
    </div>

    <MessageItem
      v-for="(message, index) in messages"
      :key="message.id"
      :message="message"
      :is-last-streaming="isStreaming && index === messages.length - 1 && message.role === 'assistant'"
      @regenerate="(msg) => $emit('regenerate', msg)"
    />

    <!-- Thinking indicator -->
    <div v-if="showThinking" class="thinking-row">
      <ThinkingIndicator />
    </div>

    <ToolCallDisplay :tool-call="toolCall" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import MessageItem from './MessageItem.vue'
import ToolCallDisplay from './ToolCallDisplay.vue'
import ThinkingIndicator from './ThinkingIndicator.vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  toolCall: { type: Object, default: null },
  isStreaming: { type: Boolean, default: false },
})

defineEmits(['regenerate'])

const showThinking = computed(() => {
  if (!props.isStreaming) return false
  const last = props.messages[props.messages.length - 1]
  return last?.role === 'assistant' && !last?.content
})
</script>

<style lang="scss" scoped>
.message-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 0;
  background: #fff;
}

.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #a3a3a3;
  font-size: 14px;
  text-align: center;
}

.thinking-row {
  padding: 8px 24px;
}
</style>
