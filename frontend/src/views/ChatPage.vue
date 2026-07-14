<template>
  <div class="agent-page">
    <div class="agent-header">
      <div>
        <h2>钢铁表面缺陷检测智能助手</h2>
        <p>上传钢铁表面图像，询问缺陷类型、检测结果、原因分析和处理建议</p>
      </div>

      <div class="header-actions">
        <el-button :loading="videoLoading" @click="handleVideoDetect">视频检测</el-button>
        <el-button @click="agentStore.newChat">新建对话</el-button>
      </div>
    </div>

    <ChatInterface />
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { ref } from 'vue'
import { detectVideoApi, getVideoStatusApi } from '@/api/detection'
import { getModelsApi, getScenesApi } from '@/api/models'
import ChatInterface from '@/components/agent/ChatInterface.vue'
import { useAgentStore } from '@/stores/agent'

const agentStore = useAgentStore()
const videoLoading = ref(false)

function selectVideo() {
  return new Promise((resolve) => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.mp4,.avi,.mov,.mkv,.wmv,.flv'
    input.onchange = () => resolve(input.files?.[0] ?? null)
    input.click()
  })
}

async function waitForVideo(taskId, message) {
  for (;;) {
    await new Promise((resolve) => window.setTimeout(resolve, 1500))
    const status = await getVideoStatusApi(taskId)
    message.content = status.message ?? '视频处理中...'
    if (status.status === 'completed') return status.result
    if (status.status === 'failed') throw new Error(status.message || '视频检测失败')
  }
}

async function handleVideoDetect() {
  const file = await selectVideo()
  if (!file) return
  if (file.size > 50 * 1024 * 1024) {
    ElMessage.warning('视频文件不能超过 50 MB')
    return
  }
  videoLoading.value = true
  const videoUrl = URL.createObjectURL(file)
  agentStore.addMessage({
    role: 'user',
    content: `[视频检测] ${file.name} (${(file.size / 1024 / 1024).toFixed(1)} MB)`,
    videoUrl,
  })
  const pendingMessage = {
    role: 'assistant',
    content: '正在上传视频...',
  }
  agentStore.addMessage(pendingMessage)
  const message = agentStore.messages[agentStore.messages.length - 1]
  try {
    const scenes = await getScenesApi()
    const models = await getModelsApi(scenes[0]?.id)
    const modelId = models.find((model) => model.isDefault)?.id ?? models[0]?.id
    if (!modelId) throw new Error('没有可用的检测模型')
    const task = await detectVideoApi(file, {
      modelId,
      confThreshold: 0.25,
      iouThreshold: 0.45,
      frameSampleRate: 5,
      maxFrames: 50,
    })
    message.content = '视频已上传，正在处理中...'
    message.videoResult = await waitForVideo(task.task_id, message)
    message.content = `视频检测完成：处理 ${message.videoResult.processed_frames} 个关键帧，发现 ${message.videoResult.total_objects} 个目标。`
  } catch (error) {
    message.content = `视频检测失败：${error.message || error}`
    message.error = true
  } finally {
    videoLoading.value = false
  }
}
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

.header-actions {
  display: flex;
  gap: 8px;
}
</style>
