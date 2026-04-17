import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user' // 假设你的 store 路径
import { ElMessage } from 'element-plus'

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()

  // 1. 检查路由是否需要登录
  if (to.meta.requiresAuth) {
    // 确保用户信息已从后端同步（如果是初次加载或刷新页面）
    if (!userStore.isLoggedIn) {
      ElMessage.warning('请先登录以访问此页面')
      return next({ path: '/login', query: { redirect: to.fullPath } })
    }

    // 2. 角色权限校验 (管理员=1, 用户=0)
    const requiredRole = to.meta.role || 0
    const userRole = userStore.role

    if (userRole < requiredRole) {
      ElMessage.error('权限不足：该页面仅限管理员访问')
      return next({ path: '/' }) // 拦截并退回首页
    }
  }

  next() // 校验通过，放行
})

export default router

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../views/HomeView.vue'),
      meta: {
        requiresAuth: true,
        role: 0 // 登录用户即可进入
      }
    },
    {
      path: '/main',
      name: 'main',
      component: () => import('../views/MainLayout.vue'),
      meta: {
        requiresAuth: true,
        role: 0 // 登录用户即可进入
      }
    },
    {
      path: '/person_center',
      name: 'PersonCenter',
      component: () => import('../views/PersonCenter.vue'),
      meta: {
        requiresAuth: true,
        role: 0 // 登录用户即可进入
      }
    },
    {
      path: '/quickly_look',
      name: 'quickly_look',
      component: () => import('../views/QuicklyLookView.vue'),
      meta: {
        requiresAuth: true,
        role: 0 // 登录用户即可进入
      }
    },
    {
      path: '/data_analysis',
      name: 'data_analysis',
      component: () => import('../views/DataAnalysis.vue'),
      meta: {
        requiresAuth: true,
        role: 0 // 登录用户即可进入
      }
    },
    {
      path: '/admin/users',
      component: () => import('../views/admin/UserManagement.vue'),
      meta: {
        requiresAuth: true,
        role: 1 // 只有管理员能进入
      }
    },
    {
      path: '/history',
      component: () => import('../views/HistoryQueryOrBrows.vue'),
      meta: {
        requiresAuth: true,
        role: 0 // 登录用户即可进入
      }
  }
  ],
})

export default router
