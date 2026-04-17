<template>
  <div class="layout-master">

    <div class="cell br bb col-1"></div>

    <div class="cell br bb col-2 flex-center logo-cell">
      <img v-if="!isLogoError" :src="logoImg" @error="isLogoError = true" alt="辟谣系统" class="logo" />
      <span v-else class="fallback-logo-text">辟谣系统个人中心</span>
    </div>

    <div class="cell br bb col-3 top-nav-cell">
      <nav class="top-nav">
        <a
          href="javascript:void(0)"
          class="nav-item"
          :class="{ active: $route.path === '/user-center' }"
          @click="router.push('/person_center')"
        >
          用户中心
        </a>
        <a
          href="javascript:void(0)"
          class="nav-item"
          :class="{ active: $route.path === '/history' }"
          @click ="router.push({ path: '/history', query: { id: userInfo.accountId } })"
        >
          历史查询/浏览
        </a>
      </nav>
      <div class="top-right">
        <el-dropdown trigger="click">
          <span class="user-phone-dropdown">
            {{ userInfo.phone || '未登录' }} <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="handleLogout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <div class="cell bb col-4"></div>

    <div class="cell br bb col-1"></div>

    <div class="cell br bb col-2 flex-center">
      <el-icon class="hamburger-icon"><Menu /></el-icon>
    </div>

    <div class="cell br bb col-3 flex-center">
      <span class="page-title">{{ pageTitle }}</span>
    </div>

    <div class="cell bb col-4"></div>

    <div class="cell br col-1 bg-light"></div>

    <div class="cell br col-2 bg-light">
      <aside class="sidebar">
        <div class="menu-group">
          <a class="menu-item" :class="{ active: activeSideNav === 'account' }" @click="switchSideNav('account', '账号信息')">
            账号信息
          </a>
          <a class="menu-item" :class="{ active: activeSideNav === 'rebind' }" @click="switchSideNav('rebind', '换绑手机')">
            换绑手机
          </a>
          <a class="menu-item" :class="{ active: activeSideNav === 'password' }" @click="switchSideNav('password', '修改密码')">
            修改密码
          </a>
        </div>

        <div class="menu-group" style="margin-top: 20px;">
          <div
            class="menu-title"
            @click="isOtherOpen = !isOtherOpen"
            style="cursor: pointer; display: flex; justify-content: space-between; align-items: center;"
          >
            其它
            <el-icon><ArrowDown v-if="!isOtherOpen"/><ArrowUp v-else/></el-icon>
          </div>

          <el-collapse-transition>
            <div v-show="isOtherOpen">
              <a class="menu-item" @click="goBack">
                返回
              </a>
              <a class="menu-item logout-item" style="margin-top: 0;" @click="handleLogout">
                退出登录
              </a>
            </div>
          </el-collapse-transition>
        </div>
      </aside>
    </div>

    <div class="cell br col-3 dynamic-content-box">

      <vue-particles
        id="tsparticles"
        :options="particlesOptions"
        class="particles-bg"
      />

      <transition name="fade" mode="out-in">
        <div v-if="activeSideNav === 'account'" class="panel-wrapper" key="account">
          <div class="info-card">
            <div class="avatar-container">
              <el-avatar :size="120" :src="userInfo.avatar" class="user-avatar">
                <img src="https://cube.elemecdn.com/e/fd/0fc7d20532fdaf769a25683617711png.png" />
              </el-avatar>
            </div>
            <div class="info-details">
              <div class="info-row">
                <span class="info-label">通行证ID:</span>
                <span class="info-value">{{ userInfo.accountId || '加载中...' }}</span>
              </div>
              <div class="divider"></div>
              <div class="info-row">
                <span class="info-label">绑定手机:</span>
                <span class="info-value">{{ userInfo.phone || '加载中...' }}</span>
              </div>
              <div class="divider"></div>
              <div class="info-row">
                <span class="info-label">实名认证:</span>
                <span class="info-value">{{ userInfo.realNameAuth || '加载中...' }}</span>
              </div>
              <div class="divider"></div>
              <div class="info-row">
                <span class="info-label">账号状态:</span>
                <span class="info-value status-normal">[ {{ userInfo.status === 1 ? '正常' : '异常' }} ]</span>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="activeSideNav === 'rebind'" class="panel-wrapper" key="rebind">
          <div class="info-card placeholder-card">
            <el-empty description="换绑手机组件区域" />
          </div>
        </div>

        <div v-else-if="activeSideNav === 'password'" class="panel-wrapper" key="password">
          <div class="info-card placeholder-card">
            <el-empty description="修改密码组件区域" />
          </div>
        </div>
      </transition>
    </div>

    <div class="cell col-4 bg-light"></div>

    <div class="cell bt col-1"></div>
    <div class="cell bt col-2 bg-light"></div>
    <div class="cell bt col-3 bg-light"></div>
    <div class="cell bt col-4"></div>

  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Menu, Service, ArrowDown, ArrowUp } from '@element-plus/icons-vue'
