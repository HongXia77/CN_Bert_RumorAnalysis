import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'

import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../views/HomeView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/main',
      name: 'main',
      component: () => import('../views/MainLayout.vue'),
      meta: { requiresAuth: true, roles: ['user', 'admin'] },
    },
    {
      path: '/person_center',
      name: 'person-center',
      component: () => import('../views/PersonCenter.vue'),
      meta: { requiresAuth: true, roles: ['user', 'admin'] },
    },
    {
      path: '/quickly_look',
      name: 'quickly-look',
      component: () => import('../views/QuicklyLookView.vue'),
      meta: { requiresAuth: true, roles: ['user', 'admin'] },
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('../views/HistoryQueryOrBrows.vue'),
      meta: { requiresAuth: true, roles: ['user', 'admin'] },
    },
    {
      path: '/rumor_library',
      name: 'rumor-library',
      component: () => import('../views/RumorLibraryView.vue'),
      meta: { requiresAuth: true, roles: ['user', 'admin'] },
    },
    {
      path: '/data_analysis',
      name: 'data-analysis',
      component: () => import('../views/DataAnalysis.vue'),
      meta: { requiresAuth: true, roles: ['admin'] },
    },
    {
      path: '/geo_analysis',
      name: 'geo-analysis',
      component: () => import('../views/GeoAnalysisView.vue'),
      meta: { requiresAuth: true, roles: ['user', 'admin'] },
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('../views/AdminConsole.vue'),
      meta: { requiresAuth: true, roles: ['admin'] },
    },
    {
      path: '/admin/quick_sources',
      name: 'admin-quick-sources',
      component: () => import('../views/QuickSourceAdminView.vue'),
      meta: { requiresAuth: true, roles: ['admin'] },
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

router.beforeEach(async (to) => {
  const userStore = useUserStore()
  userStore.bootstrap()

  if (userStore.token && !userStore.profile) {
    try {
      await userStore.fetchCurrentUser()
    } catch {
      userStore.clearSession()
    }
  }

  if (to.meta.guestOnly && userStore.isLoggedIn) {
    return userStore.isAdmin ? '/admin' : '/main'
  }

  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    ElMessage.warning('请先登录以访问系统内容')
    return '/'
  }

  if (to.meta.roles?.length && !to.meta.roles.includes(userStore.role)) {
    ElMessage.error('当前账号无权访问该页面')
    return userStore.isAdmin ? '/admin' : '/main'
  }

  return true
})

export default router
