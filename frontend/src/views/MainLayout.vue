<template>
  <el-container class="layout-container">
<!--    折叠后宽度是80px-->
    <el-aside :width="isCollapse ? '80px' : '220px'" class="sidebar">
      <div class="logo-area" :class="{ 'is-collapsed': isCollapse }">
        <el-icon class="logo-icon"><Monitor /></el-icon>
        <span class="logo-text" v-show="!isCollapse">辟谣分析系统</span>
      </div>

      <el-menu
        :default-active="activeMenu"
        class="custom-menu"
        :collapse="isCollapse"
        :collapse-transition="false"
        @select="handleMenuSelect"
      >
        <el-menu-item index="home">
          <el-icon><House /></el-icon>
          <template #title>主页</template>
        </el-menu-item>
        <el-menu-item index="rumors">
          <el-icon><Warning /></el-icon>
          <template #title>速看！辟谣</template>
        </el-menu-item>
        <el-menu-item index="profile" @click="goToPersonCenter">
          <el-icon><User /></el-icon>
          <template #title >个人中心</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container class="main-container">
      <el-header class="header">
        <div class="header-left">
          <el-icon class="toggle-btn" @click="toggleCollapse">
            <Expand v-if="isCollapse" />
            <Fold v-else />
          </el-icon>
        </div>

        <div class="header-right">
          <el-popover
            placement="bottom-end"
            :width="260"
            trigger="click"
            popper-class="user-popover-card"
          >
            <template #reference>
              <div class="user-trigger-wrapper">
                <el-tooltip
                  effect="dark"
                  :content="`${userInfo.role} | ${userInfo.department}`"
                  placement="bottom"
                  :show-after="300"
                >
                  <div class="user-info-trigger">
                    <el-avatar :size="36" :src="userInfo.avatar" class="user-avatar" />
                    <span class="username">{{ userInfo.name }}</span>
                  </div>
                </el-tooltip>
              </div>
            </template>

            <div class="user-card-content">
              <div class="user-card-header">
                <el-avatar :size="72" :src="userInfo.avatar" class="large-avatar" />
                <h3 class="welcome-text">你好，{{ userInfo.name }}</h3>
                <span class="user-role-badge">{{ userInfo.role }}</span>
              </div>
              <div class="user-card-actions">
                <el-button type="primary" plain class="action-btn" @click="handleManageAccount">
                  管理账号
                </el-button>
                <el-button type="danger" plain class="action-btn" @click="handleLogout">
                  退出账号
                </el-button>
              </div>
            </div>
          </el-popover>
        </div>
      </el-header>

      <el-main class="main-content">
        <transition name="fade-transform" mode="out-in">
          <div v-if="activeMenu === 'home'" class="page-wrapper" key="home">
            <div class="search-section">
              <h1 class="search-title">探索真实的世界</h1>
              <div class="search-box">
                <el-input
                  v-model="searchQuery"
                  placeholder="请输入您要查询的事件或关键词..."
                  size="large"
                  class="search-input"
                  @keyup.enter="handleSearch"
                  clearable
                >
                  <template #prefix>
                    <el-icon class="el-input__icon"><Search /></el-icon>
                  </template>
                </el-input>
                <el-button
                  type="primary"
                  size="large"
                  class="search-btn"
                  @click="handleSearch"
                >
                  查询
                </el-button>
              </div>
            </div>

            <div class="content-section">
              <div class="section-header">
                <h3>最新动态</h3>
                <el-link type="primary" :underline="false">查看更多 <el-icon><ArrowRight /></el-icon></el-link>
              </div>

              <el-row :gutter="24">
                <el-col
                  v-for="item in mockData"
                  :key="item.id"
                  :xs="24" :sm="12" :md="8" :lg="6"
                  class="card-col"
                >
                  <el-card shadow="hover" class="info-card">
                    <div class="card-header">
                      <span class="tag" :class="item.status === '已辟谣' ? 'tag-success' : 'tag-warning'">
                        {{ item.status }}
                      </span>
                      <span class="date">{{ item.date }}</span>
                    </div>
                    <h4 class="card-title">{{ item.title }}</h4>
                    <p class="card-desc">{{ item.description }}</p>

                    <div class="card-footer">
                      <el-icon><Link /></el-icon>
                      <a :href="item.url" target="_blank" class="source-link" @click.stop>
                        {{ item.source }}
                      </a>
                    </div>
                  </el-card>
                </el-col>
              </el-row>
            </div>
          </div>

          <div v-else-if="activeMenu === 'rumors'" class="placeholder-page" key="rumors">
            <el-empty description="速看！辟谣板块开发中..." />
          </div>
        </transition>
      </el-main>
    </el-container>

    <el-dialog
      v-model="searchDialogVisible"
      title="搜索结果"
      width="50%"
      class="custom-dialog"
      destroy-on-close
    >
      <div class="dialog-content">
        <p class="search-keyword">关于“<span>{{ searchQuery || '空' }}</span>”的查询结果：</p>
        <div class="empty-state">
          <el-skeleton :rows="4" animated />
          <p class="loading-text">正在从数据库拉取对应内容...</p>
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="searchDialogVisible = false">关 闭</el-button>
        </span>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  House, Warning, User, Search,
  Monitor, ArrowRight, Link,
  Fold, Expand
} from '@element-plus/icons-vue'

