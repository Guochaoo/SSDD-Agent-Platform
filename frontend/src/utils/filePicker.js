/**
 * Open a native file picker and resolve with an empty list when the dialog is
 * cancelled. The injected globals keep the browser behavior directly
 * testable without mounting the whole chat page.
 */
export function chooseFiles({ accept, multiple }, {
  documentRef = document,
  windowRef = window,
} = {}) {
  return new Promise((resolve) => {
    const input = documentRef.createElement('input')
    input.type = 'file'
    input.accept = accept
    input.multiple = multiple
    let settled = false

    const cleanup = () => {
      windowRef.removeEventListener('focus', onFocus)
    }

    const onFocus = () => {
      cleanup()
      setTimeout(() => {
        if (!settled) {
          settled = true
          resolve([])
        }
      }, 300)
    }

    input.onchange = () => {
      settled = true
      cleanup()
      resolve(Array.from(input.files || []))
    }

    windowRef.addEventListener('focus', onFocus, { once: true })
    input.click()
  })
}
