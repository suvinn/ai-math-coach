<!-- 📄 src/views/my/HistoryView.vue -->
<script setup>
import { ref, computed, onMounted } from 'vue'
import api, { unwrap } from '@/api'
import SidebarShell from '@/components/common/SidebarShell.vue'
import WdsIcon from '@/components/common/WdsIcon.vue'

const loading = ref(true)
const data = ref(null)

const SESSION_TYPE_LABEL = {
  normal: '1차 풀이',
  review_1: '보완 1차',
  review_2: '보완 2차',
}

function formatDate(iso) {
  return iso ? iso.slice(0, 10) : ''
}

// 필터 상태
const selectedMajor = ref(null)  // null = 전체
const selectedMiddle = ref(null)

// 대단원 목록 (중복 제거, 오름차순)
const majorList = computed(() => {
  if (!data.value) return []
  const set = new Set(data.value.subtype_mastery.map(m => m.chapter_major).filter(Boolean))
  return [...set].sort()
})

// 선택된 대단원 기준 소단원 목록
const middleList = computed(() => {
  if (!data.value) return []
  const set = new Set(
    data.value.subtype_mastery
      .filter(m => !selectedMajor.value || m.chapter_major === selectedMajor.value)
      .map(m => m.chapter_middle)
      .filter(Boolean)
  )
  return [...set].sort()
})

// 대단원 선택 시 소단원 초기화
function selectMajor(major) {
  selectedMajor.value = major
  selectedMiddle.value = null
}

// 필터 + 정렬 적용된 목록
const filteredMastery = computed(() => {
  if (!data.value) return []
  return data.value.subtype_mastery
    .filter(m => {
      if (selectedMajor.value && m.chapter_major !== selectedMajor.value) return false
      if (selectedMiddle.value && m.chapter_middle !== selectedMiddle.value) return false
      return true
    })
    .slice()
    .sort((a, b) => {
      const ma = a.chapter_major || ''
      const mb = b.chapter_major || ''
      if (ma !== mb) return ma.localeCompare(mb, 'ko')
      const ca = a.chapter_middle || ''
      const cb = b.chapter_middle || ''
      if (ca !== cb) return ca.localeCompare(cb, 'ko')
      return (a.problem_subtype || '').localeCompare(b.problem_subtype || '', 'ko')
    })
})

