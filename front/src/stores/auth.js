// 📄 src/stores/auth.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api, { unwrap } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)          // { username, name }
  const checked = ref(false)      // 최초 /auth/me 확인 완료 여부

  const isLoggedIn = computed(() => !!user.value)

  async function login(username, password) {
    const res = await api.post('/auth/login', { username, password })
    user.value = unwrap(res)
    return user.value
  }

  async function register(username, password, name) {
    // 백엔드 RegisterSerializer는 first_name 필드를 name으로 받음
    const res = await api.post('/auth/register', {
      username,
      password,
      first_name: name,
    })
    return unwrap(res)
  }

  async function logout() {
    try {
      await api.post('/auth/logout')
    } finally {
      user.value = null
    }
  }

  // 새로고침 시 로그인 상태 복원
  async function fetchMe() {
    try {
      const res = await api.get('/auth/me')
      user.value = unwrap(res)
    } catch {
      user.value = null
    } finally {
      checked.value = true
    }
  }

  return { user, checked, isLoggedIn, login, register, logout, fetchMe }
})