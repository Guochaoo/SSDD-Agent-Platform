import { streamChat } from '@/utils/stream'
import request from '@/utils/request'
import { getHistoryApi, getHistoryDetailApi } from './history'

export function streamAgentChat(payload, callbacks) {
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

export function listAgentSessions() {
  return request.get('/agent/sessions')
}

export function getAgentSession(sessionId) {
  return request.get(`/agent/sessions/${encodeURIComponent(sessionId)}`)
}

export function getAgentMessageImage(sessionId, messageId, index = 0) {
  return request.get(`/agent/sessions/${encodeURIComponent(sessionId)}/messages/${messageId}/image`, {
    params: { index },
    responseType: 'blob',
  })
}

export function deleteAgentSession(sessionId) {
  return request.delete(`/agent/sessions/${encodeURIComponent(sessionId)}`)
}
