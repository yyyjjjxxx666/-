<template>
  <div>
    <div class="page-header">
      <h2>🔔 通知中心 <el-badge v-if="unreadCount" :value="unreadCount" style="margin-left:8px" /></h2>
      <div class="header-actions">
        <el-button @click="markAll">全部已读</el-button>
        <el-button @click="clearRead">清理已读</el-button>
        <el-button v-if="canSend" type="primary" @click="sendVisible = true">发送通知</el-button>
      </div>
    </div>

    <el-table :data="notifications" border stripe v-loading="loading" empty-text="暂无通知" @row-click="handleRowClick" highlight-current-row>
      <el-table-column prop="title" label="标题" width="200" />
      <el-table-column prop="content" label="内容" show-overflow-tooltip />
      <el-table-column prop="source_label" label="来源" width="160">
        <template #default="{ row }">
          <el-tag size="small" :type="row.source_label === '校联社' ? 'danger' : 'primary'">{{ row.source_label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="时间" width="160" />
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag size="small" :type="row.is_read ? 'info' : 'warning'">{{ row.is_read ? '已读' : '未读' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80">
        <template #default="{ row }">
          <el-button v-if="!row.is_read" size="small" @click="handleMarkRead(row.id)">标为已读</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Send Notification Dialog -->
    <el-dialog v-model="sendVisible" title="发送通知" width="600px">
      <el-form :model="sendForm" label-width="80px">
        <el-form-item label="目标范围">
          <el-select v-model="sendForm.target" style="width:100%">
            <el-option v-if="userStore.role === 'admin'" label="全体用户" value="all" />
            <el-option v-if="userStore.role === 'admin'" label="指定社团" value="club" />
            <el-option label="未加入社团的学生" value="unaffiliated" />
            <el-option v-if="userStore.role === 'president'" label="本社团成员" value="club" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="sendForm.target === 'club' && userStore.role === 'admin'" label="目标社团">
          <el-select v-model="sendForm.club_id" style="width:100%" filterable placeholder="选择社团">
            <el-option v-for="c in allClubs" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="sendForm.title" placeholder="通知标题" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="sendForm.content" type="textarea" :rows="5" placeholder="通知内容" />
        </el-form-item>
      </el-form>
      <div style="margin-bottom:12px">
        <el-button size="small" :loading="aiLoading" @click="handleAIGenerate">
          🤖 {{ aiLoading ? '生成中...' : 'AI生成通知' }}
        </el-button>
        <el-button v-if="aiGeneratedText" size="small" @click="handleAIRegenerate">🔄 换一个</el-button>
      </div>
      <template #footer>
        <el-button @click="sendVisible = false">取消</el-button>
        <el-button type="primary" :loading="sending" @click="handleSend">发送</el-button>
      </template>
    </el-dialog>

    <!-- Notification Detail Dialog -->
    <el-dialog v-model="detailVisible" title="通知详情" width="500px">
      <h3 style="margin-bottom:12px">{{ detailNotification.title }}</h3>
      <div style="color:#666;margin-bottom:12px">
        <el-tag size="small" :type="detailNotification.source_label === '校联社' ? 'danger' : 'primary'">{{ detailNotification.source_label }}</el-tag>
        <span style="margin-left:12px">{{ detailNotification.created_at }}</span>
      </div>
      <div style="white-space:pre-wrap;line-height:1.8">{{ detailNotification.content }}</div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getNotifications, sendNotification, markRead, markAllRead, deleteReadNotifications, getUnreadCount, aiGenerateNotification, getClubs } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()

const userStore = useUserStore()
const notifications = ref([])
const loading = ref(false)
const unreadCount = ref(0)
const sendVisible = ref(false)
const sending = ref(false)
const aiLoading = ref(false)
const aiGeneratedText = ref(false)
const allClubs = ref([])

const canSend = computed(() => userStore.role === 'admin' || userStore.role === 'president')

const sendForm = reactive({ target: '', club_id: null, title: '', content: '' })

const fetchNotifications = async () => {
  loading.value = true
  try {
    const { data } = await getNotifications()
    notifications.value = data
    unreadCount.value = data.filter(n => !n.is_read).length
  } catch {} finally { loading.value = false }
}

const fetchUnreadCount = async () => {
  try { const { data } = await getUnreadCount(); unreadCount.value = data.count } catch {}
}

const handleMarkRead = async (id) => {
  try { await markRead(id); fetchNotifications() } catch {}
}

const markAll = async () => {
  try { await markAllRead(); ElMessage.success('已全部标记为已读'); fetchNotifications() } catch {}
}

const clearRead = async () => {
  try { await deleteReadNotifications(); ElMessage.success('已清理已读通知'); fetchNotifications() } catch {}
}

const detailVisible = ref(false)
const detailNotification = ref({})

const handleRowClick = async (row) => {
  if (!row.is_read) {
    try { await markRead(row.id) } catch {}
  }
  if (row.club_id) {
    router.push(`/clubs/${row.club_id}`)
  } else {
    detailNotification.value = row
    detailVisible.value = true
  }
}

const handleAIGenerate = async () => {
  aiLoading.value = true
  try {
    const { data } = await aiGenerateNotification({
      type: sendForm.target === 'unaffiliated' ? '招募通知' : '社团公告',
      club_name: allClubs.value.find(c => c.id === sendForm.club_id)?.name || '',
      extra: sendForm.title || ''
    })
    sendForm.content = data.text
    aiGeneratedText.value = true
  } catch {} finally { aiLoading.value = false }
}

const handleAIRegenerate = () => { handleAIGenerate() }

const handleSend = async () => {
  if (!sendForm.title || !sendForm.content) { ElMessage.warning('请填写标题和内容'); return }
  if (sendForm.target === 'club' && userStore.role === 'admin' && !sendForm.club_id) { ElMessage.warning('请选择目标社团'); return }
  sending.value = true
  try {
    await sendNotification({
      target: sendForm.target,
      club_id: sendForm.club_id,
      title: sendForm.title,
      content: sendForm.content
    })
    ElMessage.success('发送成功')
    sendVisible.value = false
    sendForm.title = ''; sendForm.content = ''; sendForm.target = ''; sendForm.club_id = null
    aiGeneratedText.value = false
    fetchNotifications()
  } catch {} finally { sending.value = false }
}

onMounted(async () => {
  fetchNotifications()
  if (canSend.value) {
    try { const { data } = await getClubs(); allClubs.value = data } catch {}
  }
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.header-actions { display: flex; gap: 8px; }
</style>
