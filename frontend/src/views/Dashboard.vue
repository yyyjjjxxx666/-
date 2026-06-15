<template>
  <el-container class="layout">
    <!-- ── Glass Header ── -->
    <el-header class="header glass-header">
      <div class="header-left">
        <span class="logo" @click="$router.push('/dashboard')">
          <el-icon :size="22"><School /></el-icon>
          <span class="logo-text">社团管理系统</span>
        </span>
      </div>

      <div class="header-right">
        <!-- Theme Toggle -->
        <el-button size="small" circle class="theme-toggle" @click="themeStore.toggle()">
          <el-icon :size="16"><Sunny v-if="!themeStore.isDark" /></el-icon>
          <span v-if="themeStore.isDark" style="font-size:16px">🌙</span>
        </el-button>

        <!-- Admin Approval Badge -->
        <el-badge v-if="userStore.role === 'admin'" :value="pendingCount" :hidden="!pendingCount">
          <el-button size="small" circle class="header-btn" @click="$router.push('/admin-approval')">
            <el-icon :size="16"><List /></el-icon>
          </el-button>
        </el-badge>

        <!-- Notification Badge -->
        <el-badge :value="unreadCount" :hidden="!unreadCount">
          <el-button size="small" circle class="header-btn" @click="$router.push('/notifications')">
            <el-icon :size="16"><Bell /></el-icon>
          </el-button>
        </el-badge>

        <!-- User Info -->
        <span class="user-name">{{ userStore.userInfo.real_name }}</span>
        <el-tag size="small" effect="plain" round>{{ roleLabel }}</el-tag>

        <!-- Settings Dropdown -->
        <el-dropdown trigger="click" @command="handleDropdownCommand">
          <el-button size="small" class="settings-btn">
            <el-icon :size="14"><Setting /></el-icon>
            <span>设置</span>
            <el-icon :size="12" class="arrow-icon"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="resetPassword">
                <el-icon :size="14"><Lock /></el-icon>
                <span>重置密码</span>
              </el-dropdown-item>
              <el-dropdown-item v-if="userStore.userInfo.club_id" command="leaveClub">
                <el-icon :size="14"><Switch /></el-icon>
                <span>退出社团</span>
              </el-dropdown-item>
              <el-dropdown-item command="logout" divided>
                <el-icon :size="14"><SwitchButton /></el-icon>
                <span>退出账号</span>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <el-container class="body-container">
      <!-- ── Glass Sidebar ── -->
      <el-aside :width="sidebarCollapsed ? '64px' : '220px'" class="aside glass-sidebar" :class="{ collapsed: sidebarCollapsed }">
        <el-menu
          :default-active="route.path"
          router
          class="menu"
          :collapse="sidebarCollapsed"
        >
          <el-menu-item index="/dashboard">
            <el-icon :size="18"><DataAnalysis /></el-icon>
            <template #title>首页概览</template>
          </el-menu-item>
          <el-menu-item index="/clubs">
            <el-icon :size="18"><HomeFilled /></el-icon>
            <template #title>社团管理</template>
          </el-menu-item>
          <el-menu-item index="/activities">
            <el-icon :size="18"><Calendar /></el-icon>
            <template #title>活动管理</template>
          </el-menu-item>
          <el-menu-item index="/notifications">
            <el-icon :size="18"><Bell /></el-icon>
            <template #title>通知中心</template>
          </el-menu-item>
          <el-menu-item index="/ai-recommend">
            <el-icon :size="18"><Cpu /></el-icon>
            <template #title>AI智能推荐</template>
          </el-menu-item>
          <el-menu-item index="/checkin">
            <el-icon :size="18"><Camera /></el-icon>
            <template #title>签到考勤</template>
          </el-menu-item>
          <el-menu-item v-if="userStore.role === 'admin'" index="/admin-approval">
            <el-icon :size="18"><Document /></el-icon>
            <template #title>审批管理</template>
          </el-menu-item>
        </el-menu>

        <!-- Sidebar Footer -->
        <div class="sidebar-footer">
          <el-button class="collapse-btn" @click="sidebarCollapsed = !sidebarCollapsed">
            <el-icon :size="16">
              <DArrowLeft v-if="!sidebarCollapsed" />
              <DArrowRight v-else />
            </el-icon>
          </el-button>
        </div>
      </el-aside>

      <!-- ── Main Content ── -->
      <el-main class="main">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>

    <!-- AI Assistant -->
    <AIAssistant />

    <!-- Reset Password Dialog -->
    <el-dialog v-model="passwordVisible" title="重置密码" width="400px" class="modern-dialog">
      <el-form :model="passwordForm" label-position="top">
        <el-form-item label="旧密码">
          <el-input v-model="passwordForm.old_password" type="password" show-password size="large" />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="passwordForm.new_password" type="password" show-password size="large" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordVisible = false">取消</el-button>
        <el-button type="primary" :loading="resettingPassword" @click="handleResetPassword">确认重置</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, computed, reactive, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '../stores/user'
