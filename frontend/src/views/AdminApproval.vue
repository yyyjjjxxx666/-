<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">
        <el-icon :size="22"><Document /></el-icon>
        审批管理
      </h2>
    </div>

    <div class="glass-card approval-card" style="cursor:default">
      <el-tabs v-model="activeTab" class="modern-tabs">
        <el-tab-pane name="all">
          <template #label>
            <span class="tab-label"><el-icon :size="16"><List /></el-icon> 全部审批</span>
          </template>

          <!-- Filters -->
          <div class="all-filters">
            <el-select v-model="allStatusFilter" placeholder="全部状态" clearable size="small" style="width:140px" @change="fetchAllApprovals">
              <el-option label="全部状态" value="" />
              <el-option label="待审批" value="pending" />
              <el-option label="已通过" value="approved" />
              <el-option label="已拒绝" value="rejected" />
            </el-select>
            <el-select v-model="allTypeFilter" placeholder="全部类型" clearable size="small" style="width:140px" @change="fetchAllApprovals">
              <el-option label="全部类型" value="" />
              <el-option label="社团审批" value="club" />
              <el-option label="活动审批" value="activity" />
              <el-option label="注销审批" value="dissolution" />
              <el-option label="入社申请" value="join_request" />
            </el-select>
            <span class="filter-count">共 {{ filteredAllItems.length }} 条记录</span>
          </div>

          <el-table :data="filteredAllItems" border empty-text="暂无审批记录" class="modern-table" max-height="520">
            <el-table-column label="类型" width="110">
              <template #default="{ row }">
                <el-tag :type="typeTagType(row.type)" size="small" effect="light">{{ row.type_label }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="name" label="名称" show-overflow-tooltip>
              <template #default="{ row }">
                <el-link v-if="row.type === 'club'" type="primary" @click="$router.push(`/clubs/${row.id}`)">{{ row.name }}</el-link>
                <el-link v-else-if="row.type === 'activity'" type="primary" @click="$router.push(`/activities/${row.id}`)">{{ row.name }}</el-link>
                <span v-else>{{ row.name }}</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)" size="small" effect="light">{{ statusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="applicant" label="申请人" width="100" />
            <el-table-column prop="created_at" label="申请时间" width="160" />
            <el-table-column prop="reviewed_at" label="审批时间" width="160">
              <template #default="{ row }">
                <span v-if="row.reviewed_at">{{ row.reviewed_at }}</span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane name="clubs">
          <template #label>
            <span class="tab-label"><el-icon :size="16"><HomeFilled /></el-icon> 社团审批</span>
          </template>
          <el-table :data="pending.clubs" border stripe empty-text="暂无待审批社团" class="modern-table">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="name" label="社团名称">
              <template #default="{ row }">
                <el-link type="primary" @click="$router.push(`/clubs/${row.id}`)">{{ row.name }}</el-link>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="简介" show-overflow-tooltip />
            <el-table-column prop="tags" label="标签" />
            <el-table-column prop="president_id" label="负责人ID" width="80" />
            <el-table-column prop="created_at" label="申请时间" width="160" />
            <el-table-column label="操作" width="200">
              <template #default="{ row }">
                <el-button type="success" size="small" @click="handleApproveClub(row.id)">
                  <el-icon :size="14"><Select /></el-icon> 通过
                </el-button>
                <el-button type="danger" size="small" @click="handleRejectClub(row.id)">
                  <el-icon :size="14"><Close /></el-icon> 拒绝
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane name="activities">
          <template #label>
            <span class="tab-label"><el-icon :size="16"><Calendar /></el-icon> 活动审批</span>
          </template>
          <el-table :data="pending.activities" border stripe empty-text="暂无待审批活动" class="modern-table">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="title" label="活动名称">
              <template #default="{ row }">
                <el-link type="primary" @click="$router.push(`/activities/${row.id}`)">{{ row.title }}</el-link>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" show-overflow-tooltip />
            <el-table-column prop="location" label="地点" />
            <el-table-column prop="club_id" label="所属社团ID" width="100" />
            <el-table-column prop="created_at" label="申请时间" width="160" />
            <el-table-column label="操作" width="200">
              <template #default="{ row }">
                <el-button type="success" size="small" @click="handleApproveActivity(row.id)">
                  <el-icon :size="14"><Select /></el-icon> 通过
                </el-button>
                <el-button type="danger" size="small" @click="handleRejectActivity(row.id)">
                  <el-icon :size="14"><Close /></el-icon> 拒绝
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane name="dissolutions">
          <template #label>
            <span class="tab-label"><el-icon :size="16"><WarningFilled /></el-icon> 注销审批</span>
          </template>
          <el-table :data="pending.dissolutions" border stripe empty-text="暂无注销申请" class="modern-table">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="name" label="社团名称" />
            <el-table-column prop="president_id" label="负责人ID" width="80" />
            <el-table-column prop="created_at" label="申请时间" width="160" />
            <el-table-column label="操作" width="200">
              <template #default="{ row }">
                <el-button type="success" size="small" @click="handleApproveDissolve(row.id)">
                  <el-icon :size="14"><Select /></el-icon> 批准注销
                </el-button>
                <el-button type="danger" size="small" @click="handleRejectDissolve(row.id)">
                  <el-icon :size="14"><Close /></el-icon> 拒绝注销
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getPendingItems, approveClub, approveActivityApi, rejectActivityApi, rejectClubApi, getAllApprovals } from '../api'
import api from '../api'

