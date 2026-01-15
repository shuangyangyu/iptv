import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Status',
      component: () => import('../views/Status.vue'),
    },
    {
      path: '/config',
      name: 'Config',
      component: () => import('../views/Config.vue'),
    },
    {
      path: '/jobs',
      name: 'Jobs',
      component: () => import('../views/Jobs.vue'),
    },
    {
      path: '/logs',
      name: 'Logs',
      component: () => import('../views/Logs.vue'),
    },
    {
      path: '/udpxy',
      name: 'Udpxy',
      component: () => import('../views/Udpxy.vue'),
    },
  ],
  scrollBehavior(to, from, savedPosition) {
    // 如果有保存的滚动位置（浏览器前进/后退），恢复它
    if (savedPosition) {
      return savedPosition
    }
    // 如果是同一个路由（例如刷新页面），保持当前位置
    if (to.path === from.path) {
      return { left: 0, top: window.scrollY }
    }
    // 否则滚动到顶部（新路由）
    return { left: 0, top: 0 }
  },
})

export default router

