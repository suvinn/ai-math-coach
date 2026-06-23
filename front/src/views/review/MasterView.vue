<!-- 📄 src/views/review/MasterView.vue -->
<!-- 완료 (A6): 재도전까지 모두 통과했을 때 표시하는 축하 화면 -->
<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useQuizStore } from '@/stores/quiz'
import FocusShell from '@/components/common/FocusShell.vue'
import WdsButton from '@/components/common/WdsButton.vue'
import WdsIcon from '@/components/common/WdsIcon.vue'

const router = useRouter()
const quiz   = useQuizStore()

// 홈으로 돌아갈 때 store 초기화
function goHome() {
  quiz.reset()
  router.push('/')
}

function goHistory() {
  quiz.reset()
  router.push('/my/history')
}

// 보완 풀이 + 재도전을 거친 약점 유형들 (CoachingView → setupReviewLoop로 저장됨)
const subtypeNames = computed(() => quiz.reviewSubtypes.map((s) => s.problemSubtype))
</script>

<template>
  <FocusShell title="학습 완료" :back="false">
    <div class="master-body">
      <!-- 축하 일러스트 영역 -->
      <div class="confetti-wrap">
        <div class="confetti-ring">
          <WdsIcon name="circle-check" :size="52" color="var(--status-positive)" />
        </div>
      </div>

      <div class="stack-8 center">
        <div class="wds-headline-1 master-title">완료!</div>
        <div v-if="subtypeNames.length" class="wds-body-1 master-sub">
          <span style="color:var(--suql-accent); font-weight:700">{{ subtypeNames.join(', ') }}</span> 유형을<br />
          보완 학습과 재도전까지 마쳤어요 🎉
        </div>
        <div v-else class="wds-body-1 master-sub">
          보완 학습과 재도전을 모두 마쳤어요 🎉
        </div>
      </div>

      <!-- 성취 뱃지 -->
      <div class="badge-row">
        <div class="achieve-badge">
          <WdsIcon name="sparkle" :size="16" color="var(--suql-accent)" />
          <span class="wds-caption-1" style="font-weight:600; color:var(--suql-accent)">오답 루프 완료</span>
        </div>
      </div>

      <div class="master-hint wds-body-2 assistive">
        이 유형은 마이페이지 → 학습 기록에서 다시 확인할 수 있어요.
      </div>
    </div>

    <template #foot>
      <div class="master-foot">
        <WdsButton variant="secondary" size="large" @click="goHistory">
          학습 기록 보기
        </WdsButton>
        <WdsButton variant="primary" size="large" block icon-right="arrow-right" @click="goHome">
          홈으로
        </WdsButton>
      </div>
    </template>
  </FocusShell>
</template>

<style scoped>
.master-body {
  display: flex; flex-direction: column;
  align-items: center; gap: 28px;
  padding: 32px 0;
  text-align: center;
}
.confetti-wrap { position: relative; }
.confetti-ring {
  width: 100px; height: 100px; border-radius: 50%;
  background: var(--green-99, #f0fff4);
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 0 0 12px var(--green-95, #dcfce7);
}
.master-title {
  font: var(--weight-bold) 32px/1.2 var(--font-sans);
  letter-spacing: -0.03em;
}
.master-sub {
  line-height: 1.6;
  color: var(--label-alternative);
}
.center { align-items: center; }
.badge-row { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; }
.achieve-badge {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 14px; border-radius: 99px;
  background: var(--blue-99); border: 1.5px solid var(--suql-accent);
}
.master-hint {
  max-width: 260px; line-height: 1.6;
}
.master-foot { display: flex; gap: 10px; }
</style>