<template>
  <div>
    <div class="page-header">
      <h2>🏠 社团管理</h2>
      <div class="header-right">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索社团..."
          clearable
          size="default"
          style="width: 280px; margin-right: 12px"
          @input="handleSearch"
          @clear="fetchClubs()"
        >
          <template #prefix>🔍</template>
        </el-input>
        <el-button type="primary" @click="openCreateDialog">创建社团</el-button>
      </div>
    </div>

    <el-table :data="clubs" border stripe v-loading="loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="社团名称">
        <template #default="{ row }">
          <el-link type="primary" @click="$router.push(`/clubs/${row.id}`)">{{ row.name }}</el-link>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="简介" show-overflow-tooltip />
      <el-table-column prop="member_count" label="成员数" width="80" />
      <el-table-column prop="activity_count" label="活动数" width="80" />
      <el-table-column prop="star_rating" label="星级" width="80">
        <template #default="{ row }">{{ row.star_rating ? row.star_rating + '⭐' : '未评' }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280">
        <template #default="{ row }">
          <el-button v-if="isAdmin && row.status === 'pending'" type="success" size="small" @click="handleApprove(row.id)">审批通过</el-button>
          <el-button v-if="!isInClub(row) && !hasPendingRequest(row)" size="small" type="primary" @click="handleJoin(row.id)">申请加入</el-button>
          <el-tag v-if="hasPendingRequest(row)" type="warning" size="small">等待审批</el-tag>
          <el-tag v-if="isInClub(row)" type="success" size="small">已加入</el-tag>
          <el-button v-if="isPresidentOf(row)" size="small" @click="openManageDialog(row)">⚙️ 管理</el-button>

        </template>
      </el-table-column>
    </el-table>

    <!-- Create Club Dialog -->
    <el-dialog v-model="dialogVisible" title="创建社团" width="550px">
      <el-form :model="form">
        <el-form-item label="社团名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="简介">
          <el-input v-model="form.description" type="textarea" :rows="4" />
          <div style="margin-top:6px">
            <el-button size="small" :loading="aiLoading" @click="handleAIDesc">
              🤖 {{ aiLoading ? '生成中...' : 'AI生成描述' }}
            </el-button>
          </div>
        </el-form-item>
        <el-form-item label="标签（逗号分隔）"><el-input v-model="form.tags" placeholder="如：学术,科技,文艺" /></el-form-item>
        <el-form-item label="社团Logo/海报">
          <el-button size="small" @click="handleLogoUploadClick">📷 上传图片</el-button>
          <input ref="logoFileInput" type="file" accept="image/*" style="display:none" @change="onLogoFileChange" />
          <el-button size="small" style="margin-left:8px" :loading="clubPosterLoading" @click="handleGenerateClubPoster">🎨 AI生成海报</el-button>
        </el-form-item>
        <el-form-item v-if="clubLogoPreview">
          <img :src="clubLogoPreview" style="max-width:200px;max-height:200px;border-radius:8px" />
          <el-button size="small" type="danger" style="margin-left:8px" @click="clubLogoPreview = ''">移除</el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreate">确认创建</el-button>
      </template>
    </el-dialog>

    <!-- Manage Club Dialog (for president) -->
    <el-dialog v-model="manageVisible" :title="'管理社团: ' + managingClub?.name" width="700px">
      <el-tabs v-model="manageTab">
        <el-tab-pane label="成员管理" name="members">
          <el-table :data="clubMembers" border stripe max-height="300" empty-text="暂无成员">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="real_name" label="姓名" />
            <el-table-column prop="role" label="角色" width="100">
              <template #default="{ row }">
                <el-tag size="small">{{ row.role === 'president' ? '负责人' : '成员' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-popconfirm v-if="row.role !== 'president'" title="确认踢出该成员？" @confirm="handleKick(row.id)">
                  <template #reference>
                    <el-button size="small" type="danger">踢出</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="入社申请" name="requests">
          <el-table :data="joinRequests" border stripe max-height="300" empty-text="暂无待审批申请">
            <el-table-column prop="user_name" label="申请人" />
            <el-table-column prop="created_at" label="申请时间" width="160" />
            <el-table-column label="操作" width="180">
              <template #default="{ row }">
                <el-button type="success" size="small" @click="handleRequestAction(row.id, 'approve')">通过</el-button>
                <el-button type="danger" size="small" @click="handleRequestAction(row.id, 'reject')">拒绝</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="转让负责人" name="transfer">
          <p style="margin-bottom:12px">选择新的负责人：</p>
          <el-select v-model="newPresidentId" style="width:100%" filterable placeholder="选择成员">
            <el-option v-for="m in clubMembers.filter(x => x.role !== 'president')" :key="m.id" :label="`${m.real_name} (ID:${m.id})`" :value="m.id" />
          </el-select>
          <div style="margin-top:16px">
            <el-button type="primary" :loading="transferring" @click="handleTransfer">确认转让</el-button>
          </div>
        </el-tab-pane>
        <el-tab-pane label="注销社团" name="dissolve">
          <el-alert title="注意" type="warning" show-icon :closable="false"
            description="申请注销后将无法进行任何社团活动，需等待管理员审批后正式删除社团，所有成员将变为未加入任何社团的状态。" />
          <div style="margin-top:16px">
            <el-button type="danger" :loading="dissolving" @click="handleDissolve">申请注销社团</el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
      <template #footer><el-button @click="manageVisible = false">关闭</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getClubs, createClub, approveClub, aiGenerateCopy, sendJoinRequest, getMyPendingRequests, getJoinRequests, handleJoinRequest, kickMember, transferClub, dissolveClub, getClubMembers, uploadFile, aiGeneratePosterPreview } from '../api'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
const clubs = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)
const aiLoading = ref(false)
const form = reactive({ name: '', description: '', tags: '' })

// Search
const searchKeyword = ref('')
let searchTimer = null
const handleSearch = () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => fetchClubs(), 300)
}

