<template>
  <div v-loading="loading" class="detail-page">
    <div class="back-bar">
      <el-button @click="$router.back()" text size="large">
        <el-icon :size="18"><ArrowLeft /></el-icon>
        返回
      </el-button>
    </div>

    <div v-if="club" class="detail-layout">
      <!-- Hero Card -->
      <div class="hero-card glass-card" style="cursor:default">
        <div class="hero-body">
          <div class="hero-info">
            <div class="club-badge">
              <el-icon :size="28"><HomeFilled /></el-icon>
            </div>
            <div>
              <h1 class="club-name">{{ club.name }}</h1>
              <el-tag :type="statusType(club.status)" size="small" round>{{ statusLabel(club.status) }}</el-tag>
              <span class="star-display" v-if="club.star_rating">
                <el-icon :size="14"><StarFilled /></el-icon>
                {{ club.star_rating }} 星
              </span>
            </div>
          </div>
          <div class="hero-actions">
            <el-button v-if="canJoin" type="primary" size="large" @click="handleJoin">
              <el-icon :size="16"><Plus /></el-icon> 申请加入
            </el-button>
            <el-tag v-if="isAlreadyMember" type="success" size="large" round>已加入</el-tag>
            <el-button v-if="canLeave" type="warning" @click="handleLeave">
              <el-icon :size="16"><Switch /></el-icon> 退出社团
            </el-button>
            <el-button v-if="isPresident" @click="transferVisible = true">
              <el-icon :size="16"><Switch /></el-icon> 转让
            </el-button>
            <el-button v-if="isPresident" type="danger" @click="handleDissolve">
              <el-icon :size="16"><Delete /></el-icon> 注销
            </el-button>
          </div>
        </div>
      </div>

      <!-- Content Grid -->
      <el-row :gutter="20" style="margin-top:20px">
        <!-- Left: Info -->
        <el-col :span="16">
          <div class="info-card glass-card" style="cursor:default">
            <div class="section-title">
              <el-icon :size="18"><Document /></el-icon>
              <span>社团简介</span>
            </div>
            <p class="desc">{{ club.description }}</p>

            <div class="section-title" style="margin-top:20px">
              <el-icon :size="18"><PriceTag /></el-icon>
              <span>标签</span>
            </div>
            <div class="tags">
              <el-tag v-for="t in (club.tags || '').split(',').filter(Boolean)" :key="t" size="small" round effect="plain">{{ t.trim() }}</el-tag>
            </div>

            <el-divider />

            <div class="stats-grid">
              <div class="stat-item">
                <el-icon :size="20"><UserFilled /></el-icon>
                <div><span class="stat-label">负责人</span><span class="stat-value">{{ presidentName }}</span></div>
              </div>
              <div class="stat-item">
                <el-icon :size="20"><Avatar /></el-icon>
                <div><span class="stat-label">成员数</span><span class="stat-value">{{ club.member_count }}</span></div>
              </div>
              <div class="stat-item">
                <el-icon :size="20"><Calendar /></el-icon>
                <div><span class="stat-label">活动数</span><span class="stat-value">{{ club.activity_count }}</span></div>
              </div>
            </div>
          </div>
        </el-col>

        <!-- Right: Logo/Poster -->
        <el-col :span="8">
          <div class="poster-card glass-card" style="cursor:pointer" @click="posterVisible = true">
            <img v-if="club.logo_url" :src="club.logo_url" class="club-img" alt="社团海报" />
            <div v-else class="img-placeholder">
              <el-icon :size="64"><HomeFilled /></el-icon>
              <p>暂无海报</p>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <el-empty v-else description="社团不存在" />

    <!-- Transfer Dialog -->
    <el-dialog v-model="transferVisible" title="转让负责人" width="400px" class="modern-dialog">
      <p style="margin-bottom:12px;color:var(--text-secondary)">请选择新负责人（仅显示本社团成员）：</p>
      <el-select v-model="newPresidentId" style="width:100%" filterable placeholder="选择成员" size="large">
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
        <img v-if="club?.logo_url" :src="club.logo_url" style="max-width:100%;max-height:80vh;border-radius:var(--radius-lg)" alt="社团海报大图" />
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

const route = useRoute(); const router = useRouter(); const userStore = useUserStore()
const club = ref(null); const loading = ref(false); const members = ref([])
const transferVisible = ref(false); const posterVisible = ref(false)
const transferring = ref(false); const newPresidentId = ref(null)

