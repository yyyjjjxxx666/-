<template>
  <div>
    <h2 style="margin-bottom:20px">📊 首页概览</h2>

    <!-- Admin View -->
    <template v-if="userStore.role === 'admin'">
      <el-row :gutter="16">
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card"><div class="stat-num">{{ stats.clubs }}</div><div class="stat-label">社团总数</div></el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card"><div class="stat-num">{{ stats.activities }}</div><div class="stat-label">活动总数</div></el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card"><div class="stat-num">{{ stats.members }}</div><div class="stat-label">成员总数</div></el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card"><div class="stat-num">{{ stats.ongoing_activities }}</div><div class="stat-label">进行中活动</div></el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top:20px">
        <el-col :span="12">
          <el-card>
            <template #header>📊 社团统计</template>
            <v-chart :option="clubChartOption" style="height:260px" autoresize />
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card>
            <template #header>👥 人员分布</template>
            <v-chart :option="memberChartOption" style="height:260px" autoresize />
          </el-card>
        </el-col>
      </el-row>
    </template>

    <!-- Non-Admin View -->
    <template v-else>
      <!-- Face Registration -->
      <el-card style="margin-bottom:16px">
        <template #header><span>👤 人脸信息</span></template>
        <el-row :gutter="16" align="middle">
          <el-col :span="8">
            <div v-if="faceError" style="padding:20px;text-align:center">
              <p style="color:#e6a23c">{{ faceError }}</p>
            </div>
            <video v-show="!faceError && faceCameraActive" ref="dashboardFaceVideo" autoplay playsinline
              style="width:100%;max-width:260px;height:200px;background:#000;border-radius:8px" />
            <img v-if="faceRegistered && !faceCameraActive"
              :src="`/uploads/faces/${userStore.userInfo.id}/face.jpg`"
              style="width:100%;max-width:200px;height:200px;object-fit:cover;border-radius:8px;border:2px solid #e8e8e8" />
            <div v-if="!faceRegistered && !faceCameraActive" style="width:200px;height:200px;background:#f0f0f0;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#999">
              未上传人脸
            </div>
          </el-col>
          <el-col :span="16">
            <div style="line-height:1.8">
              <p v-if="faceRegMsg" :style="{color: faceRegOk ? '#67c23a' : '#e6a23c', margin: '0 0 8px'}">{{ faceRegMsg }}</p>
              <p v-if="!faceRegistered" style="color:#e6a23c;margin:0 0 8px">⚠️ 您还未上传人脸信息，将影响签到使用</p>
              <el-button v-if="!faceRegistered || faceCameraActive" type="warning" :loading="faceRegLoading" @click="captureAndRegisterFace">
                📷 {{ faceCameraActive ? '确认拍照' : '拍照注册' }}
              </el-button>
              <div v-else>
                <el-tag type="success" size="large">✅ 已注册人脸</el-tag>
                <el-button size="small" style="margin-left:12px" @click="startFaceCamera">📷 更换人脸</el-button>
              </div>
            </div>
          </el-col>
        </el-row>
      </el-card>

      <!-- User Card -->
      <el-row :gutter="16" style="margin-bottom:16px">
        <el-col :span="12">
          <el-card>
            <div class="user-info">
              <h3>👤 {{ userStore.userInfo.real_name || userStore.userInfo.username }}</h3>
              <el-tag>{{ roleLabel }}</el-tag>
              <div class="user-id-area">
                <span class="id-label">我的ID：</span>
                <span class="id-value">{{ userStore.userInfo.id }}</span>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <!-- My Club -->
          <el-card v-if="myClub">
            <template #header>🏠 我的社团</template>
            <h4 style="cursor:pointer;color:#1e3c72" @click="$router.push(`/clubs/${myClub.id}`)">{{ myClub.name }}</h4>
            <p style="color:#888;font-size:13px;margin:4px 0">{{ myClub.description }}</p>
            <el-tag v-for="t in (myClub.tags||'').split(',').filter(Boolean)" :key="t" size="small" style="margin-right:4px">{{ t.trim() }}</el-tag>
          </el-card>
          <el-card v-else>
            <div style="text-align:center;padding:20px;color:#999">
              <p>📭 您还未加入任何社团</p>
              <p style="font-size:13px">前往 <el-link type="primary" @click="$router.push('/clubs')">社团管理</el-link> 加入或创建一个社团</p>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- Interests -->
      <el-card style="margin-bottom:16px">
        <template #header><span>🏷️ 我的兴趣</span></template>
        <div v-if="!editingInterests">
          <div v-if="userInterests" class="interests-display">
            <el-tag v-for="t in userInterests.split(',').filter(Boolean)" :key="t" style="margin-right:6px">{{ t.trim() }}</el-tag>
            <el-button size="small" text @click="startEditInterests">✏️ 编辑</el-button>
          </div>
          <div v-else>
            <el-alert title="您还未填写兴趣，智能推荐将不会生效" type="info" show-icon :closable="false" />
            <div style="margin-top:8px">
              <el-input v-model="interestInput" placeholder="输入兴趣标签，如：AI, 机器学习" style="width:320px" @keyup.enter="saveInterests" />
              <el-button type="primary" size="small" style="margin-left:8px" :loading="savingInterests" @click="saveInterests">保存</el-button>
            </div>
          </div>
        </div>
        <div v-else>
          <el-input v-model="interestInput" placeholder="输入兴趣标签，逗号分隔" style="width:320px" />
          <el-button type="primary" size="small" style="margin-left:8px" :loading="savingInterests" @click="saveInterests">保存</el-button>
          <el-button size="small" style="margin-left:4px" @click="editingInterests = false">取消</el-button>
        </div>
      </el-card>

      <!-- AI Recommendations -->
      <el-card v-if="userInterests" style="margin-bottom:16px">
        <template #header>
          <span>🎯 智能推荐</span>
          <el-button size="small" style="float:right" :loading="refreshingRecs" @click="refreshRecommendations">🔄 刷新推荐</el-button>
        </template>
        <el-row :gutter="12">
          <el-col v-for="rec in recommendations" :key="rec.club_id" :span="8">
            <el-card shadow="hover" class="rec-card" @click="$router.push(`/clubs/${rec.club_id}`)">
              <h4>{{ rec.club_name }}</h4>
              <p class="rec-reason">{{ rec.reason }}</p>
            </el-card>
          </el-col>
        </el-row>
        <el-empty v-if="!recommendations.length" description="暂无推荐" :image-size="60" />
      </el-card>

      <!-- Recent Activities -->
      <el-card>
        <template #header><span>📅 近期活动</span></template>
        <el-row :gutter="12">
          <el-col v-for="act in recentActivities" :key="act.id" :span="8">
            <el-card shadow="hover" class="activity-card" @click="$router.push(`/activities/${act.id}`)">
              <h4>{{ act.title }}</h4>
              <p class="act-location">📍 {{ act.location }}</p>
              <p class="act-time">🕐 {{ act.start_time }}</p>
              <el-tag size="small">{{ statusLabel(act.status) }}</el-tag>
            </el-card>
          </el-col>
        </el-row>
        <el-empty v-if="!recentActivities.length" description="暂无活动" :image-size="60" />
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { use } from 'echarts/core'
import { BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, TitleComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { useUserStore } from '../stores/user'
import { getClub, getActivities, getRecentActivities, getMe, updateInterests, faceRegister, aiRecommend, getAdminStats } from '../api'

use([BarChart, PieChart, GridComponent, TooltipComponent, TitleComponent, LegendComponent, CanvasRenderer])

const userStore = useUserStore()

const roleLabel = computed(() => {
  const map = { admin: '管理员', president: '社团负责人', member: '成员' }
  return map[userStore.role] || userStore.role
})
const statusLabel = (s) => ({ pending: '待审批', approved: '已通过', registration: '报名中', ongoing: '进行中', finished: '已结束' }[s] || s)

// Admin stats
const stats = reactive({ clubs: 0, activities: 0, members: 0, ongoing_activities: 0, approved_clubs: 0, pending_clubs: 0, presidents: 0 })
const clubChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: ['已通过', '待审批', '总数'] },
  yAxis: { type: 'value' },
  series: [{ type: 'bar', data: [stats.approved_clubs, stats.pending_clubs, stats.clubs], itemStyle: { color: '#1e3c72' }, barWidth: '40%' }],
}))
const memberChartOption = computed(() => ({
  tooltip: { trigger: 'item' },
  series: [{
    type: 'pie', radius: ['40%', '70%'],
    data: [
      { value: stats.members, name: '普通成员' },
      { value: stats.presidents, name: '社团负责人' },
    ],
    label: { formatter: '{b}: {c}' },
  }],
}))

