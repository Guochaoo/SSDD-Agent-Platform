/**
 * SSE (Server-Sent Events) 娴佸紡澶勭悊宸ュ叿
 * 鐢ㄤ簬 Day 11 鏅鸿兘浣撳璇濈殑娴佸紡娓叉煋
 *
 * 浣跨敤鏂瑰紡锛?
 *  const stop = streamChat(
 *    '/api/chat/stream',
 *    { message: '浣犲ソ' },
 *    {
 *      onMessage: (chunk) => { content += chunk },
 *      onDone: () => { console.log('瀹屾垚') },
 *      onError: (err) => { console.error(err) },
 *    }
 *  )
 */

/**
 * 鍙戣捣 SSE 娴佸紡璇锋眰
 *
 * @param {string} url - 璇锋眰鍦板潃锛堢浉瀵硅矾寰勶紝浼氱粡杩?Vite proxy锛?
 * @param {Object} body - 璇锋眰浣?
 * @param {Object} callbacks - 鍥炶皟鍑芥暟
 * @param {Function} callbacks.onMessage - 鏀跺埌娑堟伅鐗囨鏃剁殑鍥炶皟
 * @param {Function} callbacks.onDone - 娴佺粨鏉熸椂鐨勫洖璋?
 * @param {Function} callbacks.onError - 閿欒鏃剁殑鍥炶皟
 * @returns {Function} stop - 璋冪敤姝ゅ嚱鏁板彲涓柇杩炴帴
 */
export function streamChat(url, body, callbacks) {
  const { onMessage, onDone, onError } = callbacks

  // 浠?localStorage 鑾峰彇 Token
  const token = localStorage.getItem('ssdd_token')

  // 浣跨敤 fetch + ReadableStream 瀹炵幇 SSE
  const controller = new AbortController()

  fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')

      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          onDone?.()
          break
        }

        // 瑙ｆ瀽 SSE 鏁版嵁
        const text = decoder.decode(value, { stream: true })
        const lines = text.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6) // 鍘绘帀 "data: " 鍓嶇紑

            if (data === '[DONE]') {
              onDone?.()
              return
            }

            try {
              const parsed = JSON.parse(data)
              onMessage?.(parsed)
            } catch {
              // 闈?JSON 鏁版嵁锛岀洿鎺ヤ綔涓烘枃鏈墖娈?
              onMessage?.(data)
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError?.(err)
      }
    })

  // 杩斿洖涓柇鍑芥暟
  return () => controller.abort()
}
