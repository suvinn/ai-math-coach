<!-- 📄 src/components/common/QuizOption.vue -->
<script setup>
import { computed } from 'vue'
import KatexRenderer from './KatexRenderer.vue'
import WdsIcon from './WdsIcon.vue'

// 프로토타입 Option: 번호 + 본문(tex 또는 슬롯) + 상태 아이콘.
// state: '' | 'selected' | 'correct' | 'wrong'
// label이 있으면 그걸 그대로 표시(①②③ 등 — 채점용 원본 라벨), 없으면 index+1.
const props = defineProps({
  index: { type: Number, required: true },
  state: { type: String, default: '' },
  tex: { type: String, default: '' },
  label: { type: String, default: '' },
})
const emit = defineEmits(['click'])

// ①②③ 유니코드 원문자는 폰트에 따라 작은 아이콘처럼 깨져 보이므로,
// 배지 표시용으로는 숫자만 뽑아서 보여준다(채점/클릭 값은 label 그대로 사용).
const CIRCLED_TO_DIGIT = { '①': '1', '②': '2', '③': '3', '④': '4', '⑤': '5', '⑥': '6', '⑦': '7', '⑧': '8', '⑨': '9', '⑩': '10' }
const displayNum = computed(() => CIRCLED_TO_DIGIT[props.label] || props.label || props.index + 1)
</script>

<template>
  <button class="opt" :data-state="state || ''" @click="emit('click')">
    <span class="num">{{ displayNum }}</span>
    <span style="flex: 1">
      <KatexRenderer v-if="tex" :tex="tex" />
      <slot v-else />
    </span>
    <span v-if="state === 'correct'" class="tail">
      <WdsIcon name="circle-check" :size="20" color="var(--status-positive)" />
    </span>
    <span v-else-if="state === 'wrong'" class="tail">
      <WdsIcon name="circle-exclamation" :size="20" color="var(--status-negative)" />
    </span>
  </button>
</template>