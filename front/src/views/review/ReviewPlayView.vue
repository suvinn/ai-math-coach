<!-- 📄 src/views/review/ReviewPlayView.vue -->
<!-- 오답 루프: 약점 유형 Top3를 유형별로 순서대로 진행.
     유형당: 보완1(s1, 하) → [정답: 보완2(mid, 중) | 오답: 해설+챗봇 → 보완2(s2, 하)]
           → 보완2 결과 무관하게 → 재도전(원래 틀린 문제) → 해설(틀렸을 때만) → 유형 완료
     CoachingView에서 quiz.setupReviewLoop()로 reviewSubtypes를 채우고 진입해야 한다. -->
<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useQuizStore } from '@/stores/quiz'
import { useToast } from '@/composables/useToast'
import api, { unwrap } from '@/api'
import FocusShell from '@/components/common/FocusShell.vue'
import QuizStem from '@/components/quiz/QuizStem.vue'
import OptionsBox from '@/components/common/OptionsBox.vue'
import QuizOption from '@/components/common/QuizOption.vue'
import InlineTex from '@/components/common/InlineTex.vue'
import WdsButton from '@/components/common/WdsButton.vue'
import WdsField from '@/components/common/WdsField.vue'
import WdsIcon from '@/components/common/WdsIcon.vue'
import { parseCircledOptions, parseOptionPreamble } from '@/utils/circledOptions'
import { difficultyTone } from '@/utils/difficulty'

const STEP_LABEL = { s1: '보완 1단계', mid: '보완 2단계', s2: '보완 2단계', redo: '재도전' }
const RESUME_KEY = 'reviewLoop_resume'

const router = useRouter()
const quiz   = useQuizStore()
const { toast, showToast } = useToast()

if (!quiz.reviewSubtypes.length) router.replace('/quiz/coaching')

const loadingProblem = ref(true)
const submitting     = ref(false)
const originalWrongMap = ref({})  // problem_id → 원본 세션의 오답 상세 (재도전용)

const currentStepKey = ref('s1')   // s1 | mid | s2 | redo
const currentProblem = ref(null)
const answer          = ref('')
const selectedLabels  = ref([])
const revealed         = ref(false)  // 제출 후 정오답/해설 표시 중인지
const lastResult       = ref(null)   // { isCorrect, correctLabel, correctText, explanation }
const subtypeDone      = ref(false)  // "이 유형 보완 학습 완료" 인터스티셔

const subtype = computed(() => quiz.reviewSubtypes[quiz.reviewSubtypeIdx])
const subtypeCount = computed(() => quiz.reviewSubtypes.length)
const isLastSubtype = computed(() => quiz.reviewSubtypeIdx >= subtypeCount.value - 1)

const mcOptions = computed(() =>
  currentProblem.value ? parseCircledOptions(currentProblem.value.question_with_options) : null
)
const optionPreamble = computed(() =>
  currentProblem.value
    ? parseOptionPreamble(currentProblem.value.question_with_options, currentProblem.value.question_text)
    : null
)
const isMulti = computed(() => !!currentProblem.value?.is_multi_answer)

// ─── 이어하기 저장 ────────────────────────────────────────────────
// subtypeDone 인터스티셔에서 "홈으로" 누를 때 호출.
// 다음 유형 인덱스와 원본 세션 정보를 localStorage에 저장해둔다.
function saveResume() {
  const nextIdx = quiz.reviewSubtypeIdx + 1
  if (nextIdx >= quiz.reviewSubtypes.length) {
    // 마지막 유형이면 저장할 필요 없음
    localStorage.removeItem(RESUME_KEY)
    return
  }
  const payload = {
    parentSessionId: quiz.parentSessionId,
    reviewSubtypes:  quiz.reviewSubtypes,
    resumeFromIdx:   nextIdx,
  }
  localStorage.setItem(RESUME_KEY, JSON.stringify(payload))
}

