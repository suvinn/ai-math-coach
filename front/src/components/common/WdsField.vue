<!-- 📄 src/components/common/WdsField.vue -->
<script setup>
// 라벨 + 입력 필드. 로그인/회원가입 폼에서 사용.
const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, default: '' },
  type: { type: String, default: 'text' },
  placeholder: { type: String, default: '' },
  autocomplete: { type: String, default: 'off' },
})
const emit = defineEmits(['update:modelValue', 'enter'])
</script>

<template>
  <label class="wds-field">
    <span v-if="label" class="field-label">{{ label }}</span>
    <input
      class="wds-input"
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      :autocomplete="autocomplete"
      @input="emit('update:modelValue', $event.target.value)"
      @keyup.enter="emit('enter')"
    />
  </label>
</template>

<style scoped>
.wds-field {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.field-label {
  font: var(--weight-semibold) 14px/1 var(--font-sans);
  color: var(--label-alternative);
  letter-spacing: -0.01em;
}
.wds-input {
  height: 52px;
  padding: 0 16px;
  border-radius: 13px;
  border: none;
  background: var(--fill-normal);
  font: var(--weight-medium) 16px/1 var(--font-sans);
  color: var(--label-normal);
  outline: none;
  transition: box-shadow 0.15s;
}
.wds-input::placeholder {
  color: var(--label-assistive);
  font-weight: var(--weight-regular);
}
.wds-input:focus {
  box-shadow: inset 0 0 0 1.5px var(--suql-accent);
  background: var(--background-normal-normal);
}
</style>