<!-- 📄 src/views/my/HistoryView.vue -->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useQuizStore } from '@/stores/quiz'
import api, { unwrap } from '@/api'
import SidebarShell from '@/components/common/SidebarShell.vue'
import WdsIcon from '@/components/common/WdsIcon.vue'
import { resumeKey } from '@/utils/reviewResume'

const router = useRouter()
const auth   = useAuthStore()
const quiz   = useQuizStore()

const loading = ref(true)
const data    = ref(null)

// ── 이어하기 ─────────────────────────────────────────
const resumeData = computed(() => {
  if (!auth.user?.id) return null
  try {
    const raw = localStorage.getItem(resumeKey(auth.user.id))
    return raw ? JSON.parse(raw) : null
  } catch { return null }
})

function canResume(sessionId) {
  return resumeData.value?.parentSessionId === sessionId
}

function resumeSession(sessionId) {
  const d = resumeData.value
  if (!d || d.parentSessionId !== sessionId) return
  quiz.parentSessionId  = d.parentSessionId
  quiz.reviewSubtypes   = d.reviewSubtypes
  quiz.reviewSubtypeIdx = d.resumeFromIdx
  router.push('/review/play')
}
// ─────────────────────────────────────────────────────

const SESSION_TYPE_LABEL = {
  normal: '1차 풀이',
  review_1: '보완 1차',
  review_2: '보완 2차',
}

function formatDate(iso) {
  return iso ? iso.slice(0, 10) : ''
}

// ── 유형 필터 ─────────────────────────────────────────
const selectedMajor  = ref(null)
const selectedMiddle = ref(null)
const selectedLevel  = ref(null)
const MASTERY_PAGE_SIZE = 6
const masteryPage = ref(1)

const LEVEL_OPTIONS = [
  { label: '풀이 필요', icon: 'bulb' },
  { label: '풀이 중',   icon: 'fire' },
  { label: '풀이 완료', icon: 'circle-check' },
  { label: '숙달 완료', icon: 'medal' },
]

const majorList = computed(() => {
  if (!data.value) return []
  const set = new Set(data.value.subtype_mastery.map(m => m.chapter_major).filter(Boolean))
  return [...set].sort()
})

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

function selectMajor(major) {
  selectedMajor.value  = major
  selectedMiddle.value = null
  masteryPage.value = 1
}

function selectMiddle(middle) {
  selectedMiddle.value = middle
  masteryPage.value = 1
}

function selectLevel(level) {
  selectedLevel.value = level
  masteryPage.value = 1
}

const filteredMastery = computed(() => {
  if (!data.value) return []
  return data.value.subtype_mastery
    .filter(m => {
      if (selectedMajor.value  && m.chapter_major  !== selectedMajor.value)  return false
      if (selectedMiddle.value && m.chapter_middle !== selectedMiddle.value) return false
      if (selectedLevel.value  && m.level          !== selectedLevel.value)  return false
      return true
    })
    .slice()
    .sort((a, b) => {
      const ma = a.chapter_major || '', mb = b.chapter_major || ''
      if (ma !== mb) return ma.localeCompare(mb, 'ko')
      const ca = a.chapter_middle || '', cb = b.chapter_middle || ''
      if (ca !== cb) return ca.localeCompare(cb, 'ko')
      return (a.problem_subtype || '').localeCompare(b.problem_subtype || '', 'ko')
    })
})

const totalMasteryPages = computed(() =>
  Math.ceil(filteredMastery.value.length / MASTERY_PAGE_SIZE)
)

const visibleMastery = computed(() => {
  const start = (masteryPage.value - 1) * MASTERY_PAGE_SIZE
  return filteredMastery.value.slice(start, start + MASTERY_PAGE_SIZE)
})

// ── 퀴즈 기록 정렬 + 페이지네이션 ──────────────────────
const SESSION_PAGE_SIZE = 6
const sessionOrder  = ref('desc')
const sessionPage   = ref(1)

const sortedSessions = computed(() => {
  if (!data.value) return []
  return [...data.value.sessions].sort((a, b) => {
    const diff = new Date(a.created_at) - new Date(b.created_at)
    return sessionOrder.value === 'desc' ? -diff : diff
  })
})

