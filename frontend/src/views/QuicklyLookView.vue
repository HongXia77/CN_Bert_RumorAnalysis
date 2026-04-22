<template>
  <div class="quick-page">
    <header class="quick-top surface-card">
      <div>
        <span class="section-chip">Trusted Radar</span>
        <h1>速看辟谣入口</h1>
        <p>默认先看权威机构，下层保留精选创作者卡片；点击下层卡片即可切换主视角。</p>
      </div>

      <div class="top-actions">
        <button class="ghost-btn" @click="router.push('/rumor_library')">主谣言库</button>
        <button class="ghost-btn" @click="router.push('/main')">返回主页</button>
      </div>
    </header>

    <section class="quick-stage surface-card" v-loading="loading">
      <div class="stage-ornament ornament-blue"></div>
      <div class="stage-ornament ornament-warm"></div>

      <div class="stage-head">
        <div>
          <span class="stage-overline">Layered Sources</span>
          <h2>来源切换工作台</h2>
          <p>不再把官方机构和创作者入口简单堆成列表，而是做成有主次关系的双层卡片。</p>
        </div>

        <div class="stage-meta">
          <article class="meta-pill">
            <span>当前主视角</span>
            <strong>{{ activeCard === 'official' ? '权威机构' : '精选创作者' }}</strong>
          </article>
          <article class="meta-pill">
            <span>创作者平台</span>
            <strong>{{ currentPlatform.label }}</strong>
          </article>
          <article class="meta-pill">
            <span>数据状态</span>
            <strong>{{ feedStatusText }}</strong>
          </article>
        </div>
      </div>

      <div class="source-stack" :class="`is-${activeCard}`">
        <article
          class="source-card official-card"
          :class="{ active: activeCard === 'official', idle: activeCard !== 'official' }"
          @click="activateCard('official')"
        >
          <div v-if="activeCard !== 'official'" class="card-peek">
            <div class="peek-head">
              <span class="peek-chip">Official</span>
              <h3>权威机构</h3>
            </div>
            <div class="peek-fog">
              <span class="fog-line line-wide"></span>
              <span class="fog-line line-mid"></span>
              <span class="fog-line line-short"></span>
            </div>
          </div>

          <template v-else>
            <div class="card-shell">
              <div class="card-header">
                <div>
                  <span class="card-chip">Official Sources</span>
                  <h3>权威机构</h3>
                  <p>默认优先展示官方入口，先建立稳定信源，再决定是否补充创作者视角。</p>
                </div>
                <button class="peek-action" type="button" @click.stop="activateCard('creators')">切到创作者</button>
              </div>

              <div v-if="officialSources.length" class="card-grid official-grid">
                <article v-for="item in officialSources" :key="item.platform_id" class="entry-card official-entry">
                  <div class="entry-top">
                    <span class="entry-badge">{{ item.short_label || buildOfficialBadge(item.name) }}</span>
                    <span class="entry-tag">{{ item.badge_text || '权威入口' }}</span>
                  </div>
                  <h4>{{ item.name }}</h4>
                  <p>{{ item.description || '当前暂无补充说明。' }}</p>
                  <div class="entry-meta">
                    <span>{{ item.scene_hint || item.subtitle || '适合作为优先核查入口' }}</span>
                    <a v-if="item.url" :href="item.url" target="_blank" rel="noreferrer">查看平台</a>
                    <span v-else class="link-placeholder">链接待补充</span>
                  </div>
                </article>
              </div>
              <el-empty v-else description="当前还没有启用的权威机构入口。" />
            </div>
          </template>
        </article>

        <article
          class="source-card creator-card"
          :class="{ active: activeCard === 'creators', idle: activeCard !== 'creators' }"
          @click="activateCard('creators')"
        >
          <div v-if="activeCard !== 'creators'" class="card-peek">
            <div class="peek-head">
              <span class="peek-chip">Creators</span>
              <h3>精选创作者</h3>
            </div>
            <div class="peek-fog">
              <span class="fog-line line-wide"></span>
              <span class="fog-line line-mid"></span>
              <span class="fog-line line-short"></span>
            </div>
          </div>

          <template v-else>
            <div class="card-shell">
              <div class="card-header">
                <div>
                  <span class="card-chip creator-chip">Creator Deck</span>
                  <h3>精选创作者</h3>
                  <p>{{ currentPlatform.description || '按平台切换展示创作者资料，方便后续接入真实账号。' }}</p>
                </div>
                <button class="peek-action" type="button" @click.stop="activateCard('official')">切到官方</button>
              </div>

              <div v-if="creatorPlatforms.length" class="platform-switch">
                <button
                  v-for="platform in creatorPlatforms"
                  :key="platform.key"
                  class="platform-btn"
                  :class="{ active: activePlatform === platform.key }"
                  @click.stop="activePlatform = platform.key"
                >
                  <strong>{{ platform.label }}</strong>
                  <small>{{ platform.subtitle || '创作者平台' }}</small>
                </button>
              </div>

              <div v-if="visibleCreators.length" class="card-grid creator-grid">
                <article v-for="item in visibleCreators" :key="item.creator_id" class="entry-card creator-entry">
                  <div class="creator-top">
                    <div class="creator-avatar-shell">
                      <img
                        v-if="resolveCreatorAvatar(item)"
                        :src="resolveCreatorAvatar(item)"
                        :alt="item.display_name"
                        class="creator-avatar"
                      />
                      <div v-else class="creator-avatar placeholder" :class="`theme-${currentPlatform.themeToken}`">
                        {{ creatorInitial(item.display_name) }}
                      </div>
                    </div>

                    <div class="creator-top-copy">
                      <div class="entry-top creator-headline">
                        <span class="creator-pill">{{ currentPlatform.label }}</span>
                        <span class="followers">{{ item.follower_text || '粉丝数据待补充' }}</span>
                      </div>
                      <h4>{{ item.display_name }}</h4>
                      <span class="creator-positioning">{{ item.positioning || '定位说明待补充' }}</span>
                    </div>
                  </div>

                  <p>{{ item.description || '当前暂无创作者简介。' }}</p>
                  <div class="creator-tags" v-if="item.tags?.length">
                    <span v-for="tag in item.tags" :key="tag">{{ tag }}</span>
                  </div>
                  <div class="entry-meta">
                    <span>{{ item.platform_name || currentPlatform.label }}</span>
                    <a v-if="item.profile_url" :href="item.profile_url" target="_blank" rel="noreferrer">查看主页</a>
                    <span v-else class="link-placeholder">链接待补充</span>
                  </div>
                </article>
              </div>
              <el-empty v-else description="当前平台下还没有启用的创作者入口。" />
            </div>
          </template>
        </article>
      </div>

      <el-alert
        v-if="errorMessage"
        class="stage-alert"
        type="warning"
        :closable="false"
        show-icon
        :title="errorMessage"
      />

      <div class="principles-row">
        <article class="principle-card">
          <strong>01</strong>
          <div>
            <h4>先看官方</h4>
            <p>把权威入口置于上层，确保进入页面时先落在稳定信源上。</p>
          </div>
        </article>
        <article class="principle-card">
          <strong>02</strong>
          <div>
            <h4>再看创作者</h4>
            <p>创作者视角保留在下层，作为辅助解释与传播链路观察入口。</p>
          </div>
        </article>
        <article class="principle-card">
          <strong>03</strong>
          <div>
            <h4>平台分组</h4>
            <p>同一类创作者按平台切换，避免未来真实数据接入时结构混乱。</p>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import api, { resolveAssetUrl } from '@/api/client'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const errorMessage = ref('')
