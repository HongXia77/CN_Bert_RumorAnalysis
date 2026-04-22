<template>
  <div class="profile-page">
    <header class="profile-top surface-card">
      <div>
        <span class="section-chip">Profile Center</span>
        <h1>账号资料与身份信息</h1>
        <p>这里展示的是后端实时返回的用户资料，你可以在此维护个人信息与头像。</p>
      </div>

      <div class="profile-top-actions">
        <button class="ghost-btn" @click="router.push('/rumor_library')">主谣言库</button>
        <button class="ghost-btn" @click="router.push('/main')">返回主页</button>
        <button v-if="userStore.isAdmin" class="ghost-btn" @click="router.push('/admin')">进入管理台</button>
        <button class="ghost-btn danger" @click="handleLogout">退出登录</button>
      </div>
    </header>

    <section class="profile-grid">
      <article class="surface-card profile-aside">
        <div class="aside-head">
          <img
            :key="avatarPreviewUrl"
            :src="avatarPreviewUrl"
            class="avatar"
            alt="avatar"
            @error="handleAvatarError"
          />
          <div>
            <h2>{{ userStore.profile?.username || '未命名用户' }}</h2>
            <p>{{ userStore.isAdmin ? '管理员账号' : '普通用户账号' }}</p>
          </div>
        </div>

        <div class="aside-stats">
          <div>
            <span>账号状态</span>
            <strong>{{ userStore.profile?.status || '未知' }}</strong>
          </div>
          <div>
            <span>已保存历史</span>
            <strong>{{ userStore.predictionHistory.length }} 条</strong>
          </div>
          <div>
            <span>创建时间</span>
            <strong>{{ userStore.profile?.create_time ? userStore.profile.create_time.slice(0, 10) : '--' }}</strong>
          </div>
        </div>

        <el-upload
          class="upload-slot"
          :show-file-list="false"
          :http-request="uploadAvatar"
          accept="image/png,image/jpeg"
        >
          <el-button type="primary" plain>更换头像</el-button>
        </el-upload>
      </article>

      <article class="surface-card profile-form-card">
        <div class="section-head">
          <div>
            <span class="section-chip">Account Form</span>
            <h2>维护个人资料</h2>
          </div>
        </div>

        <el-skeleton v-if="loading" :rows="8" animated />

        <el-form v-else label-position="top" class="profile-form">
          <div class="form-grid">
            <el-form-item label="用户名">
              <el-input :model-value="userStore.profile?.username" disabled />
            </el-form-item>

            <el-form-item label="角色">
              <el-input :model-value="userStore.profile?.role" disabled />
            </el-form-item>

            <el-form-item label="邮箱">
              <el-input v-model="form.email" placeholder="请输入邮箱" clearable />
            </el-form-item>

            <el-form-item label="手机号">
              <el-input v-model="form.phone" placeholder="请输入手机号" clearable />
            </el-form-item>

            <el-form-item label="性别">
              <el-select v-model="form.gender" placeholder="请选择性别">
                <el-option label="男" value="男" />
                <el-option label="女" value="女" />
                <el-option label="未知" value="未知" />
              </el-select>
            </el-form-item>

            <el-form-item label="生日">
              <el-date-picker
                v-model="form.birthday"
                type="date"
                value-format="x"
                placeholder="请选择生日"
                :disabled-date="disabledFutureDates"
              />
            </el-form-item>

            <el-form-item label="省份">
              <el-select v-model="form.province" placeholder="请选择省份" filterable>
                <el-option
                  v-for="item in provinceOptions"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-select>
            </el-form-item>

            <el-form-item :label="subregionLabel">
              <el-select
                v-model="form.city"
                :placeholder="subregionPlaceholder"
                filterable
                :disabled="cityOptions.length === 0"
              >
                <el-option
                  v-for="item in cityOptions"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-select>
            </el-form-item>
          </div>

          <div class="form-actions">
            <el-button @click="resetForm">重置</el-button>
            <el-button type="primary" :loading="saving" @click="saveProfile">保存修改</el-button>
          </div>
        </el-form>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import api, { resolveAssetUrl } from '@/api/client'
