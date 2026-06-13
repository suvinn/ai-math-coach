<template>
  <section class="page">
    <div class="page-header">
      <p class="eyebrow">AI Math Coach</p>
      <h1>학습 범위 선택</h1>
      <p class="description">
        풀고 싶은 단원과 문제 수를 선택하면 맞춤형 퀴즈를 시작할 수 있어요.
      </p>
    </div>

    <div v-if="isLoading" class="notice">
      단원 정보를 불러오는 중입니다...
    </div>

    <div v-else-if="errorMessage" class="notice error">
      {{ errorMessage }}
    </div>

    <div v-else class="form-card">
      <div class="form-group">
        <label>대단원</label>
        <select v-model="selectedMajor">
          <option value="">대단원을 선택하세요</option>
          <option
            v-for="chapter in chapters"
            :key="chapter.chapter_major"
            :value="chapter.chapter_major"
          >
            {{ chapter.chapter_major }}
          </option>
        </select>
      </div>

      <div class="form-group">
        <label>중단원</label>
        <select v-model="selectedMiddle" :disabled="!selectedMajor">
          <option value="">중단원을 선택하세요</option>
          <option
            v-for="middle in middleOptions"
            :key="middle.chapter_middle"
            :value="middle.chapter_middle"
          >
            {{ middle.chapter_middle }}
          </option>
        </select>
      </div>

      <div class="form-group">
        <label>소단원</label>
        <select v-model="selectedMinor" :disabled="!selectedMiddle">
          <option value="">소단원 전체</option>
          <option
            v-for="minor in minorOptions"
            :key="minor"
            :value="minor"
          >
            {{ minor }}
          </option>
        </select>
      </div>

      <div class="form-group">
        <label>문제 수</label>
        <div class="count-options">
          <button
            v-for="count in problemCountOptions"
            :key="count"
            type="button"
            :class="{ active: selectedProblemCount === count }"
            @click="selectedProblemCount = count"
          >
            {{ count }}문제
          </button>
        </div>
      </div>

      <div class="summary-box">
        <h2>선택한 학습 범위</h2>

        <p>
          <span>대단원</span>
          <strong>{{ selectedMajor || '미선택' }}</strong>
        </p>
        <p>
          <span>중단원</span>
          <strong>{{ selectedMiddle || '미선택' }}</strong>
        </p>
        <p>
          <span>소단원</span>
          <strong>{{ selectedMinor || '전체' }}</strong>
        </p>
        <p>
          <span>문제 수</span>
          <strong>{{ selectedProblemCount }}문제</strong>
        </p>
      </div>

      <button
        class="primary-button"
        type="button"
        :disabled="!canStartQuiz || isStarting"
        @click="handleStartQuiz"
      >
        {{ isStarting ? '퀴즈 생성 중...' : '퀴즈 시작하기' }}
      </button>

      <p v-if="startErrorMessage" class="form-error">
        {{ startErrorMessage }}
      </p>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { fetchChapters } from '../api/chapters'
import { createQuizSession } from '../api/quiz'

const router = useRouter()

const chapters = ref([])
const isLoading = ref(false)
const errorMessage = ref('')
const startErrorMessage = ref('')
const isStarting = ref(false)

const selectedMajor = ref('')
const selectedMiddle = ref('')
const selectedMinor = ref('')
const selectedProblemCount = ref(10)

const problemCountOptions = [10, 20, 30]

const selectedMajorObject = computed(() => {
  return chapters.value.find(
    chapter => chapter.chapter_major === selectedMajor.value
  )
})

const middleOptions = computed(() => {
  return selectedMajorObject.value?.chapter_middles || []
})

const selectedMiddleObject = computed(() => {
  return middleOptions.value.find(
    middle => middle.chapter_middle === selectedMiddle.value
  )
})

const minorOptions = computed(() => {
  return selectedMiddleObject.value?.chapter_minors || []
})

const canStartQuiz = computed(() => {
  return selectedMajor.value && selectedMiddle.value && selectedProblemCount.value
})

watch(selectedMajor, () => {
  selectedMiddle.value = ''
  selectedMinor.value = ''
  startErrorMessage.value = ''
})

watch(selectedMiddle, () => {
  selectedMinor.value = ''
  startErrorMessage.value = ''
})

const loadChapters = async () => {
  isLoading.value = true
  errorMessage.value = ''

  try {
    chapters.value = await fetchChapters()
  } catch (error) {
    console.error(error)
    errorMessage.value = '단원 정보를 불러오지 못했습니다. 백엔드 서버를 확인해주세요.'
  } finally {
    isLoading.value = false
  }
}

const handleStartQuiz = async () => {
  if (!canStartQuiz.value) return

  startErrorMessage.value = ''
  isStarting.value = true

  try {
    const session = await createQuizSession({
      chapter_major: selectedMajor.value,
      chapter_middle: selectedMiddle.value,
      chapter_minor: selectedMinor.value || null,
      problem_count: selectedProblemCount.value,
    })

    router.push(`/quiz/${session.session_id}`)
  } catch (error) {
    console.error(error)

    const data = error.response?.data

    if (error.response?.status === 401 || error.response?.status === 403) {
      startErrorMessage.value = '로그인이 필요합니다. 다시 로그인해주세요.'
      router.push('/login')
      return
    }

    startErrorMessage.value =
      data?.message ||
      data?.detail ||
      data?.error ||
      '퀴즈 세션을 생성하지 못했습니다.'
  } finally {
    isStarting.value = false
  }
}

onMounted(() => {
  loadChapters()
})
</script>