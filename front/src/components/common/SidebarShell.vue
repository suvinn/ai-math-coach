<!-- 📄 src/components/common/SidebarShell.vue -->
<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api, { unwrap } from '@/api'
import Logo from './Logo.vue'
import WdsIcon from './WdsIcon.vue'
import NotificationBell from './NotificationBell.vue'

const props = defineProps({
  tab: { type: String, default: 'home' },
})

const router = useRouter()
const auth = useAuthStore()

const navItems = [
  { id: 'home',   label: '홈',   icon: 'home',        to: '/' },
  { id: 'learn',  label: '학습', icon: 'write',       to: null },
  { id: 'report', label: '분석', icon: 'sparkle',     to: '/my/history' },
  { id: 'my',     label: '마이', icon: 'nav-mypage',  to: '/my' },
]

function handleNavClick(item) {
  if (item.id === 'learn') {
    router.push({ path: '/quiz/setup', query: { t: Date.now() } })
  } else {
    router.push(item.to)
  }
}

const initial = computed(() => (auth.user?.name || '학생').slice(0, 1))

// 사이드바 통계
const streak = ref(0)
const solvingCount = ref(0)

onMounted(async () => {
  try {
    const data = unwrap(await api.get('/users/me/dashboard'))
    streak.value = data?.streak ?? 0
    solvingCount.value = data?.solving_count ?? 0
  } catch {
    // 실패해도 그대로
  }
})

// 프로필 메뉴
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
        <NotificationBell />
      </div>
    </header>

    <aside class="app-sidebar">
      <div class="app-nav-scroll">
        <nav class="app-nav">
          <button
            v-for="item in navItems"
            :key="item.id"
            class="app-nav-item"
            :data-active="item.id === tab"
            @click="handleNavClick(item)"
          >
            <span class="ico"><WdsIcon :name="item.icon" :size="20" /></span>
            <span class="label">{{ item.label }}</span>
          </button>
        </nav>
      </div>

      <!-- 프로필 위 통계 -->
      <div class="sidebar-stats">
        <div class="sidebar-stat">
          <WdsIcon name="calendar" :size="13" color="#8b5cf6" />
          <span class="sidebar-stat-label">연속 학습</span>
          <span class="sidebar-stat-val">{{ streak }}일</span>
        </div>
        <div class="sidebar-stat-divider" />
        <div class="sidebar-stat">
          <WdsIcon name="fire" :size="13" color="#d4700a" />
          <span class="sidebar-stat-label">풀이 중인 유형</span>
          <span class="sidebar-stat-val">{{ solvingCount }}개</span>
        </div>
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

<style scoped>
.sidebar-stats {
  padding: 12px 14px;
  margin: 0 8px 8px;
  border-radius: 12px;
  background: var(--fill-alternative, #f5f5f5);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sidebar-stat {
  display: flex;
  align-items: center;
  gap: 6px;
}
.sidebar-stat-label {
  font-size: 14px;
  color: var(--label-assistive);
  flex: 1;
}
.sidebar-stat-val {
  font-size: 17px;
  font-weight: var(--weight-bold);
  color: var(--label-normal);
  letter-spacing: -0.02em;
}
.sidebar-stat-divider {
  height: 1px;
  background: var(--line-normal, #e2e2e2);
}
.app-nav-profile .avatar { font-size: 17px; }
.app-nav-profile .name { font-size: 18px; }
</style>