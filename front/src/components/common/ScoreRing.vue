<!-- 📄 src/components/common/ScoreRing.vue -->
<script setup>
import { computed } from 'vue'

// 프로토타입 ScoreRing: 원형 점수 게이지.
const props = defineProps({
  pct: { type: Number, required: true },
  tone: { type: String, default: 'var(--suql-accent)' },
  label: { type: String, default: '' },
})

const R = 58
const C = 2 * Math.PI * R
const offset = computed(() => C * (1 - props.pct / 100))
</script>

<template>
  <div class="score-ring">
    <svg width="132" height="132" viewBox="0 0 132 132">
      <circle cx="66" cy="66" :r="R" fill="none" stroke="var(--fill-normal)" stroke-width="11" />
      <circle
        cx="66"
        cy="66"
        :r="R"
        fill="none"
        :stroke="tone"
        stroke-width="11"
        stroke-linecap="round"
        :stroke-dasharray="C"
        :stroke-dashoffset="offset"
        transform="rotate(-90 66 66)"
      />
    </svg>
    <div class="pct">
      <span style="font: var(--weight-bold) 34px/1 var(--font-sans); letter-spacing: -0.03em">
        {{ pct }}<span style="font-size: 18px">점</span>
      </span>
      <span v-if="label" class="wds-caption-1 assistive" style="margin-top: 4px">{{ label }}</span>
    </div>
  </div>
</template>