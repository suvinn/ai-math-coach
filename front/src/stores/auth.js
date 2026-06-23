// 📄 src/stores/auth.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api, { unwrap } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)      // { username, name, grade, current_chapter_major, current_chapter_middle }
  const checked = ref(false)  // 최초 /auth/me 확인 완료 여부

  const isLoggedIn = computed(() => !!user.value)

  async function login(username, password) {
    const res = await api.post('/auth/login', { username, password })
    user.value = unwrap(res)
    return user.value
  }

  // grade, current_chapter_major, current_chapter_middle 는 선택 입력
  // 반환값: { username, name, diagnosis_session_id? }
  async function register(username, password, name, { grade, chapterMajor, chapterMiddle } = {}) {
    const payload = { username, password, first_name: name }
    if (grade)         payload.grade                  = grade
    if (chapterMajor)  payload.current_chapter_major  = chapterMajor
    if (chapterMiddle) payload.current_chapter_middle = chapterMiddle

    const res = await api.post('/auth/register', payload)
    return unwrap(res)   // { username, name, diagnosis_session_id? }
  }

  async function logout() {
    try { await api.post('/auth/logout') } finally { user.value = null }
  }

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