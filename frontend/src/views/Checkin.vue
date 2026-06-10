<template>
  <div>
    <div class="page-header">
      <h2>📷 签到考勤</h2>
    </div>

    <el-tabs v-model="tab">
      <!-- QR Code Check-in -->
      <el-tab-pane label="📱 扫码签到" name="qr">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-card>
              <template #header>选择要签到的活动</template>
              <el-select v-model="qrActivityId" placeholder="选择活动" style="width:100%" @change="loadQRCode">
                <el-option v-for="a in activeActivities" :key="a.id" :label="a.title" :value="a.id" />
              </el-select>
              <div v-if="qrUrl" style="text-align:center; margin-top:20px">
                <p style="margin-bottom:12px; color:#888">请用手机扫描二维码签到</p>
                <img :src="qrUrl" style="width:256px; height:256px; border:2px solid #e8e8e8; border-radius:8px" />
                <p style="margin-top:12px">
                  <el-tag type="success">已签到: {{ checkinCount }}</el-tag>
                </p>
              </div>
              <el-empty v-if="qrActivityId && !qrUrl" description="该活动暂无签到码" />
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card>
              <template #header>手动签到（管理员/负责人）</template>
              <el-form :inline="true">
                <el-form-item label="用户名">
                  <el-input v-model="manualUsername" placeholder="输入成员用户名" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :loading="manualLoading" @click="handleManualCheckin">确认签到</el-button>
                </el-form-item>
              </el-form>
              <el-divider />
              <p style="color:#888">或输入用户ID直接签到</p>
              <el-form :inline="true">
                <el-form-item label="用户ID">
                  <el-input-number v-model="manualUserId" :min="1" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="handleManualCheckinById">签到</el-button>
                </el-form-item>
              </el-form>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- Face Recognition Check-in -->
      <el-tab-pane label="👤 人脸签到" name="face">
        <el-card style="max-width:600px">
          <template #header>人脸签到</template>
          <p style="margin-bottom:8px; color:#888">请先在首页注册人脸信息</p>
          <div v-if="cameraError" style="padding:20px;text-align:center">
            <p style="color:#e6a23c;margin-bottom:12px">⚠️ {{ cameraError }}</p>
          </div>
          <video v-show="!cameraError" ref="checkinVideo" autoplay playsinline style="width:100%; height:260px; background:#000; border-radius:8px" />
          <el-select v-model="faceActivityId" placeholder="选择活动" style="width:100%; margin-top:12px">
            <el-option v-for="a in activeActivities" :key="a.id" :label="a.title" :value="a.id" />
          </el-select>
          <el-button type="primary" size="large" :loading="faceLoading" @click="captureAndCheckin" style="margin-top:12px; width:100%">
            拍照签到
          </el-button>
          <p v-if="checkinMsg" style="margin-top:8px" :style="{color: checkinOk ? '#67c23a' : '#e6a23c'}">{{ checkinMsg }}</p>
        </el-card>
      </el-tab-pane>

      <!-- Check-in Records -->
      <el-tab-pane label="📋 签到记录" name="records">
        <el-card>
          <el-table :data="records" border stripe>
            <el-table-column prop="activity_id" label="活动ID" width="80" />
            <el-table-column prop="user_id" label="用户ID" width="80" />
            <el-table-column prop="checkin_time" label="签到时间" width="180" />
            <el-table-column prop="method" label="签到方式" width="100">
              <template #default="{ row }">
                <el-tag :type="row.method === 'face' ? 'success' : 'primary'">{{ row.method === 'face' ? '人脸' : '扫码' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" />
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getActivities, faceRecognize, checkin, manualCheckin } from '../api'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
const route = useRoute()
const tab = ref('qr')
const activeActivities = ref([])

// QR
const qrActivityId = ref(null)
const qrUrl = ref('')
const checkinCount = ref(0)
const manualUsername = ref('')
const manualUserId = ref(null)
const manualLoading = ref(false)

// Face
const checkinVideo = ref(null)
const faceActivityId = ref(null)
const checkinMsg = ref('')
const checkinOk = ref(false)
const faceLoading = ref(false)
const cameraError = ref('')
let checkinStream = null

// Records
const records = ref([])

const fetchActivities = async () => {
  try {
    const { data } = await getActivities()
    activeActivities.value = data.filter(a => ['registration', 'ongoing'].includes(a.status))
  } catch { ElMessage.error('获取活动列表失败') }
}

const loadQRCode = () => {
  const act = activeActivities.value.find(a => a.id === qrActivityId.value)
  if (act) {
    qrUrl.value = act.checkin_qr || ''
    checkinCount.value = act.current_participants || 0
  }
}

const handleManualCheckin = async () => {
  if (!qrActivityId.value || !manualUsername.value) return ElMessage.warning('请选择活动并输入用户名')
  ElMessage.info('请使用用户ID签到，或通过用户管理查找ID')
}

const handleManualCheckinById = async () => {
  if (!qrActivityId.value || !manualUserId.value) return ElMessage.warning('请选择活动并输入用户ID')
  try {
    await manualCheckin(qrActivityId.value, manualUserId.value, 'qr')
    ElMessage.success('手动签到成功')
    loadQRCode()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '签到失败')
  }
}

