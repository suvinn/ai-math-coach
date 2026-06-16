<!-- 📄 src/App.vue -->
<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

// 프로토타입과 동일하게 360×820 폰을 뷰포트에 맞춰 스케일.
const scale = ref(1)

function fit() {
  const s = Math.min(
    1,
    (window.innerHeight - 36) / 820,
    (window.innerWidth - 24) / 360,
  )
  scale.value = s
}

onMounted(() => {
  // 강조색을 프로토타입 기본값(원티드 블루)으로 고정
  document.body.dataset.accent = '1'
  document.body.style.setProperty('--suql-accent', '#3366FF')
  document.body.style.setProperty('--suql-accent-strong', '#2456E6')
  fit()
  window.addEventListener('resize', fit)
})

onUnmounted(() => {
  window.removeEventListener('resize', fit)
})
</script>

<template>
  <div class="stage">
    <div class="stagescale" :style="{ transform: `scale(${scale})` }">
      <router-view v-slot="{ Component }">
        <transition name="screen" mode="out-in">
          <component :is="Component" class="screen" />
        </transition>
      </router-view>
    </div>
  </div>
</template>