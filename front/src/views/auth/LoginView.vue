<!-- 📄 src/views/auth/LoginView.vue -->
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import AuthShell from '@/components/common/AuthShell.vue'
import Logo from '@/components/common/Logo.vue'
import WdsField from '@/components/common/WdsField.vue'
import WdsButton from '@/components/common/WdsButton.vue'

const router = useRouter()
const auth = useAuthStore()
const { toast, showToast } = useToast()

const username = ref('')
const password = ref('')
const loading = ref(false)

async function onLogin() {
  if (!username.value || !password.value) {
    showToast('아이디와 비밀번호를 입력해주세요', 'negative', 'circle-exclamation')
    return
  }
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push('/')
  } catch (e) {
    const msg = e?.response?.data?.message || '로그인에 실패했어요'
    showToast(msg, 'negative', 'circle-exclamation')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AuthShell :toast="toast">
    <div class="auth-hero">
      <Logo :size="40" />
      <p class="auth-tagline">중2 수학, 약점부터 잡아드려요</p>
    </div>

    <div class="stack-16 auth-form">
      <WdsField
        v-model="username"
        label="아이디"
        placeholder="아이디를 입력하세요"
        autocomplete="username"
        @enter="onLogin"
      />
      <WdsField
        v-model="password"
        label="비밀번호"
        type="password"
        placeholder="비밀번호를 입력하세요"
        autocomplete="current-password"
        @enter="onLogin"
      />
    </div>

    <div class="stack-12 auth-actions">
      <WdsButton variant="primary" size="large" block :disabled="loading" @click="onLogin">
        {{ loading ? '로그인 중…' : '로그인' }}
      </WdsButton>
      <WdsButton variant="text" size="large" block @click="router.push('/register')">
        회원가입
      </WdsButton>
    </div>
  </AuthShell>
</template>

<style scoped>
.auth-hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.auth-tagline {
  margin: 0;
  font: var(--weight-medium) 14px/1.4 var(--font-sans);
  color: var(--label-assistive);
}
.auth-actions {
  margin-top: 4px;
}
</style>