<template>
  <div class="dashboard-page">
    <header class="dashboard-top surface-card">
      <div class="dashboard-top-main">
        <div class="welcome-block">
          <img
            :key="avatarUrl"
            :src="avatarUrl"
            class="welcome-avatar"
            alt="avatar"
            @error="handleAvatarError"
          />
          <div class="welcome-copy">
            <span class="page-tag">Rumor Workspace</span>
            <h1>欢迎回来，{{ userStore.profile?.username || '分析员' }}</h1>
            <p>{{ workspaceDescription }}</p>
          </div>
        </div>

        <section class="workspace-status-panel">
          <div class="workspace-status-head">
            <div>
              <span class="account-chip">账号信息</span>
              <h3>当前工作席位</h3>
              <p>{{ accountHint }}</p>
            </div>
            <el-tag class="status-tag" effect="dark" :type="userStore.isAdmin ? 'danger' : 'primary'" round>
              {{ userStore.isAdmin ? '管理员视角' : '用户视角' }}
            </el-tag>
          </div>

          <div class="account-grid">
            <article v-for="item in accountStatusItems" :key="item.title" class="account-card">
              <span>{{ item.title }}</span>
              <strong>{{ item.value }}</strong>
              <p>{{ item.description }}</p>
            </article>
          </div>
        </section>
      </div>

      <div class="top-actions">
        <div class="workspace-nav-shell">
          <div class="workspace-nav-head">
            <span class="nav-overline">工作台导航</span>
            <p>根据当前账号角色展示可进入的功能入口。</p>
          </div>

          <div class="workspace-nav-grid">
            <button
              v-for="item in workspaceEntries"
              :key="item.path"
              class="workspace-nav-item"
              :class="{ active: route.path === item.path }"
              @click="goTo(item.path)"
            >
              <span class="workspace-nav-icon">
                <el-icon><component :is="item.icon" /></el-icon>
              </span>
              <span class="workspace-nav-copy">
                <strong>{{ item.label }}</strong>
                <small>{{ item.description }}</small>
              </span>
            </button>
          </div>
        </div>

        <button class="ghost-btn danger" @click="handleLogout">退出登录</button>
      </div>
    </header>

    <section class="hero-strip">
      <article class="hero-pane hero-main">
        <div class="hero-main-copy">
          <span class="hero-chip">实时识别</span>
          <h2>输入一段文本，立即拿到风险判断与主谣言候选。</h2>
          <p>建议输入完整上下文，系统会返回谣言概率、主谣言匹配线索以及可继续回查的候选信息。</p>
        </div>

        <el-form class="predict-form" @submit.prevent>
          <el-input
            v-model="draftText"
            type="textarea"
            :rows="8"
            resize="none"
            placeholder="请输入待识别文本，例如一段网传消息、截图文案、聊天记录摘要等。"
          />
          <div class="predict-actions">
            <span class="predict-tip">完成识别后，最近一次结果会同步刷新到下方“最近一次识别”。</span>
            <el-button
              type="primary"
              size="large"
              :loading="predictLoading"
              @click="runPrediction"
            >
              {{ predictLoading ? '识别中...' : '开始识别' }}
            </el-button>
          </div>
        </el-form>
      </article>

      <article class="hero-pane hero-side hero-feed">
        <div class="feed-shell-head">
          <div>
            <span class="section-overline section-overline-warm">Trusted Sources</span>
            <h3>建议优先关注的权威入口</h3>
            <p>建议优先从权威平台核查，再结合识别结果与主谣言候选做交叉判断。</p>
          </div>
          <el-tag class="feed-tag" effect="plain" round>
            {{ userStore.isAdmin ? '识别 + 治理 + 核查' : '识别 + 核查' }}
          </el-tag>
        </div>

        <div class="feed-list feed-list-side">
          <a
            v-for="item in sourceFeeds"
            :key="item.name"
            class="feed-item"
            :href="item.url"
            target="_blank"
            rel="noreferrer"
          >
            <div>
              <strong>{{ item.name }}</strong>
              <p>{{ item.description }}</p>
            </div>
            <span>{{ item.tag }}</span>
          </a>
        </div>
      </article>
    </section>

    <section class="surface-card result-card">
      <div class="section-head">
        <div>
          <span class="section-overline">Latest Result</span>
          <h3>最近一次识别</h3>
        </div>
        <el-tag v-if="latestResult" :type="tagTypeMap[latestResult.risk_level]" effect="dark" round>
          {{ riskTextMap[latestResult.risk_level] }}
        </el-tag>
      </div>

      <div v-if="latestResult" class="result-shell">
        <div class="result-copy">
          <h4>{{ latestResult.verdict }}</h4>
          <p>{{ latestResult.text }}</p>
          <span class="result-foot">
            本条结果已同步写入历史记录，可继续前往历史页或主谣言库回查。
          </span>
        </div>

        <div class="result-metrics">
          <article class="metric-card metric-primary">
            <span>谣言概率</span>
            <strong>{{ formatPercent(latestResult.rumor_probability) }}</strong>
            <el-progress
              :percentage="toPercentage(latestResult.rumor_probability)"
              :status="latestResult.risk_level === 'high' ? 'exception' : latestResult.risk_level === 'medium' ? 'warning' : 'success'"
              :stroke-width="14"
            />
          </article>

          <article class="metric-card">
            <span>主谣言匹配概率</span>
            <strong>{{ formatPercent(latestMatchProbability) }}</strong>
            <p>优先显示后端返回的匹配概率，没有时回退到 Top1 候选分。</p>
          </article>

          <article class="metric-card">
            <span>基础模型概率</span>
            <strong>{{ formatPercent(latestBaseProbability) }}</strong>
            <p>用于辅助判断旧模型对当前结果的贡献强度。</p>
          </article>
        </div>
      </div>

      <section v-if="latestResult" class="related-strip">
        <div class="related-head">
          <div>
            <span class="section-overline">Top Matches</span>
            <h4>候选主谣言</h4>
          </div>
          <button class="ghost-btn slim-btn" @click="goTo('/rumor_library')">进入谣言库</button>
        </div>

        <div v-if="latestResult.related_rumors?.length" class="related-grid">
          <article
            v-for="item in latestResult.related_rumors.slice(0, 3)"
            :key="item.rumor_id || item.event_id || item.title"
            class="related-card"
          >
            <div class="related-meta">
              <strong>{{ item.source_name || '平台条目' }}</strong>
              <span>{{ item.publish_time || '时间待补充' }}</span>
            </div>
            <h5>{{ item.title || item.content }}</h5>
            <p>{{ item.match_hint || item.truth_text || '作为候选线索返回，可继续人工核查。' }}</p>
            <div class="related-bottom">
              <span>候选相关度 {{ formatMatchScore(item.match_score) }}</span>
              <button class="ghost-btn slim-btn primary-ghost" @click="viewRumorCandidate(item.rumor_id)">
                {{ item.rumor_id ? '查看主谣言' : '浏览谣言库' }}
              </button>
            </div>
          </article>
        </div>

        <div v-else class="candidate-empty">
          <p>当前这条结果暂未返回候选主谣言，后续补足召回后会在这里展示 Top-K 候选。</p>
        </div>
      </section>

      <el-empty
        v-else
        description="你还没有发起本轮会话的文本识别。识别完成后，这里会展示谣言概率和候选主谣言。"
      />
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Compass,
  DataBoard,
  Files,
  Location,
  Management,
  Notebook,
  UserFilled,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import api, { resolveAssetUrl } from '@/api/client'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const fallbackAvatar = 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png'

