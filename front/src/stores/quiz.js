// 📄 src/stores/quiz.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api, { unwrap } from '@/api'

export const useQuizStore = defineStore('quiz', () => {
  const sessionId      = ref(null)       // 현재 세션 id
  const sessionType    = ref('normal')   // normal | diagnosis | review_1 | review_2
  const problems       = ref([])         // [{ order, problem_id, ... }]
  const answers        = ref({})         // { [problem_id]: user_answer }
  const submitResult   = ref(null)       // submit 응답 data

  // 오답 루프용 추가 상태
  const parentSessionId = ref(null)      // 오답 루프 출발점 세션 ID (재도전 시 원본 오답 조회용)
  const chatContext     = ref(null)      // ChatView용 { sessionId, problem }

  // 약점 유형 Top3를 유형별로 순서대로 도는 오답 루프 진행 상태.
  // reviewSubtypes[i] = { rank, problemSubtype, originalProblemId, s1, mid, s2 }
  // s1/mid/s2 = { problem_id, difficulty } | null (추천 문제가 부족하면 null일 수 있음)
  const reviewSubtypes    = ref([])
  const reviewSubtypeIdx  = ref(0)

  // CoachingView에서 받은 recommendations 응답으로 유형별 보완1/보완2 후보를 구성.
  // 후보 선정 규칙: 첫 문제=s1, 난이도 '중'인 것=mid, 남는 것=s2 (데이터 부족하면 null)
  function setupReviewLoop(report) {
    reviewSubtypes.value = report.weak_subtypes.map((weak) => {
      // 백엔드가 이미 order_index 순으로 줌
      const items = report.recommendations.filter((r) => r.rank === weak.rank)
      const s1  = items[0] || null
      const mid = items.slice(1).find((r) => r.difficulty === '중') || null
      const s2  = items.find((r) => r !== s1 && r !== mid) || null
      return {
        rank:              weak.rank,
        problemSubtype:    weak.problem_subtype,
        originalProblemId: weak.original_problem_id,
        s1, mid, s2,
      }
    })
    reviewSubtypeIdx.value = 0
  }

  const total = computed(() => problems.value.length)

  function startSession({ id, type = 'normal', problemList = [] }) {
    sessionId.value    = id
    sessionType.value  = type
    problems.value     = problemList
    answers.value      = {}
    submitResult.value = null
  }

  async function createAndLoad(payload) {
    const created = unwrap(await api.post('/quiz/sessions', payload))
    const sid     = created.session_id

    const loaded  = unwrap(await api.get(`/quiz/sessions/${sid}/problems`))
    const list    = loaded.problems || []

    startSession({
      id:          sid,
      type:        created.session_type || 'normal',
      problemList: list,
    })

    return {
      sessionId:    sid,
      sessionType:  created.session_type || 'normal',
      actualCount:  created.actual_count ?? list.length,
      problems:     list,
    }
  }

  function setAnswer(problemId, userAnswer) {
    answers.value = { ...answers.value, [problemId]: userAnswer }
  }

  function buildAnswersPayload() {
    return problems.value.map(p => ({
      problem_id:  p.problem_id,
      user_answer: answers.value[p.problem_id] ?? '',
    }))
  }

  async function submit() {
    const data = unwrap(
      await api.post(`/quiz/sessions/${sessionId.value}/submit`, {
        answers: buildAnswersPayload(),
      })
    )
    submitResult.value = data
    return data
  }

  function setSubmitResult(data) {
    submitResult.value = data
  }

  function reset() {
    sessionId.value      = null
    sessionType.value    = 'normal'
    problems.value       = []
    answers.value        = {}
    submitResult.value   = null
    parentSessionId.value = null
    chatContext.value     = null
    reviewSubtypes.value   = []
    reviewSubtypeIdx.value = 0
  }

  return {
    sessionId, sessionType, problems, answers, submitResult, total,
    parentSessionId, chatContext,
    reviewSubtypes, reviewSubtypeIdx, setupReviewLoop,
    startSession, createAndLoad, setAnswer, buildAnswersPayload,
    submit, setSubmitResult, reset,
  }
})