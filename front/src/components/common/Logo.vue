<!-- 📄 src/components/common/Logo.vue -->
<script setup>
import WdsIcon from './WdsIcon.vue'

const props = defineProps({
  size: { type: Number, default: 26 },
})
</script>

<template>
  <span class="row" style="gap: 7px">
    <span
      :style="{
        width: size + 'px',
        height: size + 'px',
        borderRadius: '8px',
        flex: 'none',
        background: 'var(--suql-accent)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }"
    >
      <WdsIcon name="graduation" :size="Math.round(size * 0.62)" color="#fff" />
    </span>
    <span
      style="
        font: var(--weight-bold) 19px/1 var(--font-sans);
        letter-spacing: -0.01em;
        white-space: nowrap;
      "
      >WIDN Math</span
    >
  </span>
</template>