import { defineStore } from 'pinia'
import { deleteAgentSession, getAgentArtifact, getAgentMessageImage, getAgentSession, listAgentSessions } from '@/api/agent'

const SESSION_KEY = 'ssdd_agent_session'
const SESSIONS_KEY = 'ssdd_agent_sessions'
const USER_KEY = 'ssdd_user'

function storageKey(base, userId) {
  return `${base}:${userId}`
}

function storedUserId() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || 'null')?.id ?? null
  } catch {
    return null
  }
}

function loadSavedSessions(userId) {
  if (userId == null) return []
  try {
    return JSON.parse(localStorage.getItem(storageKey(SESSIONS_KEY, userId)) || '[]')
  } catch {
    return []
  }
}

function initialState() {
  const userId = storedUserId()
  return {
    userScope: userId == null ? null : String(userId),
    currentSessionId: userId == null
      ? crypto.randomUUID()
      : localStorage.getItem(storageKey(SESSION_KEY, userId)) || crypto.randomUUID(),
    sessions: loadSavedSessions(userId),
  }
}

function serializeMessage(message) {
  const {
    imagePreviewUrls,
    detectionPreviewUrl,
    ...serializable
  } = message
  return serializable
}

function parseToolResult(tool) {
  let payload = tool.payload ?? tool.result
  if (typeof payload === 'string') {
    try { payload = JSON.parse(payload) } catch { return null }
  }
  return payload?.result || payload
}

const AGENT_LABEL_BY_NAME = {
  detection: '检测 Agent',
  data: '数据 Agent',
  general: '通用 Agent',
}

