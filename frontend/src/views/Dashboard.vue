<template>
  <el-container class="layout">
    <el-header class="header">
      <span class="logo">🏫 社团管理系统</span>
      <div class="header-right">
        <el-badge v-if="userStore.role === 'admin'" :value="pendingCount" :hidden="!pendingCount" style="margin-right:12px">
          <el-button size="small" type="warning" circle @click="$router.push('/admin-approval')">📋</el-button>
        </el-badge>
        <el-badge :value="unreadCount" :hidden="!unreadCount" style="margin-right:12px">
          <el-button size="small" circle @click="$router.push('/notifications')">🔔</el-button>
        </el-badge>
        <span class="user-name">{{ userStore.userInfo.real_name }}</span>
        <el-tag size="small">{{ roleLabel }}</el-tag>
        <el-dropdown trigger="click" @command="handleDropdownCommand">
          <el-button size="small" type="default">设置 ▼</el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="resetPassword">🔒 重置密码</el-dropdown-item>
              <el-dropdown-item v-if="userStore.userInfo.club_id" command="leaveClub">🚪 退出社团</el-dropdown-item>
              <el-dropdown-item command="logout" divided>🔌 退出账号</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>
    <el-container>
      <el-aside width="200px" class="aside">
        <el-menu :default-active="route.path" router class="menu">
          <el-menu-item index="/dashboard">📊 首页概览</el-menu-item>
          <el-menu-item index="/clubs">🏠 社团管理</el-menu-item>
          <el-menu-item index="/activities">📅 活动管理</el-menu-item>
          <el-menu-item index="/notifications">🔔 通知中心</el-menu-item>
          <el-menu-item index="/ai-recommend">🤖 AI智能推荐</el-menu-item>
          <el-menu-item index="/checkin">📷 签到考勤</el-menu-item>
          <el-menu-item v-if="userStore.role === 'admin'" index="/admin-approval">📋 审批管理</el-menu-item>
        </el-menu>
      </el-aside>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>

    <!-- AI Assistant -->
    <AIAssistant />

    <!-- Reset Password Dialog -->
    <el-dialog v-model="passwordVisible" title="重置密码" width="400px">
      <el-form :model="passwordForm">
        <el-form-item label="旧密码"><el-input v-model="passwordForm.old_password" type="password" show-password /></el-form-item>
        <el-form-item label="新密码"><el-input v-model="passwordForm.new_password" type="password" show-password /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordVisible = false">取消</el-button>
        <el-button type="primary" :loading="resettingPassword" @click="handleResetPassword">确认</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, computed, reactive, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '../stores/user'
import { getUnreadCount, resetPassword, leaveClub, getPendingCount } from '../api'
import AIAssistant from '../components/AIAssistant.vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const unreadCount = ref(0)
const pendingCount = ref(0)
const passwordVisible = ref(false)
const resettingPassword = ref(false)
const passwordForm = reactive({ old_password: '', new_password: '' })

const roleLabel = computed(() => {
  const map = { admin: '管理员', president: '社团负责人', member: '成员' }
  return map[userStore.role] || userStore.role
})

const fetchUnread = async () => {
  try { const { data } = await getUnreadCount(); unreadCount.value = data.count } catch {}
}

const fetchPendingCount = async () => {
  if (userStore.role !== 'admin') return
  try { const { data } = await getPendingCount(); pendingCount.value = data.total } catch {}
}

let pollTimer = null

watch(() => route.path, (path) => {
  if (path === '/notifications') unreadCount.value = 0
})

const handleDropdownCommand = async (command) => {
  switch (command) {
    case 'logout':
      userStore.logout()
      router.push('/login')
      break
    case 'leaveClub':
      await handleLeaveClub()
      break
    case 'resetPassword':
      passwordForm.old_password = ''
      passwordForm.new_password = ''
      passwordVisible.value = true
      break
  }
}

const handleLeaveClub = async () => {
  try {
    await ElMessageBox.confirm('确认退出当前社团？退出后将自动通知社团全员。', '二次确认', { type: 'warning' })
    await leaveClub(userStore.userInfo.club_id)
    ElMessage.success('已退出社团')
    userStore.userInfo.club_id = null
    localStorage.setItem('userInfo', JSON.stringify(userStore.userInfo))
  } catch {}
}

const handleResetPassword = async () => {
  if (!passwordForm.old_password || !passwordForm.new_password) {
    ElMessage.warning('请填写完整')
    return
  }
  resettingPassword.value = true
  try {
    await resetPassword({ ...passwordForm })
    ElMessage.success('密码已重置，请重新登录')
    passwordVisible.value = false
    userStore.logout()
    router.push('/login')
  } catch {} finally { resettingPassword.value = false }
}

onMounted(() => {
  fetchUnread()
  fetchPendingCount()
  pollTimer = setInterval(() => { fetchUnread(); fetchPendingCount() }, 30000)
})

onBeforeUnmount(() => {
  clearInterval(pollTimer)
})
</script>

<style scoped>
.header { background: #1e3c72; color: #fff; display: flex; align-items: center; justify-content: space-between; height: 56px; padding: 0 20px; position: relative; }
.logo { font-size: 18px; font-weight: bold; }
.header-middle { position: relative; }
.header-right { display: flex; align-items: center; gap: 12px; }
.user-name { font-size: 14px; }
.aside { background: #fafafa; border-right: 1px solid #e8e8e8; min-height: calc(100vh - 56px); }
.menu { border-right: none; }
.main { padding: 24px; background: #f0f2f5; }
.search-dropdown { position: absolute; top: 100%; left: 0; right: 0; background: #fff; border-radius: 4px; box-shadow: 0 2px 12px rgba(0,0,0,.15); z-index: 1000; }
.search-item { display: flex; justify-content: space-between; padding: 10px 12px; cursor: pointer; border-bottom: 1px solid #f0f0f0; color: #333; }
.search-item:hover { background: #f5f7fa; }
.search-name { font-weight: bold; }
.search-tags { color: #999; font-size: 12px; }
</style>
