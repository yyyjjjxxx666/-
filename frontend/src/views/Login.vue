<template>
  <div class="login-page">
    <!-- Animated Background Blobs -->
    <div class="bg-blobs">
      <div class="blob blob-1" />
      <div class="blob blob-2" />
      <div class="blob blob-3" />
    </div>

    <!-- Theme Toggle (top-right) -->
    <button class="theme-float-btn" @click="themeStore.toggle()" :title="themeStore.isDark ? '切换浅色模式' : '切换深色模式'">
      <el-icon :size="18"><Sunny v-if="!themeStore.isDark" /></el-icon>
      <span v-if="themeStore.isDark" style="font-size:18px">🌙</span>
    </button>

    <!-- Glass Card -->
    <div class="login-card glass-modal">
      <!-- Logo Area -->
      <div class="card-header">
        <div class="logo-icon">
          <el-icon :size="36"><School /></el-icon>
        </div>
        <h1 class="title gradient-text">社团管理与活动报名系统</h1>
        <p class="subtitle">人工智能综合能力实训项目</p>
      </div>

      <!-- Tabs -->
      <el-tabs v-model="tab" class="tabs" :stretch="true">
        <el-tab-pane name="login">
          <template #label>
            <span class="tab-label">
              <el-icon :size="16"><User /></el-icon>
              登录
            </span>
          </template>
          <el-form :model="loginForm" :rules="rules" ref="loginRef" @keyup.enter="handleLogin">
            <el-form-item prop="username">
              <el-input v-model="loginForm.username" placeholder="用户名" size="large" :prefix-icon="User" clearable />
            </el-form-item>
            <el-form-item prop="password">
              <el-input v-model="loginForm.password" type="password" placeholder="密码" size="large" show-password :prefix-icon="Lock" />
            </el-form-item>
            <el-button type="primary" size="large" :loading="loading" @click="handleLogin" class="submit-btn">
              <span v-if="!loading">登 录</span>
            </el-button>
          </el-form>
        </el-tab-pane>

        <el-tab-pane name="register">
          <template #label>
            <span class="tab-label">
              <el-icon :size="16"><EditPen /></el-icon>
              注册
            </span>
          </template>
          <el-form :model="regForm" :rules="regRules" ref="regRef" @keyup.enter="handleRegister">
            <el-form-item prop="username" :error="usernameError">
              <el-input v-model="regForm.username" placeholder="用户名" size="large" :prefix-icon="User" clearable @input="usernameError = ''" />
            </el-form-item>
            <el-form-item prop="password">
              <el-input v-model="regForm.password" type="password" placeholder="密码" size="large" show-password :prefix-icon="Lock" />
            </el-form-item>
            <el-form-item prop="real_name">
              <el-input v-model="regForm.real_name" placeholder="真实姓名" size="large" :prefix-icon="Postcard" />
            </el-form-item>
            <el-form-item prop="role">
              <el-select v-model="regForm.role" placeholder="选择角色" size="large" style="width:100%" disabled>
                <el-option label="普通成员" value="member" />
              </el-select>
            </el-form-item>
            <el-form-item prop="student_id">
              <el-input v-model="regForm.student_id" placeholder="学号（选填）" size="large" :prefix-icon="Stamp" />
            </el-form-item>
            <el-form-item prop="phone">
              <el-input v-model="regForm.phone" placeholder="手机号（选填）" size="large" :prefix-icon="Iphone" />
            </el-form-item>
            <el-button type="primary" size="large" :loading="loading" @click="handleRegister" class="submit-btn register-btn">
              <span v-if="!loading">注 册</span>
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- Footer Text -->
    <p class="footer-text">© 2025 社团管理系统 · AI-Powered</p>
  </div>
</template>

<script setup>
import { ref, reactive, markRaw } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, EditPen, Postcard, Stamp, Iphone } from '@element-plus/icons-vue'
import { login, register } from '../api'
import { useUserStore } from '../stores/user'
import { useThemeStore } from '../stores/theme'

const router = useRouter()
const userStore = useUserStore()
const themeStore = useThemeStore()
const tab = ref('login')
const loading = ref(false)
const usernameError = ref('')

const loginForm = reactive({ username: '', password: '' })
const regForm = reactive({ username: '', password: '', real_name: '', role: 'member', student_id: '', phone: '' })

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur', min: 6 }],
}
const regRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur', min: 6 }],
  real_name: [{ required: true, message: '请输入真实姓名', trigger: 'blur' }],
}

