<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">
        <el-icon :size="22"><Calendar /></el-icon>
        活动管理
      </h2>
      <el-button v-if="showCreate" type="primary" size="large" @click="openCreateDialog">
        <el-icon :size="16"><Plus /></el-icon>
        发布活动
      </el-button>
    </div>

    <!-- Table Card -->
    <div class="glass-card table-card" style="cursor:default">
      <el-table :data="activities" border stripe v-loading="loading" class="modern-table">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="title" label="活动名称">
          <template #default="{ row }">
            <el-link type="primary" @click="$router.push(`/activities/${row.id}`)">{{ row.title }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="location" label="地点" />
        <el-table-column prop="registration_deadline" label="报名截止" width="160" />
        <el-table-column prop="current_participants" label="报名人数" width="80" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" round>{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="360">
          <template #default="{ row }">
            <div class="action-btns">
              <el-button v-if="row.status === 'registration' && !row.is_registered" size="small" type="success" @click="handleRegister(row.id)">
                <el-icon :size="14"><Select /></el-icon> 报名
              </el-button>
              <el-tag v-if="row.is_registered" type="success" size="small" round>已报名</el-tag>
              <el-button v-if="canManage(row)" size="small" type="warning" @click="handleGenerateQR(row.id)">
                <el-icon :size="14"><Iphone /></el-icon> 生成签到码
              </el-button>
              <el-button v-if="canManage(row) && row.checkin_qr" size="small" @click="showQR(row)">
                <el-icon :size="14"><Camera /></el-icon> 查看签到码
              </el-button>
              <el-button size="small" @click="openCopyDialog(row)">
                <el-icon :size="14"><EditPen /></el-icon> AI文案
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Create Dialog -->
    <el-dialog v-model="dialogVisible" title="发布活动" width="550px" class="modern-dialog">
      <el-form :model="form" label-position="top">
        <el-form-item v-if="userStore.role !== 'president'" label="所属社团ID">
          <el-input-number v-model="form.club_id" :min="1" />
        </el-form-item>
        <el-form-item label="活动名称">
          <el-input v-model="form.title" size="large" placeholder="输入活动名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="4" placeholder="输入活动描述" />
          <div style="margin-top:8px">
            <el-button size="small" :loading="aiCopyLoading" @click="handleAICopyForCreate">
              <el-icon :size="14"><Cpu /></el-icon>
              {{ aiCopyLoading ? '生成中...' : 'AI生成文案' }}
            </el-button>
            <el-button v-if="form.description" size="small" :loading="aiCopyLoading" @click="handleAICopyForCreate" style="margin-left:6px">
              <el-icon :size="14"><Refresh /></el-icon> 重新生成
            </el-button>
          </div>
        </el-form-item>
        <el-form-item label="地点"><el-input v-model="form.location" size="large" /></el-form-item>
        <el-form-item label="开始时间"><el-date-picker v-model="form.start_time" type="datetime" style="width:100%" /></el-form-item>
        <el-form-item label="结束时间"><el-date-picker v-model="form.end_time" type="datetime" style="width:100%" /></el-form-item>
        <el-form-item label="报名截止"><el-date-picker v-model="form.registration_deadline" type="datetime" style="width:100%" /></el-form-item>
        <el-form-item label="人数上限"><el-input-number v-model="form.max_participants" :min="1" /></el-form-item>
        <el-form-item label="活动海报">
          <el-button size="small" @click="handlePosterUploadClick">
            <el-icon :size="14"><Upload /></el-icon> 上传海报
          </el-button>
          <input ref="posterFileInput" type="file" accept="image/*" style="display:none" @change="onPosterFileChange" />
          <el-button size="small" style="margin-left:8px" :loading="posterForCreateLoading" @click="handleGeneratePosterForCreate">
            <el-icon :size="14"><Brush /></el-icon> AI生成海报
          </el-button>
        </el-form-item>
        <el-form-item v-if="createPosterPreview">
          <img :src="createPosterPreview" class="preview-img" alt="海报预览" />
          <el-button size="small" type="danger" style="margin-left:8px" @click="createPosterPreview = ''">移除</el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreate">确认发布</el-button>
      </template>
    </el-dialog>

    <!-- Copy Dialog -->
    <el-dialog v-model="copyVisible" title="AI 生成文案" width="600px" class="modern-dialog">
      <div class="copy-content">{{ copyText || '点击下方按钮生成文案...' }}</div>
      <div style="margin-top:12px">
        <el-button size="small" :loading="copyGenerating" @click="handleRegenerateCopy">
          <el-icon :size="14"><Refresh /></el-icon> 换一个
        </el-button>
      </div>
      <template #footer>
        <el-button @click="copyVisible = false">关闭</el-button>
        <el-button type="primary" @click="copyToClipboard">复制文案</el-button>
      </template>
    </el-dialog>

    <!-- QR Dialog -->
    <el-dialog v-model="qrVisible" title="签到二维码" width="400px" class="modern-dialog">
      <div style="text-align:center;padding:20px">
        <img v-if="qrUrl" :src="qrUrl" style="max-width:280px;border-radius:var(--radius-md)" alt="签到二维码" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { getActivities, createActivity, registerActivity, aiGenerateCopy, generateQR, uploadFile, aiGeneratePosterPreview } from '../api'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
const activities = ref([]); const loading = ref(false)
const dialogVisible = ref(false); const submitting = ref(false)
const copyVisible = ref(false); const copyText = ref(''); const copyGenerating = ref(false)
const aiCopyLoading = ref(false); const qrVisible = ref(false); const qrUrl = ref('')
const copyTargetRow = ref(null)
const posterFileInput = ref(null); const createPosterPreview = ref(''); const posterForCreateLoading = ref(false)

const form = reactive({ club_id: 1, title: '', description: '', location: '', start_time: null, end_time: null, registration_deadline: null, max_participants: 100 })
const showCreate = computed(() => userStore.role === 'president' || userStore.role === 'admin')

const openCreateDialog = () => {
  if (userStore.role === 'president') { form.club_id = userStore.userInfo.club_id; if (!form.club_id) { ElMessage.warning('您还未加入社团'); return } }
  dialogVisible.value = true
}
const canManage = (row) => userStore.role === 'admin' || (userStore.role === 'president' && userStore.userInfo.club_id === row.club_id)
const statusType = (s) => ({ pending: 'warning', approved: 'success', registration: 'primary', ongoing: 'success', finished: 'info' }[s] || 'info')
const statusLabel = (s) => ({ pending: '待审批', approved: '已通过', registration: '报名中', ongoing: '进行中', finished: '已结束' }[s] || s)

const fetchActivities = async () => { loading.value = true; try { const { data } = await getActivities(); activities.value = data } catch {} finally { loading.value = false } }
const handleCreate = async () => {
  if (!form.club_id) return ElMessage.warning('请填写所属社团ID')
  if (!form.title) return ElMessage.warning('请填写活动名称')
  submitting.value = true
  try { const payload = { ...form }; if (createPosterPreview.value) payload.poster_url = createPosterPreview.value; await createActivity(payload); ElMessage.success('发布成功'); dialogVisible.value = false; form.title = ''; form.description = ''; form.location = ''; form.start_time = null; form.end_time = null; form.registration_deadline = null; form.max_participants = 100; createPosterPreview.value = ''; fetchActivities() } catch {} finally { submitting.value = false }
}
const handlePosterUploadClick = () => { posterFileInput.value?.click() }
const onPosterFileChange = async (e) => { const file = e.target.files?.[0]; if (!file) return; try { const { data } = await uploadFile(file); createPosterPreview.value = data.url } catch {} }
const handleGeneratePosterForCreate = async () => {
  if (!form.title) { ElMessage.warning('请先填写活动名称'); return }
  posterForCreateLoading.value = true
  try { const { data } = await aiGeneratePosterPreview({ title: form.title, description: form.description, location: form.location, start_time: form.start_time?.toISOString(), end_time: form.end_time?.toISOString() }); createPosterPreview.value = data.poster_url } catch {} finally { posterForCreateLoading.value = false }
}
const handleRegister = async (id) => { try { await registerActivity(id); ElMessage.success('报名成功'); fetchActivities() } catch {} }
const openCopyDialog = (row) => { copyTargetRow.value = row; copyVisible.value = true; copyText.value = ''; handleGenerateCopy(row) }
const handleGenerateCopy = async (row) => { copyGenerating.value = true; try { const { data } = await aiGenerateCopy({ prompt: `为活动"${row.title}"写一段招新/宣传文案。活动描述：${row.description || ''}。地点：${row.location || ''}。` }); copyText.value = data.text } catch {} finally { copyGenerating.value = false } }
const handleRegenerateCopy = () => { if (copyTargetRow.value) handleGenerateCopy(copyTargetRow.value) }
const handleAICopyForCreate = async () => {
  aiCopyLoading.value = true
  try { const prompt = form.title ? `为活动"${form.title}"写一段200字以内的活动宣传文案。` : '写一段200字以内的校园活动宣传文案。'; const { data } = await aiGenerateCopy({ prompt }); form.description = data.text } catch {} finally { aiCopyLoading.value = false }
}
const handleGenerateQR = async (id) => { try { const { data } = await generateQR(id); ElMessage.success('签到码已生成'); fetchActivities() } catch {} }
const showQR = (row) => { qrUrl.value = row.checkin_qr; qrVisible.value = true }
const copyToClipboard = () => { navigator.clipboard.writeText(copyText.value); ElMessage.success('已复制') }

onMounted(fetchActivities)
</script>

<style scoped>
.page-container { max-width: 1400px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-title { display: flex; align-items: center; gap: 10px; font-size: var(--text-2xl); font-weight: var(--font-bold); color: var(--text-primary); margin: 0; }
.table-card { padding: 20px; }
.action-btns { display: flex; gap: 4px; align-items: center; flex-wrap: wrap; }
.copy-content { white-space: pre-wrap; background: var(--bg-secondary); padding: 20px; border-radius: var(--radius-md); min-height: 100px; color: var(--text-primary); line-height: 1.7; }
.preview-img { max-width: 200px; max-height: 200px; border-radius: var(--radius-md); }
.modern-table :deep(.el-table__header th) { background: var(--bg-secondary); color: var(--text-primary); font-weight: var(--font-semibold); }
.modern-table :deep(.el-table__body tr:hover > td) { background: var(--color-primary-50) !important; }
[data-theme="dark"] .modern-table :deep(.el-table__body tr:hover > td) { background: rgba(124, 58, 237, 0.08) !important; }
</style>