const presidentName = computed(() => {
  if (!club.value) return ''; const m = members.value.find(m => m.id === club.value.president_id)
  return m ? (m.real_name || m.username) : `ID:${club.value.president_id}`
})
const isAlreadyMember = computed(() => Number(userStore.userInfo.club_id) === Number(club.value?.id))
const canJoin = computed(() => club.value && userStore.role === 'member' && !userStore.userInfo.club_id && club.value.status === 'approved')
const canLeave = computed(() => isAlreadyMember.value && userStore.role === 'member')
const isPresident = computed(() => Number(userStore.userInfo.id) === Number(club.value?.president_id))
const statusType = (s) => ({ pending: 'warning', approved: 'success', rejected: 'danger' }[s] || 'info')
const statusLabel = (s) => ({ pending: '待审批', approved: '已通过', rejected: '已拒绝' }[s] || s)

const fetchClub = async () => {
  loading.value = true
  try { const id = route.params.id; const { data } = await getClub(id); club.value = data; try { const { data: m } = await getClubMembers(id); members.value = m } catch { members.value = [] } } catch {} finally { loading.value = false }
}
const handleJoin = async () => { try { await sendJoinRequest(club.value.id); ElMessage.success('入社申请已提交'); fetchClub() } catch {} }
const handleLeave = async () => { try { await ElMessageBox.confirm('确认退出该社团？', '二次确认', { type: 'warning' }); await leaveClub(club.value.id); ElMessage.success('已退出社团'); userStore.userInfo.club_id = null; localStorage.setItem('userInfo', JSON.stringify(userStore.userInfo)); fetchClub() } catch {} }
const handleTransfer = async () => {
  if (!newPresidentId.value) { ElMessage.warning('请选择新负责人'); return }
  try { await ElMessageBox.confirm('确认转让负责人权限？', '二次确认', { type: 'warning' }); transferring.value = true; await transferClub(club.value.id, { new_president_id: newPresidentId.value }); ElMessage.success('转让成功'); transferVisible.value = false; fetchClub() } catch {} finally { transferring.value = false }
}
const handleDissolve = async () => { try { await ElMessageBox.confirm('确认申请注销社团？', '二次确认', { type: 'warning' }); await dissolveClub(club.value.id); ElMessage.success('注销申请已提交'); fetchClub() } catch {} }

onMounted(fetchClub)
</script>

<style scoped>
.detail-page { max-width: 1000px; margin: 0 auto; }
.back-bar { margin-bottom: 16px; }

/* Hero Card */
.hero-card { padding: 24px; margin-bottom: 0; }
.hero-body { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; }
.hero-info { display: flex; align-items: center; gap: 16px; }
.club-badge {
  width: 56px; height: 56px; border-radius: var(--radius-md);
  background: var(--gradient-primary); color: #fff;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.club-name { font-size: var(--text-2xl); font-weight: var(--font-bold); color: var(--text-primary); margin: 0 0 6px; }
.star-display { color: var(--color-warning-500); font-size: var(--text-sm); margin-left: 8px; display: inline-flex; align-items: center; gap: 2px; }
.hero-actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }

/* Info Card */
.info-card { padding: 24px; }
.section-title { display: flex; align-items: center; gap: 8px; font-size: var(--text-base); font-weight: var(--font-semibold); color: var(--text-primary); margin-bottom: 10px; }
.desc { line-height: 1.7; color: var(--text-secondary); }
.tags { display: flex; gap: 6px; flex-wrap: wrap; }

/* Stats Grid */
.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 12px; }
.stat-item { display: flex; align-items: center; gap: 10px; padding: 12px; background: var(--gradient-card-accent); border-radius: var(--radius-md); color: var(--text-primary); }
.stat-item .stat-label { display: block; font-size: var(--text-xs); color: var(--text-muted); }
.stat-item .stat-value { display: block; font-size: var(--text-base); font-weight: var(--font-semibold); color: var(--text-primary); }

/* Poster Card */
.poster-card { padding: 16px; text-align: center; }
.club-img { max-width: 100%; max-height: 260px; border-radius: var(--radius-md); object-fit: contain; }
.img-placeholder { padding: 48px 20px; color: var(--text-muted); background: var(--bg-secondary); border-radius: var(--radius-md); }

@media (max-width: 768px) { .stats-grid { grid-template-columns: 1fr; } }
</style>
