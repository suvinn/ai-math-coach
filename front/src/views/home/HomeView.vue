<!-- 📄 src/views/home/HomeView.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api, { unwrap } from '@/api'
import { useAuthStore } from '@/stores/auth'
import AppShell from '@/components/common/AppShell.vue'
import Logo from '@/components/common/Logo.vue'
import WdsIcon from '@/components/common/WdsIcon.vue'
import WdsButton from '@/components/common/WdsButton.vue'

const router = useRouter()
const auth = useAuthStore()

const userName = ref(auth.user?.name || '')

onMounted(async () => {
  // 대시보드에서 유저 이름 가져오기 (이미 있으면 그대로 사용)
  try {
    const data = unwrap(await api.get('/users/me/dashboard'))
    userName.value = data?.user?.name || userName.value
  } catch {
    // 실패해도 화면은 그대로 (이름만 비거나 기존값 유지)
  }
})

// 빠른 진단 시작 → 퀴즈 설정으로 (진단 모드)
function startDiagnosis() {
  router.push({ path: '/quiz/setup', query: { mode: 'diag' } })
}

// 오늘의 추천 학습 → 퀴즈 설정으로 (추천 prefill 모드)
function goTodayRec() {
  router.push({ path: '/quiz/setup', query: { mode: 'today' } })
}
</script>

<template>
  <AppShell tab="home">
    <div class="ph-appbar">
      <Logo />
      <span class="spacer" />
      <button class="ph-iconbtn" aria-label="알림" style="position: relative">
        <WdsIcon name="bell" :size="22" />
        <span class="bell-dot" />
      </button>
    </div>

    <div class="ph-body">
      <div>
        <div class="wds-body-2 assistive">안녕하세요, {{ userName || '학생' }}님</div>
        <div class="home-headline">
          오늘은 <span style="color: var(--suql-accent)">내 약점</span>부터<br />찾아볼까요?
        </div>
      </div>

      <!-- 진단 추천 — 가장 강조 -->
      <div class="diag-card">
        <div class="diag-glow" />
        <div class="row" style="gap: 6px; margin-bottom: 10px">
          <WdsIcon name="sparkle" :size="18" color="#fff" />
          <span class="diag-eyebrow">AI 빠른 진단</span>
        </div>
        <div class="diag-title">10문제로 내 취약 유형 찾기</div>
        <div class="wds-body-2 diag-sub">5분이면 충분해요</div>
        <div style="margin-top: 16px; position: relative">
          <WdsButton variant="primary" size="large" block icon-right="arrow-right" @click="startDiagnosis">
            진단 시작하기
          </WdsButton>
        </div>
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
  </AppShell>
</template>

<style scoped>
.bell-dot {
  position: absolute;
  top: 9px;
  right: 10px;
  width: 7px;
  height: 7px;
  border-radius: 4px;
  background: var(--status-negative);
  box-shadow: 0 0 0 2px var(--background-normal-normal);
}
.home-headline {
  font: var(--weight-bold) 23px/1.35 var(--font-sans);
  letter-spacing: -0.02em;
  margin-top: 2px;
}

/* 진단 카드 */
.diag-card {
  border-radius: 20px;
  padding: 20px;
  background: var(--label-normal);
  color: #fff;
  position: relative;
  overflow: hidden;
}
.diag-glow {
  position: absolute;
  right: -24px;
  top: -24px;
  width: 120px;
  height: 120px;
  border-radius: 60px;
  background: rgba(91, 132, 255, 0.25);
}
.diag-eyebrow {
  font: var(--weight-bold) 12px/1 var(--font-sans);
  letter-spacing: 0.06em;
  opacity: 0.85;
  white-space: nowrap;
}
.diag-title {
  font: var(--weight-bold) 20px/1.4 var(--font-sans);
  letter-spacing: -0.02em;
  position: relative;
}
.diag-sub {
  opacity: 0.7;
  margin-top: 8px;
  position: relative;
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