import { useThemeStore } from '../stores/theme'
import { getUnreadCount, resetPassword, leaveClub, getPendingCount } from '../api'
import AIAssistant from '../components/AIAssistant.vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const themeStore = useThemeStore()

const unreadCount = ref(0)
const pendingCount = ref(0)
const passwordVisible = ref(false)
const resettingPassword = ref(false)
const sidebarCollapsed = ref(false)
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
/* ── Layout Container ── */
.layout {
  height: 100vh;
  overflow: hidden;
}

/* ── Header ── */
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  padding: 0 24px;
  position: relative;
  z-index: var(--z-header);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  color: var(--text-primary);
  text-decoration: none;
  transition: opacity var(--transition-fast);
}
.logo:hover { opacity: 0.8; }

.logo-text {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.theme-toggle {
  border: none !important;
  background: transparent !important;
  color: var(--text-secondary) !important;
  transition: color var(--transition-fast), transform var(--transition-fast);
}
.theme-toggle:hover {
  color: var(--color-primary-500) !important;
  transform: rotate(15deg);
}

.header-btn {
  border: 1px solid var(--border-light) !important;
  background: var(--bg-card) !important;
  color: var(--text-secondary) !important;
  transition: all var(--transition-fast);
}
.header-btn:hover {
  border-color: var(--border-accent) !important;
  color: var(--color-primary-500) !important;
  box-shadow: var(--shadow-sm);
}

.user-name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  margin: 0 4px;
}

.settings-btn {
  border: 1px solid var(--border-light) !important;
  background: var(--bg-card) !important;
  color: var(--text-secondary) !important;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all var(--transition-fast);
}
.settings-btn:hover {
  border-color: var(--border-accent) !important;
  color: var(--color-primary-500) !important;
}
.arrow-icon { transition: transform var(--transition-fast); }
.settings-btn:hover .arrow-icon { transform: rotate(180deg); }

/* ── Body Container ── */
.body-container {
  flex: 1;
  overflow: hidden;
}

/* ── Sidebar ── */
.aside {
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  transition: width var(--transition-base);
  overflow: hidden;
}

.menu {
  flex: 1;
  border-right: none !important;
  background: transparent !important;
  padding: 8px;
  padding-top: 12px;
}

/* Menu items */
.menu :deep(.el-menu-item) {
  border-radius: var(--radius-md);
  margin-bottom: 4px;
  height: 44px;
  line-height: 44px;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
  position: relative;
  overflow: hidden;
}
.menu :deep(.el-menu-item):hover {
  background: var(--color-primary-50) !important;
  color: var(--color-primary-600) !important;
}
.menu :deep(.el-menu-item).is-active {
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.12), rgba(167, 139, 250, 0.06)) !important;
  color: var(--color-primary-600) !important;
  font-weight: var(--font-semibold);
}
.menu :deep(.el-menu-item).is-active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  background: var(--gradient-primary);
  border-radius: 0 var(--radius-full) var(--radius-full) 0;
}

/* Icon in menu */
.menu :deep(.el-menu-item .el-icon) {
  color: inherit;
}

/* Dark sidebar menu */
[data-theme="dark"] .menu :deep(.el-menu-item):hover {
  background: rgba(124, 58, 237, 0.15) !important;
  color: var(--color-primary-300) !important;
}
[data-theme="dark"] .menu :deep(.el-menu-item).is-active {
  background: rgba(124, 58, 237, 0.2) !important;
  color: var(--color-primary-300) !important;
}

/* Collapsed sidebar */
.aside.collapsed .menu :deep(.el-menu-item) {
  justify-content: center;
  padding: 0 !important;
}
.aside.collapsed .menu :deep(.el-menu-item) .el-icon {
  margin: 0 !important;
}

/* Sidebar Footer */
.sidebar-footer {
  padding: 12px;
  border-top: 1px solid var(--border-light);
  display: flex;
  justify-content: center;
}
.collapse-btn {
  border: none !important;
  background: transparent !important;
  color: var(--text-muted) !important;
  font-size: 16px;
  padding: 6px;
  transition: color var(--transition-fast);
}
.collapse-btn:hover {
  color: var(--color-primary-500) !important;
}

/* ── Main Content ── */
.main {
  padding: 28px;
  background: transparent;
  overflow-y: auto;
  height: 100%;
}

/* ── Modern Dialog ── */
.modern-dialog :deep(.el-dialog) {
  border-radius: var(--radius-xl);
}
.modern-dialog :deep(.el-dialog__header) {
  padding: 24px 24px 0;
}
.modern-dialog :deep(.el-dialog__body) {
  padding: 20px 24px;
}
.modern-dialog :deep(.el-dialog__footer) {
  padding: 0 24px 24px;
}

/* ── Dropdown Icons ── */
:deep(.el-dropdown-menu__item .el-icon) {
  margin-right: 8px;
}
</style>