function goHomeWithSave() {
  saveResume()
  quiz.reset()
  router.push('/')
}

// 어떤 방식으로 나가든 (뒤로가기, 탭 닫기 등) 현재 진행 상태 저장
// 단, 챗봇 페이지로 이동 시엔 reviewReturnState가 설정되므로 저장 불필요
onBeforeUnmount(() => {
  if (quiz.reviewReturnState) return           // 챗봇으로 이동 중 → 저장 생략
  if (!quiz.reviewSubtypes.length) return
  if (subtypeDone.value && isLastSubtype.value) return  // 전부 완료 → 저장 불필요
  const payload = {
    parentSessionId: quiz.parentSessionId,
    reviewSubtypes:  quiz.reviewSubtypes,
    resumeFromIdx:   subtypeDone.value
      ? quiz.reviewSubtypeIdx + 1   // 이 유형은 끝났으므로 다음 유형부터
      : quiz.reviewSubtypeIdx,      // 이 유형 처음부터
  }
  localStorage.setItem(RESUME_KEY, JSON.stringify(payload))
})
// ─────────────────────────────────────────────────────────────────

onMounted(async () => {
  try {
    const data = unwrap(await api.get(`/quiz/sessions/${quiz.parentSessionId}/wrong-answers`))
    originalWrongMap.value = Object.fromEntries(
      (data.wrong_problems || []).map((p) => [p.problem_id, p])
    )
  } catch {
    showToast('원본 오답 정보를 불러오지 못했어요', 'negative', 'circle-exclamation')
  }

  // 챗봇에서 돌아온 경우: 이전 단계 상태를 그대로 복원
  if (quiz.reviewReturnState) {
    const { stepKey, problem, result } = quiz.reviewReturnState
    quiz.reviewReturnState = null
    currentStepKey.value  = stepKey
    currentProblem.value  = problem
    loadingProblem.value  = false
    if (result) {
      lastResult.value = result
      revealed.value   = true
    }
    return
  }

  await startSubtype()
})

async function startSubtype() {
  subtypeDone.value = false
  const s = subtype.value
  if (s?.s1) {
    await loadStep('s1', s.s1.problem_id)
  } else {
    await loadRedoStep()
  }
}

async function loadStep(stepKey, problemId) {
  currentStepKey.value = stepKey
  revealed.value   = false
  lastResult.value = null
  answer.value     = ''
  selectedLabels.value = []
  loadingProblem.value = true
  try {
    const res = await quiz.createAndLoad({
      problem_ids:       [problemId],
      parent_session_id: quiz.parentSessionId,
    })
    currentProblem.value = res.problems[0] || null
    if (!currentProblem.value) await loadRedoStep()
  } catch {
    showToast('문제를 불러오지 못했어요', 'negative', 'circle-exclamation')
  } finally {
    loadingProblem.value = false
  }
}

async function loadRedoStep() {
  currentStepKey.value  = 'redo'
  revealed.value        = false
  lastResult.value      = null
  answer.value          = ''
  selectedLabels.value  = []
  loadingProblem.value  = true

  const problemId = subtype.value?.originalProblemId
  currentProblem.value = (problemId && originalWrongMap.value[problemId]) || null

  if (!currentProblem.value && problemId) {
    // originalWrongMap 캐시 미스 → API로 직접 조회
    try {
      const data = unwrap(
        await api.get(`/quiz/sessions/${quiz.parentSessionId}/redo-problem?problem_id=${encodeURIComponent(problemId)}`)
      )
      currentProblem.value = data
    } catch {
      // API 조회 실패 → 유형 완료 처리
    }
  }

  loadingProblem.value = false
  if (!currentProblem.value) subtypeDone.value = true
}

function isSelected(label) {
  return isMulti.value ? selectedLabels.value.includes(label) : answer.value === label
}

