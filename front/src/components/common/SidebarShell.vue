<!-- 📄 src/components/common/SidebarShell.vue -->
<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Logo from './Logo.vue'
import WdsIcon from './WdsIcon.vue'
import NotificationBell from './NotificationBell.vue'   // ← 추가

// 데스크톱 웹 셸: 상단바 + 좌측 사이드바 + 메인. shell.css의 .app-shell 레이아웃을 사용.
const props = defineProps({
  tab: { type: String, default: 'home' }, // home | learn | report | my
})

const router = useRouter()
const auth = useAuthStore()

const navItems = [
  { id: 'home',   label: '홈',   icon: 'home',        to: '/' },
  { id: 'learn',  label: '학습', icon: 'write',       to: '/quiz/setup' },
  { id: 'report', label: '분석', icon: 'sparkle',     to: '/my/history' },
  { id: 'my',     label: '마이', icon: 'nav-mypage',  to: '/my' },
]

const initial = computed(() => (auth.user?.name || '학생').slice(0, 1))

// 프로필 클릭 시 로그아웃 메뉴 토글 (바깥 클릭하면 닫힘)
const profileMenuOpen = ref(false)
function toggleProfileMenu() {
  profileMenuOpen.value = !profileMenuOpen.value
}
function closeProfileMenu(e) {
  if (!e.target.closest('.app-nav-profile-wrap')) profileMenuOpen.value = false
}
onMounted(() => document.addEventListener('click', closeProfileMenu))
onUnmounted(() => document.removeEventListener('click', closeProfileMenu))

async function handleLogout() {
  profileMenuOpen.value = false
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-shell">
    <header class="app-topbar">
      <Logo />
      <span class="spacer" />
      <div class="actions">
        <!-- 알림 벨 버튼 -->
        <NotificationBell />                            <!-- ← 추가 -->
      </div>
    </header>

    <aside class="app-sidebar">
      <div class="app-nav-scroll">
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
      </div>
      <div class="app-nav-profile-wrap">
        <div v-if="profileMenuOpen" class="app-nav-profile-menu">
          <button class="app-nav-profile-menu-item" @click="handleLogout">
            <WdsIcon name="close" :size="16" />
            로그아웃
          </button>
        </div>
        <button class="app-nav-profile" @click="toggleProfileMenu">
          <span class="avatar">{{ initial }}</span>
          <span class="meta">
            <div class="name">{{ auth.user?.name || '학생' }}</div>
          </span>
        </button>
      </div>
    </aside>

    <main class="app-main">
      <slot />
    </main>
  </div>
</template>