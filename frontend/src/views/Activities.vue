<template>
  <div>
    <div class="page-header">
      <h2>活动管理</h2>
      <el-button v-if="showCreate" type="primary" @click="openCreateDialog">发布活动</el-button>
    </div>

    <el-table :data="activities" border stripe v-loading="loading">
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
          <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="340">
        <template #default="{ row }">
          <el-button v-if="row.status === 'registration' && !row.is_registered" size="small" type="success" @click="handleRegister(row.id)">报名</el-button>
          <el-tag v-if="row.is_registered" type="success" size="small">已报名</el-tag>
          <el-button v-if="canManage(row)" size="small" type="warning" @click="handleGenerateQR(row.id)">📱 生成签到码</el-button>
          <el-button v-if="canManage(row) && row.checkin_qr" size="small" @click="showQR(row)">📷 查看签到码</el-button>
          <el-button size="small" @click="openCopyDialog(row)">📝 AI文案</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Create Dialog -->
    <el-dialog v-model="dialogVisible" title="发布活动" width="550px">
      <el-form :model="form">
        <el-form-item v-if="userStore.role !== 'president'" label="所属社团ID"><el-input-number v-model="form.club_id" :min="1" /></el-form-item>
        <el-form-item label="活动名称"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="4" />
          <div style="margin-top:6px">
            <el-button size="small" :loading="aiCopyLoading" @click="handleAICopyForCreate">
              🤖 {{ aiCopyLoading ? '生成中...' : 'AI生成文案' }}
            </el-button>
            <el-button v-if="form.description" size="small" :loading="aiCopyLoading" @click="handleAICopyForCreate" style="margin-left:6px">
              🔄 重新生成
            </el-button>
          </div>
        </el-form-item>
        <el-form-item label="地点"><el-input v-model="form.location" /></el-form-item>
        <el-form-item label="开始时间"><el-date-picker v-model="form.start_time" type="datetime" /></el-form-item>
        <el-form-item label="结束时间"><el-date-picker v-model="form.end_time" type="datetime" /></el-form-item>
        <el-form-item label="报名截止"><el-date-picker v-model="form.registration_deadline" type="datetime" /></el-form-item>
        <el-form-item label="人数上限"><el-input-number v-model="form.max_participants" :min="1" /></el-form-item>
        <el-form-item label="活动海报">
          <el-button size="small" @click="handlePosterUploadClick">📷 上传海报</el-button>
          <input ref="posterFileInput" type="file" accept="image/*" style="display:none" @change="onPosterFileChange" />
          <el-button size="small" style="margin-left:8px" :loading="posterForCreateLoading" @click="handleGeneratePosterForCreate">🎨 AI生成海报</el-button>
        </el-form-item>
        <el-form-item v-if="createPosterPreview">
          <img :src="createPosterPreview" style="max-width:200px;max-height:200px;border-radius:8px" />
          <el-button size="small" type="danger" style="margin-left:8px" @click="createPosterPreview = ''">移除</el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreate">确认发布</el-button>
      </template>
    </el-dialog>

    <!-- Copy Dialog -->
    <el-dialog v-model="copyVisible" title="AI生成的文案" width="600px">
      <div style="white-space: pre-wrap; background:#f5f5f5; padding:16px; border-radius:8px; min-height:100px;">{{ copyText }}</div>
      <div style="margin-top:8px">
        <el-button size="small" :loading="copyGenerating" @click="handleRegenerateCopy">🔄 换一个</el-button>
      </div>
      <template #footer>
        <el-button @click="copyVisible = false">关闭</el-button>
        <el-button type="primary" @click="copyToClipboard">复制文案</el-button>
      </template>
    </el-dialog>

    <!-- QR Dialog -->
    <el-dialog v-model="qrVisible" title="签到二维码" width="400px">
      <div style="text-align:center">
        <img v-if="qrUrl" :src="qrUrl" style="max-width:300px" />
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
const activities = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)
const copyVisible = ref(false)
const copyText = ref('')
const copyGenerating = ref(false)
const aiCopyLoading = ref(false)
const qrVisible = ref(false)
const qrUrl = ref('')
const copyTargetRow = ref(null)

// Poster in create dialog
const posterFileInput = ref(null)
const createPosterPreview = ref('')
const posterForCreateLoading = ref(false)

const form = reactive({
  club_id: 1, title: '', description: '', location: '',
  start_time: null, end_time: null, registration_deadline: null, max_participants: 100,
})