const draftText = ref('')
const latestResult = ref(null)
const predictLoading = ref(false)

const riskTextMap = {
  high: '高风险',
  medium: '需复核',
  low: '较稳定',
}

const tagTypeMap = {
  high: 'danger',
  medium: 'warning',
  low: 'success',
}

const sourceFeeds = [
  {
    name: '中国互联网联合辟谣平台',
    description: '适合核查社会热点、公共安全与政策类网传信息。',
    tag: '国家级',
    url: 'https://www.piyao.org.cn/',
  },
  {
    name: '较真查证平台',
    description: '适合寻找互联网流传说法的事实核验材料。',
    tag: '媒体',
    url: 'https://vp.fact.qq.com/',
  },
  {
    name: '科学辟谣',
    description: '偏向健康、科普、生活常识相关的误导信息澄清。',
    tag: '科普',
    url: 'https://piyao.kepuchina.cn/',
  },
]

const avatarUrl = computed(() => (
  resolveAssetUrl(
    userStore.profile?.avatar,
    userStore.profile?.update_time || userStore.profile?.avatar || '',
  ) || fallbackAvatar
))

const workspaceDescription = computed(() => (
  userStore.isAdmin
    ? '你可以在这里完成实时识别，并继续进入管理台、系统分析和地区分析页面进行联动核查。'
    : '你可以在这里完成实时识别，并继续前往历史记录、主谣言库和地区分析页面交叉核查。'
))

