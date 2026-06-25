<!-- 📄 src/views/my/HistoryView.vue -->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuizStore } from '@/stores/quiz'
import api, { unwrap } from '@/api'
import SidebarShell from '@/components/common/SidebarShell.vue'
import WdsIcon from '@/components/common/WdsIcon.vue'

const router = useRouter()
const quiz   = useQuizStore()

const loading = ref(true)
const data    = ref(null)

// ── 이어하기 ─────────────────────────────────────────
const RESUME_KEY = 'reviewLoop_resume'

const resumeData = computed(() => {
  try {
    const raw = localStorage.getItem(RESUME_KEY)
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
const masteryExpanded = ref(false)
const MASTERY_LIMIT = 12

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
  masteryExpanded.value = false
}

function selectMiddle(middle) {
  selectedMiddle.value = middle
  masteryExpanded.value = false
}

const filteredMastery = computed(() => {
  if (!data.value) return []
  return data.value.subtype_mastery
    .filter(m => {
      if (selectedMajor.value  && m.chapter_major  !== selectedMajor.value)  return false
      if (selectedMiddle.value && m.chapter_middle !== selectedMiddle.value) return false
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

const visibleMastery = computed(() =>
  masteryExpanded.value ? filteredMastery.value : filteredMastery.value.slice(0, MASTERY_LIMIT)
)

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

// 1차 풀이 session_id → 해당 보완 세션들 묶기
const sessionTree = computed(() => {
  const sessions = pagedSessions.value
  const roots = []
  const childMap = {}

  sessions.forEach(s => {
    if (s.session_type === 'normal') {
      roots.push({ ...s, children: [] })
    } else {
      if (!childMap[s.parent_session_id]) childMap[s.parent_session_id] = []
      childMap[s.parent_session_id].push(s)
    }
  })

  return roots.map(r => ({
    ...r,
    children: childMap[r.session_id] || [],
  }))
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
        <!-- ── 유형별 마스터 현황 ── -->
        <div class="stack-12" style="margin-bottom: 32px">
          <div class="wds-label-1" style="font-weight: 700; font-size: 22px;">유형별 마스터 현황</div>
          <div v-if="!data.subtype_mastery.length" class="assistive wds-body-2">아직 학습 기록이 없어요.</div>
          <template v-else>
            <!-- 단원 선택 박스 -->
            <div class="filter-box">
              <div class="filter-section-label" style="margin-top: 0; font-size: 17px">단원 선택</div>

              <!-- 대단원 필터 -->
              <div class="filter-row">
                <span class="filter-label">대단원</span>
                <button class="filter-chip" :data-active="selectedMajor === null" @click="selectMajor(null)">전체</button>
                <button
                  v-for="major in majorList" :key="major"
                  class="filter-chip" :data-active="selectedMajor === major"
                  @click="selectMajor(major)">{{ major }}</button>
              </div>

              <!-- 중단원 필터 (항상 표시, 대단원 선택 시 목록 생김) -->
              <div class="filter-row">
                <span class="filter-label">중단원</span>
                <button class="filter-chip filter-chip--sub" :data-active="selectedMiddle === null" @click="selectMiddle(null)">전체</button>
                <template v-if="selectedMajor">
                  <button
                    v-for="middle in middleList" :key="middle"
                    class="filter-chip filter-chip--sub" :data-active="selectedMiddle === middle"
                    @click="selectMiddle(middle)">{{ middle }}</button>
                </template>
              </div>
            </div>

            <!-- 카드 목록 -->
            <div class="card-grid cols-4">
              <div v-for="m in visibleMastery" :key="m.problem_subtype" class="mastery-card">
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

            <!-- 더보기 버튼 -->
            <div v-if="filteredMastery.length > MASTERY_LIMIT" style="text-align: center; margin-top: 4px">
              <button class="more-btn" @click="masteryExpanded = !masteryExpanded">
                {{ masteryExpanded ? '접기 ▲' : `더보기 (${filteredMastery.length - MASTERY_LIMIT}개 더) ▼` }}
              </button>
            </div>
          </template>
        </div>

        <!-- ── 퀴즈 기록 ── -->
        <div class="stack-12">
          <div class="between" style="align-items: center">
            <div class="wds-label-1" style="font-weight: 700; font-size: 22px">퀴즈 기록</div>
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

/* ── 단원 선택 박스 ── */
.filter-box {
  display: flex; flex-direction: column; gap: 12px;
  padding: 16px 20px;
  border-radius: 16px;
  border: 1px solid #bfdbfe;
  background: #eff6ff;
  margin-bottom: 4px;
}

/* ── 유형 필터 ── */
.filter-section-label {
  font: var(--weight-semibold) 15px/1 var(--font-sans);
  color: var(--label-alternative);
  margin-bottom: -4px;
}
.filter-row {
  display: flex; flex-wrap: wrap; align-items: center; gap: 8px;
}
.filter-label {
  font: var(--weight-semibold) 13px/1 var(--font-sans);
  color: var(--label-assistive);
  white-space: nowrap;
  margin-right: 2px;
}
.filter-chip {
  padding: 6px 14px; border-radius: var(--radius-full);
  border: 1px solid #bfdbfe;
  background: #fff; color: var(--label-alternative);
  font: var(--weight-medium) 15px/1 var(--font-sans);
  cursor: pointer; transition: background .12s, color .12s;
}
.filter-chip:hover { background: #dbeafe; }
.filter-chip[data-active="true"] { background: var(--suql-accent); color: #fff; border-color: var(--suql-accent); }
.filter-chip--sub {
  font-size: 15px; padding: 5px 12px;
  background: #fff; border: 1px solid #bfdbfe;
}
.filter-chip--sub[data-active="true"] { background: var(--suql-accent); color: #fff; border-color: var(--suql-accent); }

/* ── 마스터 카드 ── */
.mastery-card {
  padding: 18px; border-radius: 16px;
  box-shadow: inset 0 0 0 1px var(--line-normal-normal);
}
.more-btn {
  padding: 8px 24px; border-radius: var(--radius-full); border: 0;
  background: var(--fill-alternative); color: var(--label-alternative);
  font: var(--weight-medium) 14px/1 var(--font-sans); cursor: pointer;
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
.session-row--resumable {
  box-shadow: inset 0 0 0 1.5px var(--suql-accent);
}
.session-row--child { background: var(--background-normal-alternative); }
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

/* ── 보완 세션 들여쓰기 ── */
.review-group {
  display: flex; gap: 0; margin-left: 20px;
}
.review-line {
  width: 2px; background: var(--line-normal-normal);
  border-radius: 2px; margin-right: 12px; flex: none;
}
.review-children { display: flex; flex-direction: column; gap: 8px; flex: 1; }

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
</style>