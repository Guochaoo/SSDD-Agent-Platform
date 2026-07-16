import { beforeEach, describe, expect, it, vi } from 'vitest'

const request = vi.hoisted(() => ({ get: vi.fn() }))
vi.mock('@/utils/request', () => ({ default: request }))

import { getModelsApi } from '@/api/models'

describe('model API', () => {
  beforeEach(() => vi.clearAllMocks())

  it('lists every non-deleted version for a scene instead of only its default', async () => {
    request.get.mockResolvedValue([
      { id: 1, version: 'v3.0.0', model_name: 'current', is_default: true, status: 'active' },
      { id: 2, version: 'v1.0.0', model_name: 'previous', is_default: false, status: 'active' },
    ])

    const models = await getModelsApi(7)

    expect(request.get).toHaveBeenCalledWith('/scenes/7/models')
    expect(models.map((model) => model.version)).toEqual(['v3.0.0', 'v1.0.0'])
  })
})