const handleLogin = async () => {
  loading.value = true
  try {
    const { data } = await login(loginForm)
    userStore.setAuth(data.access_token, { id: data.user_id, role: data.role, real_name: data.real_name, club_id: data.club_id })
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch {} finally { loading.value = false }
}

const handleRegister = async () => {
  usernameError.value = ''
  loading.value = true
  try {
    await register(regForm)
    ElMessage.success('注册成功，请登录')
    tab.value = 'login'
    regForm.username = ''; regForm.password = ''; regForm.real_name = ''; regForm.student_id = ''; regForm.phone = ''
  } catch (err) {
    const detail = err.response?.data?.detail || ''
    if (detail.includes('用户名')) usernameError.value = detail
  } finally { loading.value = false }
}
</script>

<style scoped>
/* ── Page Layout ── */
.login-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  position: relative;
  overflow: hidden;
  background: var(--gradient-page);
}

/* ── Animated Background Blobs ── */
.bg-blobs {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}
.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.4;
  animation: float 8s ease-in-out infinite;
}
.blob-1 {
  width: 500px; height: 500px;
  background: rgba(124, 58, 237, 0.15);
  top: -15%; left: -10%;
  animation-delay: 0s;
}
.blob-2 {
  width: 400px; height: 400px;
  background: rgba(249, 115, 22, 0.1);
  bottom: -10%; right: -8%;
  animation-delay: -3s;
  animation-duration: 10s;
}
.blob-3 {
  width: 350px; height: 350px;
  background: rgba(14, 165, 233, 0.1);
  top: 50%; left: 50%;
  animation-delay: -6s;
  animation-duration: 7s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -30px) scale(1.05); }
  66% { transform: translate(-20px, 20px) scale(0.95); }
}

/* ── Theme Float Button ── */
.theme-float-btn {
  position: absolute;
  top: 24px;
  right: 24px;
  width: 44px;
  height: 44px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-light);
  background: var(--bg-card);
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
  z-index: 10;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}
.theme-float-btn:hover {
  border-color: var(--border-accent);
  color: var(--color-primary-500);
  box-shadow: var(--shadow-md);
  transform: scale(1.08);
}

/* ── Login Card ── */
.login-card {
  width: 440px;
  padding: 40px 36px 32px;
  position: relative;
  z-index: 1;
  animation: dialog-enter 0.5s ease-out;
}

@keyframes dialog-enter {
  from { opacity: 0; transform: scale(0.94) translateY(16px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

/* ── Card Header ── */
.card-header {
  text-align: center;
  margin-bottom: 20px;
}
.logo-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: var(--radius-lg);
  background: var(--gradient-primary);
  color: #fff;
  margin-bottom: 16px;
  box-shadow: 0 4px 20px rgba(124, 58, 237, 0.3);
}
.title {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  margin-bottom: 6px;
}
.subtitle {
  color: var(--text-muted);
  font-size: var(--text-sm);
}

/* ── Tabs ── */
.tabs {
  margin-top: 8px;
}
.tab-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

/* Tab active underline animation */
.tabs :deep(.el-tabs__active-bar) {
  background: var(--gradient-primary) !important;
  height: 3px !important;
  border-radius: var(--radius-full);
}
.tabs :deep(.el-tabs__item) {
  font-size: var(--text-sm);
  color: var(--text-muted);
  transition: color var(--transition-fast);
}
.tabs :deep(.el-tabs__item):hover {
  color: var(--color-primary-500);
}
.tabs :deep(.el-tabs__item.is-active) {
  color: var(--color-primary-600);
  font-weight: var(--font-semibold);
}
.tabs :deep(.el-tabs__nav-wrap::after) {
  background: var(--border-light);
}

/* ── Form Items ── */
.submit-btn {
  width: 100%;
  margin-top: 12px;
  height: 44px;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  letter-spacing: 0.1em;
  border-radius: var(--radius-md) !important;
  background: var(--gradient-primary) !important;
  border: none !important;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast), opacity var(--transition-fast);
}
.submit-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 24px rgba(124, 58, 237, 0.35);
}
.submit-btn:active {
  transform: translateY(0);
}
.register-btn {
  background: linear-gradient(135deg, #10B981, #34D399) !important;
}
.register-btn:hover {
  box-shadow: 0 6px 24px rgba(16, 185, 129, 0.35);
}

/* ── Footer ── */
.footer-text {
  position: absolute;
  bottom: 24px;
  color: var(--text-muted);
  font-size: var(--text-xs);
  z-index: 1;
}

/* ── Responsive ── */
@media (max-width: 480px) {
  .login-card {
    width: 92vw;
    padding: 28px 20px 24px;
    margin: 16px;
  }
  .title { font-size: var(--text-xl); }
}
</style>
