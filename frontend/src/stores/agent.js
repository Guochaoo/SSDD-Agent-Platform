import { defineStore } from 'pinia'

const SESSION_KEY = 'ssdd_agent_session'
const SESSIONS_KEY = 'ssdd_agent_sessions'

function loadSavedSessions() {
  try {
    return JSON.parse(localStorage.getItem(SESSIONS_KEY) || '[]')
  } catch {
    return []
  }
}

function serializeMessage(message) {
  const {
    imagePreviewUrl,
    detectionPreviewUrl,
    ...serializable
  } = message
  return serializable
}

export const useAgentStore = defineStore('agent', {
  state: () => ({
    currentSessionId: localStorage.getItem(SESSION_KEY) || crypto.randomUUID(),
    messages: [],
    sessions: loadSavedSessions(),
    isStreaming: false,
    abortController: null,
    selectedImage: null,
    imagePreviewUrl: '',
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
    addMessage(message) {
      localStorage.setItem(SESSION_KEY, this.currentSessionId)
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

    setSelectedImage(file) {
      this.clearImage()
      this.selectedImage = file
      this.imagePreviewUrl = URL.createObjectURL(file)
    },

    clearImage() {
      if (this.imagePreviewUrl) URL.revokeObjectURL(this.imagePreviewUrl)
      this.selectedImage = null
      this.imagePreviewUrl = ''
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

      // 清理 image URL
      if (userMsg?.imagePreviewUrl) {
        URL.revokeObjectURL(userMsg.imagePreviewUrl)
      }
      if (assistantMsg?.detectionPreviewUrl) {
        URL.revokeObjectURL(assistantMsg.detectionPreviewUrl)
      }

      this.currentToolCall = null
      return userMsg
    },

    newChat() {
      this.stopStreaming()
      this.messages.forEach((message) => {
        if (message.imagePreviewUrl) URL.revokeObjectURL(message.imagePreviewUrl)
        if (message.detectionPreviewUrl) URL.revokeObjectURL(message.detectionPreviewUrl)
      })
      this.currentSessionId = crypto.randomUUID()
      localStorage.setItem(SESSION_KEY, this.currentSessionId)
      this.messages = []
      this.currentToolCall = null
      this.errorMessage = ''
      this.connectionStatus = 'idle'
      this.reconnectCount = 0
      this.clearImage()
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
      localStorage.setItem(SESSIONS_KEY, JSON.stringify(this.sessions))
    },

    loadSession(id) {
      const session = this.sessions.find(s => s.id === id)
      if (!session) return
      this.stopStreaming()
      this.currentSessionId = session.id
      this.messages = session.messages.map(m => ({ ...m }))
      this.currentToolCall = null
      this.errorMessage = ''
      this.clearImage()
    },

    deleteSession(id) {
      this.sessions = this.sessions.filter(s => s.id !== id)
      localStorage.setItem(SESSIONS_KEY, JSON.stringify(this.sessions))
      if (this.currentSessionId === id) {
        this.newChat()
      }
    },
  },
})
