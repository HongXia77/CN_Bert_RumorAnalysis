<template>
  <div class="library-page">
    <header class="library-top surface-card">
      <div>
        <span class="section-chip">Rumor Atlas</span>
        <h1>已知主谣言知识库</h1>
        <p>这里展示平台沉淀的主谣言条目，方便你把自己的查询历史与已知谣言样本交叉核查。</p>
      </div>

      <div class="library-actions">
        <button class="ghost-btn" @click="router.push('/history')">查看历史</button>
        <button class="ghost-btn" @click="router.push('/main')">返回主页</button>
      </div>
    </header>

    <section class="toolbar surface-card">
      <div class="toolbar-row">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索标题 / 核心断言 / 辟谣摘要"
          clearable
          @keyup.enter="applySearch"
        />
        <el-button type="primary" @click="applySearch">查询</el-button>
      </div>

      <div class="toolbar-meta">
        <span>当前展示 {{ rumors.length }} / {{ pagination.total }} 条</span>
        <span>已按发布时间优先排序</span>
      </div>
    </section>

    <el-empty
      v-if="!loading && rumors.length === 0"
      description="当前没有匹配的主谣言条目。"
    />

    <section v-else class="rumor-grid" v-loading="loading">
      <article v-for="item in rumors" :key="item.rumor_id" class="rumor-card surface-card">
        <div class="card-top">
          <div class="card-copy">
            <span class="meta-line">
              <strong>{{ item.source_name || '平台条目' }}</strong>
              <em>{{ item.publish_time || '时间待补充' }}</em>
            </span>
            <h3>{{ item.title || item.content }}</h3>
          </div>

          <el-tag type="primary" effect="plain" round>主谣言</el-tag>
        </div>

        <div class="claim-panel">
          <span>核心断言</span>
          <p>{{ item.content }}</p>
        </div>

        <div class="truth-panel">
          <span>辟谣摘要</span>
          <p>{{ item.truth_text || '当前暂无摘要，可打开详情查看原文。' }}</p>
        </div>

        <div class="card-bottom">
          <button class="ghost-btn" @click="reuseRumorText(item)">带回识别</button>
          <div class="action-group">
            <a
              v-if="item.article_url"
              class="ghost-btn link-btn"
              :href="item.article_url"
              target="_blank"
              rel="noreferrer"
            >
              查看来源
            </a>
            <button class="ghost-btn primary-ghost" @click="openRumorDetail(item)">查看详情</button>
          </div>
        </div>
      </article>
    </section>

    <div class="pagination-wrap" v-if="pagination.total > 0">
      <el-pagination
        background
        layout="total, sizes, prev, pager, next"
        :total="pagination.total"
        :current-page="pagination.page"
        :page-size="pagination.pageSize"
        :page-sizes="[6, 12, 24, 48]"
        @current-change="handlePageChange"
        @size-change="handlePageSizeChange"
      />
    </div>

    <el-drawer
      v-model="detailVisible"
      size="46%"
      destroy-on-close
      class="rumor-drawer"
    >
      <template #header>
        <div class="drawer-head" v-if="activeRumor">
          <span class="section-chip">Rumor Detail</span>
          <h2>{{ activeRumor.title || activeRumor.content }}</h2>
          <p>{{ activeRumor.source_name || '平台条目' }} · {{ activeRumor.publish_time || '时间待补充' }}</p>
        </div>
      </template>

      <div v-if="activeRumor" class="drawer-body">
        <section class="drawer-section surface-card">
          <span>核心断言</span>
          <p>{{ activeRumor.content }}</p>
        </section>

        <section class="drawer-section surface-card">
          <span>辟谣摘要</span>
          <p>{{ activeRumor.truth_text || '当前暂无摘要。' }}</p>
        </section>

        <section class="drawer-section surface-card">
          <div class="section-title">
            <span>原始正文</span>
            <a
              v-if="activeRumor.article_url"
              :href="activeRumor.article_url"
              target="_blank"
              rel="noreferrer"
            >
              打开原文
            </a>
          </div>
          <p class="long-text">{{ activeRumor.raw_content || '当前未保存正文内容。' }}</p>
        </section>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import api from '@/api/client'

const router = useRouter()
const route = useRoute()

const loading = ref(false)
const detailVisible = ref(false)
const searchKeyword = ref('')
const rumors = ref([])
const activeRumor = ref(null)
const pagination = reactive({
  page: 1,
  pageSize: 12,
  total: 0,
})

const fetchRumors = async () => {
  loading.value = true
  try {
    const response = await api.get('/rumors/library', {
      params: {
        search: searchKeyword.value || undefined,
        page: pagination.page,
        page_size: pagination.pageSize,
      },
    })
    const payload = response.data.data || {}
    rumors.value = payload.items || []
    pagination.total = Number(payload.total || 0)
    pagination.page = Number(payload.page || pagination.page)
    pagination.pageSize = Number(payload.page_size || pagination.pageSize)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '获取主谣言列表失败')
  } finally {
    loading.value = false
  }
}

