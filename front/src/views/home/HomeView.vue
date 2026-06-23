<!-- 📄 src/views/home/HomeView.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api, { unwrap } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useQuizStore } from '@/stores/quiz'
import { useToast } from '@/composables/useToast'
import SidebarShell from '@/components/common/SidebarShell.vue'
import WdsIcon from '@/components/common/WdsIcon.vue'
import WdsButton from '@/components/common/WdsButton.vue'
import Toast from '@/components/common/Toast.vue'
import ReviewResumeBanner from '@/components/review/ReviewResumeBanner.vue'

const router = useRouter()
const auth = useAuthStore()
const quiz = useQuizStore()
const { toast, showToast } = useToast()

const userName = ref(auth.user?.name || '')
const diagnosing = ref(false)

onMounted(async () => {
  try {
    const data = unwrap(await api.get('/users/me/dashboard'))
    userName.value = data?.user?.name || userName.value
  } catch {
    // 실패해도 화면은 그대로
  }
})

async function startDiagnosis() {
  if (diagnosing.value) return
  diagnosing.value = true
  try {
    const res = await quiz.createAndLoad({ mode: 'diagnosis', problem_count: 20 })
    if (!res.problems.length) {
      showToast('출제 가능한 문제가 없어요', 'negative', 'circle-exclamation')
      diagnosing.value = false
      return
    }
    router.push('/quiz/play')
  } catch (e) {
    showToast('진단을 시작하지 못했어요', 'negative', 'circle-exclamation')
    diagnosing.value = false
  }
}

function goTodayRec() {
  router.push({ path: '/quiz/setup', query: { mode: 'today' } })
}
</script>

<template>
  <SidebarShell tab="home">
    <Toast :toast="toast" />

    <div class="page">
      <div class="page-head">
        <div class="wds-body-2 assistive">안녕하세요, {{ userName || '학생' }}님</div>
        <div class="title home-headline">
          오늘은 <span style="color: var(--suql-accent)">내 약점</span>부터 찾아볼까요?
        </div>
      </div>

      <div class="stack-16">
        <!-- 진단 추천 -->
        <div class="diag-card">
          <div class="diag-card-text">
            <div class="row" style="gap: 6px; margin-bottom: 10px">
              <WdsIcon name="sparkle" :size="18" color="rgba(255,255,255,0.7)" />
              <span class="diag-eyebrow">AI 빠른 진단</span>
            </div>
            <div class="diag-title">20문제로 내 취약 유형 찾기</div>
            <div class="wds-body-2 diag-sub">전체 단원에서 골고루 출제돼요</div>
          </div>
          <!-- 흰색 outlined 버튼 — 검정 배경과 대비 -->
          <button
            class="diag-btn"
            :disabled="diagnosing"
            @click="startDiagnosis"
          >
            {{ diagnosing ? '준비 중…' : '진단 시작하기' }}
            <WdsIcon name="arrow-right" :size="16" color="var(--label-normal)" />
          </button>
        </div>

        <!-- 오늘의 추천 진입점 -->
        <button class="today-row" @click="goTodayRec">
          <div class="today-row-text">
            <span class="today-ico">
              <WdsIcon name="sparkle" :size="20" color="var(--suql-accent)" />
            </span>
            <div>
              <div class="today-title">오늘의 추천 학습</div>
              <div class="wds-body-2 assistive" style="margin-top: 4px">단원을 골라 바로 퀴즈 시작하기</div>
            </div>
          </div>
          <WdsButton variant="outlined" size="large" icon-right="arrow-right" @click.stop="goTodayRec">
            퀴즈 설정하기
          </WdsButton>
        </button>

        <!-- 이어하기 배너 -->
        <ReviewResumeBanner />
      </div>
    </div>
  </SidebarShell>
</template>

<style scoped>
.home-headline {
  font: var(--weight-bold) 23px/1.35 var(--font-sans);
  letter-spacing: -0.02em;
  margin-top: 2px;
}

/* 진단 카드 */
.diag-card {
  border-radius: 20px;
  padding: 32px 40px;
  background: var(--label-normal);
  color: #fff;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
}
.diag-card-text { position: relative; }
.diag-eyebrow {
  font: var(--weight-bold) 12px/1 var(--font-sans);
  letter-spacing: 0.06em;
  opacity: 0.75;
  white-space: nowrap;
}
.diag-title {
  font: var(--weight-bold) 22px/1.4 var(--font-sans);
  letter-spacing: -0.02em;
}
.diag-sub {
  opacity: 0.6;
  margin-top: 8px;
}

/* 진단 버튼 — 흰색 배경, 검정 텍스트 */
.diag-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 14px 24px;
  border-radius: 12px;
  border: none;
  background: #fff;
  color: var(--label-normal);
  font: var(--weight-bold) 15px/1 var(--font-sans);
  cursor: pointer;
  flex-shrink: 0;
  transition: opacity 0.15s;
}
.diag-btn:hover { opacity: 0.88; }
.diag-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* 오늘의 추천 행 */
.today-row {
  padding: 32px 40px;
  margin: 0;
  border-radius: 20px;
  border: 2px solid var(--label-normal);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
  width: 100%;
  text-align: left;
  background: transparent;
  cursor: pointer;
  transition: background 0.12s;
}
.today-row:hover { background: var(--fill-alternative); }
.today-row-text {
  display: flex;
  align-items: center;
  gap: 16px;
}
.today-title {
  font: var(--weight-bold) 22px/1.4 var(--font-sans);
  letter-spacing: -0.02em;
  color: var(--label-normal);
}
.today-ico {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  flex: none;
  background: var(--blue-95);
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>