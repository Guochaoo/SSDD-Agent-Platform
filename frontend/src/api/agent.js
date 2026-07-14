import { streamChat } from '@/utils/stream'
import request from '@/utils/request'
import { getHistoryApi, getHistoryDetailApi } from './history'

const USE_MOCK_AGENT = import.meta.env.VITE_USE_MOCK_AGENT !== 'false'

export function streamAgentChat(payload, callbacks) {
  if (USE_MOCK_AGENT) {
    return mockAgentStream(callbacks)
  }

  return streamChat('/api/agent/chat/stream', payload, callbacks, {
    maxRetries: 1,
    retryDelay: 1000,
  })
}

export function getAgentModelsApi() {
  return request.get('/agent/models')
}

export function getCachedAgentModelsApi() {
  return request.get('/agent/models/cached')
}

export function uploadAgentImageApi(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/agent/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function getAgentDetectionHistoryApi(params = {}) {
  return getHistoryApi(params)
}

export function getAgentDetectionHistoryDetailApi(taskId) {
  return getHistoryDetailApi(taskId)
}

export async function searchAgentKnowledgeApi() {
  return {
    items: [],
    ready: false,
    message: '知识库检索接口尚未开放，前端已预留接入点。',
  }
}

function mockAgentStream(callbacks) {
  const events = [
    { type: 'text_delta', content: '正在分析钢铁表面图像……\n\n' },
    { type: 'tool_start', tool_name: 'detection_tool' },
    {
      type: 'tool_result',
      tool_name: 'detection_tool',
      result: {
        class_name: '划痕',
        count: 1,
        confidence: 0.91,
        annotated_image_url: '',
      },
    },
    { type: 'text_delta', content: '检测到 1 处疑似划痕缺陷，置信度约为 91%。\n\n' },
    { type: 'text_delta', content: '建议进一步检查该区域是否存在表面磨损、搬运摩擦或轧制过程异常。' },
    { type: 'message_end' },
  ]

  let index = 0
  const timer = setInterval(() => {
    callbacks.onMessage?.(events[index])
    index += 1

    if (index >= events.length) {
      clearInterval(timer)
      callbacks.onDone?.()
    }
  }, 600)

  return () => clearInterval(timer)
}