const totalSessionPages = computed(() =>
  Math.ceil(sortedSessions.value.length / SESSION_PAGE_SIZE)
)

const pagedSessions = computed(() => {
  const start = (sessionPage.value - 1) * SESSION_PAGE_SIZE
  return sortedSessions.value.slice(start, start + SESSION_PAGE_SIZE)
})

function setSessionOrder(order) {
  sessionOrder.value = order
  sessionPage.value  = 1
}

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
      <div class="page-head"><div class="title">학습 이력 분석</div></div>

      <div v-if="loading" class="hist-loading">
        <p class="assistive">불러오는 중…</p>
      </div>

      <template v-else-if="data">
        <!-- ── 유형별 진행 현황 ── -->
        <div class="stack-12" style="margin-bottom: 32px">
          <div class="wds-label-1" style="font-weight: 700; font-size: 24px;">유형별 진행 현황</div>
          <div v-if="!data.subtype_mastery.length" class="assistive wds-body-2">아직 학습 기록이 없어요.</div>
          <template v-else>
            <!-- 단원 + 진행 상태 통합 박스 -->
            <div class="filter-box">
              <!-- 왼쪽: 단원 선택 -->
              <div class="filter-group filter-group--chapter">
                <div class="filter-section-label">단원 선택</div>

                <div class="filter-row">
                  <span class="filter-label">대단원</span>
                  <button class="filter-chip" :data-active="selectedMajor === null" @click="selectMajor(null)">전체</button>
                  <button
                    v-for="major in majorList" :key="major"
                    class="filter-chip" :data-active="selectedMajor === major"
                    @click="selectMajor(major)"
                  >
                    {{ major }}
                  </button>
                </div>

                <div class="filter-row">
                  <span class="filter-label">중단원</span>
                  <button class="filter-chip" :data-active="selectedMiddle === null" @click="selectMiddle(null)">전체</button>
                  <template v-if="selectedMajor">
                    <button
                      v-for="middle in middleList" :key="middle"
                      class="filter-chip" :data-active="selectedMiddle === middle"
                      @click="selectMiddle(middle)"
                    >
                      {{ middle }}
                    </button>
                  </template>
                </div>
              </div>

              <!-- 가운데 짧은 세로선 -->
              <div class="filter-vertical-divider" />

              <!-- 오른쪽: 진행 상태 -->
              <div class="filter-group filter-group--status">
                <div class="filter-section-label">진행 상태</div>

                <div class="filter-row status-filter-row">
                  <button class="filter-chip" :data-active="selectedLevel === null" @click="selectLevel(null)">전체</button>

                  <div class="status-chip-grid">
                    <button
                      v-for="opt in LEVEL_OPTIONS" :key="opt.label"
                      class="filter-chip"
                      :data-active="selectedLevel === opt.label"
                      @click="selectLevel(opt.label)"
                    >
                      <WdsIcon :name="opt.icon" :size="14" color="currentColor" style="margin-right: 4px" />
                      {{ opt.label }}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- 카드 목록 -->
            <div class="card-grid mastery-grid">
              <div v-for="m in visibleMastery" :key="m.problem_subtype" class="mastery-card">
                <div class="between" style="align-items: center">
                  <span class="master-badge" :data-level="m.level">
                    <WdsIcon v-if="m.level === '숙달 완료'" name="medal" :size="15" color="currentColor" />
                    <WdsIcon v-else-if="m.level === '풀이 완료'" name="circle-check" :size="15" color="currentColor" />
                    <WdsIcon v-else-if="m.level === '풀이 중'" name="fire" :size="15" color="currentColor" />
                    <WdsIcon v-else name="bulb" :size="15" color="currentColor" />
                    {{ m.level }}
                  </span>
                  <template v-if="m.accuracy_before != null && m.accuracy_after != null">
                    <span class="rate-jump">
                      <span class="was">{{ m.accuracy_before }}%</span>
                      <WdsIcon name="arrow-right" :size="16" color="var(--label-assistive)" />
                      <span class="now">{{ m.accuracy_after }}%</span>
                    </span>
                  </template>
                  <span v-else class="wds-caption-1" style="color: var(--suql-accent); font-weight: 600; font-size: 16px">정답률 {{ m.accuracy }}%</span>
                </div>
                <div class="wds-caption-1 assistive" style="margin-top: 10px; font-size: 14px">
                  {{ m.chapter_major }}<template v-if="m.chapter_middle"> › {{ m.chapter_middle }}</template>
                </div>
                <div class="wds-label-1" style="font-weight: 700; margin-top: 2px; font-size: 16px">{{ m.problem_subtype }}</div>
                <div class="wds-caption-1 assistive" style="margin-top: 6px; font-size: 15px">{{ m.total_attempts }} / {{ m.total_in_subtype }}문제 시도</div>
              </div>
            </div>

            <!-- 유형 카드 페이지네이션 -->
            <div v-if="totalMasteryPages > 1" class="pagination">
              <button :disabled="masteryPage === 1" @click="masteryPage--">← 이전</button>
              <span class="page-info">{{ masteryPage }} / {{ totalMasteryPages }}</span>
              <button :disabled="masteryPage === totalMasteryPages" @click="masteryPage++">다음 →</button>
            </div>
          </template>
        </div>

        <!-- ── 퀴즈 기록 ── -->
        <div class="stack-12">
          <div class="between" style="align-items: center">
            <div class="wds-label-1" style="font-weight: 700; font-size: 24px">퀴즈 기록</div>
            <div class="order-toggle">
              <button :data-active="sessionOrder === 'desc'" @click="setSessionOrder('desc')">최신순</button>
              <button :data-active="sessionOrder === 'asc'"  @click="setSessionOrder('asc')">과거순</button>
            </div>
          </div>

          <div v-if="!data.sessions.length" class="assistive wds-body-2">아직 풀어본 퀴즈가 없어요.</div>
          <div v-else class="stack-8">
            <div
              v-for="s in pagedSessions" :key="s.session_id"
              class="session-row"
              :class="{ 'session-row--resumable': canResume(s.session_id) }"
            >
              <span class="play-badge play-badge--type">{{ SESSION_TYPE_LABEL[s.session_type] || s.session_type }}</span>
              <div style="flex: 1; min-width: 0">
                <div class="wds-label-1" style="font-weight: 600">
                  {{ s.chapter_middle }}<template v-if="s.chapter_minor"> · {{ s.chapter_minor }}</template>
                </div>
                <div class="wds-caption-1 assistive" style="margin-top: 2px">{{ formatDate(s.created_at) }}</div>
              </div>
              <div style="display: flex; align-items: center; gap: 10px; flex: none">
                <button v-if="canResume(s.session_id)" class="resume-chip" @click="resumeSession(s.session_id)">
                  오답 루프 이어하기 →
                </button>
                <div class="session-score">{{ s.score }} / {{ s.total }}</div>
              </div>
            </div>
          </div>

          <!-- 페이지네이션 -->
          <div v-if="totalSessionPages > 1" class="pagination">
            <button :disabled="sessionPage === 1" @click="sessionPage--">← 이전</button>
            <span class="page-info">{{ sessionPage }} / {{ totalSessionPages }}</span>
            <button :disabled="sessionPage === totalSessionPages" @click="sessionPage++">다음 →</button>
          </div>
        </div>
      </template>
    </div>
  </SidebarShell>
