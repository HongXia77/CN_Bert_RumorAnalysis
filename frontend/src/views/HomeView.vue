<template>
  <div class="auth-page">
    <section class="hero-panel">
      <div class="hero-copy">
        <span class="hero-badge">CN Rumor Control Center</span>
        <h1>把谣言识别、权限管理和核查工作流收进一个控制台。</h1>
        <p>
          面向普通用户提供快速识别与可信入口，面向管理员提供成员管理、系统统计与审核视角。
        </p>

        <div class="hero-grid">
          <article class="hero-card surface-card">
            <span class="hero-icon hero-icon-blue">
              <el-icon><Monitor /></el-icon>
            </span>
            <div>
              <h3>统一前后端联动</h3>
              <p>登录、注册、资料、角色权限与文本识别都走真实接口。</p>
            </div>
          </article>

          <article class="hero-card surface-card">
            <span class="hero-icon hero-icon-warm">
              <el-icon><DataBoard /></el-icon>
            </span>
            <div>
              <h3>管理员专属视角</h3>
              <p>支持账号状态管理、角色切换与数据总览，补齐后台逻辑。</p>
            </div>
          </article>

          <article class="hero-card surface-card">
            <span class="hero-icon hero-icon-ice">
              <el-icon><StarFilled /></el-icon>
            </span>
            <div>
              <h3>面向核查的 UI</h3>
              <p>重构为控制中心式布局，强调信息密度、视觉层级与操作反馈。</p>
            </div>
          </article>
        </div>
      </div>

      <div class="hero-orbit">
        <div class="orbit-ring ring-a"></div>
        <div class="orbit-ring ring-b"></div>
        <div class="orbit-dot orbit-dot-a"></div>
        <div class="orbit-dot orbit-dot-b"></div>
        <div class="hero-core">
          <span>Rumor</span>
          <strong>Signal</strong>
        </div>
      </div>
    </section>

    <section class="auth-panel panel-shell">
      <div class="auth-head">
        <div>
          <span class="auth-overline">System Access</span>
          <h2>{{ activeCard === 'register' ? '创建工作席位' : '进入系统' }}</h2>
          <p>{{ activeCard === 'register' ? '注册卡片当前位于上层，可点击底部登录卡片切换。' : '登录卡片当前位于上层，可再次点击底部注册卡片返回。' }}</p>
        </div>
        <el-tag effect="dark" type="primary" round>{{ activeCard === 'register' ? 'Register First' : 'Login First' }}</el-tag>
      </div>

      <el-alert
        v-if="bootstrapState && !bootstrapState.admin_exists"
        title="系统尚未初始化，第一个注册账号会自动获得管理员权限。"
        type="warning"
        show-icon
        :closable="false"
        class="bootstrap-alert"
      />

      <div class="auth-stack" :class="`is-${activeCard}`">
        <article
          class="auth-card login-card"
          :class="{ active: activeCard === 'login', idle: activeCard !== 'login' }"
          @click="promoteCard('login')"
        >
          <div v-if="activeCard !== 'login'" class="card-peek">
            <span class="peek-chip">Login</span>
            <h3>已有账号</h3>
            <p>点击这张下层卡片，切换到登录视图并直接进入控制台。</p>
          </div>

          <template v-else>
            <div class="card-shell">
              <div class="card-header">
                <span class="card-chip">登录卡片</span>
                <button class="peek-action" type="button" @click.stop="promoteCard('register')">切到注册</button>
              </div>

          <el-form label-position="top" class="auth-form" @submit.prevent>
            <el-form-item label="账号">
              <el-input
                v-model="loginForm.username"
                placeholder="用户名 / 邮箱 / 手机号"
                size="large"
                clearable
              >
                <template #prefix>
                  <el-icon><UserFilled /></el-icon>
                </template>
              </el-input>
            </el-form-item>

            <el-form-item label="密码">
              <el-input
                v-model="loginForm.password"
                placeholder="请输入密码"
                size="large"
                show-password
                type="password"
                clearable
                @keyup.enter="handleLogin"
              >
                <template #prefix>
                  <el-icon><Lock /></el-icon>
                </template>
              </el-input>
            </el-form-item>

            <div class="sub-actions">
              <el-checkbox v-model="loginForm.remember">记住账号</el-checkbox>
              <span class="auth-hint">首次管理员注册会自动初始化后台角色。</span>
            </div>

            <el-button
              class="primary-btn"
              type="primary"
              size="large"
              :loading="loginLoading"
              @click="handleLogin"
            >
              {{ loginLoading ? '正在登录...' : '登录并进入控制台' }}
            </el-button>
          </el-form>
            </div>
          </template>
        </article>

        <article
          class="auth-card register-card"
          :class="{ active: activeCard === 'register', idle: activeCard !== 'register' }"
          @click="promoteCard('register')"
        >
          <div v-if="activeCard !== 'register'" class="card-peek">
            <span class="peek-chip">Register</span>
            <h3>创建账号</h3>
            <p>点击这张下层卡片，返回注册视图并继续完善资料。</p>
          </div>

          <template v-else>
            <div class="card-shell">
              <div class="card-header">
                <span class="card-chip">注册卡片</span>
                <button class="peek-action" type="button" @click.stop="promoteCard('login')">切到登录</button>
              </div>

          <el-form label-position="top" class="auth-form register-form" @submit.prevent>
            <div class="avatar-block surface-card">
              <el-upload
                class="avatar-uploader"
                :show-file-list="false"
                :http-request="uploadAvatar"
                accept="image/png,image/jpeg"
              >
                <img v-if="registerForm.avatar" :src="registerAvatarPreviewUrl" class="avatar-preview" alt="avatar" />
                <div v-else class="avatar-placeholder">
                  <el-icon><Plus /></el-icon>
                  <span>上传头像</span>
                </div>
              </el-upload>
              <p>支持 JPG / PNG，建议正方形头像。</p>
            </div>

            <div class="form-grid">
              <el-form-item label="用户名">
                <el-input v-model="registerForm.username" placeholder="请输入用户名" clearable>
                  <template #prefix>
                    <el-icon><UserFilled /></el-icon>
                  </template>
                </el-input>
              </el-form-item>

              <el-form-item label="密码">
                <el-input v-model="registerForm.password" type="password" show-password placeholder="至少 8 位">
                  <template #prefix>
                    <el-icon><Lock /></el-icon>
                  </template>
                </el-input>
              </el-form-item>

              <el-form-item label="邮箱">
                <el-input v-model="registerForm.email" placeholder="you@example.com" clearable>
                  <template #prefix>
                    <el-icon><Message /></el-icon>
                  </template>
                </el-input>
              </el-form-item>

              <el-form-item label="手机号">
                <el-input v-model="registerForm.phone" placeholder="请输入手机号" clearable>
                  <template #prefix>
                    <el-icon><Phone /></el-icon>
                  </template>
                </el-input>
              </el-form-item>

              <el-form-item label="性别">
                <el-select v-model="registerForm.gender" placeholder="请选择性别">
                  <el-option label="男" value="男" />
                  <el-option label="女" value="女" />
                  <el-option label="未知" value="未知" />
                </el-select>
              </el-form-item>

              <el-form-item label="生日">
                <el-date-picker
                  v-model="registerForm.birthday"
                  type="date"
                  value-format="x"
                  placeholder="选择日期"
                  :disabled-date="disabledFutureDates"
                />
              </el-form-item>

              <el-form-item label="省份">
                <el-select v-model="registerForm.province" placeholder="请选择省份" filterable>
                  <el-option
                    v-for="item in provinceOptions"
                    :key="item"
                    :label="item"
                    :value="item"
                  />
                </el-select>
              </el-form-item>

              <el-form-item :label="registerSubregionLabel">
                <el-select
                  v-model="registerForm.city"
                  :placeholder="registerSubregionPlaceholder"
                  filterable
                  :disabled="registerCityOptions.length === 0"
                >
                  <el-option
                    v-for="item in registerCityOptions"
                    :key="item"
                    :label="item"
                    :value="item"
                  />
                </el-select>
              </el-form-item>
            </div>

            <el-button
              class="primary-btn"
              type="primary"
              size="large"
              :loading="registerLoading"
              @click="handleRegister"
            >
              {{ registerLoading ? '正在创建账号...' : '注册并开始使用' }}
            </el-button>
          </el-form>
            </div>
          </template>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  DataBoard,
  Lock,
  Location,
  Message,
  Monitor,
  Phone,
  Plus,
  StarFilled,
  UserFilled,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import api, { resolveAssetUrl } from '@/api/client'
