<template>
  <div v-loading="loading" class="detail-page">
    <div class="back-bar">
      <el-button @click="$router.back()" text size="large">
        <el-icon :size="18"><ArrowLeft /></el-icon>
        返回
      </el-button>
    </div>

    <div v-if="activity" class="detail-layout">
      <!-- Hero Card -->
      <div class="hero-card glass-card" style="cursor:default">
        <div class="hero-body">
          <div class="hero-info">
            <div class="act-badge">
              <el-icon :size="28"><Calendar /></el-icon>
            </div>
            <div>
              <h1 class="act-name">{{ activity.title }}</h1>
              <el-tag :type="statusType(activity.status)" size="small" round>{{ statusLabel(activity.status) }}</el-tag>
            </div>
          </div>
          <div class="hero-actions">
            <el-button v-if="activity.status === 'registration'" type="primary" size="large" @click="handleRegister">
              <el-icon :size="16"><Select /></el-icon> 立即报名
            </el-button>
            <el-button v-if="canManage" type="warning" @click="handleGenerateQR">
              <el-icon :size="16"><Iphone /></el-icon> 生成签到码
            </el-button>
            <el-button v-if="canManage && activity.checkin_qr" @click="qrVisible = true">
              <el-icon :size="16"><Camera /></el-icon> 查看签到码
            </el-button>
            <el-button v-if="canManage" @click="handleOpenRegistration">开放报名</el-button>
            <el-button v-if="canManage" @click="handleStartActivity">开始活动</el-button>
            <el-button v-if="canManage" @click="handleEndActivity">结束活动</el-button>
          </div>
        </div>
      </div>

      <!-- Content Grid -->
      <el-row :gutter="20" style="margin-top:20px">
        <el-col :span="16">
          <div class="info-card glass-card" style="cursor:default">
            <div class="section-title">
              <el-icon :size="18"><Document /></el-icon>
              <span>活动描述</span>
            </div>
            <p class="desc">{{ activity.description }}</p>

            <el-divider />

            <div class="meta-grid">
              <div class="meta-item">
                <el-icon :size="18"><Location /></el-icon>
                <div><span class="meta-label">地点</span><span class="meta-value">{{ activity.location }}</span></div>
              </div>
              <div class="meta-item">
                <el-icon :size="18"><HomeFilled /></el-icon>
                <div><span class="meta-label">举办社团</span><span class="meta-value"><el-link type="primary" @click="$router.push(`/clubs/${activity.club_id}`)">查看详情 →</el-link></span></div>
              </div>
              <div class="meta-item">
                <el-icon :size="18"><Clock /></el-icon>
                <div><span class="meta-label">开始时间</span><span class="meta-value">{{ activity.start_time }}</span></div>
              </div>
              <div class="meta-item">
                <el-icon :size="18"><Clock /></el-icon>
                <div><span class="meta-label">结束时间</span><span class="meta-value">{{ activity.end_time }}</span></div>
              </div>
              <div class="meta-item">
                <el-icon :size="18"><Avatar /></el-icon>
                <div><span class="meta-label">报名人数</span><span class="meta-value">{{ activity.current_participants }} / {{ activity.max_participants || '不限' }}</span></div>
              </div>
              <div v-if="canSeeAttendance" class="meta-item">
                <el-icon :size="18"><TrendCharts /></el-icon>
                <div><span class="meta-label">签到率</span><span class="meta-value">{{ attendance.checkins }}人 / {{ attendance.registrations }}人 = <b>{{ attendance.rate }}%</b></span></div>
              </div>
            </div>
          </div>
        </el-col>

        <el-col :span="8">
          <div class="poster-card glass-card" style="cursor:pointer" @click="posterVisible = true">
            <img v-if="activity.poster_url" :src="activity.poster_url" class="act-poster" alt="活动海报" />
            <div v-else class="poster-placeholder">
              <el-icon :size="64"><PictureFilled /></el-icon>
              <p>暂无海报</p>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <el-empty v-else description="活动不存在" />

    <!-- QR Dialog -->
    <el-dialog v-model="qrVisible" title="签到二维码" width="400px" class="modern-dialog">
      <div style="text-align:center;padding:20px">
        <img v-if="activity?.checkin_qr" :src="activity.checkin_qr" style="max-width:280px;border-radius:var(--radius-md)" alt="签到二维码" />
      </div>
    </el-dialog>

    <!-- Poster Preview Dialog -->
    <el-dialog v-model="posterVisible" title="活动海报" width="80%" :close-on-click-modal="true">
      <div style="text-align:center">
        <img v-if="activity?.poster_url" :src="activity.poster_url" style="max-width:100%;max-height:80vh;border-radius:var(--radius-lg)" alt="活动海报大图" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getActivity, registerActivity, getAttendance, generateQR, updateActivityStatus } from '../api'
