import request from '@/utils/request'

export function undoAction(undoId) {
  return request.post(`/undo/${encodeURIComponent(undoId)}`)
}
