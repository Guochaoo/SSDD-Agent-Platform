const STORAGE_KEY = 'ssdd_error_logs'
const MAX_LOGS = 50

function normalizeError(error, extra = {}) {
  return {
    type: extra.type || 'frontend_error',
    message: error?.message || String(error),
    stack: error?.stack || '',
    url: window.location.href,
    userAgent: window.navigator.userAgent,
    timestamp: new Date().toISOString(),
    ...extra,
  }
}

export function reportError(error, extra = {}) {
  const entry = normalizeError(error, extra)
  const logs = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
  logs.unshift(entry)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(logs.slice(0, MAX_LOGS)))
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
