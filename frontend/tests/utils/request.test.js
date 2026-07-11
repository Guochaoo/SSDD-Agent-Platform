import { beforeEach, describe, expect, it, vi } from 'vitest'

describe('request utility', () => {
  beforeEach(() => { vi.clearAllMocks(); localStorage.clear() })
  it('creates the axios instance with expected defaults', async () => {
    const { default: request } = await import('@/utils/request')
    expect(request).toBeDefined()
    expect(request.defaults.baseURL).toBe('/api')
    expect(request.defaults.timeout).toBe(30000)
    expect(request.defaults.headers['Content-Type']).toBe('application/json')
  })
})
