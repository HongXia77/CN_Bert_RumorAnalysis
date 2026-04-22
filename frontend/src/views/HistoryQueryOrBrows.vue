<template>
  <div class="history-page">
    <header class="history-top surface-card">
      <div>
        <span class="section-chip">Activity Ledger</span>
        <h1>识别历史与主谣言回看</h1>
        <p>这里汇总的是当前账号自己的识别记录，以及平台侧公开的主谣言样本，方便快速交叉核查。</p>
      </div>

      <div class="history-actions">
        <button class="ghost-btn" @click="router.push('/rumor_library')">主谣言库</button>
        <button class="ghost-btn" @click="router.push('/main')">返回主页</button>
        <button
          class="ghost-btn danger"
          :disabled="loading || userStore.predictionHistory.length === 0"
          @click="clearAll"
        >
          清空记录
        </button>
      </div>
    </header>

    <section class="toolbar surface-card">
      <el-radio-group v-model="filterType" size="large">
        <el-radio-button label="all">全部</el-radio-button>
        <el-radio-button label="high">高风险</el-radio-button>
        <el-radio-button label="medium">需复核</el-radio-button>
        <el-radio-button label="low">较稳定</el-radio-button>
      </el-radio-group>

      <div class="toolbar-meta">
        <span>{{ filteredRecords.length }} / {{ userStore.predictionHistory.length }} 条历史</span>
        <span>{{ publicRumors.length }} 条主谣言预览</span>
      </div>
    </section>

    <section class="content-section surface-card" v-loading="loading">
      <div class="section-head">
        <div>
          <span class="section-chip">My History</span>
          <h2>我的查询历史</h2>
        </div>
        <span class="section-note">支持回带识别、删除记录和跳转主谣言详情。</span>
      </div>

      <el-empty
        v-if="!loading && filteredRecords.length === 0"
        description="当前没有符合筛选条件的识别记录。"
      />

      <section v-else class="card-grid">
        <article v-for="item in filteredRecords" :key="item.id" class="history-card surface-card">
          <div class="card-top">
            <div class="card-copy">
              <span class="record-time">{{ formatTime(item.createdAt) }}</span>
              <h3>{{ item.verdict }}</h3>
            </div>

            <div class="card-tags">
              <el-tag :type="tagTypeMap[item.risk_level]" effect="dark" round>
                {{ riskTextMap[item.risk_level] }}
              </el-tag>
              <el-tag v-if="item.upload_status" type="info" effect="plain" round>
                {{ item.upload_status }}
              </el-tag>
            </div>
          </div>

          <p class="record-text" :title="item.text">{{ item.text }}</p>

          <div class="record-metrics">
            <div>
              <span>谣言概率</span>
              <strong>{{ formatPercent(item.rumor_probability) }}</strong>
            </div>
            <div>
              <span>可信概率</span>
              <strong>{{ formatPercent(item.credible_probability) }}</strong>
            </div>
          </div>

          <div v-if="item.related_rumors?.length" class="match-strip">
            <span class="match-label">关联主谣言</span>
            <div class="match-list">
              <button
                v-for="candidate in item.related_rumors.slice(0, 2)"
                :key="`${item.id}-${candidate.rumor_id || candidate.event_id || candidate.title}`"
                class="match-pill"
                @click="openRumorById(candidate.rumor_id)"
              >
                {{ candidate.title || candidate.content }}
              </button>
            </div>
          </div>

          <div class="card-bottom">
            <span class="record-hint">{{ buildHint(item) }}</span>

            <div class="card-actions">
              <button
                v-if="item.merged_rumor_id || item.related_rumors?.length"
                class="ghost-btn"
                @click="openRumorFromRecord(item)"
              >
                查看主谣言
              </button>
              <button class="ghost-btn" @click="fillBackToMain(item.text)">再次识别</button>
              <button class="ghost-btn danger" :disabled="loading" @click="removeRecord(item.id)">删除</button>
            </div>
          </div>
        </article>
      </section>
    </section>

    <section class="content-section surface-card" v-loading="rumorLoading">
      <div class="section-head">
        <div>
          <span class="section-chip">Rumor Feed</span>
          <h2>近期主谣言信息</h2>
        </div>
        <button class="ghost-btn" @click="router.push('/rumor_library')">查看更多</button>
      </div>

      <el-empty
        v-if="!rumorLoading && publicRumors.length === 0"
        description="当前暂未获取到主谣言预览。"
      />

      <section v-else class="card-grid">
        <article v-for="item in publicRumors" :key="item.rumor_id" class="rumor-card surface-card">
          <div class="card-top">
            <div class="card-copy">
              <span class="record-time">{{ item.source_name || '平台条目' }}</span>
              <h3>{{ item.title || item.content }}</h3>
            </div>
            <el-tag type="primary" effect="plain" round>{{ item.publish_time || '时间待补充' }}</el-tag>
          </div>

          <div class="claim-block">
            <span>核心断言</span>
            <p>{{ item.content }}</p>
          </div>

          <p class="record-text">{{ item.truth_text || '当前暂无辟谣摘要，可进入详情继续查看。' }}</p>

          <div class="card-bottom">
            <span class="record-hint">来自主谣言库，可直接带回识别或打开详情核查。</span>

            <div class="card-actions">
              <button class="ghost-btn" @click="reuseRumorText(item)">带回识别</button>
              <button class="ghost-btn" @click="openRumorById(item.rumor_id)">查看详情</button>
            </div>
          </div>
        </article>
      </section>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import api from '@/api/client'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
