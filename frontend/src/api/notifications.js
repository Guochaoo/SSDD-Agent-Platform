import request from '@/utils/request'

export function listNotificationsApi(params = {}) {
  return request.get('/notifications', { params })
}

export function markNotificationReadApi(id) {
  return request.post(`/notifications/${id}/read`)
}
