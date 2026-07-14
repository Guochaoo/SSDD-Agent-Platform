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

      <video
        v-if="message.videoUrl"
        :src="message.videoUrl"
        class="message-video"
        controls
        preload="metadata"
      />

      <div v-if="message.videoResult" class="video-result">
        <div class="video-tags">
          <span>时长 {{ message.videoResult.duration_seconds }}s</span>
          <span>FPS {{ message.videoResult.fps }}</span>
          <span>关键帧 {{ message.videoResult.processed_frames }}</span>
          <span>目标 {{ message.videoResult.total_objects }}</span>
        </div>
        <video
          v-if="message.videoResult.annotated_video_url"
          :src="message.videoResult.annotated_video_url"
          class="message-video"
          controls
          preload="metadata"
        />
        <div v-else class="message-frames">
          <img
            v-for="frame in previewFrames"
            :key="frame.frame_index"
            :src="`data:image/jpeg;base64,${frame.annotated_image_base64}`"
            :alt="`关键帧 ${frame.frame_index}`"
          />
        </div>
      </div>

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

const previewFrames = computed(() =>
  (props.message.videoResult?.key_frames ?? [])
    .filter((frame) => frame.annotated_image_base64)
    .slice(0, 6),
)
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

.message-video {
  display: block;
  width: min(520px, 100%);
  max-height: 320px;
  margin-bottom: 8px;
  border-radius: 6px;
  background: #101828;
}

.video-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.video-tags span {
  padding: 3px 7px;
  border-radius: 999px;
  background: #eef4ff;
  color: #2563eb;
  font-size: 11px;
}

.message-frames {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}

.message-frames img {
  width: 100%;
  border-radius: 5px;
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
