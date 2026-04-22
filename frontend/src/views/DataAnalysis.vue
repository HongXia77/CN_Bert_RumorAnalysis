<template>
  <div class="analysis-page">
    <header class="analysis-top surface-card">
      <div>
        <span class="section-chip">Admin Analytics</span>
        <h1>系统分析总览</h1>
        <p>结合管理员接口返回的数据，查看成员结构、账号状态和谣言库的整体分布。</p>
      </div>

      <div class="analysis-actions">
        <button class="ghost-btn" @click="router.push('/admin')">返回管理台</button>
        <button class="ghost-btn" @click="router.push('/main')">返回主页</button>
      </div>
    </header>

    <section class="kpi-grid">
      <article v-for="item in kpiCards" :key="item.title" class="kpi-card surface-card">
        <span>{{ item.title }}</span>
        <strong>{{ item.value }}</strong>
        <p>{{ item.description }}</p>
      </article>
    </section>

    <section class="chart-grid">
      <article class="surface-card chart-card">
        <div class="card-head">
          <div>
            <span class="section-chip">Users</span>
            <h2>成员状态结构</h2>
          </div>
        </div>
        <div ref="userChartRef" class="chart-box"></div>
      </article>

      <article class="surface-card chart-card">
        <div class="card-head">
          <div>
            <span class="section-chip">Rumors</span>
            <h2>谣言库概况</h2>
          </div>
        </div>
        <div ref="rumorChartRef" class="chart-box"></div>
      </article>
    </section>

    <section class="surface-card table-card">
      <div class="card-head">
        <div>
          <span class="section-chip">Latest Members</span>
          <h2>最近创建的账号</h2>
        </div>
      </div>

      <el-table :data="overview.latest_users || []" stripe>
        <el-table-column prop="username" label="用户名" min-width="140" />
        <el-table-column prop="role" label="角色" width="120" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column prop="email" label="邮箱" min-width="220" />
        <el-table-column prop="create_time" label="创建时间" min-width="180" />
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'

import api from '@/api/client'

const router = useRouter()

const userChartRef = ref(null)
const rumorChartRef = ref(null)
const overview = ref({
  user_stats: { total: 0, admin: 0, active: 0, disabled: 0, pending: 0 },
  rumor_stats: { total: 0, approved: 0, pending: 0, ratio: { rumor: 0, normal: 0 } },
  latest_users: [],
})

let userChart = null
let rumorChart = null

const kpiCards = computed(() => [
  {
    title: '总用户数',
    value: overview.value.user_stats.total,
    description: '包含普通用户与管理员。',
  },
  {
    title: '管理员数量',
    value: overview.value.user_stats.admin,
    description: '具备后台治理权限的账号数量。',
  },
  {
    title: '正常账号',
    value: overview.value.user_stats.active,
    description: '当前可正常访问系统的账号。',
  },
  {
    title: '谣言库规模',
    value: overview.value.rumor_stats.total,
    description: '来自数据库中可统计的谣言数据总数。',
  },
])

const renderCharts = async () => {
  await nextTick()

  if (userChartRef.value) {
    userChart?.dispose()
    userChart = echarts.init(userChartRef.value)
    userChart.setOption({
      tooltip: { trigger: 'item' },
      series: [
        {
          type: 'pie',
          radius: ['48%', '72%'],
          label: { color: '#334155' },
          data: [
            { value: overview.value.user_stats.active, name: '正常' },
            { value: overview.value.user_stats.disabled, name: '禁用' },
            { value: overview.value.user_stats.pending, name: '未激活' },
            { value: overview.value.user_stats.admin, name: '管理员' },
          ],
          color: ['#0f7bff', '#ef4444', '#f59e0b', '#10b981'],
        },
      ],
    })
  }

  if (rumorChartRef.value) {
    rumorChart?.dispose()
    rumorChart = echarts.init(rumorChartRef.value)
    rumorChart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: {
        type: 'category',
        data: ['总量', '已通过', '待审核', '谣言类', '非谣言类'],
        axisLabel: { color: '#475569' },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#475569' },
        splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.2)' } },
      },
      series: [
        {
          type: 'bar',
          barWidth: 28,
          data: [
            overview.value.rumor_stats.total,
            overview.value.rumor_stats.approved,
            overview.value.rumor_stats.pending,
            overview.value.rumor_stats.ratio?.rumor || 0,
            overview.value.rumor_stats.ratio?.normal || 0,
          ],
          itemStyle: {
            borderRadius: [10, 10, 0, 0],
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#0f7bff' },
              { offset: 1, color: '#0ea5e9' },
            ]),
          },
        },
      ],
    })
  }
}

const fetchOverview = async () => {
  try {
    const response = await api.get('/admin/overview')
    overview.value = response.data.data
    renderCharts()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '系统分析数据获取失败')
  }
}

const handleResize = () => {
  userChart?.resize()
  rumorChart?.resize()
}

onMounted(() => {
  fetchOverview()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  userChart?.dispose()
  rumorChart?.dispose()
})
</script>

<style scoped>
.analysis-page {
  padding: 24px;
  display: grid;
  gap: 22px;
}

.analysis-top,
.kpi-card,
.chart-card,
.table-card {
  padding: 24px;
  border-radius: 28px;
}

.analysis-top {
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

.analysis-top h1,
.card-head h2 {
  margin: 14px 0 8px;
  font-size: clamp(28px, 4vw, 42px);
  line-height: 1.08;
  letter-spacing: -0.04em;
  color: var(--ink-strong);
}

.analysis-top p {
  margin: 0;
  color: var(--ink-soft);
  line-height: 1.8;
}

.analysis-actions {
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

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.kpi-card span {
  color: var(--ink-soft);
  font-size: 13px;
}

.kpi-card strong {
  display: block;
  margin: 12px 0 8px;
  font-size: 32px;
  color: var(--ink-strong);
}

.kpi-card p {
  margin: 0;
  color: var(--ink-soft);
  line-height: 1.7;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.card-head {
  margin-bottom: 18px;
}

.chart-box {
  width: 100%;
  min-height: 360px;
}

.table-card :deep(.el-table) {
  border-radius: 18px;
  overflow: hidden;
}

@media (max-width: 1080px) {
  .kpi-grid,
  .chart-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .analysis-page {
    padding: 14px;
  }

  .analysis-top,
  .kpi-card,
  .chart-card,
  .table-card {
    padding: 18px;
    border-radius: 22px;
  }

  .analysis-top,
  .analysis-actions {
    flex-direction: column;
    align-items: flex-start;
  }

  .kpi-grid,
  .chart-grid {
    grid-template-columns: 1fr;
  }
}
</style>
