<!-- 📄 src/views/auth/RegisterView.vue -->
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import AuthShell from '@/components/common/AuthShell.vue'
import WdsField from '@/components/common/WdsField.vue'
import WdsButton from '@/components/common/WdsButton.vue'

const router = useRouter()
const auth = useAuthStore()
const { toast, showToast } = useToast()

const name = ref('')
const username = ref('')
const password = ref('')
const passwordConfirm = ref('')
const loading = ref(false)

async function onRegister() {
  if (!name.value || !username.value || !password.value) {
    showToast('모든 항목을 입력해주세요', 'negative', 'circle-exclamation')
    return
  }
  if (password.value !== passwordConfirm.value) {
    showToast('비밀번호가 일치하지 않아요', 'negative', 'circle-exclamation')
    return
  }
  loading.value = true
  try {
    await auth.register(username.value, password.value, name.value)
    // 가입 성공 → 자동 로그인 후 홈으로
    await auth.login(username.value, password.value)
    router.push('/')
  } catch (e) {
    const status = e?.response?.status
    let msg = e?.response?.data?.message || '회원가입에 실패했어요'
    if (status === 409) msg = '이미 존재하는 아이디입니다'
    showToast(msg, 'negative', 'circle-exclamation')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AuthShell :toast="toast">
    <div class="row register-head">
      <button class="app-iconbtn" @click="router.push('/login')" aria-label="뒤로">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M15 5l-7 7 7 7" />
        </svg>
      </button>
      <span class="wds-headline-2" style="font-weight: 700">회원가입</span>
    </div>

    <div class="stack-16">
      <WdsField
        v-model="name"
        label="이름"
        placeholder="이름을 입력하세요"
      />
      <WdsField
        v-model="username"
        label="아이디"
        placeholder="사용할 아이디를 입력하세요"
        autocomplete="username"
      />
      <WdsField
        v-model="password"
        label="비밀번호"
        type="password"
        placeholder="비밀번호를 입력하세요"
        autocomplete="new-password"
      />
      <WdsField
        v-model="passwordConfirm"
        label="비밀번호 확인"
        type="password"
        placeholder="비밀번호를 다시 입력하세요"
        autocomplete="new-password"
        @enter="onRegister"
      />
    </div>

    <WdsButton variant="primary" size="large" block :disabled="loading" @click="onRegister">
      {{ loading ? '가입 중…' : '가입하고 시작하기' }}
    </WdsButton>
  </AuthShell>
</template>

<style scoped>
.register-head {
  gap: 4px;
}
</style>