const activeCard = ref('official')
const activePlatform = ref('bilibili')
const officialSources = ref([])
const creatorPlatforms = ref([])
const creatorGroups = ref({})
const overview = ref({
  official_total: 0,
  creator_total: 0,
  creator_platform_total: 0,
})

const currentPlatform = computed(() => (
  creatorPlatforms.value.find((item) => item.key === activePlatform.value) || {
    key: 'fallback',
    label: '创作者平台',
    subtitle: '资料待补充',
    description: '当前还没有启用的创作者平台。',
    themeToken: 'warm',
  }
))

const visibleCreators = computed(() => creatorGroups.value[activePlatform.value] || [])

const feedStatusText = computed(() => {
  if (loading.value) {
    return '加载中'
  }
  if (overview.value.official_total || overview.value.creator_total) {
    return `${overview.value.official_total} 个机构 / ${overview.value.creator_total} 位创作者`
  }
  return '待接数据'
})

const buildOfficialBadge = (name = '') => (
  name.replace(/[^\u4e00-\u9fa5A-Za-z0-9]/g, '').slice(0, 5).toUpperCase() || 'SRC'
)

const creatorInitial = (name = '') => (
  (name.trim().charAt(0) || '创').toUpperCase()
)

const resolveCreatorAvatar = (creator) => {
  if (!creator?.avatar_url) {
    return ''
  }
  return resolveAssetUrl(creator.avatar_url, creator.update_time || '')
}