userStore.bootstrap()

const filterType = ref('all')
const loading = ref(false)
const rumorLoading = ref(false)
const publicRumors = ref([])

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

const filteredRecords = computed(() => {
  if (filterType.value === 'all') {
    return userStore.predictionHistory
  }
  return userStore.predictionHistory.filter((item) => item.risk_level === filterType.value)
})

const formatTime = (value) => {
  const date = new Date(value)
  return date.toLocaleString('zh-CN', { hour12: false })
}

const formatPercent = (value) => `${(Number(value || 0) * 100).toFixed(1)}%`

const buildHint = (item) => {
  if (item.merge_reason) {
    return item.merge_reason
  }
  if (item.upload_status === '待合并') {
    return '该条记录仍在等待归并确认。'
  }
  if (item.upload_status === '无效') {
    return '当前未命中已知主谣言，已作为普通查询历史保留。'
  }
  if (item.merge_strategy === 'new_rumor') {
    return '已单独形成一条新的主记录。'
  }
  if (item.merge_strategy) {
    return '已并入相近主记录，支持继续回查。'
  }
  return '可将文本带回主页继续识别。'
}

const loadHistory = async () => {
  loading.value = true
  try {
    await userStore.fetchPredictionHistory({ force: true })
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '获取识别历史失败')
  } finally {
    loading.value = false
  }
}

const loadRumors = async () => {
  rumorLoading.value = true
  try {
    const response = await api.get('/rumors/library', {
      params: {
        page: 1,
        page_size: 6,
      },
    })
    publicRumors.value = response.data.data?.items || []
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '获取主谣言预览失败')
  } finally {
    rumorLoading.value = false
  }
}

const removeRecord = async (recordId) => {
  try {
    await userStore.deletePredictionRecord(recordId)
    ElMessage.success('记录已删除')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '删除记录失败')
  }
}

const clearAll = async () => {
  try {
    await ElMessageBox.confirm('确认清空当前账号的全部识别记录吗？', '清空历史', {
      type: 'warning',
      confirmButtonText: '清空',
      cancelButtonText: '取消',
    })
    loading.value = true
    await userStore.clearPredictionHistory()
    ElMessage.success('识别记录已清空')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(error.response?.data?.detail || '清空记录失败')
    }
  } finally {
    loading.value = false
  }
}

const fillBackToMain = (text) => {
  sessionStorage.setItem('draft_detection_text', text)
  router.push('/main')
}

const reuseRumorText = (item) => {
  sessionStorage.setItem('draft_detection_text', item.content || item.title || '')
  router.push('/main')
}

const openRumorById = (rumorId) => {
  if (!rumorId) {
    router.push('/rumor_library')
    return
  }
  router.push({ path: '/rumor_library', query: { focus: String(rumorId) } })
}

