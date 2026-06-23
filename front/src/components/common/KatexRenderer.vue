<!-- 📄 src/components/common/KatexRenderer.vue -->
<script setup>
import { ref, watch, onMounted } from 'vue'

// common.jsx의 Katex 컴포넌트를 Vue로 변환.
// display=true → 블록(div), false → 인라인(span)
const props = defineProps({
  tex: { type: String, required: true },
  display: { type: Boolean, default: false },
})

const el = ref(null)

function render() {
  if (!el.value) return
  if (window.katex) {
    try {
      window.katex.render(props.tex, el.value, {
        displayMode: props.display,
        throwOnError: false,
        output: 'html',
      })
    } catch {
      el.value.textContent = props.tex
    }
  } else {
    // KaTeX 스크립트(defer)가 아직 로드 전이면 원문을 잠깐 표시하고,
    // 로드되면 다시 렌더링한다.
    el.value.textContent = props.tex
    const wait = setInterval(() => {
      if (window.katex) {
        clearInterval(wait)
        render()
      }
    }, 50)
    setTimeout(() => clearInterval(wait), 3000)
  }
}

onMounted(render)
watch(() => [props.tex, props.display], render)
</script>

<template>
  <component :is="display ? 'div' : 'span'" ref="el" />
</template>