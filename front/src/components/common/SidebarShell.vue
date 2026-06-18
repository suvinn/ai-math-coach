<!-- 📄 src/components/common/SidebarShell.vue -->
<script setup>
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import Logo from './Logo.vue'
import WdsIcon from './WdsIcon.vue'

// 데스크톱 웹 셸: 상단바 + 좌측 사이드바 + 메인. shell.css의 .app-shell 레이아웃을 사용.
const props = defineProps({
  tab: { type: String, default: 'home' }, // home | learn | report | my
})

const auth = useAuthStore()

const navItems = [
  { id: 'home', label: '홈', icon: 'home', to: '/' },
  { id: 'learn', label: '학습', icon: 'write', to: '/quiz/setup' },
  { id: 'report', label: '분석', icon: 'sparkle', to: '/my/history' },
  { id: 'my', label: '마이', icon: 'nav-mypage', to: '/my' },
]

const initial = computed(() => (auth.user?.name || '학생').slice(0, 1))
</script>

<template>
  <div class="app-shell">
    <header class="app-topbar">
      <Logo />
      <span class="spacer" />
      <div class="actions">
        <slot name="actions" />
      </div>
    </header>

    <aside class="app-sidebar">
      <nav class="app-nav">
        <router-link
          v-for="item in navItems"
          :key="item.id"
          :to="item.to"
          class="app-nav-item"
          :data-active="item.id === tab"
        >
          <span class="ico"><WdsIcon :name="item.icon" :size="20" /></span>
          <span class="label">{{ item.label }}</span>
        </router-link>
      </nav>
      <span class="app-nav-spacer" />
      <button class="app-nav-profile">
        <span class="avatar">{{ initial }}</span>
        <span class="meta">
          <div class="name">{{ auth.user?.name || '학생' }}</div>
        </span>
      </button>
    </aside>

    <main class="app-main">
      <slot />
    </main>
  </div>
</template>