import {
  getCitiesByProvince,
  getSubregionLabel,
  normalizeLocationSelection,
  provinceOptions,
} from '@/constants/regions'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const activeCard = ref('register')
const loginLoading = ref(false)
const registerLoading = ref(false)
const bootstrapState = ref(null)

const loginForm = reactive({
  username: '',
  password: '',
  remember: false,
})

const registerForm = reactive({
  username: '',
  password: '',
  email: '',
  phone: '',
  avatar: '',
  gender: '未知',
  province: '',
  city: '',
  birthday: '',
})

const registerAvatarPreviewUrl = computed(() => resolveAssetUrl(registerForm.avatar))
const registerCityOptions = computed(() => getCitiesByProvince(registerForm.province))
const registerSubregionLabel = computed(() => getSubregionLabel(registerForm.province))
const registerSubregionPlaceholder = computed(() => `请选择${registerSubregionLabel.value}`)

const promoteCard = (target) => {
  if (activeCard.value === target) {
    return
  }
  activeCard.value = target
}

watch(
  () => registerForm.province,
  (nextProvince, previousProvince) => {
    if (nextProvince === previousProvince) {
      return
    }

    const normalizedLocation = normalizeLocationSelection(nextProvince, registerForm.city)
    if (registerForm.province !== normalizedLocation.province) {
      registerForm.province = normalizedLocation.province
    }
    if (registerForm.city !== normalizedLocation.city) {
      registerForm.city = normalizedLocation.city
    }
  },
)