// Non-admin state
const dashboardFaceVideo = ref(null)
const faceRegistered = ref(false)
const faceRegLoading = ref(false)
const faceRegMsg = ref('')
const faceRegOk = ref(false)
const faceCameraActive = ref(false)
const faceError = ref('')
let dashboardFaceStream = null
const userInterests = ref('')
const interestInput = ref('')
const editingInterests = ref(false)
const savingInterests = ref(false)
const recommendations = ref([])
const refreshingRecs = ref(false)
const recentActivities = ref([])
const myClub = ref(null)

const fetchAdminStats = async () => {
  try {
    const { data } = await getAdminStats()
    Object.assign(stats, data)
  } catch {}
}

// Face camera
const stopDashboardCamera = () => {
  if (dashboardFaceStream) { dashboardFaceStream.getTracks().forEach(t => t.stop()); dashboardFaceStream = null }
  faceCameraActive.value = false
  if (dashboardFaceVideo.value) dashboardFaceVideo.value.srcObject = null
}

const startFaceCamera = async () => {
  stopDashboardCamera()
  faceError.value = ''
  faceRegMsg.value = ''
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, facingMode: 'user' } })
    dashboardFaceStream = stream
    dashboardFaceVideo.value.srcObject = stream
    faceCameraActive.value = true
  } catch (err) {
    if (err.name === 'NotAllowedError') faceError.value = '摄像头权限被拒绝，请在浏览器设置中允许'
    else if (err.name === 'NotFoundError') faceError.value = '未检测到摄像头设备'
    else faceError.value = '无法访问摄像头'
  }
}