import {
  getCitiesByProvince,
  getSubregionLabel,
  normalizeLocationSelection,
  normalizeBirthdayValue,
  provinceOptions,
} from '@/constants/regions'
import { useUserStore } from '@/stores/user'

const fallbackAvatar = 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(true)
const saving = ref(false)
const avatarVersion = ref(Date.now())

const form = reactive({
  avatar: '',
  email: '',
  phone: '',
  gender: '未知',
  province: '',
  city: '',
  birthday: '',
})

const avatarPreviewUrl = computed(() => resolveAssetUrl(form.avatar, avatarVersion.value) || fallbackAvatar)
const cityOptions = computed(() => getCitiesByProvince(form.province))
const subregionLabel = computed(() => getSubregionLabel(form.province))
const subregionPlaceholder = computed(() => `请选择${subregionLabel.value}`)

const disabledFutureDates = (time) => time.getTime() > Date.now()

watch(
  () => form.province,
  (nextProvince, previousProvince) => {
    if (nextProvince === previousProvince) {
      return
    }

    const normalizedLocation = normalizeLocationSelection(nextProvince, form.city)
    if (form.province !== normalizedLocation.province) {
      form.province = normalizedLocation.province
    }
    if (form.city !== normalizedLocation.city) {
      form.city = normalizedLocation.city
    }
  },
)

const applyProfile = (profile) => {
  const normalizedLocation = normalizeLocationSelection(profile?.province, profile?.city)

  form.avatar = profile?.avatar || ''
  form.email = profile?.email || ''
  form.phone = profile?.phone || ''
  form.gender = profile?.gender || '未知'
  form.province = normalizedLocation.province
  form.city = normalizedLocation.city
  form.birthday = normalizeBirthdayValue(profile?.birthday)

  avatarVersion.value = profile?.update_time ? new Date(profile.update_time).getTime() : Date.now()
}

const loadProfile = async () => {
  loading.value = true
  try {
    const profile = await userStore.fetchCurrentUser()
    applyProfile(profile)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '获取资料失败')
  }

  try {
    await userStore.fetchPredictionHistory()
  } catch {
    // 历史数量获取失败时不阻断资料页展示
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  applyProfile(userStore.profile)
}

const handleAvatarError = (event) => {
  if (event?.target) {
    event.target.src = fallbackAvatar
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

  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await api.post('/upload-avatar', formData)
    const updatedProfileResponse = await api.put('/me', {
      avatar: response.data.url,
    })

    userStore.updateProfile(updatedProfileResponse.data.data)
    applyProfile(updatedProfileResponse.data.data)
    ElMessage.success('头像上传成功')
    onSuccess?.(updatedProfileResponse.data.data)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '头像上传失败')
    onError?.(error)
  }
}

const saveProfile = async () => {
  const normalizedLocation = normalizeLocationSelection(form.province, form.city)

  if (!/^\S+@\S+\.\S+$/.test(form.email)) {
    ElMessage.warning('请输入有效邮箱')
    return
  }
  if (!/^1[3-9]\d{9}$/.test(form.phone)) {
    ElMessage.warning('请输入有效手机号')
    return
  }
  if (!normalizedLocation.province || !normalizedLocation.city) {
    ElMessage.warning(`请补充省份和${subregionLabel.value}信息`)
    return
  }

  saving.value = true
    try {
      form.province = normalizedLocation.province
      form.city = normalizedLocation.city

      await api.put('/me', {
        avatar: form.avatar,
        email: form.email,
        phone: form.phone,
        gender: form.gender,
        province: form.province,
        city: form.city,
        birthday_ts: form.birthday ? Math.floor(Number(form.birthday) / 1000) : null,
      })

      const latestProfile = await userStore.fetchCurrentUser()
      applyProfile(latestProfile)
      ElMessage.success('资料已更新')
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '资料更新失败')
    } finally {
      saving.value = false
    }
}

