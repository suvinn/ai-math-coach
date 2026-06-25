<!-- 📄 src/App.vue -->
<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const isWeb = computed(() => route.meta.shell === 'web')
const scale = ref(1)

function fit() {
  const margin = 24
  const s = Math.min(
    (window.innerHeight - margin) / 820,
    (window.innerWidth - margin) / 360,
  )
  scale.value = Math.min(1, s)
}

onMounted(() => {
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
  <router-view v-if="isWeb" :key="route.fullPath" />

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