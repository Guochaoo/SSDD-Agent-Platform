<template>
  <el-popover
    placement="top-start"
    :width="200"
    trigger="click"
    :show-arrow="false"
  >
    <template #reference>
      <button class="model-btn">
        <span>{{ currentLabel }}</span>
        <el-icon :size="12"><ArrowDown /></el-icon>
      </button>
    </template>

    <div class="model-list">
      <button
        v-for="m in models"
        :key="m.value"
        :class="['model-item', { active: model === m.value }]"
        @click="model = m.value"
      >
        <span>{{ m.label }}</span>
        <el-icon v-if="model === m.value" :size="14" color="#8F8AB0"><Check /></el-icon>
      </button>
    </div>
  </el-popover>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowDown, Check } from '@element-plus/icons-vue'

const model = defineModel({ default: 'gpt-4o-mini' })

const models = [
  { label: 'GPT-4o Mini', value: 'gpt-4o-mini' },
  { label: 'Qwen 2.5 7B', value: 'qwen2.5:7b' },
  { label: 'GPT-4o', value: 'gpt-4o' },
]

const currentLabel = computed(() => {
  return models.find(m => m.value === model.value)?.label || '选择模型'
})
</script>

<style lang="scss" scoped>
.model-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #737373;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    background: #f1f1f0;
    color: #171717;
  }
}

.model-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 4px;
}

.model-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  font-size: 13px;
  color: #171717;
  cursor: pointer;
  transition: background 0.1s;
  width: 100%;
  text-align: left;

  &:hover {
    background: #f6f5f9;
  }

  &.active {
    color: #8F8AB0;
  }
}
</style>
