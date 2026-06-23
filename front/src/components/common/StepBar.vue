<!-- 📄 src/components/common/StepBar.vue -->
<script setup>
// 프로토타입 StepBar: normal(0) → review_1(1) → review_2(2) 단계 표시.
const props = defineProps({
  stage: { type: Number, default: 0 },
})
const labels = ['1차', '보완 1', '보완 2']
</script>

<template>
  <div class="stack-8">
    <div class="steps">
      <span v-for="i in [0, 1, 2]" :key="i" class="seg" :data-on="i <= stage" />
    </div>
    <div class="row" style="justify-content: space-between">
      <span
        v-for="(l, i) in labels"
        :key="l"
        class="wds-caption-1"
        :style="{
          whiteSpace: 'nowrap',
          color: i <= stage ? 'var(--suql-accent)' : 'var(--label-assistive)',
          fontWeight: i === stage ? 700 : 500,
        }"
        >{{ l }}</span
      >
    </div>
  </div>
</template>