<!-- 📄 src/components/review/ReviewResumeBanner.vue -->
<!-- 오답 루프 도중 홈으로 나간 경우, 홈 화면 상단에 표시되는 이어하기 배너.
     localStorage에 reviewLoop_resume 키가 있을 때만 렌더링된다. -->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuizStore } from '@/stores/quiz'
import WdsButton from '@/components/common/WdsButton.vue'
import WdsIcon from '@/components/common/WdsIcon.vue'

const RESUME_KEY = 'reviewLoop_resume'

const router = useRouter()
const quiz = useQuizStore()

const resumeData = ref(null)

onMounted(() => {
  try {
    const raw = localStorage.getItem(RESUME_KEY)
    if (raw) resumeData.value = JSON.parse(raw)
  } catch {
    localStorage.removeItem(RESUME_KEY)
  }
})

// 남은 유형 수 계산
const remainingCount = computed(() => {
  if (!resumeData.value) return 0
  return resumeData.value.reviewSubtypes.length - resumeData.value.resumeFromIdx
})

// 다음 유형 이름
const nextSubtypeName = computed(() => {
  if (!resumeData.value) return ''
  return resumeData.value.reviewSubtypes[resumeData.value.resumeFromIdx]?.problemSubtype || ''
})

function resume() {
  const d = resumeData.value
  // store에 저장된 상태 복원
  quiz.parentSessionId   = d.parentSessionId
  quiz.reviewSubtypes    = d.reviewSubtypes
  quiz.reviewSubtypeIdx  = d.resumeFromIdx
  // localStorage는 ReviewPlayView의 continueToNextSubtype에서 지워짐
  router.push('/review/play')
}

function dismiss() {
  localStorage.removeItem(RESUME_KEY)
  resumeData.value = null
}
</script>

<template>
  <div v-if="resumeData" class="resume-banner">
    <div class="resume-left">
      <div class="resume-icon">
        <WdsIcon name="circle-check" :size="24" color="#fff" />
      </div>
      <div class="resume-text">
        <div class="wds-label-1 resume-title">오답 루프 이어서 풀기</div>
        <div class="wds-body-2 resume-sub">
          <span style="font-weight: 600">{{ nextSubtypeName }}</span>
          유형 외 {{ remainingCount }}개 남음
        </div>
      </div>
    </div>
    <div class="resume-actions">
      <button class="dismiss-btn" @click="dismiss">
        <WdsIcon name="xmark" :size="14" color="var(--label-assistive)" />
      </button>
      <WdsButton variant="primary" size="large" icon-right="arrow-right" @click="resume">
        이어서 풀기
      </WdsButton>
    </div>
  </div>
</template>

<style scoped>
.resume-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
  padding: 32px 40px;
  border-radius: 20px;
  background: var(--blue-99, #f0f4ff);
  border: 1.5px solid var(--suql-accent);
}
.resume-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.resume-icon {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--suql-accent);
  display: flex;
  align-items: center;
  justify-content: center;
}
.resume-icon :deep(svg) { color: #fff; }
.resume-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.resume-title {
  font: var(--weight-bold) 22px/1.4 var(--font-sans);
  letter-spacing: -0.02em;
  color: var(--label-normal);
}
.resume-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.dismiss-btn {
  background: none;
  border: none;
  padding: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  border-radius: 6px;
}
.dismiss-btn:hover { background: var(--fill-normal); }
.resume-sub { opacity: 0.6; margin-top: 2px; }
</style>