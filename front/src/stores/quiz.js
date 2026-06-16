// 📄 src/stores/quiz.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// 퀴즈 흐름 동안 화면 간 공유하는 상태.
// QuizPlay → Result → Coaching, 그리고 Review 루프에서 사용.
export const useQuizStore = defineStore('quiz', () => {
  const sessionId = ref(null)        // 현재 세션 id
  const sessionType = ref('normal')  // normal | review_1 | review_2
  const problems = ref([])           // [{ order, problem_id, ... }]
  const answers = ref({})            // { [problem_id]: user_answer }
  const submitResult = ref(null)     // submit 응답 data (score, accuracy, results 등)

  const total = computed(() => problems.value.length)

  function startSession({ id, type = 'normal', problemList = [] }) {
    sessionId.value = id
    sessionType.value = type
    problems.value = problemList
    answers.value = {}
    submitResult.value = null
  }

  function setAnswer(problemId, userAnswer) {
    answers.value = { ...answers.value, [problemId]: userAnswer }
  }

  // submit API에 보낼 형태로 변환
  function buildAnswersPayload() {
    return problems.value.map((p) => ({
      problem_id: p.problem_id,
      user_answer: answers.value[p.problem_id] ?? '',
    }))
  }

  function setSubmitResult(data) {
    submitResult.value = data
  }

  function reset() {
    sessionId.value = null
    sessionType.value = 'normal'
    problems.value = []
    answers.value = {}
    submitResult.value = null
  }

  return {
    sessionId, sessionType, problems, answers, submitResult, total,
    startSession, setAnswer, buildAnswersPayload, setSubmitResult, reset,
  }
})