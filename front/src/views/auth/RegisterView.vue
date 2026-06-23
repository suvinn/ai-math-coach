<!-- 📄 src/views/auth/RegisterView.vue -->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useQuizStore } from '@/stores/quiz'
import { useToast } from '@/composables/useToast'
import api, { unwrap } from '@/api'
import AuthShell from '@/components/common/AuthShell.vue'
import WdsField from '@/components/common/WdsField.vue'
import WdsButton from '@/components/common/WdsButton.vue'

const router = useRouter()
const auth = useAuthStore()
const quiz = useQuizStore()
const { toast, showToast } = useToast()

// ── 스텝 ──────────────────────────────────────────────
// step 1: 기본 정보 (이름·아이디·비밀번호)
// step 2: 현재 진도 입력 (학년·대단원·중단원) — 건너뛰기 가능
const step = ref(1)

// step 1
const name            = ref('')
const username        = ref('')
const password        = ref('')
const passwordConfirm = ref('')

// step 2
const GRADES = ['중1', '중2', '중3', '고1', '고2', '고3']
const grade         = ref('중2')
const chapterMajor  = ref('')   // 대단원 선택값
const chapterMiddle = ref('')   // 중단원 선택값

const chapters       = ref([])  // [{ chapter_major, chapter_middles: [{ chapter_middle }] }]
const middleOptions  = computed(() => {
  const found = chapters.value.find(c => c.chapter_major === chapterMajor.value)
  return found ? found.chapter_middles.map(m => m.chapter_middle) : []
})

onMounted(async () => {
  try {
    const data = unwrap(await api.get('/chapters'))
    chapters.value = data || []
  } catch { /* 실패해도 건너뛰기로 진행 가능 */ }
})

function selectMajor(major) {
  chapterMajor.value  = major
  chapterMiddle.value = ''  // 중단원 초기화
}

// ── step 1 검증 → step 2로 ────────────────────────────
function goStep2() {
  if (!name.value.trim() || !username.value.trim() || !password.value) {
    showToast('모든 항목을 입력해주세요', 'negative', 'circle-exclamation')
    return
  }
  if (password.value !== passwordConfirm.value) {
    showToast('비밀번호가 일치하지 않아요', 'negative', 'circle-exclamation')
    return
  }
  step.value = 2
}

// ── 최종 가입 ─────────────────────────────────────────
const loading = ref(false)

