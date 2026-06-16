<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">
        <el-icon :size="22"><Camera /></el-icon>
        签到考勤
      </h2>
    </div>

    <div class="glass-card checkin-card" style="cursor:default">
      <el-tabs v-model="tab" class="modern-tabs">
        <!-- QR Check-in -->
        <el-tab-pane name="qr">
          <template #label>
            <span class="tab-label"><el-icon :size="16"><Iphone /></el-icon> 扫码签到</span>
          </template>
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="glass-card inner-card" style="cursor:default">
                <div class="section-title">
                  <el-icon :size="18"><List /></el-icon>
                  <span>选择签到活动</span>
                </div>
                <el-select v-model="qrActivityId" placeholder="选择活动" style="width:100%" size="large" @change="loadQRCode">
                  <el-option v-for="a in activeActivities" :key="a.id" :label="a.title" :value="a.id" />
                </el-select>
                <div v-if="qrUrl" class="qr-display">
                  <p class="qr-hint">请用手机扫描二维码签到</p>
                  <div class="qr-img-wrap">
                    <img :src="qrUrl" alt="签到二维码" />
                  </div>
                  <el-tag type="success" size="large" round>已签到: {{ checkinCount }}</el-tag>
                </div>
                <el-empty v-if="qrActivityId && !qrUrl" description="该活动暂无签到码" />
              </div>
            </el-col>
            <el-col :span="12">
              <div class="glass-card inner-card" style="cursor:default">
                <div class="section-title">
                  <el-icon :size="18"><EditPen /></el-icon>
                  <span>手动签到</span>
                  <el-tag size="small" round>管理员/负责人</el-tag>
                </div>
                <div class="manual-section">
                  <p class="manual-label">搜索用户签到</p>
                  <div class="manual-row">
                    <el-autocomplete
                      v-model="searchKeyword"
                      :fetch-suggestions="searchUsersByName"
                      :trigger-on-focus="false"
                      placeholder="输入姓名/学号搜索..."
                      size="large"
                      style="flex:1"
                      clearable
                      @select="onUserSelect"
                    >
                      <template #default="{ item }">
                        <div class="user-search-item">
                          <span class="user-name">{{ item.value }}</span>
                          <span class="user-meta">{{ item.student_id || '' }} {{ item.club_name ? '· ' + item.club_name : '' }}</span>
                        </div>
                      </template>
                    </el-autocomplete>
                    <el-button type="primary" size="large" @click="handleManualCheckin" :disabled="!selectedUserId">
                      <el-icon :size="16"><Select /></el-icon> 签到
                    </el-button>
                  </div>
                  <p v-if="selectedUserName" class="selected-user-hint">
                    已选择：<strong>{{ selectedUserName }}</strong> (ID: {{ selectedUserId }})
                  </p>
                </div>
              </div>
            </el-col>
          </el-row>
        </el-tab-pane>

        <!-- Face Check-in -->
        <el-tab-pane name="face">
          <template #label>
            <span class="tab-label"><el-icon :size="16"><UserFilled /></el-icon> 人脸签到</span>
          </template>
          <div class="face-panel glass-card inner-card" style="max-width:640px;cursor:default">
            <div class="section-title">
              <el-icon :size="18"><Camera /></el-icon>
              <span>人脸签到</span>
            </div>
            <p class="face-note">请先在首页注册人脸信息</p>
            <div v-if="cameraError" class="camera-error">
              <el-icon :size="36"><WarningFilled /></el-icon>
              <p>{{ cameraError }}</p>
              <el-button type="primary" @click="startCamera(checkinVideo)">
                <el-icon :size="14"><Refresh /></el-icon> 重试
              </el-button>
            </div>
            <video v-show="!cameraError" ref="checkinVideo" autoplay playsinline class="face-video" />
            <p v-if="cameraReady && !cameraError" class="camera-ready">
              <el-icon :size="14"><Select /></el-icon> 摄像头已就绪
            </p>
            <el-select v-model="faceActivityId" placeholder="选择活动" size="large" style="width:100%;margin-top:12px">
              <el-option v-for="a in activeActivities" :key="a.id" :label="a.title" :value="a.id" />
            </el-select>
            <el-button type="primary" size="large" :loading="faceLoading" :disabled="!cameraReady" @click="captureAndCheckin" class="capture-btn">
              <el-icon :size="18"><Camera /></el-icon>
              {{ cameraReady ? '拍照签到' : '等待摄像头就绪...' }}
            </el-button>
            <p v-if="checkinMsg" class="checkin-msg" :class="{ ok: checkinOk, err: !checkinOk }">{{ checkinMsg }}</p>
          </div>
        </el-tab-pane>

        <!-- Records -->
        <el-tab-pane name="records">
          <template #label>
            <span class="tab-label"><el-icon :size="16"><List /></el-icon> 签到记录</span>
          </template>
          <el-table :data="records" border stripe class="modern-table">
            <el-table-column prop="activity_id" label="活动ID" width="80" />
            <el-table-column prop="user_id" label="用户ID" width="80" />
            <el-table-column prop="checkin_time" label="签到时间" width="180" />
            <el-table-column prop="method" label="签到方式" width="100">
              <template #default="{ row }">
                <el-tag :type="row.method === 'face' ? 'success' : 'primary'" round>{{ row.method === 'face' ? '人脸' : '扫码' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getActivities, faceRecognize, checkin, manualCheckin, searchUsers } from '../api'
import { useUserStore } from '../stores/user'

const userStore = useUserStore(); const route = useRoute()
const tab = ref('qr'); const activeActivities = ref([])

// QR
const qrActivityId = ref(null); const qrUrl = ref(''); const checkinCount = ref(0)
const searchKeyword = ref(''); const selectedUserId = ref(null); const selectedUserName = ref('')

// Face
const checkinVideo = ref(null); const faceActivityId = ref(null)
const checkinMsg = ref(''); const checkinOk = ref(false); const faceLoading = ref(false)
const cameraError = ref(''); const cameraReady = ref(false); let checkinStream = null

// Records
const records = ref([])

const fetchActivities = async () => {
  try { const { data } = await getActivities(); activeActivities.value = data.filter(a => ['registration', 'ongoing'].includes(a.status)) } catch { ElMessage.error('获取活动列表失败') }
}
const loadQRCode = () => {
  const act = activeActivities.value.find(a => a.id === qrActivityId.value)
  if (act) { qrUrl.value = act.checkin_qr || ''; checkinCount.value = act.current_participants || 0 }
}
const searchUsersByName = async (queryString, cb) => {
  if (!queryString || queryString.trim().length === 0) return cb([])
  try {
    const { data } = await searchUsers(queryString.trim())
    const suggestions = (data || []).map(u => ({
      value: u.real_name || u.username,
      id: u.id,
      student_id: u.student_id || '',
      club_name: u.club_name || '',
      username: u.username,
    }))
    cb(suggestions)
  } catch { cb([]) }
}

const onUserSelect = (item) => {
  selectedUserId.value = item.id
  selectedUserName.value = item.value
}

const handleManualCheckin = async () => {
  if (!qrActivityId.value) return ElMessage.warning('请选择活动')
  if (!selectedUserId.value) return ElMessage.warning('请搜索并选择用户')
  try {
    await manualCheckin(qrActivityId.value, selectedUserId.value, 'qr')
    ElMessage.success(`${selectedUserName.value} 签到成功`)
    searchKeyword.value = ''; selectedUserId.value = null; selectedUserName.value = ''
    loadQRCode()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '签到失败') }
}