const redirectByRole = (role) => {
  router.push(role === 'admin' ? '/admin' : '/main')
}

const disabledFutureDates = (time) => time.getTime() > Date.now()

const loadBootstrapState = async () => {
  try {
    const response = await api.get('/bootstrap-status')
    bootstrapState.value = response.data.data
  } catch {
    bootstrapState.value = null
  }
}

const validateLogin = () => {
  if (!loginForm.username.trim()) {
    ElMessage.warning('请输入登录账号')
    return false
  }
  if (!loginForm.password) {
    ElMessage.warning('请输入登录密码')
    return false
  }
  return true
}

const validateRegister = () => {
  const normalizedLocation = normalizeLocationSelection(registerForm.province, registerForm.city)

  if (!registerForm.username.trim()) {
    ElMessage.warning('请输入用户名')
    return false
  }
  if (registerForm.password.length < 8) {
    ElMessage.warning('注册密码至少需要 8 位')
    return false
  }
  if (!/^\S+@\S+\.\S+$/.test(registerForm.email)) {
    ElMessage.warning('请输入有效邮箱')
    return false
  }
  if (!/^1[3-9]\d{9}$/.test(registerForm.phone)) {
    ElMessage.warning('请输入有效手机号')
    return false
  }
  if (!normalizedLocation.province || !normalizedLocation.city) {
    ElMessage.warning(`请补充省份和${registerSubregionLabel.value}信息`)
    return false
  }
  if (!registerForm.birthday) {
    ElMessage.warning('请选择生日')
    return false
  }
  return true
}

const handleLogin = async () => {
  if (!validateLogin()) return

  loginLoading.value = true
  try {
    const response = await api.post('/login', {
      username: loginForm.username,
      password: loginForm.password,
    })

    userStore.setSession(response.data)

    if (loginForm.remember) {
      localStorage.setItem('remember_user_account', loginForm.username)
    } else {
      localStorage.removeItem('remember_user_account')
    }

    ElMessage.success(response.data.message || '登录成功')
    redirectByRole(response.data.data.role)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '登录失败，请检查后端服务')
  } finally {
    loginLoading.value = false
  }
}

const handleRegister = async () => {
  if (!validateRegister()) return

  registerLoading.value = true
  try {
    const normalizedLocation = normalizeLocationSelection(registerForm.province, registerForm.city)
    registerForm.province = normalizedLocation.province
    registerForm.city = normalizedLocation.city

    const formData = new FormData()
    Object.entries(registerForm).forEach(([key, value]) => {
      if (key === 'birthday') {
        formData.append('birthday_ts', value)
      } else {
        formData.append(key, value)
      }
    })

    const response = await api.post('/register', formData)
    userStore.setSession(response.data)
    ElMessage.success(response.data.message || '注册成功')
    redirectByRole(response.data.data.role)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '注册失败，请检查表单内容')
  } finally {
    registerLoading.value = false
  }
}

const uploadAvatar = async ({ file, onSuccess, onError }) => {
  const isValidFormat = ['image/jpeg', 'image/png'].includes(file.type)
  const isLt2M = file.size / 1024 / 1024 < 2

  if (!isValidFormat) {
    ElMessage.error('仅支持 JPG / PNG 格式')
    onError?.(new Error('invalid-format'))
    return
  }

  if (!isLt2M) {
    ElMessage.error('头像大小不能超过 2MB')
    onError?.(new Error('file-too-large'))
    return
  }

  try {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post('/upload-avatar', formData)
    registerForm.avatar = response.data.url
    ElMessage.success('头像上传成功')
    onSuccess?.(response.data)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '头像上传失败')
    onError?.(error)
  }
}

