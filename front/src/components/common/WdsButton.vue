<!-- 📄 src/components/common/WdsButton.vue -->
<script setup>
import WdsIcon from './WdsIcon.vue'

// 프로토타입 WDS Button 재현.
// variant: primary | secondary | text   size: large | medium
// block: 가로 100%, iconRight: 오른쪽 아이콘 이름
const props = defineProps({
  variant: { type: String, default: 'primary' },
  size: { type: String, default: 'large' },
  block: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  iconRight: { type: String, default: '' },
  iconLeft: { type: String, default: '' },
  type: { type: String, default: 'button' },
})
const emit = defineEmits(['click'])
</script>

<template>
  <button
    :type="type"
    class="wds-btn"
    :class="[`v-${variant}`, `s-${size}`, { block }]"
    :disabled="disabled"
    @click="emit('click')"
  >
    <WdsIcon v-if="iconLeft" :name="iconLeft" :size="size === 'large' ? 19 : 17" />
    <span class="wds-btn-label"><slot /></span>
    <WdsIcon v-if="iconRight" :name="iconRight" :size="size === 'large' ? 19 : 17" />
  </button>
</template>

<style scoped>
.wds-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: none;
  cursor: pointer;
  font-family: var(--font-sans);
  font-weight: var(--weight-semibold);
  letter-spacing: -0.01em;
  border-radius: 14px;
  transition: transform 0.12s var(--ease-out), background 0.15s, opacity 0.15s;
  white-space: nowrap;
}
.wds-btn:active:not(:disabled) {
  transform: scale(0.98);
}
.wds-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.wds-btn.block {
  width: 100%;
}

/* sizes */
.s-large {
  height: 54px;
  padding: 0 20px;
  font-size: 16px;
}
.s-medium {
  height: 44px;
  padding: 0 16px;
  font-size: 14px;
}

/* variants */
.v-primary {
  background: var(--suql-accent);
  color: #fff;
}
.v-primary:hover:not(:disabled) {
  background: var(--suql-accent-strong);
}
.v-secondary {
  background: var(--fill-normal);
  color: var(--label-normal);
}
.v-secondary:hover:not(:disabled) {
  background: var(--line-normal-alternative);
}
.v-text {
  background: transparent;
  color: var(--label-alternative);
}
.v-text:hover:not(:disabled) {
  background: var(--fill-alternative);
}
</style>