const activeTab = ref('all')
const pending = reactive({ clubs: [], activities: [], dissolutions: [] })

const fetchPending = async () => {
  try { const { data } = await getPendingItems(); pending.clubs = data.clubs || []; pending.activities = data.activities || []; pending.dissolutions = data.dissolutions || [] } catch {}
}
const handleApproveClub = async (id) => { try { await approveClub(id); ElMessage.success('已通过'); fetchPending(); fetchAllApprovals() } catch {} }
const handleRejectClub = async (id) => { try { await rejectClubApi(id); ElMessage.success('已拒绝'); fetchPending(); fetchAllApprovals() } catch {} }
const handleApproveActivity = async (id) => { try { await approveActivityApi(id); ElMessage.success('已通过'); fetchPending(); fetchAllApprovals() } catch {} }
const handleRejectActivity = async (id) => { try { await rejectActivityApi(id); ElMessage.success('已拒绝'); fetchPending(); fetchAllApprovals() } catch {} }
const handleApproveDissolve = async (id) => {
  try { await ElMessageBox.confirm('确认批准注销该社团？此操作不可撤销。', '二次确认', { type: 'warning' }); await api.put(`/clubs/${id}/approve-dissolve`); ElMessage.success('社团已注销'); fetchPending(); fetchAllApprovals() } catch {}
}
const handleRejectDissolve = async (id) => {
  try { await ElMessageBox.confirm('确认拒绝注销申请？', '二次确认', { type: 'warning' }); await api.put(`/clubs/${id}/reject-dissolve`); ElMessage.success('已拒绝注销'); fetchPending(); fetchAllApprovals() } catch {}
}

// ── All Approvals tab ──
const allItems = ref([])
const allStatusFilter = ref('')
const allTypeFilter = ref('')

const filteredAllItems = computed(() => {
  let items = allItems.value
  if (allStatusFilter.value) items = items.filter(i => i.status === allStatusFilter.value)
  if (allTypeFilter.value) items = items.filter(i => i.type === allTypeFilter.value)
  return items
})

const fetchAllApprovals = async () => {
  try {
    const params = {}
    if (allStatusFilter.value) params.status = allStatusFilter.value
    const { data } = await getAllApprovals(params)
    allItems.value = data.items || []
  } catch {}
}

const typeTagType = (type) => {
  const map = { club: '', activity: 'primary', dissolution: 'warning', join_request: 'success' }
  return map[type] || 'info'
}
const statusTagType = (status) => {
  const map = { pending: 'warning', approved: 'success', rejected: 'danger', dissolve_pending: 'warning', registration: 'primary', ongoing: 'primary', finished: 'info' }
  return map[status] || 'info'
}
const statusLabel = (status) => {
  const map = { pending: '待审批', approved: '已通过', rejected: '已拒绝', dissolve_pending: '待审批', registration: '报名中', ongoing: '进行中', finished: '已结束' }
  return map[status] || status
}

onMounted(() => { fetchPending(); fetchAllApprovals() })
</script>

<style scoped>
.page-container { max-width: 1400px; margin: 0 auto; }
.page-header { margin-bottom: 20px; }
.page-title { display: flex; align-items: center; gap: 10px; font-size: var(--text-2xl); font-weight: var(--font-bold); color: var(--text-primary); margin: 0; }
.approval-card { padding: 24px; }
.tab-label { display: flex; align-items: center; gap: 6px; }

/* Filters */
.all-filters { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.filter-count { font-size: var(--text-xs); color: var(--text-muted); margin-left: auto; }
.text-muted { color: var(--text-muted); }

.modern-tabs :deep(.el-tabs__active-bar) { background: var(--gradient-primary) !important; height: 3px !important; border-radius: var(--radius-full); }
.modern-tabs :deep(.el-tabs__item) { font-size: var(--text-sm); color: var(--text-muted); }
.modern-tabs :deep(.el-tabs__item):hover { color: var(--color-primary-500); }
.modern-tabs :deep(.el-tabs__item.is-active) { color: var(--color-primary-600); font-weight: var(--font-semibold); }
.modern-tabs :deep(.el-tabs__nav-wrap::after) { background: var(--border-light); }
.modern-table :deep(.el-table__header th) { background: var(--bg-secondary); color: var(--text-primary); font-weight: var(--font-semibold); }
.modern-table :deep(.el-table__body tr:hover > td) { background: var(--color-primary-50) !important; }
[data-theme="dark"] .modern-table :deep(.el-table__body tr:hover > td) { background: rgba(124, 58, 237, 0.08) !important; }
</style>
