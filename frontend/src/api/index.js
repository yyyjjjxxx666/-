import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const detail = err.response?.data?.detail
    let msg
    if (detail) {
      msg = detail
    } else if (!err.response) {
      msg = '网络连接失败，请检查网络'
    } else {
      const statusMap = { 400: '请求参数错误', 403: '权限不足', 404: '资源不存在', 500: '服务器错误，请稍后重试', 503: '服务暂不可用' }
      msg = statusMap[err.response.status] || `服务器错误(${err.response.status})`
    }
    ElMessage.error(msg)
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.hash = '#/login'
    }
    return Promise.reject(err)
  }
)

// ── Auth ──
export const login = (data) => api.post('/auth/login', data)
export const register = (data) => api.post('/auth/register', data)

// ── Clubs ──
export const getClubs = (params) => api.get('/clubs', { params })
export const getClub = (id) => api.get(`/clubs/${id}`)
export const createClub = (data) => api.post('/clubs', data)
export const approveClub = (id) => api.put(`/clubs/${id}/approve`)

// ── Activities ──
export const getActivities = (params) => api.get('/activities', { params })
export const getActivity = (id) => api.get(`/activities/${id}`)
export const createActivity = (data) => api.post('/activities', data)
export const registerActivity = (id) => api.post(`/activities/${id}/register`)
export const checkin = (id, method = 'qr') => api.post(`/activities/${id}/checkin`, null, { params: { method } })
export const manualCheckin = (id, targetUserId, method = 'qr') => api.post(`/activities/${id}/checkin/manual`, null, { params: { target_user_id: targetUserId, method } })

// ── AI ──
export const aiRecommend = (data) => api.post('/ai/recommend', data)
export const aiGenerateCopy = (data) => api.post('/ai/generate-copy', data)
export const aiGeneratePoster = (data) => api.post('/ai/generate-poster-content', data)
export const aiStarRating = (data) => api.post('/ai/star-rating', data)
export const aiRecommendFeedback = (data) => api.post('/ai/recommend/feedback', data)
export const aiRecommendActivities = (data) => api.post('/ai/activities/recommend', data)
export const aiAssistantChat = (q) => fetch(`/api/ai/assistant/chat?q=${encodeURIComponent(q)}`, {
  headers: { 'Authorization': `Bearer ${localStorage.getItem('token') || ''}` }
})

// ── Face ──
export const faceRegister = (data) => api.post('/ai/face-register', data)
export const faceRecognize = (data) => api.post('/ai/face-recognize', data)

// ── Notifications ──
export const getNotifications = (params) => api.get('/notifications', { params })
export const sendNotification = (data) => api.post('/notifications', data)
export const markRead = (id) => api.put(`/notifications/${id}/read`)
export const markAllRead = () => api.put('/notifications/read-all')
export const deleteReadNotifications = () => api.delete('/notifications/read')
export const getUnreadCount = () => api.get('/notifications/unread-count')
export const aiGenerateNotification = (data) => api.post('/notifications/ai-generate', data)
export const aiNotificationDigest = () => api.get('/notifications/ai-digest')

// ── Semantic Search ──
export const aiSearch = (params) => api.get('/ai/search', { params })
export const aiSearchReindex = () => api.post('/ai/search/reindex')

// ── AI Content Generation ──
export const aiSuggestTags = (data) => api.post('/ai/suggest-tags', data)
export const aiGenerateDescription = (data) => api.post('/ai/generate-description', data)
export const aiGenerateActivitySummary = (data) => api.post('/ai/generate-activity-summary', data)

// ── Admin ──
export const getPendingItems = () => api.get('/admin/pending-items')
export const getPendingCount = () => api.get('/admin/pending-count')
export const getAdminStats = () => api.get('/admin/stats')
export const getAIInsights = () => api.get('/admin/ai-insights')
export const approveActivityApi = (id) => api.put(`/admin/activities/${id}/approve`)
export const rejectActivityApi = (id) => api.put(`/admin/activities/${id}/reject`)
export const rejectClubApi = (id) => api.put(`/admin/clubs/${id}/reject`)

// ── Club operations ──
export const leaveClub = (id) => api.post(`/clubs/${id}/leave`)
export const transferClub = (id, data) => api.post(`/clubs/${id}/transfer`, data)
export const dissolveClub = (id) => api.post(`/clubs/${id}/dissolve`)
export const getClubMembers = (id) => api.get(`/clubs/${id}/members`)

// ── Activity operations ──
export const getAttendance = (id) => api.get(`/activities/${id}/attendance`)
export const generateQR = (id) => api.post(`/activities/${id}/generate-qr`)
export const getCheckins = (id) => api.get(`/activities/${id}/checkins`)
export const updateActivityStatus = (id, status) => api.put(`/activities/${id}/status`, null, { params: { status } })

// ── Auth/Profile ──
export const getMe = () => api.get('/auth/me')
export const updateInterests = (data) => api.put('/auth/interests', data)
export const checkFace = (userId) => api.get(`/auth/check-face/${userId}`)
export const resetPassword = (data) => api.post('/auth/reset-password', data)

// ── Upload ──
export const uploadFile = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
}

// ── Join Requests ──
export const sendJoinRequest = (clubId) => api.post(`/clubs/${clubId}/join`)
export const getMyPendingRequests = () => api.get('/clubs/my-pending-requests')
export const getJoinRequests = (clubId, params) => api.get(`/clubs/${clubId}/join-requests`, { params })
export const handleJoinRequest = (clubId, requestId, data) => api.put(`/clubs/${clubId}/join-requests/${requestId}`, data)
export const kickMember = (clubId, userId) => api.post(`/clubs/${clubId}/kick/${userId}`)

// ── AI Poster Preview ──
export const aiGeneratePosterPreview = (data) => api.post('/ai/generate-poster-preview', data)

// ── Home ──
export const getRecentActivities = () => api.get('/home/recent-activities')

// ── Knowledge Base ──
export const kbAddDoc = (data) => api.post('/ai/knowledge/add', data)
export const kbUploadDoc = (formData) => api.post('/ai/knowledge/upload', formData)
export const kbQuery = (params) => api.get('/ai/knowledge/query', { params })
export const kbDeleteDoc = (id) => api.delete(`/ai/knowledge/${id}`)
export const kbListDocs = () => api.get('/ai/knowledge/documents')
export const kbStats = () => api.get('/ai/knowledge/stats')
export default api
