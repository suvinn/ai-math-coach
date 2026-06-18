<!-- 📄 src/components/quiz/QuizStem.vue -->
<script setup>
import { computed } from 'vue'
import KatexRenderer from '@/components/common/KatexRenderer.vue'
import InlineTex from '@/components/common/InlineTex.vue'

// 문제 줄기 렌더러. 두 가지 입력을 모두 지원:
//  (1) 프로토타입 샘플 구조: { prompt, promptTex, promptTail, eq }
//  (2) 백엔드 평문: { question_text } (인라인 수식이 $...$ 로 올 수 있음)
const props = defineProps({
  q: { type: Object, required: true },
})

// 프로토타입 샘플 구조 여부
const isSample = computed(() => !props.q.question_text && (props.q.prompt || props.q.promptTex || props.q.eq))
</script>

<template>
  <!-- (1) 프로토타입 샘플 구조 -->
  <template v-if="isSample">
    <div class="qstem">
      <template v-if="q.prompt">{{ q.prompt }}</template>
      <KatexRenderer v-if="q.promptTex" :tex="q.promptTex" />
      <template v-if="q.promptTail">{{ q.promptTail }}</template>
    </div>
    <div v-if="q.eq" class="q-eq"><KatexRenderer :tex="q.eq" display /></div>
  </template>

  <!-- (2) 백엔드 평문 (인라인 수식 분리 렌더링) -->
  <template v-else>
    <div class="qstem"><InlineTex :text="q.question_text" /></div>
  </template>
</template>