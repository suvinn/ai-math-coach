<!-- 📄 src/views/quiz/QuizResultView.vue -->
<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useQuizStore } from '@/stores/quiz'
import FocusShell from '@/components/common/FocusShell.vue'
import ScoreRing from '@/components/common/ScoreRing.vue'
import WeakRow from '@/components/common/WeakRow.vue'
import WdsButton from '@/components/common/WdsButton.vue'

const router = useRouter()
const quiz = useQuizStore()

// 세션 결과가 없으면(직접 URL 진입 등) 홈으로 돌려보냄
if (!quiz.submitResult) {
  router.replace('/')
}

const result = computed(() => quiz.submitResult)
const pct = computed(() => Math.round((result.value?.accuracy || 0) * 100))
const allCorrect = computed(() => result.value && result.value.score === result.value.total)

const tones = ['var(--status-negative)', 'var(--status-cautionary)', 'var(--label-assistive)']

// 취약 유형 top3 — 백엔드 QuizSessionAnalysisView와 동일한 집계 로직(틀린 비율 높은 순)
const weakSubtypes = computed(() => {
  if (!result.value || allCorrect.value) return []
  const stats = {}
  for (const r of result.value.results) {
    const s = (stats[r.problem_subtype] ||= { wrong: 0, total: 0 })
    s.total += 1
    if (!r.is_correct) s.wrong += 1
  }
  return Object.entries(stats)
    .filter(([, s]) => s.wrong > 0)
    .sort((a, b) => b[1].wrong / b[1].total - a[1].wrong / a[1].total)
    .slice(0, 3)
    .map(([subtype, s], i) => ({
      rank: i + 1,
      name: subtype,
      pct: Math.round(((s.total - s.wrong) / s.total) * 100),
      tone: tones[i],
    }))
})
</script>

<template>
  <FocusShell title="결과" :back="false">
    <div v-if="result" class="stack-16 result-body">
      <div class="result-hero">
        <ScoreRing :pct="pct" :label="`${result.score} / ${result.total} 문제`" />
      </div>

      <div v-if="allCorrect" class="verdict" data-ok="true">
        🎉 전부 맞혔어요! 다음 단계로 넘어가볼까요?
      </div>

      <div v-else class="stack-12">
        <div class="wds-label-1" style="font-weight: 700">놓친 유형</div>
        <div class="stack-16">
          <WeakRow
            v-for="w in weakSubtypes"
            :key="w.name"
            :rank="w.rank"
            :name="w.name"
            :pct="w.pct"
            :tone="w.tone"
          />
        </div>
      </div>
    </div>

    <template #foot>
      <div class="play-foot">
        <WdsButton variant="secondary" size="large" @click="router.push('/')">
          홈으로
        </WdsButton>
        <WdsButton variant="primary" size="large" block icon-right="arrow-right" @click="router.push('/quiz/coaching')">
          AI 코칭 보러가기
        </WdsButton>
      </div>
    </template>
  </FocusShell>
</template>

<style scoped>
.result-body {
  align-items: center;
  text-align: center;
}
.result-hero {
  display: flex;
  justify-content: center;
  margin-top: 12px;
}
.result-body .stack-12 {
  width: 100%;
  text-align: left;
}
.play-foot {
  display: flex;
  gap: 10px;
}
</style>
