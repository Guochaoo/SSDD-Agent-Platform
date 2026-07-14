export function streamChat(url, body, callbacks = {}, options = {}) {
  const { onMessage, onDone, onError, onRetry } = callbacks
  const {
    maxRetries = 1,
    retryDelay = 800,
  } = options
  const token = localStorage.getItem('ssdd_token')
  const controller = new AbortController()
  const isFormData = body instanceof FormData
  let retryCount = 0
  let settled = false
  let receivedAnyMessage = false

  async function connect() {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: isFormData ? body : JSON.stringify(body),
        signal: controller.signal,
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      if (!response.body) throw new Error('当前浏览器不支持流式响应')

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      while (!settled) {
        const { done, value } = await reader.read()
        if (done) {
          processSSEMessage(buffer, onMessage)
          settled = true
          onDone?.()
          return
        }

        buffer += decoder.decode(value, { stream: true })
        const messages = buffer.split(/\r?\n\r?\n/)
        buffer = messages.pop() || ''

        for (const message of messages) {
          if (!message.trim()) continue
          const shouldStop = processSSEMessage(message, (event) => {
            receivedAnyMessage = true
            onMessage?.(event)
          })
          if (shouldStop) {
            settled = true
            onDone?.()
            return
          }
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') return

      const canRetry = !receivedAnyMessage && retryCount < maxRetries
      if (canRetry) {
        retryCount += 1
        onRetry?.({ retryCount, error: err })
        window.setTimeout(connect, retryDelay * retryCount)
        return
      }

      settled = true
      onError?.(err)
    }
  }

  connect()

  return () => {
    settled = true
    controller.abort()
  }
}

function processSSEMessage(message, onMessage) {
  if (!message.trim()) return false

  const lines = message.split(/\r?\n/)
  const dataLines = lines
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trim())

  if (!dataLines.length) return false

  const data = dataLines.join('\n')
  if (data === '[DONE]') return true

  try {
    onMessage?.(JSON.parse(data))
  } catch {
    onMessage?.({ type: 'text_delta', content: data })
  }

  return false
}