function selectOption(label) {
  if (revealed.value) return
  if (isMulti.value) {
    const i = selectedLabels.value.indexOf(label)
    if (i >= 0) selectedLabels.value.splice(i, 1)
    else selectedLabels.value.push(label)
    const order = mcOptions.value.map((o) => o.label)
    answer.value = selectedLabels.value
      .slice()
      .sort((a, b) => order.indexOf(a) - order.indexOf(b))
      .join(',')
  } else {
    answer.value = label
  }
}

// revealed 상태에서 보기 시각 상태 (재도전 단계에서 정답/오답 표시용)
// correctLabel은 채점용 깨끗한 라벨(①②③ 등) — correct_answer(전체 텍스트)와 비교하면 절대 안 맞음
function optionState(label) {
  if (!revealed.value) return isSelected(label) ? 'selected' : ''
  const correctLabels = (lastResult.value?.correctLabel || '').split(',').map((s) => s.trim())
  if (correctLabels.includes(label)) return 'correct'
  if (label === answer.value) return 'wrong'
  return ''
}

async function submitCurrent() {
  if (!answer.value.trim()) {
    showToast('답을 입력해주세요', 'negative', 'circle-exclamation')
    return
  }
  if (currentStepKey.value === 'redo') {
    submitRedo()
    return
  }
  quiz.setAnswer(currentProblem.value.problem_id, answer.value.trim())
  submitting.value = true
  try {
    const res = await quiz.submit()
    const r = res.results[0]
    lastResult.value = {
      isCorrect:    r.is_correct,
      correctLabel: r.grading_answer || r.correct_answer,
      correctText:  r.correct_answer,
      explanation:  r.explanation,
    }
    // 정답/오답 모두 revealed 상태로 — 정답 피드백 확인 후 "다음" 클릭 시 advance()
    revealed.value = true
  } catch (e) {
    showToast(e?.response?.data?.message || '제출에 실패했어요', 'negative', 'circle-exclamation')
  } finally {
    submitting.value = false
  }
}

function submitRedo() {
  const p = currentProblem.value
  // originalWrongMap의 문제는 ProblemWithAnswerSerializer → answer 필드 사용 (correct_answer 없음)
  const correctLabel = (p.grading_answer || p.answer || '').trim()
  let isCorrect
  if (p.is_multi_answer) {
    const submitted = new Set(answer.value.split(',').map((s) => s.trim()))
    const correctSet = new Set(correctLabel.split(',').map((s) => s.trim()))
    isCorrect = [...submitted].sort().join() === [...correctSet].sort().join()
  } else {
    isCorrect = answer.value.trim() === correctLabel
  }
  lastResult.value = { isCorrect, correctLabel, correctText: p.answer, explanation: p.explanation }
  revealed.value = true
}

// 정답이면 바로, 오답이면 해설 패널의 "다음" 클릭 시 호출 — 유형 안에서 다음 단계로 진행
function advance() {
  const s = subtype.value
  const wasCorrect = lastResult.value?.isCorrect

  if (currentStepKey.value === 's1') {
    if (wasCorrect) {
      // 정답 → 난이도 높은 보완2(mid) 우선, 없으면 s2 폴백
      const next = s.mid || s.s2
      if (next) return loadStep('mid', next.problem_id)
      return loadRedoStep()
    } else {
      // 오답 → 난이도 하 보완2(s2) 우선, 없으면 mid 폴백
      const next = s.s2 || s.mid
      if (next) return loadStep('s2', next.problem_id)
      return loadRedoStep()
    }
  }

  if (currentStepKey.value === 'mid' || currentStepKey.value === 's2') {
    // 정답/오답 무관하게 재도전으로
    return loadRedoStep()
  }

  // redo — 정답/오답 무관하게 유형 완료
  subtypeDone.value = true
}

function continueToNextSubtype() {
  // 이어하기 데이터가 있었다면 이 유형을 완료했으므로 갱신
  localStorage.removeItem(RESUME_KEY)
  if (isLastSubtype.value) {
    router.push('/review/master')
  } else {
    quiz.reviewSubtypeIdx += 1
    startSubtype()
  }
}

