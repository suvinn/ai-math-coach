<!-- 📄 src/components/common/AppShell.vue -->
<script setup>
import { useSlots, computed } from 'vue'
import StatusBar from './StatusBar.vue'
import TabBar from './TabBar.vue'
import Toast from './Toast.vue'

// 프로토타입 PhoneLive: 상태바 + 토스트 + 본문 + (foot) + (탭바/홈 인디케이터).
// 본문은 기본 slot, 하단 고정 영역은 #foot slot, 탭은 tab prop으로 지정.
const props = defineProps({
  tab: { type: String, default: '' }, // '' 면 탭바 없음
  toast: { type: Object, default: null },
})

const slots = useSlots()
const hasFoot = computed(() => !!slots.foot)
</script>

<template>
  <div class="ph ph--live">
    <slot />
  </div>
</template>