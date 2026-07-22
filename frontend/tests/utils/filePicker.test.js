import { afterEach, describe, expect, it, vi } from 'vitest'
import { chooseFiles } from '@/utils/filePicker'

function createPickerHarness() {
  let focusHandler = null
  const input = {
    files: [],
    click: vi.fn(),
  }
  const documentRef = {
    createElement: vi.fn(() => input),
  }
  const windowRef = {
    addEventListener: vi.fn((event, handler) => {
      if (event === 'focus') focusHandler = handler
    }),
    removeEventListener: vi.fn((event, handler) => {
      if (event === 'focus' && focusHandler === handler) focusHandler = null
    }),
    dispatchFocus() {
      focusHandler?.()
    },
  }
  return { documentRef, input, windowRef }
}

afterEach(() => {
  vi.useRealTimers()
})

describe('chooseFiles', () => {
  it('resolves an empty list when the native dialog is cancelled', async () => {
    vi.useFakeTimers()
    const harness = createPickerHarness()
    const result = chooseFiles(
      { accept: 'video/*', multiple: false },
      harness,
    )

    harness.windowRef.dispatchFocus()
    await vi.advanceTimersByTimeAsync(300)

    await expect(result).resolves.toEqual([])
    expect(harness.input.click).toHaveBeenCalledOnce()
    expect(harness.input.accept).toBe('video/*')
    expect(harness.input.multiple).toBe(false)
    expect(harness.windowRef.removeEventListener).toHaveBeenCalled()
  })

  it('resolves selected files before the focus cancellation timeout', async () => {
    vi.useFakeTimers()
    const harness = createPickerHarness()
    const file = new File(['image'], 'sample.png', { type: 'image/png' })
    harness.input.files = [file]
    const result = chooseFiles({ accept: 'image/*', multiple: true }, harness)

    harness.input.onchange()
    await vi.advanceTimersByTimeAsync(300)

    await expect(result).resolves.toEqual([file])
  })
})
