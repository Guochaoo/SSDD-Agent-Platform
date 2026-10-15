const STORAGE_KEY = 'ssdd_error_logs'
const MAX_LOGS = 50
const TOKEN_KEY = 'ssdd_token'
const USER_KEY = 'ssdd_user'
const SESSION_KEY = 'ssdd_agent_session'

function redactClientText(value) {
  return String(value || '')
    .replace(/bearer\s+[A-Za-z0-9._~+/=-]+/gi, 'Bearer [redacted]')
    .replace(/(password|token|authorization|api[_-]?key|secret)\s*[:=]\s*[^\s,;]+/gi, '$1=[redacted]')
    .replace(/https?:\/\/[^\s\]}>,;]+/gi, '[resource-url-redacted]')
}

function getErrorContext() {
  try {
    const user = JSON.parse(localStorage.getItem(USER_KEY) || 'null')
    const userId = user?.id == null ? undefined : String(user.id)
    return {
      user_id: userId,
      session_id: userId ? localStorage.getItem(`${SESSION_KEY}:${userId}`) || undefined : undefined,
    }
  } catch {
    return {}
  }
}

function normalizeError(error, extra = {}) {
  return {
    type: extra.type || 'frontend_error',
    message: redactClientText(error?.message || String(error)),
    stack: redactClientText(error?.stack || ''),
    url: window.location.pathname,
    userAgent: window.navigator.userAgent,
    timestamp: new Date().toISOString(),
    ...getErrorContext(),
    ...extra,
  }
}

export function reportError(error, extra = {}) {
  const entry = normalizeError(error, extra)
  const logs = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
  logs.unshift(entry)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(logs.slice(0, MAX_LOGS)))
  const token = localStorage.getItem(TOKEN_KEY)
  if (token && typeof fetch === 'function') {
    void fetch('/api/operation-logs/client-error', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        type: entry.type,
        message: String(entry.message).slice(0, 500),
        request_id: entry.request_id || entry.requestId,
        task_id: entry.task_id || entry.taskId,
        session_id: entry.session_id || entry.sessionId,
        user_id: entry.user_id || entry.userId,
        pathname: window.location.pathname,
      }),
      keepalive: true,
    }).catch(() => {})
  }
  return entry
}

export function setupErrorReporting(app) {
  window.addEventListener('error', (event) => {
    reportError(event.error || event.message, { type: 'window_error' })
  })

  window.addEventListener('unhandledrejection', (event) => {
    reportError(event.reason || 'Unhandled promise rejection', {
      type: 'unhandled_rejection',
    })
  })

  app.config.errorHandler = (error, instance, info) => {
    reportError(error, {
      type: 'vue_error',
      component: instance?.type?.name || 'anonymous',
      info,
    })
  }
}

export { STORAGE_KEY as ERROR_LOG_STORAGE_KEY }
