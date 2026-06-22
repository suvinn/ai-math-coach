<!-- 📄 src/views/review/RedoView.vue -->
<!-- 재도전 (B4): 처음 normal/diagnosis 세션에서 틀렸던 문제를 다시 푼다.
     submitResult.results 에서 is_correct=false 문제만 추려서 한 문항씩 진행.
     모두 맞히면 MasterView로, 하나라도 틀리면 → 해설 다시 보기(ExplainView) -->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuizStore } from '@/stores/quiz'
import { useToast } from '@/composables/useToast'
import api, { unwrap } from '@/api'
import FocusShell from '@/components/common/FocusShell.vue'
import QuizStem from '@/components/quiz/QuizStem.vue'
import QuizOption from '@/components/common/QuizOption.vue'
import InlineTex from '@/components/common/InlineTex.vue'
import WdsButton from '@/components/common/WdsButton.vue'
import WdsField from '@/components/common/WdsField.vue'
import WdsIcon from '@/components/common/WdsIcon.vue'
import { parseCircledOptions } from '@/utils/circledOptions'
import { difficultyTone } from '@/utils/difficulty'

const router = useRouter()
const quiz   = useQuizStore()
const { toast, showToast } = useToast()

// 원본 normal/diagnosis 세션 ID — CoachingView에서 quiz.parentSessionId 로 넘겨줘야 함
// 없으면 현재 sessionId로 폴백
const targetSessionId = quiz.parentSessionId || quiz.sessionId

if (!targetSessionId) router.replace('/')

// ── 오답 문제 로드 ────────────────────────────────────
const loading  = ref(true)
const problems = ref([])   // 틀린 문제 전체 (문제 데이터 포함)

onMounted(async () => {
  try {
    const data = unwrap(await api.get(`/quiz/sessions/${targetSessionId}/wrong-answers`))
    problems.value = data.wrong_problems || []
  } catch {
    showToast('재도전 문제를 불러오지 못했어요', 'negative', 'circle-exclamation')
  } finally {
    loading.value = false
  }
})

// ── 풀이 상태 ────────────────────────────────────────
const idx        = ref(0)
const answer     = ref('')
const selectedLabels = ref([])
const revealed   = ref(false)   // 제출 후 정오답 표시
const results    = ref([])      // { problem_id, is_correct }

const total   = computed(() => problems.value.length)
const current = computed(() => problems.value[idx.value] || null)
const isLast  = computed(() => idx.value + 1 >= total.value)
const pct     = computed(() => total.value ? Math.round(((idx.value + 1) / total.value) * 100) : 0)

const mcOptions = computed(() =>
  current.value ? parseCircledOptions(current.value.question_with_options) : null
)
const isMulti = computed(() => !!current.value?.is_multi_answer)

// revealed 상태에서 각 선택지의 시각 상태 계산
function optionState(label) {
  if (!revealed.value) return answer.value === label ? 'selected' : ''
  const correct = current.value?.correct_answer
  if (label === correct) return 'correct'
  if (label === answer.value && label !== correct) return 'wrong'
  return ''
}

function selectOption(label) {
  if (revealed.value) return
  if (isMulti.value) {
    const i = selectedLabels.value.indexOf(label)
    if (i >= 0) selectedLabels.value.splice(i, 1)
    else selectedLabels.value.push(label)
    const order = mcOptions.value.map(o => o.label)
    answer.value = selectedLabels.value
      .slice()
      .sort((a, b) => order.indexOf(a) - order.indexOf(b))
      .join(',')
  } else {
    answer.value = label
  }
}

function submit() {
  if (!answer.value.trim()) {
    showToast('답을 입력해주세요', 'negative', 'circle-exclamation')
    return
  }
  const p = current.value
  const correct = p.correct_answer?.trim()
  let is_correct
  if (p.is_multi_answer) {
    const submitted = new Set(answer.value.split(',').map(s => s.trim()))
    const correctSet = new Set(correct.split(',').map(s => s.trim()))
    is_correct = [...submitted].sort().join() === [...correctSet].sort().join()
  } else {
    is_correct = answer.value.trim() === correct
  }
  results.value.push({ problem_id: p.problem_id, is_correct })
  revealed.value = true
}

function nextProblem() {
  if (isLast.value) {
    finishRedo()
  } else {
    idx.value += 1
    answer.value = ''
    selectedLabels.value = []
    revealed.value = false
  }
}

function finishRedo() {
  const allCorrect = results.value.every(r => r.is_correct)
  if (allCorrect) {
    router.push('/review/master')
  } else {
    // 틀린 게 있으면 해설 다시 → 이번엔 현재 review 세션 기준
    router.push('/review/explain')
  }
}