const showCreate = computed(() => userStore.role === 'president' || userStore.role === 'admin')

const openCreateDialog = () => {
  if (userStore.role === 'president') {
    form.club_id = userStore.userInfo.club_id
    if (!form.club_id) {
      ElMessage.warning('您还未加入社团，请先创建或加入社团')
      return
    }
  }
  dialogVisible.value = true
}

const canManage = (row) => {
  if (userStore.role === 'admin') return true
  if (userStore.role === 'president' && userStore.userInfo.club_id === row.club_id) return true
  return false
}

const statusType = (s) => ({ pending: 'warning', approved: 'success', registration: 'primary', ongoing: 'success', finished: 'info' }[s] || 'info')
const statusLabel = (s) => ({ pending: '待审批', approved: '已通过', registration: '报名中', ongoing: '进行中', finished: '已结束' }[s] || s)

const fetchActivities = async () => {
  loading.value = true
  try { const { data } = await getActivities(); activities.value = data } catch {} finally { loading.value = false }
}

const handleCreate = async () => {
  if (!form.club_id) return ElMessage.warning('请填写所属社团ID')
  if (!form.title) return ElMessage.warning('请填写活动名称')
  if (!form.start_time) return ElMessage.warning('请选择开始时间')
  if (!form.end_time) return ElMessage.warning('请选择结束时间')
  submitting.value = true
  try {
    const payload = { ...form }
    if (createPosterPreview.value) payload.poster_url = createPosterPreview.value
    await createActivity(payload)
    ElMessage.success('发布成功')
    dialogVisible.value = false
    form.title = ''; form.description = ''; form.location = ''
    form.start_time = null; form.end_time = null; form.registration_deadline = null
    form.max_participants = 100
    createPosterPreview.value = ''
    fetchActivities()
  } catch {} finally { submitting.value = false }
}

const handlePosterUploadClick = () => { posterFileInput.value?.click() }

const onPosterFileChange = async (e) => {
  const file = e.target.files?.[0]
  if (!file) return
  try {
    const { data } = await uploadFile(file)
    createPosterPreview.value = data.url
  } catch {}
}

const handleGeneratePosterForCreate = async () => {
  if (!form.title) { ElMessage.warning('请先填写活动名称'); return }
  posterForCreateLoading.value = true
  try {
    const { data } = await aiGeneratePosterPreview({
      title: form.title,
      description: form.description,
      location: form.location,
      start_time: form.start_time?.toISOString(),
      end_time: form.end_time?.toISOString(),
    })
    createPosterPreview.value = data.poster_url
  } catch {} finally { posterForCreateLoading.value = false }
}

const handleRegister = async (id) => {
  try { await registerActivity(id); ElMessage.success('报名成功'); fetchActivities() } catch {}
}

const openCopyDialog = (row) => {
  copyTargetRow.value = row
  copyVisible.value = true
  copyText.value = ''
  handleGenerateCopy(row)
}

const handleGenerateCopy = async (row) => {
  copyGenerating.value = true
  try {
    const { data } = await aiGenerateCopy({ prompt: `为活动"${row.title}"写一段招新/宣传文案。活动描述：${row.description || ''}。地点：${row.location || ''}。` })
    copyText.value = data.text
  } catch {} finally { copyGenerating.value = false }
}

const handleRegenerateCopy = () => {
  if (copyTargetRow.value) handleGenerateCopy(copyTargetRow.value)
}

const handleAICopyForCreate = async () => {
  aiCopyLoading.value = true
  try {
    const prompt = form.title
      ? `为活动"${form.title}"写一段200字以内的活动宣传文案。地点：${form.location || '待定'}。要求吸引人，有号召力。`
      : `写一段200字以内的校园活动宣传文案。要求吸引人，有号召力。`
    const { data } = await aiGenerateCopy({ prompt })
    form.description = data.text
  } catch {} finally { aiCopyLoading.value = false }
}

const handleGenerateQR = async (id) => {
  try {
    const { data } = await generateQR(id)
    ElMessage.success('签到码已生成')
    fetchActivities()
  } catch {}
}

const showQR = (row) => {
  qrUrl.value = row.checkin_qr
  qrVisible.value = true
}

const copyToClipboard = () => {
  navigator.clipboard.writeText(copyText.value)
  ElMessage.success('已复制')
}

onMounted(fetchActivities)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
</style>