// Logo/Poster for create
const logoFileInput = ref(null)
const clubLogoPreview = ref('')
const clubPosterLoading = ref(false)

const handleLogoUploadClick = () => { logoFileInput.value?.click() }

const onLogoFileChange = async (e) => {
  const file = e.target.files?.[0]
  if (!file) return
  try {
    const { data } = await uploadFile(file)
    clubLogoPreview.value = data.url
  } catch {}
}

const handleGenerateClubPoster = async () => {
  if (!form.name) { ElMessage.warning('请先填写社团名称'); return }
  clubPosterLoading.value = true
  try {
    const { data } = await aiGeneratePosterPreview({
      title: form.name,
      description: form.description,
      location: form.tags,
      category: '社团招新'
    })
    clubLogoPreview.value = data.poster_url
  } catch {} finally { clubPosterLoading.value = false }
}

// Computed helpers
const isAdmin = computed(() => userStore.role === 'admin')
const isInClub = (row) => userStore.userInfo.club_id === row.id
const isPresidentOf = (row) => userStore.userInfo.id === row.president_id

// Track pending requests for current user
const myPendingRequests = ref([])

const hasPendingRequest = (row) => myPendingRequests.value.includes(row.id)

const fetchMyPendingRequests = async () => {
  if (userStore.role !== 'member' || !userStore.userInfo.id) return
  try {
    const { data } = await getMyPendingRequests()
    myPendingRequests.value = data
  } catch {}
}

const statusType = (s) => ({ pending: 'warning', approved: 'success', rejected: 'danger' }[s] || 'info')
const statusLabel = (s) => ({ pending: '待审批', approved: '已通过', rejected: '已拒绝' }[s] || s)

const fetchClubs = async () => {
  loading.value = true
  try {
    const params = searchKeyword.value.trim() ? { search: searchKeyword.value.trim() } : {}
    const { data } = await getClubs(params)
    clubs.value = data
  } catch {} finally { loading.value = false }
}

