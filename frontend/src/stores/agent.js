import { defineStore } from 'pinia'

export const useAgentStore = defineStore('agent', {
  state: () => ({
    currentSessionId: crypto.randomUUID(),
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

    newChat() {
      this.stopStreaming()
      this.messages.forEach((message) => {
        if (message.imagePreviewUrl) URL.revokeObjectURL(message.imagePreviewUrl)
        if (message.videoUrl) URL.revokeObjectURL(message.videoUrl)
      })
      this.currentSessionId = crypto.randomUUID()
      this.messages = []
      this.currentToolCall = null
      this.errorMessage = ''
      this.clearImage()
    },
  },
})
