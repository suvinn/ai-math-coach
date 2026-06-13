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
          @click="handleTempFinish"
        >
          답안 확인
        </button>
      </div>

      <p class="helper-text">
        현재 단계에서는 문제 조회와 답안 선택까지만 연결했습니다. 제출 API는 다음 단계에서 연결합니다.
      </p>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'

import { fetchQuizProblems } from '../api/quiz'

const props = defineProps({
  sessionId: {
    type: String,
    required: true,
  },
})

const problems = ref([])
const answers = ref({})
const isLoading = ref(false)
const errorMessage = ref('')
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

watch(currentIndex, () => {
  manualAnswer.value = currentAnswer.value
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

const handleTempFinish = () => {
  const answerCount = Object.values(answers.value).filter(Boolean).length

  alert(
    `현재 선택한 답안 수: ${answerCount}/${problems.value.length}\n` +
    `다음 단계에서 제출 API를 연결할 예정입니다.`
  )
}

onMounted(() => {
  loadProblems()
})
</script>