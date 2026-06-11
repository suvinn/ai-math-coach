<template>
  <section class="page auth-page">
    <div class="page-header">
      <p class="eyebrow">AI Math Coach</p>
      <h1>회원가입</h1>
      <p class="description">
        학습 기록을 저장하기 위해 계정을 만들어주세요.
      </p>
    </div>

    <form class="auth-form" @submit.prevent="handleRegister">
      <div class="form-group">
        <label>이름</label>
        <input
          v-model.trim="name"
          type="text"
          placeholder="이름을 입력하세요"
          autocomplete="name"
        />
      </div>

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
          autocomplete="new-password"
        />
      </div>

      <p v-if="errorMessage" class="form-error">
        {{ errorMessage }}
      </p>

      <button class="primary-button" type="submit" :disabled="isSubmitting">
        {{ isSubmitting ? '가입 중...' : '회원가입' }}
      </button>
    </form>

    <p class="auth-link">
      이미 계정이 있다면
      <RouterLink to="/login">로그인</RouterLink>
    </p>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const name = ref('')
const username = ref('')
const password = ref('')
const errorMessage = ref('')
const isSubmitting = ref(false)

const handleRegister = async () => {
  errorMessage.value = ''

  if (!name.value || !username.value || !password.value) {
    errorMessage.value = '이름, 아이디, 비밀번호를 모두 입력해주세요.'
    return
  }

  isSubmitting.value = true

  try {
    await authStore.registerUser({
      name: name.value,
      username: username.value,
      password: password.value,
    })

    router.push('/home')
  } catch (error) {
    console.error(error)
    errorMessage.value =
      error.response?.data?.message || '회원가입에 실패했습니다.'
  } finally {
    isSubmitting.value = false
  }
}
</script>