onMounted(() => {
  userStore.bootstrap()

  const rememberedAccount = localStorage.getItem('remember_user_account')
  if (rememberedAccount) {
    loginForm.username = rememberedAccount
    loginForm.remember = true
  }

  loadBootstrapState()
})
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1.2fr minmax(420px, 520px);
  gap: 28px;
  padding: 24px;
}

.hero-panel {
  position: relative;
  overflow: hidden;
  padding: 48px;
  border-radius: 36px;
  min-height: calc(100vh - 48px);
  background:
    radial-gradient(circle at top left, rgba(255, 255, 255, 0.08), transparent 28%),
    linear-gradient(135deg, #091527 0%, #10243f 52%, #153b66 100%);
  color: rgba(255, 255, 255, 0.92);
  box-shadow: 0 28px 80px rgba(5, 15, 29, 0.36);
}

.hero-copy {
  position: relative;
  z-index: 1;
  max-width: 720px;
}

.hero-badge,
.auth-overline {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.84);
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.hero-copy h1 {
  margin: 20px 0 16px;
  font-size: clamp(38px, 5vw, 64px);
  line-height: 1.04;
  letter-spacing: -0.04em;
  color: #fff;
}

.hero-copy > p {
  max-width: 620px;
  font-size: 17px;
  line-height: 1.8;
  color: rgba(230, 240, 255, 0.76);
}

.hero-grid {
  margin-top: 34px;
  display: grid;
  gap: 18px;
}

.hero-card {
  display: grid;
  grid-template-columns: 58px 1fr;
  gap: 16px;
  padding: 18px 20px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.86);
}

.hero-card h3 {
  margin: 0 0 6px;
  font-size: 17px;
  color: #fff;
}

.hero-card p {
  margin: 0;
  line-height: 1.7;
  color: rgba(224, 233, 248, 0.74);
}

.hero-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 58px;
  height: 58px;
  border-radius: 18px;
  font-size: 24px;
  color: #fff;
}

