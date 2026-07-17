import { defineStore } from 'pinia'
import { deleteAgentSession, getAgentMessageImage, getAgentSession, listAgentSessions } from '@/api/agent'

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
      this.abortController?.()
      this.abortController = null
      this.isStreaming = false
      this.connectionStatus = 'idle'
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
      this.messages = await Promise.all(session.messages.map(async (message) => ({
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
      })))
      this.currentToolCall = null
      this.errorMessage = ''
      this.clearImages()
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
