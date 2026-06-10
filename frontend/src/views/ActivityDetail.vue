<template>
  <div v-loading="loading">
    <div class="back-bar">
      <el-button @click="$router.back()" text>← 返回</el-button>
    </div>
    <el-card v-if="activity" class="detail-card">
      <template #header>
        <div class="card-header">
          <span class="activity-title">{{ activity.title }}</span>
          <el-tag :type="statusType(activity.status)">{{ statusLabel(activity.status) }}</el-tag>
        </div>
      </template>
      <el-row :gutter="24">
        <el-col :span="16">
          <div class="info-section">
            <p class="label">活动描述</p>
            <p class="desc">{{ activity.description }}</p>
            <el-divider />
            <el-row :gutter="16">
              <el-col :span="12">
                <p class="label">📍 地点</p><p>{{ activity.location }}</p>
              </el-col>
              <el-col :span="12">
                <p class="label">🏠 举办社团</p>
                <p><el-link type="primary" @click="$router.push(`/clubs/${activity.club_id}`)">查看社团详情 →</el-link></p>
              </el-col>
              <el-col :span="12">
                <p class="label">🕐 开始时间</p><p>{{ activity.start_time }}</p>
              </el-col>
              <el-col :span="12">
                <p class="label">🕐 结束时间</p><p>{{ activity.end_time }}</p>
              </el-col>
              <el-col :span="12">
                <p class="label">👥 报名人数</p><p>{{ activity.current_participants }} / {{ activity.max_participants || '不限' }}</p>
              </el-col>
              <el-col v-if="canSeeAttendance" :span="12">
                <p class="label">📊 签到率</p>
                <p>{{ attendance.checkins }}人 / {{ attendance.registrations }}人 = <b>{{ attendance.rate }}%</b></p>
              </el-col>
            </el-row>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="poster-area">
            <img v-if="activity.poster_url" :src="activity.poster_url" class="activity-poster" @click="posterVisible = true" />
            <div v-else class="poster-placeholder">📅</div>
          </div>
        </el-col>
      </el-row>
      <el-divider />
      <div class="actions">
        <el-button v-if="activity.status === 'registration'" type="primary" @click="handleRegister">立即报名</el-button>
        <el-button v-if="canManage" type="warning" @click="handleGenerateQR">📱 生成签到码</el-button>
        <el-button v-if="canManage && activity.checkin_qr" @click="qrVisible = true">📷 查看签到码</el-button>
        <el-button v-if="canManage" @click="handleOpenRegistration">开放报名</el-button>
        <el-button v-if="canManage" @click="handleStartActivity">开始活动</el-button>
        <el-button v-if="canManage" @click="handleEndActivity">结束活动</el-button>
      </div>

      <!-- QR Dialog -->
      <el-dialog v-model="qrVisible" title="签到二维码" width="400px">
        <div style="text-align:center">
          <img v-if="activity.checkin_qr" :src="activity.checkin_qr" style="max-width:300px" />
        </div>
      </el-dialog>

      <!-- Poster Preview Dialog -->
      <el-dialog v-model="posterVisible" title="活动海报" width="80%" :close-on-click-modal="true">
        <div style="text-align:center">
          <img v-if="activity.poster_url" :src="activity.poster_url" style="max-width:100%;max-height:80vh" />
        </div>
      </el-dialog>
    </el-card>
    <el-empty v-else description="活动不存在" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getActivity, registerActivity, getAttendance, generateQR, updateActivityStatus } from '../api'
import { useUserStore } from '../stores/user'

const route = useRoute()
const userStore = useUserStore()

const activity = ref(null)
const loading = ref(false)
const qrVisible = ref(false)
const posterVisible = ref(false)
const attendance = reactive({ checkins: 0, registrations: 0, rate: 0 })

const canManage = computed(() => {
  if (!activity.value) return false
  if (userStore.role === 'admin') return true
  if (userStore.role === 'president' && userStore.userInfo.club_id === activity.value.club_id) return true
  return false
})

const canSeeAttendance = computed(() => canManage.value)

const statusType = (s) => ({ pending: 'warning', approved: 'success', registration: 'primary', ongoing: 'success', finished: 'info' }[s] || 'info')
const statusLabel = (s) => ({ pending: '待审批', approved: '已通过', registration: '报名中', ongoing: '进行中', finished: '已结束' }[s] || s)

const fetchActivity = async () => {
  loading.value = true
  try {
    const id = route.params.id
    const { data } = await getActivity(id)
    activity.value = data
    if (canSeeAttendance.value) {
      try { const { data: a } = await getAttendance(id); Object.assign(attendance, a) } catch {}
    }
  } catch {} finally { loading.value = false }
}

const handleRegister = async () => {
  try { await registerActivity(activity.value.id); ElMessage.success('报名成功'); fetchActivity() } catch {}
}

const handleGenerateQR = async () => {
  try {
    const { data } = await generateQR(activity.value.id)
    activity.value.checkin_qr = data.checkin_qr
    ElMessage.success('签到码已生成')
  } catch {}
}

const handleOpenRegistration = async () => {
  try { await updateActivityStatus(activity.value.id, 'open'); ElMessage.success('已开放报名'); fetchActivity() } catch {}
}

const handleStartActivity = async () => {
  try { await updateActivityStatus(activity.value.id, 'start'); ElMessage.success('活动已开始'); fetchActivity() } catch {}
}

const handleEndActivity = async () => {
  try { await updateActivityStatus(activity.value.id, 'end'); ElMessage.success('活动已结束'); fetchActivity() } catch {}
}

onMounted(fetchActivity)
</script>

<style scoped>
.back-bar { margin-bottom: 12px; }
.detail-card { max-width: 900px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.activity-title { font-size: 20px; font-weight: bold; }
.info-section .label { font-weight: bold; color: #555; margin-bottom: 4px; }
.info-section .desc { margin-bottom: 12px; line-height: 1.6; }
.poster-area { text-align: center; }
.activity-poster { max-width: 100%; max-height: 240px; border-radius: 8px; cursor: pointer; }
.poster-placeholder { font-size: 80px; padding: 40px; background: #f5f5f5; border-radius: 8px; }
.actions { display: flex; gap: 8px; flex-wrap: wrap; }
</style>
