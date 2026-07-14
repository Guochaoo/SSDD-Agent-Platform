<template>
  <div class="detection-card">
    <div class="card-header">
      <div>
        <strong>{{ title }}</strong>
        <p>{{ subtitle }}</p>
      </div>
      <el-tag type="success" effect="light">检测完成</el-tag>
    </div>

    <el-image
      v-if="displayImage"
      :src="displayImage"
      :preview-src-list="[displayImage]"
      fit="contain"
      class="result-image"
    />

    <div class="summary">
      <div>
        <span>图片数量</span>
        <strong>{{ imageCount }}</strong>
      </div>
      <div>
        <span>缺陷数量</span>
        <strong>{{ objectCount }}</strong>
      </div>
      <div>
        <span>最高置信度</span>
        <strong>{{ maxConfidence }}</strong>
      </div>
    </div>

    <el-table v-if="tableRows.length" :data="tableRows" size="small" max-height="240">
      <el-table-column prop="fileName" label="图片" min-width="120" />
      <el-table-column prop="className" label="缺陷类型" min-width="110" />
      <el-table-column label="置信度" width="100">
        <template #default="{ row }">{{ formatPercent(row.confidence) }}</template>
      </el-table-column>
    </el-table>

    <el-empty v-else :image-size="64" description="未检测到明显缺陷" />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  result: {
    type: Object,
    required: true,
  },
  previewUrl: {
    type: String,
    default: '',
  },
})

const isBatch = computed(() => Array.isArray(props.result.items))

const title = computed(() => (isBatch.value ? '批量检测结果' : '单图检测结果'))

const subtitle = computed(() => {
  if (isBatch.value) return `任务 ${props.result.taskId || '-'}`
  return props.result.fileName || `任务 ${props.result.taskId || '-'}`
})

const displayImage = computed(() => {
  if (isBatch.value) {
    return props.result.items?.find((item) => item.annotatedImageUrl)?.annotatedImageUrl || props.previewUrl
  }
  return props.result.annotatedImageUrl || props.previewUrl
})

const imageCount = computed(() => {
  if (isBatch.value) return props.result.items?.length || props.result.successCount || 0
  return props.result.totalImages || 1
})

const objectCount = computed(() => {
  if (isBatch.value) {
    return (props.result.items || []).reduce((sum, item) => sum + Number(item.totalObjects || 0), 0)
  }
  return props.result.totalObjects || props.result.objects?.length || 0
})

const tableRows = computed(() => {
  if (isBatch.value) {
    return (props.result.items || []).flatMap((item) => {
      if (!item.objects?.length) {
        return [{
          fileName: item.fileName || '-',
          className: item.error || '未检测到明显缺陷',
          confidence: 0,
        }]
      }
      return item.objects.map((object) => ({
        fileName: item.fileName || '-',
        className: object.classNameCn || object.className || '未知缺陷',
        confidence: object.confidence,
      }))
    })
  }

  return (props.result.objects || []).map((object) => ({
    fileName: props.result.fileName || '-',
    className: object.classNameCn || object.className || '未知缺陷',
    confidence: object.confidence,
  }))
})

const maxConfidence = computed(() => {
  const values = tableRows.value.map((row) => Number(row.confidence || 0))
  return formatPercent(Math.max(0, ...values))
})

function formatPercent(value) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`
}
</script>

<style lang="scss" scoped>
.detection-card {
  margin-top: 12px;
  padding: 16px;
  border: 1px solid #e7ebf1;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(28, 39, 60, 0.05);
}

.card-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;

  strong {
    color: #171717;
    font-size: 15px;
  }

  p {
    margin: 4px 0 0;
    color: $text-secondary;
    font-size: 12px;
  }
}

.result-image {
  width: 100%;
  max-height: 320px;
  margin-bottom: 12px;
  border: 1px solid #edf0f5;
  border-radius: 10px;
  background: #f7f9fc;
}

.summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;

  div {
    padding: 10px 12px;
    border-radius: 9px;
    background: #f7f9fc;
  }

  span,
  strong {
    display: block;
  }

  span {
    color: $text-secondary;
    font-size: 11px;
  }

  strong {
    margin-top: 3px;
    color: #172033;
    font-size: 16px;
  }
}

@media (max-width: 640px) {
  .summary {
    grid-template-columns: 1fr;
  }
}
</style>
