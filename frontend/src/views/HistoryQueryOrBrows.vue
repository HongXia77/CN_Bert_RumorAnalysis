<template>
  <div class="history-container">
    <el-page-header @back="goBack" content="活动历史" title="返回" />

    <div class="filter-bar">
      <el-radio-group v-model="filterType" size="large">
        <el-radio-button label="all">全部记录</el-radio-button>
        <el-radio-button label="evaluate">评估记录</el-radio-button>
        <el-radio-button label="view">查看历史</el-radio-button>
      </el-radio-group>
    </div>

    <div class="history-list">
      <el-empty v-if="historyData.length === 0" description="暂无历史记录" />

      <el-timeline v-else>
        <el-timeline-item
          v-for="item in filteredData"
          :key="item.id"
          :timestamp="item.date"
          placement="top"
          :type="item.type === 'evaluate' ? 'primary' : 'info'"
        >
          <el-card shadow="hover" class="history-card">
            <div class="card-header">
              <el-tag :type="item.type === 'evaluate' ? 'danger' : 'info'" effect="light">
                {{ item.type === 'evaluate' ? '谣言评估' : '浏览记录' }}
              </el-tag>
              <span class="activity-time">{{ item.time }}</span>
            </div>

            <div class="card-body">
              <h4 class="rumor-text">{{ item.content }}</h4>

              <div v-if="item.type === 'evaluate'" class="score-badge">
                <span class="label">评估概率：</span>
                <span class="value" :style="{ color: getScoreColor(item.score) }">
                  {{ (item.score * 100).toFixed(1) }}%
                </span>
              </div>
            </div>

            <div class="card-footer">
              <el-button type="primary" link @click="viewDetails(item.rumorId)">
                查看详情 <el-icon><ArrowRight /></el-icon>
              </el-button>
              <el-button type="danger" link @click="deleteHistory(item.id)">
                删除
              </el-button>
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ArrowRight } from '@element-plus/icons-vue'

const filterType = ref('all')

// 模拟数据 (后续对接后端 API)
const historyData = ref([
  {
    id: 1,
    rumorId: 101,
    type: 'evaluate',
    content: '吃大蒜可以预防新冠病毒，每天吃三颗效果更佳。',
    score: 0.92,
    date: '2026-04-15',
    time: '14:20:05'
  },
  {
    id: 2,
    rumorId: 102,
    type: 'view',
    content: '关于某地区自来水含氯量超标的传闻。',
    date: '2026-04-14',
    time: '10:15:30'
  }
])

const filteredData = computed(() => {
  if (filterType.value === 'all') return historyData.value
  return historyData.value.filter(item => item.type === filterType.value)
})

const getScoreColor = (score) => {
  if (score > 0.8) return '#F56C6C'
  if (score > 0.4) return '#E6A23C'
  return '#67C23A'
}

const viewDetails = (id) => { console.log('查看谣言 ID:', id) }
const deleteHistory = (id) => { console.log('删除记录 ID:', id) }
const goBack = () => window.history.back()
</script>

<style scoped>
.history-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
  background-color: #ffffff;
  min-height: 100vh;
}

.filter-bar {
  margin: 30px 0;
  display: flex;
  justify-content: center;
}

.history-card {
  border-radius: 12px;
  border: 1px solid #f0f0f0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.activity-time {
  font-size: 13px;
  color: #909399;
}

.rumor-text {
  font-size: 16px;
  line-height: 1.5;
  color: #303133;
  margin: 0 0 10px 0;
  /* 多行截断 */
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.score-badge {
  background: #fdf6ec;
  padding: 8px 12px;
  border-radius: 6px;
  display: inline-block;
  margin-bottom: 10px;
}

.score-badge .label { font-size: 13px; color: #606266; }
.score-badge .value { font-weight: bold; font-size: 15px; }

.card-footer {
  border-top: 1px solid #f5f7fa;
  padding-top: 12px;
  margin-top: 10px;
  display: flex;
  justify-content: space-between;
}
</style>
