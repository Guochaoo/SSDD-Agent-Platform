/**
 * Vue Router 璺敱閰嶇疆
 * - 鐧诲綍/娉ㄥ唽椤甸潰鏃犻渶璁よ瘉
 * - 鍏朵粬椤甸潰闇€瑕佺櫥褰曞悗鎵嶈兘璁块棶
 * - 璺敱瀹堝崼鑷姩妫€鏌ョ櫥褰曠姸鎬?
 */
import { createRouter, createWebHistory } from 'vue-router'

// 鈹€鈹€ 璺敱瀹氫箟 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginPage.vue'),
    meta: { title: '鐧诲綍', requiresAuth: false },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/RegisterPage.vue'),
    meta: { title: '娉ㄥ唽', requiresAuth: false },
  },

  // 鈹€鈹€ 闇€瑕佺櫥褰曠殑椤甸潰锛堜娇鐢?MainLayout 甯冨眬锛?鈹€鈹€鈹€鈹€鈹€鈹€
  {
    path: '/',
    component: () => import('@/components/layout/MainLayout.vue'),
    redirect: '/chat',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'chat',
        name: 'Chat',
        component: () => import('@/views/ChatPage.vue'),
        meta: { title: '鏅鸿兘瀵硅瘽', icon: 'ChatDotRound' },
      },
      {
        path: 'detection',
        name: 'Detection',
        component: () => import('@/views/DetectionPage.vue'),
        meta: { title: '妫€娴嬪伐浣滃彴', icon: 'Camera' },
      },
      {
        path: 'training',
        name: 'Training',
        component: () => import('@/views/TrainingPage.vue'),
        meta: { title: '妯″瀷璁粌', icon: 'Cpu' },
      },
      {
        path: 'history',
        name: 'History',
        component: () => import('@/views/HistoryPage.vue'),
        meta: { title: '鍘嗗彶璁板綍', icon: 'Clock' },
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/DashboardPage.vue'),
        meta: { title: '鏁版嵁鐪嬫澘', icon: 'DataAnalysis' },
      },
    ],
  },

  // 鈹€鈹€ 404 椤甸潰 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
  {
    path: '/:pathMatch(.*)*',
    redirect: '/login',
  },
]

// 鈹€鈹€ 鍒涘缓璺敱瀹炰緥 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 鈹€鈹€ 璺敱瀹堝崼 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
router.beforeEach((to, from, next) => {
  // 璁剧疆椤甸潰鏍囬
  document.title = to.meta.title
    ? `${to.meta.title} - SSDD Agent Platform`
    : 'SSDD Agent Platform'

  // 妫€鏌ユ槸鍚﹂渶瑕佽璇?
  const token = localStorage.getItem('ssdd_token')
  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth !== false)

  if (requiresAuth && !token) {
    // 闇€瑕佺櫥褰曚絾鏈櫥褰曪紝璺宠浆鍒扮櫥褰曢〉
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else if ((to.path === '/login' || to.path === '/register') && token) {
    // 宸茬櫥褰曠敤鎴疯闂櫥褰?娉ㄥ唽椤碉紝璺宠浆鍒伴椤?
    next('/')
  } else {
    next()
  }
})

export default router