const captureFrameDashboard = () => {
  const video = dashboardFaceVideo.value
  const canvas = document.createElement('canvas')
  canvas.width = video.videoWidth || 640
  canvas.height = video.videoHeight || 480
  canvas.getContext('2d').drawImage(video, 0, 0)
  return canvas.toDataURL('image/jpeg', 0.8).split(',')[1]
}

const captureAndRegisterFace = async () => {
  if (faceCameraActive.value) {
    // Camera already on, capture and register
    faceRegLoading.value = true
    try {
      const base64 = captureFrameDashboard()
      const { data } = await faceRegister({ user_id: userStore.userInfo.id, image_data: base64 })
      faceRegMsg.value = data.message || (data.success ? '注册成功' : '失败')
      faceRegOk.value = data.success
      if (data.success) {
        faceRegistered.value = true
        ElMessage.success('人脸注册成功！')
      }
    } catch { faceRegMsg.value = '人脸注册请求失败'; faceRegOk.value = false }
    stopDashboardCamera()
    faceRegLoading.value = false
  } else {
    // Start camera first
    await startFaceCamera()
  }
}

const fetchUserData = async () => {
  try {
    const { data } = await getMe()
    userInterests.value = data.interests || ''
    if (data.interests) interestInput.value = data.interests
    faceRegistered.value = data.face_registered
    if (data.interests) {
      try { const rec = await aiRecommend({ user_id: data.id, top_k: 6 }); recommendations.value = rec.data.recommendations || [] } catch {}
    }
    // Fetch my club if I have one
    if (data.club_id) {
      try { const c = await getClub(data.club_id); myClub.value = c.data } catch { myClub.value = null }
    }
  } catch {}
}

const fetchRecentActivities = async () => {
  try { const { data } = await getRecentActivities(); recentActivities.value = data } catch {}
}

const startEditInterests = () => { interestInput.value = userInterests.value || ''; editingInterests.value = true }
const saveInterests = async () => {
  savingInterests.value = true
  try {
    await updateInterests({ interests: interestInput.value })
    userInterests.value = interestInput.value; editingInterests.value = false
    try { const rec = await aiRecommend({ user_id: userStore.userInfo.id, top_k: 6 }); recommendations.value = rec.data.recommendations || [] } catch {}
  } catch {} finally { savingInterests.value = false }
}
const refreshRecommendations = async () => {
  refreshingRecs.value = true
  try { const rec = await aiRecommend({ user_id: userStore.userInfo.id, top_k: 6 }); recommendations.value = rec.data.recommendations || [] } catch {}
  finally { refreshingRecs.value = false }
}

onMounted(() => {
  if (userStore.role === 'admin') fetchAdminStats()
  else fetchUserData()
  fetchRecentActivities()
})

onBeforeUnmount(() => {
  stopDashboardCamera()
})
</script>

<style scoped>
.stat-card { text-align: center; }
.stat-num { font-size: 36px; font-weight: bold; color: #1e3c72; }
.stat-label { color: #888; margin-top: 8px; }
.user-info h3 { margin: 0 0 8px; }
.user-id-area { margin-top: 12px; padding: 10px; background: #f0f7ff; border-radius: 8px; display: flex; align-items: center; }
.id-label { color: #666; font-size: 14px; }
.id-value { font-size: 28px; font-weight: bold; color: #1e3c72; margin-left: 8px; }
.interests-display { display: flex; align-items: center; flex-wrap: wrap; }
.rec-card { cursor: pointer; border: 1px solid #e8e8e8; transition: all .2s; }
.rec-card:hover { border-color: #1e3c72; box-shadow: 0 2px 8px rgba(30,60,114,.15); }
.rec-card h4 { margin: 0 0 8px; }
.rec-reason { color: #888; font-size: 13px; margin: 0; }
.activity-card { cursor: pointer; border: 1px solid #e8e8e8; transition: all .2s; }
.activity-card:hover { border-color: #1e3c72; box-shadow: 0 2px 8px rgba(30,60,114,.15); }
.activity-card h4 { margin: 0 0 8px; }
.act-location, .act-time { color: #888; font-size: 13px; margin: 4px 0; }
</style>
