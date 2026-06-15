<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">
        <el-icon :size="22"><Bell /></el-icon>
        通知中心
        <el-badge v-if="unreadCount" :value="unreadCount" style="margin-left:8px" />
      </h2>
      <div class="header-actions">
        <el-button @click="markAll">
          <el-icon :size="14"><Select /></el-icon> 全部已读
        </el-button>
        <el-button @click="clearRead">
          <el-icon :size="14"><Delete /></el-icon> 清理已读
        </el-button>
        <el-button v-if="canSend" type="primary" @click="sendVisible = true">
          <el-icon :size="14"><Plus /></el-icon> 发送通知
        </el-button>
      </div>
    </div>

    <!-- Notification Cards -->
    <div v-loading="loading" class="notif-list">
      <div
        v-for="n in notifications"
        :key="n.id"
        class="notif-card glass-card"
        :class="{ unread: !n.is_read }"
        @click="handleRowClick(n)"
      >
        <div class="notif-left" :class="n.source_label === '校联社' ? 'accent-danger' : 'accent-primary'" />
        <div class="notif-body">
          <div class="notif-top">
            <h4 class="notif-title">{{ n.title }}</h4>
            <el-tag size="small" round :type="n.source_label === '校联社' ? 'danger' : 'primary'">{{ n.source_label }}</el-tag>
          </div>
          <p class="notif-content">{{ n.content }}</p>
          <div class="notif-meta">
            <span class="notif-time"><el-icon :size="12"><Clock /></el-icon> {{ n.created_at }}</span>
            <el-tag size="small" :type="n.is_read ? 'info' : 'warning'" round>{{ n.is_read ? '已读' : '未读' }}</el-tag>
            <el-button v-if="!n.is_read" size="small" text type="primary" @click.stop="handleMarkRead(n.id)">标为已读</el-button>
          </div>
        </div>
      </div>
      <el-empty v-if="!notifications.length" description="暂无通知" />
    </div>

    <!-- Send Notification Dialog -->
    <el-dialog v-model="sendVisible" title="发送通知" width="600px" class="modern-dialog">
      <el-form :model="sendForm" label-position="top">
        <el-form-item label="目标范围">
          <el-select v-model="sendForm.target" style="width:100%" size="large">
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
          <el-input v-model="sendForm.title" placeholder="通知标题" size="large" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="sendForm.content" type="textarea" :rows="5" placeholder="通知内容" />
        </el-form-item>
      </el-form>
      <div style="margin-bottom:12px">
        <el-button size="small" :loading="aiLoading" @click="handleAIGenerate">
          <el-icon :size="14"><Cpu /></el-icon>
          {{ aiLoading ? '生成中...' : 'AI生成通知' }}
        </el-button>
        <el-button v-if="aiGeneratedText" size="small" @click="handleAIRegenerate">
          <el-icon :size="14"><Refresh /></el-icon> 换一个
        </el-button>
      </div>
      <template #footer>
        <el-button @click="sendVisible = false">取消</el-button>
        <el-button type="primary" :loading="sending" @click="handleSend">发送</el-button>
      </template>
    </el-dialog>

    <!-- Notification Detail Dialog -->
    <el-dialog v-model="detailVisible" title="通知详情" width="500px" class="modern-dialog">
      <h3 style="margin-bottom:12px;color:var(--text-primary)">{{ detailNotification.title }}</h3>
      <div style="color:var(--text-muted);margin-bottom:16px;display:flex;align-items:center;gap:12px">
        <el-tag size="small" :type="detailNotification.source_label === '校联社' ? 'danger' : 'primary'" round>{{ detailNotification.source_label }}</el-tag>
        <span>{{ detailNotification.created_at }}</span>
      </div>
      <div class="detail-content">{{ detailNotification.content }}</div>
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

const router = useRouter(); const userStore = useUserStore()
const notifications = ref([]); const loading = ref(false); const unreadCount = ref(0)
const sendVisible = ref(false); const sending = ref(false); const aiLoading = ref(false)
const aiGeneratedText = ref(false); const allClubs = ref([])