const openCreateDialog = () => {
  form.name = ''; form.description = ''; form.tags = ''
  clubLogoPreview.value = ''
  dialogVisible.value = true
}

const handleCreate = async () => {
  submitting.value = true
  try {
    const payload = { ...form }
    if (clubLogoPreview.value) payload.logo_url = clubLogoPreview.value
    await createClub(payload)
    ElMessage.success('创建成功，请等待管理员审批')
    dialogVisible.value = false
    clubLogoPreview.value = ''
    fetchClubs()
  } catch {} finally { submitting.value = false }
}

const handleApprove = async (id) => {
  try { await approveClub(id); ElMessage.success('已通过'); fetchClubs() } catch {}
}

const handleJoin = async (clubId) => {
  try {
    await sendJoinRequest(clubId)
    ElMessage.success('申请已提交，等待审批')
    fetchMyPendingRequests()
    fetchClubs()
  } catch {}
}

const handleAIDesc = async () => {
  aiLoading.value = true
  try {
    const prompt = form.name
      ? `为社团"${form.name}"写一段200字以内的社团简介。标签：${form.tags || '综合'}。要求吸引人，有号召力。`
      : '写一段200字以内的校园社团简介。'
    const { data } = await aiGenerateCopy({ prompt })
    form.description = data.text
  } catch {} finally { aiLoading.value = false }
}

// Manage dialog
const manageVisible = ref(false)
const managingClub = ref(null)
const manageTab = ref('members')
const clubMembers = ref([])
const joinRequests = ref([])
const newPresidentId = ref(null)
const transferring = ref(false)
const dissolving = ref(false)

const openManageDialog = async (row) => {
  managingClub.value = row
  manageVisible.value = true
  manageTab.value = 'members'
  await Promise.all([fetchClubMembers(row.id), fetchJoinRequestsFor(row.id)])
}

const fetchClubMembers = async (clubId) => {
  try { const { data } = await getClubMembers(clubId); clubMembers.value = data } catch { clubMembers.value = [] }
}

const fetchJoinRequestsFor = async (clubId) => {
  try { const { data } = await getJoinRequests(clubId); joinRequests.value = data } catch { joinRequests.value = [] }
}

const handleKick = async (userId) => {
  try {
    await kickMember(managingClub.value.id, userId)
    ElMessage.success('已踢出')
    fetchClubMembers(managingClub.value.id)
    fetchClubs()
  } catch {}
}

const handleRequestAction = async (requestId, action) => {
  try {
    await handleJoinRequest(managingClub.value.id, requestId, { action })
    ElMessage.success(action === 'approve' ? '已通过' : '已拒绝')
    fetchJoinRequestsFor(managingClub.value.id)
    fetchClubs()
  } catch {}
}

const handleTransfer = async () => {
  if (!newPresidentId.value) { ElMessage.warning('请选择新负责人'); return }
  try {
    await ElMessageBox.confirm('确认转让负责人权限？转让后您将成为普通成员。', '二次确认', { type: 'warning' })
    transferring.value = true
    await transferClub(managingClub.value.id, { new_president_id: newPresidentId.value })
    ElMessage.success('转让成功')
    manageVisible.value = false
    fetchClubs()
  } catch {} finally { transferring.value = false }
}

const handleDissolve = async () => {
  try {
    await ElMessageBox.confirm(
      '确认申请注销社团？提交后需等待管理员审批，审批通过后社团将被永久删除，所有成员将变为无社团状态。',
      '二次确认',
      { type: 'error', confirmButtonText: '确认注销', cancelButtonText: '取消' }
    )
    dissolving.value = true
    await dissolveClub(managingClub.value.id)
    ElMessage.success('注销申请已提交，等待管理员审批')
    manageVisible.value = false
    fetchClubs()
  } catch {} finally { dissolving.value = false }
}

onMounted(() => {
  fetchClubs()
  fetchMyPendingRequests()
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.header-right { display: flex; align-items: center; }
</style>