const handleLogout = async () => {
  try {
    await ElMessageBox.confirm('确认退出当前账号吗？', '退出登录', {
      type: 'warning',
      confirmButtonText: '退出',
      cancelButtonText: '取消',
    })
    userStore.clearSession()
    router.push('/')
  } catch {
    // noop
  }
}

onMounted(() => {
  userStore.bootstrap()
  loadProfile()
})
</script>

<style scoped>
.profile-page {
  padding: 24px;
  display: grid;
  gap: 22px;
}

.profile-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
  padding: 26px 28px;
  border-radius: 28px;
}

.section-chip {
  display: inline-flex;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(15, 123, 255, 0.08);
  color: var(--brand-deep);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.profile-top h1 {
  margin: 14px 0 10px;
  font-size: clamp(28px, 4vw, 42px);
  line-height: 1.08;
  letter-spacing: -0.04em;
  color: var(--ink-strong);
}

.profile-top p {
  margin: 0;
  color: var(--ink-soft);
  line-height: 1.8;
}

.profile-top-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.ghost-btn {
  border: 1px solid var(--line-soft);
  background: rgba(255, 255, 255, 0.84);
  color: var(--ink-main);
  padding: 12px 18px;
  border-radius: 16px;
  cursor: pointer;
}

.ghost-btn.danger {
  color: var(--danger);
}

.profile-grid {
  display: grid;
  grid-template-columns: minmax(300px, 0.7fr) minmax(0, 1.3fr);
  gap: 18px;
}

.profile-aside,
.profile-form-card {
  padding: 24px;
  border-radius: 28px;
}

.aside-head {
  display: flex;
  gap: 18px;
  align-items: center;
  margin-bottom: 22px;
}

.avatar {
  width: 108px;
  height: 108px;
  object-fit: cover;
  border-radius: 28px;
  border: 1px solid var(--line-soft);
}

.aside-head h2 {
  margin: 0 0 8px;
  color: var(--ink-strong);
}

.aside-head p {
  margin: 0;
  color: var(--ink-soft);
}

.aside-stats {
  display: grid;
  gap: 12px;
  margin-bottom: 22px;
}

.aside-stats > div {
  padding: 16px 18px;
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(15, 123, 255, 0.04), rgba(255, 255, 255, 0.8));
  border: 1px solid rgba(15, 123, 255, 0.08);
}

.aside-stats span {
  display: block;
  font-size: 13px;
  color: var(--ink-soft);
}

.aside-stats strong {
  display: block;
  margin-top: 8px;
  font-size: 24px;
  color: var(--ink-strong);
}

.section-head {
  margin-bottom: 18px;
}

.section-head h2 {
  margin: 12px 0 0;
  font-size: 28px;
  color: var(--ink-strong);
}

.profile-form {
  display: grid;
  gap: 16px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.upload-slot {
  display: inline-flex;
}

.profile-form :deep(.el-input__wrapper),
.profile-form :deep(.el-select__wrapper),
.profile-form :deep(.el-date-editor.el-input__wrapper) {
  border-radius: 16px;
  box-shadow: none;
  min-height: 46px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(255, 255, 255, 0.92);
}

.profile-form :deep(.el-select),
.profile-form :deep(.el-date-editor.el-input) {
  width: 100%;
}

@media (max-width: 980px) {
  .profile-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .profile-page {
    padding: 14px;
  }

  .profile-top,
  .profile-aside,
  .profile-form-card {
    padding: 18px;
    border-radius: 22px;
  }

  .profile-top,
  .profile-top-actions {
    flex-direction: column;
    align-items: flex-start;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .form-actions {
    justify-content: stretch;
    flex-direction: column;
  }
}
</style>
