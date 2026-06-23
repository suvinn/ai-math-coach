<!-- 📄 src/components/common/InlineTex.vue -->
<script setup>
import { computed } from 'vue'
import KatexRenderer from './KatexRenderer.vue'

// 평문에 섞인 $...$ 수식을 분리해서 렌더링. (QuizStem의 백엔드 평문 처리와 동일 로직)
const props = defineProps({
  text: { type: String, default: '' },
})

const parts = computed(() => {
  const text = props.text
  if (!text) return []
  const result = []
  const re = /\$([^$]+)\$/g
  let last = 0
  let m
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) result.push({ type: 'text', value: text.slice(last, m.index) })
    result.push({ type: 'tex', value: m[1] })
    last = m.index + m[0].length
  }
  if (last < text.length) result.push({ type: 'text', value: text.slice(last) })
  return result
})
</script>

<template>
  <template v-for="(p, i) in parts" :key="i">
    <KatexRenderer v-if="p.type === 'tex'" :tex="p.value" />
    <template v-else>{{ p.value }}</template>
  </template>
</template>
