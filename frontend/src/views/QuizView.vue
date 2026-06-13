<template>
  <section class="page">
    <div class="page-header">
      <p class="eyebrow">Quiz Session #{{ sessionId }}</p>
      <h1>퀴즈 풀기</h1>
      <p class="description">
        문제를 한 개씩 확인하면서 답을 선택해보세요.
      </p>
    </div>

    <div v-if="isLoading" class="notice">
      문제를 불러오는 중입니다...
    </div>

    <div v-else-if="errorMessage" class="notice error">
      {{ errorMessage }}
    </div>

    <div v-else-if="problems.length === 0" class="notice">
      표시할 문제가 없습니다.
    </div>

    <div v-else class="quiz-layout">
      <div class="quiz-progress">
        <span>{{ currentIndex + 1 }} / {{ problems.length }}</span>
        <strong>{{ currentProblem.difficulty }} 난이도</strong>
      </div>

      <article class="problem-card">
        <div class="problem-meta">
          <span>문제 {{ currentProblem.order }}</span>
          <span>{{ currentProblem.problem_subtype }}</span>
        </div>

        <h2 class="problem-title">
          {{ currentProblem.question_text }}
        </h2>

        <div
          v-if="currentProblem.question_with_options"
          class="problem-content"
        >
          {{ currentProblem.question_with_options }}
        </div>

        <div
          v-if="currentProblem.question_image_bbox?.length"
          class="image-placeholder"
        >
          이미지 영역이 포함된 문제입니다.
        </div>
      </article>

      <div class="answer-box">
        <label>내 답안</label>

        <div class="answer-options">
          <button
            v-for="option in answerOptions"
            :key="option"
            type="button"
            :class="{ active: currentAnswer === option }"
            @click="selectAnswer(option)"
          >
            {{ option }}
          </button>
        </div>

        <input
          v-model.trim="manualAnswer"
          type="text"
          placeholder="선택지에 없으면 직접 입력하세요. 예: ㄱ, ㄴ, ㄹ"
          @input="selectAnswer(manualAnswer)"
        />
      </div>

      <div class="answer-summary">
        <span>답안 입력 현황</span>
        <strong>{{ answeredCount }} / {{ problems.length }}</strong>
      </div>

      <p v-if="submitErrorMessage" class="form-error">
        {{ submitErrorMessage }}
      </p>

      <div class="quiz-actions">
        <button
          class="secondary-button"
          type="button"
          :disabled="currentIndex === 0"
          @click="goPrev"
        >
          이전
        </button>

        <button
          v-if="!isLastProblem"
          class="primary-button"
          type="button"
          @click="goNext"
        >
          다음
        </button>

        <button
          v-else
          class="primary-button"
          type="button"
          :disabled="isSubmitting"
          @click="handleSubmit"
        >
          {{ isSubmitting ? '제출 중...' : '답안 제출하기' }}
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { fetchQuizProblems, submitQuizAnswers } from '../api/quiz'

const props = defineProps({
  sessionId: {
    type: String,
    required: true,
  },
})

const router = useRouter()

const problems = ref([])
const answers = ref({})
const isLoading = ref(false)
const isSubmitting = ref(false)
const errorMessage = ref('')
const submitErrorMessage = ref('')
const currentIndex = ref(0)
const manualAnswer = ref('')

const answerOptions = ['①', '②', '③', '④', '⑤', 'ㄱ', 'ㄴ', 'ㄷ', 'ㄹ']

const currentProblem = computed(() => {
  return problems.value[currentIndex.value] || {}
})

const currentAnswer = computed(() => {
  return answers.value[currentProblem.value.problem_id] || ''
})

const isLastProblem = computed(() => {
  return currentIndex.value === problems.value.length - 1
})

const answeredCount = computed(() => {
  return Object.values(answers.value).filter(Boolean).length
})

watch(currentIndex, () => {
  manualAnswer.value = currentAnswer.value
  submitErrorMessage.value = ''
})

const loadProblems = async () => {
  isLoading.value = true
  errorMessage.value = ''

  try {
    const data = await fetchQuizProblems(props.sessionId)
    problems.value = data.problems || []
  } catch (error) {
    console.error(error)

    const data = error.response?.data

    if (error.response?.status === 401 || error.response?.status === 403) {
      errorMessage.value = '로그인이 필요합니다. 다시 로그인해주세요.'
      return
    }

    errorMessage.value =
      data?.message ||
      data?.detail ||
      data?.error ||
      '문제 목록을 불러오지 못했습니다.'
  } finally {
    isLoading.value = false
  }
}

const selectAnswer = (answer) => {
  if (!currentProblem.value.problem_id) return

  answers.value = {
    ...answers.value,
    [currentProblem.value.problem_id]: answer,
  }
}

const goPrev = () => {
  if (currentIndex.value > 0) {
    currentIndex.value -= 1
  }
}

const goNext = () => {
  if (currentIndex.value < problems.value.length - 1) {
    currentIndex.value += 1
  }
}

const handleSubmit = async () => {
  submitErrorMessage.value = ''

  const unansweredProblems = problems.value.filter(
    problem => !answers.value[problem.problem_id]
  )

  if (unansweredProblems.length > 0) {
    const firstUnansweredIndex = problems.value.findIndex(
      problem => !answers.value[problem.problem_id]
    )

    currentIndex.value = firstUnansweredIndex
    submitErrorMessage.value = '아직 답을 선택하지 않은 문제가 있습니다.'
    return
  }

  const answerPayload = problems.value.map(problem => ({
    problem_id: problem.problem_id,
    user_answer: answers.value[problem.problem_id],
  }))

  isSubmitting.value = true

  try {
    const result = await submitQuizAnswers(props.sessionId, answerPayload)

    sessionStorage.setItem(
      `quiz-result-${props.sessionId}`,
      JSON.stringify(result)
    )

    router.push(`/result/${props.sessionId}`)
  } catch (error) {
    console.error(error)

    const data = error.response?.data

    if (error.response?.status === 409) {
      submitErrorMessage.value = '이미 제출 완료된 퀴즈입니다.'
      router.push(`/result/${props.sessionId}`)
      return
    }

    submitErrorMessage.value =
      data?.message ||
      data?.detail ||
      data?.error ||
      '답안 제출에 실패했습니다.'
  } finally {
    isSubmitting.value = false
  }
}

onMounted(() => {
  loadProblems()
})
</script>