</template>

<style scoped>
.hist-loading {
  display: flex; align-items: center; justify-content: center; padding: 80px 0;
}
.page-head .title { font-size: 32px; }

/* ── 통합 필터 박스 ── */
.filter-box {
  display: flex;
  align-items: center;
  gap: 22px;
  padding: 16px 22px;
  border-radius: 16px;
  border: 1px solid #bfdbfe;
  background: #eff6ff;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.filter-group--chapter {
  flex: 1.2;
}

.filter-group--status {
  flex: 0.8;
}

.filter-vertical-divider {
  width: 1px;
  height: 72px;
  background: #bfdbfe;
  flex: none;
}

.filter-section-label {
  font: var(--weight-semibold) 15px/1 var(--font-sans);
  color: var(--label-alternative);
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.status-filter-row {
  align-items: flex-start;
}

.status-chip-grid {
  display: grid;
  grid-template-columns: repeat(2, max-content);
  gap: 8px;
}

.filter-label {
  font: var(--weight-semibold) 13px/1 var(--font-sans);
  color: var(--label-assistive);
  white-space: nowrap;
  margin-right: 2px;
}

/* 모든 칩 동일한 크기 */
.filter-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 14px;
  border-radius: var(--radius-full);
  border: 1px solid #bfdbfe;
  background: #fff;
  color: var(--label-alternative);
  font: var(--weight-medium) 14px/1 var(--font-sans);
  cursor: pointer;
  transition: background .12s, color .12s, border-color .12s;
}

