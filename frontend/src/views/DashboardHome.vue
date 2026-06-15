<template>
  <div class="dashboard-home">
    <div class="page-header">
      <h2 class="page-title">
        <el-icon :size="24"><DataAnalysis /></el-icon>
        首页概览
      </h2>
    </div>

    <!-- ── Admin View ── -->
    <template v-if="userStore.role === 'admin'">
      <!-- Stat Cards Bento Grid -->
      <div class="stat-grid animate-stagger">
        <div class="stat-card gradient-border-top" v-for="s in statItems" :key="s.key">
          <div class="stat-icon" :style="{ background: s.gradient }">
            <el-icon :size="22"><component :is="s.icon" /></el-icon>
          </div>
          <div class="stat-body">
            <div class="stat-num">{{ stats[s.key] }}</div>
            <div class="stat-label">{{ s.label }}</div>
          </div>
        </div>
      </div>

      <!-- Charts Row -->
      <el-row :gutter="20" style="margin-top:20px">
        <el-col :span="12">
          <div class="chart-card glass-card" style="cursor:default">
            <div class="chart-card-header">
              <el-icon :size="18"><TrendCharts /></el-icon>
              <span>社团统计</span>
            </div>
            <v-chart :option="clubChartOption" style="height:280px" autoresize />
          </div>
        </el-col>
        <el-col :span="12">
          <div class="chart-card glass-card" style="cursor:default">
            <div class="chart-card-header">
              <el-icon :size="18"><UserFilled /></el-icon>
              <span>人员分布</span>
            </div>
            <v-chart :option="memberChartOption" style="height:280px" autoresize />
          </div>
        </el-col>
      </el-row>

      <!-- AI Insights -->
      <div v-if="aiInsights" class="insights-card glass-card" style="margin-top:20px; cursor:default">
        <div class="insights-header">
          <div class="insights-title">
            <el-icon :size="20"><Cpu /></el-icon>
            <span>AI 智能洞察</span>
          </div>
          <el-button size="small" class="refresh-btn" :loading="insightsLoading" @click="fetchAIInsights">
            <el-icon :size="14"><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
        <p class="insight-summary">{{ aiInsights.summary }}</p>
        <el-row :gutter="20" style="margin-top:16px">
          <el-col :span="8">
            <div class="insight-block highlight">
              <div class="insight-block-header">
                <el-icon :size="16"><StarFilled /></el-icon>
                <span>亮点</span>
              </div>
              <ul><li v-for="(h, i) in aiInsights.highlights" :key="'h'+i">{{ h }}</li></ul>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="insight-block warning">
              <div class="insight-block-header">
                <el-icon :size="16"><WarningFilled /></el-icon>
                <span>需关注</span>
              </div>
              <ul><li v-for="(c, i) in aiInsights.concerns" :key="'c'+i">{{ c || '暂无特别关注' }}</li></ul>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="insight-block suggestion">
              <div class="insight-block-header">
                <el-icon :size="16"><Sunny /></el-icon>
                <span>建议</span>
              </div>
              <ul><li v-for="(s, i) in aiInsights.suggestions" :key="'s'+i">{{ s }}</li></ul>
            </div>
          </el-col>
        </el-row>
        <div class="insight-trend">
          <el-icon :size="14"><TrendCharts /></el-icon>
          {{ aiInsights.trend_note }}
        </div>
      </div>
    </template>

    <!-- ── Non-Admin View ── -->
    <template v-else>
      <!-- Face Registration Card -->
      <div class="face-card glass-card" style="cursor:default">
        <div class="section-header">
          <el-icon :size="18"><Camera /></el-icon>
          <span>人脸信息</span>
          <el-tag v-if="faceRegistered" type="success" size="small" style="margin-left:8px">已注册</el-tag>
          <el-tag v-else type="warning" size="small" style="margin-left:8px">未注册</el-tag>
        </div>
        <el-row :gutter="20" align="middle">
          <el-col :span="8">
            <div v-if="faceError" class="face-error-box">
              <el-icon :size="32"><WarningFilled /></el-icon>
              <p>{{ faceError }}</p>
            </div>
            <video v-show="!faceError && faceCameraActive" ref="dashboardFaceVideo" autoplay playsinline class="face-video" />
            <img v-if="faceRegistered && !faceCameraActive"
              :src="`/uploads/faces/${userStore.userInfo.id}/face.jpg`"
              alt="已注册人脸"
              class="face-image" />
            <div v-if="!faceRegistered && !faceCameraActive" class="face-placeholder">
              <el-icon :size="40"><UserFilled /></el-icon>
              <p>未上传人脸</p>
            </div>
          </el-col>
          <el-col :span="16">
            <div class="face-actions">
              <p v-if="faceRegMsg" class="face-msg" :class="{ success: faceRegOk, error: !faceRegOk }">{{ faceRegMsg }}</p>
              <p v-if="!faceRegistered" class="face-warn">
                <el-icon :size="16"><WarningFilled /></el-icon>
                您还未上传人脸信息，将影响签到使用
              </p>
              <el-button v-if="!faceRegistered || faceCameraActive" type="primary" :loading="faceRegLoading" @click="captureAndRegisterFace" size="large">
                <el-icon :size="18"><Camera /></el-icon>
                {{ faceCameraActive ? '确认拍照' : '拍照注册' }}
              </el-button>
              <div v-else class="face-done">
                <el-button size="small" @click="startFaceCamera">
                  <el-icon :size="14"><Refresh /></el-icon>
                  更换人脸
                </el-button>
              </div>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- User Info + My Club Row -->
      <el-row :gutter="20" style="margin-top:16px">
        <el-col :span="12">
          <div class="user-card glass-card" style="cursor:default">
            <div class="user-card-inner">
              <div class="user-avatar">
                <el-icon :size="36"><UserFilled /></el-icon>
              </div>
              <div class="user-details">
                <h3>{{ userStore.userInfo.real_name || userStore.userInfo.username }}</h3>
                <el-tag size="small" effect="plain" round>{{ roleLabel }}</el-tag>
                <div class="user-id-box">
                  <span class="id-label">我的ID</span>
                  <span class="id-value">{{ userStore.userInfo.id }}</span>
                </div>
              </div>
            </div>
          </div>
        </el-col>
        <el-col :span="12">
          <div v-if="myClub" class="club-card glass-card" style="cursor:pointer" @click="$router.push(`/clubs/${myClub.id}`)">
            <div class="section-header">
              <el-icon :size="18"><HomeFilled /></el-icon>
              <span>我的社团</span>
            </div>
            <h4 class="club-name">{{ myClub.name }}</h4>
            <p class="club-desc">{{ myClub.description }}</p>
            <div class="club-tags">
              <el-tag v-for="t in (myClub.tags||'').split(',').filter(Boolean)" :key="t" size="small" round>{{ t.trim() }}</el-tag>
            </div>
          </div>
          <div v-else class="club-card glass-card no-club" style="cursor:default">
            <el-icon :size="40"><FolderDelete /></el-icon>
            <p style="margin-top:8px">您还未加入任何社团</p>
            <el-link type="primary" @click="$router.push('/clubs')">前往社团管理 →</el-link>
          </div>
        </el-col>
      </el-row>

      <!-- Interests -->
      <div class="glass-card" style="margin-top:16px; cursor:default">
        <div class="section-header">
          <el-icon :size="18"><PriceTag /></el-icon>
          <span>我的兴趣</span>
        </div>
        <div v-if="!editingInterests">
          <div v-if="userInterests" class="interests-display">
            <el-tag v-for="t in userInterests.split(',').filter(Boolean)" :key="t" size="large" round effect="plain" class="interest-tag">{{ t.trim() }}</el-tag>
            <el-button size="small" @click="startEditInterests" class="edit-interest-btn">
              <el-icon :size="14"><EditPen /></el-icon>
              编辑
            </el-button>
          </div>
          <div v-else class="no-interests">
            <el-alert title="您还未填写兴趣，智能推荐将不会生效" type="info" show-icon :closable="false" />
            <div style="margin-top:12px">
              <el-input v-model="interestInput" placeholder="输入兴趣标签，如：AI, 机器学习" size="large" style="max-width:360px" @keyup.enter="saveInterests">
                <template #append>
                  <el-button :loading="savingInterests" @click="saveInterests">保存</el-button>
                </template>
              </el-input>
            </div>
          </div>
        </div>
        <div v-else class="edit-interests">
          <el-input v-model="interestInput" placeholder="输入兴趣标签，逗号分隔" size="large" style="max-width:360px" />
          <el-button type="primary" :loading="savingInterests" @click="saveInterests" style="margin-left:8px">保存</el-button>
          <el-button @click="editingInterests = false" style="margin-left:4px">取消</el-button>
        </div>
      </div>

      <!-- AI Recommendations -->
      <div v-if="userInterests" class="glass-card" style="margin-top:16px; cursor:default">
        <div class="section-header">
          <el-icon :size="18"><Aim /></el-icon>
          <span>智能推荐</span>
          <el-button size="small" class="refresh-btn" :loading="refreshingRecs" @click="refreshRecommendations" style="margin-left:auto">
            <el-icon :size="14"><Refresh /></el-icon>
            刷新推荐
          </el-button>
        </div>
        <el-row :gutter="16" v-if="recommendations.length">
          <el-col v-for="rec in recommendations" :key="rec.club_id" :span="8">
            <div class="rec-card glass-card" @click="$router.push(`/clubs/${rec.club_id}`)">
              <div class="rec-header">
                <h4>{{ rec.club_name }}</h4>
                <el-tag v-if="rec.category" size="small" :type="categoryTagType(rec.category)" round>{{ rec.category }}</el-tag>
              </div>
              <p class="rec-reason">{{ rec.reason }}</p>
              <div class="rec-feedback" @click.stop>
                <el-button size="small" text :type="rec._fb === 'liked' ? 'primary' : ''" @click="handleRecFeedback(rec, 'liked')">
                  <el-icon :size="16"><component :is="rec._fb === 'liked' ? 'StarFilled' : 'Star'" /></el-icon>
                </el-button>
                <el-button size="small" text :type="rec._fb === 'disliked' ? 'danger' : ''" @click="handleRecFeedback(rec, 'disliked')">
                  <el-icon :size="16"><CloseBold /></el-icon>
                </el-button>
              </div>
            </div>
          </el-col>
        </el-row>
        <el-empty v-else description="暂无推荐" :image-size="60" />
      </div>

      <!-- Recent Activities -->
      <div class="glass-card" style="margin-top:16px; cursor:default">
        <div class="section-header">
          <el-icon :size="18"><Calendar /></el-icon>
          <span>近期活动</span>
        </div>
        <el-row :gutter="16" v-if="recentActivities.length">
          <el-col v-for="act in recentActivities" :key="act.id" :span="8">
            <div class="activity-mini-card glass-card" @click="$router.push(`/activities/${act.id}`)">
              <h4>{{ act.title }}</h4>
              <div class="act-meta">
                <span><el-icon :size="14"><Location /></el-icon> {{ act.location }}</span>
                <span><el-icon :size="14"><Clock /></el-icon> {{ act.start_time }}</span>
              </div>
              <el-tag size="small" round :type="actStatusType(act.status)">{{ statusLabel(act.status) }}</el-tag>
            </div>
          </el-col>
        </el-row>
        <el-empty v-else description="暂无活动" :image-size="60" />
      </div>
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
import { useThemeStore } from '../stores/theme'
import { getClub, getActivities, getRecentActivities, getMe, updateInterests, faceRegister, aiRecommend, aiRecommendFeedback, getAdminStats, getAIInsights } from '../api'