function goChat() {
  // 챗봇에서 돌아올 때 현재 단계를 그대로 복원하기 위해 상태 저장
  quiz.reviewReturnState = {
    stepKey: currentStepKey.value,
    problem: currentProblem.value,
    result:  lastResult.value,
  }
  quiz.chatContext = {
    sessionId: currentStepKey.value === 'redo' ? quiz.parentSessionId : quiz.sessionId,
    problem:   currentProblem.value,
  }
  router.push('/review/chat')
}
</script>

<template>
  <FocusShell title="보완 풀이" :toast="toast" @back="router.push('/quiz/coaching')">
    <template #topbar>
      <span class="count">유형 {{ quiz.reviewSubtypeIdx + 1 }} / {{ subtypeCount }} · {{ STEP_LABEL[currentStepKey] }}</span>
    </template>

    <div v-if="subtypeDone" class="center-msg">
      <div class="all-correct-ico">🎉</div>
      <div class="wds-headline-2" style="font-weight:700">{{ subtype?.problemSubtype }} 보완 학습 완료!</div>
      <div class="wds-body-2 assistive">{{ isLastSubtype ? '약점 유형을 모두 돌았어요' : '다음 약점 유형으로 넘어가요' }}</div>
    </div>

    <div v-else-if="loadingProblem" class="center-msg assistive">문제를 불러오는 중…</div>

    <div v-else-if="currentProblem" class="play-body">
      <div v-if="revealed" class="feedback-banner" :data-ok="lastResult.isCorrect">
        <WdsIcon :name="lastResult.isCorrect ? 'circle-check' : 'circle-exclamation'" :size="18" />
        <span class="wds-label-1" style="font-weight:700">
          {{ lastResult.isCorrect ? '정답이에요!' : '아쉽지만 틀렸어요' }}
        </span>
        <span v-if="!lastResult.isCorrect" class="wds-caption-1">정답: <InlineTex :text="lastResult.correctLabel" /></span>
      </div>

      <div class="row" style="gap:6px; flex-wrap:wrap">
        <span class="play-badge play-badge--type">{{ currentProblem.problem_subtype }}</span>
        <span class="play-badge" :data-tone="difficultyTone(currentProblem.difficulty)">
          난이도 {{ currentProblem.difficulty }}
        </span>
      </div>

      <QuizStem :q="currentProblem" />

      <div v-if="currentProblem.assets?.length" class="play-assets">
        <div v-for="(asset, i) in currentProblem.assets" :key="i" class="play-asset">
          <img
            :src="asset.image_url"
            :alt="asset.asset_role"
            @error="$event.target.closest('.play-asset').style.display='none'"
          />
        </div>
      </div>

      <div v-if="mcOptions" class="stack-8">
        <div v-if="isMulti" class="wds-caption-1 assistive">정답을 모두 고르세요 (복수 선택)</div>
        <div v-if="optionPreamble" class="option-preamble"><InlineTex :text="optionPreamble" /></div>
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
        <div v-if="currentProblem.question_with_options" class="play-options">
          <OptionsBox :text="currentProblem.question_with_options" />
        </div>
        <div class="answer-box">
          <div class="field-label">정답 입력</div>
          <WdsField
            v-model="answer"
            :disabled="revealed"
            :placeholder="isMulti ? '예: ①,④' : '답을 입력하세요'"
            @enter="submitCurrent"
          />
        </div>
      </template>

      <!-- 오답일 때만: 해설 + 챗봇 -->
      <div v-if="revealed && !lastResult.isCorrect" class="explain-box stack-12">
        <div class="wds-label-1" style="font-weight:700">해설</div>
        <div class="explain-text wds-body-2"><InlineTex :text="lastResult.explanation" /></div>
        <button class="chat-btn" @click="goChat">
          <WdsIcon name="sparkle" :size="15" color="var(--suql-accent)" />
          <span class="wds-caption-1" style="color:var(--suql-accent); font-weight:600">AI에게 질문하기</span>
        </button>
      </div>
    </div>

    <template #foot>
      <!-- 유형 완료 인터스티셔: 다음 유형으로 + 홈으로 나란히 -->
      <div v-if="subtypeDone" class="play-foot">
        <WdsButton
          v-if="!isLastSubtype"
          variant="secondary"
          size="large"
          @click="goHomeWithSave"
        >
          홈으로
        </WdsButton>
        <WdsButton variant="primary" size="large" block icon-right="arrow-right" @click="continueToNextSubtype">
          {{ isLastSubtype ? '결과 보기' : '다음 유형으로' }}
        </WdsButton>
      </div>
      <div v-else-if="currentProblem" class="play-foot">
        <WdsButton
          v-if="!revealed"
          variant="primary" size="large" block
          :disabled="submitting"
          @click="submitCurrent"
        >
          {{ submitting ? '제출 중…' : '제출하기' }}
        </WdsButton>
        <WdsButton v-else variant="primary" size="large" block icon-right="arrow-right" @click="advance">
          {{ currentStepKey === 'redo' ? '완료' : '다음' }}
        </WdsButton>
      </div>
    </template>
  </FocusShell>
