<template>
  <div class="app">
    <header class="app-header">
      <RouterLink to="/home" class="logo">AI Math Coach</RouterLink>

      <nav class="nav">
        <RouterLink to="/home">홈</RouterLink>
        <RouterLink to="/history">학습 이력</RouterLink>

        <template v-if="authStore.isLoggedIn">
          <span class="user-name">{{ displayName }}님</span>
          <button class="nav-button" type="button" @click="handleLogout">
            로그아웃
          </button>
        </template>

        <template v-else>
          <RouterLink to="/login">로그인</RouterLink>
          <RouterLink to="/register">회원가입</RouterLink>
        </template>
      </nav>
    </header>

    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const displayName = computed(() => {
  return (
    authStore.user?.name ||
    authStore.user?.display_name ||
    authStore.user?.first_name ||
    authStore.user?.username ||
    ''
  )
})

const handleLogout = async () => {
  try {
    await authStore.logoutUser()
    router.push('/login')
  } catch (error) {
    console.error(error)
    alert('로그아웃에 실패했습니다.')
  }
}

onMounted(() => {
  authStore.initializeAuth()
})
</script>