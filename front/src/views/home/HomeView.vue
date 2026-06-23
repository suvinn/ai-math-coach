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

const router = useRouter()
const auth = useAuthStore()
const quiz = useQuizStore()
const { toast, showToast } = useToast()

const userName = ref(auth.user?.name || '')
const diagnosing = ref(false)

onMounted(async () => {
  // 대시보드에서 유저 이름 가져오기 (이미 있으면 그대로 사용)
  try {
    const data = unwrap(await api.get('/users/me/dashboard'))
    userName.value = data?.user?.name || userName.value
  } catch {
    // 실패해도 화면은 그대로 (이름만 비거나 기존값 유지)
  }
})

// 빠른 진단 — 단원 선택 없이 전체 단원에서 골고루 20문제를 뽑아 바로 풀이 화면으로
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

// 오늘의 추천 학습 → 퀴즈 설정으로 (추천 prefill 모드)
function goTodayRec() {
  router.push({ path: '/quiz/setup', query: { mode: 'today' } })
}
</script>

<template>
  <SidebarShell tab="home">
    <template #actions>
      <button class="app-iconbtn" aria-label="알림">
        <WdsIcon name="bell" :size="22" />
        <span class="dot" />
      </button>
    </template>

    <Toast :toast="toast" />

    <div class="page">
      <div class="page-head">
        <div class="wds-body-2 assistive">안녕하세요, {{ userName || '학생' }}님</div>
        <div class="title home-headline">
          오늘은 <span style="color: var(--suql-accent)">내 약점</span>부터 찾아볼까요?
        </div>
      </div>

      <div class="stack-16">
        <!-- 진단 추천 — 가장 강조 -->
        <div class="diag-card">
          <div class="diag-card-text">
            <div class="row" style="gap: 6px; margin-bottom: 10px">
              <WdsIcon name="sparkle" :size="18" color="#fff" />
              <span class="diag-eyebrow">AI 빠른 진단</span>
            </div>
            <div class="diag-title">20문제로 내 취약 유형 찾기</div>
            <div class="wds-body-2 diag-sub">전체 단원에서 골고루 출제돼요</div>
          </div>
          <WdsButton
            variant="primary"
            size="large"
            icon-right="arrow-right"
            :disabled="diagnosing"
            @click="startDiagnosis"
          >
            {{ diagnosing ? '준비 중…' : '진단 시작하기' }}
          </WdsButton>
        </div>

        <!-- 오늘의 추천 진입점 -->
        <button class="tap-row today-row" @click="goTodayRec">
          <span class="today-ico">
            <WdsIcon name="sparkle" :size="20" color="var(--suql-accent)" />
          </span>
          <div style="flex: 1">
            <div class="wds-label-1" style="font-weight: 700">오늘의 추천 학습</div>
            <div class="wds-caption-1 assistive" style="margin-top: 2px">정체된 유형부터 짧게 풀어보기</div>
          </div>
          <WdsIcon name="chevron-right" :size="20" color="var(--label-assistive)" />
        </button>
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

/* 진단 카드 — 가로로 트인 웹 히어로 (폰 카드의 박스 느낌 제거) */
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
  opacity: 0.85;
  white-space: nowrap;
}
.diag-title {
  font: var(--weight-bold) 22px/1.4 var(--font-sans);
  letter-spacing: -0.02em;
}
.diag-sub {
  opacity: 0.7;
  margin-top: 8px;
}

/* 오늘의 추천 행 */
.today-row {
  padding: 14px;
  margin: 0;
  border-radius: 16px;
  box-shadow: inset 0 0 0 1px var(--line-normal-normal);
}
.today-row:hover {
  background: var(--fill-alternative);
}
.today-ico {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  flex: none;
  background: var(--blue-95);
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>