<!-- 📄 src/views/quiz/QuizPlayView.vue -->
<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useQuizStore } from '@/stores/quiz'
import { useToast } from '@/composables/useToast'
import AppShell from '@/components/common/AppShell.vue'
import AppBar from '@/components/common/AppBar.vue'
import ProgressBar from '@/components/common/ProgressBar.vue'
import QuizStem from '@/components/quiz/QuizStem.vue'
import WdsButton from '@/components/common/WdsButton.vue'
import WdsField from '@/components/common/WdsField.vue'

const router = useRouter()
const quiz = useQuizStore()
const { toast, showToast } = useToast()

// 세션이 없으면(직접 URL 진입 등) 설정 화면으로 돌려보냄
if (!quiz.problems.length) {
  router.replace('/quiz/setup')
}

const idx = ref(0)
const answer = ref('')
const submitting = ref(false)

const total = computed(() => quiz.problems.length)
const current = computed(() => quiz.problems[idx.value] || null)
const isLast = computed(() => idx.value + 1 >= total.value)

function next() {
  if (!answer.value.trim()) {
    showToast('답을 입력해주세요', 'negative', 'circle-exclamation')
    return
  }
  // 현재 답 저장
  quiz.setAnswer(current.value.problem_id, answer.value.trim())

  if (isLast.value) {
    finish()
  } else {
    idx.value += 1
    // 다음 문제에 기존 답 있으면 복원
    answer.value = quiz.answers[quiz.problems[idx.value].problem_id] || ''
  }
}

function prev() {
  if (idx.value === 0) return
  // 현재 답 저장 후 이전으로
  if (answer.value.trim()) {
    quiz.setAnswer(current.value.problem_id, answer.value.trim())
  }
  idx.value -= 1
  answer.value = quiz.answers[quiz.problems[idx.value].problem_id] || ''
}

async function finish() {
  submitting.value = true
  try {
    await quiz.submit()
    router.push('/quiz/result')
  } catch (e) {
    const msg = e?.response?.data?.message || '제출에 실패했어요'
    showToast(msg, 'negative', 'circle-exclamation')
    submitting.value = false
  }
}
</script>

<template>
  <AppShell :toast="toast">
    <AppBar title="퀴즈" back @back="router.push('/')">
      <template #action>
        <span class="wds-label-2 assistive" style="padding-right: 8px">
          {{ idx + 1 }} / {{ total }}
        </span>
      </template>
    </AppBar>

    <div v-if="current" class="ph-body play-body">
      <ProgressBar :value="idx + 1" :total="total" />

      <div class="row" style="gap: 6px; flex-wrap: wrap">
        <span class="play-badge play-badge--type">{{ current.problem_subtype }}</span>
        <span
          class="play-badge"
          :data-tone="current.difficulty === '하' ? 'positive' : 'neutral'"
        >
          난이도 {{ current.difficulty }}
        </span>
      </div>

      <QuizStem :q="current" />

      <!-- 보기가 이미지로 들어간 경우 안내 (bbox 있을 때) -->
      <div v-if="current.question_with_options" class="play-options">
        {{ current.question_with_options }}
      </div>

      <!-- 답 입력 (선택지가 비정형이라 직접 입력) -->
      <div class="answer-box">
        <div class="field-label">정답 입력</div>
        <WdsField
          v-model="answer"
          placeholder="답을 입력하세요 (예: ㄹ, ②, 3)"
          @enter="next"
        />
      </div>
    </div>

    <template #foot>
      <div class="play-foot">
        <WdsButton
          v-if="idx > 0"
          variant="secondary"
          size="large"
          @click="prev"
        >
          이전
        </WdsButton>
        <WdsButton
          variant="primary"
          size="large"
          block
          :disabled="submitting"
          @click="next"
        >
          {{ isLast ? (submitting ? '제출 중…' : '제출하기') : '다음' }}
        </WdsButton>
      </div>
    </template>
  </AppShell>
</template>

<style scoped>
.play-body {
  overflow-y: auto;
  gap: 18px;
}
.play-badge {
  padding: 5px 10px;
  border-radius: var(--radius-full);
  font: var(--weight-semibold) 12px/1 var(--font-sans);
  background: var(--fill-normal);
  color: var(--label-alternative);
}
.play-badge--type {
  background: var(--blue-99);
  color: var(--suql-accent);
}
.play-badge[data-tone='positive'] {
  background: var(--green-99);
  color: var(--status-positive);
}
.play-options {
  background: var(--fill-alternative);
  border-radius: 14px;
  padding: 16px;
  font: var(--weight-regular) 14px/1.7 var(--font-sans);
  color: var(--label-normal);
  white-space: pre-wrap;
}
.answer-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.field-label {
  font: var(--weight-semibold) 13px/1 var(--font-sans);
  color: var(--label-alternative);
}
.play-foot {
  display: flex;
  gap: 10px;
}
</style>