// Face
const startCamera = async (videoEl) => {
  try {
    if (!navigator.mediaDevices?.getUserMedia) { cameraError.value = '浏览器不支持摄像头'; return null }
    const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, facingMode: 'user' } })
    const ready = new Promise((resolve) => { videoEl.onloadedmetadata = () => { videoEl.play().then(() => setTimeout(resolve, 800)).catch(() => resolve()) } })
    videoEl.srcObject = stream; cameraError.value = ''
    await ready; cameraReady.value = true; checkinStream = stream
    return stream
  } catch (err) {
    cameraError.value = '无法访问摄像头: ' + (err.message || '未知错误')
    return null
  }
}
const stopCamera = () => {
  if (checkinStream) { checkinStream.getTracks().forEach(t => t.stop()); checkinStream = null }
  if (checkinVideo.value) checkinVideo.value.srcObject = null
  cameraReady.value = false
}
const captureFrame = (videoEl) => {
  const canvas = document.createElement('canvas')
  canvas.width = videoEl.videoWidth || 640; canvas.height = videoEl.videoHeight || 480
  canvas.getContext('2d').drawImage(videoEl, 0, 0)
  return canvas.toDataURL('image/jpeg', 0.8).split(',')[1]
}
const captureAndCheckin = async () => {
  if (!faceActivityId.value) return ElMessage.warning('请选择活动')
  if (!cameraReady.value || !checkinStream) { ElMessage.warning('摄像头未就绪'); return }
  faceLoading.value = true; checkinMsg.value = ''
  try {
    const base64 = captureFrame(checkinVideo.value)
    const { data: faceData } = await faceRecognize({ image_data: base64 })
    if (!faceData.success || !faceData.user_id) { checkinMsg.value = faceData.message || '人脸不匹配'; checkinOk.value = false; ElMessage.error(checkinMsg.value); return }
    if (faceData.user_id !== userStore.userInfo.id) { checkinMsg.value = '人脸与当前登录用户不匹配'; checkinOk.value = false; ElMessage.error(checkinMsg.value); return }
    await checkin(faceActivityId.value, 'face')
    checkinMsg.value = `签到成功！置信度: ${faceData.confidence}%`; checkinOk.value = true; ElMessage.success('人脸签到成功！')
  } catch (err) { const detail = err?.response?.data?.detail; if (detail) ElMessage.error(detail) } finally { faceLoading.value = false }
}

