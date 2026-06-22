<!-- 📄 src/views/review/ReviewPlayView.vue -->
<!-- 보완 풀이 (B1): review_1 / review_2 세션을 QuizPlayView와 동일한 UI로 풀되,
     제출 후 결과를 오답 루프 전용으로 라우팅한다.
     CoachingView에서 createAndLoad() 후 /review/play 로 push 해야 한다. -->
<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useQuizStore } from '@/stores/quiz'
import { useToast } from '@/composables/useToast'
import FocusShell from '@/components/common/FocusShell.vue'
import QuizStem from '@/components/quiz/QuizStem.vue'
import OptionsBox from '@/components/common/OptionsBox.vue'
import QuizOption from '@/components/common/QuizOption.vue'
import InlineTex from '@/components/common/InlineTex.vue'
import WdsButton from '@/components/common/WdsButton.vue'
import WdsField from '@/components/common/WdsField.vue'
import { parseCircledOptions } from '@/utils/circledOptions'

const router = useRouter()
const quiz   = useQuizStore()
const { toast, showToast } = useToast()

if (!quiz.problems.length) router.replace('/quiz/coaching')

const idx        = ref(0)
const answer     = ref('')
const selectedLabels = ref([])
const submitting = ref(false)

const total   = computed(() => quiz.problems.length)
const current = computed(() => quiz.problems[idx.value] || null)
const isLast  = computed(() => idx.value + 1 >= total.value)
const pct     = computed(() => total.value ? Math.round(((idx.value + 1) / total.value) * 100) : 0)

const mcOptions = computed(() =>
  current.value ? parseCircledOptions(current.value.question_with_options) : null
)
const isMulti = computed(() => !!current.value?.is_multi_answer)

function isSelected(label) {
  return isMulti.value ? selectedLabels.value.includes(label) : answer.value === label
}

function selectOption(label) {
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

function restoreAnswer(problemId) {
  const saved = quiz.answers[problemId] || ''
  answer.value = saved
  selectedLabels.value = saved ? saved.split(',').map(s => s.trim()).filter(Boolean) : []
}

function prev() {
  if (idx.value === 0) return
  if (answer.value.trim()) quiz.setAnswer(current.value.problem_id, answer.value.trim())
  idx.value -= 1
  restoreAnswer(quiz.problems[idx.value].problem_id)
}

function next() {
  if (!answer.value.trim()) {
    showToast('답을 입력해주세요', 'negative', 'circle-exclamation')
    return
  }
  quiz.setAnswer(current.value.problem_id, answer.value.trim())
  if (isLast.value) finish()
  else {
    idx.value += 1
    restoreAnswer(quiz.problems[idx.value].problem_id)
  }
}

async function finish() {
  submitting.value = true
  try {
    await quiz.submit()
    // 보완 풀이 결과 → 해설 화면으로 (QuizResult 거치지 않음)
    router.push('/review/explain')
  } catch (e) {
    showToast(e?.response?.data?.message || '제출에 실패했어요', 'negative', 'circle-exclamation')
    submitting.value = false
  }
}

// 앱바 타이틀: review_1이면 "1단계 보완", review_2이면 "2단계 보완"
const shellTitle = computed(() => {
  if (quiz.sessionType === 'review_2') return '2단계 보완 풀이'
  return '1단계 보완 풀이'
})
</script>

<template>
  <FocusShell :title="shellTitle" :toast="toast" @back="router.push('/quiz/coaching')">
    <template #topbar>
      <div class="prog"><i :style="{ width: pct + '%' }" /></div>
      <span class="count">{{ idx + 1 }} / {{ total }}</span>
    </template>

    <div v-if="current" class="play-body">
      <div class="row" style="gap: 6px; flex-wrap: wrap">
        <span class="play-badge play-badge--type">{{ current.problem_subtype }}</span>
        <span class="play-badge" :data-tone="current.difficulty === '하' ? 'positive' : 'neutral'">
          난이도 {{ current.difficulty }}
        </span>
      </div>

      <QuizStem :q="current" />

      <div v-if="current.assets?.length" class="play-assets">
        <div v-for="(asset, i) in current.assets" :key="i" class="play-asset">
          <span class="wds-caption-1 assistive">{{ asset.asset_role }}</span>
          <img :src="asset.image_url" :alt="asset.asset_role" />
        </div>
      </div>

      <div v-if="mcOptions" class="stack-8">
        <div v-if="isMulti" class="wds-caption-1 assistive">정답을 모두 고르세요 (복수 선택)</div>
        <QuizOption
          v-for="(opt, i) in mcOptions"
          :key="opt.label"
          :index="i"
          :label="opt.label"
          :state="isSelected(opt.label) ? 'selected' : ''"
          @click="selectOption(opt.label)"
        >
          <InlineTex :text="opt.text" />
        </QuizOption>
      </div>

      <template v-else>
        <div v-if="current.question_with_options" class="play-options">
          <OptionsBox :text="current.question_with_options" />
        </div>
        <div class="answer-box">
          <div class="field-label">정답 입력</div>
          <div v-if="isMulti" class="wds-caption-1 assistive">콤마로 구분해서 입력하세요 (예: ①,④)</div>
          <WdsField
            v-model="answer"
            :placeholder="isMulti ? '예: ①,④' : '답을 입력하세요'"
            @enter="next"
          />
        </div>
      </template>
    </div>

    <template #foot>
      <div class="play-foot">
        <WdsButton v-if="idx > 0" variant="secondary" size="large" @click="prev">이전</WdsButton>
        <WdsButton variant="primary" size="large" block :disabled="submitting" @click="next">
          {{ isLast ? (submitting ? '제출 중…' : '제출하기') : '다음' }}
        </WdsButton>
      </div>
    </template>
  </FocusShell>
</template>

<style scoped>
.play-body { display: flex; flex-direction: column; gap: 18px; }
.play-badge {
  padding: 5px 10px; border-radius: var(--radius-full);
  font: var(--weight-semibold) 12px/1 var(--font-sans);
  background: var(--fill-normal); color: var(--label-alternative);
}
.play-badge--type { background: var(--blue-99); color: var(--suql-accent); }
.play-badge[data-tone='positive'] { background: var(--green-99); color: var(--status-positive); }
.play-assets { display: flex; flex-direction: column; gap: 10px; }
.play-asset { display: flex; flex-direction: column; gap: 6px; }
.play-asset img { max-width: 100%; border-radius: 12px; box-shadow: inset 0 0 0 1px var(--line-normal-normal); }
.play-options {
  background: var(--fill-alternative); border-radius: 14px; padding: 16px;
  font: var(--weight-regular) 14px/1.7 var(--font-sans); color: var(--label-normal); white-space: pre-wrap;
}
.answer-box { display: flex; flex-direction: column; gap: 8px; }
.field-label { font: var(--weight-semibold) 13px/1 var(--font-sans); color: var(--label-alternative); }
.play-foot { display: flex; gap: 10px; }
</style>