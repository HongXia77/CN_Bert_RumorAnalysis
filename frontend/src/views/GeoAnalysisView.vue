<template>
  <div class="geo-page">
    <header class="geo-page-top surface-card">
      <div>
        <span class="section-chip">Regional Workspace</span>
        <h1>地区分析</h1>
        <p>这里单独承接全国到城市的地区热度下钻，方便在不打断主页识别流程的情况下查看区域传播画像。</p>
      </div>

      <div class="geo-page-actions">
        <button class="ghost-btn" @click="router.push('/main')">返回主页</button>
        <button
          v-if="userStore.isAdmin"
          class="ghost-btn"
          @click="router.push('/data_analysis')"
        >
          系统分析
        </button>
      </div>
    </header>

    <GeoAnalyticsPanel />
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

import GeoAnalyticsPanel from '@/components/GeoAnalyticsPanel.vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

userStore.bootstrap()
</script>

<style scoped>
.geo-page {
  padding: 24px;
  display: grid;
  gap: 18px;
}

.geo-page-top {
  padding: 22px 24px;
  border-radius: 28px;
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

.geo-page-top h1 {
  margin: 14px 0 8px;
  font-size: clamp(30px, 4vw, 42px);
  line-height: 1.08;
  letter-spacing: -0.04em;
  color: var(--ink-strong);
}

.geo-page-top p {
  margin: 0;
  max-width: 760px;
  color: var(--ink-soft);
  line-height: 1.8;
}

.geo-page-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.ghost-btn {
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: rgba(255, 255, 255, 0.84);
  color: var(--ink-main);
  padding: 10px 16px;
  border-radius: 16px;
  cursor: pointer;
  transition: 0.2s ease;
}

.ghost-btn:hover {
  transform: translateY(-1px);
  border-color: rgba(15, 123, 255, 0.24);
}

@media (max-width: 760px) {
  .geo-page {
    padding: 14px;
  }

  .geo-page-top {
    padding: 18px;
    border-radius: 22px;
    flex-direction: column;
    align-items: flex-start;
  }

  .geo-page-actions {
    justify-content: flex-start;
  }
}
</style>