use([BarChart, PieChart, GridComponent, TooltipComponent, TitleComponent, LegendComponent, CanvasRenderer])

const userStore = useUserStore()
const themeStore = useThemeStore()

const roleLabel = computed(() => {
  const map = { admin: '管理员', president: '社团负责人', member: '成员' }
  return map[userStore.role] || userStore.role
})
const statusLabel = (s) => ({ pending: '待审批', approved: '已通过', registration: '报名中', ongoing: '进行中', finished: '已结束' }[s] || s)
const actStatusType = (s) => ({ ongoing: 'success', registration: 'warning', finished: 'info', approved: '', pending: 'danger' }[s] || '')

// Stat card config
const statItems = [
  { key: 'clubs', label: '社团总数', icon: 'HomeFilled', gradient: 'linear-gradient(135deg, #7C3AED, #A78BFA)' },
  { key: 'activities', label: '活动总数', icon: 'Calendar', gradient: 'linear-gradient(135deg, #F97316, #FB923C)' },
  { key: 'members', label: '成员总数', icon: 'UserFilled', gradient: 'linear-gradient(135deg, #10B981, #34D399)' },
  { key: 'ongoing_activities', label: '进行中活动', icon: 'Loading', gradient: 'linear-gradient(135deg, #0EA5E9, #38BDF8)' },
]