export const AGENT_ICON_BY_NAME = {
  detection: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>`,
  data: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="12" width="3" height="9" rx="1"/><rect x="10" y="7" width="3" height="14" rx="1"/><rect x="17" y="3" width="3" height="18" rx="1"/></svg>`,
  general: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`,
}

function ensureAgentLabel(tool) {
  if (tool.agentLabel) return
  tool.agentLabel = AGENT_LABEL_BY_NAME[tool.agent] || ''
}

function restoreToolCards(message) {
  (message.toolCalls || []).forEach(ensureAgentLabel)
  const completedTools = (message.toolCalls || []).filter((item) => item.status !== 'error' && parseToolResult(item))
  const tool = [...completedTools].reverse().find((item) => {
    const result = parseToolResult(item)
    return result?.detections || result?.results
  })
  message.toolResultCards = completedTools
    .map((item) => ({
      id: item.id || `${item.name || item.tool_name}-${item.display_order || 0}`,
      type: item.card_type || 'tool_result',
      result: parseToolResult(item),
      references: item.references || {},
    }))
    .filter((card) => card.type !== 'detection_result')
  if (!tool) return message
  const result = parseToolResult(tool)
  if (!result || result.error) return message
  const normalizeObjects = (items = []) => items.map((item, index) => ({
    id: String(index), className: item.class_name || item.className || 'unknown',
    classNameCn: item.class_name_cn || item.classNameCn || item.class_name || 'unknown',
    confidence: Number(item.confidence || 0), bbox: Array.isArray(item.bbox) ? item.bbox.map(Number) : [0, 0, 0, 0], bboxPercent: null,
  }))
  if (Array.isArray(result.results)) {
    message.detectionResult = { taskId: `agent-${message.id}`, totalImages: result.total_images ?? result.results.length, totalObjects: result.total_objects ?? 0, items: result.results.map((item) => ({ fileName: item.filename || item.file_name || '', annotatedImageUrl: item.annotated_image_url || item.annotatedImageUrl || '', totalObjects: item.total_objects ?? item.detections?.length ?? 0, inferenceTimeMs: Number(item.inference_time || 0), objects: normalizeObjects(item.detections), error: item.error || null })) }
  } else {
    const detections = result.detections || []
    message.detectionResult = { taskId: `agent-${message.id}`, fileName: result.filename || '', originalImageUrl: result.image_url || result.originalImageUrl || '', annotatedImageUrl: result.annotated_image_url || result.annotatedImageUrl || '', totalObjects: result.total_objects ?? result.totalObjects ?? detections.length, totalImages: result.total_images ?? 1, inferenceTimeMs: Number(result.inference_time ?? result.inference_time_ms ?? result.inferenceTimeMs ?? 0), objects: normalizeObjects(detections) }
  }
  return message
}

  function artifactFilename(url) {
    if (typeof url !== 'string' || !url) return ''
    try {
      const parsed = new URL(url, window.location.origin)
      const match = parsed.pathname.match(/^\/api\/agent\/artifacts\/([^/?]+)$/)
      return match ? decodeURIComponent(match[1]) : ''
    } catch {
      return ''
    }
  }

async function hydrateArtifactUrl(url) {
  const filename = artifactFilename(url)
  if (!filename) return url || ''
  try {
    return URL.createObjectURL(await getAgentArtifact(filename))
  } catch {
    return ''
  }
}

export const useAgentStore = defineStore('agent', {
  state: () => ({
    ...initialState(),
    messages: [],
    isStreaming: false,
    abortController: null,
    selectedImages: [],
    imagePreviewUrls: [],
    currentToolCall: null,
    errorMessage: '',
    connectionStatus: 'idle',
    reconnectCount: 0,
  }),

  getters: {
    messageCount: (state) => state.messages.length,
    hasMessages: (state) => state.messages.length > 0,
  },

  actions: {
    activateUser(userId = storedUserId()) {
      const nextScope = userId == null ? null : String(userId)
      if (this.userScope === nextScope) return
      this.stopStreaming()
      this.clearImages()
      this.messages = []
      this.currentToolCall = null
      this.errorMessage = ''
      this.userScope = nextScope
      this.sessions = loadSavedSessions(nextScope)
      this.currentSessionId = nextScope == null
        ? crypto.randomUUID()
        : localStorage.getItem(storageKey(SESSION_KEY, nextScope)) || crypto.randomUUID()
    },

    clearUserScope() {
      this.activateUser(null)
    },

    persistCurrentSessionId() {
      if (this.userScope != null) {
        localStorage.setItem(storageKey(SESSION_KEY, this.userScope), this.currentSessionId)
      }
    },

    async fetchSessions(userId = storedUserId()) {
      this.activateUser(userId)
      const sessions = await listAgentSessions()
      this.sessions = (sessions || []).map((session) => ({
        id: session.id,
        ownerId: session.owner_id,
        ownerUsername: session.owner_username,
        title: session.title,
        createdAt: session.created_at,
        updatedAt: session.updated_at,
        messages: [],
      }))
      if (this.sessions.some((session) => session.id === this.currentSessionId)) {
        await this.loadSession(this.currentSessionId)
      } else {
        this.messages = []
        this.currentSessionId = crypto.randomUUID()
        this.persistCurrentSessionId()
      }
    },

    addMessage(message) {
      this.persistCurrentSessionId()
      this.messages.push({
        id: crypto.randomUUID(),
        createdAt: new Date().toISOString(),
        status: 'done',
        ...message,
      })
      this.saveSession()
    },

    appendAssistantContent(content) {
      const lastMsg = this.messages[this.messages.length - 1]
      if (lastMsg?.role === 'assistant') {
        lastMsg.content += content
        lastMsg.status = this.isStreaming ? 'streaming' : 'done'
        this.saveSession()
      }
    },

    setToolCall(toolCall) {
      this.currentToolCall = toolCall
      const lastAssistant = [...this.messages].reverse().find((message) => message.role === 'assistant')
      if (lastAssistant) {
        lastAssistant.toolCalls = lastAssistant.toolCalls || []
        const key = toolCall.id || toolCall.name || toolCall.tool_name || 'tool'
        const existingIndex = lastAssistant.toolCalls.findIndex((item) => (
          (item.id || item.name || item.tool_name || 'tool') === key
        ))
        if (existingIndex >= 0) {
          lastAssistant.toolCalls[existingIndex] = {
            ...lastAssistant.toolCalls[existingIndex],
            ...toolCall,
            updatedAt: new Date().toISOString(),
          }
        } else {
          lastAssistant.toolCalls.push({
            ...toolCall,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          })
        }
        this.saveSession()
      }
    },

    setConnectionStatus(status) {
      this.connectionStatus = status
    },

    markLastAssistantError(message) {
      const lastMsg = this.messages[this.messages.length - 1]
      if (lastMsg?.role === 'assistant') {
        lastMsg.status = 'error'
        lastMsg.errorMessage = message
        if (!lastMsg.content) {
          lastMsg.content = message || '智能体响应失败，请稍后重试。'
        }
      }
      this.errorMessage = message || ''
      this.saveSession()
    },

    addSelectedImages(files) {
      files.forEach(file => {
        this.selectedImages.push(file)
        this.imagePreviewUrls.push(URL.createObjectURL(file))
      })
    },

    removeSelectedImage(index) {
      if (this.imagePreviewUrls[index]) URL.revokeObjectURL(this.imagePreviewUrls[index])
      this.selectedImages.splice(index, 1)
      this.imagePreviewUrls.splice(index, 1)
    },

    clearImages() {
      this.imagePreviewUrls.forEach(url => URL.revokeObjectURL(url))
      this.selectedImages = []
      this.imagePreviewUrls = []
    },

    stopStreaming() {
      const wasStreaming = this.isStreaming
      this.abortController?.()
      this.abortController = null
      this.isStreaming = false
      this.connectionStatus = 'idle'
      const lastMessage = this.messages[this.messages.length - 1]
      if (wasStreaming && lastMessage?.role === 'assistant' && lastMessage.status === 'streaming') {
        lastMessage.status = 'cancelled'
        this.saveSession()
      }
    },

    /**
     * 重新生成：移除最后一对 user+assistant 消息
     * 返回被移除的 user 消息，供调用方重新发送
     */
    removeLastExchange() {
      // 找到最后一个 assistant
      const lastIdx = this.messages.length - 1
      if (lastIdx < 1) return null
      if (this.messages[lastIdx]?.role !== 'assistant') return null

      const assistantMsg = this.messages.pop()
      const userMsg = this.messages.pop()

      // 清理 image URLs
      (userMsg?.imagePreviewUrls || []).forEach(url => URL.revokeObjectURL(url))
      if (assistantMsg?.detectionPreviewUrl) {
        URL.revokeObjectURL(assistantMsg.detectionPreviewUrl)
      }

      this.currentToolCall = null
      return userMsg
    },

    newChat() {
      this.stopStreaming()
      this.messages.forEach((message) => {
        (message.imagePreviewUrls || []).forEach(url => URL.revokeObjectURL(url))
        if (message.videoUrl) URL.revokeObjectURL(message.videoUrl)
        if (message.detectionPreviewUrl) URL.revokeObjectURL(message.detectionPreviewUrl)
      })
      this.currentSessionId = crypto.randomUUID()
      this.persistCurrentSessionId()
      this.messages = []
      this.currentToolCall = null
      this.errorMessage = ''
      this.connectionStatus = 'idle'
      this.reconnectCount = 0
      this.clearImages()
    },

    saveSession() {
      if (!this.hasMessages) return
      const existing = this.sessions.find(s => s.id === this.currentSessionId)
      const title = this.messages.find(m => m.role === 'user')?.content?.slice(0, 30) || '新对话'
      const messages = this.messages.map(serializeMessage)
      if (existing) {
        existing.messages = messages
        existing.title = title
        existing.updatedAt = new Date().toISOString()
      } else {
        this.sessions.unshift({
          id: this.currentSessionId,
          title,
          messages,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        })
      }
      this.sessions = this.sessions.slice(0, 20)
      if (this.userScope != null) {
        localStorage.setItem(storageKey(SESSIONS_KEY, this.userScope), JSON.stringify(this.sessions))
      }
    },

    async loadSession(id) {
      const session = this.sessions.find(s => s.id === id)
      if (!session) return
      this.stopStreaming()
      const remote = await getAgentSession(id)
      this.currentSessionId = session.id
      this.persistCurrentSessionId()
      session.title = remote.title
      session.messages = remote.messages || []
      this.messages = await Promise.all(session.messages.map(async (message) => {
        const restored = restoreToolCards({
          id: String(message.id),
          role: message.role,
          content: message.content || '',
          imagePreviewUrls: (await Promise.all(
            (message.image_urls || (message.image_url ? [message.image_url] : [])).map(async (_, index) => {
              try {
                const blob = await getAgentMessageImage(session.id, message.id, index)
                return URL.createObjectURL(blob)
              } catch {
                return ''
              }
            }),
          )).filter(Boolean),
          toolCalls: message.tool_calls || [],
          createdAt: message.created_at,
        })
        await this.hydrateDetectionImages(restored)
        return restored
      }))
      this.currentToolCall = null
      this.errorMessage = ''
      this.clearImages()
    },

    async hydrateDetectionImages(message) {
      const result = message?.detectionResult
      if (!result) return
      if (Array.isArray(result.items)) {
        await Promise.all(result.items.map(async (item) => {
          item.annotatedImageUrl = await hydrateArtifactUrl(item.annotatedImageUrl)
          item.originalImageUrl = await hydrateArtifactUrl(item.originalImageUrl)
        }))
      } else {
        result.annotatedImageUrl = await hydrateArtifactUrl(result.annotatedImageUrl)
        result.originalImageUrl = await hydrateArtifactUrl(result.originalImageUrl)
      }
    },

    async deleteSession(id) {
      await deleteAgentSession(id)
      this.sessions = this.sessions.filter(s => s.id !== id)
      if (this.userScope != null) {
        localStorage.setItem(storageKey(SESSIONS_KEY, this.userScope), JSON.stringify(this.sessions))
      }
      if (this.currentSessionId === id) {
        this.newChat()
      }
    },
  },
})
