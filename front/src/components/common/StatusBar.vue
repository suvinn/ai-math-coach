<!-- 📄 src/components/common/TabBar.vue -->
<script setup>
import { useRouter } from 'vue-router'
import WdsIcon from './WdsIcon.vue'

// 하단 탭바. 프로토타입은 표시만 했지만 실제 라우팅 연결.
const props = defineProps({
  active: { type: String, default: 'home' }, // home | learn | report | my
})
const router = useRouter()

const tabs = [
  { id: 'home', label: '홈', icon: 'home', to: '/' },
  { id: 'learn', label: '학습', icon: 'write', to: '/quiz/setup' },
  { id: 'report', label: '분석', icon: 'sparkle', to: '/my/history' },
  { id: 'my', label: '마이', icon: 'nav-mypage', to: '/my' },
]

function go(tab) {
  if (tab.id !== props.active) router.push(tab.to)
}
</script>

<template>
  <div class="ph-tabbar">
    <button
      v-for="t in tabs"
      :key="t.id"
      class="ph-tab"
      :data-active="t.id === active"
      @click="go(t)"
    >
      <WdsIcon :name="t.icon" :size="23" />
      <span>{{ t.label }}</span>
    </button>
  </div>
</template>