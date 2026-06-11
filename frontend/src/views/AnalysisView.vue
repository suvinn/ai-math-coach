<template>
  <section class="page">
    <h1>AI 분석</h1>
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