watch(tab, async (val) => {
  if (val === 'face') { cameraError.value = ''; cameraReady.value = false; if (!checkinStream) { await new Promise(r => setTimeout(r, 200)); if (checkinVideo.value) { checkinStream = await startCamera(checkinVideo.value) } } } else { stopCamera() }
})

onMounted(() => { if (route.query.tab === 'face') tab.value = 'face'; fetchActivities() })
onBeforeUnmount(() => { stopCamera() })
</script>

<style scoped>
.page-container { max-width: 1200px; margin: 0 auto; }
.page-header { margin-bottom: 20px; }
.page-title { display: flex; align-items: center; gap: 10px; font-size: var(--text-2xl); font-weight: var(--font-bold); color: var(--text-primary); margin: 0; }
.checkin-card { padding: 24px; }
.tab-label { display: flex; align-items: center; gap: 6px; }
.inner-card { padding: 24px; margin-bottom: 0; }
.section-title { display: flex; align-items: center; gap: 8px; font-size: var(--text-base); font-weight: var(--font-semibold); color: var(--text-primary); margin-bottom: 16px; }

/* QR */
.qr-display { text-align: center; margin-top: 24px; }
.qr-hint { color: var(--text-muted); margin-bottom: 16px; font-size: var(--text-sm); }
.qr-img-wrap { display: inline-block; padding: 16px; background: #fff; border-radius: var(--radius-lg); border: 2px solid var(--border-light); margin-bottom: 16px; }
.qr-img-wrap img { width: 256px; height: 256px; display: block; }
.manual-section { margin-top: 12px; }
.manual-label { color: var(--text-secondary); font-size: var(--text-sm); margin-bottom: 8px; }
.manual-row { display: flex; gap: 8px; }
.user-search-item { display: flex; align-items: center; justify-content: space-between; width: 100%; }
.user-name { font-size: var(--text-sm); color: var(--text-primary); }
.user-meta { font-size: var(--text-xs); color: var(--text-muted); }
.selected-user-hint { margin-top: 8px; font-size: var(--text-sm); color: var(--color-success-600); }
[data-theme="dark"] .selected-user-hint { color: var(--color-success-400); }

/* Face */
.face-panel { margin: 0 auto; }
.face-note { color: var(--text-muted); font-size: var(--text-sm); margin-bottom: 12px; }
.face-video { width: 100%; max-width: 500px; height: 280px; background: #000; border-radius: var(--radius-md); object-fit: cover; display: block; margin: 0 auto; }
.camera-ready { color: var(--color-success-500); margin-top: 8px; display: flex; align-items: center; gap: 4px; justify-content: center; font-size: var(--text-sm); }
.camera-error { padding: 32px 20px; text-align: center; color: var(--color-warning-500); display: flex; flex-direction: column; align-items: center; gap: 12px; }
.capture-btn { width: 100%; margin-top: 12px; height: 48px; font-size: var(--text-base); }
.checkin-msg { margin-top: 12px; text-align: center; font-size: var(--text-sm); }
.checkin-msg.ok { color: var(--color-success-500); }
.checkin-msg.err { color: var(--color-warning-500); }

/* Tabs */
.modern-tabs :deep(.el-tabs__active-bar) { background: var(--gradient-primary) !important; height: 3px !important; border-radius: var(--radius-full); }
.modern-tabs :deep(.el-tabs__item) { font-size: var(--text-sm); color: var(--text-muted); }
.modern-tabs :deep(.el-tabs__item):hover { color: var(--color-primary-500); }
.modern-tabs :deep(.el-tabs__item.is-active) { color: var(--color-primary-600); font-weight: var(--font-semibold); }
.modern-tabs :deep(.el-tabs__nav-wrap::after) { background: var(--border-light); }
.modern-table :deep(.el-table__header th) { background: var(--bg-secondary); color: var(--text-primary); font-weight: var(--font-semibold); }
.modern-table :deep(.el-table__body tr:hover > td) { background: var(--color-primary-50) !important; }
[data-theme="dark"] .modern-table :deep(.el-table__body tr:hover > td) { background: rgba(124, 58, 237, 0.08) !important; }
[data-theme="dark"] .qr-img-wrap { background: #fff; }
</style>