const activateCard = (target) => {
  if (activeCard.value === target) {
    return
  }
  activeCard.value = target
}

const fetchQuickSources = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await api.get('/quick-look/feed')
    const payload = response.data.data || {}
    officialSources.value = payload.official_sources || []
    creatorPlatforms.value = (payload.creator_platforms || []).map((item) => ({
      key: item.slug,
      label: item.name,
      subtitle: item.subtitle,
      description: item.description,
      themeToken: item.theme_token || 'warm',
    }))
    creatorGroups.value = payload.creator_groups || {}
    overview.value = payload.overview || overview.value

    if (creatorPlatforms.value.length > 0) {
      const currentExists = creatorPlatforms.value.some((item) => item.key === activePlatform.value)
      if (!currentExists) {
        activePlatform.value = creatorPlatforms.value[0].key
      }
    }
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || '速看辟谣来源加载失败，当前先保留界面结构。'
    ElMessage.error(errorMessage.value)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  userStore.bootstrap()
  fetchQuickSources()
})
</script>

<style scoped>
.quick-page {
  padding: 24px;
  display: grid;
  gap: 16px;
}

.quick-top,
.quick-stage {
  position: relative;
  overflow: hidden;
  padding: 18px 24px;
  border-radius: 30px;
}

.quick-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
}

.section-chip,
.stage-overline {
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

.quick-top h1,
.stage-head h2,
.card-header h3,
.card-peek h3,
.principle-card h4 {
  margin: 10px 0 8px;
  color: var(--ink-strong);
}

.quick-top h1,
.stage-head h2 {
  font-size: clamp(28px, 4vw, 40px);
  line-height: 1.08;
  letter-spacing: -0.04em;
}

.quick-top p,
.stage-head p,
.card-header p,
.card-peek p,
.entry-card p,
.principle-card p {
  margin: 0;
  color: var(--ink-soft);
  line-height: 1.8;
}

.top-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.ghost-btn {
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(255, 255, 255, 0.88);
  color: var(--ink-main);
  padding: 9px 15px;
  border-radius: 14px;
  cursor: pointer;
  transition: 0.2s ease;
}

.ghost-btn:hover {
  transform: translateY(-1px);
  border-color: rgba(15, 123, 255, 0.24);
  color: var(--brand-deep);
}

.quick-stage {
  padding: 24px 28px 26px;
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.08), transparent 24%),
    radial-gradient(circle at bottom right, rgba(255, 138, 61, 0.08), transparent 26%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(249, 250, 252, 0.98));
}

.stage-ornament {
  position: absolute;
  border-radius: 999px;
  filter: blur(4px);
  opacity: 0.55;
  pointer-events: none;
}

.ornament-blue {
  top: 44px;
  right: 160px;
  width: 180px;
  height: 180px;
  background: radial-gradient(circle, rgba(96, 165, 250, 0.18), transparent 68%);
}

.ornament-warm {
  left: 56px;
  bottom: 120px;
  width: 220px;
  height: 220px;
  background: radial-gradient(circle, rgba(251, 146, 60, 0.16), transparent 70%);
}