const openRumorDetail = async (item) => {
  activeRumor.value = item
  detailVisible.value = true
}

const openFocusedRumorFromRoute = async () => {
  const focusId = Number(route.query.focus || 0)
  if (!focusId) {
    return
  }

  try {
    const response = await api.get(`/rumors/library/${focusId}`)
    activeRumor.value = response.data.data
    detailVisible.value = true
  } catch {
    // 忽略无效的 focus 参数
  }
}

const applySearch = () => {
  pagination.page = 1
  fetchRumors()
}

const handlePageChange = (page) => {
  pagination.page = page
  fetchRumors()
}

const handlePageSizeChange = (pageSize) => {
  pagination.pageSize = pageSize
  pagination.page = 1
  fetchRumors()
}

const reuseRumorText = (item) => {
  sessionStorage.setItem('draft_detection_text', item.content || item.title || '')
  router.push('/main')
}

watch(
  () => route.query.focus,
  () => {
    openFocusedRumorFromRoute()
  },
)

onMounted(async () => {
  searchKeyword.value = typeof route.query.search === 'string' ? route.query.search : ''
  await fetchRumors()
  await openFocusedRumorFromRoute()
})
</script>

<style scoped>
.library-page {
  padding: 24px;
  display: grid;
  gap: 18px;
}

.library-top,
.toolbar {
  padding: 22px 24px;
  border-radius: 28px;
}

.library-top {
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

.library-top h1,
.drawer-head h2 {
  margin: 14px 0 10px;
  font-size: clamp(28px, 4vw, 42px);
  line-height: 1.08;
  letter-spacing: -0.04em;
  color: var(--ink-strong);
}

.library-top p,
.drawer-head p {
  margin: 0;
  color: var(--ink-soft);
  line-height: 1.8;
}

.library-actions,
.action-group {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.toolbar-row {
  flex: 1;
  display: flex;
  gap: 12px;
}

.toolbar-row :deep(.el-input__wrapper) {
  min-height: 46px;
  border-radius: 16px;
  box-shadow: none;
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.toolbar-meta {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  color: var(--ink-soft);
  font-size: 13px;
}

.rumor-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.rumor-card {
  padding: 20px;
  border-radius: 24px;
  display: grid;
  gap: 16px;
  align-content: start;
}

.card-top,
.card-bottom {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
}

.meta-line {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  color: var(--ink-soft);
  font-size: 12px;
}

.meta-line strong {
  color: var(--brand-deep);
}

.meta-line em {
  font-style: normal;
}

.card-copy h3 {
  margin: 10px 0 0;
  font-size: 22px;
  line-height: 1.35;
  color: var(--ink-strong);
}

.claim-panel,
.truth-panel,
.drawer-section {
  padding: 16px 18px;
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(15, 123, 255, 0.04), rgba(255, 255, 255, 0.88));
  border: 1px solid rgba(15, 123, 255, 0.08);
}

.claim-panel span,
.truth-panel span,
.drawer-section span {
  display: block;
  color: var(--ink-soft);
  font-size: 12px;
  margin-bottom: 8px;
}

.claim-panel p,
.truth-panel p,
.drawer-section p {
  margin: 0;
  color: var(--ink-main);
  line-height: 1.8;
}

.truth-panel p {
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.ghost-btn {
  border: 1px solid var(--line-soft);
  background: rgba(255, 255, 255, 0.84);
  color: var(--ink-main);
  padding: 10px 14px;
  border-radius: 14px;
  cursor: pointer;
  transition: 0.2s ease;
  text-decoration: none;
}

.ghost-btn:hover {
  transform: translateY(-1px);
  border-color: rgba(15, 123, 255, 0.24);
}

.primary-ghost {
  color: var(--brand-deep);
}

.link-btn {
  display: inline-flex;
  align-items: center;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
}

.drawer-body {
  display: grid;
  gap: 16px;
}

.section-title {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 8px;
}

.section-title a {
  color: var(--brand-deep);
  text-decoration: none;
  font-weight: 600;
}

.long-text {
  white-space: pre-wrap;
}

@media (max-width: 980px) {
  .rumor-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .library-page {
    padding: 14px;
  }

  .library-top,
  .toolbar,
  .rumor-card {
    padding: 18px;
    border-radius: 22px;
  }

  .library-top,
  .toolbar,
  .card-top,
  .card-bottom {
    flex-direction: column;
    align-items: flex-start;
  }

  .toolbar-row {
    width: 100%;
    flex-direction: column;
  }
}
</style>
