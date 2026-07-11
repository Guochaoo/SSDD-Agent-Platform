<template>
  <div :class="['message-item', message.role]">
    <div class="avatar">
      {{ message.role === 'user' ? '我' : 'AI' }}
    </div>

    <div class="bubble">
      <img
        v-if="message.imagePreviewUrl"
        :src="message.imagePreviewUrl"
        class="message-image"
        alt="上传的钢铁表面图像"
      />

      <div
        v-if="message.role === 'assistant'"
        class="markdown-body"
        v-html="renderedContent"
      />

      <div v-else class="plain-text">
        {{ message.content }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { renderMarkdown } from '@/utils/markdown'

const props = defineProps({
  message: {
    type: Object,
    required: true,
  },
})

const renderedContent = computed(() => {
  return renderMarkdown(props.message.content || '')
})
</script>

<style lang="scss" scoped>
.message-item {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;

  &.user {
    flex-direction: row-reverse;

    .bubble {
      background: #ecf5ff;
    }
  }

  &.assistant .bubble {
    background: #fff;
  }
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.bubble {
  max-width: 72%;
  padding: 12px 14px;
  border-radius: 8px;
  box-shadow: $shadow-sm;
  line-height: 1.6;
}

.message-image {
  max-width: 260px;
  max-height: 180px;
  display: block;
  margin-bottom: 8px;
  border-radius: 6px;
  object-fit: contain;
}

.plain-text {
  white-space: pre-wrap;
}

.markdown-body {
  :deep(p) {
    margin: 0 0 8px;
  }

  :deep(p:last-child) {
    margin-bottom: 0;
  }

  :deep(code) {
    background: #f2f3f5;
    padding: 2px 4px;
    border-radius: 4px;
  }
}
</style>