const accountHint = computed(() => (
  userStore.isAdmin
    ? '当前账号同时拥有识别、后台审核、地区分析和系统分析入口。'
    : '当前账号可进行文本识别、历史回看、主谣言查询和地区分析浏览。'
))

const workspaceEntries = computed(() => {
  const userEntries = [
    {
      path: '/geo_analysis',
      label: '地区分析',
      description: '单独查看全国到城市的地区传播画像。',
      icon: Location,
    },
    {
      path: '/history',
      label: '历史记录',
      description: '回看最近识别结果与处理轨迹。',
      icon: Notebook,
    },
    {
      path: '/rumor_library',
      label: '主谣言库',
      description: '浏览已知主谣言条目与辟谣摘要。',
      icon: Files,
    },
    {
      path: '/quickly_look',
      label: '速看辟谣',
      description: '查看常用权威平台与科普入口。',
      icon: Compass,
    },
    {
      path: '/person_center',
      label: '个人中心',
      description: '维护个人资料、头像和账号信息。',
      icon: UserFilled,
    },
  ]

  if (!userStore.isAdmin) {
    return userEntries
  }

  return [
    {
      path: '/admin',
      label: '管理员控制台',
      description: '处理用户治理、审核记录与主谣言维护。',
      icon: Management,
    },
    {
      path: '/data_analysis',
      label: '系统分析',
      description: '查看成员结构和后台统计总览。',
      icon: DataBoard,
    },
    ...userEntries,
  ]
})

const accountStatusItems = computed(() => [
  {
    title: '当前角色',
    value: userStore.isAdmin ? '管理员' : '普通用户',
    description: userStore.isAdmin ? '具备后台审核与治理权限。' : '聚焦识别、回查与浏览功能。',
  },
  {
    title: '账号状态',
    value: userStore.profile?.status || '未知',
    description: '状态由用户资料接口实时同步。',
  },
  {
    title: '最近活动量',
    value: `${userStore.predictionHistory.length} 条`,
    description: '仅统计当前账号自己的识别历史。',
  },
  {
    title: '可用功能',
    value: userStore.isAdmin ? '识别 + 管理 + 分析' : '识别 + 历史 + 分析',
    description: userStore.isAdmin ? '包含后台管理台和系统分析入口。' : '包含地区分析、主谣言库与历史回看。',
  },
])

const latestMatchProbability = computed(() => {
  if (!latestResult.value) {
    return 0
  }

  const directValue = Number(latestResult.value.event_match_probability)
  if (Number.isFinite(directValue) && directValue > 0) {
    return Math.max(0, Math.min(directValue, 1))
  }

  const fallbackValue = Number(latestResult.value.related_rumors?.[0]?.match_score)
  if (Number.isFinite(fallbackValue)) {
    return Math.max(0, Math.min(fallbackValue, 1))
  }

  return 0
})

const latestBaseProbability = computed(() => {
  const value = Number(latestResult.value?.base_model_probability)
  if (!Number.isFinite(value)) {
    return 0
  }
  return Math.max(0, Math.min(value, 1))
})

const goTo = (path) => {
  router.push(path)
}

const formatPercent = (value) => {
  const score = Number(value)
  if (!Number.isFinite(score)) {
    return '--'
  }
  return `${(Math.max(0, Math.min(score, 1)) * 100).toFixed(1)}%`
}

const toPercentage = (value) => {
  const score = Number(value)
  if (!Number.isFinite(score)) {
    return 0
  }
  return Number((Math.max(0, Math.min(score, 1)) * 100).toFixed(1))
}

