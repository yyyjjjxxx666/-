<template>
  <div v-loading="loading">
    <div class="back-bar">
      <el-button @click="$router.back()" text>← 返回</el-button>
    </div>
    <el-card v-if="club" class="detail-card">
      <template #header>
        <div class="card-header">
          <span class="club-name">{{ club.name }}</span>
          <el-tag :type="statusType(club.status)">{{ statusLabel(club.status) }}</el-tag>
        </div>
      </template>
      <el-row :gutter="24">
        <el-col :span="16">
          <div class="info-section">
            <p class="label">社团简介</p>
            <p class="desc">{{ club.description }}</p>
            <p class="label">标签</p>
            <div class="tags">
              <el-tag v-for="t in (club.tags || '').split(',').filter(Boolean)" :key="t" size="small" style="margin-right:4px">{{ t.trim() }}</el-tag>
            </div>
            <el-divider />
            <el-row :gutter="16">
              <el-col :span="8"><p class="label">负责人</p><p>{{ presidentName }}</p></el-col>
              <el-col :span="8"><p class="label">成员数</p><p>{{ club.member_count }}</p></el-col>
              <el-col :span="8"><p class="label">活动数</p><p>{{ club.activity_count }}</p></el-col>
              <el-col :span="8"><p class="label">星级</p><p>{{ club.star_rating ? club.star_rating + ' ⭐' : '未评' }}</p></el-col>
              <el-col :span="8"><p class="label">负责人ID</p><p>{{ club.president_id }}</p></el-col>
            </el-row>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="logo-area">
            <img v-if="club.logo_url" :src="club.logo_url" class="club-logo" @click="posterVisible = true" />
            <div v-else class="logo-placeholder">🏠</div>
          </div>
        </el-col>
      </el-row>
      <el-divider />
      <div class="actions">
        <el-button v-if="canJoin" type="primary" @click="handleJoin">申请加入</el-button>
        <el-tag v-if="isAlreadyMember" type="success">已加入</el-tag>
        <el-button v-if="canLeave" type="warning" @click="handleLeave">退出社团</el-button>
        <el-button v-if="isPresident" @click="transferVisible = true">转让负责人</el-button>
        <el-button v-if="isPresident" type="danger" @click="handleDissolve">注销社团</el-button>
      </div>
    </el-card>
    <el-empty v-else description="社团不存在" />

    <!-- Transfer Dialog -->
    <el-dialog v-model="transferVisible" title="转让负责人" width="400px">
      <p style="margin-bottom:12px">请选择新的负责人（仅显示本社团成员）：</p>
      <el-select v-model="newPresidentId" style="width:100%" filterable placeholder="选择成员">
        <el-option v-for="m in members" :key="m.id" :label="`${m.real_name || m.username} (ID:${m.id})`" :value="m.id" />
      </el-select>
      <template #footer>
        <el-button @click="transferVisible = false">取消</el-button>
        <el-button type="primary" :loading="transferring" @click="handleTransfer">确认转让</el-button>
      </template>
    </el-dialog>

    <!-- Poster Preview Dialog -->
    <el-dialog v-model="posterVisible" title="社团海报" width="80%" :close-on-click-modal="true">
      <div style="text-align:center">
        <img v-if="club.logo_url" :src="club.logo_url" style="max-width:100%;max-height:80vh" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getClub, leaveClub, transferClub, dissolveClub, getClubMembers, sendJoinRequest } from '../api'
import { useUserStore } from '../stores/user'
import api from '../api'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const club = ref(null)
const loading = ref(false)
const members = ref([])
const transferVisible = ref(false)
const posterVisible = ref(false)
const transferring = ref(false)
const newPresidentId = ref(null)

const presidentName = computed(() => {
  if (!club.value) return ''
  const m = members.value.find(m => m.id === club.value.president_id)
  return m ? (m.real_name || m.username) : `ID:${club.value.president_id}`
})

const isAlreadyMember = computed(() => {
  return userStore.userInfo.club_id === club.value?.id
})

const canJoin = computed(() => {
  if (!club.value || userStore.role !== 'member') return false
  return !userStore.userInfo.club_id && club.value.status === 'approved'
})

const canLeave = computed(() => {
  return isAlreadyMember.value && userStore.role === 'member'
})

const isPresident = computed(() => {
  return userStore.userInfo.id === club.value?.president_id
})

const statusType = (s) => ({ pending: 'warning', approved: 'success', rejected: 'danger' }[s] || 'info')
const statusLabel = (s) => ({ pending: '待审批', approved: '已通过', rejected: '已拒绝' }[s] || s)

const fetchClub = async () => {
  loading.value = true
  try {
    const id = route.params.id
    const { data } = await getClub(id)
    club.value = data
    // Fetch members
    try { const { data: m } = await getClubMembers(id); members.value = m } catch { members.value = [] }
  } catch {} finally { loading.value = false }
}

const handleJoin = async () => {
  try {
    await sendJoinRequest(club.value.id)
    ElMessage.success('入社申请已提交，等待审批')
    fetchClub()
  } catch {}
}

const handleLeave = async () => {
  try {
    await ElMessageBox.confirm('确认退出该社团？退出后将自动通知社团全员。', '二次确认', { type: 'warning' })
    await leaveClub(club.value.id)
    ElMessage.success('已退出社团')
    userStore.userInfo.club_id = null
    localStorage.setItem('userInfo', JSON.stringify(userStore.userInfo))
    fetchClub()
  } catch {}
}

const handleTransfer = async () => {
  if (!newPresidentId.value) { ElMessage.warning('请选择新负责人'); return }
  try {
    await ElMessageBox.confirm('确认转让负责人权限？转让后您将成为普通成员。', '二次确认', { type: 'warning' })
    transferring.value = true
    await transferClub(club.value.id, { new_president_id: newPresidentId.value })
    ElMessage.success('转让成功')
    transferVisible.value = false
    fetchClub()
  } catch {} finally { transferring.value = false }
}

const handleDissolve = async () => {
  try {
    await ElMessageBox.confirm('确认申请注销社团？需要管理员审批。', '二次确认', { type: 'warning' })
    await dissolveClub(club.value.id)
    ElMessage.success('注销申请已提交，等待管理员审批')
    fetchClub()
  } catch {}
}

onMounted(fetchClub)
</script>

<style scoped>
.back-bar { margin-bottom: 12px; }
.detail-card { max-width: 900px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.club-name { font-size: 20px; font-weight: bold; }
.info-section .label { font-weight: bold; color: #555; margin-bottom: 4px; }
.info-section .desc { margin-bottom: 12px; line-height: 1.6; }
.tags { margin-bottom: 8px; }
.logo-area { text-align: center; }
.club-logo { max-width: 100%; max-height: 200px; border-radius: 8px; cursor: pointer; }
.logo-placeholder { font-size: 80px; padding: 40px; background: #f5f5f5; border-radius: 8px; }
.actions { display: flex; gap: 8px; }
</style>