// Face Recognition
const startCamera = async (videoEl) => {
  try {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      cameraError.value = '当前浏览器不支持摄像头，请使用Chrome/Edge等现代浏览器'
      return null
    }
    const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, facingMode: 'user' } })
    videoEl.srcObject = stream
    cameraError.value = ''
    return stream
  } catch (err) {
    if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
      cameraError.value = '摄像头权限被拒绝，请在浏览器设置中允许摄像头访问'
    } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
      cameraError.value = '未检测到摄像头设备，请确认摄像头已连接'
    } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
      cameraError.value = '摄像头被其他应用占用，请关闭其他使用摄像头的程序'
    } else if (err.name === 'OverconstrainedError') {
      cameraError.value = '摄像头分辨率不支持，请尝试其他摄像头'
    } else if (err.name === 'SecurityError') {
      cameraError.value = '摄像头需要HTTPS安全连接，请使用 https:// 或 localhost 访问'
    } else {
      cameraError.value = '无法访问摄像头: ' + (err.message || '未知错误')
    }
    return null
  }
}

const stopCamera = () => {
  if (checkinStream) { checkinStream.getTracks().forEach(t => t.stop()); checkinStream = null }
  if (checkinVideo.value) checkinVideo.value.srcObject = null
}

const captureFrame = (videoEl) => {
  const canvas = document.createElement('canvas')
  canvas.width = videoEl.videoWidth || 640
  canvas.height = videoEl.videoHeight || 480
  canvas.getContext('2d').drawImage(videoEl, 0, 0)
  return canvas.toDataURL('image/jpeg', 0.8).split(',')[1]
}

const captureAndCheckin = async () => {
  if (!faceActivityId.value) return ElMessage.warning('请选择活动')
  stopCamera()
  checkinStream = await startCamera(checkinVideo.value)
  if (!checkinStream) return
  faceLoading.value = true
  try {
    const base64 = captureFrame(checkinVideo.value)
    const { data: faceData } = await faceRecognize({ image_data: base64 })
    if (!faceData.success || !faceData.user_id) {
      checkinMsg.value = faceData.message || '人脸不匹配，请重试'
      checkinOk.value = false
      ElMessage.error(checkinMsg.value)
      return
    }
    await checkin(faceActivityId.value, 'face')
    checkinMsg.value = `签到成功！置信度: ${faceData.confidence}%`
    checkinOk.value = true
    ElMessage.success('人脸签到成功！')
  } catch (err) {
    const detail = err?.response?.data?.detail
    if (detail) ElMessage.error(detail)
  } finally { faceLoading.value = false; stopCamera() }
}

onMounted(() => {
  if (route.query.tab === 'face') tab.value = 'face'
  fetchActivities()
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
</style>
