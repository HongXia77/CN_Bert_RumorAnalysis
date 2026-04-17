import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../views/HomeView.vue'),
    },
    {
      path: '/main',
      name: 'main',
      component: () => import('../views/MainLayout.vue'),
    },
    {
      path: '/person_center',
      name: 'PersonCenter',
      component: () => import('../views/PersonCenter.vue'),
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('../views/HistoryQueryOrBrows.vue'),
    },
    {
      path: '/quickly_look',
      name: 'quickly_look',
      component: () => import('../views/QuicklyLookView.vue'),
    },
    {
      path: '/data_analysis',
      name: 'data_analysis',
      component: () => import('../views/DataAnalysis.vue'),
    },
  ],
})

export default router
