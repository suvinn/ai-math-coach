<!-- 📄 src/views/quiz/CoachingView.vue -->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api, { unwrap } from '@/api'
import { useQuizStore } from '@/stores/quiz'
import { useToast } from '@/composables/useToast'
import FocusShell from '@/components/common/FocusShell.vue'
import WdsIcon from '@/components/common/WdsIcon.vue'
import WdsButton from '@/components/common/WdsButton.vue'
import InlineTex from '@/components/common/InlineTex.vue'

const router = useRouter()
const quiz   = useQuizStore()
const { toast, showToast } = useToast()

if (!quiz.sessionId) router.replace('/')

const loading  = ref(true)
const report   = ref(null)

onMounted(async () => {
  try {
    const data = unwrap(await api.get(`/quiz/sessions/${quiz.sessionId}/recommendations`))
    report.value = data
  } catch {
    showToast('코칭 정보를 불러오지 못했어요', 'negative', 'circle-exclamation')
  } finally {
    loading.value = false
  }
})

const groupedRecs = computed(() => {
  if (!report.value?.recommendations?.length) return []
  const byRank = new Map()
  for (const r of report.value.recommendations) {
    if (!byRank.has(r.rank)) byRank.set(r.rank, [])
    byRank.get(r.rank).push(r)
  }
  return [...byRank.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([rank, items]) => ({ rank, items }))
})

const hasWeakSubtypes = computed(() => !!report.value?.weak_subtypes?.length)

function startReview() {
  if (!report.value?.weak_subtypes?.length) return
  // 원본 세션 id 보존(재도전 시 오답 조회용) + 약점 유형 Top3를 순서대로 도는 오답 루프 상태 구성
  quiz.parentSessionId = quiz.sessionId
  quiz.setupReviewLoop(report.value)
  router.push('/review/play')
}
</script>

<template>
  <FocusShell title="AI 코칭" :toast="toast" @back="router.push('/quiz/result')">
    <div v-if="loading" class="coaching-loading">
      <p class="assistive">AI가 분석 중이에요…</p>
    </div>

    <div v-else-if="report" class="stack-16">
      <div class="ai-bubble">
        <div class="ai-head">
          <WdsIcon name="sparkle" :size="18" />
          <span class="wds-label-1" style="font-weight:700">AI 코칭</span>
        </div>
        <p class="wds-body-2" style="margin:0">{{ report.ai_feedback }}</p>
      </div>

      <div v-for="group in groupedRecs" :key="group.rank" class="stack-8">
        <div class="wds-label-1" style="font-weight:700">{{ group.items[0].problem_subtype }}</div>
        <button v-for="rec in group.items" :key="rec.problem_id" class="tap-row rec-row">
          <div style="flex:1">
            <div class="wds-caption-1"><InlineTex :text="rec.question_text" /></div>
            <div class="wds-caption-2 assistive" style="margin-top:4px">{{ rec.reason }}</div>
          </div>
        </button>
      </div>
    </div>

    <template #foot>
      <WdsButton
        v-if="hasWeakSubtypes"
        variant="primary" size="large" block icon-right="arrow-right"
        @click="startReview"
      >
        보완 풀이 시작하기
      </WdsButton>
      <WdsButton v-else variant="secondary" size="large" block @click="router.push('/')">
        홈으로
      </WdsButton>
    </template>
  </FocusShell>
</template>

<style scoped>
.coaching-loading { flex:1; display:flex; align-items:center; justify-content:center; padding:60px 0; }
.rec-row { padding:12px 14px; margin:0; border-radius:14px; box-shadow: inset 0 0 0 1px var(--line-normal-normal); }
</style>