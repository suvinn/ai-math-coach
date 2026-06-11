<template>
  <section class="page">
    <h1>퀴즈 풀기</h1>
    <p>세션 ID: {{ sessionId }}</p>
  </section>
</template>

<script setup>
defineProps({
  sessionId: {
    type: String,
    required: true,
  },
})
</script>