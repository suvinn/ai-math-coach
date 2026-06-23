<!-- 📄 src/components/common/ProgressBar.vue -->
<script setup>
import { computed } from 'vue'

// 프로토타입 Progress: 현재/전체 + 진행률 바.
const props = defineProps({
  value: { type: Number, required: true },
  total: { type: Number, required: true },
})

const pct = computed(() =>
  props.total ? Math.round((props.value / props.total) * 100) : 0,
)
</script>

<template>
  <div class="stack-8">
    <div class="between">
      <span style="font: var(--weight-bold) 14px/1 var(--font-sans); white-space: nowrap">
        <span style="color: var(--suql-accent)">{{ value }}</span>
        <span class="assistive"> / {{ total }}</span>
      </span>
      <span class="wds-caption-1 assistive" style="white-space: nowrap">진행률 {{ pct }}%</span>
    </div>
    <div class="prog"><i :style="{ width: pct + '%' }" /></div>
  </div>
</template>