<template>
  <section class="page auth-page">
    <div class="page-header">
      <p class="eyebrow">AI Math Coach</p>
      <h1>로그인</h1>
      <p class="description">
        계정으로 로그인하고 수학 퀴즈 학습을 이어가세요.
      </p>
    </div>

    <form class="auth-form" @submit.prevent="handleLogin">
      <div class="form-group">
        <label>아이디</label>
        <input
          v-model.trim="username"
          type="text"
          placeholder="아이디를 입력하세요"
          autocomplete="username"
        />
      </div>

      <div class="form-group">
        <label>비밀번호</label>
        <input
          v-model="password"
          type="password"
          placeholder="비밀번호를 입력하세요"
          autocomplete="current-password"
        />
      </div>

      <p v-if="errorMessage" class="form-error">
        {{ errorMessage }}
      </p>

      <button class="primary-button" type="submit" :disabled="isSubmitting">
        {{ isSubmitting ? '로그인 중...' : '로그인' }}
      </button>
    </form>

    <p class="auth-link">
      아직 계정이 없다면
      <RouterLink to="/register">회원가입</RouterLink>
    </p>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const errorMessage = ref('')
const isSubmitting = ref(false)

const handleLogin = async () => {
  errorMessage.value = ''

  if (!username.value || !password.value) {
    errorMessage.value = '아이디와 비밀번호를 모두 입력해주세요.'
    return
  }

  isSubmitting.value = true

  try {
    await authStore.loginUser({
      username: username.value,
      password: password.value,
    })

    router.push('/home')
  } catch (error) {
    console.error(error)
    errorMessage.value =
      error.response?.data?.message || '로그인에 실패했습니다.'
  } finally {
    isSubmitting.value = false
  }
}
</script>