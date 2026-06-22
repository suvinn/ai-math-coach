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
  const parentSessionId = ref(null)      // 오답 루프 출발점 세션 ID (RedoView에서 원본 오답 조회용)
  const masteredSubtype = ref(null)      // MasterView 축하 메시지용 subtype 이름
  const chatContext     = ref(null)      // ChatView용 { sessionId, problem }

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
    masteredSubtype.value = null
    chatContext.value     = null
  }

  return {
    sessionId, sessionType, problems, answers, submitResult, total,
    parentSessionId, masteredSubtype, chatContext,
    startSession, createAndLoad, setAnswer, buildAnswersPayload,
    submit, setSubmitResult, reset,
  }
})