async function onRegister(skip = false) {
  loading.value = true
  try {
    const registerData = await auth.register(
      username.value, password.value, name.value,
      skip ? {} : {
        grade:         grade.value,
        chapterMajor:  chapterMajor.value  || undefined,
        chapterMiddle: chapterMiddle.value || undefined,
      }
    )

    // 자동 로그인
    await auth.login(username.value, password.value)

    // 진단 세션이 백엔드에서 생성됐으면 → 바로 퀴즈 풀이로
    if (!skip && registerData.diagnosis_session_id) {
      const sid = registerData.diagnosis_session_id
      const loaded = unwrap(await api.get(`/quiz/sessions/${sid}/problems`))
      quiz.startSession({
        id:          sid,
        type:        'diagnosis',
        problemList: loaded.problems || [],
      })
      if (loaded.problems?.length) {
        router.push('/quiz/play')
        return
      }
    }

    router.push('/')
  } catch (e) {
    const status = e?.response?.status
    let msg = e?.response?.data?.message || '회원가입에 실패했어요'
    if (status === 409) msg = '이미 존재하는 아이디입니다'
    showToast(msg, 'negative', 'circle-exclamation')
    // 에러가 났으면 step 1로 돌아가서 다시 입력할 수 있게
    step.value = 1
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AuthShell :toast="toast">

    <!-- ── STEP 1: 기본 정보 ── -->
    <template v-if="step === 1">
      <div class="row register-head">
        <button class="app-iconbtn" @click="router.push('/login')" aria-label="뒤로">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M15 5l-7 7 7 7" />
          </svg>
        </button>
        <span class="wds-headline-2" style="font-weight: 700">회원가입</span>
      </div>

      <div class="step-indicator">
        <span class="step-dot active" /><span class="step-dot" />
      </div>

      <div class="stack-16">
        <WdsField v-model="name"            label="이름"        placeholder="이름을 입력하세요" />
        <WdsField v-model="username"        label="아이디"      placeholder="사용할 아이디를 입력하세요" autocomplete="username" />
        <WdsField v-model="password"        label="비밀번호"    type="password" placeholder="비밀번호를 입력하세요"      autocomplete="new-password" />
        <WdsField v-model="passwordConfirm" label="비밀번호 확인" type="password" placeholder="비밀번호를 다시 입력하세요" autocomplete="new-password" @enter="goStep2" />
      </div>

      <WdsButton variant="primary" size="large" block icon-right="arrow-right" @click="goStep2">
        다음
      </WdsButton>
    </template>

    <!-- ── STEP 2: 현재 진도 입력 ── -->
    <template v-else>
      <div class="row register-head">
        <button class="app-iconbtn" @click="step = 1" aria-label="뒤로">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M15 5l-7 7 7 7" />
          </svg>
        </button>
        <span class="wds-headline-2" style="font-weight: 700">현재 진도</span>
      </div>

      <div class="step-indicator">
        <span class="step-dot" /><span class="step-dot active" />
      </div>

      <p class="wds-body-2 assistive" style="margin: 0">
        지금 배우고 있는 단원을 알려주시면<br />
        딱 맞는 <strong style="color: var(--label-normal)">10문제 빠른 진단</strong>을 바로 시작해드려요.
      </p>

      <!-- 학년 -->
      <div class="field-section">
        <div class="field-label">학년</div>
        <div class="chip-row">
          <button
            v-for="g in GRADES"
            :key="g"
            class="chip"
            :class="{ active: grade === g }"
            @click="grade = g"
          >{{ g }}</button>
        </div>
      </div>

      <!-- 대단원 -->
      <div class="field-section">
        <div class="field-label">대단원 <span class="label-optional">(선택)</span></div>
        <div v-if="chapters.length" class="chip-row wrap">
          <button
            v-for="c in chapters"
            :key="c.chapter_major"
            class="chip"
            :class="{ active: chapterMajor === c.chapter_major }"
            @click="selectMajor(c.chapter_major)"
          >{{ c.chapter_major }}</button>
        </div>
        <p v-else class="wds-caption-1 assistive">단원 목록을 불러오는 중…</p>
      </div>

      <!-- 중단원 (대단원 선택 시에만) -->
      <div v-if="chapterMajor && middleOptions.length" class="field-section">
        <div class="field-label">중단원 <span class="label-optional">(선택)</span></div>
        <div class="chip-row wrap">
          <button
            v-for="m in middleOptions"
            :key="m"
            class="chip"
            :class="{ active: chapterMiddle === m }"
            @click="chapterMiddle = m"
          >{{ m }}</button>
        </div>
      </div>

      <div class="stack-10">
        <WdsButton
          variant="primary"
          size="large"
          block
          icon-right="arrow-right"
          :disabled="loading"
          @click="onRegister(false)"
        >
          {{ loading ? '가입 중…' : '가입하고 진단 시작하기' }}
        </WdsButton>
        <WdsButton
          variant="text"
          size="large"
          block
          :disabled="loading"
          @click="onRegister(true)"
        >
          건너뛰고 시작하기
        </WdsButton>
      </div>
    </template>

  </AuthShell>
</template>

<style scoped>
.register-head { gap: 4px; }

.step-indicator {
  display: flex;
  gap: 6px;
  align-items: center;
}
.step-dot {
  width: 6px;
  height: 6px;
  border-radius: 99px;
  background: var(--line-normal-normal);
  transition: width 0.2s, background 0.2s;
}
.step-dot.active {
  width: 18px;
  background: var(--suql-accent);
}

.field-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.field-label {
  font: var(--weight-semibold) 13px/1 var(--font-sans);
  color: var(--label-alternative);
}
.label-optional {
  font-weight: var(--weight-regular);
  color: var(--label-assistive);
}

.chip-row {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 2px;
}
.chip-row.wrap { flex-wrap: wrap; overflow-x: visible; }

.chip {
  flex: none;
  padding: 7px 14px;
  border-radius: 99px;
  border: 1.5px solid var(--line-normal-normal);
  background: transparent;
  font: var(--weight-medium) 13px/1 var(--font-sans);
  color: var(--label-alternative);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s, color 0.15s;
  white-space: nowrap;
}
.chip.active {
  border-color: var(--suql-accent);
  background: var(--blue-99);
  color: var(--suql-accent);
  font-weight: var(--weight-semibold);
}

.stack-10 { display: flex; flex-direction: column; gap: 10px; }
</style>