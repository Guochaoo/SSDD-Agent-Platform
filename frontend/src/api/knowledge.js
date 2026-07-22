import request from '@/utils/request'

export function getKnowledgeDocumentsApi() {
  return request.get('/knowledge/documents')
}

export function uploadKnowledgeDocumentApi(title, file) {
  const formData = new FormData()
  formData.append('title', title)
  formData.append('file', file)
  return request.post('/knowledge/documents', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
}

export function downloadKnowledgeDocumentApi(documentId) {
  return request.get(`/knowledge/documents/${documentId}/download`, { responseType: 'blob', timeout: 120000 })
}

export function deleteKnowledgeDocumentApi(documentId) {
  return request.delete(`/knowledge/documents/${documentId}`)
}
