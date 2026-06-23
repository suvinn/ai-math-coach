<!-- 📄 src/components/common/WdsIcon.vue -->
<script setup>
// wds-icons.js가 body에 주입한 SVG 스프라이트(#i-<name>)를 참조.
// 프로토타입의 <Icon name="graduation" size=.. color=.. /> 와 동일 역할.
const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 22 },
  color: { type: String, default: 'currentColor' },
})
</script>

<template>
  <svg
    :width="size"
    :height="size"
    :style="{ color, flex: 'none' }"
    aria-hidden="true"
  >
    <use :href="`#i-${name}`" />
  </svg>
</template>