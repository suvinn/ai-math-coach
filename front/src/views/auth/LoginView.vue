<!-- 📄 src/views/auth/LoginView.vue -->
<script setup>
import { computed, ref, unref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import WdsField from '@/components/common/WdsField.vue'
import WdsButton from '@/components/common/WdsButton.vue'
import loginSkyBg from '@/assets/images/login-sky-bg.png'

const router = useRouter()
const auth = useAuthStore()
const { toast, showToast } = useToast()

const username = ref('')
const password = ref('')
const loading = ref(false)

const currentToast = computed(() => unref(toast))
const isToastVisible = computed(() => Boolean(currentToast.value))
const toastMessage = computed(() => currentToast.value?.text || '')
const toastTypeClass = computed(() => `login-toast--${currentToast.value?.tone || 'info'}`)

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
  <main class="login-shell">
    <div class="login-page" :style="{ backgroundImage: `url(${loginSkyBg})` }">
      <section class="login-intro" aria-label="서비스 소개">
        <div class="intro-content">
          <div class="intro-brand" aria-label="WIDN Math">
            <span class="brand-widn">WIDN</span>
            <span class="brand-math">Math</span>
          </div>

          <p class="intro-kicker">What I Don’t Know</p>

          <div class="intro-line"></div>

          <p class="intro-copy">
            내가 어떤 유형을 어려워하는지 모르는 학생들을 위해<br />
            AI가 나의 약점을 찾아, 성장으로 이어줍니다.
          </p>
        </div>
      </section>

      <section class="login-card" aria-label="로그인">
        <div class="card-header">
          <h2 class="card-title">로그인</h2>
          <p class="card-subtitle">WIDN Math에 오신 것을 환영합니다.</p>
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

          <div class="divider">
            <span></span>
            <em>또는</em>
            <span></span>
          </div>

          <WdsButton variant="text" size="large" block @click="router.push('/register')">
            회원가입
          </WdsButton>
        </div>
      </section>
    </div>

    <Transition name="toast-fade">
      <div
        v-if="isToastVisible"
        class="login-toast"
        :class="toastTypeClass"
        role="alert"
      >
        {{ toastMessage }}
      </div>
    </Transition>
  </main>
</template>

<style scoped>
:global(html),
:global(body),
:global(#app) {
  width: 100%;
  height: 100%;
  margin: 0;
}

:global(*) {
  box-sizing: border-box;
}

.login-shell {
  width: 100%;
  height: 100dvh;
  overflow: hidden;
  background: #f8fafc;
}

.login-page {
  /*
    위치 조절은 여기만 바꾸면 됨.
    x: 음수면 로그인 박스 왼쪽, 양수면 오른쪽
    y: 음수면 위, 양수면 아래
  */
  --login-card-x: -13vw;
  --login-card-y: 0px;

  --intro-x: 4vw;
  --intro-y: 0px;

  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  column-gap: clamp(56px, 7vw, 120px);
  align-items: start;
  align-content: center;

  width: 100%;
  height: 100%;
  padding: clamp(52px, 7vh, 84px) clamp(64px, 7vw, 132px);

  overflow: hidden;
  background-repeat: no-repeat;
  background-size: cover;
  background-position: center center;
}

.login-intro {
  position: relative;
  z-index: 2;
  min-height: min(620px, calc(100dvh - 140px));
}

.intro-content {
  position: relative;
  z-index: 3;
  max-width: 680px;
  padding-top: 4px;
  transform: translate(var(--intro-x), var(--intro-y));
}

.intro-brand {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin: 0;
  font-family: var(--font-sans);
  font-weight: 900;
  line-height: 1;
  letter-spacing: -0.065em;
}

.brand-widn {
  font-size: clamp(54px, 5.2vw, 82px);
  color: #ffffff;
  text-shadow:
    0 4px 18px rgba(37, 99, 235, 0.18),
    0 1px 0 rgba(255, 255, 255, 0.25);
}

.brand-math {
  font-size: clamp(54px, 5.2vw, 82px);
  color: #1f64e7;
  text-shadow:
    0 4px 18px rgba(37, 99, 235, 0.16),
    0 1px 0 rgba(255, 255, 255, 0.25);
}

.intro-kicker {
  margin: 12px 0 0;
  font-size: clamp(22px, 2vw, 32px);
  font-weight: 700;
  line-height: 1.15;
  letter-spacing: -0.01em;
  color: rgba(255, 255, 255, 0.96);
  text-shadow: 0 4px 14px rgba(37, 99, 235, 0.16);
}

.intro-line {
  width: min(280px, 34vw);
  height: 1px;
  margin: 18px 0 24px;
  background: linear-gradient(
    90deg,
    rgba(255, 255, 255, 0.95),
    rgba(255, 255, 255, 0.35),
    transparent
  );
}

.intro-copy {
  margin: 0;
  font-size: clamp(18px, 1.45vw, 23px);
  font-weight: 700;
  line-height: 1.6;
  letter-spacing: -0.025em;
  color: rgba(15, 42, 95, 0.84);
}

.login-card {
  position: relative;
  z-index: 4;
  width: 100%;
  padding: 52px 44px 44px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.12);
  backdrop-filter: blur(18px);

  transform: translate(var(--login-card-x), var(--login-card-y));
}

