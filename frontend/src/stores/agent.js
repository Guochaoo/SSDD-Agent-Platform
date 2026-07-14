import { defineStore } from 'pinia'

export const useAgentStore = defineStore('agent', {
  state: () => ({
    currentSessionId: localStorage.getItem('ssdd_agent_session') || crypto.randomUUID(),
    messages: [],
    sessions: [],
    isStreaming: false,
    abortController: null,
    selectedImage: null,
    imagePreviewUrl: '',
    currentToolCall: null,
    errorMessage: '',
  }),

  getters: {
    messageCount: (state) => state.messages.length,
    hasMessages: (state) => state.messages.length > 0,
  },

  actions: {
    addMessage(message) {
      localStorage.setItem('ssdd_agent_session', this.currentSessionId)
      this.messages.push({
        id: crypto.randomUUID(),
        createdAt: new Date().toISOString(),
        ...message,
      })
    },

    appendAssistantContent(content) {
      const lastMsg = this.messages[this.messages.length - 1]
      if (lastMsg?.role === 'assistant') {
        lastMsg.content += content
      }
    },

    setToolCall(toolCall) {
      this.currentToolCall = toolCall
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
        if (message.videoUrl) URL.revokeObjectURL(message.videoUrl)
        if (message.detectionPreviewUrl) URL.revokeObjectURL(message.detectionPreviewUrl)
      })
      this.currentSessionId = crypto.randomUUID()
      localStorage.setItem('ssdd_agent_session', this.currentSessionId)
      this.messages = []
      this.currentToolCall = null
      this.errorMessage = ''
      this.clearImage()
    },

    saveSession() {
      if (!this.hasMessages) return
      const existing = this.sessions.find(s => s.id === this.currentSessionId)
      const title = this.messages.find(m => m.role === 'user')?.content?.slice(0, 30) || '新对话'
      if (existing) {
        existing.messages = [...this.messages]
        existing.title = title
        existing.updatedAt = new Date().toISOString()
      } else {
        this.sessions.unshift({
          id: this.currentSessionId,
          title,
          messages: [...this.messages],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        })
      }
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
      if (this.currentSessionId === id) {
        this.newChat()
      }
    },
  },
})