</template>

<style scoped>
.count { font: var(--weight-semibold) 13px/1 var(--font-sans); color: var(--label-alternative); }
.center-msg {
  display: flex; flex-direction: column; align-items: center;
  gap: 12px; padding: 80px 0; text-align: center;
}
.all-correct-ico { font-size: 48px; }
.play-body { display: flex; flex-direction: column; gap: 18px; }
.feedback-banner {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 16px; border-radius: 14px;
}
.feedback-banner[data-ok="true"]  { background: var(--green-99); color: var(--status-positive); }
.feedback-banner[data-ok="false"] { background: var(--red-99);   color: var(--status-negative); }
.play-badge {
  padding: 5px 10px; border-radius: var(--radius-full);
  font: var(--weight-semibold) 12px/1 var(--font-sans);
  background: var(--fill-normal); color: var(--label-alternative);
}
.play-badge--type { background: var(--blue-99); color: var(--suql-accent); }
.play-badge[data-tone='positive']   { background: var(--green-99);  color: var(--status-positive); }
.play-badge[data-tone='cautionary'] { background: var(--orange-99); color: var(--status-cautionary); }
.play-badge[data-tone='negative']   { background: var(--red-99);    color: var(--status-negative); }
.option-preamble {
  text-align: center;
  font: var(--weight-regular) 15px/1.6 var(--font-sans);
  color: var(--label-normal);
  padding: 4px 0;
}
.play-assets { display: flex; flex-direction: column; gap: 10px; }
.play-asset { display: flex; flex-direction: column; gap: 6px; }
.play-asset img { max-width: 100%; border-radius: 12px; box-shadow: inset 0 0 0 1px var(--line-normal-normal); }
.play-options {
  background: var(--fill-alternative); border-radius: 14px; padding: 16px;
  font: var(--weight-regular) 14px/1.7 var(--font-sans); color: var(--label-normal); white-space: pre-wrap;
}
.answer-box { display: flex; flex-direction: column; gap: 8px; }
.field-label { font: var(--weight-semibold) 13px/1 var(--font-sans); color: var(--label-alternative); }
.explain-box {
  padding: 16px; border-radius: 16px;
  box-shadow: inset 0 0 0 1px var(--line-normal-normal);
}
.explain-text {
  padding: 12px; background: var(--fill-alternative); border-radius: 12px;
  line-height: 1.7; white-space: pre-wrap;
}
.chat-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 12px; border-radius: 10px; border: none; background: var(--blue-99);
  cursor: pointer; align-self: flex-start;
}
.chat-btn:hover { background: var(--blue-95, #e8f0ff); }
.play-foot { display: flex; gap: 10px; }
</style>