const isCorrectNow = computed(() => {
  if (!revealed.value || !results.value.length) return null
  return results.value[results.value.length - 1]?.is_correct
})

</script>

<template>
  <FocusShell title="재도전" :toast="toast" @back="router.push('/review/explain')">
    <template #topbar>
      <div class="prog"><i :style="{ width: pct + '%' }" /></div>
      <span class="count">{{ idx + 1 }} / {{ total }}</span>
    </template>

    <div v-if="loading" class="center-msg assistive">문제를 불러오는 중…</div>

    <div v-else-if="!problems.length" class="center-msg">
      <div class="wds-body-2 assistive">재도전할 문제가 없어요.</div>
      <WdsButton variant="primary" size="large" @click="router.push('/review/master')">완료하기</WdsButton>
    </div>

    <div v-else-if="current" class="play-body">
      <!-- 정오답 피드백 배너 -->
      <div v-if="revealed" class="feedback-banner" :data-ok="isCorrectNow">
        <WdsIcon :name="isCorrectNow ? 'check-circle' : 'circle-exclamation'" :size="18" />
        <span class="wds-label-1" style="font-weight:700">
          {{ isCorrectNow ? '정답이에요!' : '아쉽지만 틀렸어요' }}
        </span>
        <span v-if="!isCorrectNow" class="wds-caption-1">
          정답: {{ current.correct_answer }}
        </span>
      </div>

      <div class="row" style="gap:6px; flex-wrap:wrap">
        <span class="play-badge play-badge--type">{{ current.problem_subtype }}</span>
        <span class="play-badge" :data-tone="difficultyTone(current.difficulty)">
          난이도 {{ current.difficulty }}
        </span>
      </div>

      <QuizStem :q="current" />

      <div v-if="mcOptions" class="stack-8">
        <div v-if="isMulti" class="wds-caption-1 assistive">정답을 모두 고르세요</div>
        <QuizOption
          v-for="(opt, i) in mcOptions"
          :key="opt.label"
          :index="i"
          :label="opt.label"
          :state="optionState(opt.label)"
          @click="selectOption(opt.label)"
        >
          <InlineTex :text="opt.text" />
        </QuizOption>
      </div>

      <template v-else>
        <div class="answer-box">
          <div class="field-label">정답 입력</div>
          <WdsField
            v-model="answer"
            :placeholder="isMulti ? '예: ①,④' : '답을 입력하세요'"
            :disabled="revealed"
            @enter="revealed ? nextProblem() : submit()"
          />
        </div>
      </template>
    </div>

    <template #foot>
      <div class="play-foot">
        <WdsButton
          v-if="!revealed"
          variant="primary" size="large" block
          :disabled="!answer.trim()"
          @click="submit"
        >
          제출하기
        </WdsButton>
        <WdsButton
          v-else
          variant="primary" size="large" block icon-right="arrow-right"
          @click="nextProblem"
        >
          {{ isLast ? '결과 보기' : '다음 문제' }}
        </WdsButton>
      </div>
    </template>
  </FocusShell>
</template>

<style scoped>
.center-msg { display:flex; flex-direction:column; align-items:center; gap:16px; padding:60px 0; text-align:center; }
.play-body  { display:flex; flex-direction:column; gap:18px; }

.feedback-banner {
  display:flex; align-items:center; gap:8px;
  padding:12px 16px; border-radius:14px;
}
.feedback-banner[data-ok="true"]  { background:var(--green-99,#f0fff4); color:var(--status-positive); }
.feedback-banner[data-ok="false"] { background:var(--red-99,#fff0f0);   color:var(--status-negative); }

.play-badge {
  padding:5px 10px; border-radius:var(--radius-full);
  font:var(--weight-semibold) 12px/1 var(--font-sans);
  background:var(--fill-normal); color:var(--label-alternative);
}
.play-badge--type { background:var(--blue-99); color:var(--suql-accent); }
.play-badge[data-tone='positive'] { background:var(--green-99); color:var(--status-positive); }
.play-badge[data-tone='cautionary'] { background:var(--orange-99); color:var(--status-cautionary); }
.play-badge[data-tone='negative'] { background:var(--red-99); color:var(--status-negative); }
.answer-box { display:flex; flex-direction:column; gap:8px; }
.field-label { font:var(--weight-semibold) 13px/1 var(--font-sans); color:var(--label-alternative); }
.play-foot { display:flex; gap:10px; }
</style>