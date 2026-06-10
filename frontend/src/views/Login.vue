<template>
  <div class="login-page">
    <div class="login-card">
      <h1 class="title">社团管理与活动报名系统</h1>
      <p class="subtitle">人工智能综合能力实训项目</p>
      <el-tabs v-model="tab" class="tabs">
        <el-tab-pane label="登录" name="login">
          <el-form :model="loginForm" :rules="rules" ref="loginRef">
            <el-form-item prop="username">
              <el-input v-model="loginForm.username" placeholder="用户名" size="large" />
            </el-form-item>
            <el-form-item prop="password">
              <el-input v-model="loginForm.password" type="password" placeholder="密码" size="large" show-password />
            </el-form-item>
            <el-button type="primary" size="large" :loading="loading" @click="handleLogin" class="btn">登 录</el-button>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="注册" name="register">
          <el-form :model="regForm" :rules="regRules" ref="regRef">
            <el-form-item prop="username" :error="usernameError">
              <el-input v-model="regForm.username" placeholder="用户名" size="large" @input="usernameError = ''" />
            </el-form-item>
            <el-form-item prop="password">
              <el-input v-model="regForm.password" type="password" placeholder="密码" size="large" show-password />
            </el-form-item>
            <el-form-item prop="real_name">
              <el-input v-model="regForm.real_name" placeholder="真实姓名" size="large" />
            </el-form-item>
            <el-form-item prop="role">
              <el-select v-model="regForm.role" placeholder="选择角色" size="large" style="width:100%" disabled>
                <el-option label="普通成员" value="member" />
              </el-select>
            </el-form-item>
            <el-form-item prop="student_id">
              <el-input v-model="regForm.student_id" placeholder="学号（选填）" size="large" />
            </el-form-item>
            <el-form-item prop="phone">
              <el-input v-model="regForm.phone" placeholder="手机号（选填）" size="large" />
            </el-form-item>
            <el-button type="success" size="large" :loading="loading" @click="handleRegister" class="btn">注 册</el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login, register } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()
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
  ...rules,
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
.login-page {
  display: flex; justify-content: center; align-items: center;
  min-height: 100vh; background: linear-gradient(135deg, #1e3c72, #2a5298);
}
.login-card {
  width: 420px; padding: 40px; background: #fff; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,.2);
}
.title { text-align: center; color: #1e3c72; margin-bottom: 4px; font-size: 24px; }
.subtitle { text-align: center; color: #888; margin-bottom: 24px; }
.btn { width: 100%; margin-top: 8px; }
</style>
