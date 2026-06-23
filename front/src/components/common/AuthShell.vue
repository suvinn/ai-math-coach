<!-- 📄 src/components/common/AuthShell.vue -->
<script setup>
import Toast from './Toast.vue'

// 데스크톱 웹 셸: 가운데 정렬 카드 (로그인/회원가입). shell.css의 .auth-shell 레이아웃을 사용.
defineProps({
  toast: { type: Object, default: null },
})
</script>

<template>
  <div class="auth-shell">
    <div class="auth-card">
      <slot />
    </div>
    <Toast :toast="toast" />
  </div>
</template>
