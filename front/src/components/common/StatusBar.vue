<!-- 📄 src/components/common/StatusBar.vue -->
<script setup>
// 폰 상단 상태바 (9:41 + 신호/와이파이/배터리). 프로토타입 마크업 그대로.
</script>

<template>
  <div class="ph-status">
    <span>9:41</span>
    <span class="dots">
      <svg width="17" height="11" viewBox="0 0 17 11" fill="currentColor">
        <rect x="0" y="6" width="3" height="5" rx="1" />
        <rect x="4.5" y="4" width="3" height="7" rx="1" />
        <rect x="9" y="2" width="3" height="9" rx="1" />
        <rect x="13.5" y="0" width="3" height="11" rx="1" />
      </svg>
      <svg width="16" height="11" viewBox="0 0 16 11" fill="currentColor">
        <path d="M8 2.2c2 0 3.8.8 5.1 2l1.1-1.2A9 9 0 0 0 8 .5 9 9 0 0 0 1.8 3l1.1 1.2A7.3 7.3 0 0 1 8 2.2Z" />
        <path d="M8 5.4c1.1 0 2.2.45 3 1.2l1.1-1.2A6 6 0 0 0 8 3.7a6 6 0 0 0-4.1 1.7L5 6.6c.8-.75 1.9-1.2 3-1.2Z" opacity=".9" />
        <circle cx="8" cy="9" r="1.7" />
      </svg>
      <svg width="25" height="12" viewBox="0 0 25 12" fill="none">
        <rect x="0.5" y="0.5" width="21" height="11" rx="3" stroke="currentColor" opacity=".4" />
        <rect x="2" y="2" width="16" height="8" rx="1.5" fill="currentColor" />
        <rect x="23" y="4" width="1.5" height="4" rx="0.75" fill="currentColor" opacity=".4" />
      </svg>
    </span>
  </div>
</template>