const formatMatchScore = (value) => formatPercent(value)

const viewRumorCandidate = (rumorId) => {
  if (!rumorId) {
    router.push('/rumor_library')
    return
  }
  router.push({ path: '/rumor_library', query: { focus: String(rumorId) } })
}

const handleAvatarError = (event) => {
  if (event?.target) {
    event.target.src = fallbackAvatar
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
    ElMessage.success('已退出登录')
    router.push('/')
  } catch {
    // noop
  }
}

const runPrediction = async () => {
  if (!draftText.value.trim()) {
    ElMessage.warning('请输入要识别的文本')
    return
  }

  predictLoading.value = true
  try {
    const response = await api.post('/predict', { text: draftText.value })
    latestResult.value = userStore.recordPrediction(response.data.data)
    ElMessage.success('识别完成')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '识别失败，请确认后端模型是否可用')
  } finally {
    predictLoading.value = false
  }
}

onMounted(async () => {
  try {
    await userStore.fetchCurrentUser()
    await userStore.fetchPredictionHistory()
  } catch {
    // 保持当前缓存资料作为降级
  }

  const draftFromHistory = sessionStorage.getItem('draft_detection_text')
  if (draftFromHistory) {
    draftText.value = draftFromHistory
    sessionStorage.removeItem('draft_detection_text')
  }

  if (userStore.predictionHistory.length > 0) {
    latestResult.value = userStore.predictionHistory[0]
  }
})
</script>

<style scoped>
.dashboard-page {
  padding: 24px;
  display: grid;
  gap: 18px;
}

.dashboard-top {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(420px, 0.95fr);
  gap: 22px;
  padding: 24px 26px;
  border-radius: 30px;
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.14), transparent 22%),
    radial-gradient(circle at top right, rgba(255, 138, 61, 0.12), transparent 24%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.97), rgba(247, 249, 253, 0.96));
}

.dashboard-top-main {
  display: grid;
  gap: 18px;
  min-width: 0;
}

.welcome-block {
  display: flex;
  align-items: center;
  gap: 18px;
  min-width: 0;
  flex: 1;
}

.welcome-copy {
  min-width: 0;
}

.welcome-avatar {
  width: 76px;
  height: 76px;
  border-radius: 24px;
  object-fit: cover;
  border: 1px solid rgba(15, 123, 255, 0.12);
  box-shadow: 0 12px 24px rgba(15, 123, 255, 0.12);
  background: rgba(255, 255, 255, 0.86);
}

.page-tag,
.section-overline,
.hero-chip,
.nav-overline,
.account-chip {
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

.nav-overline {
  background: rgba(15, 123, 255, 0.1);
}

.account-chip {
  background: rgba(37, 99, 235, 0.1);
}

.section-overline-warm {
  background: rgba(249, 115, 22, 0.12);
  color: #c2410c;
}

.dashboard-top h1 {
  margin: 14px 0 10px;
  font-size: clamp(30px, 4vw, 44px);
  line-height: 1.06;
  letter-spacing: -0.04em;
  color: var(--ink-strong);
}

.dashboard-top p {
  margin: 0;
  max-width: 720px;
  color: var(--ink-soft);
  line-height: 1.8;
}

.top-actions {
  display: grid;
  gap: 14px;
  align-content: start;
}

.workspace-nav-shell {
  display: grid;
  gap: 12px;
}

.workspace-nav-head {
  display: grid;
  gap: 8px;
  justify-items: end;
}

.workspace-nav-head p {
  max-width: 520px;
  text-align: right;
}

.workspace-nav-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.workspace-nav-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.9), rgba(244, 248, 255, 0.94));
  cursor: pointer;
  text-align: left;
  transition: 0.24s ease;
}

.workspace-nav-item:hover {
  transform: translateY(-1px);
  border-color: rgba(15, 123, 255, 0.26);
  box-shadow: 0 14px 26px rgba(15, 23, 42, 0.06);
}

.workspace-nav-item.active {
  border-color: rgba(15, 123, 255, 0.3);
  box-shadow: inset 0 0 0 1px rgba(15, 123, 255, 0.12);
}

