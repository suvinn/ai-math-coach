<!-- 📄 src/components/common/NotificationBell.vue -->
<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useNotifications } from '@/composables/useNotifications'
import WdsIcon from './WdsIcon.vue'

const router = useRouter()
const { notifications, hasUnread, isRead, markRead } = useNotifications()

const open = ref(false)

function toggle() {
  open.value = !open.value
}

function closeOnOutside(e) {
  if (!e.target.closest('.notif-bell-wrap')) open.value = false
}

onMounted(() => document.addEventListener('click', closeOnOutside))
onUnmounted(() => document.removeEventListener('click', closeOnOutside))

function handleNotifClick(notif) {
  markRead(notif.id)
  if (notif.actionRoute) {
    open.value = false
    router.push(notif.actionRoute)
  }
}
</script>

<template>
  <div class="notif-bell-wrap">
    <!-- 알림 버튼 -->
    <button
      class="notif-bell-btn"
      :class="{ 'is-open': open }"
      aria-label="알림"
      @click.stop="toggle"
    >
      <WdsIcon name="bell" :size="20" />
      <!-- 빨간 점: 읽지 않은 알림이 있을 때만 표시 -->
      <span v-if="hasUnread" class="notif-badge" aria-hidden="true" />
    </button>

    <!-- 드롭다운 -->
    <Transition name="notif-drop">
      <div v-if="open" class="notif-dropdown" role="menu">
        <div class="notif-header">
          <span class="notif-title">알림</span>
        </div>

        <ul v-if="notifications.length" class="notif-list">
          <li
            v-for="notif in notifications"
            :key="notif.id"
            class="notif-item"
            :class="{ 'is-read': isRead(notif.id) }"
            role="menuitem"
            @click="handleNotifClick(notif)"
          >
            <span class="notif-icon">{{ notif.icon }}</span>
            <div class="notif-body">
              <p class="notif-msg">{{ notif.message }}</p>
              <span v-if="notif.actionLabel && !isRead(notif.id)" class="notif-action">
                {{ notif.actionLabel }} →
              </span>
            </div>
            <!-- 읽지 않음 dot -->
            <span v-if="!isRead(notif.id)" class="notif-unread-dot" />
          </li>
        </ul>

        <div v-else class="notif-empty">
          새로운 알림이 없어요
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
/* ── 래퍼 ── */
.notif-bell-wrap {
  position: relative;
  display: inline-flex;
}

/* ── 버튼 ── */
.notif-bell-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: var(--label-normal);
  cursor: pointer;
  transition: background 0.15s;
}
.notif-bell-btn:hover,
.notif-bell-btn.is-open {
  background: var(--fill-normal, #f2f2f2);
}

/* 빨간 뱃지 dot */
.notif-badge {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #ff3b30;
  border: 1.5px solid #fff;
}

/* ── 드롭다운 ── */
.notif-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 300px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12), 0 0 0 1px rgba(0, 0, 0, 0.06);
  z-index: 200;
  overflow: hidden;
}

.notif-header {
  padding: 14px 16px 10px;
  border-bottom: 1px solid var(--line-normal-normal, #ebebeb);
}
.notif-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--label-normal);
  letter-spacing: -0.01em;
}

/* ── 리스트 ── */
.notif-list {
  list-style: none;
  margin: 0;
  padding: 6px 0;
}

.notif-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.12s;
  position: relative;
}
.notif-item:hover {
  background: var(--fill-normal, #f7f7f7);
}
.notif-item.is-read {
  opacity: 0.5;
  cursor: default;
}
.notif-item.is-read:hover {
  background: transparent;
}

.notif-icon {
  font-size: 20px;
  flex: none;
  line-height: 1.2;
  margin-top: 1px;
}

.notif-body {
  flex: 1;
  min-width: 0;
}
.notif-msg {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--label-normal);
  word-break: keep-all;
}
.notif-action {
  display: inline-block;
  margin-top: 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--suql-accent, #4f6ef7);
}

/* 읽지 않음 파란 dot */
.notif-unread-dot {
  flex: none;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--suql-accent, #4f6ef7);
  margin-top: 6px;
}

/* ── 비어있을 때 ── */
.notif-empty {
  padding: 24px 16px;
  text-align: center;
  font-size: 13px;
  color: var(--label-assistive);
}

/* ── 트랜지션 ── */
.notif-drop-enter-active,
.notif-drop-leave-active {
  transition: opacity 0.15s, transform 0.15s;
}
.notif-drop-enter-from,
.notif-drop-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>