.hero-icon-blue {
  background: linear-gradient(135deg, #0f7bff, #0ea5e9);
}

.hero-icon-warm {
  background: linear-gradient(135deg, #ff8a3d, #f97316);
}

.hero-icon-ice {
  background: linear-gradient(135deg, #22c55e, #10b981);
}

.hero-orbit {
  position: absolute;
  right: -80px;
  bottom: -120px;
  width: 420px;
  height: 420px;
}

.orbit-ring {
  position: absolute;
  inset: 0;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 50%;
}

.ring-b {
  inset: 48px;
}

.orbit-dot {
  position: absolute;
  border-radius: 50%;
  box-shadow: 0 0 30px rgba(15, 123, 255, 0.8);
}

.orbit-dot-a {
  width: 14px;
  height: 14px;
  top: 42px;
  right: 96px;
  background: #0ea5e9;
}

.orbit-dot-b {
  width: 18px;
  height: 18px;
  left: 38px;
  bottom: 112px;
  background: #ff8a3d;
}

.hero-core {
  position: absolute;
  inset: 108px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(15, 123, 255, 0.22), rgba(9, 21, 39, 0.86));
  box-shadow: inset 0 0 60px rgba(255, 255, 255, 0.06);
}

.hero-core span {
  font-size: 14px;
  letter-spacing: 0.28em;
  text-transform: uppercase;
  color: rgba(215, 228, 246, 0.72);
}

.hero-core strong {
  margin-top: 10px;
  font-size: 38px;
  letter-spacing: -0.04em;
  color: #fff;
}

.auth-panel {
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 22px;
  padding: 30px;
  border-radius: 32px;
  min-height: calc(100vh - 48px);
  overflow: hidden;
}

.auth-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.auth-head h2 {
  margin: 12px 0 8px;
  font-size: 36px;
  color: var(--ink-strong);
}

.auth-head p {
  margin: 0;
  color: var(--ink-soft);
  line-height: 1.7;
}

.bootstrap-alert {
  border-radius: 18px;
}

.auth-stack {
  position: relative;
  min-height: 890px;
  padding: 0 32px 86px 0;
}

.auth-card {
  position: absolute;
  border-radius: 30px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  transition:
    transform 0.32s ease,
    box-shadow 0.32s ease,
    inset 0.32s ease,
    background 0.32s ease;
}

.auth-card.active {
  inset: 0 32px 86px 0;
  z-index: 2;
  box-shadow: 0 26px 52px rgba(15, 23, 42, 0.12);
}

.auth-card.idle {
  inset: 62px 0 0 28px;
  z-index: 1;
  cursor: pointer;
  box-shadow: 0 18px 34px rgba(15, 23, 42, 0.08);
}

.auth-card.idle:hover {
  transform: translate(-4px, -4px);
}

.login-card.active {
  background:
    radial-gradient(circle at top right, rgba(15, 123, 255, 0.14), transparent 28%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(247, 250, 255, 0.96));
}

.register-card.active {
  background:
    radial-gradient(circle at top right, rgba(255, 138, 61, 0.14), transparent 28%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 250, 246, 0.96));
}

.login-card.idle {
  background:
    linear-gradient(180deg, rgba(245, 249, 255, 0.94), rgba(232, 243, 255, 0.9));
}

.register-card.idle {
  background:
    linear-gradient(180deg, rgba(255, 248, 242, 0.96), rgba(255, 238, 226, 0.9));
}

.card-shell {
  height: 100%;
  overflow-y: auto;
  padding: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 8px;
}

.card-chip,
.peek-chip {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.card-chip {
  background: rgba(15, 123, 255, 0.08);
  color: var(--brand-deep);
}

.peek-chip {
  background: rgba(255, 255, 255, 0.7);
  color: var(--ink-soft);
}

.peek-action {
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(255, 255, 255, 0.88);
  color: var(--ink-main);
  padding: 10px 14px;
  border-radius: 14px;
  cursor: pointer;
  transition: 0.2s ease;
}

.peek-action:hover {
  border-color: rgba(15, 123, 255, 0.24);
  color: var(--brand-deep);
}

.card-peek {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 22px 24px 26px;
}

.card-peek h3 {
  margin: 14px 0 8px;
  font-size: 26px;
  line-height: 1.1;
  color: var(--ink-strong);
}

.card-peek p {
  margin: 0;
  max-width: 280px;
  color: var(--ink-soft);
  line-height: 1.7;
}

.auth-form {
  display: grid;
  gap: 8px;
  padding-top: 8px;
}

.sub-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  color: var(--ink-soft);
  font-size: 13px;
  margin-bottom: 12px;
}

.auth-hint {
  text-align: right;
}

.primary-btn {
  width: 100%;
  height: 52px;
  border-radius: 16px;
  font-weight: 600;
  letter-spacing: 0.02em;
  box-shadow: 0 18px 30px rgba(15, 123, 255, 0.24);
}

.register-form {
  gap: 16px;
}

.avatar-block {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 18px;
  border-radius: 24px;
}

.avatar-block p {
  margin: 0;
  color: var(--ink-soft);
  line-height: 1.7;
}

.avatar-uploader :deep(.el-upload) {
  border-radius: 22px;
}

.avatar-preview,
.avatar-placeholder {
  width: 92px;
  height: 92px;
  border-radius: 22px;
}

.avatar-preview {
  object-fit: cover;
  border: 1px solid var(--line-soft);
}

.avatar-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: linear-gradient(145deg, rgba(15, 123, 255, 0.08), rgba(255, 138, 61, 0.1));
  color: var(--brand-deep);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

.auth-form :deep(.el-input__wrapper),
.auth-form :deep(.el-select__wrapper),
.auth-form :deep(.el-textarea__inner) {
  border-radius: 16px;
  box-shadow: none;
  min-height: 46px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(255, 255, 255, 0.92);
}

.auth-form :deep(.el-date-editor.el-input),
.auth-form :deep(.el-date-editor.el-input__wrapper),
.auth-form :deep(.el-select) {
  width: 100%;
}

@media (max-width: 1180px) {
  .auth-page {
    grid-template-columns: 1fr;
  }

  .hero-panel,
  .auth-panel {
    min-height: auto;
  }

  .hero-orbit {
    opacity: 0.28;
  }
}

@media (max-width: 760px) {
  .auth-page {
    padding: 14px;
    gap: 16px;
  }

  .hero-panel,
  .auth-panel {
    padding: 22px;
    border-radius: 26px;
  }

  .auth-stack {
    min-height: auto;
    padding: 0;
    display: grid;
    gap: 14px;
  }

  .auth-card {
    position: relative;
    inset: auto !important;
    transform: none !important;
  }

  .auth-card.idle {
    min-height: 160px;
  }

  .auth-card.active {
    box-shadow: 0 18px 34px rgba(15, 23, 42, 0.1);
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .sub-actions {
    flex-direction: column;
    align-items: flex-start;
  }

  .card-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
