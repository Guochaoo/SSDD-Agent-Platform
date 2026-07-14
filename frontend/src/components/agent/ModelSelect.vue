<template>
  <el-popover
    placement="top-start"
    :width="220"
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
      <div class="model-config">
        <el-input v-model="apiKey" type="password" show-password size="small" placeholder="输入 API key" />
        <el-select v-model="baseUrl" size="small" class="config-select">
          <el-option label="OpenAI" value="https://api.openai.com/v1" />
          <el-option label="通义千问" value="https://dashscope.aliyuncs.com/compatible-mode/v1" />
        </el-select>
        <el-button size="small" type="primary" :loading="llmStore.loading" @click="configure">验证并加载模型</el-button>
      </div>
      <div v-if="llmStore.loading" class="model-hint">加载中…</div>
      <template v-else>
        <button
          v-for="m in options"
          :key="m.value"
          :class="['model-item', { active: model === m.value }]"
          @click="model = m.value"
        >
          <div class="model-info">
            <span class="model-name">{{ m.label }}</span>
            <span class="model-provider">{{ m.ownedBy }}</span>
          </div>
          <el-icon v-if="model === m.value" :size="14" color="#8F8AB0"><Check /></el-icon>
        </button>
        <div v-if="options.length === 0 && llmStore.error" class="model-hint error">
          {{ llmStore.error }}
        </div>
        <details v-if="otherOptions.length" class="other-models">
          <summary>其他模型（{{ otherOptions.length }}）</summary>
          <button v-for="m in otherOptions" :key="m.value" class="model-item" @click="model = m.value">
            {{ m.label }}
          </button>
        </details>
      </template>
    </div>
  </el-popover>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ArrowDown, Check } from '@element-plus/icons-vue'
import { useLlmStore } from '@/stores/llm'

const llmStore = useLlmStore()

const model = defineModel({ default: useLlmStore().defaultModel })

const options = computed(() => llmStore.modelOptions)
const otherOptions = computed(() => llmStore.otherModels.map(m => ({ label: m.id, value: m.id })))
const apiKey = ref('')
const baseUrl = ref('https://dashscope.aliyuncs.com/compatible-mode/v1')

const currentLabel = computed(() => {
  const found = options.value.find(m => m.value === model.value)
  return found?.label || model.value || '选择模型'
})

async function configure() {
  if (!apiKey.value.trim()) return
  const selectedModel = options.value.length
    ? model.value
    : (baseUrl.value.includes('dashscope') ? 'qwen-plus' : 'gpt-4o-mini')
  model.value = selectedModel
  await llmStore.configure(apiKey.value.trim(), baseUrl.value, selectedModel)
}
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
  max-height: 280px;
  overflow-y: auto;
}

.model-config {
  display: grid;
  gap: 6px;
  padding: 6px;
  border-bottom: 1px solid #eee;
}

.config-select { width: 100%; }
.other-models { padding: 6px; font-size: 12px; color: #737373; }
.other-models summary { cursor: pointer; padding: 4px; }

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

.model-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
  overflow: hidden;
}

.model-name {
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.model-provider {
  font-size: 11px;
  color: #999;
}

.model-hint {
  padding: 8px 10px;
  font-size: 12px;
  color: #999;
  text-align: center;

  &.error {
    color: #e5534b;
  }
}
</style>
