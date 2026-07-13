<template>
  <div class="agent-page">
    <div class="agent-header">
      <div>
        <h2>钢铁表面缺陷检测智能助手</h2>
        <p>上传钢铁表面图像，询问缺陷类型、检测结果、原因分析和处理建议</p>
      </div>

      <el-button @click="agentStore.newChat">新建对话</el-button>
    </div>

    <ChatInterface />
  </div>
</template>

<script setup>
import ChatInterface from '@/components/agent/ChatInterface.vue'
import { useAgentStore } from '@/stores/agent'

const agentStore = useAgentStore()
</script>

<style lang="scss" scoped>
.agent-page {
  height: calc(100vh - 96px);
  display: flex;
  flex-direction: column;
}

.agent-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;

  h2 {
    margin: 0 0 6px;
  }

  p {
    margin: 0;
    color: $text-secondary;
  }
}
</style>