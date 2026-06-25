// 📄 src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/login',    name: 'login',    component: () => import('@/views/auth/LoginView.vue'),    meta: { public: true, shell: 'web' } },
  { path: '/register', name: 'register', component: () => import('@/views/auth/RegisterView.vue'), meta: { public: true, shell: 'web' } },

  { path: '/',            name: 'home',       component: () => import('@/views/home/HomeView.vue'),         meta: { shell: 'web' } },
  { path: '/quiz/setup',  name: 'quiz-setup', component: () => import('@/views/quiz/QuizSetupView.vue'),    meta: { shell: 'web' } },
  { path: '/quiz/play',   name: 'quiz-play',  component: () => import('@/views/quiz/QuizPlayView.vue'),     meta: { shell: 'web' } },
  { path: '/quiz/result', name: 'quiz-result',component: () => import('@/views/quiz/QuizResultView.vue'),   meta: { shell: 'web' } },
  { path: '/quiz/coaching',name:'quiz-coaching',component:() => import('@/views/quiz/CoachingView.vue'),    meta: { shell: 'web' } },

  // 오답 루프: 약점 유형별로 보완1→보완2→재도전을 도는 스텝퍼(ReviewPlayView) → 완료(MasterView)
  { path: '/review/play',    name: 'review-play',    component: () => import('@/views/review/ReviewPlayView.vue'), meta: { shell: 'web' } },
  { path: '/review/master',  name: 'review-master',  component: () => import('@/views/review/MasterView.vue'),    meta: { shell: 'web' } },
  { path: '/review/chat',    name: 'review-chat',    component: () => import('@/views/review/ChatView.vue'),       meta: { shell: 'web' } },

  { path: '/my',         name: 'my-dashboard', component: () => import('@/views/my/DashboardView.vue'), meta: { shell: 'web' } },
  { path: '/my/history', name: 'my-history',   component: () => import('@/views/my/HistoryView.vue'),   meta: { shell: 'web' } },

  { path: '/:pathMatch(.*)*', redirect: '/' },

  {
    path: '/problems/:problem_id/posts',
    name: 'post-list',
    component: () => import('@/views/community/PostListView.vue'),
    meta: { shell: 'web' }
  },
  {
    path: '/problems/:problem_id/posts/:post_id',
    name: 'post-detail',
    component: () => import('@/views/community/PostDetailView.vue'),
    meta: { shell: 'web' }
  },
  ]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.checked) await auth.fetchMe()
  if (!to.meta.public && !auth.isLoggedIn) return { name: 'login' }
  if (to.meta.public && auth.isLoggedIn)   return { name: 'home' }
})

export default router