<!-- 📄 src/components/common/QuizOption.vue -->
<script setup>
import KatexRenderer from './KatexRenderer.vue'
import WdsIcon from './WdsIcon.vue'

// 프로토타입 Option: 번호 + 본문(tex 또는 슬롯) + 상태 아이콘.
// state: '' | 'selected' | 'correct' | 'wrong'
const props = defineProps({
  index: { type: Number, required: true },
  state: { type: String, default: '' },
  tex: { type: String, default: '' },
})
const emit = defineEmits(['click'])
</script>

<template>
  <button class="opt" :data-state="state || ''" @click="emit('click')">
    <span class="num">{{ index + 1 }}</span>
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