.stage-head {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
}

.stage-meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  min-width: 420px;
}

.meta-pill {
  padding: 12px 14px;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  background: rgba(255, 255, 255, 0.82);
}

.meta-pill span,
.entry-meta span,
.followers,
.creator-positioning {
  color: var(--ink-soft);
  font-size: 12px;
}

.meta-pill strong {
  display: block;
  margin-top: 6px;
  color: var(--ink-strong);
  font-size: 18px;
}

.source-stack {
  position: relative;
  z-index: 1;
  min-height: 860px;
  margin-top: 20px;
}

.source-card {
  position: absolute;
  border-radius: 32px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  transition:
    transform 0.32s ease,
    box-shadow 0.32s ease,
    background 0.32s ease;
}

.source-card.active {
  inset: 0 64px 72px 0;
  z-index: 2;
  box-shadow: 0 28px 54px rgba(15, 23, 42, 0.12);
}

.source-card.idle {
  inset: 94px 0 0 290px;
  z-index: 1;
  cursor: pointer;
  box-shadow: 0 18px 34px rgba(15, 23, 42, 0.08);
}

.source-card.idle:hover {
  transform: translate(-4px, -4px);
}

.source-stack.is-creators .source-card.active {
  inset: 0 0 72px 64px;
}

.source-stack.is-creators .source-card.idle {
  inset: 94px 290px 0 0;
}

.official-card.active {
  background:
    radial-gradient(circle at top right, rgba(15, 123, 255, 0.14), transparent 28%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(247, 250, 255, 0.96));
}

.creator-card.active {
  background:
    radial-gradient(circle at top right, rgba(255, 138, 61, 0.14), transparent 28%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 250, 246, 0.96));
}

.official-card.idle {
  background: linear-gradient(180deg, rgba(245, 249, 255, 0.94), rgba(232, 243, 255, 0.9));
}

.creator-card.idle {
  background: linear-gradient(180deg, rgba(255, 248, 242, 0.96), rgba(255, 238, 226, 0.9));
}

.card-shell {
  height: 100%;
  overflow-y: auto;
  padding: 26px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 20px;
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

.creator-chip {
  background: rgba(255, 138, 61, 0.14);
  color: #c2410c;
}

.peek-chip {
  background: rgba(255, 255, 255, 0.7);
  color: var(--ink-soft);
}

.card-header h3,
.card-peek h3 {
  font-size: 28px;
  line-height: 1.08;
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
  display: grid;
  align-content: space-between;
  padding: 24px 26px 28px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.2), rgba(255, 255, 255, 0.08)),
    radial-gradient(circle at top right, rgba(255, 255, 255, 0.14), transparent 34%);
  backdrop-filter: blur(8px);
}

.peek-head {
  display: grid;
  gap: 8px;
}

.peek-fog {
  display: grid;
  gap: 12px;
  filter: blur(5px);
  opacity: 0.85;
}

.fog-line {
  display: block;
  height: 18px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.55);
}

.line-wide {
  width: 82%;
}

.line-mid {
  width: 68%;
}

.line-short {
  width: 44%;
}

.card-grid {
  display: grid;
  gap: 14px;
}

.official-grid,
.creator-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.entry-card {
  padding: 22px;
  border-radius: 24px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  display: grid;
  gap: 14px;
}

.official-entry {
  background:
    radial-gradient(circle at top right, rgba(15, 123, 255, 0.08), transparent 34%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(247, 251, 255, 0.96));
}

.creator-entry {
  background:
    radial-gradient(circle at top right, rgba(255, 138, 61, 0.08), transparent 34%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 250, 246, 0.96));
}

.entry-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.creator-top {
  display: grid;
  grid-template-columns: 72px 1fr;
  gap: 14px;
  align-items: start;
}

.creator-top-copy {
  display: grid;
  gap: 8px;
}

.creator-headline {
  align-items: center;
}

.creator-avatar-shell {
  width: 72px;
  height: 72px;
}

