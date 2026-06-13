<template>
  <section class="page">
    <div class="page-header">
      <p class="eyebrow">Quiz Result #{{ sessionId }}</p>
      <h1>제출 결과</h1>
      <p class="description">
        채점 결과와 문제별 해설을 확인해보세요.
      </p>
    </div>

    <div v-if="!result" class="notice error">
      결과 정보를 찾을 수 없습니다. 퀴즈를 다시 제출하거나 학습 이력에서 확인해주세요.
    </div>

    <div v-else class="result-layout">
      <div class="score-card">
        <div>
          <span class="score-label">점수</span>
          <strong class="score-value">{{ result.score }} / {{ result.total }}</strong>
        </div>

        <div>
          <span class="score-label">정답률</span>
          <strong class="score-value">{{ accuracyPercent }}%</strong>
        </div>
      </div>

      <div class="result-actions">
        <RouterLink class="secondary-link-button" to="/home">
          새 퀴즈 풀기
        </RouterLink>

        <RouterLink
          class="primary-link-button"
          :to="`/analysis/${sessionId}`"
        >
          AI 분석 보기
        </RouterLink>
      </div>

      <div class="result-list">
        <article
          v-for="(item, index) in result.results"
          :key="item.problem_id"
          class="result-item"
          :class="{ correct: item.is_correct, wrong: !item.is_correct }"
        >
          <div class="result-item-header">
            <strong>문제 {{ index + 1 }}</strong>
            <span>
              {{ item.is_correct ? '정답' : '오답' }}
            </span>
          </div>

          <div class="result-row">
            <span>내 답안</span>
            <strong>{{ item.user_answer || '-' }}</strong>
          </div>

          <div class="result-row">
            <span>정답</span>
            <strong>{{ item.correct_answer }}</strong>
          </div>

          <div class="result-row">
            <span>유형</span>
            <strong>{{ item.problem_subtype }}</strong>
          </div>

          <div class="result-row">
            <span>난이도</span>
            <strong>{{ item.difficulty }}</strong>
          </div>

          <div v-if="item.explanation" class="explanation-box">
            <h3>해설</h3>
            <p>{{ item.explanation }}</p>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

const props = defineProps({
  sessionId: {
    type: String,
    required: true,
  },
})

const result = ref(null)

const accuracyPercent = computed(() => {
  if (!result.value) return 0
  return Math.round(result.value.accuracy * 100)
})

onMounted(() => {
  const savedResult = sessionStorage.getItem(`quiz-result-${props.sessionId}`)

  if (savedResult) {
    result.value = JSON.parse(savedResult)
  }
})
</script>