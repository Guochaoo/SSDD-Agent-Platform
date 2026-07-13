import { beforeEach, describe, expect, it, vi } from 'vitest'

const request = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}))

vi.mock('@/utils/request', () => ({ default: request }))

import {
  downloadTrainingModel,
  downloadTrainingResults,
  exportTrainingModel,
  getTrainingMetrics,
  getTrainingStatus,
  getTrainingTasks,
  predictTrainingImage,
  startTraining,
  stopTraining,
  validateTrainingModel,
} from '@/api/training'

describe('training api', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('uses the six Day 6 training endpoints', async () => {
    const payload = { scene_id: 1, model_name: 'yolo11n' }

    await getTrainingTasks()
    await startTraining(payload)
    await getTrainingStatus(7)
    await getTrainingMetrics(7)
    await stopTraining(7)
    await downloadTrainingResults('task-abcd')

    expect(request.get).toHaveBeenNthCalledWith(1, '/training/tasks')
    expect(request.post).toHaveBeenNthCalledWith(1, '/training/start', payload)
    expect(request.get).toHaveBeenNthCalledWith(2, '/training/status/7')
    expect(request.get).toHaveBeenNthCalledWith(3, '/training/metrics/7')
    expect(request.post).toHaveBeenNthCalledWith(2, '/training/stop/7')
    expect(request.get).toHaveBeenNthCalledWith(4, '/training/results/task-abcd', {
      responseType: 'blob',
    })
  })

  it('uses the four Day 7 evaluation endpoints', async () => {
    const validatePayload = { split: 'val', conf: 0.001, iou: 0.6 }
    const exportPayload = { version: 'v1.0.0', set_default: true }
    const formData = new FormData()

    await validateTrainingModel(9, validatePayload)
    await exportTrainingModel(9, exportPayload)
    await downloadTrainingModel(9)
    await predictTrainingImage(formData)

    expect(request.post).toHaveBeenNthCalledWith(
      1,
      '/training/validate/9',
      validatePayload,
      { timeout: 300000 },
    )
    expect(request.post).toHaveBeenNthCalledWith(2, '/training/export/9', exportPayload)
    expect(request.get).toHaveBeenCalledWith('/training/download/9', {
      responseType: 'blob',
      timeout: 120000,
    })
    expect(request.post).toHaveBeenNthCalledWith(3, '/training/predict', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000,
    })
  })
})