// 状态管理
const activeMenu = ref('home')
const searchQuery = ref('')
const searchDialogVisible = ref(false)
const isCollapse = ref(false) // 侧边栏折叠状态
const router = useRouter()

// 模拟用户信息
const userInfo = ref({
  name: '分析师-张三',
  avatar: 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png',
  role: '高级数据分析师',
  department: '信息核查中心'
})

// 侧边栏切换逻辑
const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
}

// 菜单切换逻辑
const handleMenuSelect = (index) => {
  activeMenu.value = index
}

// 用户操作逻辑
const handleManageAccount = () => {
  ElMessage.success('正在进入账号管理界面...')
  activeMenu.value = 'profile'
}

const handleLogout = () => {
  ElMessage.warning('已安全退出账号')
}

// 搜索逻辑
const handleSearch = () => {
  searchDialogVisible.value = true
}

// 模拟后端数据库返回的卡片数据
const mockData = ref([
  {
    id: 1,
    title: '网传“吃加碘盐可以防核辐射”是真的吗？',
    description: '近期部分网络平台上流传“吃加碘盐可以防核辐射”的消息，引发公众关注和部分地区抢购食盐。',
    url: 'https://example.com/article/1',
    source: '中国互联网联合辟谣平台',
    date: '2023-10-15',
    status: '已辟谣'
  },
  {
    id: 2,
    title: '关于“某地将发生7.0级大地震”的紧急说明',
    description: '关于微信群流传的某地即将发生大地震的截图，经地震局核实为彻头彻尾的虚假信息。',
    url: 'https://example.com/article/2',
    source: '国家地震台网',
    date: '2023-10-18',
    status: '已辟谣'
  },
  {
    id: 3,
    title: '喝骨头汤真的能快速补钙吗？',
    description: '传统观念认为吃啥补啥，喝骨头汤能补钙。营养学专家指出骨头汤中的钙极难溶于水。',
    url: 'https://example.com/article/3',
    source: '丁香医生科普',
    date: '2023-10-20',
    status: '疑似谣言'
  },
  {
    id: 4,
    title: '长期喝纯净水会导致身体缺矿物质？',
    description: '人体吸收矿物质的主要途径是日常饮食，而非饮用水。合格的纯净水安全健康。',
    url: 'https://example.com/article/4',
    source: '中国科普博览',
    date: '2023-10-22',
    status: '已辟谣'
  }
])

const goToPersonCenter = () => {
  // 通过 name 跳转（推荐，因为 path 变更时 name 通常不动）
  router.push({ name: 'PersonCenter' })

  // 或者通过 path 跳转
  // router.push('/person_center')
}
</script>

<style scoped>
/* 全局布局 */
.layout-container {
  height: 100vh;
  background-color: #f5f7fa;
}

/* --- 新增/修改：侧边栏及动画样式 --- */
.sidebar {
  background-color: #ffffff;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);
  z-index: 10;
  display: flex;
  flex-direction: column;
  transition: width 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  overflow: hidden; /* 防止折叠时文字换行乱板 */
}


.logo-area {
  height: 60px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
  border-bottom: 1px solid #f0f2f5;
  white-space: nowrap;
  transition: padding 0.3s;
}

.logo-area.is-collapsed {
  padding: 0;
  justify-content: center;
}

.logo-icon {
  font-size: 24px;
  color: #409eff;
  margin-right: 10px;
}

.logo-area.is-collapsed .logo-icon {
  margin-right: 0;
}

.custom-menu {
  border-right: none;
  margin-top: 10px;
}

.custom-menu:not(.el-menu--collapse) {
  width: 220px;
}

.custom-menu .el-menu-item {
  border-radius: 8px;
  margin: 4px 12px;
  height: 48px;
  line-height: 48px;
}

.custom-menu .el-menu-item.is-active {
  background-color: #ecf5ff;
  color: #409eff;
  font-weight: 500;
}