import logoImg from '@/assets/rumor_log.png'
import { useRouter, useRoute } from 'vue-router'

// ================= 状态管理 =================
const activeTopNav = ref('userCenter')
const activeSideNav = ref('account')
const pageTitle = ref('账号信息')
const isOtherOpen = ref(false)
const isLogoError = ref(false) // 监控 Logo 是否加载失败
const router = useRouter()

// 粒子特效参数配置
const particlesOptions = reactive({
  background: { color: { value: "transparent" } },
  fpsLimit: 60,
  particles: {
    color: { value: "#ffffff" },
    links: { color: "#ffffff", distance: 150, enable: true, opacity: 0.5, width: 1 },
    move: { enable: true, speed: 1.5 },
    number: { density: { enable: true, area: 800 }, value: 60 },
    opacity: { value: 0.5 },
    size: { value: { min: 1, max: 3 } },
  },
})

// ================= 用户动态数据 =================
const userInfo = reactive({
  accountId: '', phone: '', realNameAuth: '', status: 1, avatar: ''
})

// ================= 方法与逻辑 =================
const switchSideNav = (navKey, title) => {
  activeSideNav.value = navKey
  pageTitle.value = title
}
const goBack = () => window.history.back()

// ================= 模拟后端 API =================
const apiService = {
  getUserInfo: async () => {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          code: 200,
          data: {
            accountId: '305669147945',
            phone: '166****7235',
            realNameAuth: '付** (5001**********0019)',
            status: 1,
            avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png'
          }
        })
      }, 400)
    })
  },
  logout: async () => Promise.resolve({ code: 200 })
}

onMounted(async () => {
  try {
    const res = await apiService.getUserInfo()
    if (res.code === 200) Object.assign(userInfo, res.data)
  } catch (error) {
    ElMessage.error('数据加载失败')
  }
})

const handleLogout = () => {
  ElMessageBox.confirm('确认退出当前账号?', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
    roundButton: true // 样式优化：使用圆角按钮
  }).then(async () => {
    try {
      // 1. 通知后端销毁 Session 或 Token
      await apiService.logout()

      // 2. 清除本地持久化存储
      // 如果你使用了 Token 验证，通常存储在这里
      localStorage.removeItem('user_token')
      sessionStorage.clear()

      // 3. 重置当前页面的响应式数据 (关键：防止内存泄露或数据残留)
      Object.assign(userInfo, {
        accountId: '',
        phone: '',
        realNameAuth: '',
        status: 1,
        avatar: ''
      })

      // 4. 成功提示
      ElMessage({
        type: 'success',
        message: '已安全退出登录',
        duration: 2000
      })

      // 5. 跳转至登录页
      router.push('/')

    } catch (error) {
      // 处理接口调用失败的情况
      ElMessage.error('退出操作异常，请刷新页面重试')
      console.error('Logout Error:', error)
    }
  }).catch(() => {
    // 用户取消操作，无需额外逻辑
  })
}
</script>

<style scoped>
/* ================= 核心 CSS Grid 布局拓宽 ================= */
.layout-master {
  display: grid;
  /* 【核心修改】：缩小了两侧边距，加宽了中间内容区，使其向左右延展 */
  grid-template-columns: minmax(5vw, 1fr) 240px minmax(800px, 1200px) minmax(5vw, 1fr);
  /* 【核心修改】：增加底部 60px 的行，用于绘制底部网格线 */
  grid-template-rows: 70px 50px 1fr 60px;
  min-height: 100vh;
  background-color: #f5f7fa;
}

