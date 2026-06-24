<!-- 📄 src/components/review/ReviewResumeBanner.vue -->
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

const remainingCount = computed(() => {
  if (!resumeData.value) return 0
  return resumeData.value.reviewSubtypes.length - resumeData.value.resumeFromIdx
})

const nextSubtypeName = computed(() => {
  if (!resumeData.value) return ''
  return resumeData.value.reviewSubtypes[resumeData.value.resumeFromIdx]?.problemSubtype || ''
})

function resume() {
  const d = resumeData.value
  quiz.parentSessionId   = d.parentSessionId
  quiz.reviewSubtypes    = d.reviewSubtypes
  quiz.reviewSubtypeIdx  = d.resumeFromIdx
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
      <div class="resume-text">
        <div class="resume-title">오답 이어풀기</div>
        <div class="wds-body-2 resume-sub">
          {{ nextSubtypeName }} 외 {{ remainingCount }}개 남음
        </div>
      </div>
    </div>
    <div class="resume-actions">
      <button class="dismiss-btn" @click="dismiss">
        <WdsIcon name="xmark" :size="14" color="var(--label-assistive)" />
      </button>
      <WdsButton class="resume-btn" variant="primary" size="large" icon-right="arrow-right" @click="resume">
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
  padding: 28px 32px;
  border-radius: 16px;
  background: linear-gradient(105deg, #ddeeff 0%, #ffffff 100%);
  border: 1px solid #d0e8f9;
}
.resume-left {
  display: flex;
  align-items: center;
  min-width: 0;
}
.resume-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.resume-title {
  font: var(--weight-bold) 20px/1.4 var(--font-sans);
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
.resume-sub { color: var(--label-assistive); margin-top: 2px; }
.resume-btn { min-width: 148px; }
</style>