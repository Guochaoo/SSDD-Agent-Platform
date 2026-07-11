<template>
  <el-card v-if="toolCall" class="tool-call-card">
    <div class="tool-header">
      <strong>{{ toolName }}</strong>
      <el-tag :type="tagType">
        {{ statusText }}
      </el-tag>
    </div>

    <div v-if="toolCall.status === 'running'" class="running">
      正在调用缺陷检测工具...
    </div>

    <div v-if="toolCall.result" class="result">
      <p v-if="toolCall.result.class_name">
        缺陷类型：{{ toolCall.result.class_name }}
      </p>

      <p v-if="toolCall.result.count != null">
        缺陷数量：{{ toolCall.result.count }}
      </p>

      <p v-if="toolCall.result.confidence != null">
        置信度：{{ formatConfidence(toolCall.result.confidence) }}
      </p>

      <el-image
        v-if="toolCall.result.annotated_image_url"
        :src="toolCall.result.annotated_image_url"
        fit="contain"
        class="result-image"
      />
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  toolCall: {
    type: Object,
    default: null,
  },
})

const toolName = computed(() => {
  if (!props.toolCall?.name) return '缺陷检测工具'
  if (props.toolCall.name === 'detection_tool') return '缺陷检测工具'
  return props.toolCall.name
})

const statusText = computed(() => {
  if (props.toolCall?.status === 'running') return '运行中'
  if (props.toolCall?.status === 'success') return '成功'
  if (props.toolCall?.status === 'error') return '失败'
  return '未知'
})

const tagType = computed(() => {
  if (props.toolCall?.status === 'success') return 'success'
  if (props.toolCall?.status === 'error') return 'danger'
  return 'warning'
})

function formatConfidence(value) {
  return `${Math.round(Number(value) * 100)}%`
}
</script>

<style lang="scss" scoped>
.tool-call-card {
  margin: 12px 0 16px 48px;
  max-width: 520px;
}

.tool-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.running {
  color: $text-secondary;
}

.result p {
  margin: 6px 0;
}

.result-image {
  width: 100%;
  max-height: 260px;
  margin-top: 8px;
  border-radius: 6px;
}
</style>