const openRumorFromRecord = (item) => {
  const targetId = item.merged_rumor_id || item.candidate_rumor_id || item.related_rumors?.[0]?.rumor_id
  openRumorById(targetId)
}

onMounted(async () => {
  await Promise.all([loadHistory(), loadRumors()])
})
</script>

<style scoped>
.history-page {
  padding: 24px;
  display: grid;
  gap: 18px;
}

.history-top,
.toolbar,
.content-section {
  padding: 22px 24px;
  border-radius: 28px;
}

.history-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
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

.history-top h1,
.section-head h2 {
  margin: 14px 0 10px;
  font-size: clamp(28px, 4vw, 42px);
  line-height: 1.08;
  letter-spacing: -0.04em;
  color: var(--ink-strong);
}

.history-top p,
.section-note {
  margin: 0;
  color: var(--ink-soft);
  line-height: 1.8;
}

.history-actions,
.card-actions,
.card-tags {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.history-actions {
  justify-content: flex-end;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.toolbar-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  color: var(--ink-soft);
  font-size: 13px;
}

.content-section {
  display: grid;
  gap: 18px;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  align-items: start;
}

.history-card,
.rumor-card {
  padding: 18px 18px 16px;
  border-radius: 24px;
  display: grid;
  gap: 14px;
  align-content: start;
}

.history-card {
  background:
    radial-gradient(circle at top right, rgba(15, 123, 255, 0.1), transparent 30%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 251, 255, 0.96));
}

.rumor-card {
  background:
    radial-gradient(circle at top right, rgba(255, 138, 61, 0.12), transparent 26%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(252, 248, 243, 0.96));
}

.card-top,
.card-bottom {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
}

.card-copy {
  min-width: 0;
}

.record-time {
  display: block;
  margin-bottom: 8px;
  color: var(--ink-soft);
  font-size: 12px;
}

.card-top h3 {
  margin: 0;
  font-size: 20px;
  line-height: 1.35;
  color: var(--ink-strong);
}

.record-text {
  margin: 0;
  color: var(--ink-main);
  line-height: 1.75;
  white-space: pre-wrap;
  display: -webkit-box;
  -webkit-line-clamp: 5;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.record-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.record-metrics > div,
.claim-block {
  padding: 12px 14px;
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(15, 123, 255, 0.04), rgba(255, 255, 255, 0.82));
  border: 1px solid rgba(15, 123, 255, 0.08);
}

.claim-block span,
.record-metrics span {
  display: block;
  font-size: 12px;
  color: var(--ink-soft);
}

.claim-block p {
  margin: 8px 0 0;
  color: var(--ink-main);
  line-height: 1.7;
}

.record-metrics strong {
  display: block;
  margin-top: 6px;
  font-size: 20px;
  color: var(--ink-strong);
}

.match-strip {
  display: grid;
  gap: 10px;
}

.match-label {
  color: var(--ink-soft);
  font-size: 12px;
}

.match-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.match-pill {
  border: 1px solid rgba(15, 123, 255, 0.18);
  background: rgba(239, 246, 255, 0.92);
  color: var(--brand-deep);
  border-radius: 999px;
  padding: 8px 12px;
  cursor: pointer;
  transition: 0.2s ease;
}

.match-pill:hover {
  transform: translateY(-1px);
}

.record-hint {
  max-width: 360px;
  color: var(--ink-soft);
  font-size: 12px;
  line-height: 1.6;
}

.ghost-btn {
  border: 1px solid var(--line-soft);
  background: rgba(255, 255, 255, 0.84);
  color: var(--ink-main);
  padding: 10px 14px;
  border-radius: 14px;
  cursor: pointer;
  transition: 0.2s ease;
}

.ghost-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(15, 123, 255, 0.24);
}

.ghost-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.ghost-btn.danger {
  color: var(--danger);
}

@media (max-width: 980px) {
  .card-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .history-page {
    padding: 14px;
  }

  .history-top,
  .toolbar,
  .content-section,
  .history-card,
  .rumor-card {
    padding: 18px;
    border-radius: 22px;
  }

  .history-top,
  .history-actions,
  .toolbar,
  .section-head,
  .card-top,
  .card-bottom {
    flex-direction: column;
    align-items: flex-start;
  }

  .record-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
