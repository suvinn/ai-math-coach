<!-- 📄 src/components/common/WeakRow.vue -->
<script setup>
// 프로토타입 WeakRow: 취약 유형 순위 + 이름 + 정답률 막대.
const props = defineProps({
  rank: { type: Number, required: true },
  name: { type: String, required: true },
  pct: { type: Number, required: true },
  tone: { type: String, required: true },
})
</script>

<template>
  <div class="stack-8">
    <div class="between">
      <span class="row" style="gap: 8px">
        <span
          :style="{
            width: '22px',
            height: '22px',
            borderRadius: '7px',
            flex: 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: tone,
            color: '#fff',
            font: 'var(--weight-bold) 12px/1 var(--font-sans)',
          }"
          >{{ rank }}</span
        >
        <span style="font: var(--weight-semibold) 15px/1.3 var(--font-sans)">{{ name }}</span>
      </span>
      <span :style="{ font: 'var(--weight-bold) 14px/1 var(--font-sans)', color: tone }">{{ pct }}%</span>
    </div>
    <div class="weakbar"><i :style="{ width: pct + '%', background: tone }" /></div>
  </div>
</template>