.workspace-nav-icon {
  width: 42px;
  height: 42px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(15, 123, 255, 0.12), rgba(14, 165, 233, 0.16));
  color: var(--brand-deep);
  font-size: 18px;
}

.workspace-nav-copy {
  display: grid;
  gap: 6px;
}

.workspace-nav-copy strong {
  color: var(--ink-strong);
  line-height: 1.45;
}

.workspace-nav-copy small {
  color: var(--ink-soft);
  line-height: 1.55;
}

.ghost-btn {
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: rgba(255, 255, 255, 0.84);
  color: var(--ink-main);
  padding: 10px 16px;
  border-radius: 16px;
  cursor: pointer;
  transition: 0.24s ease;
}

.ghost-btn:hover {
  transform: translateY(-1px);
  border-color: rgba(15, 123, 255, 0.28);
}

.ghost-btn.danger {
  color: var(--danger);
}

.ghost-btn.slim-btn {
  padding: 8px 12px;
  border-radius: 12px;
  font-size: 13px;
}

.ghost-btn.primary-ghost {
  color: var(--brand-deep);
}

.workspace-status-panel {
  padding-top: 18px;
  border-top: 1px solid rgba(148, 163, 184, 0.18);
}

.workspace-status-head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
  margin-bottom: 16px;
}

.workspace-status-head h3 {
  margin: 12px 0 8px;
  font-size: 28px;
  color: var(--ink-strong);
  line-height: 1.08;
  letter-spacing: -0.04em;
}

.workspace-status-head p {
  max-width: 760px;
}

.status-tag {
  margin-top: 2px;
}

.account-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.account-card {
  padding: 16px;
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.76), rgba(243, 248, 255, 0.78));
  border: 1px solid rgba(148, 163, 184, 0.14);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.66);
}

.account-card span {
  display: block;
  color: var(--ink-soft);
  font-size: 12px;
}

.account-card strong {
  display: block;
  margin: 10px 0 8px;
  font-size: 24px;
  color: var(--ink-strong);
}

.account-card p {
  margin: 0;
  color: var(--ink-soft);
  line-height: 1.65;
  font-size: 13px;
}

.hero-strip {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(340px, 0.85fr);
  gap: 14px;
}

.hero-pane {
  border-radius: 30px;
  padding: 24px;
}

.hero-main {
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.28), transparent 26%),
    linear-gradient(135deg, #dbeafe 0%, #ffffff 52%, #eff6ff 100%);
  border: 1px solid rgba(37, 99, 235, 0.14);
  box-shadow: 0 24px 50px rgba(37, 99, 235, 0.1);
}

.hero-main h2 {
  margin: 16px 0 10px;
  font-size: clamp(28px, 4vw, 40px);
  line-height: 1.08;
  letter-spacing: -0.04em;
  color: var(--ink-strong);
}

.hero-main p {
  margin: 0 0 24px;
  color: var(--ink-soft);
  line-height: 1.8;
}

.predict-form :deep(.el-textarea__inner) {
  min-height: 210px;
  border-radius: 22px;
  box-shadow: none;
  border: 1px solid rgba(37, 99, 235, 0.16);
  padding: 16px;
  background: rgba(255, 255, 255, 0.94);
}

.predict-actions {
  margin-top: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.predict-tip {
  color: var(--ink-soft);
  font-size: 13px;
}

.hero-side {
  display: grid;
  gap: 16px;
  background:
    radial-gradient(circle at top right, rgba(255, 138, 61, 0.16), transparent 24%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.97), rgba(255, 248, 241, 0.96));
  border: 1px solid rgba(249, 115, 22, 0.14);
  box-shadow: 0 24px 50px rgba(249, 115, 22, 0.08);
}

.feed-shell-head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
}

.hero-side h3 {
  margin: 12px 0 8px;
  font-size: 26px;
  color: var(--ink-strong);
}

.result-card {
  display: grid;
  gap: 18px;
  padding: 20px;
  border-radius: 26px;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.section-head h3 {
  margin: 10px 0 0;
  font-size: 24px;
  color: var(--ink-strong);
}

.result-shell {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.95fr);
  gap: 16px;
}

