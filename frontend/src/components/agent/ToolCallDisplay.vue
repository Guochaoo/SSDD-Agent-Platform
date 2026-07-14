<template>
  <div v-if="toolCall" class="tool-call">
    <!-- Running state -->
    <div v-if="toolCall.status === 'running'" class="tool-running">
      <div class="tool-dot" />
      <span>正在调用缺陷检测工具…</span>
    </div>

    <!-- Result state -->
    <div v-else-if="toolCall.result" class="tool-result">
      <div class="result-header">
        <el-icon :size="16" color="#67c23a"><CircleCheck /></el-icon>
        <span>检测完成</span>
      </div>

      <!-- Stats row -->
      <div class="result-stats">
        <div v-if="toolCall.result.class_name" class="stat">
          <span class="stat-label">缺陷类型</span>
          <span class="stat-value">{{ toolCall.result.class_name }}</span>
        </div>
        <div v-if="toolCall.result.count != null" class="stat">
          <span class="stat-label">数量</span>
          <span class="stat-value">{{ toolCall.result.count }}</span>
        </div>
        <div v-if="toolCall.result.confidence != null" class="stat">
          <span class="stat-label">置信度</span>
          <span class="stat-value accent">{{ formatConfidence(toolCall.result.confidence) }}</span>
        </div>
      </div>

      <!-- Annotated image embedded in the result -->
      <el-image
        v-if="toolCall.result.annotated_image_url"
        :src="toolCall.result.annotated_image_url"
        :preview-src-list="[toolCall.result.annotated_image_url]"
        fit="contain"
        class="result-image"
        :initial-index="0"
      >
        <template #placeholder>
          <div class="image-placeholder">
            <el-icon :size="24"><Picture /></el-icon>
            <span>加载标注图中…</span>
          </div>
        </template>
      </el-image>
    </div>

    <!-- Error state -->
    <div v-else-if="toolCall.status === 'error'" class="tool-error">
      <el-icon :size="16"><CircleClose /></el-icon>
      <span>工具调用失败</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { CircleCheck, CircleClose, Picture } from '@element-plus/icons-vue'

const props = defineProps({
  toolCall: { type: Object, default: null },
})

function formatConfidence(value) {
  return `${Math.round(Number(value) * 100)}%`
}
</script>

<style lang="scss" scoped>
.tool-call {
  margin: 8px auto 16px;
  max-width: 780px;
  padding: 0 24px;
}

/* ── Running ── */
.tool-running {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: $text-secondary;
  padding: 8px 12px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
}

.tool-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: #e6a23c;
  animation: blink 1s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.2; }
}

/* ── Result ── */
.tool-result {
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 12px;
  overflow: hidden;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
  color: #67c23a;
  background: #f6fdf3;
  border-bottom: 1px solid #edf7e7;
}

.result-stats {
  display: flex;
  gap: 0;
  padding: 10px 14px;
}

.stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-label {
  font-size: 11px;
  color: #a3a3a3;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  font-size: 14px;
  font-weight: 600;
  color: #171717;

  &.accent {
    color: #8F8AB0;
  }
}

.result-image {
  width: 100%;
  max-height: 300px;
  border-top: 1px solid #f0f0f0;
  cursor: pointer;
}

.image-placeholder {
  width: 100%;
  height: 140px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: #fff;
  color: #a3a3a3;
  font-size: 13px;
}

/* ── Error ── */
.tool-error {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #f56c6c;
  padding: 8px 12px;
  background: #fef0f0;
  border-radius: 8px;
}
</style>
