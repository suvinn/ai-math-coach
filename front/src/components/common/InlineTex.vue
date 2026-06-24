<!-- 📄 src/components/common/InlineTex.vue -->
<script setup>
import { computed } from 'vue'
import KatexRenderer from './KatexRenderer.vue'

// 평문에 섞인 수식을 분리해서 렌더링.
// 지원 포맷:
//   $$...$$ → display (블록)
//   \[...\] → display (블록)
//   \(...\) → inline
//   $...$   → inline
const props = defineProps({
  text: { type: String, default: '' },
})

const parts = computed(() => {
  const text = props.text
  if (!text) return []
  const result = []
  // 순서 중요: $$ 를 $ 보다 먼저, \[...\] / \(...\) 도 함께 매칭
  const re = /\$\$([\s\S]*?)\$\$|\\\[([\s\S]*?)\\\]|\\\(([\s\S]*?)\\\)|\$([^\$\n]+)\$/g
  let last = 0
  let m
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) result.push({ type: 'text', value: text.slice(last, m.index) })
    if (m[1] !== undefined)
      result.push({ type: 'tex', value: m[1], display: true })       // $$...$$
    else if (m[2] !== undefined)
      result.push({ type: 'tex', value: m[2], display: true })       // \[...\]
    else if (m[3] !== undefined)
      result.push({ type: 'tex', value: m[3], display: false })      // \(...\)
    else
      result.push({ type: 'tex', value: m[4], display: false })      // $...$
    last = m.index + m[0].length
  }
  if (last < text.length) result.push({ type: 'text', value: text.slice(last) })
  return result
})
</script>

<template>
  <template v-for="(p, i) in parts" :key="i">
    <KatexRenderer v-if="p.type === 'tex'" :tex="p.value" :display="p.display" />
    <template v-else>{{ p.value }}</template>
  </template>
</template>
