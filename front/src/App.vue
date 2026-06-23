<!-- 📄 src/App.vue -->
<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'

// 프로토타입과 동일하게 360×820 폰을 뷰포트에 맞춰 스케일.
// route.meta.shell === 'web' 인 화면은 폰 프레임 없이 일반 웹 레이아웃으로 렌더링.
const route = useRoute()
const isWeb = computed(() => route.meta.shell === 'web')
const scale = ref(1)

function fit() {
  // 폰(360×820)을 현재 창에 '온전히' 들어가도록 축소 비율 계산.
  // 세로·가로 중 더 빡빡한 쪽에 맞춰 잘림 없이 표시.
  const margin = 24
  const s = Math.min(
    (window.innerHeight - margin) / 820,
    (window.innerWidth - margin) / 360,
  )
  scale.value = Math.min(1, s)
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
  <router-view v-if="isWeb" />

  <div v-else class="stage">
    <div class="stagescale" :style="{ transform: `scale(${scale})` }">
      <router-view v-slot="{ Component }">
        <transition name="screen" mode="out-in">
          <component :is="Component" class="screen" />
        </transition>
      </router-view>
    </div>
  </div>
</template>