.result-copy,
.metric-card {
  padding: 18px;
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(15, 123, 255, 0.05), rgba(255, 255, 255, 0.96));
  border: 1px solid rgba(15, 123, 255, 0.1);
}

.result-copy {
  display: grid;
  align-content: start;
  gap: 12px;
}

.result-copy h4 {
  margin: 0;
  font-size: 26px;
  color: var(--ink-strong);
}

.result-copy p {
  margin: 0;
  color: var(--ink-main);
  line-height: 1.9;
  white-space: pre-wrap;
}

.result-foot {
  color: var(--ink-soft);
  line-height: 1.7;
}

.result-metrics {
  display: grid;
  gap: 12px;
}

.metric-card {
  display: grid;
  gap: 8px;
}

.metric-primary {
  background: linear-gradient(180deg, rgba(15, 123, 255, 0.08), rgba(255, 255, 255, 0.98));
}

.metric-card span {
  color: var(--ink-soft);
  font-size: 12px;
}

.metric-card strong {
  color: var(--ink-strong);
  font-size: 28px;
}

.metric-card p {
  margin: 0;
  color: var(--ink-soft);
  line-height: 1.65;
  font-size: 13px;
}

.related-strip {
  display: grid;
  gap: 14px;
}

.related-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.related-head h4 {
  margin: 10px 0 0;
  font-size: 20px;
  color: var(--ink-strong);
}

.related-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.related-card {
  padding: 16px;
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(244, 248, 255, 0.96));
  border: 1px solid rgba(15, 123, 255, 0.1);
  display: grid;
  gap: 10px;
}

.related-meta {
  display: grid;
  gap: 4px;
}

.related-meta strong {
  color: var(--brand-deep);
  font-size: 12px;
}

.related-meta span {
  color: var(--ink-soft);
  font-size: 12px;
}

.related-card h5 {
  margin: 0;
  font-size: 17px;
  line-height: 1.45;
  color: var(--ink-strong);
}

.related-card p {
  margin: 0;
  color: var(--ink-soft);
  line-height: 1.7;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.related-bottom {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  color: var(--ink-soft);
  font-size: 12px;
}

.candidate-empty {
  padding: 16px 18px;
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.92);
  border: 1px dashed rgba(148, 163, 184, 0.28);
}

.candidate-empty p {
  margin: 0;
  color: var(--ink-soft);
  line-height: 1.8;
}

.feed-tag {
  color: #c2410c;
  border-color: rgba(249, 115, 22, 0.22);
}

.feed-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.feed-list-side {
  grid-template-columns: 1fr;
}

.feed-item {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 16px 18px;
  border-radius: 22px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(245, 248, 252, 0.94));
  border: 1px solid rgba(15, 23, 42, 0.08);
  text-decoration: none;
  transition: 0.25s ease;
}

.feed-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 20px 36px rgba(15, 23, 42, 0.08);
}

.feed-item strong {
  display: block;
  color: var(--ink-strong);
  margin-bottom: 8px;
}

.feed-item p {
  margin: 0;
  color: var(--ink-soft);
  line-height: 1.7;
}

.feed-item span {
  white-space: nowrap;
  color: var(--brand-deep);
  font-weight: 700;
}

@media (max-width: 1260px) {
  .dashboard-top,
  .hero-strip,
  .result-shell,
  .feed-list,
  .related-grid {
    grid-template-columns: 1fr;
  }

  .dashboard-top {
    align-items: stretch;
  }

  .top-actions,
  .workspace-nav-head {
    justify-items: start;
  }

  .workspace-nav-head p {
    text-align: left;
  }
}

@media (max-width: 820px) {
  .account-grid,
  .workspace-nav-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .dashboard-page {
    padding: 14px;
  }

  .dashboard-top,
  .hero-pane,
  .result-card,
  .feed-strip {
    padding: 18px;
    border-radius: 22px;
  }

  .dashboard-top,
  .welcome-block,
  .predict-actions,
  .workspace-status-head,
  .feed-shell-head,
  .related-head,
  .related-bottom {
    flex-direction: column;
    align-items: flex-start;
  }

  .workspace-nav-item,
  .feed-item {
    padding: 14px;
  }
}
</style>