.creator-avatar {
  width: 72px;
  height: 72px;
  border-radius: 22px;
  object-fit: cover;
  display: block;
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.creator-avatar.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  border-radius: 22px;
  color: #fff;
  font-size: 28px;
  font-weight: 800;
  letter-spacing: 0.06em;
}

.creator-avatar.theme-blue {
  background: linear-gradient(135deg, #0f7bff, #0ea5e9);
}

.creator-avatar.theme-warm {
  background: linear-gradient(135deg, #ff8a3d, #f97316);
}

.entry-badge,
.creator-pill,
.entry-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 82px;
  min-height: 42px;
  padding: 0 16px;
  border-radius: 14px;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.entry-badge {
  background: linear-gradient(135deg, #0f7bff, #0ea5e9);
  color: #fff;
}

.creator-pill {
  background: linear-gradient(135deg, #ff8a3d, #f97316);
  color: #fff;
}

.entry-tag {
  min-width: auto;
  min-height: auto;
  padding: 8px 12px;
  background: rgba(15, 123, 255, 0.08);
  color: var(--brand-deep);
}

.entry-card h4 {
  margin: 0;
  font-size: 22px;
  line-height: 1.35;
  color: var(--ink-strong);
}

.entry-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.entry-meta a {
  color: var(--brand-deep);
  text-decoration: none;
  font-weight: 700;
}

.link-placeholder {
  color: var(--ink-soft);
  font-size: 12px;
}

.platform-switch {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.platform-btn {
  padding: 16px 18px;
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  background: rgba(255, 255, 255, 0.88);
  cursor: pointer;
  text-align: left;
  transition: 0.22s ease;
}

.platform-btn:hover {
  transform: translateY(-1px);
  border-color: rgba(255, 138, 61, 0.26);
}

.platform-btn.active {
  border-color: rgba(255, 138, 61, 0.3);
  background: linear-gradient(180deg, rgba(255, 246, 240, 0.98), rgba(255, 237, 225, 0.96));
  box-shadow: inset 0 0 0 1px rgba(255, 138, 61, 0.12);
}

.platform-btn strong {
  display: block;
  margin-bottom: 6px;
  color: var(--ink-strong);
}

.platform-btn small {
  color: var(--ink-soft);
  line-height: 1.6;
}

.creator-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.creator-tags span {
  display: inline-flex;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 138, 61, 0.12);
  color: #c2410c;
  font-size: 12px;
}

.stage-alert {
  position: relative;
  z-index: 1;
  margin-top: 16px;
}

.principles-row {
  position: relative;
  z-index: 1;
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.principle-card {
  display: grid;
  grid-template-columns: 52px 1fr;
  gap: 14px;
  padding: 18px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.principle-card strong {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: 16px;
  background: linear-gradient(135deg, #0f7bff, #0ea5e9);
  color: #fff;
  font-size: 18px;
}

.principle-card h4 {
  font-size: 18px;
}

@media (max-width: 1200px) {
  .stage-head,
  .quick-top {
    flex-direction: column;
    align-items: flex-start;
  }

  .stage-meta,
  .official-grid,
  .creator-grid,
  .principles-row {
    grid-template-columns: 1fr;
    min-width: 0;
  }

  .source-stack {
    min-height: 980px;
  }
}

@media (max-width: 900px) {
  .platform-switch {
    grid-template-columns: 1fr;
  }

  .source-stack {
    min-height: auto;
    display: grid;
    gap: 14px;
  }

  .source-card {
    position: relative;
    inset: auto !important;
    transform: none !important;
  }

  .source-card.idle {
    min-height: 160px;
  }
}

@media (max-width: 760px) {
  .quick-page {
    padding: 14px;
  }

  .quick-top,
  .quick-stage {
    padding: 18px;
    border-radius: 24px;
  }

  .top-actions,
  .card-header,
  .entry-top,
  .entry-meta,
  .creator-top {
    flex-direction: column;
    align-items: flex-start;
  }

  .creator-top {
    display: flex;
  }
}
</style>