const adminColor = computed(() => themeStore.isDark ? '#A78BFA' : '#7C3AED')

// Admin state
const stats = reactive({ clubs: 0, activities: 0, members: 0, ongoing_activities: 0, approved_clubs: 0, pending_clubs: 0, presidents: 0 })
const aiInsights = ref(null)
const insightsLoading = ref(false)
const clubChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 20, top: 20, bottom: 30 },
  xAxis: { type: 'category', data: ['已通过', '待审批', '总数'], axisLabel: { color: themeStore.isDark ? '#94A3B8' : '#64748B' } },
  yAxis: { type: 'value', axisLabel: { color: themeStore.isDark ? '#94A3B8' : '#64748B' } },
  series: [{
    type: 'bar',
    data: [stats.approved_clubs, stats.pending_clubs, stats.clubs],
    itemStyle: {
      color: adminColor.value,
      borderRadius: [6, 6, 0, 0],
    },
    barWidth: '40%',
  }],
}))
const memberChartOption = computed(() => ({
  tooltip: { trigger: 'item' },
  series: [{
    type: 'pie', radius: ['45%', '72%'],
    data: [
      { value: stats.members, name: '普通成员', itemStyle: { color: '#7C3AED' } },
      { value: stats.presidents, name: '社团负责人', itemStyle: { color: '#F97316' } },
    ],
    label: { formatter: '{b}: {c}', color: themeStore.isDark ? '#CBD5E1' : '#475569' },
    emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.1)' } },
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

// ── API Calls ──
const fetchAdminStats = async () => {
  try { const { data } = await getAdminStats(); Object.assign(stats, data) } catch {}
}
const fetchAIInsights = async () => {
  insightsLoading.value = true
  try { const { data } = await getAIInsights(); aiInsights.value = data.insights } catch {} finally { insightsLoading.value = false }
}
const stopDashboardCamera = () => {
  if (dashboardFaceStream) { dashboardFaceStream.getTracks().forEach(t => t.stop()); dashboardFaceStream = null }
  faceCameraActive.value = false
  if (dashboardFaceVideo.value) dashboardFaceVideo.value.srcObject = null
}
const startFaceCamera = async () => {
  stopDashboardCamera()
  faceError.value = ''; faceRegMsg.value = ''
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
    faceRegLoading.value = true
    try {
      const base64 = captureFrameDashboard()
      const { data } = await faceRegister({ user_id: userStore.userInfo.id, image_data: base64 })
      faceRegMsg.value = data.message || (data.success ? '注册成功' : '失败')
      faceRegOk.value = data.success
      if (data.success) { faceRegistered.value = true; ElMessage.success('人脸注册成功！') }
    } catch { faceRegMsg.value = '人脸注册请求失败'; faceRegOk.value = false }
    stopDashboardCamera(); faceRegLoading.value = false
  } else { await startFaceCamera() }
}
const fetchUserData = async () => {
  try {
    const { data } = await getMe()
    userStore.userInfo = { ...userStore.userInfo, ...data }
    localStorage.setItem('userInfo', JSON.stringify(userStore.userInfo))
    userInterests.value = data.interests || ''
    if (data.interests) interestInput.value = data.interests
    faceRegistered.value = data.face_registered
    if (data.interests) {
      try { const rec = await aiRecommend({ user_id: data.id, top_k: 6 }); recommendations.value = rec.data.recommendations || [] } catch {}
    }
    if (data.club_id) {
      try { const c = await getClub(data.club_id); myClub.value = c.data } catch { myClub.value = null }
    } else { myClub.value = null }
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
const categoryTagType = (cat) => {
  const map = { '兴趣匹配': 'success', '热门推荐': 'warning', '探索新领域': 'info', '高评分推荐': '', '基于你的活动偏好': 'primary', '综合推荐': 'info' }
  return map[cat] || 'info'
}
const handleRecFeedback = async (rec, type) => {
  if (rec._fb === type) { rec._fb = null; return }
  rec._fb = type
  try { await aiRecommendFeedback({ user_id: userStore.userInfo.id, club_id: rec.club_id, feedback: type === 'liked' ? 'liked' : 'disliked' }) } catch {}
}

onMounted(() => {
  if (userStore.role === 'admin') { fetchAdminStats(); fetchAIInsights() }
  else fetchUserData()
  fetchRecentActivities()
})
onBeforeUnmount(() => { stopDashboardCamera() })
</script>

<style scoped>
.dashboard-home { max-width: 1400px; margin: 0 auto; }

/* ── Page Header ── */
.page-header { margin-bottom: 20px; }
.page-title {
  display: flex; align-items: center; gap: 10px;
  font-size: var(--text-2xl); font-weight: var(--font-bold); color: var(--text-primary); margin: 0;
}

/* ── Section Header ── */
.section-header {
  display: flex; align-items: center; gap: 8px;
  font-size: var(--text-base); font-weight: var(--font-semibold); color: var(--text-primary);
  margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid var(--border-light);
}

/* ── Stat Grid (Bento) ── */
.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
@media (max-width: 1024px) { .stat-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 640px) { .stat-grid { grid-template-columns: 1fr; } }

.stat-card {
  display: flex; align-items: center; gap: 16px;
  padding: 24px; cursor: default;
}
.stat-icon {
  width: 52px; height: 52px; border-radius: var(--radius-md);
  display: flex; align-items: center; justify-content: center;
  color: #fff; flex-shrink: 0;
}
.stat-body { flex: 1; }
.stat-num { font-size: var(--text-4xl); font-weight: var(--font-bold); color: var(--text-primary); line-height: 1.2; }
.stat-label { color: var(--text-secondary); font-size: var(--text-sm); margin-top: 4px; }

/* ── Chart Cards ── */
.chart-card { padding: 20px; }
.chart-card-header {
  display: flex; align-items: center; gap: 8px;
  font-size: var(--text-sm); font-weight: var(--font-semibold); color: var(--text-primary);
  margin-bottom: 12px;
}

/* ── AI Insights ── */
.insights-card { padding: 24px; }
.insights-header {
  display: flex; align-items: center; justify-content: space-between;
  padding-bottom: 12px; border-bottom: 1px solid var(--border-light);
}
.insights-title { display: flex; align-items: center; gap: 8px; font-size: var(--text-base); font-weight: var(--font-semibold); color: var(--text-primary); }
.insight-summary { font-size: var(--text-base); line-height: 1.8; color: var(--text-primary); padding: 12px 0; border-bottom: 1px solid var(--border-light); }
.insight-block { padding: 4px 0; }
.insight-block-header { display: flex; align-items: center; gap: 6px; font-size: var(--text-sm); font-weight: var(--font-semibold); margin-bottom: 8px; }
.insight-block.highlight .insight-block-header { color: var(--color-success-500); }
.insight-block.warning .insight-block-header { color: var(--color-warning-500); }
.insight-block.suggestion .insight-block-header { color: var(--color-info-500); }
.insight-block ul { margin: 0; padding-left: 18px; }
.insight-block li { color: var(--text-secondary); font-size: var(--text-sm); line-height: 1.8; }
.insight-trend {
  margin-top: 16px; padding: 12px 16px;
  background: var(--gradient-card-accent); border-radius: var(--radius-md);
  color: var(--text-primary); font-size: var(--text-sm);
  display: flex; align-items: center; gap: 8px;
}

/* ── Face Card ── */
.face-card { padding: 24px; }
.face-video { width: 100%; max-width: 260px; height: 200px; background: #000; border-radius: var(--radius-md); object-fit: cover; }
.face-image { width: 100%; max-width: 200px; height: 200px; object-fit: cover; border-radius: var(--radius-md); border: 2px solid var(--border-light); }
.face-placeholder {
  width: 200px; height: 200px; background: var(--bg-secondary); border-radius: var(--radius-md);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  color: var(--text-muted); gap: 8px; font-size: var(--text-sm);
}
.face-error-box {
  padding: 20px; text-align: center; color: var(--color-warning-500);
  display: flex; flex-direction: column; align-items: center; gap: 8px;
}
.face-actions { line-height: 1.8; }
.face-msg.success { color: var(--color-success-500); margin-bottom: 8px; }
.face-msg.error { color: var(--color-warning-500); margin-bottom: 8px; }
.face-warn { color: var(--color-warning-500); margin-bottom: 12px; display: flex; align-items: center; gap: 4px; font-size: var(--text-sm); }

/* ── User Card ── */
.user-card { padding: 24px; }
.user-card-inner { display: flex; align-items: center; gap: 20px; }
.user-avatar {
  width: 64px; height: 64px; border-radius: var(--radius-full);
  background: var(--gradient-primary); color: #fff;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.user-details h3 { margin: 0 0 6px; font-size: var(--text-lg); color: var(--text-primary); }
.user-id-box { margin-top: 12px; padding: 10px 14px; background: var(--gradient-card-accent); border-radius: var(--radius-md); display: flex; align-items: center; }
.id-label { color: var(--text-secondary); font-size: var(--text-sm); }
.id-value { font-size: 28px; font-weight: var(--font-bold); color: var(--color-primary-600); margin-left: 8px; }

/* ── Club Card ── */
.club-card { padding: 24px; }
.club-name { margin: 4px 0 8px; color: var(--text-primary); font-size: var(--text-lg); }
.club-desc { color: var(--text-secondary); font-size: var(--text-sm); margin-bottom: 8px; }
.club-tags { display: flex; gap: 4px; flex-wrap: wrap; }
.no-club { text-align: center; padding: 32px; color: var(--text-muted); display: flex; flex-direction: column; align-items: center; gap: 8px; }

/* ── Interests ── */
.interests-display { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.interest-tag { cursor: default; }
.edit-interest-btn { margin-left: 4px; }

/* ── Recommendation Cards ── */
.rec-card { padding: 16px; }
.rec-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; margin-bottom: 8px; }
.rec-header h4 { margin: 0; font-size: var(--text-sm); color: var(--text-primary); }
.rec-reason { color: var(--text-secondary); font-size: var(--text-xs); line-height: 1.5; margin-bottom: 8px; }
.rec-feedback { display: flex; gap: 4px; justify-content: flex-end; }

/* ── Activity Mini Cards ── */
.activity-mini-card { padding: 16px; }
.activity-mini-card h4 { margin: 0 0 8px; font-size: var(--text-sm); color: var(--text-primary); }
.act-meta { display: flex; flex-direction: column; gap: 4px; margin-bottom: 8px; }
.act-meta span { display: flex; align-items: center; gap: 4px; color: var(--text-muted); font-size: var(--text-xs); }

/* ── Refresh Button ── */
.refresh-btn { border: 1px solid var(--border-light) !important; background: var(--bg-card) !important; color: var(--text-secondary) !important; }
.refresh-btn:hover { border-color: var(--border-accent) !important; color: var(--color-primary-500) !important; }
</style>