.card-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 34px;
  text-align: center;
}

.card-title {
  margin: 0;
  font: var(--weight-bold) 30px/1.3 var(--font-sans);
  letter-spacing: -0.03em;
  color: var(--label-normal);
}

.card-subtitle {
  margin: 10px 0 0;
  font: var(--weight-medium) 18px/1.45 var(--font-sans);
  color: var(--label-assistive);
}

.auth-actions {
  margin-top: 24px;
}

.divider {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 14px;
  margin: 6px 0 2px;
}

.divider span {
  height: 1px;
  background: var(--line-normal, #e5e7eb);
}

.divider em {
  font: var(--weight-medium) 13px/1 var(--font-sans);
  font-style: normal;
  color: var(--label-assistive);
}

.login-toast {
  position: fixed;
  top: 24px;
  left: 50%;
  z-index: 9999;
  min-width: 280px;
  max-width: min(420px, calc(100vw - 32px));
  padding: 14px 18px;
  border-radius: 14px;
  font: var(--weight-bold) 14px/1.45 var(--font-sans);
  text-align: center;
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.16);
  transform: translateX(-50%);
}

.login-toast--negative {
  color: #dc2626;
  border: 1px solid rgba(239, 68, 68, 0.22);
  background: rgba(254, 242, 242, 0.96);
}

.login-toast--positive {
  color: #2563eb;
  border: 1px solid rgba(37, 99, 235, 0.22);
  background: rgba(239, 246, 255, 0.96);
}

.login-toast--info {
  color: #1f2937;
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: rgba(255, 255, 255, 0.96);
}

.toast-fade-enter-active,
.toast-fade-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}

.toast-fade-enter-from,
.toast-fade-leave-to {
  opacity: 0;
  transform: translate(-50%, -8px);
}

@media (max-width: 1180px) {
  :global(body) {
    overflow: auto;
  }

  .login-shell {
    min-height: 100dvh;
    height: auto;
    overflow-x: hidden;
    overflow-y: auto;
  }

  .login-page {
    --login-card-x: 0px;
    --login-card-y: 0px;

    --intro-x: 0px;
    --intro-y: 0px;

    grid-template-columns: 1fr;
    min-height: 100dvh;
    height: auto;
    padding: 36px 24px;
    background-position: 24% center;
  }

  .login-intro {
    min-height: auto;
    text-align: center;
  }

  .intro-content {
    transform: none;
  }

  .intro-brand {
    justify-content: center;
  }

  .brand-widn,
  .brand-math {
    font-size: 44px;
  }

  .intro-kicker {
    font-size: 22px;
  }

  .intro-line {
    margin: 16px auto 20px;
  }

  .intro-copy {
    font-size: 17px;
    line-height: 1.55;
  }

  .login-card {
    width: min(100%, 420px);
    margin: 36px auto 0;
    padding: 34px 24px 28px;
    border-radius: 24px;
  }
}

@media (max-width: 520px) {
  .login-page {
    padding: 28px 18px;
    background-position: 20% center;
  }

  .brand-widn,
  .brand-math {
    font-size: 38px;
  }

  .intro-copy {
    font-size: 15px;
  }

  .login-card {
    padding: 30px 18px 24px;
  }
}
</style>