onMounted(async () => {
  try {
    data.value = unwrap(await api.get('/users/me/history'))
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <SidebarShell tab="report">
    <div class="page">
      <div class="page-head"><div class="title">학습 이력</div></div>

      <div v-if="loading" class="hist-loading">
        <p class="assistive">불러오는 중…</p>
      </div>

      <template v-else-if="data">
        <div class="stack-12" style="margin-bottom: 32px">
          <div class="wds-label-1" style="font-weight: 700; font-size: 22px;">유형별 마스터 현황</div>
          <div v-if="!data.subtype_mastery.length" class="assistive wds-body-2">아직 학습 기록이 없어요.</div>
          <template v-else>
            <!-- 대단원 필터 -->
            <div class="filter-row">
              <button class="filter-chip" :data-active="selectedMajor === null" @click="selectMajor(null)">전체</button>
              <button
                v-for="major in majorList" :key="major"
                class="filter-chip" :data-active="selectedMajor === major"
                @click="selectMajor(major)">{{ major }}</button>
            </div>
            <!-- 소단원 필터 (대단원 선택 시에만 표시) -->
            <div v-if="selectedMajor" class="filter-row">
              <button class="filter-chip filter-chip--sub" :data-active="selectedMiddle === null" @click="selectedMiddle = null">전체</button>
              <button
                v-for="middle in middleList" :key="middle"
                class="filter-chip filter-chip--sub" :data-active="selectedMiddle === middle"
                @click="selectedMiddle = middle">{{ middle }}</button>
            </div>
            <!-- 카드 목록 -->
            <div class="card-grid cols-3">
              <div v-for="m in filteredMastery" :key="m.problem_subtype" class="mastery-card">
                <div class="between" style="align-items: center">
                  <span class="master-badge" :data-on="m.mastered" :data-level="m.level">
                    <WdsIcon v-if="m.level === '숙달'" name="crown" :size="13" color="currentColor" />
                    <WdsIcon v-else-if="m.level === '연습 중'" name="fire" :size="13" color="currentColor" />
                    <WdsIcon v-else name="bulb" :size="13" color="currentColor" />
                    {{ m.level }}
                  </span>
                  <template v-if="m.accuracy_before != null && m.accuracy_after != null">
                    <span class="rate-jump">
                      <span class="was">{{ m.accuracy_before }}%</span>
                      <WdsIcon name="arrow-right" :size="14" color="var(--label-assistive)" />
                      <span class="now">{{ m.accuracy_after }}%</span>
                    </span>
                  </template>
                  <span v-else class="wds-caption-1" style="color: var(--suql-accent); font-weight: 600; font-size: 14px">정답률 {{ m.accuracy }}%</span>
                </div>
                <div class="wds-caption-1 assistive" style="margin-top: 10px; font-size: 14px">
                  {{ m.chapter_major }}<template v-if="m.chapter_middle"> › {{ m.chapter_middle }}</template>
                </div>
                <div class="wds-label-1" style="font-weight: 700; margin-top: 2px; font-size: 16px">{{ m.problem_subtype }}</div>
                <div class="wds-caption-1 assistive" style="margin-top: 6px; font-size: 13px">{{ m.total_attempts }} / {{ m.total_in_subtype }}문제 시도</div>
              </div>
            </div>
          </template>
        </div>

        <div class="stack-12">
          <div class="wds-label-1" style="font-weight: 700; font-size: 22px">퀴즈 기록</div>
          <div v-if="!data.sessions.length" class="assistive wds-body-2">아직 풀어본 퀴즈가 없어요.</div>
          <div v-else class="stack-8">
            <div v-for="s in data.sessions" :key="s.session_id" class="session-row">
              <span class="play-badge play-badge--type">{{ SESSION_TYPE_LABEL[s.session_type] || s.session_type }}</span>
              <div style="flex: 1; min-width: 0">
                <div class="wds-label-1" style="font-weight: 600">
                  {{ s.chapter_middle }}<template v-if="s.chapter_minor"> · {{ s.chapter_minor }}</template>
                </div>
                <div class="wds-caption-1 assistive" style="margin-top: 2px">{{ formatDate(s.created_at) }}</div>
              </div>
              <div class="session-score">{{ s.score }} / {{ s.total }}</div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </SidebarShell>
</template>

<style scoped>
.hist-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
}
.mastery-card {
  padding: 18px;
  border-radius: 16px;
  box-shadow: inset 0 0 0 1px var(--line-normal-normal);
}
.session-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border-radius: 14px;
  box-shadow: inset 0 0 0 1px var(--line-normal-normal);
}
.session-score {
  font: var(--weight-bold) 15px/1 var(--font-sans);
  color: var(--suql-accent);
  flex: none;
}
.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.filter-chip {
  padding: 6px 14px;
  border-radius: var(--radius-full);
  border: 0;
  background: var(--fill-alternative);
  color: var(--label-alternative);
  font: var(--weight-medium) 15px/1 var(--font-sans);
  cursor: pointer;
  transition: background .12s, color .12s;
}
.filter-chip:hover {
  background: var(--fill-normal);
}
.filter-chip[data-active="true"] {
  background: var(--suql-accent);
  color: #fff;
}
.filter-chip--sub {
  font-size: 15px;
  padding: 5px 12px;
  background: var(--background-normal-alternative);
}
.filter-chip--sub[data-active="true"] {
  background: var(--blue-90);
  color: var(--suql-accent);
}
</style>