const canSend = computed(() => userStore.role === 'admin' || userStore.role === 'president')
const sendForm = reactive({ target: '', club_id: null, title: '', content: '' })

const fetchNotifications = async () => {
  loading.value = true
  try { const { data } = await getNotifications(); notifications.value = data; unreadCount.value = data.filter(n => !n.is_read).length } catch {} finally { loading.value = false }
}
const handleMarkRead = async (id) => { try { await markRead(id); fetchNotifications() } catch {} }
const markAll = async () => { try { await markAllRead(); ElMessage.success('已全部标记为已读'); fetchNotifications() } catch {} }
const clearRead = async () => { try { await deleteReadNotifications(); ElMessage.success('已清理已读通知'); fetchNotifications() } catch {} }

const detailVisible = ref(false); const detailNotification = ref({})
const handleRowClick = async (row) => {
  if (!row.is_read) { try { await markRead(row.id) } catch {} }
  if (row.club_id) { router.push(`/clubs/${row.club_id}`) }
  else { detailNotification.value = row; detailVisible.value = true }
}
const handleAIGenerate = async () => {
  aiLoading.value = true
  try { const { data } = await aiGenerateNotification({ type: sendForm.target === 'unaffiliated' ? '招募通知' : '社团公告', club_name: allClubs.value.find(c => c.id === sendForm.club_id)?.name || '', extra: sendForm.title || '' }); sendForm.content = data.text; aiGeneratedText.value = true } catch {} finally { aiLoading.value = false }
}
const handleAIRegenerate = () => { handleAIGenerate() }
const handleSend = async () => {
  if (!sendForm.title || !sendForm.content) { ElMessage.warning('请填写标题和内容'); return }
  if (sendForm.target === 'club' && userStore.role === 'admin' && !sendForm.club_id) { ElMessage.warning('请选择目标社团'); return }
  sending.value = true
  try { await sendNotification({ target: sendForm.target, club_id: sendForm.club_id, title: sendForm.title, content: sendForm.content }); ElMessage.success('发送成功'); sendVisible.value = false; sendForm.title = ''; sendForm.content = ''; sendForm.target = ''; sendForm.club_id = null; aiGeneratedText.value = false; fetchNotifications() } catch {} finally { sending.value = false }
}

onMounted(async () => { fetchNotifications(); if (canSend.value) { try { const { data } = await getClubs(); allClubs.value = data } catch {} } })
</script>

<style scoped>
.page-container { max-width: 1000px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-title { display: flex; align-items: center; gap: 8px; font-size: var(--text-2xl); font-weight: var(--font-bold); color: var(--text-primary); margin: 0; }
.header-actions { display: flex; gap: 8px; }

.notif-list { display: flex; flex-direction: column; gap: 8px; }
.notif-card { display: flex; overflow: hidden; padding: 0; transition: transform var(--transition-fast); }
.notif-card:hover { transform: translateX(4px); }
.notif-card.unread { border-color: var(--border-accent); }
.notif-left { width: 4px; flex-shrink: 0; }
.notif-left.accent-danger { background: var(--gradient-accent); }
.notif-left.accent-primary { background: var(--gradient-primary); }
.notif-body { padding: 16px 20px; flex: 1; }
.notif-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.notif-title { margin: 0; font-size: var(--text-sm); font-weight: var(--font-semibold); color: var(--text-primary); }
.notif-content { color: var(--text-secondary); font-size: var(--text-sm); line-height: 1.5; margin-bottom: 8px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.notif-meta { display: flex; align-items: center; gap: 10px; }
.notif-time { color: var(--text-muted); font-size: var(--text-xs); display: flex; align-items: center; gap: 4px; }
.detail-content { white-space: pre-wrap; line-height: 1.8; color: var(--text-primary); padding: 16px; background: var(--bg-secondary); border-radius: var(--radius-md); }
</style>