import { useUserStore } from '../stores/user'

const route = useRoute(); const userStore = useUserStore()
const activity = ref(null); const loading = ref(false)
const qrVisible = ref(false); const posterVisible = ref(false)
const attendance = reactive({ checkins: 0, registrations: 0, rate: 0 })

const canManage = computed(() => {
  if (!activity.value) return false
  if (userStore.role === 'admin') return true
  return userStore.role === 'president' && userStore.userInfo.club_id === activity.value.club_id
})
const canSeeAttendance = computed(() => canManage.value)
const statusType = (s) => ({ pending: 'warning', approved: 'success', registration: 'primary', ongoing: 'success', finished: 'info' }[s] || 'info')
const statusLabel = (s) => ({ pending: '待审批', approved: '已通过', registration: '报名中', ongoing: '进行中', finished: '已结束' }[s] || s)

const fetchActivity = async () => {
  loading.value = true
  try { const id = route.params.id; const { data } = await getActivity(id); activity.value = data; if (canSeeAttendance.value) { try { const { data: a } = await getAttendance(id); Object.assign(attendance, a) } catch {} } } catch {} finally { loading.value = false }
}
const handleRegister = async () => { try { await registerActivity(activity.value.id); ElMessage.success('报名成功'); fetchActivity() } catch {} }
const handleGenerateQR = async () => { try { const { data } = await generateQR(activity.value.id); activity.value.checkin_qr = data.checkin_qr; ElMessage.success('签到码已生成') } catch {} }
const handleOpenRegistration = async () => { try { await updateActivityStatus(activity.value.id, 'open'); ElMessage.success('已开放报名'); fetchActivity() } catch {} }
const handleStartActivity = async () => { try { await updateActivityStatus(activity.value.id, 'start'); ElMessage.success('活动已开始'); fetchActivity() } catch {} }
const handleEndActivity = async () => { try { await updateActivityStatus(activity.value.id, 'end'); ElMessage.success('活动已结束'); fetchActivity() } catch {} }

onMounted(fetchActivity)
</script>

<style scoped>
.detail-page { max-width: 1000px; margin: 0 auto; }
.back-bar { margin-bottom: 16px; }

/* Hero */
.hero-card { padding: 24px; }
.hero-body { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; }
.hero-info { display: flex; align-items: center; gap: 16px; }
.act-badge { width: 56px; height: 56px; border-radius: var(--radius-md); background: var(--gradient-accent); color: #fff; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.act-name { font-size: var(--text-2xl); font-weight: var(--font-bold); color: var(--text-primary); margin: 0 0 6px; }
.hero-actions { display: flex; gap: 8px; flex-wrap: wrap; }

/* Info Card */
.info-card { padding: 24px; }
.section-title { display: flex; align-items: center; gap: 8px; font-size: var(--text-base); font-weight: var(--font-semibold); color: var(--text-primary); margin-bottom: 10px; }
.desc { line-height: 1.7; color: var(--text-secondary); }

/* Meta Grid */
.meta-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.meta-item { display: flex; align-items: center; gap: 10px; padding: 12px; background: var(--gradient-card-accent); border-radius: var(--radius-md); color: var(--text-primary); }
.meta-item .meta-label { display: block; font-size: var(--text-xs); color: var(--text-muted); }
.meta-item .meta-value { display: block; font-size: var(--text-sm); font-weight: var(--font-medium); color: var(--text-primary); }

/* Poster */
.poster-card { padding: 16px; text-align: center; }
.act-poster { max-width: 100%; max-height: 260px; border-radius: var(--radius-md); object-fit: contain; }
.poster-placeholder { padding: 48px 20px; color: var(--text-muted); background: var(--bg-secondary); border-radius: var(--radius-md); }

@media (max-width: 768px) { .meta-grid { grid-template-columns: 1fr; } }
</style>