/* 右侧容器 */
.main-container {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

/* --- 新增：顶部 Header 及用户信息栏 --- */
.header {
  height: 60px;
  background-color: #ffffff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
  z-index: 9;
}

.header-left {
  display: flex;
  align-items: center;
}

.toggle-btn {
  font-size: 22px;
  color: #606266;
  cursor: pointer;
  transition: color 0.3s;
  padding: 4px;
}

.toggle-btn:hover {
  color: #409eff;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-trigger-wrapper {
  display: inline-block;
}

.user-info-trigger {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 12px;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
  background-color: transparent;
}

.user-info-trigger:hover {
  background-color: #f0f2f5;
}

.user-avatar {
  border: 1px solid #ebeef5;
}

.username {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

/* 弹出用户卡片内容样式 */
.user-card-content {
  display: flex;
  flex-direction: column;
  padding: 8px;
}

.user-card-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
}

.large-avatar {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border: 2px solid #ffffff;
}

.welcome-text {
  margin: 16px 0 6px 0;
  font-size: 18px;
  color: #303133;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  letter-spacing: 0.5px;
}

.user-role-badge {
  font-size: 12px;
  color: #909399;
  background-color: #f4f4f5;
  padding: 2px 10px;
  border-radius: 10px;
}

.user-card-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 20px;
}

.user-card-actions .action-btn {
  margin-left: 0;
  width: 100%;
  border-radius: 8px;
  height: 36px;
  transition: all 0.3s;
}

/* 主内容区样式 */
.main-content {
  padding: 0;
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
  height: calc(100vh - 60px);
}

.page-wrapper {
  padding: 32px 48px;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}

.placeholder-page {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 搜索区域 */
.search-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0 60px;
}

.search-title {
  font-size: 32px;
  color: #1f2f3d;
  margin-bottom: 30px;
  font-weight: 600;
  letter-spacing: 2px;
}

.search-box {
  display: flex;
  width: 100%;
  max-width: 700px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  transition: all 0.3s;
}

.search-box:hover {
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
}

.search-input {
  flex: 1;
}

.search-input :deep(.el-input__wrapper) {
  box-shadow: none !important;
  border-radius: 8px 0 0 8px;
  padding-left: 20px;
}

.search-btn {
  border-radius: 0 8px 8px 0;
  padding: 0 32px;
  font-size: 16px;
}

/* 内容展示区域及卡片（保持原有样式） */
.content-section {
  margin-top: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.section-header h3 {
  margin: 0;
  font-size: 20px;
  color: #303133;
  font-weight: 600;
}

.card-col {
  margin-bottom: 24px;
}

.info-card {
  border-radius: 12px;
  border: none;
  height: 100%;
  display: flex;
  flex-direction: column;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.info-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1) !important;
}

.info-card :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.tag {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}

.tag-success {
  background-color: #f0f9eb;
  color: #67c23a;
}

.tag-warning {
  background-color: #fdf6ec;
  color: #e6a23c;
}

.date {
  font-size: 13px;
  color: #909399;
}

.card-title {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: #303133;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-desc {
  margin: 0;
  font-size: 14px;
  color: #606266;
  line-height: 1.5;
  flex: 1;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
  display: flex;
  align-items: center;
  font-size: 13px;
  color: #409eff;
}

.card-footer .el-icon {
  margin-right: 6px;
}

.source-link {
  color: #409eff;
  text-decoration: none;
  transition: color 0.2s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.source-link:hover {
  color: #66b1ff;
  text-decoration: underline;
}

/* 弹窗样式 */
.custom-dialog :deep(.el-dialog) {
  border-radius: 12px;
}

.search-keyword {
  margin: 0 0 20px 0;
  font-size: 16px;
  color: #303133;
}

.search-keyword span {
  color: #409eff;
  font-weight: bold;
}

.empty-state {
  padding: 30px;
  background-color: #f8f9fa;
  border-radius: 8px;
  text-align: center;
}

.loading-text {
  margin-top: 20px;
  color: #909399;
  font-size: 14px;
}

/* 页面切换动画 */
.fade-transform-leave-active,
.fade-transform-enter-active {
  transition: all 0.3s;
}

.fade-transform-enter-from {
  opacity: 0;
  transform: translateX(-30px);
}

.fade-transform-leave-to {
  opacity: 0;
  transform: translateX(30px);
}


/* 修复侧边栏折叠时，菜单激活背景被截断的问题 */
.el-menu--collapse .el-menu-item {
  margin: 4px 8px;           /* 减小左右边距，适配 64px 宽度 */
  width: 48px;               /* 限制宽度为 48px，使其成为完美圆角矩形 */
  padding: 0 !important;     /* 清除自带的 padding */
  justify-content: center;   /* 图标水平居中 */
}

/* 隐藏折叠状态下的 tooltip 触发块自带的 padding（Element Plus 内部结构） */
.el-menu--collapse .el-menu-item :deep(.el-tooltip__trigger) {
  padding: 0;
  justify-content: center;
}
</style>
