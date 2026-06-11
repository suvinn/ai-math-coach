import { createRouter, createWebHistory } from 'vue-router'

import LoginView from '@/views/LoginView.vue'
import RegisterView from '@/views/RegisterView.vue'
import HomeView from '@/views/HomeView.vue'
import QuizView from '@/views/QuizView.vue'
import ResultView from '@/views/ResultView.vue'
import AnalysisView from '@/views/AnalysisView.vue'
import HistoryView from '@/views/HistoryView.vue'

const routes = [
  {
    path: '/',
    redirect: '/login',
  },
  {
    path: '/login',
    name: 'login',
    component: LoginView,
  },
  {
    path: '/register',
    name: 'register',
    component: RegisterView,
  },
  {
    path: '/home',
    name: 'home',
    component: HomeView,
  },
  {
    path: '/quiz/:sessionId',
    name: 'quiz',
    component: QuizView,
    props: true,
  },
  {
    path: '/result/:sessionId',
    name: 'result',
    component: ResultView,
    props: true,
  },
  {
    path: '/analysis/:sessionId',
    name: 'analysis',
    component: AnalysisView,
    props: true,
  },
  {
    path: '/history',
    name: 'history',
    component: HistoryView,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router