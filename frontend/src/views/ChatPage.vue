<template>
  <div class="chat-page">
    <div class="chat-header">
      <div>
        <h2>钢铁表面缺陷检测智能助手</h2>
        <p>上传钢铁表面图像，询问缺陷类型、检测结果、原因分析和处理建议</p>
      </div>
      <el-button :icon="Plus" @click="agentStore.newChat()">
        新建对话
      </el-button>
    </div>
    <ChatInterface />
  </div>
</template>

<script setup>
import { Plus } from '@element-plus/icons-vue'
import ChatInterface from '@/components/agent/ChatInterface.vue'
import { useAgentStore } from '@/stores/agent'

const agentStore = useAgentStore()
</script>

<style lang="scss" scoped>
.chat-page {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chat-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: $spacing-md;
  flex-shrink: 0;

  h2 {
    margin: 0 0 4px;
    font-size: 18px;
    font-weight: 600;
  }

  p {
    margin: 0;
    color: $text-secondary;
    font-size: 13px;
  }
}
</style>
