<template>
  <div class="message-list">
    <div v-if="!messages.length" class="empty-state">
      <h3>钢铁表面缺陷检测智能助手</h3>
      <p>你可以上传钢铁表面图片，并询问缺陷类型、置信度和处理建议。</p>
    </div>

    <MessageItem
      v-for="message in messages"
      :key="message.id"
      :message="message"
    />

    <ToolCallDisplay :tool-call="toolCall" />
  </div>
</template>

<script setup>
import MessageItem from './MessageItem.vue'
import ToolCallDisplay from './ToolCallDisplay.vue'

defineProps({
  messages: {
    type: Array,
    default: () => [],
  },
  toolCall: {
    type: Object,
    default: null,
  },
})
</script>

<style lang="scss" scoped>
.message-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 20px;
  background: #f6f8fb;
}

.empty-state {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: $text-secondary;
  text-align: center;

  h3 {
    color: $text-primary;
    margin-bottom: 8px;
  }

  p {
    margin: 0;
  }
}
</style>