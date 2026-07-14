<template>
  <div class="quick-detect-bar">
    <button class="quick-detect-btn" :disabled="disabled" @click="$emit('single')">
      单图检测
    </button>
    <button class="quick-detect-btn" :disabled="disabled" @click="$emit('batch')">
      批量图片检测
    </button>
    <button class="quick-detect-btn muted" :disabled="disabled" @click="$emit('zip')">
      ZIP 检测
    </button>
  </div>
</template>

<script setup>
defineProps({
  disabled: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['single', 'batch', 'zip'])
</script>

<style lang="scss" scoped>
.quick-detect-bar {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
}

.quick-detect-btn {
  height: 32px;
  padding: 0 14px;
  border: 1px solid #e0e0e0;
  border-radius: 18px;
  background: #fff;
  color: #525252;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;

  &:hover:not(:disabled) {
    border-color: #8f8ab0;
    color: #8f8ab0;
    background: #f8f7fb;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &.muted {
    color: #737373;
  }
}
</style>