.filter-chip:hover {
  background: #dbeafe;
}

.filter-chip[data-active="true"] {
  background: var(--suql-accent);
  color: #fff;
  border-color: var(--suql-accent);
}

/* ── 마스터 카드 ── */
.card-grid.mastery-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.mastery-card {
  padding: 18px;
  border-radius: 16px;
  box-shadow: inset 0 0 0 1px var(--line-normal-normal);
}

.more-btn {
  padding: 8px 24px;
  border-radius: var(--radius-full);
  border: 0;
  background: var(--fill-alternative);
  color: var(--label-alternative);
  font: var(--weight-medium) 14px/1 var(--font-sans);
  cursor: pointer;
  transition: background .12s;
}
.more-btn:hover { background: var(--fill-normal); }

/* ── 퀴즈 기록 ── */
.order-toggle {
  display: flex; gap: 4px;
  background: var(--fill-alternative); border-radius: var(--radius-full);
  padding: 3px;
}
.order-toggle button {
  padding: 5px 14px; border-radius: var(--radius-full); border: 0;
  background: transparent; color: var(--label-alternative);
  font: var(--weight-medium) 13px/1 var(--font-sans); cursor: pointer;
  transition: background .12s, color .12s;
}
.order-toggle button[data-active="true"] {
  background: #fff; color: var(--label-normal);
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}
.session-row {
  display: flex; align-items: center; gap: 12px; padding: 14px;
  border-radius: 14px; box-shadow: inset 0 0 0 1px var(--line-normal-normal);
}
.session-row--resumable { box-shadow: inset 0 0 0 1.5px var(--suql-accent); }
.session-score {
  font: var(--weight-bold) 15px/1 var(--font-sans);
  color: var(--suql-accent); flex: none;
}
.resume-chip {
  padding: 6px 12px; border-radius: var(--radius-full);
  border: 1.5px solid var(--suql-accent);
  background: var(--blue-99); color: var(--suql-accent);
  font: var(--weight-semibold) 12px/1 var(--font-sans);
  cursor: pointer; white-space: nowrap; transition: background .12s;
}
.resume-chip:hover { background: var(--blue-95, #e8f0ff); }

/* ── 페이지네이션 ── */
.pagination {
  display: flex; align-items: center; justify-content: center; gap: 16px;
  margin-top: 8px;
}
.pagination button {
  padding: 7px 18px; border-radius: var(--radius-full); border: 0;
  background: var(--fill-alternative); color: var(--label-normal);
  font: var(--weight-medium) 14px/1 var(--font-sans); cursor: pointer;
  transition: background .12s;
}
.pagination button:hover:not(:disabled) { background: var(--fill-normal); }
.pagination button:disabled { opacity: 0.4; cursor: default; }
.page-info {
  font: var(--weight-medium) 14px/1 var(--font-sans);
  color: var(--label-alternative);
}

@media (max-width: 960px) {
  .filter-box {
    flex-direction: column;
    align-items: stretch;
    gap: 14px;
  }

  .filter-vertical-divider {
    width: 100%;
    height: 1px;
  }

  .filter-group--chapter,
  .filter-group--status {
    flex: none;
  }
}

@media (max-width: 760px) {
  .card-grid.mastery-grid {
    grid-template-columns: 1fr;
  }
}
</style>