.cell { box-sizing: border-box; }
.br { border-right: 1px solid #dcdfe6; }
.bb { border-bottom: 1px solid #dcdfe6; }
.bt { border-top: 1px solid #dcdfe6; } /* 新增顶部边框，用于最后一行 */
.bg-light { background-color: #fdfdfd; }
.flex-center { display: flex; justify-content: center; align-items: center; }

/* ================= 顶部导航区 ================= */
.logo-cell { background-color: #fff; }
.logo { max-width: 140px; max-height: 40px; }

/* 优雅的字体 Logo 降级方案 */
.fallback-logo-text {
  font-size: 18px;
  font-weight: 800;
  color: #0098ea;
  letter-spacing: 1px;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
  text-shadow: 0px 2px 4px rgba(0, 152, 234, 0.2);
}

.top-nav-cell {
  background-color: #fff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 40px;
}

.top-nav { height: 100%; display: flex; gap: 40px; }
.nav-item {
  height: 100%;
  display: flex;
  align-items: center;
  text-decoration: none;
  color: #606266;
  font-size: 16px;
  position: relative;
}
.nav-item.active { color: #333; font-weight: bold; }
.nav-item.active::after {
  content: ''; position: absolute; bottom: 0; left: 0;
  width: 100%; height: 3px; background-color: #0098ea;
}

.top-right { display: flex; gap: 30px; align-items: center; }
.user-phone-dropdown { cursor: pointer; color: #333; display: flex; align-items: center; }

/* ================= 次级标题区 ================= */
.hamburger-icon { font-size: 20px; color: #909399; cursor: pointer; }
.page-title { font-size: 16px; font-weight: bold; color: #333; }

/* ================= 侧边栏菜单 ================= */
.sidebar { padding: 30px 0; height: 100%; background-color: #fdfdfd; }
.menu-group { display: flex; flex-direction: column; }
.menu-title { padding: 0 30px 15px; font-size: 14px; color: #333; font-weight: bold; }

.menu-item {
  padding: 12px 30px;
  font-size: 14px;
  color: #606266;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  border-radius: 0 20px 20px 0;
  margin-right: 15px;
  position: relative;
  display: block;
}

.menu-item:hover { background-color: #f0f5ff; color: #0098ea; transform: translateX(5px); }
.menu-item.active {
  color: #fff;
  background: linear-gradient(90deg, #0098ea, #53c2ff);
  box-shadow: 0 4px 12px rgba(0, 152, 234, 0.3);
  font-weight: bold;
}

.logout-item { margin-top: 20px; }
.logout-item:hover { color: #f56c6c !important; background-color: #fef0f0 !important; }

/* ================= 动态内容区 (绿框范围) ================= */
.dynamic-content-box {
  background-image: url('@/assets/userinfo_background.png');
  background-size: cover;
  background-position: center;
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px;
  overflow: hidden;
}

.particles-bg { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 0; }
.panel-wrapper { width: 100%; display: flex; justify-content: center; z-index: 1; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* ================= 信息卡片 ================= */
.info-card {
  width: 680px;
  background-color: rgba(255, 255, 255, 0.95);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  border-radius: 4px;
  padding: 50px 60px;
  display: flex;
  align-items: center;
  gap: 60px;
  backdrop-filter: blur(4px);
}

.avatar-container {
  flex-shrink: 0; border-radius: 50%; padding: 4px; background: #fff;
  border: 2px solid #9c27b0; box-shadow: 0 4px 12px rgba(156, 39, 176, 0.2);
  display: flex; justify-content: center; align-items: center;
}

.user-avatar { border-radius: 50%; border: 1px solid #ebeef5; }
.info-details { flex: 1; display: flex; flex-direction: column; }
.info-row { display: flex; align-items: center; padding: 12px 0; }
.info-label { width: 100px; color: #606266; font-size: 14px; }
.info-value { color: #303133; font-size: 15px; font-weight: 500; font-family: Arial, sans-serif; }
.divider { height: 1px; background-color: #ebeef5; width: 100%; }
.status-normal { color: #0098ea; font-weight: bold; }
.placeholder-card { justify-content: center; min-height: 300px; }
</style>
