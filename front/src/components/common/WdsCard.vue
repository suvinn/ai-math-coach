<!-- 📄 src/components/common/WdsCard.vue -->
<script setup>
// 프로토타입 WDS Card 재현.
// padding: sm | md | lg, elevation: ring(테두리) | none, interactive: 클릭 가능
const props = defineProps({
  padding: { type: String, default: 'md' },
  elevation: { type: String, default: 'ring' },
  interactive: { type: Boolean, default: false },
})
const emit = defineEmits(['click'])
</script>

<template>
  <div
    class="wds-card"
    :class="[`p-${padding}`, `e-${elevation}`, { interactive }]"
    @click="interactive && emit('click')"
  >
    <slot />
  </div>
</template>

<style scoped>
.wds-card {
  background: var(--background-normal-normal);
  border-radius: 16px;
}
.e-ring {
  box-shadow: inset 0 0 0 1px var(--line-normal-normal);
}
.p-sm {
  padding: 14px;
}
.p-md {
  padding: 18px;
}
.p-lg {
  padding: 22px;
}
.interactive {
  cursor: pointer;
  transition: transform 0.12s var(--ease-out), box-shadow 0.15s;
}
.interactive:active {
  transform: scale(0.99);
}
.interactive:hover {
  box-shadow: inset 0 0 0 1px var(--line-normal-strong);
}
</style>