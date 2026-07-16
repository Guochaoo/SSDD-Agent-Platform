<template>
  <div class="chat-input">
    <el-input
      v-model="text"
      type="textarea"
      :rows="3"
      resize="none"
      placeholder="请输入问题，例如：这张钢铁表面图片可能是什么缺陷？"
      :disabled="loading"
      @keydown.enter.exact.prevent="handleSend"
    />

    <div class="actions">
      <el-button v-if="loading" @click="$emit('stop')">
        停止
      </el-button>

      <el-button
        type="primary"
        :loading="loading"
        @click="handleSend"
      >
        发送
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  loading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['send', 'stop'])
const text = ref('')

function handleSend() {
  const value = text.value.trim()
  if (!value) return

  emit('send', value)
  text.value = ''
}
</script>

<style lang="scss" scoped>
.chat-input {
  border-top: 1px solid #ebeef5;
  padding: 14px;
  background: #fff;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 10px;
}
</style>
