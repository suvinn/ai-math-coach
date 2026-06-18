<!-- 📄 src/components/common/FocusShell.vue -->
<script setup>
import { computed, getCurrentInstance } from 'vue'
import { useRouter } from 'vue-router'
import Toast from './Toast.vue'

// 데스크톱 웹 셸: 상단 슬림바 + 좁은 컬럼 + 하단 CTA (문제 풀이/설정 전용).
// shell.css의 .focus-shell 레이아웃을 사용.
const props = defineProps({
  title: { type: String, default: '' },
  back: { type: Boolean, default: true },
  toast: { type: Object, default: null },
})
const emit = defineEmits(['back'])
const router = useRouter()

const instance = getCurrentInstance()
const hasBackListener = computed(() => !!instance?.vnode?.props?.onBack)

function handleBack() {
  if (hasBackListener.value) emit('back')
  else router.back()
}
</script>

<template>
  <div class="focus-shell">
    <header class="focus-topbar">
      <button v-if="back" class="back" @click="handleBack" aria-label="뒤로">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M15 5l-7 7 7 7" />
        </svg>
      </button>
      <span class="title">{{ title }}</span>
      <slot name="topbar" />
    </header>

    <main class="focus-body">
      <div class="page page--narrow">
        <slot />
      </div>
    </main>

    <footer v-if="$slots.foot" class="focus-foot">
      <div class="page page--narrow">
        <slot name="foot" />
      </div>
    </footer>

    <Toast :toast="toast" />
  </div>
</template>
